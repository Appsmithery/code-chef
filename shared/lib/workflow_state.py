"""
Workflow State Management for Multi-Agent Collaboration.

Provides CRUD operations for workflow state persistence, checkpointing,
and recovery. Integrates with LangGraph for stateful multi-agent workflows.

Usage:
    from shared.lib.workflow_state import WorkflowStateManager
    
    state_mgr = WorkflowStateManager(db_conn_string)
    
    # Create workflow
    workflow_id = await state_mgr.create_workflow(
        workflow_type="pr_deployment",
        initial_state={"pr_number": 123},
        participating_agents=["orchestrator", "code-review"]
    )
    
    # Update state
    await state_mgr.update_state(
        workflow_id=workflow_id,
        updates={"current_step": "testing"},
        agent_id="cicd"
    )
    
    # Create checkpoint
    await state_mgr.checkpoint(
        workflow_id=workflow_id,
        step_name="code_review",
        agent_id="code-review",
        data={"review_comments": [...]}
    )
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import asyncpg
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class WorkflowStatus:
    """Workflow status constants."""
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CheckpointStatus:
    """Checkpoint status constants."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class WorkflowState(BaseModel):
    """Workflow state model."""
    workflow_id: str
    workflow_type: str
    current_step: str
    state_data: Dict[str, Any]
    participating_agents: List[str]
    started_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowCheckpoint(BaseModel):
    """Workflow checkpoint model."""
    checkpoint_id: int
    workflow_id: str
    step_name: str
    agent_id: str
    checkpoint_data: Dict[str, Any]
    created_at: datetime
    duration_ms: Optional[int] = None
    status: str


class WorkflowStateManager:
    """
    Manager for workflow state persistence and checkpointing.
    
    Provides high-level operations for multi-agent workflow coordination:
    - Create/read/update workflows
    - Create/restore checkpoints
    - Query workflow status
    - Cleanup old workflows
    """
    
    def __init__(self, db_conn_string: str):
        """
        Initialize workflow state manager.
        
        Args:
            db_conn_string: PostgreSQL connection string
                Format: postgresql://user:pass@host:port/dbname
        """
        self.db_conn_string = db_conn_string
        self.pool: Optional[asyncpg.Pool] = None
        
    async def connect(self):
        """Establish database connection pool."""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                self.db_conn_string,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("WorkflowStateManager connected to PostgreSQL")
    
    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("WorkflowStateManager disconnected from PostgreSQL")
    
    async def create_workflow(
        self,
        workflow_type: str,
        initial_state: Dict[str, Any],
        participating_agents: List[str],
        workflow_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create new workflow with initial state.
        
        Args:
            workflow_type: Type of workflow (e.g., "pr_deployment")
            initial_state: Initial state data
            participating_agents: List of agent IDs involved
            workflow_id: Optional custom workflow ID (auto-generated if None)
            metadata: Optional workflow metadata
        
        Returns:
            workflow_id: Unique workflow identifier
        """
        workflow_id = workflow_id or f"wf-{uuid4().hex[:12]}"
        now = datetime.utcnow()  # asyncpg expects naive UTC datetime
        
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO workflow_state (
                    workflow_id, workflow_type, current_step, state_data,
                    participating_agents, started_at, updated_at, status, metadata
                ) VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9::jsonb)
                """,
                workflow_id,
                workflow_type,
                "initialized",
                json.dumps(initial_state),
                participating_agents,
                now,
                now,
                WorkflowStatus.RUNNING,
                json.dumps(metadata or {})
            )
        
        logger.info(f"Created workflow {workflow_id} ({workflow_type})")
        return workflow_id
    
    async def get_workflow(self, workflow_id: str) -> Optional[WorkflowState]:
        """
        Get workflow by ID.
        
        Args:
            workflow_id: Workflow identifier
        
        Returns:
            WorkflowState or None if not found
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM workflow_state WHERE workflow_id = $1
                """,
                workflow_id
            )
        
        if not row:
            return None
        
        # Convert row to dict and parse JSON fields
        data = dict(row)
        if isinstance(data.get('state_data'), str):
            data['state_data'] = json.loads(data['state_data'])
        if isinstance(data.get('metadata'), str):
            data['metadata'] = json.loads(data['metadata'])
        
        return WorkflowState(**data)
    
    async def update_state(
        self,
        workflow_id: str,
        updates: Dict[str, Any],
        agent_id: Optional[str] = None
    ):
        """
        Update workflow state.
        
        Args:
            workflow_id: Workflow identifier
            updates: State updates to apply (merged with existing state)
            agent_id: Agent performing the update (for audit trail)
        """
        async with self.pool.acquire() as conn:
            # Get current state
            current_state_raw = await conn.fetchval(
                "SELECT state_data FROM workflow_state WHERE workflow_id = $1",
                workflow_id
            )
            
            if current_state_raw is None:
                raise ValueError(f"Workflow {workflow_id} not found")
            
            # Parse JSON if needed
            current_state = json.loads(current_state_raw) if isinstance(current_state_raw, str) else current_state_raw
            
            # Merge updates
            new_state = {**current_state, **updates}
            
            # Update database
            await conn.execute(
                """
                UPDATE workflow_state
                SET state_data = $1::jsonb, updated_at = $2
                WHERE workflow_id = $3
                """,
                json.dumps(new_state),
                datetime.utcnow(),
                workflow_id
            )
        
        logger.info(f"Updated workflow {workflow_id} state (by {agent_id or 'system'})")
    
    async def update_step(
        self,
        workflow_id: str,
        current_step: str,
        agent_id: Optional[str] = None
    ):
        """
        Update workflow current step.
        
        Args:
            workflow_id: Workflow identifier
            current_step: New current step name
            agent_id: Agent performing the update
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE workflow_state
                SET current_step = $1, updated_at = $2
                WHERE workflow_id = $3
                """,
                current_step,
                datetime.utcnow(),
                workflow_id
            )
        
        logger.info(f"Workflow {workflow_id} advanced to step: {current_step}")
    
    async def complete_workflow(
        self,
        workflow_id: str,
        final_state: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ):
        """
        Mark workflow as completed or failed.
        
        Args:
            workflow_id: Workflow identifier
            final_state: Optional final state updates
            error_message: Error message if workflow failed
        """
        status = WorkflowStatus.FAILED if error_message else WorkflowStatus.COMPLETED
        now = datetime.utcnow()
        
        async with self.pool.acquire() as conn:
            if final_state:
                await conn.execute(
                    """
                    UPDATE workflow_state
                    SET state_data = state_data || $1::jsonb,
                        status = $2,
                        completed_at = $3,
                        updated_at = $3,
                        error_message = $4
                    WHERE workflow_id = $5
                    """,
                    json.dumps(final_state),
                    status,
                    now,
                    error_message,
                    workflow_id
                )
            else:
                await conn.execute(
                    """
                    UPDATE workflow_state
                    SET status = $1,
                        completed_at = $2,
                        updated_at = $2,
                        error_message = $3
                    WHERE workflow_id = $4
                    """,
                    status,
                    now,
                    error_message,
                    workflow_id
                )
        
        logger.info(f"Workflow {workflow_id} {status}: {error_message or 'success'}")
    
    async def checkpoint(
        self,
        workflow_id: str,
        step_name: str,
        agent_id: str,
        data: Dict[str, Any],
        duration_ms: Optional[int] = None,
        status: str = CheckpointStatus.SUCCESS
    ) -> int:
        """
        Create checkpoint at current workflow step.
        
        Args:
            workflow_id: Workflow identifier
            step_name: Name of the step being checkpointed
            agent_id: Agent creating the checkpoint
            data: Checkpoint data (step results, intermediate state)
            duration_ms: Step execution duration in milliseconds
            status: Checkpoint status (success, error, timeout, skipped)
        
        Returns:
            checkpoint_id: Unique checkpoint identifier
        """
        async with self.pool.acquire() as conn:
            checkpoint_id = await conn.fetchval(
                """
                INSERT INTO workflow_checkpoints (
                    workflow_id, step_name, agent_id, checkpoint_data,
                    created_at, duration_ms, status
                ) VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7)
                RETURNING checkpoint_id
                """,
                workflow_id,
                step_name,
                agent_id,
                json.dumps(data),
                datetime.utcnow(),
                duration_ms,
                status
            )
        
        logger.info(
            f"Checkpoint created: workflow={workflow_id}, "
            f"step={step_name}, agent={agent_id}, id={checkpoint_id}"
        )
        return checkpoint_id
    
    async def get_checkpoints(
        self,
        workflow_id: str,
        limit: int = 100
    ) -> List[WorkflowCheckpoint]:
        """
        Get checkpoints for workflow.
        
        Args:
            workflow_id: Workflow identifier
            limit: Maximum number of checkpoints to return
        
        Returns:
            List of WorkflowCheckpoint objects (newest first)
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM workflow_checkpoints
                WHERE workflow_id = $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                workflow_id,
                limit
            )
        
        # Parse JSON fields
        result = []
        for row in rows:
            data = dict(row)
            if isinstance(data.get('checkpoint_data'), str):
                data['checkpoint_data'] = json.loads(data['checkpoint_data'])
            result.append(WorkflowCheckpoint(**data))
        
        return result
    
    async def get_latest_checkpoint(
        self,
        workflow_id: str
    ) -> Optional[WorkflowCheckpoint]:
        """
        Get most recent checkpoint for workflow.
        
        Args:
            workflow_id: Workflow identifier
        
        Returns:
            WorkflowCheckpoint or None if no checkpoints exist
        """
        checkpoints = await self.get_checkpoints(workflow_id, limit=1)
        return checkpoints[0] if checkpoints else None
    
    async def restore_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: int
    ) -> Dict[str, Any]:
        """
        Restore workflow to specific checkpoint.
        
        Args:
            workflow_id: Workflow identifier
            checkpoint_id: Checkpoint to restore
        
        Returns:
            Checkpoint data
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM workflow_checkpoints
                WHERE workflow_id = $1 AND checkpoint_id = $2
                """,
                workflow_id,
                checkpoint_id
            )
            
            if not row:
                raise ValueError(
                    f"Checkpoint {checkpoint_id} not found for workflow {workflow_id}"
                )
            
            # Update workflow to checkpoint state
            await conn.execute(
                """
                UPDATE workflow_state
                SET current_step = $1,
                    state_data = state_data || $2::jsonb,
                    updated_at = $3
                WHERE workflow_id = $4
                """,
                row["step_name"],
                row["checkpoint_data"],
                datetime.utcnow(),
                workflow_id
            )
        
        logger.info(f"Restored workflow {workflow_id} to checkpoint {checkpoint_id}")
        return dict(row["checkpoint_data"])
    
    async def list_active_workflows(self) -> List[WorkflowState]:
        """
        List all active (running/paused) workflows.
        
        Returns:
            List of active WorkflowState objects
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM workflow_state
                WHERE status IN ($1, $2)
                ORDER BY started_at DESC
                """,
                WorkflowStatus.RUNNING,
                WorkflowStatus.PAUSED
            )
        
        # Parse JSON fields
        result = []
        for row in rows:
            data = dict(row)
            if isinstance(data.get('state_data'), str):
                data['state_data'] = json.loads(data['state_data'])
            if isinstance(data.get('metadata'), str):
                data['metadata'] = json.loads(data['metadata'])
            result.append(WorkflowState(**data))
        
        return result
    
    async def get_workflow_statistics(self) -> List[Dict[str, Any]]:
        """
        Get workflow execution statistics by type.
        
        Returns:
            List of workflow statistics dictionaries
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM workflow_statistics")
        
        return [dict(row) for row in rows]
    
    async def cleanup_old_workflows(self, days: int = 30) -> int:
        """
        Delete completed workflows older than specified days.
        
        Args:
            days: Age threshold in days
        
        Returns:
            Number of workflows deleted
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchval("SELECT cleanup_old_workflows()")
        
        logger.info(f"Cleaned up {result} old workflows")
        return result


# Singleton instance (optional - can be instantiated per-use)
_state_manager: Optional[WorkflowStateManager] = None


def get_workflow_state_manager(db_conn_string: str) -> WorkflowStateManager:
    """
    Get singleton WorkflowStateManager instance.
    
    Args:
        db_conn_string: PostgreSQL connection string
    
    Returns:
        WorkflowStateManager instance
    """
    global _state_manager
    if _state_manager is None:
        _state_manager = WorkflowStateManager(db_conn_string)
    return _state_manager
