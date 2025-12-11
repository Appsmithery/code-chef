"""End-to-end A/B testing suite for baseline vs code-chef comparison.

Tests Phase 5 (CHEF-243): Create Comprehensive A/B Test Suite

Validates:
- Full A/B workflow from task execution through comparison
- Task execution through both baseline and code-chef with task_id correlation
- Statistical significance of improvements using comparison_engine
- Comparison engine accuracy and recommendation logic
- Integration between baseline_runner, evaluators, and database

Part of: Testing, Tracing & Evaluation Refactoring (CHEF-238)
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, List
from uuid import uuid4

import pytest

# Set test environment
os.environ["TEST_DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/devtools_test"
)
os.environ["TRACE_ENVIRONMENT"] = "test"
os.environ["EXPERIMENT_GROUP"] = "code-chef"

from shared.lib.comparison_engine import comparison_engine
from shared.lib.longitudinal_tracker import longitudinal_tracker


@pytest.fixture
async def initialized_engines():
    """Initialize comparison engine and tracker."""
    await comparison_engine.initialize()
    await longitudinal_tracker.initialize()
    yield {"comparison": comparison_engine, "tracker": longitudinal_tracker}
    # Cleanup
    await longitudinal_tracker.close()


@pytest.fixture
def sample_experiment_id():
    """Generate unique experiment ID for isolated testing."""
    return f"test-ab-{uuid4().hex[:8]}"


@pytest.fixture
def sample_tasks():
    """Generate sample tasks for A/B testing."""
    return [
        {
            "task_id": f"task-{uuid4().hex[:8]}",
            "prompt": "Create a JWT authentication middleware",
            "category": "code_generation",
            "difficulty": "medium",
        },
        {
            "task_id": f"task-{uuid4().hex[:8]}",
            "prompt": "Implement a pagination system with cursor-based scrolling",
            "category": "code_generation",
            "difficulty": "hard",
        },
        {
            "task_id": f"task-{uuid4().hex[:8]}",
            "prompt": "Write unit tests for a React component with hooks",
            "category": "testing",
            "difficulty": "medium",
        },
    ]


class TestEndToEndABWorkflow:
    """Test complete A/B testing workflow from execution to comparison."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_ab_workflow(
        self, initialized_engines, sample_experiment_id, sample_tasks
    ):
        """Test full A/B workflow: baseline → code-chef → compare."""
        tracker = initialized_engines["tracker"]
        engine = initialized_engines["comparison"]

        # Step 1: Execute baseline tasks
        for task in sample_tasks:
            await tracker.record_result(
                experiment_id=sample_experiment_id,
                task_id=task["task_id"],
                experiment_group="baseline",
                extension_version="1.0.0-test",
                model_version="baseline-model",
                agent_name="feature_dev",
                scores={
                    "accuracy": 0.70,
                    "completeness": 0.75,
                    "efficiency": 0.65,
                    "integration_quality": 0.68,
                },
                metrics={
                    "latency_ms": 2500,
                    "tokens_used": 3000,
                    "cost_usd": 0.002,
                },
                success=True,
                metadata=task,
            )

        # Step 2: Execute code-chef tasks
        for task in sample_tasks:
            await tracker.record_result(
                experiment_id=sample_experiment_id,
                task_id=task["task_id"],
                experiment_group="code-chef",
                extension_version="1.0.0-test",
                model_version="codechef-model-v1",
                agent_name="feature_dev",
                scores={
                    "accuracy": 0.88,
                    "completeness": 0.92,
                    "efficiency": 0.85,
                    "integration_quality": 0.87,
                },
                metrics={
                    "latency_ms": 1800,
                    "tokens_used": 2200,
                    "cost_usd": 0.0015,
                },
                success=True,
                metadata=task,
            )

        # Step 3: Generate comparison report
        report = await engine.generate_comparison_report(
            experiment_id=sample_experiment_id
        )

        # Assertions
        assert "error" not in report
        assert report["summary"]["total_tasks"] == len(sample_tasks)
        assert report["summary"]["wins"] > 0  # Code-chef should win
        assert report["summary"]["recommendation"] in ["deploy", "needs_review"]

        # Verify task-level comparisons
        assert len(report["tasks"]) == len(sample_tasks)
        for task_comparison in report["tasks"]:
            assert task_comparison["winner"] in ["code-chef", "baseline", "tie"]
            assert "improvements" in task_comparison

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_task_correlation_accuracy(
        self, initialized_engines, sample_experiment_id, sample_tasks
    ):
        """Test that task_id correctly correlates baseline and code-chef runs."""
        tracker = initialized_engines["tracker"]
        engine = initialized_engines["comparison"]

        task = sample_tasks[0]
        task_id = task["task_id"]

        # Record both variants
        await tracker.record_result(
            experiment_id=sample_experiment_id,
            task_id=task_id,
            experiment_group="baseline",
            extension_version="1.0.0-test",
            model_version="baseline",
            scores={"accuracy": 0.60},
            metrics={"latency_ms": 3000},
        )

        await tracker.record_result(
            experiment_id=sample_experiment_id,
            task_id=task_id,
            experiment_group="code-chef",
            extension_version="1.0.0-test",
            model_version="codechef",
            scores={"accuracy": 0.90},
            metrics={"latency_ms": 2000},
        )

        # Compare task
        comparison = await engine.compare_task(
            experiment_id=sample_experiment_id,
            task_id=task_id,
        )

        # Verify correlation
        assert comparison["task_id"] == task_id
        assert comparison["baseline"]["scores"]["accuracy"] == 0.60
        assert comparison["codechef"]["scores"]["accuracy"] == 0.90
        assert comparison["improvements"]["accuracy"] == pytest.approx(50.0, abs=1.0)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_multiple_experiments_isolation(
        self, initialized_engines, sample_tasks
    ):
        """Test that multiple experiments remain isolated from each other."""
        tracker = initialized_engines["tracker"]
        engine = initialized_engines["comparison"]

        exp1 = f"test-exp1-{uuid4().hex[:8]}"
        exp2 = f"test-exp2-{uuid4().hex[:8]}"

        task = sample_tasks[0]

        # Experiment 1: code-chef wins
        await tracker.record_result(
            experiment_id=exp1,
            task_id=task["task_id"],
            experiment_group="baseline",
            extension_version="1.0.0-test",
            model_version="baseline",
            scores={"accuracy": 0.60},
            metrics={"latency_ms": 3000},
        )

        await tracker.record_result(
            experiment_id=exp1,
            task_id=task["task_id"],
            experiment_group="code-chef",
            extension_version="1.0.0-test",
            model_version="codechef",
            scores={"accuracy": 0.90},
            metrics={"latency_ms": 2000},
        )

        # Experiment 2: baseline wins
        await tracker.record_result(
            experiment_id=exp2,
            task_id=task["task_id"],
            experiment_group="baseline",
            extension_version="1.0.0-test",
            model_version="baseline",
            scores={"accuracy": 0.95},
            metrics={"latency_ms": 1500},
        )

        await tracker.record_result(
            experiment_id=exp2,
            task_id=task["task_id"],
            experiment_group="code-chef",
            extension_version="1.0.0-test",
            model_version="codechef",
            scores={"accuracy": 0.70},
            metrics={"latency_ms": 2500},
        )

        # Verify isolation
        comp1 = await engine.compare_task(exp1, task["task_id"])
        comp2 = await engine.compare_task(exp2, task["task_id"])

        assert comp1["winner"] == "code-chef"
        assert comp2["winner"] == "baseline"


class TestStatisticalSignificance:
    """Test statistical significance calculations and thresholds."""

    @pytest.mark.asyncio
    async def test_improvement_calculation_higher_is_better(self, initialized_engines):
        """Test improvement percentage for metrics where higher is better."""
        engine = initialized_engines["comparison"]

        # Accuracy: 0.70 → 0.85 = +21.43%
        improvement = engine.calculate_improvement(0.70, 0.85, "higher_is_better")
        assert improvement == pytest.approx(21.43, abs=0.01)

        # No improvement
        improvement = engine.calculate_improvement(0.80, 0.80, "higher_is_better")
        assert improvement == 0.0

        # Regression
        improvement = engine.calculate_improvement(0.90, 0.75, "higher_is_better")
        assert improvement < 0

    @pytest.mark.asyncio
    async def test_improvement_calculation_lower_is_better(self, initialized_engines):
        """Test improvement percentage for metrics where lower is better."""
        engine = initialized_engines["comparison"]

        # Latency: 2000ms → 1500ms = +25% improvement (faster)
        improvement = engine.calculate_improvement(2000, 1500, "lower_is_better")
        assert improvement == pytest.approx(25.0, abs=0.01)

        # No improvement
        improvement = engine.calculate_improvement(2000, 2000, "lower_is_better")
        assert improvement == 0.0

        # Regression (slower)
        improvement = engine.calculate_improvement(1500, 2000, "lower_is_better")
        assert improvement < 0

    @pytest.mark.asyncio
    async def test_weighted_improvement_calculation(self, initialized_engines):
        """Test weighted overall improvement using standardized weights."""
        engine = initialized_engines["comparison"]

        improvements = {
            "accuracy": 20.0,  # 30% weight
            "completeness": 15.0,  # 25% weight
            "efficiency": 10.0,  # 20% weight
            "latency_ms": 25.0,  # 15% weight
            "integration_quality": 5.0,  # 10% weight
        }

        # Expected: 0.30*20 + 0.25*15 + 0.20*10 + 0.15*25 + 0.10*5
        #         = 6 + 3.75 + 2 + 3.75 + 0.5 = 16.0
        overall = engine._calculate_weighted_improvement(improvements)
        assert overall == pytest.approx(16.0, abs=0.1)

    @pytest.mark.asyncio
    async def test_winner_determination_thresholds(self, initialized_engines):
        """Test winner determination based on improvement thresholds."""
        engine = initialized_engines["comparison"]

        # Code-chef wins (>5%)
        assert engine._determine_winner(10.0) == "code-chef"
        assert engine._determine_winner(5.1) == "code-chef"

        # Tie (-5% to 5%)
        assert engine._determine_winner(4.9) == "tie"
        assert engine._determine_winner(0.0) == "tie"
        assert engine._determine_winner(-4.9) == "tie"

        # Baseline wins (<-5%)
        assert engine._determine_winner(-5.1) == "baseline"
        assert engine._determine_winner(-10.0) == "baseline"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_recommendation_generation(
        self, initialized_engines, sample_experiment_id, sample_tasks
    ):
        """Test deployment recommendation based on improvement levels."""
        tracker = initialized_engines["tracker"]
        engine = initialized_engines["comparison"]

        test_cases = [
            {
                "name": "strong_improvement",
                "baseline_acc": 0.70,
                "codechef_acc": 0.88,
                "expected": "deploy",
            },
            {
                "name": "moderate_improvement",
                "baseline_acc": 0.80,
                "codechef_acc": 0.88,
                "expected": "needs_review",
            },
            {
                "name": "marginal_improvement",
                "baseline_acc": 0.85,
                "codechef_acc": 0.87,
                "expected": "reject",
            },
        ]

        for case in test_cases:
            exp_id = f"{sample_experiment_id}-{case['name']}"
            task = sample_tasks[0]

            await tracker.record_result(
                experiment_id=exp_id,
                task_id=task["task_id"],
                experiment_group="baseline",
                extension_version="1.0.0-test",
                model_version="baseline",
                scores={"accuracy": case["baseline_acc"]},
                metrics={"latency_ms": 2000},
            )

            await tracker.record_result(
                experiment_id=exp_id,
                task_id=task["task_id"],
                experiment_group="code-chef",
                extension_version="1.0.0-test",
                model_version="codechef",
                scores={"accuracy": case["codechef_acc"]},
                metrics={"latency_ms": 1800},
            )

            report = await engine.generate_comparison_report(exp_id)
            assert (
                report["summary"]["recommendation"] == case["expected"]
            ), f"Failed for case: {case['name']}"


class TestComparisonEdgeCases:
    """Test edge cases and error handling in comparison logic."""

    @pytest.mark.asyncio
    async def test_missing_baseline_data(
        self, initialized_engines, sample_experiment_id, sample_tasks
    ):
        """Test comparison when baseline data is missing."""
        tracker = initialized_engines["tracker"]
        engine = initialized_engines["comparison"]

        task = sample_tasks[0]

        # Only code-chef data
        await tracker.record_result(
            experiment_id=sample_experiment_id,
            task_id=task["task_id"],
            experiment_group="code-chef",
            extension_version="1.0.0-test",
            model_version="codechef",
            scores={"accuracy": 0.90},
            metrics={"latency_ms": 2000},
        )

        comparison = await engine.compare_task(sample_experiment_id, task["task_id"])

        assert "error" in comparison

    @pytest.mark.asyncio
    async def test_missing_codechef_data(
        self, initialized_engines, sample_experiment_id, sample_tasks
    ):
        """Test comparison when code-chef data is missing."""
        tracker = initialized_engines["tracker"]
        engine = initialized_engines["comparison"]

        task = sample_tasks[0]

        # Only baseline data
        await tracker.record_result(
            experiment_id=sample_experiment_id,
            task_id=task["task_id"],
            experiment_group="baseline",
            extension_version="1.0.0-test",
            model_version="baseline",
            scores={"accuracy": 0.70},
            metrics={"latency_ms": 2500},
        )

        comparison = await engine.compare_task(sample_experiment_id, task["task_id"])

        assert "error" in comparison

    @pytest.mark.asyncio
    async def test_zero_baseline_values(self, initialized_engines):
        """Test improvement calculation with zero baseline values."""
        engine = initialized_engines["comparison"]

        # Zero baseline, non-zero codechef (higher is better)
        improvement = engine.calculate_improvement(0, 0.90, "higher_is_better")
        assert improvement == 100.0

        # Zero baseline, non-zero codechef (lower is better)
        improvement = engine.calculate_improvement(0, 2000, "lower_is_better")
        assert improvement == -100.0

        # Both zero
        improvement = engine.calculate_improvement(0, 0, "higher_is_better")
        assert improvement == 0.0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_empty_experiment(self, initialized_engines, sample_experiment_id):
        """Test report generation for experiment with no data."""
        engine = initialized_engines["comparison"]

        report = await engine.generate_comparison_report(sample_experiment_id)

        assert "error" in report
        assert report["experiment_id"] == sample_experiment_id


class TestComparisonReportFormat:
    """Test comparison report structure and format."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_report_structure(
        self, initialized_engines, sample_experiment_id, sample_tasks
    ):
        """Test that report has expected structure and fields."""
        tracker = initialized_engines["tracker"]
        engine = initialized_engines["comparison"]

        # Add sample data
        task = sample_tasks[0]
        for group, scores in [
            ("baseline", {"accuracy": 0.70}),
            ("code-chef", {"accuracy": 0.90}),
        ]:
            await tracker.record_result(
                experiment_id=sample_experiment_id,
                task_id=task["task_id"],
                experiment_group=group,
                extension_version="1.0.0-test",
                model_version=f"{group}-model",
                scores=scores,
                metrics={"latency_ms": 2000},
            )

        report = await engine.generate_comparison_report(sample_experiment_id)

        # Verify top-level structure
        assert "experiment_id" in report
        assert "timestamp" in report
        assert "tasks" in report
        assert "summary" in report

        # Verify summary structure
        summary = report["summary"]
        assert "total_tasks" in summary
        assert "wins" in summary
        assert "losses" in summary
        assert "ties" in summary
        assert "avg_improvements" in summary
        assert "recommendation" in summary
        assert "reasoning" in summary

        # Verify avg_improvements structure
        improvements = summary["avg_improvements"]
        expected_metrics = [
            "accuracy",
            "completeness",
            "efficiency",
            "latency_ms",
            "cost_usd",
            "overall",
        ]
        for metric in expected_metrics:
            assert metric in improvements

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_task_comparison_structure(
        self, initialized_engines, sample_experiment_id, sample_tasks
    ):
        """Test that task comparisons have expected structure."""
        tracker = initialized_engines["tracker"]
        engine = initialized_engines["comparison"]

        task = sample_tasks[0]
        for group, scores in [
            ("baseline", {"accuracy": 0.70, "completeness": 0.75}),
            ("code-chef", {"accuracy": 0.90, "completeness": 0.88}),
        ]:
            await tracker.record_result(
                experiment_id=sample_experiment_id,
                task_id=task["task_id"],
                experiment_group=group,
                extension_version="1.0.0-test",
                model_version=f"{group}-model",
                scores=scores,
                metrics={"latency_ms": 2000, "cost_usd": 0.001},
            )

        comparison = await engine.compare_task(sample_experiment_id, task["task_id"])

        # Verify structure
        assert "task_id" in comparison
        assert "experiment_id" in comparison
        assert "baseline" in comparison
        assert "codechef" in comparison
        assert "improvements" in comparison
        assert "overall_improvement" in comparison
        assert "winner" in comparison

        # Verify improvements has all expected metrics
        improvements = comparison["improvements"]
        assert "accuracy" in improvements
        assert "completeness" in improvements
        assert "latency_ms" in improvements
        assert "cost_usd" in improvements


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
