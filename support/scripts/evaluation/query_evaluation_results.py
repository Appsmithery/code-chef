"""Query utilities for evaluation results from database.

Provides helper functions to retrieve and analyze evaluation results stored
in the longitudinal_tracker database for:
- Time-series analysis across extension versions
- A/B comparison between baseline and code-chef
- Longitudinal performance trends
- Export for visualization

Part of Phase 4: Testing, Tracing & Evaluation Refactoring (CHEF-242)

Usage:
    # Get metric trends for an agent
    python support/scripts/evaluation/query_evaluation_results.py \
        --agent feature_dev --metric accuracy --days 30

    # Compare experiment results
    python support/scripts/evaluation/query_evaluation_results.py \
        --experiment exp-2025-01-001 --compare

    # Export to CSV for Grafana
    python support/scripts/evaluation/query_evaluation_results.py \
        --agent feature_dev --export results.csv --days 90

    # Get experiment summary
    python support/scripts/evaluation/query_evaluation_results.py \
        --experiment exp-2025-01-001 --summary
"""

import argparse
import asyncio
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "shared"))

from lib.longitudinal_tracker import longitudinal_tracker
from loguru import logger


async def get_metric_trend(
    agent_name: str,
    metric: str,
    experiment_group: str = "code-chef",
    days: int = 30,
) -> List[Dict]:
    """Get time-series trend for a metric.

    Args:
        agent_name: Agent to query
        metric: accuracy, completeness, efficiency, or integration_quality
        experiment_group: 'baseline' or 'code-chef'
        days: Number of days to look back

    Returns:
        List of trend data points
    """
    if not longitudinal_tracker._initialized:
        await longitudinal_tracker.initialize()

    trend = await longitudinal_tracker.get_metric_trend(
        agent_name=agent_name,
        metric=metric,
        experiment_group=experiment_group,
        days=days,
    )

    return trend


async def compare_experiment(experiment_id: str, task_id: Optional[str] = None) -> Dict:
    """Compare baseline vs code-chef for an experiment.

    Args:
        experiment_id: Experiment identifier
        task_id: Optional specific task to compare

    Returns:
        Comparison data or summary
    """
    if not longitudinal_tracker._initialized:
        await longitudinal_tracker.initialize()

    if task_id:
        # Compare specific task
        comparison = await longitudinal_tracker.compare_variants(
            experiment_id=experiment_id,
            task_id=task_id,
        )
        return comparison
    else:
        # Get experiment summary
        summary = await longitudinal_tracker.get_experiment_summary(
            experiment_id=experiment_id
        )
        return summary


async def export_to_csv(
    agent_name: str,
    output_path: str,
    experiment_group: str = "code-chef",
    days: int = 90,
):
    """Export evaluation results to CSV for visualization.

    Args:
        agent_name: Agent to query
        output_path: Path to output CSV file
        experiment_group: 'baseline' or 'code-chef'
        days: Number of days to look back
    """
    if not longitudinal_tracker._initialized:
        await longitudinal_tracker.initialize()

    # Query all metrics
    metrics = ["accuracy", "completeness", "efficiency", "integration_quality"]
    all_data = []

    for metric in metrics:
        trend = await longitudinal_tracker.get_metric_trend(
            agent_name=agent_name,
            metric=metric,
            experiment_group=experiment_group,
            days=days,
        )

        for point in trend:
            all_data.append(
                {
                    "extension_version": point["extension_version"],
                    "model_version": point["model_version"],
                    "metric": metric,
                    "avg_score": point["avg_score"],
                    "min_score": point["min_score"],
                    "max_score": point["max_score"],
                    "sample_count": point["sample_count"],
                    "last_recorded": point["last_recorded"],
                }
            )

    # Write to CSV
    if all_data:
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
            writer.writeheader()
            writer.writerows(all_data)

        logger.info(f"✓ Exported {len(all_data)} data points to {output_path}")
    else:
        logger.warning("No data to export")


async def print_metric_trend(
    agent_name: str,
    metric: str,
    experiment_group: str = "code-chef",
    days: int = 30,
):
    """Print metric trend to console in formatted table."""
    trend = await get_metric_trend(agent_name, metric, experiment_group, days)

    if not trend:
        logger.warning(f"No trend data found for {agent_name} / {metric}")
        return

    print(f"\n{'=' * 80}")
    print(f"Metric Trend: {agent_name} / {metric} / {experiment_group}")
    print(f"{'=' * 80}\n")

    print(
        f"{'Version':<20} {'Model':<25} {'Avg':<8} {'Min':<8} {'Max':<8} {'Samples':<8} {'Last Recorded'}"
    )
    print("-" * 100)

    for point in trend:
        print(
            f"{point['extension_version']:<20} "
            f"{point['model_version']:<25} "
            f"{point['avg_score']:<8.3f} "
            f"{point['min_score']:<8.3f} "
            f"{point['max_score']:<8.3f} "
            f"{point['sample_count']:<8} "
            f"{point['last_recorded']}"
        )

    print()


async def print_comparison(experiment_id: str, task_id: Optional[str] = None):
    """Print comparison results to console."""
    comparison = await compare_experiment(experiment_id, task_id)

    if "error" in comparison:
        logger.error(f"Error: {comparison['error']}")
        return

    print(f"\n{'=' * 80}")
    print(f"Experiment Comparison: {experiment_id}")
    if task_id:
        print(f"Task: {task_id}")
    print(f"{'=' * 80}\n")

    if task_id:
        # Detailed task comparison
        print(f"Agent: {comparison.get('agent_name', 'N/A')}")
        print(f"Version: {comparison.get('extension_version', 'N/A')}\n")

        print("Baseline Results:")
        for metric, value in comparison.get("baseline", {}).items():
            print(f"  {metric}: {value:.3f}" if value else f"  {metric}: N/A")

        print("\nCode-chef Results:")
        for metric, value in comparison.get("codechef", {}).items():
            print(f"  {metric}: {value:.3f}" if value else f"  {metric}: N/A")

        print("\nImprovements:")
        for metric, pct in comparison.get("improvements", {}).items():
            print(f"  {metric}: {pct:+.1f}%")

    else:
        # Experiment summary
        print(f"Total Tasks: {comparison.get('total_tasks', 0)}")
        print(f"Code-chef Wins: {comparison.get('codechef_wins', 0)}")
        print(f"Baseline Wins: {comparison.get('baseline_wins', 0)}")
        print(f"Ties: {comparison.get('ties', 0)}\n")

        print("Average Improvements:")
        print(f"  Accuracy: {comparison.get('avg_accuracy_improvement_pct', 0):+.1f}%")
        print(
            f"  Latency Reduction: {comparison.get('avg_latency_reduction_pct', 0):+.1f}%"
        )
        print(f"  Cost Reduction: {comparison.get('avg_cost_reduction_pct', 0):+.1f}%")

    print()


async def get_recent_evaluations(
    agent_name: Optional[str] = None,
    experiment_group: Optional[str] = None,
    limit: int = 10,
) -> List[Dict]:
    """Get most recent evaluation results.

    Args:
        agent_name: Filter by agent (optional)
        experiment_group: Filter by baseline/code-chef (optional)
        limit: Max results to return

    Returns:
        List of recent evaluation results
    """
    if not longitudinal_tracker._initialized:
        await longitudinal_tracker.initialize()

    async with longitudinal_tracker.pool.acquire() as conn:
        query = """
            SELECT
                result_id,
                experiment_id,
                task_id,
                experiment_group,
                extension_version,
                model_version,
                agent_name,
                accuracy,
                completeness,
                efficiency,
                integration_quality,
                latency_ms,
                tokens_used,
                cost_usd,
                created_at
            FROM evaluation_results
            WHERE 1=1
        """
        params = []

        if agent_name:
            params.append(agent_name)
            query += f" AND agent_name = ${len(params)}"

        if experiment_group:
            params.append(experiment_group)
            query += f" AND experiment_group = ${len(params)}"

        params.append(limit)
        query += f" ORDER BY created_at DESC LIMIT ${len(params)}"

        rows = await conn.fetch(query, *params)

    return [dict(row) for row in rows]


async def print_recent_evaluations(
    agent_name: Optional[str] = None,
    experiment_group: Optional[str] = None,
    limit: int = 10,
):
    """Print recent evaluation results to console."""
    results = await get_recent_evaluations(agent_name, experiment_group, limit)

    if not results:
        logger.warning("No recent evaluations found")
        return

    print(f"\n{'=' * 120}")
    print(f"Recent Evaluations (limit: {limit})")
    if agent_name:
        print(f"Agent: {agent_name}")
    if experiment_group:
        print(f"Group: {experiment_group}")
    print(f"{'=' * 120}\n")

    print(
        f"{'Experiment ID':<30} {'Task ID':<12} {'Agent':<15} {'Group':<10} {'Acc':<6} {'Comp':<6} {'Created'}"
    )
    print("-" * 120)

    for result in results:
        acc = f"{result['accuracy']:.3f}" if result["accuracy"] else "N/A"
        comp = f"{result['completeness']:.3f}" if result["completeness"] else "N/A"
        created = result["created_at"].strftime("%Y-%m-%d %H:%M")

        print(
            f"{result['experiment_id']:<30} "
            f"{result['task_id'][:12]:<12} "
            f"{result['agent_name'] or 'N/A':<15} "
            f"{result['experiment_group']:<10} "
            f"{acc:<6} "
            f"{comp:<6} "
            f"{created}"
        )

    print()


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Query and analyze evaluation results from database"
    )

    # Operation selection
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument(
        "--trend", action="store_true", help="Show metric trend over time"
    )
    operation.add_argument(
        "--compare", action="store_true", help="Compare baseline vs code-chef"
    )
    operation.add_argument("--export", type=str, help="Export to CSV file")
    operation.add_argument(
        "--recent", action="store_true", help="Show recent evaluations"
    )
    operation.add_argument(
        "--summary", action="store_true", help="Show experiment summary"
    )

    # Parameters
    parser.add_argument("--agent", type=str, help="Agent name (e.g., feature_dev)")
    parser.add_argument(
        "--metric",
        type=str,
        choices=["accuracy", "completeness", "efficiency", "integration_quality"],
        help="Metric to query",
    )
    parser.add_argument("--experiment", type=str, help="Experiment ID")
    parser.add_argument("--task", type=str, help="Task ID (for detailed comparison)")
    parser.add_argument(
        "--group",
        type=str,
        choices=["baseline", "code-chef"],
        default="code-chef",
        help="Experiment group (default: code-chef)",
    )
    parser.add_argument(
        "--days", type=int, default=30, help="Number of days to look back (default: 30)"
    )
    parser.add_argument(
        "--limit", type=int, default=10, help="Max results to return (default: 10)"
    )

    args = parser.parse_args()

    # Validate arguments
    if args.trend:
        if not args.agent or not args.metric:
            parser.error("--trend requires --agent and --metric")
        await print_metric_trend(args.agent, args.metric, args.group, args.days)

    elif args.compare or args.summary:
        if not args.experiment:
            parser.error("--compare/--summary requires --experiment")
        await print_comparison(args.experiment, args.task)

    elif args.export:
        if not args.agent:
            parser.error("--export requires --agent")
        await export_to_csv(args.agent, args.export, args.group, args.days)

    elif args.recent:
        await print_recent_evaluations(args.agent, args.group, args.limit)


if __name__ == "__main__":
    asyncio.run(main())
