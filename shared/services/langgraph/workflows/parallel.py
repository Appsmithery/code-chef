"""
Parallel Workflow Pattern

Executes multiple independent subtasks concurrently across different agents.
Useful for:
- Running multiple test suites (unit, integration, e2e)
- Analyzing code from different perspectives (security, style, performance)
- Generating documentation for multiple modules
"""

import asyncio
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from ..state import MultiAgentState
from shared.lib.event_bus import get_event_bus, InterAgentEvent

async def decompose_task(state: MultiAgentState):
    """
    Analyze task and break it down into parallel subtasks.
    (This would typically use an LLM, but we'll use the state's subtasks if present)
    """
    # If subtasks already defined in state (from Orchestrator), use them
    if state.get("subtasks"):
        return {"subtask_status": {st["id"]: "pending" for st in state["subtasks"]}}
    
    # Otherwise, we'd need logic to decompose here
    return state

async def delegate_to_agents(state: MultiAgentState):
    """
    Delegate all pending subtasks to appropriate agents in parallel.
    """
    bus = get_event_bus()
    subtasks = state.get("subtasks", [])
    tasks = []
    
    for subtask in subtasks:
        # Create a task for each delegation
        tasks.append(delegate_single_task(bus, subtask, state["task_id"]))
        
    # Wait for all delegations to complete (or at least be acknowledged)
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Update state with assignments
    assignments = {}
    for i, subtask in enumerate(subtasks):
        if not isinstance(results[i], Exception):
            assignments[subtask["id"]] = subtask["agent_type"]
            
    return {"agent_assignments": assignments}

async def delegate_single_task(bus, subtask, correlation_id):
    """Helper to emit delegation event"""
    # In a real system, we might wait for acceptance
    await bus.emit(
        "task.delegated",
        {
            "subtask_id": subtask["id"],
            "description": subtask["description"],
            "payload": subtask
        },
        source="orchestrator",
        target_agent=subtask["agent_type"], # Assuming agent_type maps to agent_id/name
        correlation_id=correlation_id
    )
    return True

async def aggregate_results(state: MultiAgentState):
    """
    Collect results from all subtasks.
    """
    # In a real implementation, this would check if all subtasks are complete
    # and combine their outputs.
    return {"status": "completed"}

def create_parallel_workflow():
    """
    Create a parallel execution workflow.
    """
    workflow = StateGraph(MultiAgentState)
    
    workflow.add_node("decompose", decompose_task)
    workflow.add_node("delegate", delegate_to_agents)
    workflow.add_node("aggregate", aggregate_results)
    
    workflow.set_entry_point("decompose")
    workflow.add_edge("decompose", "delegate")
    workflow.add_edge("delegate", "aggregate")
    workflow.add_edge("aggregate", END)
    
    return workflow.compile()
