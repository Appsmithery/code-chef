"""Documentation node placeholder."""

from __future__ import annotations

from agents.langgraph.state import AgentState, ensure_agent_state

from .base import agent_response


def documentation_node(state: AgentState) -> AgentState:
    """Simulate documentation/uplift tasks inside LangGraph."""

    normalized = ensure_agent_state(state)
    description = normalized["task_description"]

    content = (
        "[documentation] Drafting release notes, changelog entries, and handbook "
        f"updates for task: {description}"
    )

    return agent_response(normalized, agent_name="documentation", content=content)
