"""
Comparison Engine - Side-by-side baseline vs code-chef performance comparison

Part of Phase 3: Testing, Tracing & Evaluation Refactoring (CHEF-241)

Features:
- Calculate improvement percentages across all metrics (latency, accuracy, cost)
- Generate task-by-task comparison reports with statistical analysis
- Query evaluation_results database for aggregate experiment summaries
- Cache comparison results in experiment_summaries table
- Export JSON reports for Grafana dashboards and LangSmith analysis

Database Integration:
- Reads from evaluation_results table (baseline vs code-chef variants)
- Writes to experiment_summaries table (cached aggregate results)
- Uses task_comparisons for correlation between runs

Usage:
    from shared.lib.comparison_engine import comparison_engine

    # Initialize (call once at startup)
    await comparison_engine.initialize()

    # Compare single task
    result = await comparison_engine.compare_task(
        experiment_id="exp-2025-01-001",
        task_id="task-550e8400-e29b-41d4-a716-446655440000",
    )

    # Generate full experiment report
    report = await comparison_engine.generate_comparison_report(
        experiment_id="exp-2025-01-001",
    )

    # Store cached summary
    await comparison_engine.store_experiment_summary(
        experiment_id="exp-2025-01-001",
    )
"""

import asyncio
import json
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional

from loguru import logger

from shared.lib.longitudinal_tracker import longitudinal_tracker


class ComparisonEngine:
    """
    Engine for comparing baseline (untrained) vs code-chef (trained) performance.

    Provides:
    - Task-level comparisons with improvement percentages
    - Experiment-level aggregate statistics
    - Win/loss/tie categorization
    - Statistical significance indicators
    - JSON export for dashboards
    """

    _instance: Optional["ComparisonEngine"] = None
    _lock: Lock = Lock()
    _initialized: bool = False

    def __new__(cls) -> "ComparisonEngine":
        """Singleton pattern - ensure only one instance exists."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self) -> None:
        """
        Initialize the comparison engine.

        Ensures longitudinal_tracker is initialized for database access.
        """
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            logger.info("Initializing ComparisonEngine")

            # Initialize dependencies
            await longitudinal_tracker.initialize()

            self._initialized = True
            logger.info("ComparisonEngine initialized successfully")

    def calculate_improvement(
        self,
        baseline_value: float,
        codechef_value: float,
        metric_type: str = "higher_is_better",
    ) -> float:
        """
        Calculate improvement percentage from baseline to code-chef.

        Args:
            baseline_value: Baseline metric value
            codechef_value: Code-chef metric value
            metric_type: "higher_is_better" (accuracy, scores) or
                        "lower_is_better" (latency, cost)

        Returns:
            Improvement percentage (positive = improvement)

        Examples:
            # Accuracy: 0.80 -> 0.92 = +15% improvement
            calculate_improvement(0.80, 0.92, "higher_is_better") -> 15.0

            # Latency: 2000ms -> 1500ms = +25% improvement (faster)
            calculate_improvement(2000, 1500, "lower_is_better") -> 25.0
        """
        if baseline_value == 0:
            # Avoid division by zero
            if codechef_value == 0:
                return 0.0
            return 100.0 if metric_type == "higher_is_better" else -100.0

        if metric_type == "higher_is_better":
            # Higher values are better (accuracy, completeness)
            return ((codechef_value - baseline_value) / baseline_value) * 100
        else:
            # Lower values are better (latency, cost)
            return ((baseline_value - codechef_value) / baseline_value) * 100

    async def compare_task(
        self,
        experiment_id: str,
        task_id: str,
    ) -> Dict[str, Any]:
        """
        Compare baseline vs code-chef for a single task.

        Args:
            experiment_id: Experiment identifier
            task_id: Task identifier

        Returns:
            Comparison dict with baseline, codechef, and improvements:
            {
                "task_id": str,
                "baseline": {...},
                "codechef": {...},
                "improvements": {
                    "accuracy": 15.2,
                    "completeness": 12.5,
                    "latency_ms": 25.3,
                    "cost_usd": 18.7,
                },
                "winner": "code-chef" | "baseline" | "tie",
            }
        """
        if not self._initialized:
            await self.initialize()

        # Query longitudinal_tracker for both variants
        comparison = await longitudinal_tracker.compare_variants(
            experiment_id=experiment_id,
            task_id=task_id,
        )

        if not comparison:
            logger.warning(
                f"No comparison data found for experiment={experiment_id}, task={task_id}"
            )
            return {
                "task_id": task_id,
                "error": "No data available",
            }

        baseline = comparison.get("baseline")
        codechef = comparison.get("codechef")

        if not baseline or not codechef:
            return {
                "task_id": task_id,
                "baseline": baseline,
                "codechef": codechef,
                "error": "Missing baseline or codechef data",
            }

        # Calculate improvements for all metrics
        improvements = {}

        # Score metrics (higher is better)
        for score_metric in [
            "accuracy",
            "completeness",
            "efficiency",
            "integration_quality",
        ]:
            baseline_score = baseline.get("scores", {}).get(score_metric, 0)
            codechef_score = codechef.get("scores", {}).get(score_metric, 0)
            improvements[score_metric] = self.calculate_improvement(
                baseline_score, codechef_score, "higher_is_better"
            )

        # Performance metrics (lower is better)
        for perf_metric in ["latency_ms", "cost_usd"]:
            baseline_perf = baseline.get("metrics", {}).get(perf_metric, 0)
            codechef_perf = codechef.get("metrics", {}).get(perf_metric, 0)
            improvements[perf_metric] = self.calculate_improvement(
                baseline_perf, codechef_perf, "lower_is_better"
            )

        # Tokens used (lower is better)
        baseline_tokens = baseline.get("metrics", {}).get("tokens_used", 0)
        codechef_tokens = codechef.get("metrics", {}).get("tokens_used", 0)
        improvements["tokens_used"] = self.calculate_improvement(
            baseline_tokens, codechef_tokens, "lower_is_better"
        )

        # Calculate overall winner based on weighted score improvements
        overall_improvement = self._calculate_weighted_improvement(improvements)
        winner = self._determine_winner(overall_improvement)

        return {
            "task_id": task_id,
            "experiment_id": experiment_id,
            "baseline": baseline,
            "codechef": codechef,
            "improvements": improvements,
            "overall_improvement": overall_improvement,
            "winner": winner,
        }

    def _calculate_weighted_improvement(self, improvements: Dict[str, float]) -> float:
        """
        Calculate weighted overall improvement score.

        Weights from llm-operations.md:
        - Accuracy: 30%
        - Completeness: 25%
        - Efficiency: 20%
        - Latency: 15%
        - Integration Quality: 10%
        """
        weights = {
            "accuracy": 0.30,
            "completeness": 0.25,
            "efficiency": 0.20,
            "latency_ms": 0.15,
            "integration_quality": 0.10,
        }

        weighted_sum = 0.0
        total_weight = 0.0

        for metric, weight in weights.items():
            if metric in improvements:
                weighted_sum += improvements[metric] * weight
                total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _determine_winner(self, overall_improvement: float) -> str:
        """
        Determine winner based on overall improvement percentage.

        Rules:
        - >5%: code-chef wins
        - <-5%: baseline wins
        - -5% to 5%: tie
        """
        if overall_improvement > 5.0:
            return "code-chef"
        elif overall_improvement < -5.0:
            return "baseline"
        else:
            return "tie"

    async def generate_comparison_report(
        self,
        experiment_id: str,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive comparison report for an experiment.

        Queries all tasks in the experiment and produces:
        - Task-by-task comparisons
        - Aggregate statistics (wins/losses/ties)
        - Average improvements across all metrics
        - Recommendation (deploy, needs_review, reject)

        Args:
            experiment_id: Experiment identifier

        Returns:
            Report dict with structure:
            {
                "experiment_id": str,
                "timestamp": str (ISO 8601),
                "tasks": [...],  # List of task comparisons
                "summary": {
                    "total_tasks": int,
                    "wins": int,
                    "losses": int,
                    "ties": int,
                    "avg_improvements": {...},
                    "recommendation": "deploy" | "needs_review" | "reject",
                },
            }
        """
        if not self._initialized:
            await self.initialize()

        logger.info(f"Generating comparison report for experiment: {experiment_id}")

        # Get experiment summary from longitudinal_tracker
        summary = await longitudinal_tracker.get_experiment_summary(experiment_id)

        if not summary:
            logger.warning(f"No summary found for experiment: {experiment_id}")
            return {
                "experiment_id": experiment_id,
                "error": "No experiment data found",
                "timestamp": datetime.now().isoformat(),
            }

        # Query all tasks for this experiment
        pool = longitudinal_tracker._pool
        if not pool:
            raise RuntimeError("LongitudinalTracker not initialized")

        async with pool.acquire() as conn:
            # Get all unique task_ids for this experiment
            task_ids = await conn.fetch(
                """
                SELECT DISTINCT task_id
                FROM evaluation_results
                WHERE experiment_id = $1
                ORDER BY created_at
                """,
                experiment_id,
            )

        # Compare each task
        task_comparisons = []
        for row in task_ids:
            task_id = row["task_id"]
            comparison = await self.compare_task(experiment_id, task_id)
            task_comparisons.append(comparison)

        # Calculate recommendation based on overall improvement
        avg_improvement = summary.get("avg_overall_improvement", 0.0)
        recommendation = self._generate_recommendation(avg_improvement)

        report = {
            "experiment_id": experiment_id,
            "timestamp": datetime.now().isoformat(),
            "tasks": task_comparisons,
            "summary": {
                "total_tasks": summary.get("total_tasks", 0),
                "wins": summary.get("wins", 0),
                "losses": summary.get("losses", 0),
                "ties": summary.get("ties", 0),
                "avg_improvements": {
                    "accuracy": summary.get("avg_accuracy_improvement", 0.0),
                    "completeness": summary.get("avg_completeness_improvement", 0.0),
                    "efficiency": summary.get("avg_efficiency_improvement", 0.0),
                    "latency_ms": summary.get("avg_latency_improvement", 0.0),
                    "cost_usd": summary.get("avg_cost_improvement", 0.0),
                    "overall": avg_improvement,
                },
                "recommendation": recommendation,
                "reasoning": self._generate_reasoning(avg_improvement, summary),
            },
        }

        logger.info(
            f"Report generated: {report['summary']['total_tasks']} tasks, "
            f"recommendation={recommendation}"
        )

        return report

    def _generate_recommendation(self, avg_improvement: float) -> str:
        """
        Generate deployment recommendation based on improvement.

        From llm-operations.md:
        - >15%: deploy
        - 5-15%: needs_review
        - <5%: reject
        """
        if avg_improvement >= 15.0:
            return "deploy"
        elif avg_improvement >= 5.0:
            return "needs_review"
        else:
            return "reject"

    def _generate_reasoning(
        self, avg_improvement: float, summary: Dict[str, Any]
    ) -> str:
        """Generate human-readable reasoning for the recommendation."""
        wins = summary.get("wins", 0)
        losses = summary.get("losses", 0)
        total = summary.get("total_tasks", 0)

        if avg_improvement >= 15.0:
            return (
                f"Significant improvement ({avg_improvement:.1f}%) across all metrics. "
                f"Code-chef won {wins}/{total} tasks. Deploy recommended."
            )
        elif avg_improvement >= 5.0:
            return (
                f"Moderate improvement ({avg_improvement:.1f}%). "
                f"Code-chef won {wins}/{total} tasks. Manual validation recommended."
            )
        elif avg_improvement > -5.0:
            return (
                f"Minimal improvement ({avg_improvement:.1f}%). "
                f"No significant difference detected. Reject deployment."
            )
        else:
            return (
                f"Performance degradation ({avg_improvement:.1f}%). "
                f"Baseline won {losses}/{total} tasks. Reject deployment."
            )

    async def store_experiment_summary(
        self,
        experiment_id: str,
    ) -> None:
        """
        Store cached experiment summary in database.

        Queries evaluation_results, calculates aggregate metrics,
        and upserts into experiment_summaries table.

        Args:
            experiment_id: Experiment identifier
        """
        if not self._initialized:
            await self.initialize()

        logger.info(f"Storing experiment summary for: {experiment_id}")

        # Generate report (includes all calculations)
        report = await self.generate_comparison_report(experiment_id)

        if "error" in report:
            logger.warning(f"Cannot store summary: {report['error']}")
            return

        summary = report["summary"]

        # Insert/update experiment_summaries table
        pool = longitudinal_tracker._pool
        if not pool:
            raise RuntimeError("LongitudinalTracker not initialized")

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO experiment_summaries (
                    experiment_id,
                    total_tasks,
                    wins,
                    losses,
                    ties,
                    avg_accuracy_improvement,
                    avg_completeness_improvement,
                    avg_efficiency_improvement,
                    avg_latency_improvement,
                    avg_cost_improvement,
                    avg_overall_improvement,
                    recommendation,
                    created_at,
                    updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW(), NOW())
                ON CONFLICT (experiment_id)
                DO UPDATE SET
                    total_tasks = EXCLUDED.total_tasks,
                    wins = EXCLUDED.wins,
                    losses = EXCLUDED.losses,
                    ties = EXCLUDED.ties,
                    avg_accuracy_improvement = EXCLUDED.avg_accuracy_improvement,
                    avg_completeness_improvement = EXCLUDED.avg_completeness_improvement,
                    avg_efficiency_improvement = EXCLUDED.avg_efficiency_improvement,
                    avg_latency_improvement = EXCLUDED.avg_latency_improvement,
                    avg_cost_improvement = EXCLUDED.avg_cost_improvement,
                    avg_overall_improvement = EXCLUDED.avg_overall_improvement,
                    recommendation = EXCLUDED.recommendation,
                    updated_at = NOW()
                """,
                experiment_id,
                summary["total_tasks"],
                summary["wins"],
                summary["losses"],
                summary["ties"],
                summary["avg_improvements"]["accuracy"],
                summary["avg_improvements"]["completeness"],
                summary["avg_improvements"]["efficiency"],
                summary["avg_improvements"]["latency_ms"],
                summary["avg_improvements"]["cost_usd"],
                summary["avg_improvements"]["overall"],
                summary["recommendation"],
            )

        logger.info(
            f"Stored summary for {experiment_id}: "
            f"{summary['total_tasks']} tasks, recommendation={summary['recommendation']}"
        )

    async def export_report_json(
        self,
        experiment_id: str,
        output_path: str,
    ) -> None:
        """
        Export comparison report to JSON file.

        Args:
            experiment_id: Experiment identifier
            output_path: Output file path (e.g., "results/exp-2025-01-001.json")
        """
        report = await self.generate_comparison_report(experiment_id)

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Exported report to: {output_path}")


# Singleton instance
comparison_engine = ComparisonEngine()
