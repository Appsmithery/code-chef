"""
Checkpoint connection utilities for HITL manager and approval workflows.
Re-exports get_checkpoint_connection from langgraph checkpointer service.
"""
import sys
import os

# Add langgraph service to path
langgraph_src = os.path.join(
    os.path.dirname(__file__),
    "..", "services", "langgraph", "src"
)
sys.path.insert(0, langgraph_src)

from checkpointer import get_checkpoint_connection, get_postgres_checkpointer

__all__ = ["get_checkpoint_connection", "get_postgres_checkpointer"]
