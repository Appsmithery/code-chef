"""Integration tests for longitudinal tracking and regression detection.

Tests Phase 5 (CHEF-243): Comprehensive A/B Test Suite - Regression Detection

Validates:
- Version-over-version performance tracking
- Regression detection across extension versions
- Time-series trend analysis
- Historical comparison queries
- Performance degradation alerts

This suite ensures that model updates don't introduce regressions
and that performance trends are accurately tracked over time.

Part of: Testing, Tracing & Evaluation Refactoring (CHEF-238)
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import List
from uuid import uuid4

import pytest

# Set test environment
os.environ["TEST_DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/devtools_test"
)

from shared.lib.longitudinal_tracker import longitudinal_tracker


@pytest.fixture
async def initialized_tracker():
    """Initialize tracker with test database."""
    await longitudinal_tracker.initialize()
    yield longitudinal_tracker
    await longitudinal_tracker.close()


@pytest.fixture
def sample_agent():
    """Return test agent name."""
    return "feature_dev"


@pytest.fixture
def version_sequence():
    """Generate sequence of version numbers."""
    return ["1.0.0-test", "1.1.0-test", "1.2.0-test", "1.3.0-test", "2.0.0-test"]


class TestVersionOverVersionTracking:
    """Test tracking performance across multiple versions."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_track_improvement_across_versions(
        self, initialized_tracker, sample_agent, version_sequence
    ):
        """Test tracking progressive improvement across versions."""
        # Simulate progressive improvement: 0.70 → 0.75 → 0.80 → 0.85 → 0.90
        base_accuracy = 0.70
        improvement_per_version = 0.05

        for idx, version in enumerate(version_sequence):
            accuracy = base_accuracy + (improvement_per_version * idx)

            # Store multiple tasks for this version
            for task_num in range(3):
                await initialized_tracker.record_result(
                    experiment_id=f"exp-version-{version}",
                    task_id=f"task-{uuid4().hex[:8]}",
                    experiment_group="code-chef",
                    extension_version=version,
                    model_version=f"model-{version}",
                    agent_name=sample_agent,
                    scores={"accuracy": accuracy},
                    metrics={"latency_ms": 2000},
                )

        # Query trend
        trend = await initialized_tracker.get_metric_trend(
            agent_name=sample_agent,
            metric="accuracy",
            experiment_group="code-chef",
            days=1,
            limit=len(version_sequence),
        )

        # Verify we got data for all versions
        assert len(trend) >= len(version_sequence)

        # Verify trend shows improvement
        trend_versions = [t["extension_version"] for t in trend]
        for version in version_sequence:
            assert version in trend_versions

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_detect_regression_between_versions(
        self, initialized_tracker, sample_agent
    ):
        """Test detection of performance regression between versions."""
        v1 = "1.5.0-test"
        v2 = "1.6.0-test"  # Regression version

        # Version 1.5.0: Good performance
        for _ in range(5):
            await initialized_tracker.record_result(
                experiment_id=f"exp-{v1}",
                task_id=f"task-{uuid4().hex[:8]}",
                experiment_group="code-chef",
                extension_version=v1,
                model_version=f"model-{v1}",
                agent_name=sample_agent,
                scores={"accuracy": 0.90, "completeness": 0.88},
                metrics={"latency_ms": 1800},
            )

        # Version 1.6.0: Regression!
        for _ in range(5):
            await initialized_tracker.record_result(
                experiment_id=f"exp-{v2}",
                task_id=f"task-{uuid4().hex[:8]}",
                experiment_group="code-chef",
                extension_version=v2,
                model_version=f"model-{v2}",
                agent_name=sample_agent,
                scores={"accuracy": 0.75, "completeness": 0.70},  # Regression
                metrics={"latency_ms": 2500},  # Slower
            )

        # Query both versions
        trend = await initialized_tracker.get_metric_trend(
            agent_name=sample_agent,
            metric="accuracy",
            experiment_group="code-chef",
            days=1,
        )

        # Find scores for each version
        v1_data = next((t for t in trend if t["extension_version"] == v1), None)
        v2_data = next((t for t in trend if t["extension_version"] == v2), None)

        assert v1_data is not None
        assert v2_data is not None

        # Verify regression detected
        assert v2_data["avg_score"] < v1_data["avg_score"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_track_multiple_metrics_simultaneously(
        self, initialized_tracker, sample_agent, version_sequence
    ):
        """Test tracking multiple metrics across versions simultaneously."""
        metrics_evolution = {
            "1.0.0-test": {"accuracy": 0.70, "completeness": 0.75, "efficiency": 0.65},
            "1.1.0-test": {"accuracy": 0.75, "completeness": 0.78, "efficiency": 0.70},
            "1.2.0-test": {"accuracy": 0.80, "completeness": 0.82, "efficiency": 0.75},
        }

        for version, scores in metrics_evolution.items():
            await initialized_tracker.record_result(
                experiment_id=f"exp-multi-{version}",
                task_id=f"task-{uuid4().hex[:8]}",
                experiment_group="code-chef",
                extension_version=version,
                model_version=f"model-{version}",
                agent_name=sample_agent,
                scores=scores,
                metrics={"latency_ms": 2000},
            )

        # Query trends for all metrics
        for metric in ["accuracy", "completeness", "efficiency"]:
            trend = await initialized_tracker.get_metric_trend(
                agent_name=sample_agent,
                metric=metric,
                experiment_group="code-chef",
                days=1,
            )

            # Verify we have data for this metric
            assert len(trend) >= len(metrics_evolution)


class TestRegressionDetection:
    """Test specific regression detection scenarios."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_detect_latency_regression(self, initialized_tracker, sample_agent):
        """Test detection of latency increase (performance regression)."""
        v1 = "2.1.0-test"
        v2 = "2.2.0-test"

        # v1: Fast response times
        await initialized_tracker.record_result(
            experiment_id=f"exp-{v1}",
            task_id=f"task-{uuid4().hex[:8]}",
            experiment_group="code-chef",
            extension_version=v1,
            model_version=f"model-{v1}",
            agent_name=sample_agent,
            scores={"accuracy": 0.85},
            metrics={"latency_ms": 1500, "tokens_used": 2000},
        )

        # v2: Slower response times (regression)
        await initialized_tracker.record_result(
            experiment_id=f"exp-{v2}",
            task_id=f"task-{uuid4().hex[:8]}",
            experiment_group="code-chef",
            extension_version=v2,
            model_version=f"model-{v2}",
            agent_name=sample_agent,
            scores={"accuracy": 0.85},  # Same accuracy
            metrics={"latency_ms": 3000, "tokens_used": 2000},  # But slower
        )

        # Query to detect regression
        # In real scenario, would compare avg latency between versions
        async with initialized_tracker.pool.acquire() as conn:
            v1_latency = await conn.fetchval(
                """
                SELECT AVG(latency_ms) FROM evaluation_results
                WHERE extension_version = $1 AND agent_name = $2
                """,
                v1,
                sample_agent,
            )

            v2_latency = await conn.fetchval(
                """
                SELECT AVG(latency_ms) FROM evaluation_results
                WHERE extension_version = $2 AND agent_name = $3
                """,
                v2,
                sample_agent,
            )

        assert v2_latency > v1_latency  # Regression detected

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_detect_cost_increase(self, initialized_tracker, sample_agent):
        """Test detection of cost increase."""
        v1 = "2.3.0-test"
        v2 = "2.4.0-test"

        # v1: Lower cost
        await initialized_tracker.record_result(
            experiment_id=f"exp-{v1}",
            task_id=f"task-{uuid4().hex[:8]}",
            experiment_group="code-chef",
            extension_version=v1,
            model_version=f"model-{v1}",
            agent_name=sample_agent,
            scores={"accuracy": 0.85},
            metrics={"cost_usd": 0.001},
        )

        # v2: Higher cost (regression)
        await initialized_tracker.record_result(
            experiment_id=f"exp-{v2}",
            task_id=f"task-{uuid4().hex[:8]}",
            experiment_group="code-chef",
            extension_version=v2,
            model_version=f"model-{v2}",
            agent_name=sample_agent,
            scores={"accuracy": 0.85},
            metrics={"cost_usd": 0.005},  # 5x more expensive
        )

        # Verify cost increase
        async with initialized_tracker.pool.acquire() as conn:
            costs = await conn.fetch(
                """
                SELECT extension_version, AVG(cost_usd) as avg_cost
                FROM evaluation_results
                WHERE extension_version IN ($1, $2) AND agent_name = $3
                GROUP BY extension_version
                ORDER BY extension_version
                """,
                v1,
                v2,
                sample_agent,
            )

        assert len(costs) == 2
        v1_cost = next(c["avg_cost"] for c in costs if c["extension_version"] == v1)
        v2_cost = next(c["avg_cost"] for c in costs if c["extension_version"] == v2)

        assert v2_cost > v1_cost

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_mixed_regression_scenario(self, initialized_tracker, sample_agent):
        """Test scenario where some metrics improve but others regress."""
        v1 = "2.5.0-test"
        v2 = "2.6.0-test"

        # v1: Baseline
        await initialized_tracker.record_result(
            experiment_id=f"exp-{v1}",
            task_id=f"task-{uuid4().hex[:8]}",
            experiment_group="code-chef",
            extension_version=v1,
            model_version=f"model-{v1}",
            agent_name=sample_agent,
            scores={"accuracy": 0.80, "completeness": 0.85},
            metrics={"latency_ms": 2000},
        )

        # v2: Better accuracy, worse completeness
        await initialized_tracker.record_result(
            experiment_id=f"exp-{v2}",
            task_id=f"task-{uuid4().hex[:8]}",
            experiment_group="code-chef",
            extension_version=v2,
            model_version=f"model-{v2}",
            agent_name=sample_agent,
            scores={"accuracy": 0.90, "completeness": 0.70},  # Mixed
            metrics={"latency_ms": 1800},
        )

        # Query both metrics
        acc_trend = await initialized_tracker.get_metric_trend(
            agent_name=sample_agent,
            metric="accuracy",
            experiment_group="code-chef",
            days=1,
        )

        comp_trend = await initialized_tracker.get_metric_trend(
            agent_name=sample_agent,
            metric="completeness",
            experiment_group="code-chef",
            days=1,
        )

        # Find data for both versions
        v1_acc = next(
            (t["avg_score"] for t in acc_trend if t["extension_version"] == v1), None
        )
        v2_acc = next(
            (t["avg_score"] for t in acc_trend if t["extension_version"] == v2), None
        )
        v1_comp = next(
            (t["avg_score"] for t in comp_trend if t["extension_version"] == v1), None
        )
        v2_comp = next(
            (t["avg_score"] for t in comp_trend if t["extension_version"] == v2), None
        )

        # Verify mixed results
        assert v2_acc > v1_acc  # Accuracy improved
        assert v2_comp < v1_comp  # Completeness regressed


class TestTimeSeriesQueries:
    """Test time-series query capabilities."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_query_with_date_range(
        self, initialized_tracker, sample_agent, version_sequence
    ):
        """Test querying results within specific date range."""
        # Store results across multiple days
        for idx, version in enumerate(version_sequence[:3]):
            await initialized_tracker.record_result(
                experiment_id=f"exp-time-{version}",
                task_id=f"task-{uuid4().hex[:8]}",
                experiment_group="code-chef",
                extension_version=version,
                model_version=f"model-{version}",
                agent_name=sample_agent,
                scores={"accuracy": 0.70 + (idx * 0.05)},
                metrics={"latency_ms": 2000},
            )

        # Query last 7 days
        trend_7d = await initialized_tracker.get_metric_trend(
            agent_name=sample_agent,
            metric="accuracy",
            experiment_group="code-chef",
            days=7,
        )

        # Query last 1 day
        trend_1d = await initialized_tracker.get_metric_trend(
            agent_name=sample_agent,
            metric="accuracy",
            experiment_group="code-chef",
            days=1,
        )

        # Both should return results (all stored recently)
        assert len(trend_7d) >= 3
        assert len(trend_1d) >= 3

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_limit_results(
        self, initialized_tracker, sample_agent, version_sequence
    ):
        """Test limiting number of results returned."""
        # Store many versions
        for version in version_sequence:
            await initialized_tracker.record_result(
                experiment_id=f"exp-limit-{version}",
                task_id=f"task-{uuid4().hex[:8]}",
                experiment_group="code-chef",
                extension_version=version,
                model_version=f"model-{version}",
                agent_name=sample_agent,
                scores={"accuracy": 0.85},
                metrics={"latency_ms": 2000},
            )

        # Query with limit
        trend = await initialized_tracker.get_metric_trend(
            agent_name=sample_agent,
            metric="accuracy",
            experiment_group="code-chef",
            days=1,
            limit=3,
        )

        # Should respect limit
        assert len(trend) <= 3


class TestHistoricalComparison:
    """Test historical comparison capabilities."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_compare_current_vs_previous_version(
        self, initialized_tracker, sample_agent
    ):
        """Test comparing current version against previous version."""
        v_previous = "3.0.0-test"
        v_current = "3.1.0-test"

        task_id = f"task-{uuid4().hex[:8]}"

        # Store results for same task across versions
        await initialized_tracker.record_result(
            experiment_id=f"exp-{v_previous}",
            task_id=task_id,
            experiment_group="code-chef",
            extension_version=v_previous,
            model_version=f"model-{v_previous}",
            agent_name=sample_agent,
            scores={"accuracy": 0.80},
            metrics={"latency_ms": 2000},
        )

        await initialized_tracker.record_result(
            experiment_id=f"exp-{v_current}",
            task_id=task_id,
            experiment_group="code-chef",
            extension_version=v_current,
            model_version=f"model-{v_current}",
            agent_name=sample_agent,
            scores={"accuracy": 0.90},
            metrics={"latency_ms": 1800},
        )

        # Query trend
        trend = await initialized_tracker.get_metric_trend(
            agent_name=sample_agent,
            metric="accuracy",
            experiment_group="code-chef",
            days=1,
        )

        # Find both versions
        prev = next((t for t in trend if t["extension_version"] == v_previous), None)
        curr = next((t for t in trend if t["extension_version"] == v_current), None)

        assert prev is not None
        assert curr is not None
        assert curr["avg_score"] > prev["avg_score"]

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_track_best_performing_version(
        self, initialized_tracker, sample_agent, version_sequence
    ):
        """Test identifying best performing version historically."""
        # Store varying performance across versions
        performance_map = {
            "1.0.0-test": 0.70,
            "1.1.0-test": 0.85,  # Best
            "1.2.0-test": 0.75,
            "1.3.0-test": 0.80,
            "2.0.0-test": 0.82,
        }

        for version, accuracy in performance_map.items():
            await initialized_tracker.record_result(
                experiment_id=f"exp-best-{version}",
                task_id=f"task-{uuid4().hex[:8]}",
                experiment_group="code-chef",
                extension_version=version,
                model_version=f"model-{version}",
                agent_name=sample_agent,
                scores={"accuracy": accuracy},
                metrics={"latency_ms": 2000},
            )

        # Query all versions
        trend = await initialized_tracker.get_metric_trend(
            agent_name=sample_agent,
            metric="accuracy",
            experiment_group="code-chef",
            days=1,
            limit=10,
        )

        # Find best performing version
        best = max(trend, key=lambda t: t["avg_score"])

        assert best["extension_version"] == "1.1.0-test"
        assert best["avg_score"] >= 0.85


class TestDataConsistency:
    """Test data consistency across versions."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_version_data_isolation(self, initialized_tracker, sample_agent):
        """Test that version data remains isolated."""
        versions = ["4.0.0-test", "4.1.0-test"]

        # Store different data for each version
        for idx, version in enumerate(versions):
            await initialized_tracker.record_result(
                experiment_id=f"exp-isolation-{version}",
                task_id=f"task-{uuid4().hex[:8]}",
                experiment_group="code-chef",
                extension_version=version,
                model_version=f"model-{version}",
                agent_name=sample_agent,
                scores={"accuracy": 0.70 + (idx * 0.20)},
                metrics={"latency_ms": 2000},
            )

        # Query each version separately
        trend = await initialized_tracker.get_metric_trend(
            agent_name=sample_agent,
            metric="accuracy",
            experiment_group="code-chef",
            days=1,
        )

        # Verify each version has distinct data
        v1_data = next(
            (t for t in trend if t["extension_version"] == versions[0]), None
        )
        v2_data = next(
            (t for t in trend if t["extension_version"] == versions[1]), None
        )

        assert v1_data["avg_score"] != v2_data["avg_score"]


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
