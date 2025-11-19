"""
Distributed Resource Locking for Multi-Agent Coordination

Provides a Redis-based distributed lock manager to prevent concurrent modification
conflicts when multiple agents access shared resources (files, state, etc.).

Usage:
    from shared.lib.resource_lock import ResourceLockManager
    
    # Initialize with Redis client
    lock_manager = ResourceLockManager(redis_client, event_bus)
    
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
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, Any

logger = logging.getLogger(__name__)

class ResourceLockError(Exception):
    """Raised when a lock cannot be acquired."""
    pass

class ResourceLockManager:
    def __init__(self, redis_client: Any, event_bus: Any = None):
        """
        Initialize lock manager.
        
        Args:
            redis_client: Async Redis client instance
            event_bus: Optional EventBus for emitting lock events
        """
        self.redis = redis_client
        self.event_bus = event_bus

    @asynccontextmanager
    async def acquire(
        self, 
        resource_id: str, 
        agent_id: str, 
        timeout: int = 300, 
        wait_timeout: int = 0
    ):
        """
        Acquire distributed lock with timeout.
        
        Args:
            resource_id: Unique identifier for the resource (e.g., "file:path/to/file")
            agent_id: ID of the agent requesting the lock
            timeout: Lock expiration time in seconds (default 300)
            wait_timeout: How long to wait for lock if busy (default 0 = fail immediately)
            
        Raises:
            ResourceLockError: If lock cannot be acquired within wait_timeout
        """
        if not self.redis:
            logger.warning("Redis client not available, skipping lock acquisition (unsafe mode)")
            yield "mock-lock"
            return

        lock_key = f"lock:{resource_id}"
        # Value includes agent_id and unique token to prevent accidental release of others' locks
        lock_token = str(uuid.uuid4())
        lock_value = f"{agent_id}:{lock_token}"
        lock_acquired = False
        
        start_time = datetime.utcnow()
        
        try:
            # Try to acquire lock loop
            while True:
                # SET NX (Not Exists) EX (Expire)
                lock_acquired = await self.redis.set(
                    lock_key, lock_value, nx=True, ex=timeout
                )
                
                if lock_acquired:
                    break
                    
                # Check if we should keep waiting
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed >= wait_timeout:
                    break
                    
                await asyncio.sleep(0.1)

            if not lock_acquired:
                current_owner_val = await self.redis.get(lock_key)
                current_owner = current_owner_val.split(":")[0] if current_owner_val else "unknown"
                
                logger.warning(f"Agent {agent_id} failed to acquire lock on {resource_id} (held by {current_owner})")
                raise ResourceLockError(f"Resource {resource_id} is locked by {current_owner}")

            # Emit lock event
            if self.event_bus:
                await self.event_bus.emit("resource.locked", {
                    "resource_id": resource_id,
                    "agent_id": agent_id,
                    "expires_at": (datetime.utcnow() + timedelta(seconds=timeout)).isoformat()
                })
            
            logger.debug(f"Agent {agent_id} acquired lock on {resource_id}")

            yield lock_value # Context manager body executes

        finally:
            if lock_acquired:
                # Release lock only if we still own it (Lua script for atomicity)
                # This prevents deleting a lock that expired and was re-acquired by someone else
                release_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("del", KEYS[1])
                else
                    return 0
                end
                """
                try:
                    await self.redis.eval(release_script, 1, lock_key, lock_value)
                    
                    if self.event_bus:
                        await self.event_bus.emit("resource.unlocked", {
                            "resource_id": resource_id,
                            "agent_id": agent_id
                        })
                    logger.debug(f"Agent {agent_id} released lock on {resource_id}")
                except Exception as e:
                    logger.error(f"Error releasing lock {resource_id}: {e}")

    async def is_locked(self, resource_id: str) -> bool:
        """Check if resource is locked."""
        if not self.redis:
            return False
        return await self.redis.exists(f"lock:{resource_id}")
        
    async def get_owner(self, resource_id: str) -> Optional[str]:
        """Get current lock owner."""
        if not self.redis:
            return None
        val = await self.redis.get(f"lock:{resource_id}")
        if val:
            return val.split(":")[0]
        return None

    async def force_unlock(self, resource_id: str, agent_id: str):
        """Force unlock a resource (admin/cleanup only)."""
        if not self.redis:
            return
            
        lock_key = f"lock:{resource_id}"
        await self.redis.delete(lock_key)
        
        if self.event_bus:
            await self.event_bus.emit("resource.unlocked", {
                "resource_id": resource_id,
                "agent_id": agent_id,
                "reason": "force_unlock"
            })
