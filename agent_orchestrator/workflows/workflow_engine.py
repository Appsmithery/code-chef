"""
Workflow Engine for declarative multi-agent workflows.

This module implements a workflow engine that:
1. Loads workflow YAML templates
2. Executes steps sequentially with state management
3. Handles LLM decision gates for dynamic routing
4. Integrates with LangGraph checkpointing for HITL approvals
5. Supports resource locking to prevent concurrent operations
6. Renders Jinja2-style templates for dynamic payloads

Architecture:
- Pure Python orchestration (no LangGraph for workflow logic)
- LangGraph only for HITL checkpointing
- Deterministic step execution with LLM decision gates at strategic points
"""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from jinja2 import Template
from pydantic import BaseModel, Field

from shared.lib.gradient_client import GradientClient

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

    def __init__(
        self,
        templates_dir: str = "agent_orchestrator/workflows/templates",
        gradient_client: Optional[GradientClient] = None,
        state_client: Optional[Any] = None,
    ):
        self.templates_dir = Path(templates_dir)
        self.gradient_client = gradient_client  # Will be provided by caller
        self.state_client = state_client  # Will be provided by caller

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

    async def execute_workflow(
        self,
        template_name: str,
        context: Dict[str, Any],
    ) -> WorkflowState:
        """
        Execute a workflow from start to completion.

        Args:
            template_name: Name of workflow template
            context: Initial context variables (e.g., pr_number, branch, environment)

        Returns:
            WorkflowState: Final workflow state
        """
        workflow_id = str(uuid.uuid4())
        definition = self.load_workflow(template_name)

        # Initialize workflow state
        state = WorkflowState(
            workflow_id=workflow_id,
            definition=definition,
            status=WorkflowStatus.RUNNING,
            context=context,
            step_statuses={step.id: StepStatus.PENDING for step in definition.steps},
        )

        # Persist initial state
        await self.state_client.save_workflow_state(state)

        # Execute steps sequentially
        try:
            current_step_id = definition.steps[0].id if definition.steps else None

            while current_step_id:
                step = self._get_step_by_id(definition, current_step_id)

                # Execute step
                state.current_step = current_step_id
                state.step_statuses[current_step_id] = StepStatus.RUNNING
                await self.state_client.save_workflow_state(state)

                step_output = await self._execute_step(step, state)

                # Store output
                state.outputs[current_step_id] = step_output
                state.step_statuses[current_step_id] = StepStatus.COMPLETED

                # Determine next step
                current_step_id = await self._determine_next_step(
                    step, step_output, state
                )

                # Check for HITL pause
                if state.status == WorkflowStatus.PAUSED:
                    await self.state_client.save_workflow_state(state)
                    return state

                await self.state_client.save_workflow_state(state)

            # Workflow completed
            state.status = WorkflowStatus.COMPLETED
            state.completed_at = datetime.utcnow()
            await self.state_client.save_workflow_state(state)

            return state

        except Exception as e:
            # Handle workflow failure
            state.status = WorkflowStatus.FAILED
            state.error_message = str(e)
            state.completed_at = datetime.utcnow()
            await self.state_client.save_workflow_state(state)

            # Attempt error handling
            await self._handle_error(state, step, e)

            raise

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

            return {
                "agent": step.agent,
                "status": "success",
                "response": response,
                "task_result": final_state.get("task_result", {}),
                "payload": rendered_payload,
            }

        except Exception as e:
            # Fallback to mock response if agent execution fails
            return {
                "agent": step.agent,
                "status": "error",
                "error": str(e),
                "payload": rendered_payload,
            }

    async def _execute_hitl_approval(
        self,
        step: WorkflowStep,
        state: WorkflowState,
    ) -> Dict[str, Any]:
        """Execute HITL approval step."""

        # Evaluate risk assessment
        risk_assessment = await self._evaluate_risk_assessment(step, state)

        # Check if auto-approval is possible
        if (
            risk_assessment.get("risk_level") == "low"
            and risk_assessment.get("approver_role") == "none"
        ):
            return {
                "approval_status": "auto_approved",
                "risk_assessment": risk_assessment,
            }

        # Create Linear approval issue
        approval_issue = await self._create_approval_issue(step, state, risk_assessment)

        # Pause workflow for approval
        state.status = WorkflowStatus.PAUSED

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
            from lib.linear_workspace_client import LinearWorkspaceClient
            import os

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
    ):
        """Handle workflow errors with configured error handlers."""
        # TODO: Implement error handling logic from workflow.error_handling
        pass

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

    async def resume_workflow(
        self,
        workflow_id: str,
        approval_decision: str,  # "approved" or "rejected"
    ) -> WorkflowState:
        """
        Resume a paused workflow after HITL approval.

        Args:
            workflow_id: Workflow to resume
            approval_decision: "approved" or "rejected"

        Returns:
            WorkflowState: Updated workflow state
        """
        # Load workflow state
        state = await self.state_client.load_workflow_state(workflow_id)

        if state.status != WorkflowStatus.PAUSED:
            raise ValueError(f"Workflow {workflow_id} is not paused")

        # Get current step (should be HITL approval)
        step = self._get_step_by_id(state.definition, state.current_step)

        # Determine next step based on approval decision
        if approval_decision == "approved":
            next_step_id = step.on_approved or step.on_success
        else:
            next_step_id = step.on_rejected or step.on_failure

        # Resume execution
        state.status = WorkflowStatus.RUNNING

        # Continue from next step
        while next_step_id:
            step = self._get_step_by_id(state.definition, next_step_id)

            state.current_step = next_step_id
            state.step_statuses[next_step_id] = StepStatus.RUNNING
            await self.state_client.save_workflow_state(state)

            step_output = await self._execute_step(step, state)

            state.outputs[next_step_id] = step_output
            state.step_statuses[next_step_id] = StepStatus.COMPLETED

            next_step_id = await self._determine_next_step(step, step_output, state)

            # Check for another pause
            if state.status == WorkflowStatus.PAUSED:
                await self.state_client.save_workflow_state(state)
                return state

            await self.state_client.save_workflow_state(state)

        # Workflow completed
        state.status = WorkflowStatus.COMPLETED
        state.completed_at = datetime.utcnow()
        await self.state_client.save_workflow_state(state)

        return state

    async def get_workflow_status(self, workflow_id: str) -> WorkflowState:
        """Get current status of a workflow."""
        return await self.state_client.load_workflow_state(workflow_id)
