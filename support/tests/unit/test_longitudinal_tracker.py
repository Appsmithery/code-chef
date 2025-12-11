"""
Unit tests for Longitudinal Tracker

Tests database operations, time-series queries, and thread safety for
evaluation result tracking.

Part of Phase 1: Testing, Tracing & Evaluation Refactoring (CHEF-239)
"""

import asyncio
import os

# Add project root to path
import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).parents[3]))

from shared.lib.longitudinal_tracker import LongitudinalTracker

pytestmark = pytest.mark.asyncio


class TestLongitudinalTracker:
    """Test suite for LongitudinalTracker."""

    @pytest.fixture
    async def tracker(self):
        """Initialize tracker with test database."""
        tracker = LongitudinalTracker()

        # Use test database URL
        test_db_url = os.getenv(
            "TEST_DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/devtools_test",
        )

        await tracker.initialize(db_url=test_db_url)
        yield tracker

        # Cleanup
        if tracker.pool:
            async with tracker.pool.acquire() as conn:
                await conn.execute("TRUNCATE TABLE evaluation_results CASCADE")
                await conn.execute("TRUNCATE TABLE task_comparisons CASCADE")
                await conn.execute("TRUNCATE TABLE experiment_summaries CASCADE")

        await tracker.close()

    async def test_initialize(self, tracker):
        """Test tracker initialization."""
        assert tracker._initialized is True
        assert tracker.pool is not None
        assert tracker.pool.get_size() > 0

    async def test_record_result_baseline(self, tracker):
        """Test recording a baseline evaluation result."""
        experiment_id = f"exp-test-{uuid4().hex[:8]}"
        task_id = f"task-{uuid4().hex[:8]}"

        result_id = await tracker.record_result(
            experiment_id=experiment_id,
            task_id=task_id,
            experiment_group="baseline",
            extension_version="1.0.0",
            model_version="claude-3-haiku",
            agent_name="feature_dev",
            scores={
                "accuracy": 0.75,
                "completeness": 0.70,
                "efficiency": 0.80,
                "integration_quality": 0.65,
            },
            metrics={
                "latency_ms": 2100.5,
                "tokens_used": 3200,
                "cost_usd": 0.0024,
            },
        )

        assert result_id is not None
        assert len(result_id) > 0  # UUID string

    async def test_record_result_codechef(self, tracker):
        """Test recording a code-chef evaluation result."""
        experiment_id = f"exp-test-{uuid4().hex[:8]}"
        task_id = f"task-{uuid4().hex[:8]}"

        result_id = await tracker.record_result(
            experiment_id=experiment_id,
            task_id=task_id,
            experiment_group="code-chef",
            extension_version="1.0.0",
            model_version="qwen-coder-32b-v2",
            agent_name="feature_dev",
            scores={
                "accuracy": 0.92,
                "completeness": 0.88,
                "efficiency": 0.85,
                "integration_quality": 0.90,
            },
            metrics={
                "latency_ms": 1650.0,
                "tokens_used": 2450,
                "cost_usd": 0.00172,
            },
        )

        assert result_id is not None

    async def test_record_result_invalid_group(self, tracker):
        """Test that invalid experiment_group raises ValueError."""
        with pytest.raises(ValueError, match="Invalid experiment_group"):
            await tracker.record_result(
                experiment_id="exp-test",
                task_id="task-test",
                experiment_group="invalid",
                extension_version="1.0.0",
                model_version="test",
                scores={},
                metrics={},
            )

    async def test_compare_variants(self, tracker):
        """Test A/B comparison between baseline and code-chef."""
        experiment_id = f"exp-test-{uuid4().hex[:8]}"
        task_id = f"task-{uuid4().hex[:8]}"

        # Record baseline
        await tracker.record_result(
            experiment_id=experiment_id,
            task_id=task_id,
            experiment_group="baseline",
            extension_version="1.0.0",
            model_version="claude-3-haiku",
            agent_name="feature_dev",
            scores={
                "accuracy": 0.75,
                "completeness": 0.70,
                "efficiency": 0.80,
                "integration_quality": 0.65,
            },
            metrics={
                "latency_ms": 2100.0,
                "tokens_used": 3200,
                "cost_usd": 0.0024,
            },
        )

        # Record code-chef
        await tracker.record_result(
            experiment_id=experiment_id,
            task_id=task_id,
            experiment_group="code-chef",
            extension_version="1.0.0",
            model_version="qwen-coder-32b-v2",
            agent_name="feature_dev",
            scores={
                "accuracy": 0.92,
                "completeness": 0.88,
                "efficiency": 0.85,
                "integration_quality": 0.90,
            },
            metrics={
                "latency_ms": 1650.0,
                "tokens_used": 2450,
                "cost_usd": 0.00172,
            },
        )

        # Compare
        comparison = await tracker.compare_variants(experiment_id, task_id)

        assert "baseline" in comparison
        assert "codechef" in comparison
        assert "improvements" in comparison

        # Verify improvements
        assert comparison["improvements"]["accuracy_pct"] > 0  # code-chef better
        assert comparison["improvements"]["latency_reduction_pct"] > 0  # faster
        assert comparison["improvements"]["cost_reduction_pct"] > 0  # cheaper

    async def test_compare_variants_missing_data(self, tracker):
        """Test comparison with missing data."""
        comparison = await tracker.compare_variants("nonexistent", "task-123")
        assert "error" in comparison

    async def test_get_metric_trend(self, tracker):
        """Test longitudinal metric trend queries."""
        experiment_id = f"exp-test-{uuid4().hex[:8]}"

        # Record results across multiple versions
        versions = ["1.0.0", "1.1.0", "1.2.0"]
        accuracies = [0.75, 0.82, 0.89]

        for version, accuracy in zip(versions, accuracies):
            await tracker.record_result(
                experiment_id=experiment_id,
                task_id=f"task-{uuid4().hex[:8]}",
                experiment_group="code-chef",
                extension_version=version,
                model_version="qwen-coder-32b-v2",
                agent_name="feature_dev",
                scores={
                    "accuracy": accuracy,
                    "completeness": 0.85,
                    "efficiency": 0.80,
                    "integration_quality": 0.75,
                },
                metrics={"latency_ms": 1800.0, "tokens_used": 2500, "cost_usd": 0.002},
            )

        # Query trend
        trend = await tracker.get_metric_trend(
            agent_name="feature_dev",
            metric="accuracy",
            experiment_group="code-chef",
            days=30,
        )

        assert len(trend) == 3
        assert all("extension_version" in item for item in trend)
        assert all("avg_score" in item for item in trend)

    async def test_get_metric_trend_invalid_metric(self, tracker):
        """Test that invalid metric raises ValueError."""
        with pytest.raises(ValueError, match="Invalid metric"):
            await tracker.get_metric_trend(
                agent_name="feature_dev",
                metric="invalid_metric",
            )

    async def test_get_experiment_summary(self, tracker):
        """Test aggregate experiment summary calculation."""
        experiment_id = f"exp-test-{uuid4().hex[:8]}"

        # Create 3 tasks: 2 wins for code-chef, 1 loss
        tasks = [
            ("task-1", 0.70, 0.90),  # +20% accuracy = win
            ("task-2", 0.75, 0.88),  # +13% accuracy = win
            ("task-3", 0.85, 0.82),  # -3% accuracy = loss
        ]

        for task_id, baseline_acc, codechef_acc in tasks:
            # Baseline
            await tracker.record_result(
                experiment_id=experiment_id,
                task_id=task_id,
                experiment_group="baseline",
                extension_version="1.0.0",
                model_version="claude-3-haiku",
                agent_name="feature_dev",
                scores={
                    "accuracy": baseline_acc,
                    "completeness": 0.75,
                    "efficiency": 0.80,
                    "integration_quality": 0.70,
                },
                metrics={"latency_ms": 2000.0, "tokens_used": 3000, "cost_usd": 0.0024},
            )

            # Code-chef
            await tracker.record_result(
                experiment_id=experiment_id,
                task_id=task_id,
                experiment_group="code-chef",
                extension_version="1.0.0",
                model_version="qwen-coder-32b-v2",
                agent_name="feature_dev",
                scores={
                    "accuracy": codechef_acc,
                    "completeness": 0.85,
                    "efficiency": 0.85,
                    "integration_quality": 0.88,
                },
                metrics={"latency_ms": 1600.0, "tokens_used": 2400, "cost_usd": 0.0018},
            )

        # Get summary
        summary = await tracker.get_experiment_summary(experiment_id)

        assert summary["total_tasks"] == 3
        assert summary["codechef_wins"] == 2
        assert summary["baseline_wins"] == 1
        assert summary["avg_accuracy_improvement_pct"] > 0  # Overall improvement

    async def test_concurrent_records(self, tracker):
        """Test thread safety with concurrent record operations."""
        experiment_id = f"exp-test-{uuid4().hex[:8]}"

        async def record_many(group: str, count: int):
            for i in range(count):
                await tracker.record_result(
                    experiment_id=experiment_id,
                    task_id=f"task-{group}-{i}",
                    experiment_group=group,
                    extension_version="1.0.0",
                    model_version="test",
                    agent_name="feature_dev",
                    scores={
                        "accuracy": 0.85,
                        "completeness": 0.80,
                        "efficiency": 0.75,
                        "integration_quality": 0.70,
                    },
                    metrics={
                        "latency_ms": 1500.0,
                        "tokens_used": 2000,
                        "cost_usd": 0.001,
                    },
                )

        # Run concurrently
        await asyncio.gather(
            record_many("baseline", 10),
            record_many("code-chef", 10),
        )

        # Verify all recorded
        async with tracker.pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM evaluation_results WHERE experiment_id = $1",
                experiment_id,
            )

        assert count == 20

    async def test_record_with_metadata(self, tracker):
        """Test recording results with custom metadata."""
        experiment_id = f"exp-test-{uuid4().hex[:8]}"
        task_id = f"task-{uuid4().hex[:8]}"

        metadata = {
            "task_description": "Create JWT middleware",
            "complexity": "complex",
            "phase": "phase2",
        }

        result_id = await tracker.record_result(
            experiment_id=experiment_id,
            task_id=task_id,
            experiment_group="code-chef",
            extension_version="1.0.0",
            model_version="qwen-coder-32b-v2",
            agent_name="feature_dev",
            scores={
                "accuracy": 0.90,
                "completeness": 0.85,
                "efficiency": 0.80,
                "integration_quality": 0.88,
            },
            metrics={"latency_ms": 1700.0, "tokens_used": 2300, "cost_usd": 0.0019},
            metadata=metadata,
        )

        # Verify metadata stored
        async with tracker.pool.acquire() as conn:
            stored_metadata = await conn.fetchval(
                "SELECT metadata FROM evaluation_results WHERE result_id = $1",
                result_id,
            )

        assert stored_metadata["task_description"] == "Create JWT middleware"
        assert stored_metadata["complexity"] == "complex"

    async def test_upsert_on_conflict(self, tracker):
        """Test that duplicate records update instead of error."""
        experiment_id = f"exp-test-{uuid4().hex[:8]}"
        task_id = f"task-{uuid4().hex[:8]}"

        # Insert first time
        result_id_1 = await tracker.record_result(
            experiment_id=experiment_id,
            task_id=task_id,
            experiment_group="baseline",
            extension_version="1.0.0",
            model_version="claude-3-haiku",
            agent_name="feature_dev",
            scores={
                "accuracy": 0.75,
                "completeness": 0.70,
                "efficiency": 0.80,
                "integration_quality": 0.65,
            },
            metrics={"latency_ms": 2000.0, "tokens_used": 3000, "cost_usd": 0.0024},
        )

        # Insert again (should update)
        result_id_2 = await tracker.record_result(
            experiment_id=experiment_id,
            task_id=task_id,
            experiment_group="baseline",
            extension_version="1.0.0",
            model_version="claude-3-haiku",
            agent_name="feature_dev",
            scores={
                "accuracy": 0.80,
                "completeness": 0.75,
                "efficiency": 0.82,
                "integration_quality": 0.70,
            },  # Updated scores
            metrics={"latency_ms": 1900.0, "tokens_used": 2900, "cost_usd": 0.0023},
        )

        assert result_id_1 == result_id_2  # Same record updated

        # Verify only one record exists
        async with tracker.pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM evaluation_results WHERE experiment_id = $1 AND task_id = $2",
                experiment_id,
                task_id,
            )

        assert count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
