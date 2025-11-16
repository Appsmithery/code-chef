"""Code review node placeholder."""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from agents.langgraph.state import AgentState, ensure_agent_state

from .base import agent_response


def code_review_node(state: AgentState) -> AgentState:
    """Simulate code review feedback while LangGraph wiring is in progress."""

    normalized = ensure_agent_state(state)
    description = normalized["task_description"]

    latest_diff_request = next(
        (msg for msg in reversed(normalized["messages"]) if isinstance(msg, HumanMessage)),
        None,
    )

    focus = latest_diff_request.content[:200] if latest_diff_request else description
    content = (
        "[code-review] Analyzing submitted artifacts for style, tests, and potential "
        f"regressions. Focus area: {focus}"
    )

    return agent_response(normalized, agent_name="code-review", content=content)
