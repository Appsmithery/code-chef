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

        # TODO: Call agent via graph.py or delegation.py
        # For now, return mock response
        agent_output = {
            "agent": step.agent,
            "status": "success",
            "payload": rendered_payload,
            # Agent-specific outputs would go here
        }

        return agent_output

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
        
        gate_type = DecisionGateType(gate["type"])        if gate_type == DecisionGateType.LLM_ASSESSMENT:
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

        # TODO: Integrate with gradient_client for actual LLM calls
        # For now, return mock decision
        return {
            "decision": "proceed",
            "reasoning": "All checks passed",
            "risk_level": "low",
            "approver_role": "none",
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
        """Acquire resource lock to prevent concurrent operations."""
        # TODO: Implement distributed locking with PostgreSQL
        state.resource_locks.append(lock_name)

    async def _release_lock(self, lock_name: str, state: WorkflowState):
        """Release resource lock."""
        # TODO: Implement distributed locking with PostgreSQL
        if lock_name in state.resource_locks:
            state.resource_locks.remove(lock_name)

    async def _create_approval_issue(
        self,
        step: WorkflowStep,
        state: WorkflowState,
        risk_assessment: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create Linear issue for HITL approval."""
        # TODO: Integrate with Linear API
        return {
            "id": "DEV-999",
            "url": "https://linear.app/dev-ops/issue/DEV-999",
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
