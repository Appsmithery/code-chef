"""Code review node implementation (stub).

Note: This is a stub implementation since agent_code-review service has been
consolidated into agent_orchestrator/agents/code_review.py. The langgraph service
will be updated to use orchestrator agents directly in a future refactor.
"""

from __future__ import annotations

import logging

from services.langgraph.state import AgentState, ensure_agent_state

from .base import agent_response

logger = logging.getLogger(__name__)


async def code_review_node(state: AgentState) -> AgentState:
    """Execute code review workflow (stub implementation)."""

    normalized = ensure_agent_state(state)
    description = normalized.get("task_description", "")

    request_payload = normalized.get("code_review_request", {})
    task_id = (
        request_payload.get("task_id")
        or normalized.get("linear_issue_id")
        or "code-review-task"
    )

    logger.info(f"[code-review] Processing review request: {task_id}")

    # Stub implementation - return success with placeholder data
    content = (
        f"[code-review] Review {task_id} completed. "
        f"Findings: 0 (critical=0). Status=stub."
    )

    update = agent_response(normalized, agent_name="code-review", content=content)
    update["code_review_request"] = {"task_id": task_id}
    update["code_review_response"] = {
        "review_id": task_id,
        "status": "stub",
        "findings": [],
        "message": "Stub implementation - awaiting orchestrator integration",
    }

    return update
