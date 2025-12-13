"""
LangSmith Evaluation Runner for IB-Agent Platform scenarios.

Runs evaluations against traced runs using custom evaluators.
Outputs results as JSON and optionally creates Linear issues for failures.

Usage:
    python support/tests/evaluation/run_evaluation.py --dataset ib-agent-scenarios-v1
    python support/tests/evaluation/run_evaluation.py --dataset ib-agent-scenarios-v1 --output results.json
    python support/tests/evaluation/run_evaluation.py --list-datasets

Linear Issue: DEV-195
Test Project: https://github.com/Appsmithery/IB-Agent
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project paths
sys.path.insert(0, str(Path(__file__).parent / "../../.."))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Lazy import langsmith
try:
    from langsmith import Client
    from langsmith.evaluation import evaluate

    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    logger.warning("LangSmith SDK not installed. Run: pip install langsmith")

# Import evaluators
from support.tests.evaluation.evaluators import (
    ALL_EVALUATORS,
    agent_routing_accuracy,
    latency_threshold,
    mcp_integration_quality,
    modelops_deployment_success,
    modelops_training_quality,
    risk_assessment_accuracy,
    streaming_response_quality,
    token_efficiency,
    workflow_completeness,
)

# Import longitudinal tracker for database persistence
try:
    from shared.lib.longitudinal_tracker import longitudinal_tracker

    TRACKER_AVAILABLE = True
except ImportError:
    TRACKER_AVAILABLE = False
    logger.warning(
        "Longitudinal tracker not available - results will not be persisted to database"
    )

# =============================================================================
# EVALUATION CONFIGURATION
# =============================================================================

DEFAULT_DATASET = "ib-agent-scenarios-v1"
DEFAULT_PROJECT = os.getenv("LANGCHAIN_PROJECT", "code-chef-testing")

# Score thresholds for pass/fail
SCORE_THRESHOLDS = {
    "agent_routing_accuracy": 0.7,
    "token_efficiency": 0.6,
    "latency_threshold": 0.8,
    "workflow_completeness": 0.7,
    "mcp_integration_quality": 0.6,
    "risk_assessment_accuracy": 0.7,
    "streaming_response_quality": 0.7,
}


def get_client() -> Optional["Client"]:
    """Get LangSmith client if available."""
    if not LANGSMITH_AVAILABLE:
        logger.error("LangSmith SDK not available")
        return None

    api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        logger.error("LANGCHAIN_API_KEY not set")
        return None

    return Client()


def list_datasets(client: "Client") -> None:
    """List all available datasets."""
    datasets = list(client.list_datasets())

    print(f"\n{'Dataset Name':<40} {'Examples':<10} {'Created':<25}")
    print("-" * 75)

    for ds in datasets:
        created = str(ds.created_at)[:25] if ds.created_at else "N/A"
        print(f"{ds.name:<40} {ds.example_count or 0:<10} {created}")

    print()


def list_recent_runs(client: "Client", project: str, hours: int = 24) -> List[Any]:
    """List recent runs from a project."""
    runs = list(
        client.list_runs(
            project_name=project,
            start_time=datetime.now() - timedelta(hours=hours),
            run_type="chain",
        )
    )
    return runs


async def run_evaluation(
    client: "Client",
    dataset_name: str,
    project_name: str,
    evaluators: Optional[List] = None,
    experiment_id: Optional[str] = None,
    experiment_group: str = "code-chef",
    extension_version: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run evaluation on a dataset using specified evaluators.

    Args:
        client: LangSmith client
        dataset_name: Name of the dataset to evaluate
        project_name: LangSmith project containing runs
        evaluators: List of evaluator functions (default: all)
        experiment_id: Experiment ID for correlation (default: auto-generated)
        experiment_group: 'baseline' or 'code-chef' (default: 'code-chef')
        extension_version: Extension version for tracking (default: from env)

    Returns:
        Evaluation results summary
    """
    if evaluators is None:
        evaluators = ALL_EVALUATORS

    # Generate experiment_id if not provided
    if not experiment_id:
        experiment_id = f"eval-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Get extension version
    if not extension_version:
        extension_version = os.getenv("EXTENSION_VERSION", "1.0.0")

    # Initialize longitudinal tracker if available
    if TRACKER_AVAILABLE and not longitudinal_tracker._initialized:
        try:
            await longitudinal_tracker.initialize()
            logger.info("✓ Longitudinal tracker initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize tracker: {e}")

    # Get dataset
    datasets = list(client.list_datasets(dataset_name=dataset_name))
    if not datasets:
        logger.error(f"Dataset not found: {dataset_name}")
        return {"error": f"Dataset not found: {dataset_name}"}

    dataset = datasets[0]
    logger.info(
        f"Running evaluation on dataset: {dataset_name} ({dataset.example_count} examples)"
    )

    # Get recent runs from project
    runs = list_recent_runs(client, project_name, hours=24)
    logger.info(f"Found {len(runs)} runs in project: {project_name}")

    if not runs:
        logger.warning("No recent runs to evaluate")
        return {
            "dataset": dataset_name,
            "project": project_name,
            "runs_evaluated": 0,
            "warning": "No recent runs found",
        }

    # Run evaluation
    results = {
        "dataset": dataset_name,
        "project": project_name,
        "timestamp": datetime.now().isoformat(),
        "runs_evaluated": len(runs),
        "evaluators": [e.__name__ for e in evaluators],
        "scores": {},
        "failures": [],
        "summary": {},
    }

    # Evaluate each run against matching examples
    examples = list(client.list_examples(dataset_id=dataset.id))

    # Track all scores per run for database storage
    run_scores = {}  # run_id -> {metric: score}
    run_metadata = {}  # run_id -> metadata

    for evaluator in evaluators:
        eval_name = evaluator.__name__
        scores = []

        for run in runs[: min(len(runs), len(examples))]:
            # Match run to example with proper task_id correlation
            example_idx = runs.index(run) % len(examples)
            example = examples[example_idx]

            # Get task_id from run metadata or example.id
            task_id = getattr(run, "metadata", {}).get("task_id") or str(example.id)

            # Initialize score tracking for this run
            run_id_str = str(run.id)
            if run_id_str not in run_scores:
                run_scores[run_id_str] = {}
                run_metadata[run_id_str] = {
                    "task_id": task_id,
                    "agent_name": getattr(run, "metadata", {}).get("agent")
                    or getattr(run, "metadata", {}).get("agent_name"),
                    "model_version": getattr(run, "metadata", {}).get(
                        "model_version", "unknown"
                    ),
                    "latency_ms": getattr(run, "latency", 0),
                    "tokens_used": getattr(run, "total_tokens", 0),
                    "cost_usd": getattr(run, "total_cost", 0),
                }

            try:
                result = evaluator(run, example)
                scores.append(result.score)

                # Store score for this run
                metric_name = eval_name.replace("_", "")
                run_scores[run_id_str][metric_name] = result.score

                # Track failures
                threshold = SCORE_THRESHOLDS.get(eval_name, 0.7)
                if result.score < threshold:
                    results["failures"].append(
                        {
                            "evaluator": eval_name,
                            "run_id": run_id_str,
                            "task_id": task_id,
                            "score": result.score,
                            "threshold": threshold,
                            "comment": result.comment,
                        }
                    )
            except Exception as e:
                logger.error(f"Evaluator {eval_name} failed on run {run.id}: {e}")
                scores.append(0.0)

        if scores:
            avg_score = sum(scores) / len(scores)
            results["scores"][eval_name] = {
                "average": round(avg_score, 3),
                "min": round(min(scores), 3),
                "max": round(max(scores), 3),
                "count": len(scores),
            }

    # Generate summary
    all_scores = [v["average"] for v in results["scores"].values()]
    evaluators_passed = sum(
        1
        for eval_name, v in results["scores"].items()
        if v["average"] >= SCORE_THRESHOLDS.get(eval_name, 0.7)
    )
    results["summary"] = {
        "overall_score": (
            round(sum(all_scores) / len(all_scores), 3) if all_scores else 0.0
        ),
        "evaluators_passed": evaluators_passed,
        "total_evaluators": len(evaluators),
        "failure_count": len(results["failures"]),
    }

    # Store results in database
    if TRACKER_AVAILABLE and longitudinal_tracker._initialized:
        stored_count = 0
        for run_id_str, scores_dict in run_scores.items():
            metadata = run_metadata.get(run_id_str, {})
            task_id = metadata.get("task_id", run_id_str)

            try:
                await longitudinal_tracker.record_result(
                    experiment_id=experiment_id,
                    task_id=task_id,
                    experiment_group=experiment_group,
                    extension_version=extension_version,
                    model_version=metadata.get("model_version", "unknown"),
                    agent_name=metadata.get("agent_name"),
                    scores={
                        "accuracy": scores_dict.get("agentroutingaccuracy"),
                        "completeness": scores_dict.get("workflowcompleteness"),
                        "efficiency": scores_dict.get("tokenefficiency"),
                        "integration_quality": scores_dict.get("mcpintegrationquality"),
                    },
                    metrics={
                        "latency_ms": metadata.get("latency_ms", 0),
                        "tokens_used": metadata.get("tokens_used", 0),
                        "cost_usd": metadata.get("cost_usd", 0),
                    },
                    success=True,
                    metadata={
                        "project": project_name,
                        "dataset": dataset_name,
                        "run_id": run_id_str,
                    },
                )
                stored_count += 1
            except Exception as e:
                logger.error(f"Failed to store result for run {run_id_str}: {e}")

        logger.info(
            f"✓ Stored {stored_count}/{len(run_scores)} evaluation results in database"
        )
        results["database_stored"] = stored_count

    return results


def print_results(results: Dict[str, Any]) -> None:
    """Print evaluation results to console."""
    print("\n" + "=" * 60)
    print("LANGSMITH EVALUATION RESULTS")
    print("=" * 60)

    print(f"\nDataset: {results.get('dataset', 'N/A')}")
    print(f"Project: {results.get('project', 'N/A')}")
    print(f"Runs Evaluated: {results.get('runs_evaluated', 0)}")
    print(f"Timestamp: {results.get('timestamp', 'N/A')}")

    if "warning" in results:
        print(f"\n⚠️  Warning: {results['warning']}")
        return

    if "error" in results:
        print(f"\n❌ Error: {results['error']}")
        return

    # Score table
    print(f"\n{'Evaluator':<30} {'Avg Score':<12} {'Min':<8} {'Max':<8} {'Status'}")
    print("-" * 70)

    for eval_name, scores in results.get("scores", {}).items():
        threshold = SCORE_THRESHOLDS.get(eval_name, 0.7)
        status = "✅ PASS" if scores["average"] >= threshold else "❌ FAIL"
        print(
            f"{eval_name:<30} {scores['average']:<12.3f} {scores['min']:<8.3f} {scores['max']:<8.3f} {status}"
        )

    # Summary
    summary = results.get("summary", {})
    print(f"\n{'=' * 60}")
    print(f"Overall Score: {summary.get('overall_score', 0):.1%}")
    print(f"Failures: {summary.get('failure_count', 0)}")

    # Show failures
    failures = results.get("failures", [])
    if failures:
        print(f"\n⚠️  Top Failures:")
        for f in failures[:5]:
            print(
                f"  - {f['evaluator']}: {f['score']:.3f} < {f['threshold']} ({f['comment'][:50]}...)"
            )


def save_results(results: Dict[str, Any], output_path: str) -> None:
    """Save results to JSON file."""
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"Results saved to: {output_path}")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run LangSmith evaluations for IB-Agent Platform scenarios"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=DEFAULT_DATASET,
        help=f"Dataset name to evaluate (default: {DEFAULT_DATASET})",
    )
    parser.add_argument(
        "--project",
        type=str,
        default=DEFAULT_PROJECT,
        help=f"LangSmith project name (default: {DEFAULT_PROJECT})",
    )
    parser.add_argument("--output", type=str, help="Output JSON file for results")
    parser.add_argument(
        "--list-datasets", action="store_true", help="List available datasets"
    )
    parser.add_argument(
        "--evaluators",
        type=str,
        nargs="+",
        choices=list(SCORE_THRESHOLDS.keys()),
        help="Specific evaluators to run (default: all)",
    )
    parser.add_argument(
        "--experiment-id",
        type=str,
        help="Experiment ID for correlation (default: auto-generated)",
    )
    parser.add_argument(
        "--experiment-group",
        type=str,
        choices=["baseline", "code-chef"],
        default="code-chef",
        help="Experiment group for A/B testing (default: code-chef)",
    )
    parser.add_argument(
        "--extension-version",
        type=str,
        help="Extension version for tracking (default: from EXTENSION_VERSION env)",
    )

    args = parser.parse_args()

    # Check LangSmith availability
    if not LANGSMITH_AVAILABLE:
        print("❌ LangSmith SDK not installed. Run: pip install langsmith")
        sys.exit(1)

    # Get client
    client = get_client()
    if not client:
        print("❌ Could not initialize LangSmith client. Check LANGCHAIN_API_KEY.")
        sys.exit(1)

    # List datasets
    if args.list_datasets:
        list_datasets(client)
        return

    # Select evaluators
    evaluators = ALL_EVALUATORS
    if args.evaluators:
        from support.tests.evaluation.evaluators import get_evaluators

        evaluators = get_evaluators(args.evaluators)

    # Run evaluation
    results = await run_evaluation(
        client=client,
        dataset_name=args.dataset,
        project_name=args.project,
        evaluators=evaluators,
        experiment_id=args.experiment_id,
        experiment_group=args.experiment_group,
        extension_version=args.extension_version,
    )

    # Print results
    print_results(results)

    # Save results
    if args.output:
        save_results(results, args.output)

    # Exit code based on failures
    failure_count = results.get("summary", {}).get("failure_count", 0)
    if failure_count > 0:
        logger.warning(f"Evaluation completed with {failure_count} failures")
        sys.exit(1)

    logger.info("Evaluation completed successfully")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
