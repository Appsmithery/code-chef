"""
Distributed Resource Locking for Multi-Agent Coordination

Provides a PostgreSQL-based distributed lock manager using advisory locks
to prevent concurrent modification conflicts when multiple agents access
shared resources (files, state, etc.).

Usage:
    from shared.lib.resource_lock import ResourceLockManager
    
    # Initialize with DB connection string
    lock_manager = ResourceLockManager(db_conn_string, event_bus)
    await lock_manager.connect()
    
    # Acquire lock
    try:
        async with lock_manager.acquire("file:shared/config.yaml", "agent-feature-dev"):
            # Modify resource safely
            await modify_file()
    except ResourceLockError:
        # Handle lock contention
        print("Resource is busy")
"""

import asyncio
import logging
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, Any, Dict

import asyncpg

logger = logging.getLogger(__name__)

class ResourceLockError(Exception):
    """Raised when a lock cannot be acquired."""
    pass

class ResourceLockManager:
    def __init__(self, db_conn_string: str, event_bus: Any = None):
        """
        Initialize lock manager.
        
        Args:
            db_conn_string: PostgreSQL connection string
            event_bus: Optional EventBus for emitting lock events
        """
        self.db_conn_string = db_conn_string
        self.event_bus = event_bus
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        """Establish database connection pool."""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                self.db_conn_string,
                min_size=2,
                max_size=10
            )
            logger.info("ResourceLockManager connected to PostgreSQL")

    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("ResourceLockManager disconnected from PostgreSQL")

    @asynccontextmanager
    async def acquire(
        self, 
        resource_id: str, 
        agent_id: str, 
        timeout: int = 300, 
        wait_timeout: int = 0,
        reason: str = None,
        metadata: Dict[str, Any] = None
    ):
        """
        Acquire distributed lock with timeout.
        
        Args:
            resource_id: Unique identifier for the resource
            agent_id: ID of the agent requesting the lock
            timeout: Lock expiration time in seconds (default 300)
            wait_timeout: How long to wait for lock if busy (default 0 = fail immediately)
            reason: Reason for acquiring the lock
            metadata: Additional metadata
            
        Raises:
            ResourceLockError: If lock cannot be acquired within wait_timeout
        """
        if not self.pool:
            await self.connect()

        start_time = datetime.utcnow()
        lock_acquired = False
        
        try:
            # Try to acquire lock loop
            while True:
                async with self.pool.acquire() as conn:
                    # Call stored procedure
                    row = await conn.fetchrow(
                        """
                        SELECT * FROM acquire_resource_lock($1, $2, $3, $4, $5::jsonb)
                        """,
                        resource_id,
                        agent_id,
                        timeout,
                        reason,
                        json.dumps(metadata or {})
                    )
                    
                    if row['success']:
                        lock_acquired = True
                        break
                
                # Check if we should keep waiting
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed >= wait_timeout:
                    break
                    
                await asyncio.sleep(0.5)

            if not lock_acquired:
                # Get current owner info
                owner_info = await self.get_lock_info(resource_id)
                owner = owner_info.get('agent_id', 'unknown') if owner_info else 'unknown'
                
                logger.warning(f"Agent {agent_id} failed to acquire lock on {resource_id} (held by {owner})")
                raise ResourceLockError(f"Resource {resource_id} is locked by {owner}")

            # Emit lock event
            if self.event_bus:
                await self.event_bus.emit("resource.locked", {
                    "resource_id": resource_id,
                    "agent_id": agent_id,
                    "expires_at": (datetime.utcnow() + timedelta(seconds=timeout)).isoformat()
                })
            
            logger.debug(f"Agent {agent_id} acquired lock on {resource_id}")

            yield  # Context manager body executes

        finally:
            if lock_acquired:
                await self.release(resource_id, agent_id)

    async def release(self, resource_id: str, agent_id: str):
        """Release a resource lock."""
        if not self.pool:
            return

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM release_resource_lock($1, $2)",
                    resource_id,
                    agent_id
                )
                
                if row and row['success']:
                    if self.event_bus:
                        await self.event_bus.emit("resource.unlocked", {
                            "resource_id": resource_id,
                            "agent_id": agent_id
                        })
                    logger.debug(f"Agent {agent_id} released lock on {resource_id}")
                else:
                    msg = row['message'] if row else "Unknown error"
                    logger.warning(f"Failed to release lock {resource_id}: {msg}")
        except Exception as e:
            logger.error(f"Error releasing lock {resource_id}: {e}")

    async def is_locked(self, resource_id: str) -> bool:
        """Check if resource is locked."""
        info = await self.get_lock_info(resource_id)
        return info is not None and info.get('is_locked', False)
        
    async def get_lock_info(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """Get current lock info."""
        if not self.pool:
            await self.connect()
            
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM check_lock_status($1)",
                resource_id
            )
            if row and row['is_locked']:
                return dict(row)
        return None

    async def force_unlock(self, resource_id: str, admin_agent_id: str = "admin"):
        """Force unlock a resource (admin/cleanup only)."""
        if not self.pool:
            await self.connect()
            
        async with self.pool.acquire() as conn:
            await conn.execute(
                "SELECT * FROM force_release_lock($1, $2)",
                resource_id,
                admin_agent_id
            )
        
        if self.event_bus:
            await self.event_bus.emit("resource.unlocked", {
                "resource_id": resource_id,
                "agent_id": admin_agent_id,
                "reason": "force_unlock"
            })
