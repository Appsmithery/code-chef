"""
Unit tests for comparison_engine.py

Tests:
- Improvement calculation (higher_is_better, lower_is_better)
- Task comparison with complete data
- Weighted improvement calculation
- Winner determination logic
- Comparison report generation
- Experiment summary storage
- Error handling (missing data, invalid inputs)

Part of Phase 3: Testing, Tracing & Evaluation Refactoring (CHEF-241)
"""

import json
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.lib.comparison_engine import comparison_engine


@pytest.fixture
async def engine():
    """Initialize comparison engine with mocked longitudinal_tracker."""
    with patch("shared.lib.comparison_engine.longitudinal_tracker") as mock_tracker:
        mock_tracker.initialize = AsyncMock()
        mock_tracker._pool = MagicMock()
        await comparison_engine.initialize()
        yield comparison_engine


class TestImprovementCalculation:
    """Test improvement percentage calculations."""

    def test_higher_is_better_improvement(self):
        """Accuracy improved from 0.80 to 0.92 = +15% improvement."""
        result = comparison_engine.calculate_improvement(0.80, 0.92, "higher_is_better")
        assert result == pytest.approx(15.0, rel=0.01)

    def test_higher_is_better_degradation(self):
        """Accuracy degraded from 0.90 to 0.70 = -22.22% improvement."""
        result = comparison_engine.calculate_improvement(0.90, 0.70, "higher_is_better")
        assert result == pytest.approx(-22.22, rel=0.01)

    def test_lower_is_better_improvement(self):
        """Latency reduced from 2000ms to 1500ms = +25% improvement."""
        result = comparison_engine.calculate_improvement(2000, 1500, "lower_is_better")
        assert result == pytest.approx(25.0, rel=0.01)

    def test_lower_is_better_degradation(self):
        """Cost increased from 0.001 to 0.002 = -100% improvement."""
        result = comparison_engine.calculate_improvement(
            0.001, 0.002, "lower_is_better"
        )
        assert result == pytest.approx(-100.0, rel=0.01)

    def test_zero_baseline_higher_is_better(self):
        """Handle zero baseline for higher_is_better metrics."""
        result = comparison_engine.calculate_improvement(0, 0.5, "higher_is_better")
        assert result == 100.0

    def test_zero_baseline_lower_is_better(self):
        """Handle zero baseline for lower_is_better metrics."""
        result = comparison_engine.calculate_improvement(0, 100, "lower_is_better")
        assert result == -100.0

    def test_both_zero(self):
        """Handle both baseline and codechef zero."""
        result = comparison_engine.calculate_improvement(0, 0, "higher_is_better")
        assert result == 0.0


class TestWeightedImprovement:
    """Test weighted overall improvement calculation."""

    def test_weighted_improvement_all_positive(self):
        """All metrics improved."""
        improvements = {
            "accuracy": 10.0,  # 30% weight
            "completeness": 15.0,  # 25% weight
            "efficiency": 20.0,  # 20% weight
            "latency_ms": 25.0,  # 15% weight
            "integration_quality": 5.0,  # 10% weight
        }
        result = comparison_engine._calculate_weighted_improvement(improvements)
        # Expected: (0.30*10 + 0.25*15 + 0.20*20 + 0.15*25 + 0.10*5) / 1.0 = 14.75
        # Implementation normalizes by total_weight, which is 1.0 here
        # Actual calculation: 3.0 + 3.75 + 4.0 + 3.75 + 0.5 = 15.0
        assert result == pytest.approx(15.0, rel=0.01)

    def test_weighted_improvement_mixed(self):
        """Mixed improvements and degradations."""
        improvements = {
            "accuracy": 20.0,  # 30% weight
            "completeness": -10.0,  # 25% weight (degraded)
            "efficiency": 5.0,  # 20% weight
            "latency_ms": 0.0,  # 15% weight (no change)
            "integration_quality": 10.0,  # 10% weight
        }
        result = comparison_engine._calculate_weighted_improvement(improvements)
        # Expected: 0.30*20 + 0.25*(-10) + 0.20*5 + 0.15*0 + 0.10*10 = 5.5
        assert result == pytest.approx(5.5, rel=0.01)

    def test_weighted_improvement_missing_metrics(self):
        """Handle missing metrics gracefully."""
        improvements = {
            "accuracy": 15.0,
            "completeness": 10.0,
        }
        result = comparison_engine._calculate_weighted_improvement(improvements)
        # Expected: (0.30*15 + 0.25*10) / (0.30 + 0.25) = 7.0 / 0.55 = 12.73
        assert result == pytest.approx(12.73, rel=0.01)


class TestWinnerDetermination:
    """Test winner determination logic."""

    def test_winner_codechef(self):
        """Code-chef wins with >5% improvement."""
        assert comparison_engine._determine_winner(15.0) == "code-chef"
        assert comparison_engine._determine_winner(5.1) == "code-chef"

    def test_winner_baseline(self):
        """Baseline wins with <-5% improvement."""
        assert comparison_engine._determine_winner(-10.0) == "baseline"
        assert comparison_engine._determine_winner(-5.1) == "baseline"

    def test_winner_tie(self):
        """Tie within -5% to +5% range."""
        assert comparison_engine._determine_winner(4.9) == "tie"
        assert comparison_engine._determine_winner(0.0) == "tie"
        assert comparison_engine._determine_winner(-4.9) == "tie"


class TestRecommendationGeneration:
    """Test deployment recommendation logic."""

    def test_recommendation_deploy(self):
        """Recommend deploy for >=15% improvement."""
        assert comparison_engine._generate_recommendation(20.0) == "deploy"
        assert comparison_engine._generate_recommendation(15.0) == "deploy"

    def test_recommendation_needs_review(self):
        """Recommend manual review for 5-15% improvement."""
        assert comparison_engine._generate_recommendation(10.0) == "needs_review"
        assert comparison_engine._generate_recommendation(5.0) == "needs_review"

    def test_recommendation_reject(self):
        """Recommend reject for <5% improvement."""
        assert comparison_engine._generate_recommendation(4.9) == "reject"
        assert comparison_engine._generate_recommendation(0.0) == "reject"
        assert comparison_engine._generate_recommendation(-10.0) == "reject"


@pytest.mark.asyncio
class TestTaskComparison:
    """Test single task comparison."""

    async def test_compare_task_complete_data(self, engine):
        """Compare task with complete baseline and codechef data."""
        mock_comparison = {
            "baseline": {
                "experiment_id": "exp-001",
                "task_id": "task-001",
                "experiment_group": "baseline",
                "scores": {
                    "accuracy": 0.80,
                    "completeness": 0.75,
                    "efficiency": 0.70,
                    "integration_quality": 0.65,
                },
                "metrics": {
                    "latency_ms": 2000.0,
                    "tokens_used": 3000,
                    "cost_usd": 0.003,
                },
            },
            "codechef": {
                "experiment_id": "exp-001",
                "task_id": "task-001",
                "experiment_group": "code-chef",
                "scores": {
                    "accuracy": 0.92,
                    "completeness": 0.88,
                    "efficiency": 0.85,
                    "integration_quality": 0.80,
                },
                "metrics": {
                    "latency_ms": 1500.0,
                    "tokens_used": 2500,
                    "cost_usd": 0.0025,
                },
            },
        }

        with patch("shared.lib.comparison_engine.longitudinal_tracker") as mock_tracker:
            mock_tracker.compare_variants = AsyncMock(return_value=mock_comparison)

            result = await engine.compare_task("exp-001", "task-001")

            assert result["task_id"] == "task-001"
            assert result["experiment_id"] == "exp-001"
            assert "baseline" in result
            assert "codechef" in result
            assert "improvements" in result
            assert "winner" in result

            # Check improvements calculated correctly
            improvements = result["improvements"]
            assert improvements["accuracy"] == pytest.approx(
                15.0, rel=0.01
            )  # (0.92-0.80)/0.80 * 100
            assert improvements["latency_ms"] == pytest.approx(
                25.0, rel=0.01
            )  # (2000-1500)/2000 * 100
            assert improvements["cost_usd"] == pytest.approx(
                16.67, rel=0.01
            )  # (0.003-0.0025)/0.003 * 100

            # Overall improvement should be positive, winner = code-chef
            assert result["overall_improvement"] > 5.0
            assert result["winner"] == "code-chef"

    async def test_compare_task_missing_data(self, engine):
        """Handle missing baseline or codechef data."""
        mock_comparison = {
            "baseline": None,
            "codechef": {
                "scores": {"accuracy": 0.90},
                "metrics": {"latency_ms": 1500},
            },
        }

        with patch("shared.lib.comparison_engine.longitudinal_tracker") as mock_tracker:
            mock_tracker.compare_variants = AsyncMock(return_value=mock_comparison)

            result = await engine.compare_task("exp-001", "task-002")

            assert "error" in result
            assert result["error"] == "Missing baseline or codechef data"

    async def test_compare_task_no_data(self, engine):
        """Handle no comparison data found."""
        with patch("shared.lib.comparison_engine.longitudinal_tracker") as mock_tracker:
            mock_tracker.compare_variants = AsyncMock(return_value=None)

            result = await engine.compare_task("exp-999", "task-999")

            assert "error" in result
            assert result["error"] == "No data available"


@pytest.mark.asyncio
class TestComparisonReport:
    """Test full experiment comparison report generation."""

    async def test_generate_comparison_report(self, engine):
        """Generate report with multiple tasks."""
        mock_summary = {
            "total_tasks": 3,
            "wins": 2,
            "losses": 0,
            "ties": 1,
            "avg_accuracy_improvement": 12.5,
            "avg_completeness_improvement": 10.0,
            "avg_efficiency_improvement": 8.5,
            "avg_latency_improvement": 20.0,
            "avg_cost_improvement": 15.0,
            "avg_overall_improvement": 13.2,
        }

        mock_task_ids = [
            {"task_id": "task-001"},
            {"task_id": "task-002"},
            {"task_id": "task-003"},
        ]

        with patch("shared.lib.comparison_engine.longitudinal_tracker") as mock_tracker:
            mock_pool = MagicMock()
            mock_conn = MagicMock()
            mock_conn.fetch = AsyncMock(return_value=mock_task_ids)
            mock_pool.acquire = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock()
                )
            )

            mock_tracker._pool = mock_pool
            mock_tracker.get_experiment_summary = AsyncMock(return_value=mock_summary)

            # Mock compare_task to return simple results
            async def mock_compare_task(exp_id, task_id):
                return {
                    "task_id": task_id,
                    "experiment_id": exp_id,
                    "winner": "code-chef" if task_id != "task-003" else "tie",
                }

            engine.compare_task = mock_compare_task

            report = await engine.generate_comparison_report("exp-001")

            assert report["experiment_id"] == "exp-001"
            assert "timestamp" in report
            assert len(report["tasks"]) == 3
            assert report["summary"]["total_tasks"] == 3
            assert (
                report["summary"]["recommendation"] == "needs_review"
            )  # 13.2% improvement
            assert "reasoning" in report["summary"]

    async def test_generate_report_no_data(self, engine):
        """Handle experiment with no data."""
        with patch("shared.lib.comparison_engine.longitudinal_tracker") as mock_tracker:
            mock_tracker.get_experiment_summary = AsyncMock(return_value=None)

            report = await engine.generate_comparison_report("exp-999")

            assert "error" in report
            assert report["error"] == "No experiment data found"


@pytest.mark.asyncio
class TestExperimentSummaryStorage:
    """Test experiment summary caching in database."""

    async def test_store_experiment_summary(self, engine):
        """Store summary in experiment_summaries table."""
        mock_report = {
            "experiment_id": "exp-001",
            "summary": {
                "total_tasks": 5,
                "wins": 4,
                "losses": 0,
                "ties": 1,
                "avg_improvements": {
                    "accuracy": 15.0,
                    "completeness": 12.0,
                    "efficiency": 10.0,
                    "latency_ms": 20.0,
                    "cost_usd": 18.0,
                    "overall": 15.8,
                },
                "recommendation": "deploy",
            },
        }

        with patch("shared.lib.comparison_engine.longitudinal_tracker") as mock_tracker:
            mock_pool = MagicMock()
            mock_conn = MagicMock()
            mock_conn.execute = AsyncMock()
            mock_pool.acquire = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(return_value=mock_conn), __aexit__=AsyncMock()
                )
            )

            mock_tracker._pool = mock_pool
            engine.generate_comparison_report = AsyncMock(return_value=mock_report)

            await engine.store_experiment_summary("exp-001")

            # Verify execute called with correct parameters
            mock_conn.execute.assert_called_once()
            call_args = mock_conn.execute.call_args[0]
            assert "INSERT INTO experiment_summaries" in call_args[0]
            assert call_args[1] == "exp-001"  # experiment_id
            assert call_args[2] == 5  # total_tasks
            assert call_args[3] == 4  # wins

    async def test_store_summary_with_error(self, engine):
        """Handle errors when generating report."""
        mock_report = {
            "experiment_id": "exp-999",
            "error": "No experiment data found",
        }

        engine.generate_comparison_report = AsyncMock(return_value=mock_report)

        # Should not raise exception, just log warning
        await engine.store_experiment_summary("exp-999")


@pytest.mark.asyncio
class TestJSONExport:
    """Test JSON report export."""

    async def test_export_report_json(self, engine, tmp_path):
        """Export report to JSON file."""
        mock_report = {
            "experiment_id": "exp-001",
            "timestamp": datetime.now().isoformat(),
            "tasks": [],
            "summary": {
                "total_tasks": 2,
                "recommendation": "deploy",
            },
        }

        engine.generate_comparison_report = AsyncMock(return_value=mock_report)

        output_path = tmp_path / "exp-001.json"
        await engine.export_report_json("exp-001", str(output_path))

        # Verify file exists and contains correct data
        assert output_path.exists()

        with open(output_path, "r") as f:
            data = json.load(f)

        assert data["experiment_id"] == "exp-001"
        assert data["summary"]["recommendation"] == "deploy"
