from typing import TypedDict, Dict, Any, List, Optional
from langgraph.graph import StateGraph, END, START
from langsmith import traceable
from lib.event_bus import get_event_bus
from lib.agent_events import AgentRequestEvent, AgentRequestType, AgentRequestPriority

event_bus = get_event_bus()


class DocsState(TypedDict):
    repo_url: str
    api_docs: Optional[Dict]
    user_guide: Optional[Dict]
    deployment_guide: Optional[Dict]
    merged_docs: Optional[Dict]
    errors: List[str]


@traceable(name="parallel_docs_api", tags=["workflow", "documentation", "parallel"])
async def generate_api_docs(state: DocsState) -> DocsState:
    """Generate API documentation."""
    try:
        request = AgentRequestEvent(
            source_agent="orchestrator",
            target_agent="documentation",
            request_type=AgentRequestType.GENERATE_DOCS,
            payload={"repo_url": state["repo_url"], "doc_type": "api_reference"},
        )
        response = await event_bus.request_agent(request, timeout=300.0)
        if response.status == "success":
            state["api_docs"] = response.result
        else:
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append(f"API docs failed: {response.error}")
    except Exception as e:
        if "errors" not in state:
            state["errors"] = []
        state["errors"].append(f"API docs exception: {str(e)}")
    return state


@traceable(
    name="parallel_docs_user_guide", tags=["workflow", "documentation", "parallel"]
)
async def generate_user_guide(state: DocsState) -> DocsState:
    """Generate user guide."""
    try:
        request = AgentRequestEvent(
            source_agent="orchestrator",
            target_agent="documentation",
            request_type=AgentRequestType.GENERATE_DOCS,
            payload={"repo_url": state["repo_url"], "doc_type": "user_guide"},
        )
        response = await event_bus.request_agent(request, timeout=300.0)
        if response.status == "success":
            state["user_guide"] = response.result
        else:
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append(f"User guide failed: {response.error}")
    except Exception as e:
        if "errors" not in state:
            state["errors"] = []
        state["errors"].append(f"User guide exception: {str(e)}")
    return state


@traceable(
    name="parallel_docs_deployment_guide",
    tags=["workflow", "documentation", "parallel"],
)
async def generate_deployment_guide(state: DocsState) -> DocsState:
    """Generate deployment guide."""
    try:
        request = AgentRequestEvent(
            source_agent="orchestrator",
            target_agent="documentation",
            request_type=AgentRequestType.GENERATE_DOCS,
            payload={"repo_url": state["repo_url"], "doc_type": "deployment_guide"},
        )
        response = await event_bus.request_agent(request, timeout=300.0)
        if response.status == "success":
            state["deployment_guide"] = response.result
        else:
            if "errors" not in state:
                state["errors"] = []
            state["errors"].append(f"Deployment guide failed: {response.error}")
    except Exception as e:
        if "errors" not in state:
            state["errors"] = []
        state["errors"].append(f"Deployment guide exception: {str(e)}")
    return state


@traceable(name="parallel_docs_merge", tags=["workflow", "documentation", "parallel"])
async def merge_documentation(state: DocsState) -> DocsState:
    """Merge all documentation."""
    # In a real scenario, this might call another agent or do local processing
    state["merged_docs"] = {
        "api": state.get("api_docs"),
        "user": state.get("user_guide"),
        "deploy": state.get("deployment_guide"),
    }
    return state


# Parallel execution
workflow = StateGraph(DocsState)
workflow.add_node("api_docs", generate_api_docs)
workflow.add_node("user_guide", generate_user_guide)
workflow.add_node("deployment_guide", generate_deployment_guide)
workflow.add_node("merge", merge_documentation)

# All three run in parallel from START
workflow.add_edge(START, "api_docs")
workflow.add_edge(START, "user_guide")
workflow.add_edge(START, "deployment_guide")

# Merge results
workflow.add_edge("api_docs", "merge")
workflow.add_edge("user_guide", "merge")
workflow.add_edge("deployment_guide", "merge")
workflow.add_edge("merge", END)

parallel_docs_app = workflow.compile()


def node1(state):
    pass


workflow.add_node("node_1", node1)  # Add node for node1
