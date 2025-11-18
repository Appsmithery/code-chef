"""
Checkpoint connection utilities for HITL manager and approval workflows.
Re-exports get_postgres_checkpointer from langgraph_base.
"""
from .langgraph_base import get_postgres_checkpointer

# Alias for consistency
get_checkpoint_connection = get_postgres_checkpointer

__all__ = ["get_checkpoint_connection", "get_postgres_checkpointer"]
