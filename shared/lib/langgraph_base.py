"""
LangGraph Base Infrastructure
Provides shared components for LangGraph workflow integration.

Includes:
- PostgreSQL checkpointing for state persistence
- Multi-agent state schemas
- Workflow configuration helpers
- State management utilities

Usage:
    from shared.lib.langgraph_base import (
        get_postgres_checkpointer,
        MultiAgentWorkflowState,
        create_workflow_config
    )
    
    # Create workflow with checkpointing
    checkpointer = get_postgres_checkpointer()
    workflow = StateGraph(MultiAgentWorkflowState)
    app = workflow.compile(checkpointer=checkpointer)
    
    # Execute with persistent state
    result = await app.ainvoke(
        initial_state,
        config=create_workflow_config(thread_id="task-123")
    )
"""

from datetime import datetime, timezone
from typing import Any, Annotated, Dict, List, Optional, Sequence, TypedDict
import operator
import os
from pathlib import Path

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage


class BaseAgentState(TypedDict):
    """Base state schema for all agent workflows"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    task_id: str
    task_description: str
    current_agent: str
    artifacts: Dict[str, Any]
    context: Dict[str, Any]
    next_action: str
    metadata: Dict[str, Any]


class MultiAgentWorkflowState(TypedDict):
    """
    Shared state schema for multi-agent workflows.
    
    This state is persisted across agent invocations via PostgreSQL
    checkpointing and can be accessed/modified by any participating agent.
    
    Attributes:
        workflow_id: Unique workflow identifier
        workflow_type: Type of workflow (e.g., "pr_deployment")
        task_id: Original task ID from orchestrator
        task_description: Human-readable task description
        current_step: Current workflow step name
        current_agent: Agent currently executing
        participating_agents: List of agents involved in workflow
        agent_results: Results from each agent (keyed by agent name)
        shared_context: Context shared across all agents
        error_log: List of errors encountered during execution
        started_at: Workflow start timestamp
        metadata: Additional workflow metadata
    """
    workflow_id: str
    workflow_type: str
    task_id: str
    task_description: str
    current_step: str
    current_agent: str
    participating_agents: List[str]
    agent_results: Dict[str, Any]
    shared_context: Dict[str, Any]
    error_log: List[str]
    started_at: str  # ISO format timestamp
    metadata: Dict[str, Any]


class AgentStepState(TypedDict):
    """
    State for individual agent steps within a workflow.
    
    Used for fine-grained checkpointing at the agent level.
    """
    step_name: str
    agent_id: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]]
    status: str  # "pending", "running", "completed", "failed"
    error_message: Optional[str]
    duration_ms: Optional[int]
    started_at: str
    completed_at: Optional[str]


def _read_secret(env_var: str, default: str = "") -> str:
    """Read secret from file if *_FILE env var is set, otherwise read from env var directly"""
    file_var = f"{env_var}_FILE"
    if file_path := os.getenv(file_var):
        try:
            return Path(file_path).read_text().strip()
        except Exception as e:
            print(f"Warning: Could not read secret from {file_path}: {e}")
            return default
    return os.getenv(env_var, default)


def get_postgres_connection_string():
    """Get PostgreSQL connection string"""
    db_host = os.getenv("DB_HOST", "postgres")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "devtools")
    db_user = os.getenv("DB_USER", "devtools")
    db_password = _read_secret("POSTGRES_PASSWORD", "changeme")
    
    return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


def get_postgres_checkpointer():
    """Get PostgreSQL checkpointer for state persistence"""
    conn_string = get_postgres_connection_string()
    return PostgresSaver.from_conn_string(conn_string)


def create_workflow_config(thread_id: str, checkpoint_ns: str = "", **kwargs) -> Dict:
    """
    Create standard workflow configuration for LangGraph execution.
    
    Args:
        thread_id: Unique thread identifier (typically workflow_id or task_id)
        checkpoint_ns: Optional checkpoint namespace for isolation
        **kwargs: Additional configuration parameters
    
    Returns:
        Configuration dictionary for LangGraph app.ainvoke()
    """
    return {
        "configurable": {
            "thread_id": thread_id,
            "checkpoint_ns": checkpoint_ns,
            **kwargs
        }
    }


def create_initial_workflow_state(
    workflow_id: str,
    workflow_type: str,
    task_id: str,
    task_description: str,
    participating_agents: List[str],
    initial_context: Optional[Dict[str, Any]] = None
) -> MultiAgentWorkflowState:
    """
    Create initial state for multi-agent workflow.
    
    Args:
        workflow_id: Unique workflow identifier
        workflow_type: Type of workflow (e.g., "pr_deployment")
        task_id: Original task ID
        task_description: Task description
        participating_agents: List of agent IDs
        initial_context: Optional initial shared context
    
    Returns:
        MultiAgentWorkflowState ready for workflow execution
    """
    return MultiAgentWorkflowState(
        workflow_id=workflow_id,
        workflow_type=workflow_type,
        task_id=task_id,
        task_description=task_description,
        current_step="initialized",
        current_agent="orchestrator",
        participating_agents=participating_agents,
        agent_results={},
        shared_context=initial_context or {},
        error_log=[],
        started_at=datetime.now(timezone.utc).isoformat(),
        metadata={}
    )


def create_agent_step_state(
    step_name: str,
    agent_id: str,
    input_data: Dict[str, Any]
) -> AgentStepState:
    """
    Create state for individual agent step.
    
    Args:
        step_name: Name of the step
        agent_id: Agent executing the step
        input_data: Input data for the step
    
    Returns:
        AgentStepState ready for step execution
    """
    return AgentStepState(
        step_name=step_name,
        agent_id=agent_id,
        input_data=input_data,
        output_data=None,
        status="pending",
        error_message=None,
        duration_ms=None,
        started_at=datetime.now(timezone.utc).isoformat(),
        completed_at=None
    )


async def setup_workflow_tables(conn_string: str):
    """
    Setup LangGraph checkpoint tables in PostgreSQL.
    
    This is automatically called by PostgresSaver, but can be invoked
    manually for testing or initialization.
    
    Args:
        conn_string: PostgreSQL connection string
    """
    checkpointer = PostgresSaver.from_conn_string(conn_string)
    await checkpointer.setup()
    return checkpointer
