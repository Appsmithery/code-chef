"""Common helpers for LangGraph node scaffolding."""

from __future__ import annotations

from typing import Iterable, Optional

from langchain_core.messages import AIMessage

from agents.langgraph.state import AgentState, ensure_agent_state


def agent_response(
    state: AgentState,
    *,
    agent_name: str,
    content: str,
    rag_context: Optional[Iterable[str]] = None,
    mcp_tools_used: Optional[Iterable[str]] = None,
) -> AgentState:
    """Build a standardized AgentState update for node outputs.

    Each node should call this helper so we maintain consistent message formatting
    while leveraging the reducers defined on ``AgentState``.
    """

    normalized = ensure_agent_state(state)
    message = AIMessage(content=content, name=agent_name)

    update: AgentState = {
        "messages": [message],
        "current_agent": agent_name,
    }

    if rag_context:
        update["rag_context"] = list(rag_context)
    if mcp_tools_used:
        update["mcp_tools_used"] = list(mcp_tools_used)

    return update
