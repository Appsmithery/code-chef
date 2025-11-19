from typing import TypedDict, Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from lib.event_bus import get_event_bus
from lib.agent_events import AgentRequestEvent, AgentRequestType, AgentRequestPriority
import asyncio

event_bus = get_event_bus()

class HealingState(TypedDict):
    environment: str
    issues: List[Dict]
    diagnosis: Dict
    fix_result: Dict
    is_resolved: bool
    error: Optional[str]

async def detect_issue(state: HealingState) -> HealingState:
    """Query infrastructure agent for health issues."""
    try:
        request = AgentRequestEvent(
            source_agent="orchestrator",
            target_agent="infrastructure",
            request_type=AgentRequestType.HEALTH_CHECK,
            payload={"environment": state["environment"]}
        )
        response = await event_bus.request_agent(request, timeout=60.0)
        if response.status == "success":
            state["issues"] = response.result.get("issues", [])
        else:
            state["error"] = f"Health check failed: {response.error}"
    except Exception as e:
        state["error"] = f"Health check exception: {str(e)}"
    return state

async def diagnose_issue(state: HealingState) -> HealingState:
    """Ask multiple agents to diagnose."""
    if not state.get("issues"):
        return state
        
    issue = state["issues"][0]
    agents = ["code-review", "cicd", "infrastructure"]
    
    async def ask_agent(agent_name):
        try:
            req = AgentRequestEvent(
                source_agent="orchestrator",
                target_agent=agent_name,
                request_type=AgentRequestType.EXECUTE_TASK, # Using generic execute task for diagnosis
                payload={
                    "task": "diagnose_issue",
                    "issue": issue
                }
            )
            return await event_bus.request_agent(req, timeout=60.0)
        except:
            return None

    results = await asyncio.gather(*[ask_agent(a) for a in agents])
    
    # Aggregate results (simplified)
    valid_results = [r.result for r in results if r and r.status == "success"]
    
    # Simple logic: pick the first valid diagnosis or default
    if valid_results:
        state["diagnosis"] = valid_results[0] # In reality, we'd merge or vote
    else:
        # Fallback diagnosis
        state["diagnosis"] = {
            "recommended_agent": "infrastructure", 
            "fix_parameters": {
                "task": "restart_service",
                "service": issue.get("service", "unknown")
            }
        }
        
    return state

async def apply_fix(state: HealingState) -> HealingState:
    """Apply recommended fix."""
    if not state.get("diagnosis"):
        return state
        
    fix_agent = state["diagnosis"].get("recommended_agent", "infrastructure")
    fix_params = state["diagnosis"].get("fix_parameters", {})
    
    try:
        request = AgentRequestEvent(
            source_agent="orchestrator",
            target_agent=fix_agent,
            request_type=AgentRequestType.EXECUTE_TASK, # Or specific type if available
            payload=fix_params,
            priority=AgentRequestPriority.HIGH
        )
        response = await event_bus.request_agent(request, timeout=300.0)
        state["fix_result"] = response.result if response.status == "success" else {"error": response.error}
    except Exception as e:
        state["fix_result"] = {"error": str(e)}
        
    return state

async def verify_fix(state: HealingState) -> HealingState:
    """Verify issue resolved."""
    try:
        request = AgentRequestEvent(
            source_agent="orchestrator",
            target_agent="infrastructure",
            request_type=AgentRequestType.HEALTH_CHECK,
            payload={"environment": state["environment"]}
        )
        response = await event_bus.request_agent(request, timeout=60.0)
        if response.status == "success":
            current_issues = response.result.get("issues", [])
            state["is_resolved"] = len(current_issues) == 0
        else:
            state["is_resolved"] = False # Assume not resolved if check fails
    except:
        state["is_resolved"] = False
        
    return state

# Build self-healing loop
workflow = StateGraph(HealingState)
workflow.add_node("detect", detect_issue)
workflow.add_node("diagnose", diagnose_issue)
workflow.add_node("apply_fix", apply_fix)
workflow.add_node("verify", verify_fix)

workflow.add_edge("detect", "diagnose")
workflow.add_edge("diagnose", "apply_fix")
workflow.add_edge("apply_fix", "verify")

def check_resolution(state: HealingState):
    if state.get("is_resolved"):
        return END
    if state.get("error"): # Stop if we hit errors to avoid infinite loop
        return END
    # In a real system, we'd have a max retry count
    return "detect"

workflow.add_conditional_edges(
    "verify",
    check_resolution,
    {END: END, "detect": "detect"}
)

workflow.set_entry_point("detect")

self_healing_app = workflow.compile()
