"""
Workflow Integration for Orchestrator

Exposes LangGraph workflows to the Orchestrator API.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from shared.services.langgraph.workflows import (
    create_sequential_workflow,
    create_parallel_workflow,
    create_map_reduce_workflow
)
from shared.services.langgraph.state import MultiAgentState
from shared.services.langgraph.persistence import WorkflowPersistence

# Import new Phase 6 workflows
try:
    from .workflows.pr_deployment import pr_deployment_app
    from .workflows.parallel_docs import parallel_docs_app
    from .workflows.self_healing import self_healing_app
except ImportError:
    # Fallback for when running outside of package context
    from workflows.pr_deployment import pr_deployment_app
    from workflows.parallel_docs import parallel_docs_app
    from workflows.self_healing import self_healing_app

logger = logging.getLogger(__name__)

class WorkflowManager:
    def __init__(self, persistence: WorkflowPersistence):
        self.persistence = persistence
        # Cache compiled workflows
        self.workflows = {
            "sequential": create_sequential_workflow([]), # Empty template
            "parallel": create_parallel_workflow(),
            "map_reduce": create_map_reduce_workflow(),
            # Phase 6 Workflows
            "pr_deployment": pr_deployment_app,
            "parallel_docs": parallel_docs_app,
            "self_healing": self_healing_app
        }

    async def start_workflow(
        self, 
        workflow_type: str, 
        task_id: str, 
        initial_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Initialize and start a new workflow.
        """
        if workflow_type not in self.workflows:
            raise ValueError(f"Unknown workflow type: {workflow_type}")
            
        # Initialize state record
        state: MultiAgentState = {
            "task_id": task_id,
            "workflow_type": workflow_type,
            "subtasks": initial_state.get("subtasks", []),
            "subtask_status": {},
            "agent_assignments": {},
            "agent_status": {},
            "locks": {},
            "checkpoints": [],
            "partial_results": {},
            "final_result": None,
            "started_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "error_log": [],
            "_version": 1
        }
        
        # Persist initial state
        await self.persistence.save_state(task_id, state, version=0)
        
        # In a real LangGraph execution, we would invoke the graph here.
        # For now, we just return the initialized state metadata.
        # app = self.workflows[workflow_type]
        # result = await app.ainvoke(state)
        
        logger.info(f"Started {workflow_type} workflow for task {task_id}")
        
        return {
            "task_id": task_id,
            "status": "started",
            "workflow_type": workflow_type
        }

    async def get_workflow_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a workflow."""
        state = await self.persistence.load_state(task_id)
        if not state:
            return None
            
        return {
            "task_id": task_id,
            "status": state.get("status", "running"), # This field needs to be in state
            "progress": f"{len(state.get('partial_results', {}))}/{len(state.get('subtasks', []))}"
        }
