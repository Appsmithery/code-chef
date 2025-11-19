"""
Workflow State Persistence with Optimistic Locking

Handles persistence of MultiAgentState to the workflow_state table
with optimistic locking to prevent concurrent modification conflicts.
"""

import json
import logging
import os
from typing import Optional, Dict, Any
import asyncpg
from datetime import datetime

from .state import MultiAgentState

logger = logging.getLogger(__name__)

class OptimisticLockError(Exception):
    """Raised when a state update fails due to version mismatch."""
    pass

class WorkflowPersistence:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or self._get_db_url()
        self.pool: Optional[asyncpg.Pool] = None

    def _get_db_url(self) -> str:
        host = os.getenv("POSTGRES_HOST", "postgres")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "devtools")
        user = os.getenv("POSTGRES_USER", "devtools")
        password = os.getenv("POSTGRES_PASSWORD", "changeme")
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"

    async def initialize(self):
        """Initialize database connection pool."""
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.db_url)

    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None

    async def load_state(self, task_id: str) -> Optional[MultiAgentState]:
        """
        Load workflow state by task ID.
        
        Returns:
            MultiAgentState dict or None if not found
        """
        if not self.pool:
            await self.initialize()

        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT state_data, version, updated_at
                FROM workflow_state
                WHERE task_id = $1
                """,
                task_id
            )

            if not row:
                return None

            state_data = json.loads(row["state_data"])
            # Inject version for optimistic locking
            state_data["_version"] = row["version"]
            state_data["updated_at"] = row["updated_at"]
            
            return state_data

    async def save_state(self, task_id: str, state: Dict[str, Any], version: int):
        """
        Persist state with optimistic locking.
        
        Args:
            task_id: Unique task identifier
            state: State dictionary to save
            version: Expected current version (for optimistic locking)
            
        Raises:
            OptimisticLockError: If version mismatch (concurrent modification)
        """
        if not self.pool:
            await self.initialize()

        # Remove _version from state_data before saving to avoid duplication/confusion
        state_to_save = state.copy()
        if "_version" in state_to_save:
            del state_to_save["_version"]

        async with self.pool.acquire() as conn:
            # Try to insert or update with version check
            result = await conn.execute(
                """
                INSERT INTO workflow_state (
                    task_id, workflow_type, current_step, state_data, 
                    participating_agents, started_at, updated_at, status, version
                )
                VALUES ($1, $2, $3, $4, $5, $6, NOW(), $7, 1)
                ON CONFLICT (task_id) DO UPDATE
                SET state_data = $4,
                    current_step = $3,
                    participating_agents = $5,
                    status = $7,
                    version = workflow_state.version + 1,
                    updated_at = NOW()
                WHERE workflow_state.version = $8
                """,
                task_id,
                state.get("workflow_type", "unknown"),
                state.get("current_step", "unknown"),
                json.dumps(state_to_save, default=str),
                state.get("participating_agents", []),
                state.get("started_at", datetime.utcnow()),
                state.get("status", "running"),
                version
            )

            if result == "INSERT 0 0" or result == "UPDATE 0":
                # Check if it failed because of version mismatch or just didn't exist (for update)
                # But ON CONFLICT handles insert vs update.
                # If UPDATE 0, it means the WHERE clause failed (version mismatch)
                # If INSERT 0 0, that's weird for ON CONFLICT... usually it's INSERT 0 1
                
                # Let's check if record exists to confirm version mismatch
                current = await conn.fetchrow(
                    "SELECT version FROM workflow_state WHERE task_id = $1",
                    task_id
                )
                
                if current:
                    raise OptimisticLockError(
                        f"Version mismatch for task {task_id}. "
                        f"Expected {version}, found {current['version']}"
                    )
                else:
                    # Should have inserted... unless something else failed
                    raise Exception(f"Failed to save state for {task_id}: {result}")

            logger.debug(f"Saved state for task {task_id} (v{version} -> v{version+1})")

    async def create_checkpoint(self, task_id: str, step_name: str, agent_id: str, data: Dict[str, Any]):
        """Create a historical checkpoint."""
        if not self.pool:
            await self.initialize()

        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO workflow_checkpoints (
                    workflow_id, step_name, agent_id, checkpoint_data, status
                )
                VALUES ($1, $2, $3, $4, 'success')
                """,
                task_id, step_name, agent_id, json.dumps(data, default=str)
            )
