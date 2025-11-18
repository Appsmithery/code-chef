"""
LangGraph Base Infrastructure
Provides shared components for LangGraph workflow integration
"""

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Sequence, Any
from langchain_core.messages import BaseMessage
import operator
import os


class BaseAgentState(TypedDict):
    """Base state schema for all agent workflows"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    task_id: str
    task_description: str
    current_agent: str
    artifacts: dict[str, Any]
    context: dict[str, Any]
    next_action: str
    metadata: dict[str, Any]


def get_postgres_checkpointer():
    """Get PostgreSQL checkpointer for state persistence"""
    db_host = os.getenv("DB_HOST", "postgres")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "devtools")
    db_user = os.getenv("DB_USER", "devtools")
    db_password = os.getenv("DB_PASSWORD", "changeme")
    
    conn_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    return PostgresSaver.from_conn_string(conn_string)


def create_workflow_config(thread_id: str, **kwargs) -> dict:
    """Create standard workflow configuration"""
    return {
        "configurable": {
            "thread_id": thread_id,
            **kwargs
        }
    }
