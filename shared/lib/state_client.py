"""State Service Client - Task to Linear Issue Mappings

Provides interface for storing and retrieving task-to-Linear mappings
across agent lifecycle. Enables agents to track which Linear issues
correspond to orchestrator task IDs.

Environment Variables:
    STATE_SERVICE_URL: URL of state service (default: http://state:8008)
    POSTGRES_HOST: PostgreSQL host (default: postgres)
    POSTGRES_PORT: PostgreSQL port (default: 5432)
    POSTGRES_DB: Database name (default: devtools_state)
    POSTGRES_USER: Database user
    POSTGRES_PASSWORD: Database password
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncpg

logger = logging.getLogger(__name__)


class StateClient:
    """Client for state service operations."""
    
    def __init__(self):
        """Initialize state client with database connection."""
        self.db_host = os.getenv("POSTGRES_HOST", "postgres")
        self.db_port = int(os.getenv("POSTGRES_PORT", "5432"))
        self.db_name = os.getenv("POSTGRES_DB", "devtools_state")
        self.db_user = os.getenv("POSTGRES_USER")
        self.db_password = os.getenv("POSTGRES_PASSWORD")
        self._pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Establish connection pool to PostgreSQL."""
        if self._pool is None:
            try:
                self._pool = await asyncpg.create_pool(
                    host=self.db_host,
                    port=self.db_port,
                    database=self.db_name,
                    user=self.db_user,
                    password=self.db_password,
                    min_size=2,
                    max_size=10
                )
                logger.info("State client connected to PostgreSQL")
            except Exception as e:
                logger.error(f"Failed to connect to PostgreSQL: {e}")
                raise
    
    async def close(self):
        """Close database connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("State client disconnected from PostgreSQL")
    
    async def store_task_mapping(
        self,
        task_id: str,
        linear_issue_id: str,
        linear_identifier: str,
        agent_name: str,
        parent_issue_id: Optional[str] = None,
        parent_identifier: Optional[str] = None,
        status: str = "todo"
    ) -> Dict[str, Any]:
        """Store mapping between task ID and Linear issue.
        
        Args:
            task_id: Orchestrator task ID (unique)
            linear_issue_id: Linear issue UUID
            linear_identifier: Linear issue identifier (e.g., "PR-123")
            agent_name: Name of agent handling task
            parent_issue_id: Parent Linear issue UUID (optional)
            parent_identifier: Parent Linear issue identifier (optional)
            status: Initial status (default: "todo")
        
        Returns:
            Dict with stored mapping data
        
        Raises:
            ValueError: If task_id already exists
            Exception: Database errors
        """
        if self._pool is None:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                # Check for existing task_id
                existing = await conn.fetchrow(
                    "SELECT task_id FROM task_linear_mappings WHERE task_id = $1",
                    task_id
                )
                if existing:
                    raise ValueError(f"Task ID {task_id} already mapped")
                
                # Insert new mapping
                row = await conn.fetchrow(
                    """
                    INSERT INTO task_linear_mappings 
                    (task_id, linear_issue_id, linear_identifier, agent_name, 
                     parent_issue_id, parent_identifier, status)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id, task_id, linear_issue_id, linear_identifier, 
                              agent_name, status, created_at
                    """,
                    task_id, linear_issue_id, linear_identifier, agent_name,
                    parent_issue_id, parent_identifier, status
                )
                
                result = dict(row)
                logger.info(f"Stored task mapping: {task_id} → {linear_identifier}")
                return result
        
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to store task mapping: {e}")
            raise
    
    async def get_task_mapping(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve Linear issue mapping for task ID.
        
        Args:
            task_id: Orchestrator task ID
        
        Returns:
            Dict with mapping data or None if not found
        """
        if self._pool is None:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, task_id, linear_issue_id, linear_identifier, 
                           agent_name, parent_issue_id, parent_identifier, 
                           status, created_at, updated_at, completed_at
                    FROM task_linear_mappings
                    WHERE task_id = $1
                    """,
                    task_id
                )
                
                if row is None:
                    return None
                
                return dict(row)
        
        except Exception as e:
            logger.error(f"Failed to get task mapping: {e}")
            raise
    
    async def update_task_status(
        self, 
        task_id: str, 
        status: str,
        mark_completed: bool = False
    ) -> bool:
        """Update status of task mapping.
        
        Args:
            task_id: Orchestrator task ID
            status: New status (todo, in_progress, done, canceled)
            mark_completed: Set completed_at timestamp (for done/canceled)
        
        Returns:
            True if updated, False if task not found
        """
        if self._pool is None:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                if mark_completed:
                    result = await conn.execute(
                        """
                        UPDATE task_linear_mappings
                        SET status = $1, completed_at = CURRENT_TIMESTAMP
                        WHERE task_id = $2
                        """,
                        status, task_id
                    )
                else:
                    result = await conn.execute(
                        """
                        UPDATE task_linear_mappings
                        SET status = $1
                        WHERE task_id = $2
                        """,
                        status, task_id
                    )
                
                updated = result.split()[1] == "1"
                if updated:
                    logger.info(f"Updated task status: {task_id} → {status}")
                return updated
        
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
            raise
    
    async def get_agent_tasks(
        self, 
        agent_name: str, 
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all tasks for agent, optionally filtered by status.
        
        Args:
            agent_name: Name of agent
            status: Optional status filter (todo, in_progress, done, canceled)
        
        Returns:
            List of task mapping dicts
        """
        if self._pool is None:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                if status:
                    rows = await conn.fetch(
                        """
                        SELECT id, task_id, linear_issue_id, linear_identifier, 
                               agent_name, parent_issue_id, parent_identifier, 
                               status, created_at, updated_at, completed_at
                        FROM task_linear_mappings
                        WHERE agent_name = $1 AND status = $2
                        ORDER BY created_at DESC
                        """,
                        agent_name, status
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT id, task_id, linear_issue_id, linear_identifier, 
                               agent_name, parent_issue_id, parent_identifier, 
                               status, created_at, updated_at, completed_at
                        FROM task_linear_mappings
                        WHERE agent_name = $1
                        ORDER BY created_at DESC
                        """,
                        agent_name
                    )
                
                return [dict(row) for row in rows]
        
        except Exception as e:
            logger.error(f"Failed to get agent tasks: {e}")
            raise
    
    async def get_parent_subtasks(
        self, 
        parent_identifier: str
    ) -> List[Dict[str, Any]]:
        """Get all sub-tasks for parent Linear issue.
        
        Args:
            parent_identifier: Parent Linear issue identifier (e.g., "PR-68")
        
        Returns:
            List of task mapping dicts
        """
        if self._pool is None:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT id, task_id, linear_issue_id, linear_identifier, 
                           agent_name, parent_issue_id, parent_identifier, 
                           status, created_at, updated_at, completed_at
                    FROM task_linear_mappings
                    WHERE parent_identifier = $1
                    ORDER BY created_at DESC
                    """,
                    parent_identifier
                )
                
                return [dict(row) for row in rows]
        
        except Exception as e:
            logger.error(f"Failed to get parent subtasks: {e}")
            raise
    
    async def get_completion_stats(
        self, 
        agent_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get task completion statistics.
        
        Args:
            agent_name: Optional agent name filter
        
        Returns:
            Dict with total_tasks, completed, in_progress, completion_rate
        """
        if self._pool is None:
            await self.connect()
        
        try:
            async with self._pool.acquire() as conn:
                if agent_name:
                    row = await conn.fetchrow(
                        """
                        SELECT 
                            COUNT(*) as total_tasks,
                            SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as completed,
                            SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                            SUM(CASE WHEN status = 'canceled' THEN 1 ELSE 0 END) as canceled,
                            ROUND(100.0 * SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) / 
                                  NULLIF(COUNT(*), 0), 2) as completion_rate
                        FROM task_linear_mappings
                        WHERE agent_name = $1
                        """,
                        agent_name
                    )
                else:
                    row = await conn.fetchrow(
                        """
                        SELECT 
                            COUNT(*) as total_tasks,
                            SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as completed,
                            SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
                            SUM(CASE WHEN status = 'canceled' THEN 1 ELSE 0 END) as canceled,
                            ROUND(100.0 * SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) / 
                                  NULLIF(COUNT(*), 0), 2) as completion_rate
                        FROM task_linear_mappings
                        """
                    )
                
                return dict(row) if row else {
                    "total_tasks": 0,
                    "completed": 0,
                    "in_progress": 0,
                    "canceled": 0,
                    "completion_rate": 0.0
                }
        
        except Exception as e:
            logger.error(f"Failed to get completion stats: {e}")
            raise


# Singleton instance
_state_client: Optional[StateClient] = None


def get_state_client() -> StateClient:
    """Get or create singleton state client instance.
    
    Returns:
        StateClient instance
    """
    global _state_client
    if _state_client is None:
        _state_client = StateClient()
    return _state_client
