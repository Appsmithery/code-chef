"""Integration tests for evaluation database persistence.

Tests Phase 4 (CHEF-242): Enhance Evaluation Runner with Database Persistence

Verifies:
- Evaluation results are correctly stored in database
- Task ID correlation works properly
- Longitudinal queries return expected results
- A/B comparison data is accurate
- Time-series trends are queryable

Part of: Testing, Tracing & Evaluation Refactoring (CHEF-239)
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List
from uuid import uuid4

import pytest

# Set test environment before imports
os.environ["TEST_DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/devtools_test"
)

from shared.lib.longitudinal_tracker import longitudinal_tracker


@pytest.fixture
async def initialized_tracker():
    """Initialize tracker with test database."""
    await longitudinal_tracker.initialize()
    yield longitudinal_tracker
    # Cleanup after tests
    await longitudinal_tracker.close()


@pytest.fixture
def sample_experiment_id():
    """Generate unique experiment ID for tests."""
    return f"test-exp-{uuid4().hex[:8]}"


@pytest.fixture
def sample_task_ids():
    """Generate sample task IDs."""
    return [f"task-{uuid4().hex[:8]}" for _ in range(3)]


class TestEvaluationPersistence:
    """Test evaluation result persistence to database."""

    @pytest.mark.asyncio
    async def test_record_single_result(
        self, initialized_tracker, sample_experiment_id
    ):
        """Test storing a single evaluation result."""
        task_id = f"task-{uuid4().hex[:8]}"

        result_id = await initialized_tracker.record_result(
            experiment_id=sample_experiment_id,
            task_id=task_id,
            experiment_group="code-chef",
            extension_version="1.0.0-test",
            model_version="test-model-v1",
            agent_name="feature_dev",
            scores={
                "accuracy": 0.85,
                "completeness": 0.90,
                "efficiency": 0.75,
                "integration_quality": 0.80,
            },
            metrics={"latency_ms": 1850.5, "tokens_used": 2450, "cost_usd": 0.00172},
            success=True,
            metadata={"test": "test_record_single_result"},
        )

        assert result_id is not None
        assert isinstance(result_id, str)

    @pytest.mark.asyncio
    async def test_record_baseline_and_codechef(
        self, initialized_tracker, sample_experiment_id, sample_task_ids
    ):
        """Test storing baseline and code-chef results for same task."""
        task_id = sample_task_ids[0]

        # Store baseline result
        baseline_id = await initialized_tracker.record_result(
            experiment_id=sample_experiment_id,
            task_id=task_id,
            experiment_group="baseline",
            extension_version="1.0.0-test",
            model_version="baseline-model",
            agent_name="feature_dev",
            scores={"accuracy": 0.70, "completeness": 0.75, "efficiency": 0.65},
            metrics={"latency_ms": 2500, "tokens_used": 3000, "cost_usd": 0.002},
        )

        # Store code-chef result
        codechef_id = await initialized_tracker.record_result(
            experiment_id=sample_experiment_id,
            task_id=task_id,
            experiment_group="code-chef",
            extension_version="1.0.0-test",
            model_version="codechef-model-v1",
            agent_name="feature_dev",
            scores={"accuracy": 0.85, "completeness": 0.90, "efficiency": 0.80},
            metrics={"latency_ms": 1800, "tokens_used": 2200, "cost_usd": 0.0015},
        )

        assert baseline_id != codechef_id

    @pytest.mark.asyncio
    async def test_task_id_correlation(
        self, initialized_tracker, sample_experiment_id, sample_task_ids
    ):
        """Test that task_id correctly correlates baseline and code-chef runs."""
        task_id = sample_task_ids[1]

        # Store both variants
        await initialized_tracker.record_result(
            experiment_id=sample_experiment_id,
            task_id=task_id,
            experiment_group="baseline",
            extension_version="1.0.0-test",
            model_version="baseline",
            scores={"accuracy": 0.60},
            metrics={"latency_ms": 3000},
        )

        await initialized_tracker.record_result(
            experiment_id=sample_experiment_id,
            task_id=task_id,
            experiment_group="code-chef",
            extension_version="1.0.0-test",
            model_version="codechef",
            scores={"accuracy": 0.80},
            metrics={"latency_ms": 2000},
        )

        # Verify comparison works
        comparison = await initialized_tracker.compare_variants(
            experiment_id=sample_experiment_id, task_id=task_id
        )

        assert "error" not in comparison
        assert comparison["baseline"]["accuracy"] == 0.60
        assert comparison["codechef"]["accuracy"] == 0.80
        assert comparison["improvements"]["accuracy_pct"] > 0


class TestLongitudinalQueries:
    """Test time-series and longitudinal queries."""

    @pytest.mark.asyncio
    async def test_get_metric_trend(self, initialized_tracker, sample_experiment_id):
        """Test retrieving metric trends over versions."""
        agent_name = "feature_dev"

        # Store results for multiple versions
        versions = ["1.0.0-test", "1.1.0-test", "1.2.0-test"]
        accuracies = [0.70, 0.80, 0.85]

        for version, accuracy in zip(versions, accuracies):
            await initialized_tracker.record_result(
                experiment_id=f"{sample_experiment_id}-{version}",
                task_id=f"task-{uuid4().hex[:8]}",
                experiment_group="code-chef",
                extension_version=version,
                model_version=f"model-{version}",
                agent_name=agent_name,
                scores={"accuracy": accuracy},
                metrics={"latency_ms": 2000},
            )

        # Query trend
        trend = await initialized_tracker.get_metric_trend(
            agent_name=agent_name,
            metric="accuracy",
            experiment_group="code-chef",
            days=1,
        )

        assert len(trend) >= 3
        # Verify versions are present
        trend_versions = [t["extension_version"] for t in trend]
        for version in versions:
            assert version in trend_versions

    @pytest.mark.asyncio
    async def test_experiment_summary(
        self, initialized_tracker, sample_experiment_id, sample_task_ids
    ):
        """Test experiment summary with wins/losses/ties."""
        # Store multiple comparisons
        tasks_data = [
            {
                "task_id": sample_task_ids[0],
                "baseline_acc": 0.60,
                "codechef_acc": 0.80,
            },  # Win
            {
                "task_id": sample_task_ids[1],
                "baseline_acc": 0.80,
                "codechef_acc": 0.75,
            },  # Loss
            {
                "task_id": sample_task_ids[2],
                "baseline_acc": 0.70,
                "codechef_acc": 0.72,
            },  # Tie
        ]

        for data in tasks_data:
            # Baseline
            await initialized_tracker.record_result(
                experiment_id=sample_experiment_id,
                task_id=data["task_id"],
                experiment_group="baseline",
                extension_version="1.0.0-test",
                model_version="baseline",
                scores={"accuracy": data["baseline_acc"]},
                metrics={"latency_ms": 2000},
            )

            # Code-chef
            await initialized_tracker.record_result(
                experiment_id=sample_experiment_id,
                task_id=data["task_id"],
                experiment_group="code-chef",
                extension_version="1.0.0-test",
                model_version="codechef",
                scores={"accuracy": data["codechef_acc"]},
                metrics={"latency_ms": 1800},
            )

        # Get summary
        summary = await initialized_tracker.get_experiment_summary(
            experiment_id=sample_experiment_id
        )

        assert "error" not in summary
        assert summary["total_tasks"] == 3
        # Should have at least 1 win (>5% improvement)
        assert summary["codechef_wins"] >= 1


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_invalid_experiment_group(
        self, initialized_tracker, sample_experiment_id
    ):
        """Test that invalid experiment_group raises error."""
        with pytest.raises(ValueError, match="Invalid experiment_group"):
            await initialized_tracker.record_result(
                experiment_id=sample_experiment_id,
                task_id=f"task-{uuid4().hex[:8]}",
                experiment_group="invalid",  # Should be 'baseline' or 'code-chef'
                extension_version="1.0.0-test",
                model_version="test",
                scores={},
                metrics={},
            )

    @pytest.mark.asyncio
    async def test_duplicate_result_upsert(
        self, initialized_tracker, sample_experiment_id
    ):
        """Test that duplicate results are upserted (not duplicated)."""
        task_id = f"task-{uuid4().hex[:8]}"

        # Insert same result twice
        await initialized_tracker.record_result(
            experiment_id=sample_experiment_id,
            task_id=task_id,
            experiment_group="code-chef",
            extension_version="1.0.0-test",
            model_version="test",
            scores={"accuracy": 0.75},
            metrics={"latency_ms": 2000},
        )

        # Second insert with updated score
        await initialized_tracker.record_result(
            experiment_id=sample_experiment_id,
            task_id=task_id,
            experiment_group="code-chef",
            extension_version="1.0.0-test",
            model_version="test",
            scores={"accuracy": 0.85},  # Updated
            metrics={"latency_ms": 1800},
        )

        # Verify only one result exists with updated value
        async with initialized_tracker.pool.acquire() as conn:
            count = await conn.fetchval(
                """
                SELECT COUNT(*) FROM evaluation_results
                WHERE experiment_id = $1 AND task_id = $2
                """,
                sample_experiment_id,
                task_id,
            )
            assert count == 1

            accuracy = await conn.fetchval(
                """
                SELECT accuracy FROM evaluation_results
                WHERE experiment_id = $1 AND task_id = $2
                """,
                sample_experiment_id,
                task_id,
            )
            assert accuracy == 0.85  # Should be updated value

    @pytest.mark.asyncio
    async def test_missing_comparison_data(
        self, initialized_tracker, sample_experiment_id
    ):
        """Test comparison with missing data returns error."""
        comparison = await initialized_tracker.compare_variants(
            experiment_id="nonexistent-exp", task_id="nonexistent-task"
        )

        assert "error" in comparison
        assert "No comparison data found" in comparison["error"]


class TestDataIntegrity:
    """Test data integrity and constraints."""

    @pytest.mark.asyncio
    async def test_score_bounds(self, initialized_tracker, sample_experiment_id):
        """Test that scores are bounded between 0 and 1."""
        task_id = f"task-{uuid4().hex[:8]}"

        # Try to insert invalid scores (should fail or be clamped)
        # Note: Database has CHECK constraints for this
        with pytest.raises(Exception):  # asyncpg.CheckViolationError
            await initialized_tracker.record_result(
                experiment_id=sample_experiment_id,
                task_id=task_id,
                experiment_group="code-chef",
                extension_version="1.0.0-test",
                model_version="test",
                scores={"accuracy": 1.5},  # Invalid: > 1
                metrics={"latency_ms": 2000},
            )

    @pytest.mark.asyncio
    async def test_timestamps_automatic(
        self, initialized_tracker, sample_experiment_id
    ):
        """Test that timestamps are automatically set."""
        task_id = f"task-{uuid4().hex[:8]}"

        before_insert = datetime.utcnow()

        await initialized_tracker.record_result(
            experiment_id=sample_experiment_id,
            task_id=task_id,
            experiment_group="code-chef",
            extension_version="1.0.0-test",
            model_version="test",
            scores={"accuracy": 0.80},
            metrics={"latency_ms": 2000},
        )

        after_insert = datetime.utcnow()

        # Verify timestamp is within range
        async with initialized_tracker.pool.acquire() as conn:
            created_at = await conn.fetchval(
                """
                SELECT created_at FROM evaluation_results
                WHERE experiment_id = $1 AND task_id = $2
                """,
                sample_experiment_id,
                task_id,
            )

            assert before_insert <= created_at <= after_insert


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
