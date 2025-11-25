"""Infrastructure node implementation (stub).

Note: This is a stub implementation since agent_infrastructure service has been
consolidated into agent_orchestrator/agents/infrastructure.py. The langgraph service
will be updated to use orchestrator agents directly in a future refactor.
"""

from __future__ import annotations

import logging

from services.langgraph.state import AgentState, ensure_agent_state

from .base import agent_response

logger = logging.getLogger(__name__)


async def infrastructure_node(state: AgentState) -> AgentState:
    """Generate infrastructure artifacts (stub implementation)."""

    normalized = ensure_agent_state(state)
    description = normalized["task_description"]

    request_payload = normalized.get("infrastructure_request", {})
    infrastructure_type = request_payload.get("infrastructure_type", "docker")
    task_id = request_payload.get("task_id") or normalized.get("linear_issue_id") or "infra-task"

    logger.info(f"[infrastructure] Processing request: {task_id} ({infrastructure_type})")

    # Stub implementation - return success with placeholder data
    content = (
        f"[infrastructure] Generated 0 artifact(s) for {infrastructure_type}. "
        f"Validation=pending. Status=stub."
    )

    update = agent_response(normalized, agent_name="infrastructure", content=content)
    update["infrastructure_request"] = {
        "task_id": task_id,
        "infrastructure_type": infrastructure_type
    }
    update["infrastructure_response"] = {
        "task_id": task_id,
        "status": "stub",
        "artifacts": [],
        "validation_status": "pending",
        "message": "Stub implementation - awaiting orchestrator integration"
    }

    return update
