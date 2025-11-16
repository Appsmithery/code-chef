"""Infrastructure node placeholder."""

from __future__ import annotations

from agents.langgraph.state import AgentState, ensure_agent_state

from .base import agent_response


def infrastructure_node(state: AgentState) -> AgentState:
    """Simulate infra planning tasks inside the unified LangGraph."""

    normalized = ensure_agent_state(state)
    description = normalized["task_description"]

    content = (
        "[infrastructure] Evaluating deployment impact, required cloud resources, and "
        f"runbook updates for task: {description}"
    )

    return agent_response(normalized, agent_name="infrastructure", content=content)
