"""
Resource Lock Manager for Multi-Agent Coordination.

Implements distributed locking using PostgreSQL advisory locks with
automatic retry, timeout handling, and observability.

Usage:
    from shared.lib.resource_lock_manager import ResourceLockManager
    
    lock_mgr = ResourceLockManager(db_conn_string)
    await lock_mgr.connect()
    
    # Context manager (recommended - auto-release)
    async with lock_mgr.lock("deployment:prod", "cicd-agent"):
        await deploy_to_production()
    
    # Manual acquire/release
    acquired = await lock_mgr.acquire_lock("config:prod.yaml", "infra-agent")
    if acquired:
        try:
            await update_config()
        finally:
            await lock_mgr.release_lock("config:prod.yaml", "infra-agent")
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import asyncpg
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LockStatus(BaseModel):
    """Lock status information."""
    is_locked: bool
    owner_agent_id: Optional[str] = None
    acquired_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    seconds_remaining: Optional[int] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LockAcquisitionResult(BaseModel):
    """Result of lock acquisition attempt."""
    success: bool
    lock_acquired: bool
    message: str
    wait_time_ms: int


class ResourceLockManager:
    """
    Manager for distributed resource locking using PostgreSQL advisory locks.
    
    Features:
    - Automatic retry with exponential backoff
    - Timeout enforcement
    - Context manager for auto-release
    - Lock contention metrics
    - Deadlock prevention
    """
    
    def __init__(
        self,
        db_conn_string: str,
        default_timeout: int = 300,
        retry_delays: List[float] = None
    ):
        """
        Initialize resource lock manager.
        
        Args:
            db_conn_string: PostgreSQL connection string
            default_timeout: Default lock timeout in seconds (300 = 5 minutes)
            retry_delays: Exponential backoff delays for retries (seconds)
        """
        self.db_conn_string = db_conn_string
        self.default_timeout = default_timeout
        self.retry_delays = retry_delays or [1, 2, 4, 8, 16]  # Exponential backoff
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
            logger.info("ResourceLockManager connected to PostgreSQL")
    
    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("ResourceLockManager disconnected from PostgreSQL")
    
    async def acquire_lock(
        self,
        resource_id: str,
        agent_id: str,
        timeout_seconds: Optional[int] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        retry: bool = True,
        wait: bool = True
    ) -> bool:
        """
        Acquire exclusive lock on resource.
        
        Args:
            resource_id: Resource identifier (e.g., "deployment:prod")
            agent_id: Agent requesting lock
            timeout_seconds: Lock timeout (auto-release after this)
            reason: Human-readable reason for lock
            metadata: Additional context
            retry: Whether to retry on failure with exponential backoff
            wait: Whether to wait for lock or return immediately
        
        Returns:
            True if lock acquired, False otherwise
        """
        timeout_seconds = timeout_seconds or self.default_timeout
        metadata = metadata or {}
        
        async with self.pool.acquire() as conn:
            # Try to acquire lock (asyncpg requires JSON string for JSONB)
            result = await conn.fetchrow(
                """
                SELECT * FROM acquire_resource_lock($1, $2, $3, $4, $5)
                """,
                resource_id,
                agent_id,
                timeout_seconds,
                reason,
                json.dumps(metadata)
            )
            
            if result['lock_acquired']:
                logger.info(
                    f"Lock acquired: resource={resource_id}, agent={agent_id}, "
                    f"wait_time={result['wait_time_ms']}ms"
                )
                return True
            
            # Lock not acquired - retry if enabled
            if not retry or not wait:
                logger.warning(
                    f"Lock acquisition failed: resource={resource_id}, agent={agent_id}, "
                    f"message={result['message']}"
                )
                return False
            
            # Retry with exponential backoff
            for attempt, delay in enumerate(self.retry_delays, 1):
                logger.info(
                    f"Lock busy, retrying in {delay}s (attempt {attempt}/{len(self.retry_delays)}): "
                    f"resource={resource_id}, agent={agent_id}"
                )
                await asyncio.sleep(delay)
                
                # Try again (asyncpg requires JSON string for JSONB)
                result = await conn.fetchrow(
                    """
                    SELECT * FROM acquire_resource_lock($1, $2, $3, $4, $5)
                    """,
                    resource_id,
                    agent_id,
                    timeout_seconds,
                    reason,
                    json.dumps(metadata)
                )
                
                if result['lock_acquired']:
                    logger.info(
                        f"Lock acquired on retry {attempt}: resource={resource_id}, "
                        f"agent={agent_id}, wait_time={result['wait_time_ms']}ms"
                    )
                    return True
            
            # All retries exhausted
            logger.error(
                f"Lock acquisition failed after {len(self.retry_delays)} retries: "
                f"resource={resource_id}, agent={agent_id}"
            )
            return False
    
    async def release_lock(
        self,
        resource_id: str,
        agent_id: str
    ) -> bool:
        """
        Release lock on resource.
        
        Args:
            resource_id: Resource identifier
            agent_id: Agent releasing lock
        
        Returns:
            True if lock released, False if not owned or already released
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT * FROM release_resource_lock($1, $2)
                """,
                resource_id,
                agent_id
            )
            
            if result['success']:
                logger.info(
                    f"Lock released: resource={resource_id}, agent={agent_id}"
                )
                return True
            else:
                logger.warning(
                    f"Lock release failed: resource={resource_id}, agent={agent_id}, "
                    f"message={result['message']}"
                )
                return False
    
    async def check_lock_status(
        self,
        resource_id: str
    ) -> LockStatus:
        """
        Check if resource is locked and get lock details.
        
        Args:
            resource_id: Resource identifier
        
        Returns:
            LockStatus with current lock information
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT * FROM check_lock_status($1)
                """,
                resource_id
            )
            
            if result is None or not result['is_locked']:
                return LockStatus(is_locked=False)
            
            # Parse metadata (comes as JSON string from database)
            metadata = result['metadata']
            if isinstance(metadata, str):
                metadata = json.loads(metadata) if metadata else {}
            
            return LockStatus(
                is_locked=result['is_locked'],
                owner_agent_id=result['owner_agent_id'],
                acquired_at=result['acquired_at'],
                expires_at=result['expires_at'],
                seconds_remaining=result['seconds_remaining'],
                reason=result['reason'],
                metadata=metadata or {}
            )
    
    async def list_active_locks(self) -> List[Dict[str, Any]]:
        """
        List all active locks.
        
        Returns:
            List of active lock information
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM active_locks_view
                """
            )
            return [dict(row) for row in rows]
    
    async def get_lock_statistics(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get lock statistics for past N hours.
        
        Args:
            hours: Number of hours to look back
        
        Returns:
            List of lock statistics by resource
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM lock_statistics_view
                """
            )
            return [dict(row) for row in rows]
    
    async def get_lock_contention(self) -> List[Dict[str, Any]]:
        """
        Get lock contention metrics.
        
        Returns:
            List of resources with lock contention
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM lock_contention_view
                """
            )
            return [dict(row) for row in rows]
    
    async def get_wait_queue(self) -> List[Dict[str, Any]]:
        """
        Get current wait queue.
        
        Returns:
            List of agents waiting for locks
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM wait_queue_view
                """
            )
            return [dict(row) for row in rows]
    
    async def force_release_lock(
        self,
        resource_id: str,
        admin_agent_id: str = "admin"
    ) -> bool:
        """
        Forcefully release a lock (admin operation).
        
        Args:
            resource_id: Resource identifier
            admin_agent_id: ID of admin agent forcing release
        
        Returns:
            True if lock forcefully released
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT * FROM force_release_lock($1, $2)
                """,
                resource_id,
                admin_agent_id
            )
            
            if result['success']:
                logger.warning(
                    f"Lock forcefully released: resource={resource_id}, "
                    f"admin={admin_agent_id}, previous_owner={result['previous_owner']}"
                )
                return True
            else:
                logger.error(
                    f"Force release failed: resource={resource_id}, "
                    f"message={result['message']}"
                )
                return False
    
    async def cleanup_expired_locks(self) -> int:
        """
        Clean up expired locks.
        
        Returns:
            Number of locks cleaned up
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(
                """
                SELECT * FROM cleanup_expired_locks()
                """
            )
            
            count = result['cleaned_count']
            if count > 0:
                logger.info(
                    f"Cleaned up {count} expired locks: {result['resource_ids']}"
                )
            return count
    
    @asynccontextmanager
    async def lock(
        self,
        resource_id: str,
        agent_id: str,
        timeout_seconds: Optional[int] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        retry: bool = True
    ):
        """
        Context manager for automatic lock acquisition and release.
        
        Usage:
            async with lock_mgr.lock("deployment:prod", "cicd-agent"):
                await deploy_to_production()
        
        Args:
            resource_id: Resource identifier
            agent_id: Agent requesting lock
            timeout_seconds: Lock timeout
            reason: Reason for lock
            metadata: Additional context
            retry: Whether to retry on failure
        
        Raises:
            RuntimeError: If lock cannot be acquired
        """
        acquired = await self.acquire_lock(
            resource_id=resource_id,
            agent_id=agent_id,
            timeout_seconds=timeout_seconds,
            reason=reason,
            metadata=metadata,
            retry=retry
        )
        
        if not acquired:
            raise RuntimeError(
                f"Failed to acquire lock: resource={resource_id}, agent={agent_id}"
            )
        
        try:
            yield
        finally:
            await self.release_lock(resource_id, agent_id)


# Singleton instance (optional)
_lock_manager: Optional[ResourceLockManager] = None


def get_resource_lock_manager(db_conn_string: str) -> ResourceLockManager:
    """
    Get singleton ResourceLockManager instance.
    
    Args:
        db_conn_string: PostgreSQL connection string
    
    Returns:
        ResourceLockManager instance
    """
    global _lock_manager
    if _lock_manager is None:
        _lock_manager = ResourceLockManager(db_conn_string)
    return _lock_manager
