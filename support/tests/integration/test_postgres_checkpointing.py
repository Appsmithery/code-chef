"""
Integration tests for PostgreSQL checkpoint persistence.

Tests:
1. Checkpoint creation at each node transition
2. State retrieval by thread_id + checkpoint_id
3. Optimistic locking prevents conflicts
4. Checkpoint metadata tracking

Usage:
    pytest support/tests/integration/test_postgres_checkpointing.py -v -s
    
Requirements:
    - PostgreSQL database running
    - DATABASE_URL environment variable set
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
import asyncpg
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "../../../shared"))

pytestmark = pytest.mark.asyncio


class TestPostgresCheckpointing:
    """Test PostgreSQL-based workflow checkpointing."""
    
    @pytest.fixture
    async def db_pool(self):
        """Create test database connection pool."""
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:devtools@localhost:5432/devtools_test"
        )
        
        pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
        
        # Create test schema
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS langgraph_checkpoints (
                    thread_id TEXT,
                    checkpoint_id TEXT,
                    parent_checkpoint_id TEXT,
                    state JSONB,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    version INTEGER DEFAULT 0,
                    PRIMARY KEY (thread_id, checkpoint_id)
                )
            """)
        
        yield pool
        
        # Cleanup
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM langgraph_checkpoints WHERE thread_id LIKE 'test-%'")
        
        await pool.close()
    
    async def test_checkpoint_creation(self, db_pool):
        """Test checkpoint creation at node transitions."""
        thread_id = f"test-checkpoint-{datetime.utcnow().timestamp()}"
        
        # Simulate 3 node transitions
        checkpoints = [
            {
                "checkpoint_id": "cp-1-supervisor",
                "state": {
                    "messages": ["Task received"],
                    "current_agent": "supervisor",
                    "next_agent": "feature-dev"
                },
                "metadata": {"node": "supervisor", "step": 1}
            },
            {
                "checkpoint_id": "cp-2-feature-dev",
                "parent_checkpoint_id": "cp-1-supervisor",
                "state": {
                    "messages": ["Task received", "Code generated"],
                    "current_agent": "feature-dev",
                    "next_agent": "approval"
                },
                "metadata": {"node": "feature-dev", "step": 2}
            },
            {
                "checkpoint_id": "cp-3-approval",
                "parent_checkpoint_id": "cp-2-feature-dev",
                "state": {
                    "messages": ["Task received", "Code generated", "Approval required"],
                    "current_agent": "approval",
                    "requires_approval": True
                },
                "metadata": {"node": "approval", "step": 3}
            }
        ]
        
        async with db_pool.acquire() as conn:
            for cp in checkpoints:
                await conn.execute("""
                    INSERT INTO langgraph_checkpoints 
                    (thread_id, checkpoint_id, parent_checkpoint_id, state, metadata, version)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, thread_id, cp["checkpoint_id"], cp.get("parent_checkpoint_id"),
                    cp["state"], cp["metadata"], 0)
        
        # Verify all checkpoints created
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT checkpoint_id, state, metadata 
                FROM langgraph_checkpoints 
                WHERE thread_id = $1 
                ORDER BY created_at
            """, thread_id)
        
        assert len(rows) == 3, "Should create 3 checkpoints"
        assert rows[0]["checkpoint_id"] == "cp-1-supervisor", "First checkpoint should be supervisor"
        assert rows[2]["checkpoint_id"] == "cp-3-approval", "Last checkpoint should be approval"
        
        print("✅ Checkpoint creation test passed")
        print(f"   - Thread ID: {thread_id}")
        print(f"   - Checkpoints created: {len(rows)}")
    
    async def test_state_retrieval(self, db_pool):
        """Test state retrieval by thread_id and checkpoint_id."""
        thread_id = f"test-retrieval-{datetime.utcnow().timestamp()}"
        checkpoint_id = "cp-test-1"
        
        expected_state = {
            "messages": ["Test message"],
            "current_agent": "test-agent",
            "task_result": {"status": "pending"}
        }
        
        # Insert checkpoint
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO langgraph_checkpoints 
                (thread_id, checkpoint_id, state, metadata, version)
                VALUES ($1, $2, $3, $4, $5)
            """, thread_id, checkpoint_id, expected_state, {"test": True}, 0)
        
        # Retrieve checkpoint
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT state, metadata, version, created_at
                FROM langgraph_checkpoints
                WHERE thread_id = $1 AND checkpoint_id = $2
            """, thread_id, checkpoint_id)
        
        assert row is not None, "Should retrieve checkpoint"
        assert row["state"] == expected_state, "State should match"
        assert row["metadata"]["test"] == True, "Metadata should match"
        assert row["version"] == 0, "Version should be 0"
        
        print("✅ State retrieval test passed")
        print(f"   - State: {row['state']}")
        print(f"   - Metadata: {row['metadata']}")
    
    async def test_optimistic_locking(self, db_pool):
        """Test optimistic locking prevents concurrent update conflicts."""
        thread_id = f"test-locking-{datetime.utcnow().timestamp()}"
        checkpoint_id = "cp-lock-test"
        
        initial_state = {"value": 0}
        
        # Create initial checkpoint
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO langgraph_checkpoints 
                (thread_id, checkpoint_id, state, version)
                VALUES ($1, $2, $3, $4)
            """, thread_id, checkpoint_id, initial_state, 0)
        
        # Simulate two concurrent updates
        async def update_with_version_check(new_value, expected_version):
            async with db_pool.acquire() as conn:
                # Read current version
                row = await conn.fetchrow("""
                    SELECT version FROM langgraph_checkpoints
                    WHERE thread_id = $1 AND checkpoint_id = $2
                """, thread_id, checkpoint_id)
                
                current_version = row["version"]
                
                if current_version != expected_version:
                    raise ValueError(
                        f"Version mismatch: expected {expected_version}, "
                        f"got {current_version}"
                    )
                
                # Update with version increment
                result = await conn.execute("""
                    UPDATE langgraph_checkpoints
                    SET state = $1, version = version + 1
                    WHERE thread_id = $2 AND checkpoint_id = $3 AND version = $4
                """, {"value": new_value}, thread_id, checkpoint_id, expected_version)
                
                return result
        
        # Thread A updates successfully (version 0 → 1)
        await update_with_version_check(new_value=10, expected_version=0)
        
        # Thread B tries to update with stale version (should fail)
        with pytest.raises(ValueError, match="Version mismatch"):
            await update_with_version_check(new_value=20, expected_version=0)
        
        # Verify final state is from Thread A
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT state, version FROM langgraph_checkpoints
                WHERE thread_id = $1 AND checkpoint_id = $2
            """, thread_id, checkpoint_id)
        
        assert row["state"]["value"] == 10, "State should be from first update"
        assert row["version"] == 1, "Version should be incremented once"
        
        print("✅ Optimistic locking test passed")
        print(f"   - Final value: {row['state']['value']}")
        print(f"   - Final version: {row['version']}")
    
    async def test_checkpoint_history(self, db_pool):
        """Test checkpoint history tracking."""
        thread_id = f"test-history-{datetime.utcnow().timestamp()}"
        
        # Create checkpoint chain
        checkpoints = []
        parent_id = None
        for i in range(5):
            cp_id = f"cp-{i}"
            checkpoints.append({
                "checkpoint_id": cp_id,
                "parent_checkpoint_id": parent_id,
                "state": {"step": i},
                "metadata": {"sequence": i}
            })
            parent_id = cp_id
        
        async with db_pool.acquire() as conn:
            for cp in checkpoints:
                await conn.execute("""
                    INSERT INTO langgraph_checkpoints 
                    (thread_id, checkpoint_id, parent_checkpoint_id, state, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                """, thread_id, cp["checkpoint_id"], cp.get("parent_checkpoint_id"),
                    cp["state"], cp["metadata"])
        
        # Verify history
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT checkpoint_id, parent_checkpoint_id, state
                FROM langgraph_checkpoints
                WHERE thread_id = $1
                ORDER BY created_at
            """, thread_id)
        
        assert len(rows) == 5, "Should have 5 checkpoints"
        assert rows[0]["parent_checkpoint_id"] is None, "First checkpoint has no parent"
        assert rows[4]["parent_checkpoint_id"] == "cp-3", "Last checkpoint points to previous"
        
        # Verify chain integrity
        for i in range(1, len(rows)):
            expected_parent = rows[i-1]["checkpoint_id"]
            actual_parent = rows[i]["parent_checkpoint_id"]
            assert actual_parent == expected_parent, f"Checkpoint {i} parent mismatch"
        
        print("✅ Checkpoint history test passed")
        print(f"   - Total checkpoints: {len(rows)}")
        print(f"   - Chain verified: cp-0 → cp-1 → cp-2 → cp-3 → cp-4")
    
    async def test_concurrent_threads(self, db_pool):
        """Test multiple workflows with separate thread IDs."""
        threads = [
            f"test-thread-{i}-{datetime.utcnow().timestamp()}"
            for i in range(3)
        ]
        
        # Create checkpoints for 3 different threads concurrently
        async def create_thread_checkpoints(thread_id, count):
            async with db_pool.acquire() as conn:
                for i in range(count):
                    await conn.execute("""
                        INSERT INTO langgraph_checkpoints 
                        (thread_id, checkpoint_id, state)
                        VALUES ($1, $2, $3)
                    """, thread_id, f"cp-{i}", {"thread": thread_id, "step": i})
        
        await asyncio.gather(*[
            create_thread_checkpoints(threads[0], 3),
            create_thread_checkpoints(threads[1], 5),
            create_thread_checkpoints(threads[2], 2),
        ])
        
        # Verify each thread has correct number of checkpoints
        async with db_pool.acquire() as conn:
            for thread_id, expected_count in [(threads[0], 3), (threads[1], 5), (threads[2], 2)]:
                count = await conn.fetchval("""
                    SELECT COUNT(*) FROM langgraph_checkpoints
                    WHERE thread_id = $1
                """, thread_id)
                assert count == expected_count, f"Thread {thread_id} should have {expected_count} checkpoints"
        
        print("✅ Concurrent threads test passed")
        print(f"   - Thread 1: 3 checkpoints")
        print(f"   - Thread 2: 5 checkpoints")
        print(f"   - Thread 3: 2 checkpoints")


@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="Requires DATABASE_URL environment variable"
)
class TestPostgresCheckpointingIntegration:
    """Integration tests with real PostgreSQL database."""
    
    async def test_real_database_connection(self):
        """Test connection to real PostgreSQL database."""
        database_url = os.getenv("DATABASE_URL")
        
        pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
        
        async with pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            assert "PostgreSQL" in version, "Should connect to PostgreSQL"
        
        await pool.close()
        
        print("✅ Real database connection test passed")
        print(f"   - Database: {version[:50]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
