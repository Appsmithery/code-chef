from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langsmith import traceable
from lib.event_bus import get_event_bus
from lib.hitl_manager import get_hitl_manager
from lib.agent_events import AgentRequestEvent, AgentRequestType, AgentRequestPriority

# Initialize clients
event_bus = get_event_bus()
hitl_manager = get_hitl_manager()


class PRDeploymentState(TypedDict):
    pr_number: int
    repo_url: str
    review_comments: List[Dict]
    test_results: Dict
    approval_status: str
    deployment_status: str
    error: Optional[str]


@traceable(name="pr_deployment_code_review", tags=["workflow", "pr", "code-review"])
async def code_review_step(state: PRDeploymentState) -> PRDeploymentState:
    """Request code review from code-review agent."""
    try:
        request = AgentRequestEvent(
            source_agent="orchestrator",
            target_agent="code-review",
            request_type=AgentRequestType.REVIEW_CODE,
            payload={"repo_url": state["repo_url"], "pr_number": state["pr_number"]},
            priority=AgentRequestPriority.HIGH,
        )

        response = await event_bus.request_agent(request, timeout=300.0)

        if response.status == "success":
            state["review_comments"] = response.result.get("comments", [])
        else:
            state["error"] = f"Code review failed: {response.error}"

    except Exception as e:
        state["error"] = f"Code review exception: {str(e)}"

    return state


@traceable(name="pr_deployment_test", tags=["workflow", "pr", "cicd"])
async def test_step(state: PRDeploymentState) -> PRDeploymentState:
    """Request test run from cicd agent."""
    if state.get("error"):
        return state

    try:
        request = AgentRequestEvent(
            source_agent="orchestrator",
            target_agent="cicd",
            request_type=AgentRequestType.RUN_PIPELINE,
            payload={
                "repo_url": state["repo_url"],
                "pr_number": state["pr_number"],
                "pipeline_type": "test",
            },
            priority=AgentRequestPriority.HIGH,
        )

        response = await event_bus.request_agent(request, timeout=600.0)

        if response.status == "success":
            state["test_results"] = response.result
        else:
            state["error"] = f"Tests failed: {response.error}"

    except Exception as e:
        state["error"] = f"Test exception: {str(e)}"

    return state


@traceable(name="pr_deployment_approval", tags=["workflow", "pr", "hitl"])
async def approval_step(state: PRDeploymentState) -> PRDeploymentState:
    """Request HITL approval."""
    if state.get("error"):
        return state

    try:
        approval_id = await hitl_manager.create_approval_request(
            workflow_id=f"pr-{state['pr_number']}",
            thread_id=f"pr-thread-{state['pr_number']}",
            checkpoint_id=f"pr-checkpoint-{state['pr_number']}",
            task={
                "operation": "deploy_to_production",
                "description": f"Deploy PR #{state['pr_number']} to production",
                "environment": "production",
                "risk_factors": ["production-deployment"],
                "context": {
                    "pr": state["pr_number"],
                    "review_summary": f"{len(state.get('review_comments', []))} comments",
                    "test_status": state.get("test_results", {}).get(
                        "status", "unknown"
                    ),
                },
            },
            agent_name="orchestrator",
        )

        # In a real system, we would suspend here.
        # For this example, we mark as pending.
        state["approval_status"] = "pending"

    except Exception as e:
        state["error"] = f"Approval request failed: {str(e)}"

    return state


@traceable(name="pr_deployment_deploy", tags=["workflow", "pr", "infrastructure"])
async def deployment_step(state: PRDeploymentState) -> PRDeploymentState:
    """Request deployment from infrastructure agent."""
    if state.get("error") or state.get("approval_status") != "approved":
        return state

    try:
        request = AgentRequestEvent(
            source_agent="orchestrator",
            target_agent="infrastructure",
            request_type=AgentRequestType.DEPLOY_SERVICE,
            payload={
                "repo_url": state["repo_url"],
                "environment": "production",
                "version": f"pr-{state['pr_number']}",
            },
            priority=AgentRequestPriority.URGENT,
        )

        response = await event_bus.request_agent(request, timeout=600.0)

        if response.status == "success":
            state["deployment_status"] = "success"
        else:
            state["deployment_status"] = "failed"
            state["error"] = f"Deployment failed: {response.error}"

    except Exception as e:
        state["error"] = f"Deployment exception: {str(e)}"

    return state


# Build workflow
workflow = StateGraph(PRDeploymentState)
workflow.add_node("code_review", code_review_step)
workflow.add_node("test", test_step)
workflow.add_node("approval", approval_step)
workflow.add_node("deploy", deployment_step)

workflow.add_edge("code_review", "test")
workflow.add_edge("test", "approval")


def check_approval(state: PRDeploymentState):
    if state.get("error"):
        return END
    if state["approval_status"] == "approved":
        return "deploy"
    # If pending or rejected, we stop here (in reality we might wait)
    return END


workflow.add_conditional_edges(
    "approval", check_approval, {"deploy": "deploy", END: END}
)
workflow.add_edge("deploy", END)

workflow.set_entry_point("code_review")

# Compile the workflow
pr_deployment_app = workflow.compile()
