"""
Workflow Engine for declarative multi-agent workflows with Event Sourcing.

This module implements a workflow engine that:
1. Loads workflow YAML templates
2. Executes steps sequentially with state management
3. Handles LLM decision gates for dynamic routing
4. Integrates with LangGraph checkpointing for HITL approvals
5. Supports resource locking to prevent concurrent operations
6. Renders Jinja2-style templates for dynamic payloads
7. Event Sourcing: All state transitions via immutable events (Week 4)

Architecture:
- Pure Python orchestration (no LangGraph for workflow logic)
- LangGraph only for HITL checkpointing
- Deterministic step execution with LLM decision gates at strategic points
- Event-sourced state: Events are source of truth, state is derived
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from jinja2 import Template
from langsmith import traceable
from pydantic import BaseModel, Field

from shared.lib.llm_client import LLMClient

# Initialize logger
logger = logging.getLogger(__name__)
from shared.lib.dependency_handler import (
    DependencyErrorHandler,
    DependencyRemediationResult,
    get_dependency_handler,
)
from shared.lib.workflow_events import serialize_event, sign_event
from shared.lib.workflow_reducer import (
    WorkflowAction,
    WorkflowEvent,
    replay_workflow,
    workflow_reducer,
)

# Import error recovery engine for tiered recovery (CHEF-Error-Handling)
try:
    from shared.lib.error_classification import (
        ErrorCategory,
        RecoveryTier,
        classify_error,
    )
    from shared.lib.error_recovery_engine import (
        ErrorRecoveryEngine,
        RecoveryOutcome,
        RecoveryResult,
        get_error_recovery_engine,
    )

    ERROR_RECOVERY_ENABLED = True
except ImportError:
    ERROR_RECOVERY_ENABLED = False
    ErrorRecoveryEngine = None
    get_error_recovery_engine = None
    logger.warning("Error recovery engine not available")

try:
    from shared.services.state.client import StateClient
except ImportError:
    # Fallback if state service not available
    StateClient = None


class StepType(str, Enum):
    """Workflow step types."""

    AGENT_CALL = "agent_call"
    HITL_APPROVAL = "hitl_approval"
    CONDITIONAL = "conditional"
    NOTIFICATION = "notification"


class DecisionGateType(str, Enum):
    """Decision gate evaluation types."""

    LLM_ASSESSMENT = "llm_assessment"
    DETERMINISTIC_CHECK = "deterministic_check"


class WorkflowStatus(str, Enum):
    """Workflow execution statuses."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"  # Awaiting HITL approval
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class StepStatus(str, Enum):
    """Individual step statuses."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStep(BaseModel):
    """A single workflow step definition."""

    id: str
    type: StepType
    agent: Optional[str] = None  # For agent_call steps
    deterministic: bool = True
    payload: Dict[str, Any] = Field(default_factory=dict)
    resource_lock: Optional[str] = None
    decision_gate: Optional[Dict[str, Any]] = None
    risk_assessment: Optional[Dict[str, Any]] = None  # For HITL steps
    on_success: Optional[str] = None
    on_failure: Optional[str] = None
    on_approved: Optional[str] = None
    on_rejected: Optional[str] = None
    condition: Optional[str] = None  # For conditional steps
    on_true: Optional[str] = None
    on_false: Optional[str] = None


class WorkflowDefinition(BaseModel):
    """Complete workflow definition from YAML."""

    name: str
    version: str
    description: str
    steps: List[WorkflowStep]
    error_handling: List[Dict[str, Any]] = Field(default_factory=list)
    notifications: List[Dict[str, Any]] = Field(default_factory=list)


class WorkflowState(BaseModel):
    """Runtime workflow state."""

    workflow_id: str
    definition: WorkflowDefinition
    status: WorkflowStatus
    current_step: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)  # {step_id: step_output}
    step_statuses: Dict[str, StepStatus] = Field(default_factory=dict)
    resource_locks: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    failed_step: Optional[str] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class WorkflowEngine:
    """
    Declarative workflow engine with LLM decision gates.

    Features:
    - YAML template loading
    - Sequential step execution
    - LLM-based decision routing
    - HITL approval integration
    - Resource locking
    - Jinja2 template rendering
    - State persistence
    """

    # Task 5.3: Workflow TTL Management (Week 5 Zen Pattern Integration)
    # Auto-expire abandoned workflows to prevent memory leaks
    WORKFLOW_TTL_HOURS = int(os.getenv("WORKFLOW_TTL_HOURS", "24"))

    def __init__(
        self,
        templates_dir: str = "agent_orchestrator/workflows/templates",
        llm_client: Optional[LLMClient] = None,
        state_client: Optional[Any] = None,
        linear_client: Optional[Any] = None,
    ):
        self.templates_dir = Path(templates_dir)
        self.llm_client = llm_client  # Will be provided by caller
        self.state_client = state_client  # Will be provided by caller
        self.linear_client = linear_client  # For dependency escalation

        # Initialize dependency error handler for auto-remediation
        self.dependency_handler = get_dependency_handler(
            orchestrator_root=str(Path(__file__).parent.parent.parent),
            linear_client=linear_client,
        )

        # Initialize error recovery engine for tiered recovery (CHEF-Error-Handling)
        self.error_recovery_engine: Optional[ErrorRecoveryEngine] = None
        if ERROR_RECOVERY_ENABLED:
            try:
                self.error_recovery_engine = get_error_recovery_engine()
                logger.info(
                    "[WorkflowEngine] Error recovery engine initialized - "
                    "Tiered recovery enabled for Tier 0-4"
                )
            except Exception as e:
                logger.warning(
                    f"[WorkflowEngine] Failed to initialize error recovery engine: {e}"
                )

        # Task 5.3: Calculate TTL in seconds
        self.ttl_seconds = self.WORKFLOW_TTL_HOURS * 3600
        logger.info(
            f"Workflow TTL: {self.WORKFLOW_TTL_HOURS}h ({self.ttl_seconds}s) - "
            f"Zen pattern for memory leak prevention"
        )

    def load_workflow(self, template_name: str) -> WorkflowDefinition:
        """
        Load workflow definition from YAML template.

        Args:
            template_name: Name of template file (e.g., "pr-deployment.workflow.yaml")

        Returns:
            WorkflowDefinition: Parsed workflow definition
        """
        template_path = self.templates_dir / template_name

        if not template_path.exists():
            raise FileNotFoundError(f"Workflow template not found: {template_path}")

        with open(template_path, "r") as f:
            yaml_data = yaml.safe_load(f)

        # Convert steps to WorkflowStep objects
        steps = [WorkflowStep(**step) for step in yaml_data.get("steps", [])]

        return WorkflowDefinition(
            name=yaml_data["name"],
            version=yaml_data["version"],
            description=yaml_data["description"],
            steps=steps,
            error_handling=yaml_data.get("error_handling", []),
            notifications=yaml_data.get("notifications", []),
        )

    @traceable(name="workflow_execute", tags=["workflow", "engine", "orchestration"])
    async def execute_workflow(
        self,
        template_name: str,
        context: Dict[str, Any],
    ) -> WorkflowState:
        """
        Execute a workflow from start to completion using event sourcing.

        Args:
            template_name: Name of workflow template
            context: Initial context variables (e.g., pr_number, branch, environment)

        Returns:
            WorkflowState: Final workflow state
        """
        workflow_id = str(uuid.uuid4())
        definition = self.load_workflow(template_name)

        # Emit START_WORKFLOW event (event sourcing starts here)
        first_step_id = definition.steps[0].id if definition.steps else None
        await self._emit_event(
            workflow_id=workflow_id,
            action=WorkflowAction.START_WORKFLOW,
            step_id=first_step_id,
            data={
                "context": context,
                "template_name": template_name,
                "template_version": definition.version,
                "participating_agents": [
                    step.agent for step in definition.steps if step.agent
                ],
            },
        )

        # Reconstruct state from events (event sourcing: state is derived)
        state_dict = await self._reconstruct_state_from_events(workflow_id)

        # Convert to WorkflowState model for backward compatibility
        state = WorkflowState(
            workflow_id=workflow_id,
            definition=definition,
            status=WorkflowStatus(state_dict.get("status", "running")),
            context=context,
            current_step=first_step_id,
            step_statuses={step.id: StepStatus.PENDING for step in definition.steps},
        )

        # Execute steps sequentially
        try:
            current_step_id = first_step_id

            while current_step_id and current_step_id != "workflow_complete":
                step = self._get_step_by_id(definition, current_step_id)

                # Execute step
                step_output = await self._execute_step(step, state)

                # Emit COMPLETE_STEP event (instead of direct mutation)
                next_step_id = await self._determine_next_step(step, step_output, state)
                await self._emit_event(
                    workflow_id=workflow_id,
                    action=WorkflowAction.COMPLETE_STEP,
                    step_id=current_step_id,
                    data={"result": step_output, "next_step": next_step_id},
                )

                # Reconstruct state from events
                state_dict = await self._reconstruct_state_from_events(workflow_id)
                state.outputs = state_dict.get("outputs", {})
                state.status = WorkflowStatus(state_dict.get("status", "running"))

                # Check for HITL pause
                if state.status == WorkflowStatus.PAUSED:
                    return state

                # Create snapshot every 10 events for performance
                if await self._should_create_snapshot(workflow_id):
                    await self._create_snapshot(workflow_id, state_dict)

                current_step_id = next_step_id

            # Workflow completed - state is already updated via events
            return state

        except Exception as e:
            # Emit FAIL_STEP event (instead of direct mutation)
            await self._emit_event(
                workflow_id=workflow_id,
                action=WorkflowAction.FAIL_STEP,
                step_id=current_step_id,
                data={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "retriable": isinstance(e, (TimeoutError, ConnectionError)),
                },
            )

            # Attempt error handling
            await self._handle_error(state, step, e)

            raise

    @traceable(name="workflow_execute_step", tags=["workflow", "step"])
    async def _execute_step(
        self,
        step: WorkflowStep,
        state: WorkflowState,
    ) -> Dict[str, Any]:
        """Execute a single workflow step."""

        # Acquire resource lock if needed
        if step.resource_lock:
            await self._acquire_lock(step.resource_lock, state)

        try:
            if step.type == StepType.AGENT_CALL:
                return await self._execute_agent_call(step, state)

            elif step.type == StepType.HITL_APPROVAL:
                return await self._execute_hitl_approval(step, state)

            elif step.type == StepType.CONDITIONAL:
                return await self._execute_conditional(step, state)

            elif step.type == StepType.NOTIFICATION:
                return await self._execute_notification(step, state)

            else:
                raise ValueError(f"Unknown step type: {step.type}")

        finally:
            # Release resource lock
            if step.resource_lock:
                await self._release_lock(step.resource_lock, state)

    @traceable(name="workflow_agent_call", tags=["workflow", "agent", "llm"])
    async def _execute_agent_call(
        self,
        step: WorkflowStep,
        state: WorkflowState,
    ) -> Dict[str, Any]:
        """Execute an agent call step."""

        # Render payload with Jinja2
        rendered_payload = self._render_template(step.payload, state)

        # Execute agent via LangGraph workflow
        try:
            from graph import app as workflow_app
            from langchain_core.messages import HumanMessage

            # Build agent-specific prompt from payload
            agent_prompt = self._build_agent_prompt(step.agent, rendered_payload)

            # Create workflow state for agent execution
            agent_state = {
                "messages": [HumanMessage(content=agent_prompt)],
                "current_agent": step.agent,
                "next_agent": "",
                "task_result": {},
                "approvals": [],
                "requires_approval": False,
            }

            # Execute agent
            config = {"configurable": {"thread_id": f"{state.workflow_id}_{step.id}"}}
            final_state = await workflow_app.ainvoke(agent_state, config=config)

            # Extract agent response
            messages = final_state.get("messages", [])
            response = messages[-1].content if messages else "No response"

            # CHEF-207: Emit CAPTURE_INSIGHT events for any insights captured by the agent
            captured_insights = final_state.get("captured_insights", [])
            for insight in captured_insights:
                await self._emit_event(
                    workflow_id=state.workflow_id,
                    action=WorkflowAction.CAPTURE_INSIGHT,
                    step_id=step.id,
                    data={
                        "agent_id": insight.get("agent_id", step.agent),
                        "insight_type": insight.get("insight_type", "general"),
                        "content": insight.get("content", "")[
                            :500
                        ],  # Truncate for event storage
                        "confidence": insight.get("confidence", 0.8),
                        "source_step": step.id,
                    },
                )

            return {
                "agent": step.agent,
                "status": "success",
                "response": response,
                "task_result": final_state.get("task_result", {}),
                "payload": rendered_payload,
                "insights_captured": len(captured_insights),
            }

        except Exception as e:
            # Fallback to mock response if agent execution fails
            return {
                "agent": step.agent,
                "status": "error",
                "error": str(e),
                "payload": rendered_payload,
            }

    @traceable(name="workflow_hitl_approval", tags=["workflow", "hitl", "approval"])
    async def _execute_hitl_approval(
        self,
        step: WorkflowStep,
        state: WorkflowState,
    ) -> Dict[str, Any]:
        """Execute HITL approval step with event sourcing."""

        # Evaluate risk assessment
        risk_assessment = await self._evaluate_risk_assessment(step, state)

        # Check if auto-approval is possible
        if (
            risk_assessment.get("risk_level") == "low"
            and risk_assessment.get("approver_role") == "none"
        ):
            # Emit APPROVE_GATE event (auto-approved)
            await self._emit_event(
                workflow_id=state.workflow_id,
                action=WorkflowAction.APPROVE_GATE,
                step_id=step.id,
                data={
                    "approver": "system",
                    "approver_role": "auto",
                    "comment": "Auto-approved due to low risk assessment",
                },
            )

            return {
                "approval_status": "auto_approved",
                "risk_assessment": risk_assessment,
            }

        # Create Linear approval issue
        approval_issue = await self._create_approval_issue(step, state, risk_assessment)

        # Emit PAUSE_WORKFLOW event (instead of direct mutation)
        await self._emit_event(
            workflow_id=state.workflow_id,
            action=WorkflowAction.PAUSE_WORKFLOW,
            step_id=step.id,
            data={
                "reason": "awaiting_approval",
                "approval_issue_id": approval_issue["id"],
                "risk_assessment": risk_assessment,
            },
        )

        # Update state from events
        state_dict = await self._reconstruct_state_from_events(state.workflow_id)
        state.status = WorkflowStatus(state_dict.get("status", "paused"))

        return {
            "approval_status": "pending",
            "approval_issue_id": approval_issue["id"],
            "risk_assessment": risk_assessment,
        }

    async def _execute_conditional(
        self,
        step: WorkflowStep,
        state: WorkflowState,
    ) -> Dict[str, Any]:
        """Execute conditional branching step."""

        condition = self._render_template({"condition": step.condition}, state)[
            "condition"
        ]

        # Evaluate condition (simple Python eval for now)
        # TODO: Use safe expression evaluator
        result = eval(condition, {"outputs": state.outputs, "context": state.context})

        return {
            "condition": condition,
            "result": result,
        }

    async def _execute_notification(
        self,
        step: WorkflowStep,
        state: WorkflowState,
    ) -> Dict[str, Any]:
        """Execute notification step."""

        rendered_payload = self._render_template(step.payload, state)

        # TODO: Send notifications via Linear, email, Slack
        # For now, just log
        print(f"Notification: {rendered_payload}")

        return {
            "notification_sent": True,
            "payload": rendered_payload,
        }

    async def _determine_next_step(
        self,
        step: WorkflowStep,
        step_output: Dict[str, Any],
        state: WorkflowState,
    ) -> Optional[str]:
        """Determine the next step to execute based on current step output."""

        # Handle decision gates
        if step.decision_gate:
            return await self._evaluate_decision_gate(step, step_output, state)

        # Handle HITL approval routing
        if step.type == StepType.HITL_APPROVAL:
            if step_output.get("approval_status") == "auto_approved":
                return step.on_approved or step.on_success
            elif step_output.get("approval_status") == "pending":
                return None  # Workflow paused

        # Handle conditional routing
        if step.type == StepType.CONDITIONAL:
            if step_output.get("result"):
                return step.on_true
            else:
                return step.on_false

        # Default: follow on_success
        return step.on_success

    @traceable(name="workflow_decision_gate", tags=["workflow", "decision", "routing"])
    async def _evaluate_decision_gate(
        self,
        step: WorkflowStep,
        step_output: Dict[str, Any],
        state: WorkflowState,
    ) -> Optional[str]:
        """Evaluate LLM or deterministic decision gate."""

        gate = step.decision_gate
        if not gate:
            return step.on_success

        gate_type = DecisionGateType(gate["type"])

        if gate_type == DecisionGateType.LLM_ASSESSMENT:
            # Render prompt with current state
            prompt = self._render_template({"prompt": gate["prompt"]}, state)["prompt"]

            # Call LLM for decision
            decision = await self._call_llm_decision(prompt)

            # Route based on decision
            decision_key = decision.get("decision")
            if decision_key:
                return gate.get(f"on_{decision_key}")

            return step.on_success

        elif gate_type == DecisionGateType.DETERMINISTIC_CHECK:
            # Evaluate condition
            condition = self._render_template({"condition": gate["condition"]}, state)[
                "condition"
            ]
            result = eval(
                condition, {"outputs": state.outputs, "context": state.context}
            )

            if result:
                return gate.get("on_success")
            else:
                return gate.get("on_failure")

        return step.on_success

    @traceable(name="workflow_risk_assessment", tags=["workflow", "risk", "hitl"])
    async def _evaluate_risk_assessment(
        self,
        step: WorkflowStep,
        state: WorkflowState,
    ) -> Dict[str, Any]:
        """Evaluate risk assessment for HITL approval."""

        if not step.risk_assessment:
            return {"risk_level": "low", "approver_role": "none"}

        risk_config = step.risk_assessment

        # Check if using previous step's assessment
        if risk_config.get("use_previous"):
            prev_step_id = risk_config["use_previous"]
            return state.outputs[prev_step_id].get("risk_assessment", {})

        # Check for override
        if risk_config.get("type") == "override":
            return {
                "risk_level": risk_config.get("risk_level"),
                "approver_role": risk_config.get("approver_role"),
            }

        # LLM-based risk assessment
        prompt = self._render_template({"prompt": risk_config["prompt"]}, state)[
            "prompt"
        ]
        return await self._call_llm_decision(prompt)

    async def _call_llm_decision(self, prompt: str) -> Dict[str, Any]:
        """Call LLM for decision making (JSON response expected)."""

        if not self.gradient_client:
            # Fallback to mock if no LLM available
            return {
                "decision": "proceed",
                "reasoning": "No LLM configured, auto-proceeding",
                "risk_level": "low",
                "approver_role": "none",
            }

        try:
            # Call LLM with structured output request
            system_prompt = "You are a workflow decision engine. Analyze the provided context and respond with a JSON decision."

            response = await self.gradient_client.ainvoke(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=500,
            )

            # Parse JSON from response
            import json
            import re

            # Extract JSON from response (may be wrapped in markdown)
            json_match = re.search(r"\{[^}]+\}", response.content, re.DOTALL)
            if json_match:
                decision_data = json.loads(json_match.group())
                return decision_data

            # Fallback if no valid JSON found
            return {
                "decision": "proceed",
                "reasoning": "LLM response not parseable, defaulting to proceed",
                "raw_response": response.content,
            }

        except Exception as e:
            # Error fallback
            return {
                "decision": "block",
                "reasoning": f"LLM decision failed: {str(e)}",
                "error": str(e),
            }

    def _render_template(
        self,
        template_dict: Dict[str, Any],
        state: WorkflowState,
    ) -> Dict[str, Any]:
        """
        Render Jinja2-style templates in dictionary values.

        Supports: {{ context.key }}, {{ outputs.step_id.key }}
        """
        result = {}

        for key, value in template_dict.items():
            if isinstance(value, str) and "{{" in value:
                template = Template(value)
                result[key] = template.render(
                    context=state.context,
                    outputs=state.outputs,
                    workflow={
                        "failed_step": state.failed_step,
                        "error_message": state.error_message,
                    },
                )
            elif isinstance(value, dict):
                result[key] = self._render_template(value, state)
            else:
                result[key] = value

        return result

    async def _acquire_lock(self, lock_name: str, state: WorkflowState):
        """Acquire resource lock to prevent concurrent operations using PostgreSQL advisory locks."""

        if not self.state_client:
            # No state client, just track locally
            state.resource_locks.append(lock_name)
            return

        try:
            # Use PostgreSQL advisory locks
            # Convert lock_name to integer hash for pg_advisory_lock
            import hashlib

            lock_id = int(hashlib.md5(lock_name.encode()).hexdigest()[:8], 16)

            # Acquire lock (blocks until available)
            await self.state_client.execute(
                "SELECT pg_advisory_lock($1)",
                lock_id,
            )

            state.resource_locks.append(lock_name)

        except Exception as e:
            # Fallback to local tracking if DB fails
            state.resource_locks.append(lock_name)

    async def _release_lock(self, lock_name: str, state: WorkflowState):
        """Release resource lock."""

        if lock_name not in state.resource_locks:
            return

        if not self.state_client:
            # No state client, just remove from local tracking
            state.resource_locks.remove(lock_name)
            return

        try:
            # Release PostgreSQL advisory lock
            import hashlib

            lock_id = int(hashlib.md5(lock_name.encode()).hexdigest()[:8], 16)

            await self.state_client.execute(
                "SELECT pg_advisory_unlock($1)",
                lock_id,
            )

            state.resource_locks.remove(lock_name)

        except Exception as e:
            # Fallback to local removal if DB fails
            state.resource_locks.remove(lock_name)

    async def _create_approval_issue(
        self,
        step: WorkflowStep,
        state: WorkflowState,
        risk_assessment: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create Linear issue for HITL approval."""

        try:
            import os

            from lib.linear_workspace_client import LinearWorkspaceClient

            linear_client = LinearWorkspaceClient(
                api_key=os.getenv("LINEAR_API_KEY"),
                team_id=os.getenv(
                    "LINEAR_TEAM_ID", "f5b610be-ac34-4983-918b-2c9d00aa9b7a"
                ),
            )

            # Render approval payload if provided
            approval_payload = step.risk_assessment.get("approval_payload", {})
            rendered_approval = (
                self._render_template(approval_payload, state)
                if approval_payload
                else {}
            )

            # Build issue description
            description = f"""# Workflow Approval Required

**Workflow**: {state.definition.name}
**Workflow ID**: {state.workflow_id}
**Step**: {step.id}
**Risk Level**: {risk_assessment.get('risk_level', 'unknown')}

## Risk Assessment
{risk_assessment.get('reasoning', 'No reasoning provided')}

## Approval Details
{self._format_approval_details(rendered_approval)}

## Actions
- **Approve**: Resume workflow with approved decision
- **Reject**: Terminate workflow

**Resume Endpoint**: `POST http://45.55.173.72:8001/workflow/resume/{state.workflow_id}`
"""

            # Create Linear issue
            issue = await linear_client.create_issue(
                title=f"[WORKFLOW] Approval Required: {state.definition.name}",
                description=description,
                priority=2 if risk_assessment.get("risk_level") == "high" else 3,
                state_name="todo",
                parent_issue_id=os.getenv(
                    "LINEAR_HITL_PARENT_ISSUE", "DEV-68"
                ),  # HITL hub
            )

            return {
                "id": issue.get("identifier", "UNKNOWN"),
                "url": issue.get("url", "https://linear.app/dev-ops"),
                "uuid": issue.get("id"),
            }

        except Exception as e:
            # Fallback if Linear API fails
            return {
                "id": "MANUAL-APPROVAL",
                "url": "https://linear.app/dev-ops",
                "error": str(e),
                "note": "Manual approval required - Linear API unavailable",
            }

    async def _handle_error(
        self,
        state: WorkflowState,
        step: WorkflowStep,
        error: Exception,
    ) -> Optional[Dict[str, Any]]:
        """
        Handle workflow errors with tiered recovery system.

        Uses ErrorRecoveryEngine for intelligent tiered recovery:
        - Tier 0: Instant heuristic triage (<10ms, 0 tokens)
        - Tier 1: Automatic remediation (<5s, 0 tokens)
        - Tier 2: RAG-assisted recovery (<30s, ~50 tokens)
        - Tier 3: Agent-assisted diagnosis (<2min, ~500 tokens)
        - Tier 4: Human-in-the-loop escalation (async)

        Falls back to legacy dependency handler for backward compatibility.

        Returns:
            Dict with remediation result if handled, None otherwise
        """
        import traceback

        tb_str = traceback.format_exc()

        # Try tiered recovery first (CHEF-Error-Handling)
        if self.error_recovery_engine:
            logger.info(
                f"[WorkflowEngine] Using tiered recovery for error in step '{step.id}': "
                f"{type(error).__name__}"
            )

            # Create a retry operation that re-executes the step
            async def retry_step_operation():
                return await self._execute_step(step, state)

            try:
                outcome = await self.error_recovery_engine.recover(
                    exception=error,
                    workflow_id=state.workflow_id,
                    step_id=step.id,
                    agent_name=step.agent,
                    operation=retry_step_operation,
                    context={"traceback": tb_str[:2000], "step_payload": step.payload},
                    max_tier=RecoveryTier.TIER_3,  # Don't auto-escalate to HITL here
                )

                if outcome.success:
                    logger.info(
                        f"[WorkflowEngine] Tiered recovery succeeded at Tier {outcome.final_tier.value} "
                        f"for step '{step.id}'"
                    )

                    # Emit recovery success event
                    await self._emit_event(
                        workflow_id=state.workflow_id,
                        action=WorkflowAction.COMPLETE_STEP,  # Step recovered
                        step_id=step.id,
                        data={
                            "recovery_tier": outcome.final_tier.value,
                            "recovery_result": outcome.result.value,
                            "recovery_metrics": outcome.metrics,
                        },
                    )

                    return {
                        "recovered": True,
                        "tier": outcome.final_tier.value,
                        "result": outcome.result.value,
                        "metrics": outcome.metrics,
                    }
                else:
                    logger.warning(
                        f"[WorkflowEngine] Tiered recovery failed for step '{step.id}'. "
                        f"Final tier: {outcome.final_tier.value}, Result: {outcome.result.value}"
                    )

                    # If we exhausted all tiers up to TIER_3, escalate to HITL
                    if outcome.final_tier == RecoveryTier.TIER_3:
                        logger.info(
                            f"[WorkflowEngine] Escalating to HITL (Tier 4) for step '{step.id}'"
                        )
                        if self.linear_client:
                            await self._create_escalation_issue(
                                state, step, error, tb_str
                            )
                        return {
                            "escalated": True,
                            "reason": str(error),
                            "recovery_tier": outcome.final_tier.value,
                        }

            except Exception as recovery_error:
                logger.error(
                    f"[WorkflowEngine] Error recovery engine failed: {recovery_error}. "
                    f"Falling back to legacy handler."
                )

        # Legacy: Check for dependency errors (ModuleNotFoundError, ImportError)
        if isinstance(error, (ModuleNotFoundError, ImportError)):
            logger.warning(
                f"Dependency error in step '{step.id}': {error}. "
                f"Attempting auto-remediation..."
            )

            # Parse the error
            dep_error = self.dependency_handler.parse_error(
                exception=error,
                traceback_file=step.id,
                traceback_str=tb_str,
            )

            if dep_error:
                # Get workspace context from state
                workspace_path = state.context.get("workspace_path")
                docker_context = state.context.get("docker_context")

                # Create remediation plan
                plan = self.dependency_handler.create_remediation_plan(
                    error=dep_error,
                    workspace_path=workspace_path,
                    docker_context=docker_context,
                )

                # Execute remediation
                result, error_msg = await self.dependency_handler.execute_remediation(
                    plan
                )

                # Emit event for dependency remediation
                await self._emit_event(
                    workflow_id=state.workflow_id,
                    action=WorkflowAction.FAIL_STEP,  # Using FAIL_STEP with remediation data
                    step_id=step.id,
                    data={
                        "error": str(error),
                        "error_type": "DependencyError",
                        "remediation_attempted": True,
                        "remediation_strategy": plan.strategy.value,
                        "remediation_result": result.value,
                        "remediation_error": error_msg,
                        "module_name": dep_error.module_name,
                        "package_name": dep_error.package_name,
                    },
                )

                if result == DependencyRemediationResult.SUCCESS:
                    logger.info(
                        f"Successfully remediated dependency '{dep_error.module_name}'. "
                        f"Step may be retried."
                    )
                    return {
                        "remediated": True,
                        "module": dep_error.module_name,
                        "strategy": plan.strategy.value,
                        "should_retry": True,
                    }
                elif result == DependencyRemediationResult.ESCALATED:
                    logger.warning(
                        f"Dependency '{dep_error.module_name}' escalated to Linear. "
                        f"Manual intervention required."
                    )
                    return {
                        "remediated": False,
                        "escalated": True,
                        "module": dep_error.module_name,
                        "reason": plan.escalation_reason,
                    }
                else:
                    logger.error(
                        f"Failed to remediate dependency '{dep_error.module_name}': {error_msg}"
                    )

        # Check workflow.error_handling for custom handlers
        for handler in state.definition.error_handling:
            error_type = handler.get("error_type", "*")
            if error_type == "*" or error_type == type(error).__name__:
                action = handler.get("action", "fail")

                if action == "retry":
                    max_retries = handler.get("max_retries", 3)
                    # Retry logic would be implemented here
                    logger.info(f"Retry action configured for {error_type}")

                elif action == "skip":
                    logger.info(f"Skipping step '{step.id}' due to error handler")
                    return {"skipped": True, "reason": str(error)}

                elif action == "escalate":
                    # Create Linear issue for manual intervention
                    if self.linear_client:
                        await self._create_escalation_issue(state, step, error, tb_str)
                    return {"escalated": True, "reason": str(error)}

        return None

    async def _create_escalation_issue(
        self,
        state: WorkflowState,
        step: WorkflowStep,
        error: Exception,
        traceback_str: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a Linear issue for error escalation.

        Args:
            state: Current workflow state
            step: The step that failed
            error: The exception that occurred
            traceback_str: Full traceback for debugging

        Returns:
            Linear issue dict if created, None otherwise
        """
        if not self.linear_client:
            logger.warning("No Linear client available for escalation")
            return None

        try:
            title = (
                f"[Workflow Error] {state.definition.name} - Step '{step.id}' failed"
            )

            description = (
                f"## Workflow Error Escalation\n\n"
                f"**Workflow:** {state.definition.name} (v{state.definition.version})\n"
                f"**Workflow ID:** `{state.workflow_id}`\n"
                f"**Failed Step:** `{step.id}` ({step.type.value})\n"
                f"**Agent:** {step.agent or 'N/A'}\n"
                f"**Error Type:** `{type(error).__name__}`\n\n"
                f"### Error Message\n```\n{str(error)}\n```\n\n"
                f"### Context\n```json\n{state.context}\n```\n\n"
                f"### Traceback\n```\n{traceback_str[:2000]}\n```\n"
            )

            issue = await self.linear_client.create_issue(
                title=title,
                description=description,
                labels=["workflow-error", "auto-escalated"],
                priority=2,  # Medium priority
            )

            logger.info(f"Created escalation issue: {issue.get('id')}")
            return issue

        except Exception as e:
            logger.error(f"Failed to create escalation issue: {e}")
            return None

    def _build_agent_prompt(self, agent_name: str, payload: Dict[str, Any]) -> str:
        """Build agent-specific prompt from workflow payload."""

        # Extract relevant fields from payload
        prompt_parts = [f"Execute {agent_name} agent task:"]

        for key, value in payload.items():
            if value and key not in ["agent", "type"]:
                prompt_parts.append(f"- {key}: {value}")

        return "\n".join(prompt_parts)

    def _format_approval_details(self, details: Dict[str, Any]) -> str:
        """Format approval details for Linear issue description."""

        if not details:
            return "No additional details provided."

        lines = []
        for key, value in details.items():
            # Format key as title case
            formatted_key = key.replace("_", " ").title()
            lines.append(f"- **{formatted_key}**: {value}")

        return "\n".join(lines)

    def _get_step_by_id(
        self, definition: WorkflowDefinition, step_id: str
    ) -> WorkflowStep:
        """Get step by ID from workflow definition."""
        for step in definition.steps:
            if step.id == step_id:
                return step
        raise ValueError(f"Step not found: {step_id}")

    @traceable(name="workflow_resume", tags=["workflow", "hitl", "resume"])
    async def resume_workflow(
        self,
        workflow_id: str,
        approval_decision: str,  # "approved" or "rejected"
        approver: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> WorkflowState:
        """
        Resume a paused workflow after HITL approval using event sourcing.

        Args:
            workflow_id: Workflow to resume
            approval_decision: "approved" or "rejected"
            approver: User who approved/rejected
            comment: Approval/rejection comment

        Returns:
            WorkflowState: Updated workflow state
        """
        # Reconstruct state from events
        state_dict = await self._reconstruct_state_from_events(workflow_id)

        if state_dict.get("status") != "paused":
            raise ValueError(
                f"Workflow {workflow_id} is not paused (status: {state_dict.get('status')})"
            )

        # Get workflow definition
        template_name = state_dict.get("template_name")
        definition = self.load_workflow(template_name)

        # Convert to WorkflowState for execution
        state = WorkflowState(
            workflow_id=workflow_id,
            definition=definition,
            status=WorkflowStatus.PAUSED,
            context=state_dict.get("context", {}),
            outputs=state_dict.get("outputs", {}),
            current_step=state_dict.get("current_step"),
        )

        # Get current step (should be HITL approval)
        step = self._get_step_by_id(state.definition, state.current_step)

        # Emit approval or rejection event
        if approval_decision == "approved":
            await self._emit_event(
                workflow_id=workflow_id,
                action=WorkflowAction.APPROVE_GATE,
                step_id=step.id,
                data={
                    "approver": approver or "unknown",
                    "approver_role": "manual",
                    "comment": comment,
                },
            )
            next_step_id = step.on_approved or step.on_success
        else:
            await self._emit_event(
                workflow_id=workflow_id,
                action=WorkflowAction.REJECT_GATE,
                step_id=step.id,
                data={
                    "rejector": approver or "unknown",
                    "rejector_role": "manual",
                    "reason": comment,
                },
            )
            next_step_id = step.on_rejected or step.on_failure

        # Emit RESUME_WORKFLOW event
        await self._emit_event(
            workflow_id=workflow_id,
            action=WorkflowAction.RESUME_WORKFLOW,
            step_id=step.id,
            data={"decision": approval_decision},
        )

        # Reconstruct state to get updated status
        state_dict = await self._reconstruct_state_from_events(workflow_id)
        state.status = WorkflowStatus(state_dict.get("status", "running"))

        # Continue from next step
        while next_step_id and next_step_id != "workflow_complete":
            step = self._get_step_by_id(state.definition, next_step_id)

            step_output = await self._execute_step(step, state)

            # Emit COMPLETE_STEP event
            await self._emit_event(
                workflow_id=workflow_id,
                action=WorkflowAction.COMPLETE_STEP,
                step_id=next_step_id,
                data={
                    "result": step_output,
                    "next_step": await self._determine_next_step(
                        step, step_output, state
                    ),
                },
            )

            # Reconstruct state
            state_dict = await self._reconstruct_state_from_events(workflow_id)
            state.outputs = state_dict.get("outputs", {})
            state.status = WorkflowStatus(state_dict.get("status", "running"))

            next_step_id = await self._determine_next_step(step, step_output, state)

            # Check for another pause
            if state.status == WorkflowStatus.PAUSED:
                return state

            # Create snapshot if needed
            if await self._should_create_snapshot(workflow_id):
                await self._create_snapshot(workflow_id, state_dict)

        # Workflow completed - state already updated via events
        return state

    async def get_workflow_status(self, workflow_id: str) -> WorkflowState:
        """Get current status of a workflow."""
        return await self.state_client.load_workflow_state(workflow_id)

    async def cancel_workflow(
        self,
        workflow_id: str,
        reason: str,
        cancelled_by: str = "unknown",
    ) -> Dict[str, Any]:
        """Cancel a running or paused workflow with cleanup.

        Cleanup includes:
        1. Release all resource locks
        2. Mark Linear approval issues as complete
        3. Notify participating agents
        4. Cascade to child workflows

        Args:
            workflow_id: Workflow to cancel
            reason: Cancellation reason
            cancelled_by: User who cancelled

        Returns:
            Cancellation summary
        """

        # Reconstruct state from events
        state_dict = await self._reconstruct_state_from_events(workflow_id)

        if state_dict.get("status") in ["completed", "failed", "cancelled"]:
            raise ValueError(
                f"Cannot cancel workflow {workflow_id} with status {state_dict.get('status')}"
            )

        # Emit CANCEL_WORKFLOW event
        await self._emit_event(
            workflow_id=workflow_id,
            action=WorkflowAction.CANCEL_WORKFLOW,
            step_id=state_dict.get("current_step"),
            data={
                "reason": reason,
                "cancelled_by": cancelled_by,
            },
        )

        # Cleanup: Release resource locks
        resource_locks = state_dict.get("resource_locks", [])
        for lock_name in resource_locks:
            try:
                import hashlib

                lock_id = int(hashlib.md5(lock_name.encode()).hexdigest()[:8], 16)
                await self.state_client.execute(
                    "SELECT pg_advisory_unlock($1)",
                    lock_id,
                )
            except Exception as e:
                print(f"Warning: Failed to release lock {lock_name}: {e}")

        # Cleanup: Mark Linear approval issues complete
        try:
            import os

            from lib.linear_workspace_client import LinearWorkspaceClient

            linear_client = LinearWorkspaceClient(
                api_key=os.getenv("LINEAR_API_KEY"),
                team_id=os.getenv(
                    "LINEAR_TEAM_ID", "f5b610be-ac34-4983-918b-2c9d00aa9b7a"
                ),
            )

            # Find approval issues for this workflow (stored in event data)
            events = await self._load_events(workflow_id)
            approval_issues = []
            for event in events:
                if event.action == WorkflowAction.PAUSE_WORKFLOW:
                    issue_id = event.data.get("approval_issue_id")
                    if issue_id:
                        approval_issues.append(issue_id)

            # Mark issues as cancelled
            for issue_id in approval_issues:
                try:
                    await linear_client.update_issue(
                        issue_identifier=issue_id,
                        state_name="cancelled",
                        comment=f"Workflow {workflow_id} cancelled: {reason}",
                    )
                except Exception as e:
                    print(f"Warning: Failed to update Linear issue {issue_id}: {e}")

        except Exception as e:
            print(f"Warning: Failed to cleanup Linear issues: {e}")

        # Cleanup: Notify participating agents (emit notification events)
        participating_agents = state_dict.get("participating_agents", [])
        for agent_name in participating_agents:
            # Could send notifications via Linear, email, etc.
            print(f"Notifying agent {agent_name} of workflow cancellation")

        # Cleanup: Cancel child workflows
        child_workflows = state_dict.get("child_workflows", [])
        for child in child_workflows:
            if child.get("status") == "running":
                try:
                    await self.cancel_workflow(
                        workflow_id=child["child_workflow_id"],
                        reason=f"Parent workflow {workflow_id} cancelled",
                        cancelled_by=cancelled_by,
                    )
                except Exception as e:
                    print(
                        f"Warning: Failed to cancel child workflow {child['child_workflow_id']}: {e}"
                    )

        return {
            "workflow_id": workflow_id,
            "status": "cancelled",
            "reason": reason,
            "cancelled_by": cancelled_by,
            "cleanup": {
                "locks_released": len(resource_locks),
                "linear_issues_closed": (
                    len(approval_issues) if "approval_issues" in locals() else 0
                ),
                "agents_notified": len(participating_agents),
                "child_workflows_cancelled": len(
                    [c for c in child_workflows if c.get("status") == "running"]
                ),
            },
        }

    # ========================================================================
    # EVENT SOURCING METHODS (Week 4)
    # ========================================================================

    async def _emit_event(
        self,
        workflow_id: str,
        action: WorkflowAction,
        step_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> WorkflowEvent:
        """Emit workflow event and persist to database.

        All state transitions MUST go through this method to ensure
        events are the single source of truth.

        Args:
            workflow_id: Workflow this event belongs to
            action: Type of state transition
            step_id: Step this event relates to (optional)
            data: Event-specific data

        Returns:
            WorkflowEvent: Persisted event
        """

        # Create event
        event = WorkflowEvent(
            workflow_id=workflow_id,
            action=action,
            step_id=step_id,
            data=data or {},
        )

        # Sign event for tamper detection
        secret_key = os.getenv(
            "WORKFLOW_EVENT_SECRET_KEY", "default-secret-key-change-me"
        )
        event_dict = event.to_dict()
        signature = sign_event(event_dict, secret_key)

        # Create signed event
        signed_event = WorkflowEvent(**{**event_dict, "signature": signature})

        # Persist event to database
        if self.state_client:
            await self._persist_event(signed_event)

        return signed_event

    async def _persist_event(self, event: WorkflowEvent) -> None:
        """Persist event to workflow_events table and refresh workflow TTL.

        Task 5.3: Active workflows refresh TTL on every event (stay alive),
        abandoned workflows auto-expire after WORKFLOW_TTL_HOURS.

        Args:
            event: Event to persist
        """

        if not self.state_client:
            return

        try:
            # Serialize event data to JSON
            event_dict = event.to_dict()

            # Insert into workflow_events table
            await self.state_client.execute(
                """
                INSERT INTO workflow_events 
                (event_id, workflow_id, action, step_id, data, timestamp, signature, event_version)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                event_dict["event_id"],
                event_dict["workflow_id"],
                event_dict["action"],
                event_dict.get("step_id"),
                event_dict.get("data", {}),
                event_dict["timestamp"],
                event_dict.get("signature"),
                event_dict.get("event_version", 2),
            )

            # Task 5.3: Refresh workflow TTL (ZEN PATTERN)
            # Active workflows stay alive, abandoned workflows expire
            await self._refresh_workflow_ttl(event_dict["workflow_id"])

        except Exception as e:
            # Log error but don't fail workflow execution
            logger.warning(f"Failed to persist event: {e}")

    async def _refresh_workflow_ttl(self, workflow_id: str) -> None:
        """Refresh workflow TTL to prevent expiration of active workflows.

        This implements the Zen MCP Server pattern: active conversations refresh
        TTL on every turn, while abandoned conversations auto-expire.

        Args:
            workflow_id: Workflow to refresh TTL for

        Task: 5.3 - Workflow TTL Management (Week 5 Zen Pattern Integration)
        """
        if not self.state_client:
            return

        try:
            # PostgreSQL implementation: Update expiration timestamp
            expiration = datetime.utcnow() + timedelta(seconds=self.ttl_seconds)

            await self.state_client.execute(
                """
                INSERT INTO workflow_ttl (workflow_id, expires_at, refreshed_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (workflow_id) 
                DO UPDATE SET 
                    expires_at = $2,
                    refreshed_at = NOW(),
                    refresh_count = workflow_ttl.refresh_count + 1
                """,
                workflow_id,
                expiration,
            )

            logger.debug(
                f"Refreshed TTL for workflow {workflow_id}: {self.WORKFLOW_TTL_HOURS}h"
            )

        except Exception as e:
            # Non-critical: TTL refresh failure doesn't fail event persistence
            logger.warning(f"Failed to refresh TTL for {workflow_id}: {e}")

    async def _load_events(self, workflow_id: str) -> List[WorkflowEvent]:
        """Load all events for a workflow.

        Args:
            workflow_id: Workflow to load events for

        Returns:
            List of WorkflowEvent instances
        """

        if not self.state_client:
            return []

        try:
            # Query events from database
            rows = await self.state_client.fetch(
                """
                SELECT event_id, workflow_id, action, step_id, data, timestamp, signature, event_version
                FROM workflow_events
                WHERE workflow_id = $1
                ORDER BY timestamp ASC
                """,
                workflow_id,
            )

            # Convert rows to WorkflowEvent instances
            events = []
            for row in rows:
                event = WorkflowEvent(
                    event_id=row["event_id"],
                    workflow_id=row["workflow_id"],
                    action=WorkflowAction(row["action"]),
                    step_id=row.get("step_id"),
                    data=row.get("data", {}),
                    timestamp=(
                        row["timestamp"].isoformat()
                        if hasattr(row["timestamp"], "isoformat")
                        else row["timestamp"]
                    ),
                    signature=row.get("signature"),
                    event_version=row.get("event_version", 2),
                )
                events.append(event)

            return events

        except Exception as e:
            print(f"Warning: Failed to load events: {e}")
            return []

    async def _reconstruct_state_from_events(self, workflow_id: str) -> Dict[str, Any]:
        """Reconstruct workflow state by replaying all events.

        This is the core of event sourcing: state is derived from events,
        not stored directly.

        Args:
            workflow_id: Workflow to reconstruct

        Returns:
            Reconstructed state dictionary
        """

        # Load all events
        events = await self._load_events(workflow_id)

        # Replay events through reducer
        if events:
            state = replay_workflow(events)
            return state

        return {"status": "not_found"}

    def _deduplicate_workflow_resources(
        self, events: List[WorkflowEvent]
    ) -> Dict[str, Any]:
        """Deduplicate workflow resources by keeping only newest versions.

        Walks events backwards (newest first) to find latest version of each resource.
        This prevents stale data in workflow context when files are modified multiple times.

        Inspired by Zen MCP Server's conversation threading pattern with "newest-first"
        file prioritization from 1000+ production conversations.

        Example:
            Infrastructure workflow modifies docker-compose.yml 5 times:
            - Event 1: Add nginx service
            - Event 2: Add postgres service
            - Event 3: Update nginx ports
            - Event 4: Add redis service
            - Event 5: Update postgres environment

            Result: Only version 5 included in context (80% token reduction)

        Args:
            events: List of workflow events (any order)

        Returns:
            Dict mapping resource_id → newest resource data

        Performance:
            - Time complexity: O(n) where n = number of events
            - Typical overhead: <10ms for 10-50 event workflows
            - Token savings: 80-90% when resources modified multiple times

        Task: 5.2 - Resource Deduplication (Week 5 Zen Pattern Integration)
        """
        seen_resources = {}

        # Walk events backwards (newest first) - ZEN PATTERN
        # This ensures the most recent version of each resource is prioritized
        for event in reversed(events):
            resources = event.data.get("resources", {})

            for resource_id, resource_data in resources.items():
                if resource_id not in seen_resources:
                    # First occurrence (newest) wins
                    seen_resources[resource_id] = resource_data
                    logger.debug(
                        f"Resource deduplicated: {resource_id} from event {event.event_id}"
                    )

        return seen_resources

    async def build_workflow_context(self, workflow_id: str) -> Dict[str, Any]:
        """Build workflow execution context with deduplicated resources.

        This method combines workflow state reconstruction with resource deduplication
        to provide agents with clean, non-redundant context.

        Use Cases:
        1. Infrastructure workflow modifies docker-compose.yml multiple times
        2. Code review workflow analyzes same file across multiple commits
        3. Multi-step deployments update configuration files repeatedly

        Args:
            workflow_id: Workflow to build context for

        Returns:
            Context dictionary with:
            - workflow_id: Workflow identifier
            - status: Current workflow status
            - events: All workflow events (for audit trail)
            - resources: Deduplicated resources (newest versions only)
            - outputs: Step outputs
            - metadata: Workflow metadata

        Performance:
            - Token savings: 80-90% when resources modified multiple times
            - Overhead: <10ms for typical workflows (10-50 events)

        Task: 5.2 - Resource Deduplication (Week 5 Zen Pattern Integration)
        """
        # Load all events
        events = await self._load_events(workflow_id)

        # Reconstruct state from events
        state = replay_workflow(events) if events else {"status": "not_found"}

        # Deduplicate resources (Task 5.2)
        deduplicated_resources = self._deduplicate_workflow_resources(events)

        # Log deduplication savings
        total_resource_references = sum(
            len(event.data.get("resources", {})) for event in events
        )
        deduplicated_count = len(deduplicated_resources)
        if total_resource_references > 0:
            savings_percent = (
                (total_resource_references - deduplicated_count)
                / total_resource_references
            ) * 100
            logger.info(
                f"Resource dedup: {total_resource_references} → {deduplicated_count} "
                f"({savings_percent:.1f}% reduction)"
            )

        # Build context
        context = {
            "workflow_id": workflow_id,
            "status": state.get("status"),
            "events": [e.to_dict() for e in events],
            "resources": deduplicated_resources,  # Only newest versions
            "outputs": state.get("outputs", {}),
            "metadata": {
                "template_name": state.get("template_name"),
                "started_at": state.get("started_at"),
                "current_step": state.get("current_step"),
                "steps_completed": state.get("steps_completed", []),
            },
        }

        return context

    async def _create_snapshot(self, workflow_id: str, state: Dict[str, Any]) -> None:
        """Create state snapshot for performance optimization.

        Snapshots enable fast state reconstruction: snapshot + delta events
        instead of replaying all events.

        Args:
            workflow_id: Workflow to snapshot
            state: Current state to snapshot
        """

        if not self.state_client:
            return

        try:
            # Count events for this workflow
            event_count = await self.state_client.fetchval(
                "SELECT COUNT(*) FROM workflow_events WHERE workflow_id = $1",
                workflow_id,
            )

            # Create snapshot
            snapshot_id = str(uuid.uuid4())
            await self.state_client.execute(
                """
                INSERT INTO workflow_snapshots (snapshot_id, workflow_id, state, event_count)
                VALUES ($1, $2, $3, $4)
                """,
                snapshot_id,
                workflow_id,
                state,
                event_count,
            )

            # Emit snapshot event
            await self._emit_event(
                workflow_id=workflow_id,
                action=WorkflowAction.CREATE_SNAPSHOT,
                data={"snapshot_id": snapshot_id, "event_count": event_count},
            )

        except Exception as e:
            print(f"Warning: Failed to create snapshot: {e}")

    async def _should_create_snapshot(self, workflow_id: str) -> bool:
        """Check if snapshot should be created (every 10 events).

        Args:
            workflow_id: Workflow to check

        Returns:
            True if snapshot should be created
        """

        if not self.state_client:
            return False

        try:
            # Get event count since last snapshot
            event_count = await self.state_client.fetchval(
                """
                SELECT COUNT(*) FROM workflow_events e
                WHERE e.workflow_id = $1
                AND e.timestamp > COALESCE(
                    (SELECT MAX(created_at) FROM workflow_snapshots WHERE workflow_id = $1),
                    '1970-01-01'::timestamptz
                )
                """,
                workflow_id,
            )

            # Create snapshot every 10 events
            return event_count >= 10

        except Exception as e:
            return False
