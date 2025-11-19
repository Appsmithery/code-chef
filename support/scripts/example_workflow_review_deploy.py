"""
Example Multi-Agent Workflow: Code Review → Test → Deploy

Demonstrates Phase 6 multi-agent collaboration with:
- Shared state across agents
- PostgreSQL checkpointing
- Inter-agent communication via event bus
- Automatic state recovery on failure

Usage:
    python support/scripts/example_workflow_review_deploy.py
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from langgraph.graph import StateGraph, END
from shared.lib.langgraph_base import (
    MultiAgentWorkflowState,
    get_postgres_checkpointer,
    create_workflow_config,
    create_initial_workflow_state
)
from shared.lib.workflow_state import WorkflowStateManager
from shared.lib.event_bus import EventBus
from shared.lib.agent_events import AgentRequestEvent, AgentRequestType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# WORKFLOW STEP FUNCTIONS
# ============================================================================

async def code_review_step(state: MultiAgentWorkflowState) -> MultiAgentWorkflowState:
    """
    Step 1: Request code review from code-review agent.
    """
    logger.info(f"[{state['workflow_id']}] Step 1: Code Review")
    
    state["current_step"] = "code_review"
    state["current_agent"] = "code-review"
    
    # Simulate code review via agent request
    # In production, this would use event_bus.request_agent()
    review_result = {
        "status": "approved",
        "comments": [
            {"line": 42, "severity": "info", "message": "Consider using type hints"},
            {"line": 108, "severity": "warning", "message": "Potential SQL injection"}
        ],
        "security_score": 8.5,
        "quality_score": 9.0,
        "approved": True
    }
    
    state["agent_results"]["code_review"] = review_result
    state["shared_context"]["review_approved"] = review_result["approved"]
    
    logger.info(f"[{state['workflow_id']}] Code review: {review_result['status']}")
    return state


async def test_step(state: MultiAgentWorkflowState) -> MultiAgentWorkflowState:
    """
    Step 2: Run tests via CI/CD agent.
    """
    logger.info(f"[{state['workflow_id']}] Step 2: Run Tests")
    
    state["current_step"] = "test"
    state["current_agent"] = "cicd"
    
    # Simulate test execution
    test_result = {
        "total_tests": 127,
        "passed": 125,
        "failed": 2,
        "skipped": 0,
        "coverage": 87.3,
        "duration_seconds": 42.5,
        "all_passed": False  # 2 tests failed
    }
    
    state["agent_results"]["test"] = test_result
    state["shared_context"]["tests_passed"] = test_result["all_passed"]
    
    if not test_result["all_passed"]:
        state["error_log"].append(
            f"Tests failed: {test_result['failed']} failures"
        )
        logger.warning(f"[{state['workflow_id']}] Tests failed: {test_result['failed']} failures")
    else:
        logger.info(f"[{state['workflow_id']}] All tests passed")
    
    return state


async def approval_step(state: MultiAgentWorkflowState) -> MultiAgentWorkflowState:
    """
    Step 3: Request human approval for deployment.
    """
    logger.info(f"[{state['workflow_id']}] Step 3: HITL Approval")
    
    state["current_step"] = "approval"
    state["current_agent"] = "orchestrator"
    
    # Simulate approval (in production, this would wait for actual approval)
    # For demo purposes, auto-approve if review passed
    review_approved = state["shared_context"].get("review_approved", False)
    
    approval_result = {
        "approved": review_approved,
        "approver": "auto-approved" if review_approved else "system",
        "notes": "Tests failed but code review passed - manual review required"
    }
    
    state["agent_results"]["approval"] = approval_result
    state["shared_context"]["deployment_approved"] = approval_result["approved"]
    
    logger.info(f"[{state['workflow_id']}] Approval: {approval_result['approved']}")
    return state


async def deployment_step(state: MultiAgentWorkflowState) -> MultiAgentWorkflowState:
    """
    Step 4: Deploy via infrastructure agent.
    """
    logger.info(f"[{state['workflow_id']}] Step 4: Deployment")
    
    state["current_step"] = "deployment"
    state["current_agent"] = "infrastructure"
    
    # Simulate deployment
    deployment_result = {
        "environment": "staging",  # Don't deploy to prod with failed tests
        "version": "v1.2.3-pr-456",
        "url": "https://staging.example.com",
        "status": "deployed",
        "health_check": "passed"
    }
    
    state["agent_results"]["deployment"] = deployment_result
    state["shared_context"]["deployed"] = True
    
    logger.info(f"[{state['workflow_id']}] Deployed to {deployment_result['environment']}")
    return state


async def finalize_step(state: MultiAgentWorkflowState) -> MultiAgentWorkflowState:
    """
    Final step: Summarize workflow results.
    """
    logger.info(f"[{state['workflow_id']}] Step 5: Finalize")
    
    state["current_step"] = "completed"
    state["current_agent"] = "orchestrator"
    
    # Generate summary
    summary = {
        "workflow_id": state["workflow_id"],
        "status": "completed",
        "review_approved": state["shared_context"].get("review_approved", False),
        "tests_passed": state["shared_context"].get("tests_passed", False),
        "deployed": state["shared_context"].get("deployed", False),
        "errors": state["error_log"],
        "participating_agents": state["participating_agents"],
        "duration": "N/A"  # Would calculate from timestamps
    }
    
    state["agent_results"]["summary"] = summary
    
    logger.info(f"[{state['workflow_id']}] Workflow completed: {summary}")
    return state


# ============================================================================
# CONDITIONAL ROUTING
# ============================================================================

def should_run_tests(state: MultiAgentWorkflowState) -> str:
    """Route to tests if code review passed."""
    if state["shared_context"].get("review_approved", False):
        return "test"
    else:
        return "finalize"


def should_request_approval(state: MultiAgentWorkflowState) -> str:
    """Route to approval if tests passed."""
    tests_passed = state["shared_context"].get("tests_passed", False)
    if tests_passed:
        return "approval"
    else:
        # Skip approval if tests failed - deploy to staging anyway for debugging
        return "deployment"


def should_deploy(state: MultiAgentWorkflowState) -> str:
    """Route to deployment if approved (or tests failed for staging deploy)."""
    approved = state["shared_context"].get("deployment_approved", False)
    tests_passed = state["shared_context"].get("tests_passed", False)
    
    if approved or not tests_passed:  # Deploy to staging if tests failed
        return "deployment"
    else:
        return "finalize"


# ============================================================================
# WORKFLOW CONSTRUCTION
# ============================================================================

def build_review_deploy_workflow() -> StateGraph:
    """
    Build multi-agent review → test → deploy workflow.
    
    Returns:
        Compiled LangGraph StateGraph with PostgreSQL checkpointing
    """
    workflow = StateGraph(MultiAgentWorkflowState)
    
    # Add nodes
    workflow.add_node("code_review", code_review_step)
    workflow.add_node("test", test_step)
    workflow.add_node("approval", approval_step)
    workflow.add_node("deployment", deployment_step)
    workflow.add_node("finalize", finalize_step)
    
    # Add edges
    workflow.set_entry_point("code_review")
    workflow.add_conditional_edges(
        "code_review",
        should_run_tests,
        {"test": "test", "finalize": "finalize"}
    )
    workflow.add_conditional_edges(
        "test",
        should_request_approval,
        {"approval": "approval", "deployment": "deployment"}
    )
    workflow.add_conditional_edges(
        "approval",
        should_deploy,
        {"deployment": "deployment", "finalize": "finalize"}
    )
    workflow.add_edge("deployment", "finalize")
    workflow.add_edge("finalize", END)
    
    # Compile with PostgreSQL checkpointing
    checkpointer = get_postgres_checkpointer()
    return workflow.compile(checkpointer=checkpointer)


# ============================================================================
# WORKFLOW EXECUTION
# ============================================================================

async def run_workflow(workflow_id: str = "demo-workflow-001"):
    """
    Execute the multi-agent workflow with state persistence.
    
    Args:
        workflow_id: Unique workflow identifier
    """
    logger.info("="*60)
    logger.info("Multi-Agent Workflow: Code Review → Test → Deploy")
    logger.info("="*60)
    
    # Initialize state manager
    db_conn = os.getenv(
        "DATABASE_URL",
        "postgresql://devtools:changeme@localhost:5432/devtools"
    )
    state_mgr = WorkflowStateManager(db_conn)
    await state_mgr.connect()
    
    try:
        # Create workflow record
        await state_mgr.create_workflow(
            workflow_type="review_deploy",
            initial_state={
                "pr_number": 456,
                "repo_url": "https://github.com/example/repo",
                "branch": "feature/new-feature"
            },
            participating_agents=["orchestrator", "code-review", "cicd", "infrastructure"],
            workflow_id=workflow_id
        )
        
        # Create initial state
        initial_state = create_initial_workflow_state(
            workflow_id=workflow_id,
            workflow_type="review_deploy",
            task_id="task-789",
            task_description="Review and deploy PR #456",
            participating_agents=["orchestrator", "code-review", "cicd", "infrastructure"],
            initial_context={
                "pr_number": 456,
                "repo_url": "https://github.com/example/repo"
            }
        )
        
        # Build and execute workflow
        app = build_review_deploy_workflow()
        
        logger.info(f"\nExecuting workflow {workflow_id}...")
        result = await app.ainvoke(
            initial_state,
            config=create_workflow_config(thread_id=workflow_id)
        )
        
        # Create checkpoints for each step
        for agent_name, agent_result in result["agent_results"].items():
            await state_mgr.checkpoint(
                workflow_id=workflow_id,
                step_name=agent_name,
                agent_id=agent_name,
                data=agent_result,
                status="success"
            )
        
        # Mark workflow as completed
        await state_mgr.complete_workflow(
            workflow_id=workflow_id,
            final_state={"summary": result["agent_results"].get("summary", {})}
        )
        
        logger.info("\n" + "="*60)
        logger.info("Workflow Summary")
        logger.info("="*60)
        logger.info(f"Workflow ID: {workflow_id}")
        logger.info(f"Status: {result['agent_results']['summary']['status']}")
        logger.info(f"Steps executed: {len(result['agent_results'])}")
        logger.info(f"Agents involved: {', '.join(result['participating_agents'])}")
        logger.info(f"Errors: {len(result['error_log'])}")
        
        if result['error_log']:
            logger.warning("\nErrors encountered:")
            for error in result['error_log']:
                logger.warning(f"  - {error}")
        
        logger.info("\n✓ Workflow completed successfully!")
        logger.info(f"State persisted to PostgreSQL with {len(result['agent_results'])} checkpoints")
        
    finally:
        await state_mgr.close()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    asyncio.run(run_workflow())
