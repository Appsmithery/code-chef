"""
Sequential Workflow Pattern

Executes a series of agent tasks in a strict linear order.
Useful for pipelines like: Design -> Implement -> Review -> Test -> Deploy
"""

from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from ..state import MultiAgentState

def create_sequential_workflow(steps: List[Dict[str, str]]):
    """
    Create a sequential workflow graph.
    
    Args:
        steps: List of dicts defining the sequence, e.g.:
               [{"name": "design", "agent": "feature-dev"}, 
                {"name": "review", "agent": "code-review"}]
    
    Returns:
        Compiled StateGraph
    """
    workflow = StateGraph(MultiAgentState)
    
    # Add nodes for each step
    for i, step in enumerate(steps):
        node_name = step["name"]
        agent_type = step["agent"]
        
        # Define node function (placeholder for actual agent call)
        async def step_node(state: MultiAgentState, agent=agent_type, step=node_name):
            # In a real implementation, this would call the agent via HTTP/EventBus
            # For now, we update state to reflect progress
            current_results = state.get("partial_results", {})
            current_results[step] = {"status": "completed", "agent": agent}
            
            return {
                "current_step": step,
                "partial_results": current_results,
                "agent_assignments": {**state.get("agent_assignments", {}), step: agent}
            }
            
        workflow.add_node(node_name, step_node)
        
    # Set entry point
    if steps:
        workflow.set_entry_point(steps[0]["name"])
        
    # Add edges
    for i in range(len(steps) - 1):
        workflow.add_edge(steps[i]["name"], steps[i+1]["name"])
        
    # End workflow
    if steps:
        workflow.add_edge(steps[-1]["name"], END)
        
    return workflow.compile()
