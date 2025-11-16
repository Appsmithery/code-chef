"""LangGraph workflow wiring for Dev-Tools agents."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, AsyncIterator, Mapping

from langgraph.graph import END, StateGraph
from pydantic import BaseModel

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
from agents.langgraph.checkpointer import get_postgres_checkpointer

if TYPE_CHECKING:  # pragma: no cover - used only for typing
    from langgraph.graph import CompiledGraph

logger = logging.getLogger(__name__)

NODE_REGISTRY = {
    "feature-dev": feature_dev_node,
    "code-review": code_review_node,
    "infrastructure": infrastructure_node,
    "cicd": cicd_node,
    "documentation": documentation_node,
}

ENTRY_NODE = "router"

REQUEST_STATE_KEYS = {
    "feature_request",
    "code_review_request",
    "infrastructure_request",
    "cicd_request",
    "documentation_request",
}


def _serialize_request_payload(payload: object) -> Mapping[str, Any]:
    """Convert request payloads into JSON-serializable dictionaries."""

    if isinstance(payload, BaseModel):
        return payload.model_dump(mode="json")
    if isinstance(payload, Mapping):
        return dict(payload)
    raise TypeError(
        "Request payloads must be Pydantic models or mapping types; "
        f"received {type(payload)!r}",
    )


def _apply_request_payloads(state: AgentState, payloads: Mapping[str, object]) -> AgentState:
    """Merge *_request payloads into the shared state with validation."""

    if not payloads:
        return state

    mutable_state: dict[str, Any] = dict(state)
    for key, payload in payloads.items():
        if payload is None:
            continue

        normalized_key = key if key.endswith("_request") else f"{key}_request"
        if normalized_key not in REQUEST_STATE_KEYS:
            raise ValueError(
                "Unsupported request payload key '"
                f"{key}'. Expected one of: {sorted(REQUEST_STATE_KEYS)}"
            )

        mutable_state[normalized_key] = _serialize_request_payload(payload)

    return ensure_agent_state(mutable_state)


def router_node(state: AgentState) -> AgentState:
    """Normalize incoming payloads before routing."""

    normalized = ensure_agent_state(state)
    return normalized


def build_workflow(*, enable_checkpointing: bool = True) -> "CompiledGraph":
    """
    Create and compile the LangGraph workflow for Dev-Tools agents.
    
    Args:
        enable_checkpointing: If True, uses PostgreSQL checkpointer for state persistence
        
    Returns:
        CompiledGraph ready for invocation or streaming
    """
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

    # Configure checkpointer for state persistence
    checkpointer = None
    if enable_checkpointing:
        checkpointer = get_postgres_checkpointer()
        if checkpointer:
            logger.info("LangGraph workflow compiled with PostgreSQL checkpointer")
        else:
            logger.warning("LangGraph workflow compiled WITHOUT checkpointer (state will not persist)")
    
    return workflow.compile(checkpointer=checkpointer)


def invoke_workflow(
    *,
    graph: "CompiledGraph" | None = None,
    task_description: str | None = None,
    initial_state: AgentState | None = None,
    request_payloads: Mapping[str, object] | None = None,
    thread_id: str | None = None,
    enable_checkpointing: bool = True,
) -> AgentState:
    """
    Helper to run the workflow end-to-end for the provided state.
    
    Args:
        graph: Pre-compiled graph (builds new one if None)
        task_description: Description for new workflow (required if initial_state is None)
        initial_state: Starting state (creates empty state if None)
        request_payloads: Agent-specific requests to inject into state
        thread_id: Checkpoint thread ID for resuming workflows
        enable_checkpointing: Whether to persist state in PostgreSQL
        
    Returns:
        Final AgentState after workflow completion
    """
    if not graph:
        graph = build_workflow(enable_checkpointing=enable_checkpointing)

    if initial_state is None:
        if not task_description:
            raise ValueError("task_description is required when initial_state is not provided")
        state = empty_agent_state(task_description)
    else:
        state = ensure_agent_state(initial_state)

    if request_payloads:
        state = _apply_request_payloads(state, request_payloads)

    # Build invocation config
    config = {}
    if thread_id:
        config["configurable"] = {"thread_id": thread_id}
    
    return graph.invoke(state, config=config if config else None)


async def stream_workflow(
    *,
    graph: "CompiledGraph" | None = None,
    task_description: str | None = None,
    initial_state: AgentState | None = None,
    request_payloads: Mapping[str, object] | None = None,
    thread_id: str | None = None,
    enable_checkpointing: bool = True,
    stream_mode: str = "values",
) -> AsyncIterator[dict[str, Any]]:
    """
    Stream workflow execution events in real-time.
    
    Args:
        graph: Pre-compiled graph (builds new one if None)
        task_description: Description for new workflow (required if initial_state is None)
        initial_state: Starting state (creates empty state if None)
        request_payloads: Agent-specific requests to inject into state
        thread_id: Checkpoint thread ID for resuming workflows
        enable_checkpointing: Whether to persist state in PostgreSQL
        stream_mode: LangGraph streaming mode:
            - "values": Stream full state after each node
            - "updates": Stream only state updates from each node
            - "debug": Stream detailed execution events
        
    Yields:
        Dict events containing state snapshots or updates
    """
    if not graph:
        graph = build_workflow(enable_checkpointing=enable_checkpointing)

    if initial_state is None:
        if not task_description:
            raise ValueError("task_description is required when initial_state is not provided")
        state = empty_agent_state(task_description)
    else:
        state = ensure_agent_state(initial_state)

    if request_payloads:
        state = _apply_request_payloads(state, request_payloads)

    # Build invocation config
    config = {}
    if thread_id:
        config["configurable"] = {"thread_id": thread_id}
    
    # Stream events using LangGraph's async streaming
    async for event in graph.astream(state, config=config if config else None, stream_mode=stream_mode):
        yield event


async def stream_workflow_events(
    *,
    graph: "CompiledGraph" | None = None,
    task_description: str | None = None,
    initial_state: AgentState | None = None,
    request_payloads: Mapping[str, object] | None = None,
    thread_id: str | None = None,
    enable_checkpointing: bool = True,
) -> AsyncIterator[dict[str, Any]]:
    """
    Stream detailed workflow events including node execution and LLM calls.
    
    Uses LangGraph's astream_events for fine-grained event streaming,
    useful for progress tracking, debugging, and real-time UI updates.
    
    Args:
        graph: Pre-compiled graph (builds new one if None)
        task_description: Description for new workflow
        initial_state: Starting state
        request_payloads: Agent-specific requests to inject
        thread_id: Checkpoint thread ID for resuming workflows
        enable_checkpointing: Whether to persist state in PostgreSQL
        
    Yields:
        Dict events with structure:
            {
                "event": "on_chain_start" | "on_chain_end" | "on_llm_start" | "on_llm_end" | ...,
                "name": "<node_name>" or "<llm_name>",
                "data": {...},
                "metadata": {...}
            }
    """
    if not graph:
        graph = build_workflow(enable_checkpointing=enable_checkpointing)

    if initial_state is None:
        if not task_description:
            raise ValueError("task_description is required when initial_state is not provided")
        state = empty_agent_state(task_description)
    else:
        state = ensure_agent_state(initial_state)

    if request_payloads:
        state = _apply_request_payloads(state, request_payloads)

    # Build invocation config
    config = {}
    if thread_id:
        config["configurable"] = {"thread_id": thread_id}
    
    # Stream detailed events using astream_events
    async for event in graph.astream_events(state, config=config if config else None, version="v1"):
        yield event

