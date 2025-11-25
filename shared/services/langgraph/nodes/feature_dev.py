"""Feature development node implementation (stub).

Note: This is a stub implementation since agent_feature-dev service has been
consolidated into agent_orchestrator/agents/feature_dev.py. The langgraph service
will be updated to use orchestrator agents directly in a future refactor.
"""

from __future__ import annotations

import logging

from services.langgraph.state import AgentState, ensure_agent_state

from .base import agent_response

logger = logging.getLogger(__name__)


async def feature_dev_node(state: AgentState) -> AgentState:
    """Run feature implementation workflow (stub implementation)."""

    normalized = ensure_agent_state(state)
    description = normalized.get("task_description", "")

    request_payload = normalized.get("feature_request", {})
    task_id = (
        request_payload.get("task_id")
        or normalized.get("linear_issue_id")
        or "feature-dev-task"
    )

    logger.info(f"[feature-dev] Processing feature request: {task_id}")

    # Stub implementation - return success with placeholder data
    content = (
        f"[feature-dev] Completed feature '{task_id}' with status stub. "
        f"Artifacts: none. Status=pending."
    )

    update = agent_response(normalized, agent_name="feature-dev", content=content)
    update["feature_request"] = {"task_id": task_id, "description": description}
    update["feature_response"] = {
        "feature_id": task_id,
        "status": "stub",
        "artifacts": [],
        "message": "Stub implementation - awaiting orchestrator integration",
    }

    return update
