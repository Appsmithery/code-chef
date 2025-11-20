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

## Complete Usage Examples

### Example 1: File Modification with Lock

```python
from shared.lib.resource_lock import ResourceLockManager, ResourceLockError
from shared.lib.event_bus import get_event_bus
import asyncio

lock_manager = ResourceLockManager(
    db_conn_string="postgresql://user:pass@postgres:5432/devtools",
    event_bus=get_event_bus()
)

await lock_manager.connect()

async def safe_modify_file(file_path: str, agent_id: str, modifications: dict):
    """Safely modify a file with distributed locking."""
    resource_id = f"file:{file_path}"

    try:
        async with lock_manager.acquire(
            resource_id=resource_id,
            agent_id=agent_id,
            timeout=60,  # Lock expires after 60s
            wait_timeout=10,  # Wait up to 10s if busy
            reason=f"Modifying {file_path}",
            metadata={"operation": "modify", "agent": agent_id}
        ):
            # Critical section: Modify file
            print(f"✅ {agent_id} acquired lock on {file_path}")

            # Read current content
            with open(file_path, 'r') as f:
                content = f.read()

            # Apply modifications
            modified_content = apply_modifications(content, modifications)

            # Write back
            with open(file_path, 'w') as f:
                f.write(modified_content)

            print(f"✅ {agent_id} completed modifications to {file_path}")

        # Lock automatically released when exiting context

    except ResourceLockError as e:
        print(f"❌ Could not acquire lock: {e}")
        # Handle contention (retry, fail, queue, etc.)
        raise

# Usage
await safe_modify_file(
    "shared/config.yaml",
    "agent-infrastructure",
    {"timeout": 120}
)
```

### Example 2: Multiple Resource Locking (Ordered to Prevent Deadlock)

```python
async def modify_multiple_files(files: list, agent_id: str):
    """Acquire locks on multiple files in sorted order to prevent deadlock."""

    # CRITICAL: Always acquire locks in the same order to prevent deadlock
    sorted_files = sorted(files)
    resource_ids = [f"file:{f}" for f in sorted_files]

    acquired_locks = []

    try:
        # Acquire all locks in order
        for resource_id in resource_ids:
            try:
                async with lock_manager.acquire(
                    resource_id=resource_id,
                    agent_id=agent_id,
                    timeout=60,
                    wait_timeout=5
                ):
                    acquired_locks.append(resource_id)
                    print(f"✅ Acquired lock on {resource_id}")

                    # Modify file
                    await modify_file(resource_id.replace("file:", ""))

            except ResourceLockError:
                print(f"❌ Failed to acquire lock on {resource_id}")
                raise

        print(f"✅ Modified all {len(sorted_files)} files")

    except Exception as e:
        print(f"❌ Error during multi-file modification: {e}")
        raise

# Usage
await modify_multiple_files(
    ["src/main.py", "src/config.py", "tests/test_main.py"],
    "agent-feature-dev"
)
```

### Example 3: Lock with Retry and Exponential Backoff

```python
async def acquire_with_retry(
    resource_id: str,
    agent_id: str,
    max_retries: int = 3,
    base_delay: float = 1.0
):
    """Acquire lock with exponential backoff retry."""

    for attempt in range(max_retries):
        try:
            async with lock_manager.acquire(
                resource_id=resource_id,
                agent_id=agent_id,
                timeout=60,
                wait_timeout=0  # Don't wait, fail immediately
            ):
                # Critical section
                print(f"✅ Acquired lock on attempt {attempt + 1}")
                await perform_critical_operation()

            return  # Success

        except ResourceLockError:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"⚠️  Lock busy, retrying in {delay}s...")
                await asyncio.sleep(delay)
            else:
                print(f"❌ Failed to acquire lock after {max_retries} attempts")
                raise

# Usage
await acquire_with_retry(
    "file:shared/config.yaml",
    "agent-infrastructure",
    max_retries=3
)
```

### Example 4: Non-Blocking Lock Check

```python
async def conditional_modify(resource_id: str, agent_id: str):
    """Only modify resource if not currently locked."""

    # Check if locked before attempting acquisition
    if await lock_manager.is_locked(resource_id):
        lock_info = await lock_manager.get_lock_info(resource_id)
        print(f"⚠️  Resource locked by {lock_info['agent_id']}, skipping modification")
        return False

    try:
        async with lock_manager.acquire(
            resource_id=resource_id,
            agent_id=agent_id,
            timeout=60,
            wait_timeout=0  # Fail immediately if busy
        ):
            await modify_resource(resource_id)
            print(f"✅ Modified {resource_id}")
            return True

    except ResourceLockError:
        print(f"⚠️  Resource became locked, skipping")
        return False

# Usage
success = await conditional_modify("file:config.yaml", "agent-cicd")
if not success:
    print("Resource busy, will try again later")
```

## Common Patterns

### Pattern 1: Lock with Timeout Extension

```python
async def long_running_operation_with_lock(resource_id: str, agent_id: str):
    """Perform long operation with automatic lock extension."""

    async def extend_lock_periodically(resource_id, agent_id, interval=30):
        """Background task to extend lock every 30s."""
        while True:
            await asyncio.sleep(interval)
            # Note: Lock extension not yet implemented in ResourceLockManager
            # This is a placeholder for future functionality
            print(f"Would extend lock on {resource_id}")

    try:
        async with lock_manager.acquire(resource_id, agent_id, timeout=120):
            # Start background lock extension
            extension_task = asyncio.create_task(
                extend_lock_periodically(resource_id, agent_id)
            )

            try:
                # Perform long operation
                await perform_long_operation()
            finally:
                extension_task.cancel()

    except ResourceLockError as e:
        print(f"Lock acquisition failed: {e}")
```

### Pattern 2: Read/Write Lock Simulation

```python
# Simulate read/write locks using resource_id conventions
async def acquire_read_lock(resource_id: str, agent_id: str):
    """Acquire read lock (multiple readers allowed)."""
    read_lock_id = f"{resource_id}:read:{agent_id}"

    # Check if write lock exists
    write_lock_id = f"{resource_id}:write"
    if await lock_manager.is_locked(write_lock_id):
        raise ResourceLockError(f"Resource has active write lock")

    # Acquire read lock (multiple can coexist)
    async with lock_manager.acquire(read_lock_id, agent_id, timeout=300):
        yield

async def acquire_write_lock(resource_id: str, agent_id: str):
    """Acquire write lock (exclusive)."""
    write_lock_id = f"{resource_id}:write"

    # Wait for all read locks to clear (simplified check)
    # In production, implement proper read lock tracking

    async with lock_manager.acquire(write_lock_id, agent_id, timeout=60):
        yield

# Usage
async with acquire_read_lock("file:config.yaml", "agent-A"):
    content = await read_file("config.yaml")

async with acquire_write_lock("file:config.yaml", "agent-B"):
    await write_file("config.yaml", new_content)
```

### Pattern 3: Optimistic Locking Alternative

```python
async def optimistic_modify(resource_id: str, agent_id: str):
    """Modify resource optimistically (no lock, version check instead)."""

    # Read current version
    resource = await read_resource_with_version(resource_id)
    current_version = resource["version"]

    # Modify locally
    modified_resource = apply_modifications(resource)

    # Try to write back with version check
    try:
        success = await write_resource_if_version_matches(
            resource_id,
            modified_resource,
            expected_version=current_version
        )

        if success:
            print(f"✅ Optimistic update succeeded")
        else:
            print(f"❌ Version mismatch, retrying...")
            await optimistic_modify(resource_id, agent_id)  # Retry

    except Exception as e:
        print(f"❌ Optimistic update failed: {e}")
```

## Error Handling Best Practices

### Handling Contention

```python
async def handle_lock_contention(resource_id: str, agent_id: str):
    """Handle lock contention with multiple strategies."""

    try:
        async with lock_manager.acquire(resource_id, agent_id, wait_timeout=5):
            await perform_operation()

    except ResourceLockError as e:
        lock_info = await lock_manager.get_lock_info(resource_id)
        current_owner = lock_info.get("agent_id")

        # Strategy 1: Wait and retry
        if current_owner == "agent-infrastructure":
            print(f"Infrastructure operation in progress, waiting...")
            await asyncio.sleep(10)
            return await handle_lock_contention(resource_id, agent_id)

        # Strategy 2: Defer task
        elif current_owner == "agent-feature-dev":
            print(f"Feature dev in progress, deferring task...")
            await defer_task_to_queue(resource_id, agent_id)
            return

        # Strategy 3: Fail and alert
        else:
            print(f"❌ Unexpected lock owner: {current_owner}")
            await send_alert(f"Lock contention on {resource_id}")
            raise
```

### Handling Lock Expiration

```python
async def operation_with_expiration_handling(resource_id: str, agent_id: str):
    """Handle case where lock expires during operation."""

    async with lock_manager.acquire(resource_id, agent_id, timeout=30):
        start_time = time.time()

        try:
            await perform_operation()

        except Exception as e:
            elapsed = time.time() - start_time

            if elapsed > 30:
                print(f"❌ Lock likely expired ({elapsed}s elapsed)")
                # Verify lock status
                is_still_locked = await lock_manager.is_locked(resource_id)
                if not is_still_locked:
                    raise ResourceLockError("Lock expired during operation")

            raise
```

### Handling Stale Locks

```python
async def force_unlock_if_stale(resource_id: str, max_age_seconds: int = 300):
    """Force unlock if lock is stale (older than max_age_seconds)."""

    lock_info = await lock_manager.get_lock_info(resource_id)

    if lock_info:
        locked_at = datetime.fromisoformat(lock_info["locked_at"])
        age = (datetime.utcnow() - locked_at).total_seconds()

        if age > max_age_seconds:
            print(f"⚠️  Lock is stale ({age}s old), force unlocking...")
            await lock_manager.force_unlock(resource_id, admin_agent_id="admin")
            return True

    return False

# Usage (admin/cleanup operations only)
if await force_unlock_if_stale("file:stuck-lock.txt", max_age_seconds=600):
    print("Stale lock removed, retrying operation")
    await perform_operation()
```

## Best Practices

### 1. Granularity

Lock specific resources (e.g., individual files) rather than broad categories (e.g., "codebase") to maximize concurrency:

```python
# ❌ BAD: Too broad
async with lock_manager.acquire("file:entire-codebase", agent_id):
    modify_one_file()

# ✅ GOOD: Specific
async with lock_manager.acquire("file:src/main.py", agent_id):
    modify_file("src/main.py")
```

### 2. Timeouts

Keep lock duration short. If a task takes a long time, consider breaking it down:

```python
# ❌ BAD: Long lock duration
async with lock_manager.acquire(resource_id, agent_id, timeout=3600):  # 1 hour!
    await very_long_operation()

# ✅ GOOD: Short locks with checkpoints
for chunk in chunks:
    async with lock_manager.acquire(resource_id, agent_id, timeout=30):
        await process_chunk(chunk)
        await save_checkpoint()
```

### 3. Error Handling

Always handle `ResourceLockError`. Retry with exponential backoff if appropriate:

```python
# ✅ GOOD: Proper error handling
try:
    async with lock_manager.acquire(resource_id, agent_id):
        await modify_resource()
except ResourceLockError as e:
    logger.warning(f"Lock contention: {e}")
    await retry_with_backoff()
```

### 4. Lock Ordering

Always acquire locks in the same order to prevent deadlock:

```python
# ✅ GOOD: Consistent ordering
resources = sorted(["file:b.txt", "file:a.txt", "file:c.txt"])
for resource in resources:
    async with lock_manager.acquire(resource, agent_id):
        await modify(resource)
```

### 5. Cleanup

Use force_unlock for cleanup (admin only):

```python
# Admin cleanup task
stale_locks = await find_stale_locks(max_age=600)
for lock in stale_locks:
    await lock_manager.force_unlock(lock["resource_id"], "admin")
```

## Prometheus Metrics

The ResourceLockManager exports the following metrics:

- `resource_lock_acquisitions_total{resource_type, agent_id}` - Successful lock acquisitions
- `resource_lock_wait_time_seconds{resource_type, agent_id}` - Time spent waiting for locks
- `resource_locks_active{resource_type}` - Currently active locks
- `resource_lock_contentions_total{resource_type, agent_id}` - Failed immediate acquisitions
- `resource_lock_releases_total{resource_type, agent_id}` - Lock releases
- `resource_lock_timeouts_total{resource_type, agent_id}` - Lock acquisition timeouts

Query examples:

```promql
# Average lock wait time
rate(resource_lock_wait_time_seconds_sum[5m]) / rate(resource_lock_wait_time_seconds_count[5m])

# Lock contention rate
rate(resource_lock_contentions_total[5m]) / rate(resource_lock_acquisitions_total[5m])

# Active locks by resource type
resource_locks_active
```
