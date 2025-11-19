# Distributed Resource Locking

To prevent concurrent modification conflicts when multiple agents access shared resources (files, state, configuration), the system implements a distributed locking mechanism using Redis.

## Overview

- **Implementation**: `shared.lib.resource_lock.ResourceLockManager`
- **Backend**: Redis (SET NX EX)
- **Events**: Emits `resource.locked` and `resource.unlocked` events via EventBus.

## Usage

### Acquiring a Lock

Use the `acquire` async context manager. It handles acquisition, expiration, and release automatically.

```python
from shared.lib.resource_lock import ResourceLockManager

lock_manager = ResourceLockManager(redis_client, event_bus)

try:
    # Try to acquire lock for 30 seconds
    async with lock_manager.acquire(
        resource_id="file:src/main.py",
        agent_id="agent-feature-dev",
        timeout=30,
        wait_timeout=5  # Wait up to 5s if busy
    ):
        # Critical section: Modify the file
        await modify_file("src/main.py")

except ResourceLockError:
    print("Could not acquire lock - resource is busy")
```

### Checking Lock Status

```python
if await lock_manager.is_locked("file:src/main.py"):
    owner = await lock_manager.get_owner("file:src/main.py")
    print(f"File is currently locked by {owner}")
```

## Lock Semantics

1.  **Mutual Exclusion**: Only one agent can hold a lock on a `resource_id` at a time.
2.  **TTL (Time To Live)**: Locks automatically expire after the `timeout` period to prevent deadlocks if an agent crashes.
3.  **Ownership**: Only the agent that acquired the lock can release it (enforced via unique tokens).
4.  **Reentrancy**: Not currently supported (an agent cannot re-acquire a lock it already holds without releasing it first).

## Best Practices

- **Granularity**: Lock specific resources (e.g., individual files) rather than broad categories (e.g., "codebase") to maximize concurrency.
- **Timeouts**: Keep lock duration short. If a task takes a long time, consider breaking it down or refreshing the lock (refresh not yet implemented).
- **Error Handling**: Always handle `ResourceLockError`. Retry with exponential backoff if appropriate.
