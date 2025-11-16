"""Feature development node placeholder."""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from agents.langgraph.state import AgentState, ensure_agent_state

from .base import agent_response


def feature_dev_node(state: AgentState) -> AgentState:
    """Simulate feature implementation work within the LangGraph flow."""

    normalized = ensure_agent_state(state)
    description = normalized["task_description"]

    # Reference the latest user request if one exists, otherwise fall back to task description
    latest_human = next(
        (msg for msg in reversed(normalized["messages"]) if isinstance(msg, HumanMessage)),
        None,
    )
    request_summary = latest_human.content if latest_human else description

    content = (
        f"[feature-dev] Preparing implementation details for: {description}. "
        f"Latest user input: {request_summary[:180]}"
    )

    return agent_response(normalized, agent_name="feature-dev", content=content)
