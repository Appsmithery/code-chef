"""Training job lifecycle tests.

Tests cover:
- Training job submission with LangSmith data
- Job monitoring and progress tracking
- Job cancellation and cleanup
- Concurrent training jobs
- Training failure recovery
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest


class TestTrainingJobLifecycle:
    """Test training job submission, monitoring, and completion."""

    @pytest.mark.asyncio
    @pytest.mark.modelops
    async def test_training_job_submission_with_langsmith_data(
        self, modelops_coordinator, langsmith_client
    ):
        """Test submitting training job with real LangSmith dataset."""
        # Export data from code-chef-production project
        dataset = await langsmith_client.export_dataset(
            project="code-chef-production", limit=100
        )

        assert len(dataset) >= 100, "Insufficient training data"

        # Submit to AutoTrain Space
        job_response = await modelops_coordinator.submit_training_job(
            agent_name="feature_dev",
            base_model="qwen/qwen-2.5-coder-32b-instruct",
            dataset=dataset,
            is_demo=True,  # Demo mode for testing
        )

        # Verify job ID returned
        assert "job_id" in job_response
        assert job_response["job_id"] is not None

        # Verify job accepted and queued
        assert job_response["status"] in ["queued", "running"]
        assert "space_url" in job_response

    @pytest.mark.asyncio
    @pytest.mark.modelops
    async def test_training_job_monitoring_with_tensorboard(self, modelops_coordinator):
        """Test monitoring training progress."""
        # Submit job
        job_response = await modelops_coordinator.submit_training_job(
            agent_name="feature_dev",
            base_model="qwen/qwen-2.5-coder-32b-instruct",
            dataset=[{"input": "test", "output": "test"}] * 100,
            is_demo=True,
        )

        job_id = job_response["job_id"]

        # Poll job status every 30s
        progress_updates = []
        max_polls = 20  # Max 10 minutes for demo mode
        poll_count = 0

        while poll_count < max_polls:
            status = await modelops_coordinator.get_job_status(job_id)
            progress_updates.append(status["progress"])

            if status["status"] == "completed":
                break
            elif status["status"] == "failed":
                pytest.fail(f"Training job failed: {status.get('error')}")

            await asyncio.sleep(30)
            poll_count += 1

        # Verify progress updates (0% → 25% → 50% → 75% → 100%)
        assert progress_updates[0] >= 0
        assert progress_updates[-1] == 100
        assert len(progress_updates) > 1, "Expected multiple progress updates"

        # Check TensorBoard metrics accessible
        tensorboard_url = status.get("tensorboard_url")
        if tensorboard_url:
            # Verify URL is accessible (basic check)
            assert "tensorboard" in tensorboard_url.lower()

        # Verify loss decreasing (if metrics available)
        if "metrics" in status:
            losses = status["metrics"].get("train_loss", [])
            if len(losses) > 1:
                # Loss should generally decrease
                assert losses[-1] <= losses[0], "Expected loss to decrease"

    @pytest.mark.asyncio
    @pytest.mark.modelops
    async def test_training_job_cancellation(self, modelops_coordinator):
        """Test canceling running training job."""
        # Submit job
        job_response = await modelops_coordinator.submit_training_job(
            agent_name="feature_dev",
            base_model="qwen/qwen-2.5-coder-32b-instruct",
            dataset=[{"input": "test", "output": "test"}] * 1000,  # Large dataset
            is_demo=False,  # Production mode to ensure longer runtime
        )

        job_id = job_response["job_id"]

        # Wait until status = "running"
        max_wait = 300  # 5 minutes
        wait_time = 0

        while wait_time < max_wait:
            status = await modelops_coordinator.get_job_status(job_id)
            if status["status"] == "running":
                break
            await asyncio.sleep(10)
            wait_time += 10

        assert status["status"] == "running", "Job never reached running state"

        # Cancel job
        cancel_response = await modelops_coordinator.cancel_training_job(job_id)
        assert cancel_response["success"] is True

        # Verify status changes to "cancelled"
        await asyncio.sleep(10)  # Allow time for cancellation
        final_status = await modelops_coordinator.get_job_status(job_id)
        assert final_status["status"] == "cancelled"

        # Verify graceful cleanup (no orphaned processes)
        # Check Space status
        space_status = await modelops_coordinator.get_space_status()
        assert (
            space_status["active_jobs"] == 0
        ), "Expected no active jobs after cancellation"

    @pytest.mark.asyncio
    @pytest.mark.modelops
    async def test_multiple_concurrent_training_jobs(self, modelops_coordinator):
        """Test handling multiple simultaneous training jobs."""
        # Submit 3 jobs concurrently for different agents
        jobs = await asyncio.gather(
            modelops_coordinator.submit_training_job(
                agent_name="feature_dev",
                base_model="qwen/qwen-2.5-coder-32b-instruct",
                dataset=[{"input": "test1", "output": "test1"}] * 100,
                is_demo=True,
            ),
            modelops_coordinator.submit_training_job(
                agent_name="code_review",
                base_model="deepseek/deepseek-v3",
                dataset=[{"input": "test2", "output": "test2"}] * 100,
                is_demo=True,
            ),
            modelops_coordinator.submit_training_job(
                agent_name="infrastructure",
                base_model="google/gemini-2.0-flash-exp",
                dataset=[{"input": "test3", "output": "test3"}] * 100,
                is_demo=True,
            ),
        )

        # Verify queue management
        job_ids = [job["job_id"] for job in jobs]
        assert len(set(job_ids)) == 3, "Expected 3 unique job IDs"

        # Verify no interference between jobs
        statuses = await asyncio.gather(
            *[modelops_coordinator.get_job_status(job_id) for job_id in job_ids]
        )

        # Each job should have its own status
        for i, status in enumerate(statuses):
            assert status["job_id"] == job_ids[i]
            assert status["agent_name"] in [
                "feature_dev",
                "code_review",
                "infrastructure",
            ]

        # Verify all complete successfully (or at least reach running state)
        # Wait for all jobs to finish (demo mode ~5 min each)
        max_wait = 600  # 10 minutes
        start_time = datetime.now()

        while (datetime.now() - start_time).seconds < max_wait:
            statuses = await asyncio.gather(
                *[modelops_coordinator.get_job_status(job_id) for job_id in job_ids]
            )

            if all(s["status"] in ["completed", "failed"] for s in statuses):
                break

            await asyncio.sleep(30)

        # Verify all completed successfully
        final_statuses = [s["status"] for s in statuses]
        assert all(
            s == "completed" for s in final_statuses
        ), f"Not all jobs completed: {final_statuses}"

    @pytest.mark.asyncio
    @pytest.mark.modelops
    async def test_training_failure_recovery(self, modelops_coordinator):
        """Test recovery from training failures."""
        # Test 1: Submit job with invalid config (missing required field)
        with pytest.raises(ValueError, match="agent_name is required"):
            await modelops_coordinator.submit_training_job(
                agent_name=None,  # Invalid!
                base_model="qwen/qwen-2.5-coder-32b-instruct",
                dataset=[{"input": "test", "output": "test"}] * 100,
                is_demo=True,
            )

        # Test 2: Submit job with empty dataset
        with pytest.raises(ValueError, match="Dataset cannot be empty"):
            await modelops_coordinator.submit_training_job(
                agent_name="feature_dev",
                base_model="qwen/qwen-2.5-coder-32b-instruct",
                dataset=[],  # Empty!
                is_demo=True,
            )

        # Test 3: Simulate mid-training failure (OOM scenario)
        # This would require mocking the Space API to return failure
        with patch.object(
            modelops_coordinator,
            "_poll_training_job",
            side_effect=Exception("CUDA out of memory"),
        ):
            job_response = await modelops_coordinator.submit_training_job(
                agent_name="feature_dev",
                base_model="qwen/qwen-2.5-coder-32b-instruct",
                dataset=[{"input": "test", "output": "test"}] * 100,
                is_demo=True,
            )

            job_id = job_response["job_id"]

            # Verify error handling and cleanup
            status = await modelops_coordinator.get_job_status(job_id)
            assert status["status"] == "failed"
            assert "error" in status

            # Verify rollback to previous state
            # Check that registry wasn't updated
            registry = await modelops_coordinator.get_model_registry()
            assert job_id not in [m["training_job_id"] for m in registry.values()]

            # Verify cleanup
            space_status = await modelops_coordinator.get_space_status()
            assert space_status["active_jobs"] == 0


# Fixtures


@pytest.fixture
async def modelops_coordinator():
    """Provide ModelOps coordinator instance."""
    from agent_orchestrator.agents.infrastructure.modelops.coordinator import (
        ModelOpsCoordinator,
    )

    coordinator = ModelOpsCoordinator()
    yield coordinator

    # Cleanup: Cancel any remaining jobs
    try:
        space_status = await coordinator.get_space_status()
        for job_id in space_status.get("active_job_ids", []):
            await coordinator.cancel_training_job(job_id)
    except Exception:
        pass


@pytest.fixture
def langsmith_client():
    """Provide LangSmith client instance."""
    import os

    from langsmith import Client

    client = Client(api_key=os.getenv("LANGCHAIN_API_KEY"))
    return client
