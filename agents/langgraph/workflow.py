"""LangGraph workflow wiring for Dev-Tools agents."""

from __future__ import annotations

from typing import TYPE_CHECKING

from langgraph.graph import END, StateGraph

from agents.langgraph.state import AgentState, empty_agent_state, ensure_agent_state
from agents.langgraph.nodes import (
    COMPLETE_ROUTE,
    cicd_node,
    code_review_node,
    documentation_node,
    feature_dev_node,
    infrastructure_node,
    route_task,
)

if TYPE_CHECKING:  # pragma: no cover - used only for typing
    from langgraph.graph import CompiledGraph

NODE_REGISTRY = {
    "feature-dev": feature_dev_node,
    "code-review": code_review_node,
    "infrastructure": infrastructure_node,
    "cicd": cicd_node,
    "documentation": documentation_node,
}

ENTRY_NODE = "router"


def router_node(state: AgentState) -> AgentState:
    """Normalize incoming payloads before routing."""

    normalized = ensure_agent_state(state)
    return normalized


def build_workflow() -> "CompiledGraph":
    """Create and compile the LangGraph workflow for Dev-Tools agents."""

    workflow = StateGraph(AgentState)

    workflow.add_node(ENTRY_NODE, router_node)
    for label, node in NODE_REGISTRY.items():
        workflow.add_node(label, node)

    workflow.set_entry_point(ENTRY_NODE)

    workflow.add_conditional_edges(
        ENTRY_NODE,
        route_task,
        {
            "feature-dev": "feature-dev",
            "code-review": "code-review",
            "infrastructure": "infrastructure",
            "cicd": "cicd",
            "documentation": "documentation",
            COMPLETE_ROUTE: END,
        },
    )

    # For now, finish after the first specialized node executes. We will expand this
    # once the multi-hop LangGraph orchestration is ready.
    for label in NODE_REGISTRY:
        workflow.add_edge(label, END)

    return workflow.compile()


def invoke_workflow(
    *,
    graph: "CompiledGraph" | None = None,
    task_description: str | None = None,
    initial_state: AgentState | None = None,
) -> AgentState:
    """Helper to run the workflow end-to-end for the provided state."""

    if not graph:
        graph = build_workflow()

    if initial_state is None:
        if not task_description:
            raise ValueError("task_description is required when initial_state is not provided")
        state = empty_agent_state(task_description)
    else:
        state = ensure_agent_state(initial_state)

    return graph.invoke(state)
