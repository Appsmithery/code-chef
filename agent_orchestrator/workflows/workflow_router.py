"""
Workflow Router - Smart workflow selection with heuristic matching and LLM fallback.

This module implements intelligent workflow routing based on:
1. Heuristic rules (keywords, file patterns, branch patterns) - fast path
2. LLM-based semantic matching - fallback for ambiguous cases
3. Confidence scoring for HITL confirmation when below threshold

Architecture:
- Rule-based matching first (zero LLM tokens, <10ms)
- LLM fallback for semantic understanding when rules don't match
- Confidence threshold triggers user confirmation via Quick Pick
"""

import logging
import os
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from pydantic import BaseModel, Field
from langsmith import traceable

logger = logging.getLogger(__name__)


class SelectionMethod(str, Enum):
    """How the workflow was selected."""

    HEURISTIC = "heuristic"
    LLM = "llm"
    EXPLICIT = "explicit"
    DEFAULT = "default"


class WorkflowSelection(BaseModel):
    """Result of workflow selection process."""

    workflow_name: str = Field(
        ...,
        description="Name of the selected workflow template (without .workflow.yaml extension)",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0) for the selection",
    )
    method: SelectionMethod = Field(
        default=SelectionMethod.HEURISTIC, description="How the workflow was selected"
    )
    reasoning: str = Field(
        default="", description="Explanation for why this workflow was selected"
    )
    matched_rules: List[str] = Field(
        default_factory=list,
        description="List of heuristic rules that matched (if any)",
    )
    alternatives: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Alternative workflows with their confidence scores",
    )
    requires_confirmation: bool = Field(
        default=False,
        description="Whether user confirmation is required (confidence below threshold)",
    )
    context_variables: Dict[str, Any] = Field(
        default_factory=dict, description="Extracted context variables for the workflow"
    )


class WorkflowTemplate(BaseModel):
    """Metadata for a workflow template."""

    name: str
    version: str
    description: str
    required_context: List[str] = Field(default_factory=list)
    optional_context: List[str] = Field(default_factory=list)
    steps_count: int = 0
    agents_involved: List[str] = Field(default_factory=list)
    estimated_duration_minutes: int = 0
    risk_level: str = "low"


class HeuristicRule(BaseModel):
    """A single heuristic matching rule."""

    id: str
    workflow: str
    priority: int = Field(default=50, ge=0, le=100)
    keywords: List[str] = Field(default_factory=list)
    file_patterns: List[str] = Field(default_factory=list)
    branch_patterns: List[str] = Field(default_factory=list)
    context_requirements: List[str] = Field(default_factory=list)
    confidence_boost: float = Field(default=0.0, ge=-0.5, le=0.5)


class WorkflowRouter:
    """
    Smart workflow router with heuristic matching and LLM fallback.

    Selection Flow:
    1. Check for explicit workflow override → return immediately
    2. Run heuristic matching (keywords, patterns) → fast path
    3. If no match or low confidence, use LLM for semantic selection
    4. If confidence below threshold, mark for user confirmation
    """

    # Default confidence threshold for requiring user confirmation
    DEFAULT_CONFIRM_THRESHOLD = 0.7

    def __init__(
        self,
        templates_dir: str = "agent_orchestrator/workflows/templates",
        rules_path: str = "agent_orchestrator/agents/supervisor/workflows/workflow-router.rules.yaml",
        gradient_client: Optional[Any] = None,
        confirm_threshold: float = DEFAULT_CONFIRM_THRESHOLD,
    ):
        self.templates_dir = Path(templates_dir)
        self.rules_path = Path(rules_path)
        self.gradient_client = gradient_client
        self.confirm_threshold = confirm_threshold

        # Load heuristic rules
        self.rules: List[HeuristicRule] = self._load_rules()

        # Cache available templates
        self._templates_cache: Optional[Dict[str, WorkflowTemplate]] = None
        self._cache_timestamp: Optional[datetime] = None

        logger.info(
            f"WorkflowRouter initialized: {len(self.rules)} rules, "
            f"confirm_threshold={self.confirm_threshold}"
        )

    def _load_rules(self) -> List[HeuristicRule]:
        """Load heuristic rules from YAML file."""
        if not self.rules_path.exists():
            logger.warning(f"Rules file not found: {self.rules_path}")
            return []

        try:
            with open(self.rules_path, "r") as f:
                data = yaml.safe_load(f)

            rules = []
            for rule_data in data.get("rules", []):
                rules.append(HeuristicRule(**rule_data))

            # Sort by priority (higher first)
            rules.sort(key=lambda r: r.priority, reverse=True)

            logger.info(f"Loaded {len(rules)} heuristic rules from {self.rules_path}")
            return rules

        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
            return []

    def get_available_templates(self) -> Dict[str, WorkflowTemplate]:
        """
        Get metadata for all available workflow templates.
        Results are cached for 5 minutes.
        """
        now = datetime.utcnow()
        cache_ttl_seconds = 300  # 5 minutes

        if (
            self._templates_cache is not None
            and self._cache_timestamp is not None
            and (now - self._cache_timestamp).total_seconds() < cache_ttl_seconds
        ):
            return self._templates_cache

        templates = {}

        if not self.templates_dir.exists():
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            return templates

        for template_file in self.templates_dir.glob("*.workflow.yaml"):
            try:
                with open(template_file, "r") as f:
                    data = yaml.safe_load(f)

                # Extract template metadata
                name = template_file.stem.replace(".workflow", "")
                steps = data.get("steps", [])
                agents = list(
                    set(step.get("agent") for step in steps if step.get("agent"))
                )

                # Extract required context from templates
                required_context = self._extract_required_context(data)

                templates[name] = WorkflowTemplate(
                    name=name,
                    version=data.get("version", "1.0"),
                    description=data.get("description", ""),
                    required_context=required_context,
                    optional_context=data.get("optional_context", []),
                    steps_count=len(steps),
                    agents_involved=agents,
                    estimated_duration_minutes=self._estimate_duration(steps),
                    risk_level=self._assess_risk_level(data),
                )

            except Exception as e:
                logger.error(f"Failed to load template {template_file}: {e}")
                continue

        self._templates_cache = templates
        self._cache_timestamp = now

        logger.info(f"Loaded {len(templates)} workflow templates")
        return templates

    def _extract_required_context(self, template_data: Dict[str, Any]) -> List[str]:
        """Extract required context variables from template Jinja expressions."""
        required = set()

        # Common context variables
        context_patterns = [
            r"\{\{\s*context\.(\w+)\s*\}\}",  # {{ context.variable }}
            r"\{\{\s*inputs\.(\w+)\s*\}\}",  # {{ inputs.variable }}
        ]

        template_str = yaml.dump(template_data)

        for pattern in context_patterns:
            matches = re.findall(pattern, template_str)
            required.update(matches)

        return list(required)

    def _estimate_duration(self, steps: List[Dict]) -> int:
        """Estimate workflow duration based on step types."""
        base_minutes = 0
        for step in steps:
            step_type = step.get("type", "")
            if step_type == "agent_call":
                base_minutes += 2  # Agent calls take ~2 min
            elif step_type == "hitl_approval":
                base_minutes += 5  # HITL waits average ~5 min
            elif step_type == "conditional":
                base_minutes += 1  # Conditionals are fast
            else:
                base_minutes += 1
        return base_minutes

    def _assess_risk_level(self, template_data: Dict[str, Any]) -> str:
        """Assess workflow risk level based on steps and agents."""
        steps = template_data.get("steps", [])

        # Check for high-risk indicators
        has_infra = any(s.get("agent") == "infrastructure" for s in steps)
        has_deploy = any("deploy" in str(s).lower() for s in steps)
        has_production = "production" in str(template_data).lower()

        if has_production or (has_infra and has_deploy):
            return "high"
        elif has_infra or has_deploy:
            return "medium"
        return "low"

    @traceable(name="workflow_select", tags=["workflow", "routing"])
    async def select_workflow(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        explicit_workflow: Optional[str] = None,
        dry_run: bool = False,
    ) -> WorkflowSelection:
        """
        Select the most appropriate workflow for a task.

        Args:
            task_description: Natural language description of the task
            context: Project context (files, branch, etc.)
            explicit_workflow: If provided, skip selection and use this workflow
            dry_run: If True, return selection without executing

        Returns:
            WorkflowSelection with chosen workflow and confidence
        """
        context = context or {}
        templates = self.get_available_templates()

        # Phase 1: Explicit override
        if explicit_workflow:
            if explicit_workflow in templates:
                return WorkflowSelection(
                    workflow_name=explicit_workflow,
                    confidence=1.0,
                    method=SelectionMethod.EXPLICIT,
                    reasoning=f"Workflow explicitly specified: {explicit_workflow}",
                    context_variables=self._extract_context_variables(
                        explicit_workflow, task_description, context
                    ),
                )
            else:
                logger.warning(f"Explicit workflow not found: {explicit_workflow}")
                # Fall through to normal selection

        # Phase 2: Heuristic matching
        heuristic_result = self._heuristic_match(task_description, context)

        if heuristic_result and heuristic_result.confidence >= self.confirm_threshold:
            logger.info(
                f"Heuristic match: {heuristic_result.workflow_name} "
                f"(confidence={heuristic_result.confidence:.2f})"
            )
            return heuristic_result

        # Phase 3: LLM fallback
        if self.gradient_client:
            llm_result = await self._llm_select(task_description, context, templates)

            # Combine with heuristic if both have results
            if heuristic_result and llm_result:
                combined = self._combine_selections(heuristic_result, llm_result)
                return combined
            elif llm_result:
                return llm_result

        # Phase 4: Return heuristic result or default
        if heuristic_result:
            heuristic_result.requires_confirmation = True
            return heuristic_result

        # Default to feature workflow if nothing matches
        default_workflow = "feature"
        if default_workflow in templates:
            return WorkflowSelection(
                workflow_name=default_workflow,
                confidence=0.5,
                method=SelectionMethod.DEFAULT,
                reasoning="No matching workflow found, using default feature workflow",
                requires_confirmation=True,
                context_variables=self._extract_context_variables(
                    default_workflow, task_description, context
                ),
            )

        # Fallback to first available template
        first_template = next(iter(templates.keys()), "feature")
        return WorkflowSelection(
            workflow_name=first_template,
            confidence=0.3,
            method=SelectionMethod.DEFAULT,
            reasoning="Using first available workflow template",
            requires_confirmation=True,
        )

    def _heuristic_match(
        self,
        task_description: str,
        context: Dict[str, Any],
    ) -> Optional[WorkflowSelection]:
        """
        Match workflow using heuristic rules (keywords, patterns).
        Fast path with zero LLM calls.
        """
        task_lower = task_description.lower()
        branch = context.get("git_branch", "") or ""
        files = context.get("open_files", []) or []

        matched_workflows: Dict[str, Tuple[float, List[str]]] = {}

        for rule in self.rules:
            score = 0.0
            matched_criteria = []

            # Keyword matching
            if rule.keywords:
                keyword_matches = sum(
                    1 for kw in rule.keywords if kw.lower() in task_lower
                )
                if keyword_matches > 0:
                    score += 0.3 * (keyword_matches / len(rule.keywords))
                    matched_criteria.append(
                        f"keywords: {keyword_matches}/{len(rule.keywords)}"
                    )

            # Branch pattern matching
            if rule.branch_patterns and branch:
                for pattern in rule.branch_patterns:
                    if re.match(pattern, branch, re.IGNORECASE):
                        score += 0.25
                        matched_criteria.append(f"branch: {pattern}")
                        break

            # File pattern matching
            if rule.file_patterns and files:
                for pattern in rule.file_patterns:
                    file_matches = [f for f in files if re.match(pattern, f)]
                    if file_matches:
                        score += 0.2
                        matched_criteria.append(f"files: {pattern}")
                        break

            # Context requirements
            if rule.context_requirements:
                ctx_matches = sum(
                    1
                    for req in rule.context_requirements
                    if req in context and context[req]
                )
                if ctx_matches == len(rule.context_requirements):
                    score += 0.15
                    matched_criteria.append("context: all required")

            # Apply confidence boost/penalty
            score += rule.confidence_boost

            # Clamp to valid range
            score = max(0.0, min(1.0, score))

            if score > 0:
                if rule.workflow not in matched_workflows:
                    matched_workflows[rule.workflow] = (score, matched_criteria)
                else:
                    existing_score = matched_workflows[rule.workflow][0]
                    if score > existing_score:
                        matched_workflows[rule.workflow] = (score, matched_criteria)

        if not matched_workflows:
            return None

        # Sort by score and get best match
        sorted_matches = sorted(
            matched_workflows.items(), key=lambda x: x[1][0], reverse=True
        )

        best_workflow, (best_score, matched_rules) = sorted_matches[0]

        # Build alternatives list
        alternatives = [
            {"workflow": wf, "confidence": score, "rules": rules}
            for wf, (score, rules) in sorted_matches[1:4]  # Top 3 alternatives
        ]

        return WorkflowSelection(
            workflow_name=best_workflow,
            confidence=best_score,
            method=SelectionMethod.HEURISTIC,
            reasoning=f"Matched via heuristic rules: {', '.join(matched_rules)}",
            matched_rules=matched_rules,
            alternatives=alternatives,
            requires_confirmation=best_score < self.confirm_threshold,
            context_variables=self._extract_context_variables(
                best_workflow, task_description, context
            ),
        )

    @traceable(name="workflow_llm_select", tags=["workflow", "llm"])
    async def _llm_select(
        self,
        task_description: str,
        context: Dict[str, Any],
        templates: Dict[str, WorkflowTemplate],
    ) -> Optional[WorkflowSelection]:
        """
        Use LLM for semantic workflow selection when heuristics fail.
        """
        if not self.gradient_client:
            return None

        # Build template descriptions for LLM
        template_list = "\n".join(
            [
                f"- {name}: {t.description} (agents: {', '.join(t.agents_involved)})"
                for name, t in templates.items()
            ]
        )

        prompt = f"""Select the most appropriate workflow for this task.

Task Description:
{task_description}

Context:
- Branch: {context.get('git_branch', 'unknown')}
- Project Type: {context.get('project_type', 'unknown')}
- Open Files: {', '.join(context.get('open_files', [])[:5])}

Available Workflows:
{template_list}

Respond in JSON format:
{{
    "workflow": "<workflow-name>",
    "confidence": <0.0-1.0>,
    "reasoning": "<explanation>"
}}"""

        try:
            response = await self.gradient_client.chat_async(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.1,
            )

            # Parse JSON response
            import json

            content = response.get("content", "")

            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r"\{[^{}]+\}", content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())

                workflow = result.get("workflow", "")
                if workflow in templates:
                    return WorkflowSelection(
                        workflow_name=workflow,
                        confidence=float(result.get("confidence", 0.7)),
                        method=SelectionMethod.LLM,
                        reasoning=result.get("reasoning", ""),
                        requires_confirmation=float(result.get("confidence", 0.7))
                        < self.confirm_threshold,
                        context_variables=self._extract_context_variables(
                            workflow, task_description, context
                        ),
                    )

        except Exception as e:
            logger.error(f"LLM workflow selection failed: {e}")

        return None

    def _combine_selections(
        self,
        heuristic: WorkflowSelection,
        llm: WorkflowSelection,
    ) -> WorkflowSelection:
        """Combine heuristic and LLM selections for better accuracy."""

        # If both agree, boost confidence
        if heuristic.workflow_name == llm.workflow_name:
            combined_confidence = min(
                1.0, (heuristic.confidence + llm.confidence) / 2 + 0.15
            )
            return WorkflowSelection(
                workflow_name=heuristic.workflow_name,
                confidence=combined_confidence,
                method=SelectionMethod.HEURISTIC,  # Heuristic took precedence
                reasoning=f"Heuristic and LLM agree. {heuristic.reasoning}",
                matched_rules=heuristic.matched_rules,
                alternatives=[
                    {
                        "workflow": llm.workflow_name,
                        "confidence": llm.confidence,
                        "source": "llm",
                    }
                ]
                + heuristic.alternatives,
                requires_confirmation=combined_confidence < self.confirm_threshold,
                context_variables=heuristic.context_variables,
            )

        # If they disagree, prefer the one with higher confidence
        if heuristic.confidence >= llm.confidence:
            heuristic.alternatives.insert(
                0,
                {
                    "workflow": llm.workflow_name,
                    "confidence": llm.confidence,
                    "source": "llm",
                    "reasoning": llm.reasoning,
                },
            )
            return heuristic
        else:
            llm.alternatives.insert(
                0,
                {
                    "workflow": heuristic.workflow_name,
                    "confidence": heuristic.confidence,
                    "source": "heuristic",
                    "rules": heuristic.matched_rules,
                },
            )
            return llm

    def _extract_context_variables(
        self,
        workflow_name: str,
        task_description: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Extract context variables needed for the workflow."""
        variables = {}

        # Common extractions
        variables["task_description"] = task_description
        variables["branch"] = context.get("git_branch")
        variables["project_path"] = context.get("workspace_path")
        variables["language"] = context.get("project_type")

        # Extract PR number from branch name (e.g., "feature/123-description")
        branch = context.get("git_branch", "") or ""
        pr_match = re.search(r"(\d+)", branch)
        if pr_match:
            variables["pr_number"] = pr_match.group(1)

        # Extract issue ID from branch (e.g., "DEV-123-feature")
        issue_match = re.search(r"([A-Z]+-\d+)", branch)
        if issue_match:
            variables["issue_id"] = issue_match.group(1)

        # GitHub context
        if context.get("github_repo_url"):
            variables["repo_url"] = context["github_repo_url"]
        if context.get("github_commit_sha"):
            variables["commit_sha"] = context["github_commit_sha"]

        # Environment inference
        if "production" in task_description.lower() or "prod" in branch.lower():
            variables["environment"] = "production"
        elif "staging" in task_description.lower() or "stage" in branch.lower():
            variables["environment"] = "staging"
        else:
            variables["environment"] = "development"

        return variables


# Module-level singleton
_workflow_router: Optional[WorkflowRouter] = None


def get_workflow_router(
    gradient_client: Optional[Any] = None,
    confirm_threshold: float = WorkflowRouter.DEFAULT_CONFIRM_THRESHOLD,
) -> WorkflowRouter:
    """Get or create the workflow router singleton."""
    global _workflow_router

    if _workflow_router is None:
        _workflow_router = WorkflowRouter(
            gradient_client=gradient_client,
            confirm_threshold=confirm_threshold,
        )

    return _workflow_router
