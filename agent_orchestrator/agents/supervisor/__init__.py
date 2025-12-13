"""Supervisor agent for task routing and workflow orchestration.

The supervisor agent is the "Head Chef" of the multi-agent system:
1. Analyzes incoming tasks and decomposes them into subtasks
2. Routes subtasks to specialized agents (feature-dev, code-review, etc.)
3. Coordinates inter-agent handoffs via EventBus (Phase 6 - CHEF-110)
4. Manages workflow state and approvals

Inter-Agent Communication (Phase 6 - CHEF-110):
    The supervisor can delegate work to other agents via EventBus:

    # Delegate code review
    response = await supervisor.delegate_to_agent(
        target_agent="code-review",
        task_type=AgentRequestType.REVIEW_CODE,
        payload={"file_path": "main.py", "changes": diff}
    )

    # Broadcast workflow status
    await supervisor.broadcast_status("workflow_started", {"workflow_id": "123"})
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from langsmith import traceable

# Import agent event types for inter-agent communication
from lib.agent_events import AgentRequestPriority, AgentRequestType, AgentResponseStatus

from .._shared.base_agent import BaseAgent


class SupervisorAgent(BaseAgent):
    """Supervisor agent that routes tasks to specialized agents.

    Uses Claude 3.5 Sonnet (OpenRouter) for complex routing decisions.
    Analyzes tasks and determines which specialized agent should handle them.

    Phase 6 Features (CHEF-110):
    - Inter-agent task delegation via EventBus
    - Workflow coordination with parallel execution support
    - Status broadcasting to agent network
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        project_context: Optional[Dict[str, Any]] = None,
    ):
        """Initialize supervisor agent.

        Args:
            config_path: Path to supervisor config (defaults to tools.yaml in agent directory)
            project_context: Project context dict with project_id, repository_url, workspace_name
        """
        if config_path is None:
            config_path = str(Path(__file__).parent / "tools.yaml")

        super().__init__(
            str(config_path), agent_name="supervisor", project_context=project_context
        )

    # =========================================================================
    # INTER-AGENT DELEGATION (Phase 6 - CHEF-110)
    # =========================================================================

    @traceable(
        name="supervisor_delegate_to_agent",
        tags=["supervisor", "delegation", "inter-agent"],
    )
    async def delegate_to_agent(
        self,
        target_agent: str,
        task_type: AgentRequestType,
        payload: Dict[str, Any],
        priority: AgentRequestPriority = AgentRequestPriority.NORMAL,
        timeout: float = 60.0,
        correlation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delegate a task to a specialized agent via EventBus.

        This is the primary method for supervisor→agent communication in
        multi-agent workflows. The supervisor sends a request and waits
        for the agent's response.

        Args:
            target_agent: Name of agent to delegate to (e.g., "code-review", "feature-dev")
            task_type: Type of task from AgentRequestType enum
            payload: Task-specific data (file paths, code, context, etc.)
            priority: Request priority (affects queue ordering)
            timeout: Maximum seconds to wait for response
            correlation_id: Optional ID for grouping related requests

        Returns:
            Dict with response data:
            - status: "success", "error", "timeout", "rejected"
            - result: Agent's output (for success)
            - error: Error message (for error/timeout)
            - agent: Name of responding agent
            - processing_time_ms: Time taken

        Example:
            response = await self.delegate_to_agent(
                target_agent="code-review",
                task_type=AgentRequestType.REVIEW_CODE,
                payload={
                    "file_path": "src/main.py",
                    "changes": git_diff,
                    "focus_areas": ["security", "performance"]
                }
            )

            if response["status"] == "success":
                review_comments = response["result"]["comments"]
                security_issues = response["result"]["security_issues"]
        """
        # Use the EventBus request_agent from BaseAgent
        response = await self.request_agent(
            target_agent=target_agent,
            request_type=task_type,
            payload=payload,
            priority=priority,
            timeout=timeout,
            correlation_id=correlation_id,
        )

        return {
            "status": response.status.value,
            "result": response.result,
            "error": response.error,
            "agent": response.source_agent,
            "processing_time_ms": response.processing_time_ms,
            "request_id": response.request_id,
        }

    @traceable(
        name="supervisor_delegate_parallel",
        tags=["supervisor", "delegation", "parallel"],
    )
    async def delegate_parallel(
        self,
        tasks: List[Dict[str, Any]],
        timeout: float = 120.0,
    ) -> List[Dict[str, Any]]:
        """Delegate multiple tasks to agents in parallel.

        Useful for workflows that require parallel execution, such as:
        - Running code review + tests simultaneously
        - Generating documentation for multiple modules
        - Parallel infrastructure validation

        Args:
            tasks: List of task dicts, each with:
                - target_agent: Agent to delegate to
                - task_type: AgentRequestType value
                - payload: Task-specific data
                - priority: Optional priority (default: NORMAL)
            timeout: Maximum seconds to wait for all responses

        Returns:
            List of response dicts (same format as delegate_to_agent)

        Example:
            tasks = [
                {
                    "target_agent": "code-review",
                    "task_type": AgentRequestType.REVIEW_CODE,
                    "payload": {"file_path": "main.py"}
                },
                {
                    "target_agent": "cicd",
                    "task_type": AgentRequestType.RUN_PIPELINE,
                    "payload": {"pipeline": "test"}
                }
            ]
            results = await self.delegate_parallel(tasks)
        """
        import asyncio

        async def run_task(task: Dict[str, Any]) -> Dict[str, Any]:
            return await self.delegate_to_agent(
                target_agent=task["target_agent"],
                task_type=task["task_type"],
                payload=task.get("payload", {}),
                priority=task.get("priority", AgentRequestPriority.NORMAL),
                timeout=timeout,
            )

        # Execute all tasks concurrently
        results = await asyncio.gather(
            *[run_task(task) for task in tasks],
            return_exceptions=True,
        )

        # Convert exceptions to error responses
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "status": "error",
                        "error": str(result),
                        "agent": tasks[i]["target_agent"],
                        "result": None,
                        "processing_time_ms": None,
                    }
                )
            else:
                processed_results.append(result)

        return processed_results

    @traceable(
        name="supervisor_broadcast_workflow_status",
        tags=["supervisor", "broadcast", "workflow"],
    )
    async def broadcast_workflow_status(
        self,
        workflow_id: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        target_agents: Optional[List[str]] = None,
    ) -> None:
        """Broadcast workflow status to all agents in the system.

        Used to notify agents about workflow state changes, such as:
        - Workflow started/completed/failed
        - Agent assignments changed
        - Resource locks acquired/released

        Args:
            workflow_id: Unique workflow identifier
            status: Status string (e.g., "started", "completed", "failed", "paused")
            details: Additional status details
            target_agents: Specific agents to notify (None = all)

        Example:
            await self.broadcast_workflow_status(
                workflow_id="wf-123",
                status="started",
                details={
                    "template": "pr-deployment",
                    "agents_involved": ["code-review", "cicd", "infrastructure"]
                }
            )
        """
        await self.broadcast_status(
            event_type=f"workflow.{status}",
            payload={
                "workflow_id": workflow_id,
                "status": status,
                "details": details or {},
                "timestamp": None,  # Will be set by EventBus
            },
            target_agents=target_agents,
            priority=AgentRequestPriority.HIGH,
        )
