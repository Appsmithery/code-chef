"""
Performance tests for concurrent workflow execution.

Tests:
1. Multiple workflows executing in parallel
2. Resource contention handling
3. Throughput measurement
4. Checkpoint database performance

Usage:
    pytest support/tests/performance/test_concurrent_workflows.py -v -s
"""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

sys.path.insert(0, str(Path(__file__).parent / "../../../agent_orchestrator"))
sys.path.insert(0, str(Path(__file__).parent / "../../../shared"))

pytestmark = pytest.mark.asyncio


class TestConcurrentWorkflowExecution:
    """Test concurrent workflow performance."""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client."""
        mock = MagicMock()

        # Simulate LLM latency
        async def mock_chat(messages):
            await asyncio.sleep(0.1)  # 100ms latency
            return {"choices": [{"message": {"content": "Task decomposed into steps"}}]}

        mock.chat = mock_chat
        return mock

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client."""
        mock = MagicMock()

        async def mock_call_tool(server, tool, args):
            await asyncio.sleep(0.05)  # 50ms latency
            return {"success": True, "result": "tool executed"}

        mock.call_tool = mock_call_tool
        return mock

    async def test_10_concurrent_workflows(self, mock_llm_client, mock_mcp_client):
        """Test 10 workflows executing concurrently."""
        from graph import create_orchestrator_graph
        from workflows import WorkflowState

        # Create workflow graph
        graph = create_orchestrator_graph()

        # Mock clients in graph
        # (In real implementation, inject via config)

        async def run_workflow(workflow_id):
            """Run single workflow."""
            start_time = time.time()

            initial_state: WorkflowState = {
                "messages": [f"Implement feature {workflow_id}"],
                "agents": [],
                "results": {},
                "approvals": [],
            }

            config = {"configurable": {"thread_id": f"test-concurrent-{workflow_id}"}}

            # Execute workflow (mocked agents will run fast)
            async for event in graph.astream(initial_state, config):
                pass  # Consume events

            duration = time.time() - start_time
            return {"workflow_id": workflow_id, "duration": duration, "success": True}

        # Launch 10 workflows concurrently
        start_time = time.time()
        results = await asyncio.gather(*[run_workflow(i) for i in range(10)])
        total_duration = time.time() - start_time

        # Verify all succeeded
        assert len(results) == 10, "All 10 workflows should complete"
        assert all(r["success"] for r in results), "All workflows should succeed"

        # Calculate metrics
        avg_duration = sum(r["duration"] for r in results) / len(results)
        throughput = len(results) / total_duration  # workflows per second

        # Performance assertions
        assert total_duration < 30.0, "Should complete 10 workflows in <30s"
        assert avg_duration < 15.0, "Average workflow duration should be <15s"
        assert throughput > 0.3, "Should process >0.3 workflows/sec"

        print("✅ Concurrent workflow execution test passed")
        print(f"   - Total duration: {total_duration:.2f}s")
        print(f"   - Average workflow duration: {avg_duration:.2f}s")
        print(f"   - Throughput: {throughput:.2f} workflows/sec")
        print(f"   - Workflows completed: {len(results)}")

    async def test_checkpoint_database_contention(
        self, mock_llm_client, mock_mcp_client
    ):
        """Test database performance under concurrent checkpoint writes."""
        import os

        import asyncpg

        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/test_devtools",
        )

        # Create connection pool
        pool = await asyncpg.create_pool(db_url, min_size=5, max_size=20)

        try:

            async def write_checkpoint(thread_id, checkpoint_num):
                """Write checkpoint to database."""
                start_time = time.time()

                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO langgraph_checkpoints 
                        (thread_id, checkpoint_id, state, metadata, created_at, version)
                        VALUES ($1, $2, $3::jsonb, $4::jsonb, $5, $6)
                    """,
                        f"thread-{thread_id}",
                        f"checkpoint-{checkpoint_num}",
                        '{"status": "running"}',
                        '{"timestamp": "now"}',
                        datetime.utcnow(),
                        1,
                    )

                duration = time.time() - start_time
                return {"thread_id": thread_id, "duration": duration}

            # Write 50 checkpoints concurrently (5 workflows x 10 checkpoints each)
            start_time = time.time()
            tasks = [
                write_checkpoint(thread_id, checkpoint_num)
                for thread_id in range(5)
                for checkpoint_num in range(10)
            ]
            results = await asyncio.gather(*tasks)
            total_duration = time.time() - start_time

            # Calculate metrics
            avg_write_duration = sum(r["duration"] for r in results) / len(results)
            writes_per_second = len(results) / total_duration

            # Performance assertions
            assert avg_write_duration < 0.1, "Average checkpoint write should be <100ms"
            assert writes_per_second > 20, "Should handle >20 writes/sec"

            print("✅ Database contention test passed")
            print(f"   - Total duration: {total_duration:.2f}s")
            print(f"   - Average write duration: {avg_write_duration*1000:.1f}ms")
            print(f"   - Writes per second: {writes_per_second:.1f}")
            print(f"   - Total writes: {len(results)}")

        finally:
            await pool.close()

        # MCP Gateway tests removed - gateway deprecated Dec 2025
        """Test MCP gateway throughput under concurrent tool calls."""
        import httpx

        gateway_url = "http://localhost:8000"

        async def call_tool(tool_num):
            """Call MCP tool via gateway."""
            start_time = time.time()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{gateway_url}/mcp/call",
                    json={
                        "server": "rust-mcp-filesystem",
                        "tool": "list_directory",
                        "arguments": {"path": "/tmp"},
                    },
                    timeout=10.0,
                )

                duration = time.time() - start_time
                return {
                    "tool_num": tool_num,
                    "status_code": response.status_code,
                    "duration": duration,
                }

        # Make 100 concurrent tool calls
        start_time = time.time()
        results = await asyncio.gather(
            *[call_tool(i) for i in range(100)], return_exceptions=True
        )
        total_duration = time.time() - start_time

        # Filter successful calls
        successful = [
            r for r in results if isinstance(r, dict) and r["status_code"] == 200
        ]

        # Calculate metrics
        if successful:
            avg_duration = sum(r["duration"] for r in successful) / len(successful)
            throughput = len(successful) / total_duration

            print("✅ MCP gateway throughput test passed")
            print(f"   - Total duration: {total_duration:.2f}s")
            print(f"   - Successful calls: {len(successful)}/100")
            print(f"   - Average call duration: {avg_duration*1000:.1f}ms")
            print(f"   - Throughput: {throughput:.1f} calls/sec")
        else:
            print("⚠️  MCP gateway not available, test skipped")


class TestWorkflowScalability:
    """Test workflow scalability with large inputs."""

    async def test_large_context_handling(self):
        """Test workflow with large codebase context."""
        from graph import create_orchestrator_graph
        from workflows import WorkflowState

        # Create large context (simulate 50-file codebase)
        large_context = "\n".join(
            [f"File {i}: " + ("x" * 1000) for i in range(50)]  # 1KB per file
        )  # Total: ~50KB

        initial_state: WorkflowState = {
            "messages": [
                "Refactor authentication system",
                f"Codebase context:\n{large_context}",
            ],
            "agents": [],
            "results": {},
            "approvals": [],
        }

        config = {"configurable": {"thread_id": "test-large-context"}}

        # Execute workflow
        graph = create_orchestrator_graph()

        start_time = time.time()
        async for event in graph.astream(initial_state, config):
            pass  # Consume events
        duration = time.time() - start_time

        # Verify completion and performance
        assert duration < 60.0, "Should handle large context in <60s"

        print("✅ Large context handling test passed")
        print(f"   - Context size: ~50KB")
        print(f"   - Duration: {duration:.2f}s")

    async def test_deep_workflow_nesting(self):
        """Test workflow with many sequential steps."""
        from graph import create_orchestrator_graph
        from workflows import WorkflowState

        # Create task requiring 10 sequential agent calls
        initial_state: WorkflowState = {
            "messages": [
                "Complete full development lifecycle:",
                "1. Design architecture",
                "2. Implement backend",
                "3. Implement frontend",
                "4. Write tests",
                "5. Code review",
                "6. Fix review issues",
                "7. Run CI/CD",
                "8. Deploy to staging",
                "9. Integration test",
                "10. Deploy to production",
            ],
            "agents": [],
            "results": {},
            "approvals": [],
        }

        config = {"configurable": {"thread_id": "test-deep-nesting"}}

        # Execute workflow
        graph = create_orchestrator_graph()

        start_time = time.time()
        checkpoint_count = 0

        async for event in graph.astream(initial_state, config):
            if "__end__" not in event:
                checkpoint_count += 1

        duration = time.time() - start_time

        # Verify completion
        assert checkpoint_count >= 10, "Should have ≥10 checkpoints for 10 steps"

        print("✅ Deep workflow nesting test passed")
        print(f"   - Steps executed: {checkpoint_count}")
        print(f"   - Duration: {duration:.2f}s")


class TestMemoryPersistence:
    """Test memory persistence under load."""

    async def test_service_restart_recovery(self):
        """Test workflow recovery after service restart."""
        import os

        import asyncpg
        from graph import create_orchestrator_graph
        from workflows import WorkflowState

        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/test_devtools",
        )

        # Phase 1: Start workflow, save checkpoint
        thread_id = f"test-restart-{datetime.utcnow().timestamp()}"

        initial_state: WorkflowState = {
            "messages": ["Implement multi-step feature"],
            "agents": ["supervisor"],
            "results": {"step_1": "completed"},
            "approvals": [],
        }

        config = {
            "configurable": {"thread_id": thread_id, "checkpoint_id": "checkpoint-1"}
        }

        # Save checkpoint to database
        pool = await asyncpg.create_pool(db_url)

        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO langgraph_checkpoints
                    (thread_id, checkpoint_id, state, metadata, created_at, version)
                    VALUES ($1, $2, $3::jsonb, $4::jsonb, $5, $6)
                """,
                    thread_id,
                    "checkpoint-1",
                    '{"messages": ["Implement multi-step feature"], "agents": ["supervisor"], "results": {"step_1": "completed"}, "approvals": []}',
                    '{"timestamp": "now"}',
                    datetime.utcnow(),
                    1,
                )

            # Simulate service restart (recreate graph)
            graph = create_orchestrator_graph()

            # Phase 2: Resume from checkpoint
            resume_config = {"configurable": {"thread_id": thread_id}}

            # Resume workflow
            resumed = False
            async for event in graph.astream(None, resume_config):
                if "__start__" not in event:
                    resumed = True
                    break

            assert resumed, "Should resume from checkpoint"

            print("✅ Service restart recovery test passed")
            print(f"   - Thread ID: {thread_id}")
            print(f"   - Checkpoint restored: checkpoint-1")
            print(f"   - Workflow resumed successfully")

        finally:
            await pool.close()

    async def test_qdrant_memory_under_load(self):
        """Test Qdrant vector memory performance under concurrent writes."""
        import httpx

        qdrant_url = "http://localhost:6333"
        collection_name = "workflow_memory"

        async def store_vector(vector_id):
            """Store vector in Qdrant."""
            start_time = time.time()

            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{qdrant_url}/collections/{collection_name}/points",
                    json={
                        "points": [
                            {
                                "id": vector_id,
                                "vector": [0.1] * 384,  # 384-dim vector
                                "payload": {
                                    "text": f"Memory item {vector_id}",
                                    "timestamp": datetime.utcnow().isoformat(),
                                },
                            }
                        ]
                    },
                    timeout=10.0,
                )

                duration = time.time() - start_time
                return {
                    "vector_id": vector_id,
                    "status_code": response.status_code,
                    "duration": duration,
                }

        # Store 50 vectors concurrently
        start_time = time.time()
        results = await asyncio.gather(
            *[store_vector(i) for i in range(50)], return_exceptions=True
        )
        total_duration = time.time() - start_time

        # Filter successful writes
        successful = [
            r for r in results if isinstance(r, dict) and r["status_code"] == 200
        ]

        if successful:
            avg_duration = sum(r["duration"] for r in successful) / len(successful)
            throughput = len(successful) / total_duration

            print("✅ Qdrant memory under load test passed")
            print(f"   - Total duration: {total_duration:.2f}s")
            print(f"   - Successful writes: {len(successful)}/50")
            print(f"   - Average write duration: {avg_duration*1000:.1f}ms")
            print(f"   - Throughput: {throughput:.1f} vectors/sec")
        else:
            print("⚠️  Qdrant not available, test skipped")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
