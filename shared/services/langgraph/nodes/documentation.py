"""Documentation node implementation (stub).

Note: This is a stub implementation since agent_documentation service has been
consolidated into agent_orchestrator/agents/documentation.py. The langgraph service
will be updated to use orchestrator agents directly in a future refactor.
"""

from __future__ import annotations

import logging

from services.langgraph.state import AgentState, ensure_agent_state

from .base import agent_response

logger = logging.getLogger(__name__)


async def documentation_node(state: AgentState) -> AgentState:
    """Generate documentation artifacts (stub implementation)."""

    normalized = ensure_agent_state(state)
    description = normalized["task_description"]

    request_payload = normalized.get("documentation_request", {})
    doc_type = request_payload.get("doc_type", "readme")
    task_id = request_payload.get("task_id") or normalized.get("linear_issue_id") or "doc-task"

    logger.info(f"[documentation] Processing request: {task_id} ({doc_type})")

    # Stub implementation - return success with placeholder data
    content = (
        f"[documentation] Generated documentation set {task_id} for {doc_type}. "
        f"Artifacts=0. Status=stub."
    )

    update = agent_response(normalized, agent_name="documentation", content=content)
    update["documentation_request"] = {
        "task_id": task_id,
        "doc_type": doc_type
    }
    update["documentation_response"] = {
        "doc_id": task_id,
        "status": "stub",
        "artifacts": [],
        "message": "Stub implementation - awaiting orchestrator integration"
    }

    return update
