"""
Checkpoint connection utilities for HITL manager and approval workflows.
Re-exports postgres utilities from langgraph_base.
"""
from .langgraph_base import get_postgres_checkpointer, get_postgres_connection_string
import psycopg
from contextlib import asynccontextmanager

# Alias for consistency
get_checkpoint_connection = get_postgres_checkpointer


@asynccontextmanager
async def get_async_connection():
    """Get async PostgreSQL connection for HITL manager"""
    conn_string = get_postgres_connection_string()
    conn = await psycopg.AsyncConnection.connect(conn_string)
    try:
        yield conn
    finally:
        await conn.close()


__all__ = [
    "get_checkpoint_connection",
    "get_postgres_checkpointer",
    "get_postgres_connection_string",
    "get_async_connection"
]
