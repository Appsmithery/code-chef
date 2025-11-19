"""
Map-Reduce Workflow Pattern

Distributes a large dataset or task list across workers (Map),
then combines the results into a single output (Reduce).
Useful for:
- Batch processing files
- Aggregating search results
- Multi-file refactoring
"""

import asyncio
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from ..state import MultiAgentState
from shared.lib.event_bus import get_event_bus

async def map_tasks(state: MultiAgentState):
    """
    Distribute work items to available agents.
    """
    # Logic to split input_data into chunks would go here
    # For now, we assume subtasks are already prepared
    return {"current_step": "map"}

async def reduce_results(state: MultiAgentState):
    """
    Aggregate results from all map tasks.
    """
    partial_results = state.get("partial_results", {})
    results_list = list(partial_results.values())
    
    # Simple aggregation (list of results)
    final_result = {"items": results_list, "count": len(results_list)}
    
    return {
        "final_result": final_result, 
        "current_step": "reduce",
        "status": "completed"
    }

def create_map_reduce_workflow():
    """
    Create a Map-Reduce workflow.
    """
    workflow = StateGraph(MultiAgentState)
    
    workflow.add_node("map", map_tasks)
    workflow.add_node("reduce", reduce_results)
    
    workflow.set_entry_point("map")
    workflow.add_edge("map", "reduce")
    workflow.add_edge("reduce", END)
    
    return workflow.compile()
