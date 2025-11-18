"""
LangGraph interrupt nodes for Human-in-the-Loop approval workflows.
Implements interrupt_before pattern for autonomous operations requiring approval.
"""
from typing import Dict, Any, Optional
import logging
from langgraph.graph import StateGraph
from langgraph.checkpoint.postgres import PostgresSaver

from shared.lib.hitl_manager import get_hitl_manager
from shared.lib.checkpoint_connection import get_checkpoint_connection

logger = logging.getLogger(__name__)


async def approval_gate(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node that checks for approval before executing high-risk operations.
    
    This node:
    1. Extracts pending operation from state
    2. Assesses risk level
    3. Creates approval request if needed (interrupts workflow)
    4. On resumption, checks approval status and proceeds or fails
    
    State schema:
        - pending_operation: Dict with operation details
        - approval_request_id: UUID of approval request (set by this node)
        - approval_status: Status after resumption (approved/rejected/expired)
        - agent_name: Name of agent requesting approval
        - workflow_id: Unique workflow identifier
    
    Usage in LangGraph:
        workflow = StateGraph(state_schema)
        workflow.add_node("approval_gate", approval_gate)
        workflow.add_edge("plan", "approval_gate")
        workflow.add_conditional_edges(
            "approval_gate",
            lambda state: "execute" if state["approval_status"] == "approved" else "rejected"
        )
    """
    hitl_manager = get_hitl_manager()
    
    pending_operation = state.get("pending_operation")
    if not pending_operation:
        logger.warning("[approval_gate] No pending operation in state")
        return state
    
    approval_request_id = state.get("approval_request_id")
    
    # First pass: Create approval request and interrupt
    if approval_request_id is None:
        workflow_id = state.get("workflow_id")
        thread_id = state.get("thread_id")
        checkpoint_id = state.get("checkpoint_id")  # Provided by checkpointer
        agent_name = state.get("agent_name", "unknown")
        
        logger.info(
            f"[approval_gate] Assessing operation: {pending_operation.get('operation')} "
            f"on {pending_operation.get('resource_type')}"
        )
        
        # Create approval request (returns None if auto-approved)
        request_id = await hitl_manager.create_approval_request(
            workflow_id=workflow_id,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            task=pending_operation,
            agent_name=agent_name
        )
        
        if request_id is None:
            # Auto-approved, continue immediately
            logger.info("[approval_gate] Operation auto-approved")
            state["approval_status"] = "approved"
            return state
        
        # Store request ID and interrupt workflow
        state["approval_request_id"] = request_id
        state["approval_status"] = "pending"
        
        logger.info(f"[approval_gate] Created approval request {request_id}, interrupting workflow")
        
        # Return state with interrupt marker
        # LangGraph will checkpoint here and wait for human action
        return state
    
    # Resumption pass: Check approval status
    else:
        logger.info(f"[approval_gate] Checking approval status for request {approval_request_id}")
        
        status_info = await hitl_manager.check_approval_status(approval_request_id)
        approval_status = status_info["status"]
        
        state["approval_status"] = approval_status
        state["approver_id"] = status_info.get("approver_id")
        state["approval_timestamp"] = status_info.get("approved_at")
        state["rejection_reason"] = status_info.get("rejection_reason")
        
        if approval_status == "approved":
            logger.info(
                f"[approval_gate] Operation approved by {status_info.get('approver_id')}, "
                "proceeding with execution"
            )
        elif approval_status == "rejected":
            logger.warning(
                f"[approval_gate] Operation rejected: {status_info.get('rejection_reason')}"
            )
        elif approval_status == "expired":
            logger.warning("[approval_gate] Approval request expired")
        
        return state


async def conditional_approval_router(state: Dict[str, Any]) -> str:
    """
    Conditional edge router based on approval status.
    
    Routes to:
        - "execute": If approved
        - "rejected": If rejected or expired
        - "pending": If still waiting (should not happen after interrupt)
    
    Usage:
        workflow.add_conditional_edges(
            "approval_gate",
            conditional_approval_router,
            {
                "execute": "execute_operation",
                "rejected": "handle_rejection",
                "pending": "approval_gate"  # Re-check
            }
        )
    """
    approval_status = state.get("approval_status", "pending")
    
    if approval_status == "approved":
        return "execute"
    elif approval_status in ["rejected", "expired"]:
        return "rejected"
    else:
        return "pending"


def create_approval_workflow(agent_name: str) -> StateGraph:
    """
    Create a LangGraph workflow with approval gate.
    
    Workflow structure:
        start -> plan -> approval_gate -> execute -> end
                                      |
                                      +-> rejected -> end
    
    Args:
        agent_name: Name of agent using this workflow
    
    Returns:
        Configured StateGraph with checkpoint support
    """
    from typing import TypedDict
    
    class WorkflowState(TypedDict, total=False):
        workflow_id: str
        thread_id: str
        checkpoint_id: str
        agent_name: str
        pending_operation: Dict
        approval_request_id: Optional[str]
        approval_status: str
        approver_id: Optional[str]
        approval_timestamp: Optional[str]
        rejection_reason: Optional[str]
        execution_result: Optional[Dict]
    
    workflow = StateGraph(WorkflowState)
    
    # Add nodes
    workflow.add_node("approval_gate", approval_gate)
    
    # Configure checkpoint
    checkpoint_connection = get_checkpoint_connection()
    checkpointer = PostgresSaver(checkpoint_connection)
    
    # Set default agent name in state
    workflow.set_entry_point("approval_gate")
    
    logger.info(f"[create_approval_workflow] Created workflow for agent {agent_name}")
    
    return workflow.compile(checkpointer=checkpointer, interrupt_before=["approval_gate"])


async def resume_workflow(workflow_id: str, thread_id: str) -> Dict[str, Any]:
    """
    Resume a workflow after approval/rejection.
    
    Args:
        workflow_id: Workflow identifier
        thread_id: LangGraph thread ID
    
    Returns:
        Final workflow state
    """
    from langgraph.checkpoint.postgres import PostgresSaver
    
    checkpoint_connection = get_checkpoint_connection()
    checkpointer = PostgresSaver(checkpoint_connection)
    
    # Get latest checkpoint
    checkpoint = await checkpointer.aget({"thread_id": thread_id})
    
    if not checkpoint:
        raise ValueError(f"No checkpoint found for thread {thread_id}")
    
    logger.info(
        f"[resume_workflow] Resuming workflow {workflow_id} from checkpoint {checkpoint.id}"
    )
    
    # Workflow will continue from approval_gate node
    # Application code should invoke workflow.ainvoke() with checkpoint
    
    return checkpoint.state


# Example usage functions

async def example_feature_deployment():
    """Example: Feature deployment workflow with approval gate"""
    
    workflow = create_approval_workflow("feature-dev")
    
    initial_state = {
        "workflow_id": "deploy-auth-feature-123",
        "thread_id": "thread-abc",
        "agent_name": "feature-dev",
        "pending_operation": {
            "operation": "deploy",
            "environment": "production",
            "resource_type": "application",
            "description": "Deploy JWT authentication feature to production",
            "estimated_cost": 50,
            "security_findings": [],
            "data_sensitive": False
        }
    }
    
    # First invocation: workflow will interrupt at approval_gate
    result = await workflow.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": "thread-abc"}}
    )
    
    logger.info(f"Workflow interrupted, approval request: {result['approval_request_id']}")
    
    # ... Human approves via Taskfile command or API ...
    
    # Second invocation: workflow resumes and checks approval
    final_result = await workflow.ainvoke(
        None,  # State loaded from checkpoint
        config={"configurable": {"thread_id": "thread-abc"}}
    )
    
    logger.info(f"Workflow completed: {final_result['approval_status']}")


async def example_database_deletion():
    """Example: High-risk database deletion with approval gate"""
    
    workflow = create_approval_workflow("infrastructure")
    
    initial_state = {
        "workflow_id": "delete-db-456",
        "thread_id": "thread-xyz",
        "agent_name": "infrastructure",
        "pending_operation": {
            "operation": "delete",
            "environment": "production",
            "resource_type": "database",
            "description": "Delete deprecated user_sessions table",
            "estimated_cost": 0,
            "security_findings": [],
            "data_sensitive": True  # Triggers critical risk
        }
    }
    
    # Workflow will interrupt and require devops-engineer approval
    result = await workflow.ainvoke(
        initial_state,
        config={"configurable": {"thread_id": "thread-xyz"}}
    )
    
    logger.info(
        f"Critical operation requires approval: {result['approval_request_id']} "
        f"(risk_level=critical)"
    )
