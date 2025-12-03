"""
PostgreSQL checkpoint saver for LangGraph state persistence.

Provides durable state storage across workflow invocations, enabling:
- Resume interrupted workflows
- Multi-step task tracking
- State history and rollback
- Concurrent workflow isolation
"""

import logging
import os
from typing import Optional
from langgraph.checkpoint.postgres import PostgresSaver
import psycopg

logger = logging.getLogger(__name__)

# PostgreSQL connection parameters from environment
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "devtools")
DB_USER = os.getenv("DB_USER", "devtools")
DB_PASSWORD = os.getenv("DB_PASSWORD", "changeme")


def get_postgres_checkpointer() -> Optional[PostgresSaver]:
    """
    Create PostgresSaver for LangGraph state persistence.
    
    Returns PostgresSaver connected to database or None if connection fails.
    The checkpointer automatically creates the required checkpoints table.
    
    Environment Variables:
        DB_HOST: PostgreSQL host (default: postgres)
        DB_PORT: PostgreSQL port (default: 5432)
        DB_NAME: Database name (default: devtools)
        DB_USER: Database user (default: devtools)
        DB_PASSWORD: Database password (default: changeme)
    
    Returns:
        PostgresSaver instance or None if disabled/unavailable
    """
    # Skip if no database configured
    if not DB_PASSWORD or DB_PASSWORD == "changeme":
        logger.warning("PostgreSQL checkpointer disabled: DB_PASSWORD not configured")
        return None
    
    try:
        # Build connection string
        conn_string = (
            f"host={DB_HOST} "
            f"port={DB_PORT} "
            f"dbname={DB_NAME} "
            f"user={DB_USER} "
            f"password={DB_PASSWORD}"
        )
        
        # Create connection with autocommit for schema setup
        # Required because CREATE INDEX CONCURRENTLY cannot run inside a transaction
        setup_connection = psycopg.connect(conn_string, autocommit=True)
        
        # Initialize PostgresSaver and run schema setup
        checkpointer = PostgresSaver(setup_connection)
        checkpointer.setup()  # Creates tables and indexes
        setup_connection.close()
        
        # Create new connection for actual checkpointer operations
        connection = psycopg.connect(conn_string)
        checkpointer = PostgresSaver(connection)
        
        logger.info(f"PostgreSQL checkpointer initialized: {DB_HOST}:{DB_PORT}/{DB_NAME}")
        return checkpointer
        
    except Exception as e:
        logger.error(f"Failed to initialize PostgreSQL checkpointer: {e}")
        logger.warning("Workflow state will NOT be persisted")
        return None


def get_checkpoint_connection() -> Optional[psycopg.Connection]:
    """
    Get raw psycopg connection for checkpoint operations.
    
    Useful for manual checkpoint queries or migrations.
    
    Returns:
        psycopg.Connection or None if unavailable
    """
    if not DB_PASSWORD or DB_PASSWORD == "changeme":
        logger.warning("Database connection unavailable: DB_PASSWORD not configured")
        return None
    
    try:
        conn_string = (
            f"host={DB_HOST} "
            f"port={DB_PORT} "
            f"dbname={DB_NAME} "
            f"user={DB_USER} "
            f"password={DB_PASSWORD}"
        )
        return psycopg.connect(conn_string)
        
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        return None
