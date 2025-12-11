"""
Longitudinal Tracker - Performance tracking across extension versions and experiments

Part of Phase 1: Testing, Tracing & Evaluation Refactoring (CHEF-239)

Features:
- Store evaluation results with experiment_id, task_id, experiment_group correlation
- Time-series queries for longitudinal trends across extension versions
- A/B comparison between baseline and code-chef variants
- Thread-safe async operations with connection pooling
- Prometheus metrics export for real-time monitoring

Database Schema:
- evaluation_results: Main table with scores, metrics, timestamps
- task_comparisons: Correlation table linking baseline ↔ code-chef runs
- experiment_summaries: Cached aggregate results for experiments

Usage:
    from shared.lib.longitudinal_tracker import longitudinal_tracker

    # Initialize (call once at startup)
    await longitudinal_tracker.initialize()

    # Record evaluation result
    await longitudinal_tracker.record_result(
        experiment_id="exp-2025-01-001",
        task_id="task-550e8400-e29b-41d4-a716-446655440000",
        experiment_group="code-chef",
        extension_version="1.2.3",
        model_version="qwen-coder-32b-v2",
        agent_name="feature_dev",
        scores={
            "accuracy": 0.92,
            "completeness": 0.88,
            "efficiency": 0.85,
            "integration_quality": 0.90,
        },
        metrics={
            "latency_ms": 1850.5,
            "tokens_used": 2450,
            "cost_usd": 0.00172,
        },
    )

    # Get longitudinal trend
    trend = await longitudinal_tracker.get_metric_trend(
        agent_name="feature_dev",
        metric="accuracy",
        days=30,
    )

    # Compare baseline vs code-chef
    comparison = await longitudinal_tracker.compare_variants(
        experiment_id="exp-2025-01-001",
        task_id="task-550e8400-e29b-41d4-a716-446655440000",
    )
"""

import asyncio
import os
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, List, Optional

import asyncpg
from loguru import logger
from prometheus_client import Counter, Gauge, Histogram

# Prometheus metrics
eval_results_total = Counter(
    "eval_results_total",
    "Total evaluation results stored",
    ["agent", "experiment_group", "extension_version"],
)

eval_score_gauge = Gauge(
    "eval_score_current",
    "Current evaluation scores",
    ["agent", "experiment_group", "metric"],
)

eval_latency_ms = Histogram(
    "eval_latency_ms",
    "Evaluation task latency in milliseconds",
    ["agent", "experiment_group"],
    buckets=[100, 500, 1000, 2000, 5000, 10000, 30000, 60000],
)

eval_cost_usd = Histogram(
    "eval_cost_usd",
    "Evaluation task cost in USD",
    ["agent", "experiment_group"],
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5],
)


class LongitudinalTracker:
    """
    Track evaluation performance across time and experiments.

    Thread-safe async singleton for storing and querying evaluation results
    with PostgreSQL + Prometheus integration.
    """

    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self._lock = Lock()
        self._initialized = False
        self.start_time = datetime.utcnow()
        logger.info("LongitudinalTracker initialized (pending database connection)")

    async def initialize(self, db_url: Optional[str] = None):
        """
        Initialize database connection pool and create tables.

        Args:
            db_url: PostgreSQL connection string (defaults to DATABASE_URL env var)
        """
        if self._initialized:
            logger.warning("LongitudinalTracker already initialized")
            return

        db_url = db_url or os.getenv(
            "DATABASE_URL",
            os.getenv(
                "TEST_DATABASE_URL",
                "postgresql://postgres:postgres@localhost:5432/devtools",
            ),
        )

        try:
            self.pool = await asyncpg.create_pool(
                db_url,
                min_size=2,
                max_size=10,
                command_timeout=30,
            )
            logger.info(
                f"✓ Database pool created: {db_url.split('@')[1] if '@' in db_url else 'localhost'}"
            )

            # Load schema
            schema_path = os.path.join(
                os.path.dirname(__file__), "../../config/state/evaluation_results.sql"
            )

            if os.path.exists(schema_path):
                async with self.pool.acquire() as conn:
                    with open(schema_path, "r") as f:
                        schema_sql = f.read()
                    await conn.execute(schema_sql)
                logger.info("✓ Evaluation results schema loaded")
            else:
                logger.warning(f"Schema file not found: {schema_path}")

            self._initialized = True
            logger.info("✓ LongitudinalTracker ready")

        except Exception as e:
            logger.error(f"✗ Failed to initialize LongitudinalTracker: {e}")
            raise

    async def close(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("LongitudinalTracker connection pool closed")
            self._initialized = False

    async def record_result(
        self,
        experiment_id: str,
        task_id: str,
        experiment_group: str,
        extension_version: str,
        model_version: str,
        scores: Dict[str, float],
        metrics: Dict[str, float],
        agent_name: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Record an evaluation result.

        Args:
            experiment_id: Unique experiment identifier
            task_id: Task identifier (correlates baseline + code-chef)
            experiment_group: 'baseline' or 'code-chef'
            extension_version: Version string (e.g., "1.2.3")
            model_version: Model identifier (e.g., "qwen-coder-32b-v2")
            scores: Dict with accuracy, completeness, efficiency, integration_quality (0-1)
            metrics: Dict with latency_ms, tokens_used, cost_usd
            agent_name: Optional agent name
            success: Whether evaluation succeeded
            error_message: Optional error message
            metadata: Additional context

        Returns:
            result_id (UUID string)
        """
        if not self._initialized:
            raise RuntimeError(
                "LongitudinalTracker not initialized. Call initialize() first."
            )

        if experiment_group not in ["baseline", "code-chef"]:
            raise ValueError(
                f"Invalid experiment_group: {experiment_group}. Must be 'baseline' or 'code-chef'."
            )

        async with self.pool.acquire() as conn:
            result_id = await conn.fetchval(
                """
                INSERT INTO evaluation_results (
                    experiment_id, task_id, experiment_group,
                    extension_version, model_version, agent_name,
                    accuracy, completeness, efficiency, integration_quality,
                    latency_ms, tokens_used, cost_usd,
                    success, error_message, metadata
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
                )
                ON CONFLICT (experiment_id, task_id, experiment_group, extension_version)
                DO UPDATE SET
                    model_version = EXCLUDED.model_version,
                    agent_name = EXCLUDED.agent_name,
                    accuracy = EXCLUDED.accuracy,
                    completeness = EXCLUDED.completeness,
                    efficiency = EXCLUDED.efficiency,
                    integration_quality = EXCLUDED.integration_quality,
                    latency_ms = EXCLUDED.latency_ms,
                    tokens_used = EXCLUDED.tokens_used,
                    cost_usd = EXCLUDED.cost_usd,
                    success = EXCLUDED.success,
                    error_message = EXCLUDED.error_message,
                    metadata = EXCLUDED.metadata
                RETURNING result_id
                """,
                experiment_id,
                task_id,
                experiment_group,
                extension_version,
                model_version,
                agent_name,
                scores.get("accuracy"),
                scores.get("completeness"),
                scores.get("efficiency"),
                scores.get("integration_quality"),
                metrics.get("latency_ms"),
                metrics.get("tokens_used"),
                metrics.get("cost_usd"),
                success,
                error_message,
                metadata or {},
            )

        # Export to Prometheus
        if agent_name:
            eval_results_total.labels(
                agent=agent_name,
                experiment_group=experiment_group,
                extension_version=extension_version,
            ).inc()

            # Update gauges for latest scores
            for metric_name, value in scores.items():
                if value is not None:
                    eval_score_gauge.labels(
                        agent=agent_name,
                        experiment_group=experiment_group,
                        metric=metric_name,
                    ).set(value)

            # Record histograms
            if metrics.get("latency_ms"):
                eval_latency_ms.labels(
                    agent=agent_name, experiment_group=experiment_group
                ).observe(metrics["latency_ms"])
            if metrics.get("cost_usd"):
                eval_cost_usd.labels(
                    agent=agent_name, experiment_group=experiment_group
                ).observe(metrics["cost_usd"])

        logger.debug(
            f"[LongitudinalTracker] Recorded: {experiment_group} | {task_id[:8]}... | "
            f"{agent_name or 'N/A'} | acc={scores.get('accuracy', 0):.2f}"
        )

        return str(result_id)

    async def get_metric_trend(
        self,
        agent_name: str,
        metric: str,
        experiment_group: str = "code-chef",
        days: int = 30,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get longitudinal trend for a specific agent and metric.

        Args:
            agent_name: Agent to query
            metric: One of: accuracy, completeness, efficiency, integration_quality
            experiment_group: 'baseline' or 'code-chef'
            days: Number of days to look back
            limit: Max results to return

        Returns:
            List of dicts with extension_version, avg_score, min_score, max_score, sample_count
        """
        if not self._initialized:
            raise RuntimeError("LongitudinalTracker not initialized")

        if metric not in [
            "accuracy",
            "completeness",
            "efficiency",
            "integration_quality",
        ]:
            raise ValueError(f"Invalid metric: {metric}")

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT
                    extension_version,
                    model_version,
                    AVG({metric}) as avg_score,
                    MIN({metric}) as min_score,
                    MAX({metric}) as max_score,
                    COUNT(*) as sample_count,
                    MAX(created_at) as last_recorded
                FROM evaluation_results
                WHERE agent_name = $1
                  AND experiment_group = $2
                  AND created_at >= NOW() - INTERVAL '{days} days'
                  AND {metric} IS NOT NULL
                GROUP BY extension_version, model_version
                ORDER BY last_recorded DESC
                LIMIT $3
                """,
                agent_name,
                experiment_group,
                limit,
            )

        return [
            {
                "extension_version": row["extension_version"],
                "model_version": row["model_version"],
                "avg_score": float(row["avg_score"]) if row["avg_score"] else None,
                "min_score": float(row["min_score"]) if row["min_score"] else None,
                "max_score": float(row["max_score"]) if row["max_score"] else None,
                "sample_count": row["sample_count"],
                "last_recorded": (
                    row["last_recorded"].isoformat() if row["last_recorded"] else None
                ),
            }
            for row in rows
        ]

    async def compare_variants(
        self,
        experiment_id: str,
        task_id: str,
    ) -> Dict[str, Any]:
        """
        Compare baseline vs code-chef for a specific task.

        Args:
            experiment_id: Experiment identifier
            task_id: Task identifier

        Returns:
            Dict with baseline, codechef, and improvements keys
        """
        if not self._initialized:
            raise RuntimeError("LongitudinalTracker not initialized")

        async with self.pool.acquire() as conn:
            # Use the pre-built comparison view
            row = await conn.fetchrow(
                """
                SELECT * FROM evaluation_comparison_view
                WHERE experiment_id = $1 AND task_id = $2
                LIMIT 1
                """,
                experiment_id,
                task_id,
            )

            if not row:
                return {
                    "error": "No comparison data found",
                    "experiment_id": experiment_id,
                    "task_id": task_id,
                }

            return {
                "experiment_id": experiment_id,
                "task_id": task_id,
                "agent_name": row["agent_name"],
                "extension_version": row["extension_version"],
                "baseline": {
                    "accuracy": (
                        float(row["baseline_accuracy"])
                        if row["baseline_accuracy"]
                        else None
                    ),
                    "latency_ms": (
                        float(row["baseline_latency_ms"])
                        if row["baseline_latency_ms"]
                        else None
                    ),
                    "cost_usd": (
                        float(row["baseline_cost_usd"])
                        if row["baseline_cost_usd"]
                        else None
                    ),
                    "completeness": (
                        float(row["baseline_completeness"])
                        if row["baseline_completeness"]
                        else None
                    ),
                },
                "codechef": {
                    "accuracy": (
                        float(row["codechef_accuracy"])
                        if row["codechef_accuracy"]
                        else None
                    ),
                    "latency_ms": (
                        float(row["codechef_latency_ms"])
                        if row["codechef_latency_ms"]
                        else None
                    ),
                    "cost_usd": (
                        float(row["codechef_cost_usd"])
                        if row["codechef_cost_usd"]
                        else None
                    ),
                    "completeness": (
                        float(row["codechef_completeness"])
                        if row["codechef_completeness"]
                        else None
                    ),
                },
                "improvements": {
                    "accuracy_pct": (
                        float(row["accuracy_improvement_pct"])
                        if row["accuracy_improvement_pct"]
                        else 0
                    ),
                    "latency_reduction_pct": (
                        float(row["latency_reduction_pct"])
                        if row["latency_reduction_pct"]
                        else 0
                    ),
                    "cost_reduction_pct": (
                        float(row["cost_reduction_pct"])
                        if row["cost_reduction_pct"]
                        else 0
                    ),
                },
            }

    async def get_experiment_summary(self, experiment_id: str) -> Dict[str, Any]:
        """
        Get aggregate summary for an experiment.

        Args:
            experiment_id: Experiment identifier

        Returns:
            Dict with wins/losses/ties and average improvements
        """
        if not self._initialized:
            raise RuntimeError("LongitudinalTracker not initialized")

        async with self.pool.acquire() as conn:
            summary = await conn.fetchrow(
                """
                SELECT * FROM experiment_summaries
                WHERE experiment_id = $1
                """,
                experiment_id,
            )

            if summary:
                return dict(summary)

            # Calculate on-the-fly if not cached
            comparisons = await conn.fetch(
                """
                SELECT * FROM evaluation_comparison_view
                WHERE experiment_id = $1
                """,
                experiment_id,
            )

            if not comparisons:
                return {
                    "error": "No results for experiment",
                    "experiment_id": experiment_id,
                }

            wins = 0
            losses = 0
            ties = 0
            accuracy_improvements = []
            latency_reductions = []
            cost_reductions = []

            for comp in comparisons:
                acc_imp = comp["accuracy_improvement_pct"] or 0
                if acc_imp > 5:
                    wins += 1
                elif acc_imp < -5:
                    losses += 1
                else:
                    ties += 1

                accuracy_improvements.append(acc_imp)
                if comp["latency_reduction_pct"]:
                    latency_reductions.append(comp["latency_reduction_pct"])
                if comp["cost_reduction_pct"]:
                    cost_reductions.append(comp["cost_reduction_pct"])

            return {
                "experiment_id": experiment_id,
                "total_tasks": len(comparisons),
                "codechef_wins": wins,
                "baseline_wins": losses,
                "ties": ties,
                "avg_accuracy_improvement_pct": (
                    sum(accuracy_improvements) / len(accuracy_improvements)
                    if accuracy_improvements
                    else 0
                ),
                "avg_latency_reduction_pct": (
                    sum(latency_reductions) / len(latency_reductions)
                    if latency_reductions
                    else 0
                ),
                "avg_cost_reduction_pct": (
                    sum(cost_reductions) / len(cost_reductions)
                    if cost_reductions
                    else 0
                ),
            }


# Global singleton instance
longitudinal_tracker = LongitudinalTracker()
