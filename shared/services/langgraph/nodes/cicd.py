"""CI/CD node implementation (stub).

Note: This is a stub implementation since agent_cicd service has been
consolidated into agent_orchestrator/agents/cicd.py. The langgraph service
will be updated to use orchestrator agents directly in a future refactor.
"""

from __future__ import annotations

import logging

from services.langgraph.state import AgentState, ensure_agent_state

from .base import agent_response

logger = logging.getLogger(__name__)


async def cicd_node(state: AgentState) -> AgentState:
    """Generate CI/CD artifacts (stub implementation)."""

    normalized = ensure_agent_state(state)
    description = normalized["task_description"]

    request_payload = normalized.get("cicd_request", {})
    pipeline_type = request_payload.get("pipeline_type", "github-actions")
    stages = request_payload.get("stages", ["build", "test", "deploy"])
    task_id = (
        request_payload.get("task_id")
        or normalized.get("linear_issue_id")
        or "cicd-task"
    )

    logger.info(f"[cicd] Processing pipeline request: {task_id} ({pipeline_type})")

    # Stub implementation - return success with placeholder data
    content = (
        f"[cicd] Generated pipeline {task_id} for {pipeline_type}. "
        f"Stages: {', '.join(stages)}. Validation=pending."
    )

    update = agent_response(normalized, agent_name="cicd", content=content)
    update["cicd_request"] = {
        "task_id": task_id,
        "pipeline_type": pipeline_type,
        "stages": stages,
    }
    update["cicd_response"] = {
        "pipeline_id": task_id,
        "status": "stub",
        "validation_status": "pending",
        "message": "Stub implementation - awaiting orchestrator integration",
    }

    return update
