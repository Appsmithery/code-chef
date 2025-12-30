"""
Complete LangSmith evaluation automation using evaluate() API.

This script provides automated evaluation with:
- LangSmith's evaluate() API integration
- Custom evaluator wrappers
- Prebuilt LangSmith evaluators
- LLM-as-judge evaluators
- Parallel execution
- Automatic trace lineage
- Regression detection

Usage:
    # Run evaluation on existing dataset
    python support/tests/evaluation/run_langsmith_evaluation.py \
        --dataset code-chef-gold-standard-v1 \
        --experiment-prefix eval-weekly

    # Run with baseline comparison
    python support/tests/evaluation/run_langsmith_evaluation.py \
        --dataset code-chef-gold-standard-v1 \
        --compare-baseline

    # Run with custom evaluators only
    python support/tests/evaluation/run_langsmith_evaluation.py \
        --dataset code-chef-gold-standard-v1 \
        --evaluators-only custom

Linear Issue: DEV-195
Documentation: support/docs/operations/LLM_OPERATIONS.md
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project paths
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

import httpx
from loguru import logger

# LangSmith imports
try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from langsmith import Client
    from langsmith.evaluation import LangChainStringEvaluator, evaluate
    from langsmith.schemas import Example, Run

    LANGSMITH_AVAILABLE = True
except ImportError as e:
    logger.error(f"LangSmith dependencies not available: {e}")
    logger.error("Install with: pip install langsmith langchain-openai")
    LANGSMITH_AVAILABLE = False
    sys.exit(1)

# Import custom evaluators
from support.tests.evaluation.evaluators import (
    ALL_EVALUATORS,
    EVALUATOR_MAP,
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

# Import longitudinal tracker for regression detection
try:
    sys.path.insert(0, str(project_root / "shared"))
    from lib.longitudinal_tracker import longitudinal_tracker

    TRACKER_AVAILABLE = True
except ImportError:
    TRACKER_AVAILABLE = False
    logger.warning("Longitudinal tracker not available - regression detection disabled")


# =============================================================================
# CONFIGURATION
# =============================================================================

DEFAULT_DATASET = "code-chef-gold-standard-v1"
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "https://codechef.appsmithery.co")
DEFAULT_PROJECT = os.getenv("LANGCHAIN_PROJECT", "code-chef-evaluation")

# Regression thresholds
REGRESSION_THRESHOLD = 0.05  # 5% drop triggers alert
DEPLOYMENT_THRESHOLD = 0.15  # 15% improvement triggers deploy recommendation


# =============================================================================
# EVALUATOR WRAPPERS
# =============================================================================


def wrap_evaluator(evaluator_fn):
    """
    Convert custom evaluator to LangSmith evaluate() format.

    LangSmith evaluate() expects evaluators to return dict with:
    - key: str (evaluator name)
    - score: float (0.0 to 1.0)
    - comment: str (optional explanation)

    Args:
        evaluator_fn: Custom evaluator function returning EvaluationResult

    Returns:
        Wrapped evaluator function compatible with evaluate()
    """

    def wrapped(run: Run, example: Example) -> dict:
        """Wrapped evaluator compatible with LangSmith evaluate()."""
        try:
            result = evaluator_fn(run, example)
            return {
                "key": result.key,
                "score": result.score,
                "comment": result.comment or "",
            }
        except Exception as e:
            logger.error(f"Evaluator {evaluator_fn.__name__} failed: {e}")
            return {
                "key": evaluator_fn.__name__,
                "score": 0.0,
                "comment": f"Error: {str(e)}",
            }

    # Preserve function name for debugging
    wrapped.__name__ = f"wrapped_{evaluator_fn.__name__}"
    return wrapped


def get_prebuilt_evaluators() -> List:
    """
    Get LangSmith prebuilt evaluators.

    Returns:
        List of prebuilt evaluators (no LLM required)
    """
    evaluators = []

    # Try to load LangChain evaluators, but don't fail if not available
    try:
        # Embedding distance for semantic similarity
        try:
            evaluators.append(
                LangChainStringEvaluator(
                    "embedding_distance",
                    config={
                        "embeddings": OpenAIEmbeddings(),
                        "distance_metric": "cosine",
                    },
                )
            )
        except Exception as e:
            logger.warning(f"Could not create embedding_distance evaluator: {e}")

        # Exact match for structured outputs
        try:
            evaluators.append(LangChainStringEvaluator("exact_match"))
        except Exception as e:
            logger.warning(f"Could not create exact_match evaluator: {e}")

        # Regex match for expected patterns
        try:
            evaluators.append(
                LangChainStringEvaluator(
                    "regex_match",
                    config={
                        "patterns": [
                            r"MCP server",
                            r"tool",
                            r"agent",
                            r"workflow",
                        ]
                    },
                )
            )
        except Exception as e:
            logger.warning(f"Could not create regex_match evaluator: {e}")

    except Exception as e:
        logger.error(f"LangChain evaluators not available: {e}")
        logger.info("Install langchain with: pip install langchain")

    return evaluators


def get_llm_evaluators() -> List:
    """
    Get LLM-as-judge evaluators for semantic correctness.

    Returns:
        List of LLM-based evaluators
    """
    evaluators = []

    try:
        # Use GPT-4 for judge (higher quality, worth the cost for evals)
        llm = ChatOpenAI(model_name="gpt-4", temperature=0.0)

        # Criteria-based evaluation
        try:
            evaluators.append(
                LangChainStringEvaluator(
                    "criteria",
                    config={
                        "criteria": {
                            "helpfulness": "Is the response helpful and actionable?",
                            "accuracy": "Is the response factually correct?",
                            "completeness": "Does it address all parts of the question?",
                        },
                        "llm": llm,
                    },
                )
            )
        except Exception as e:
            logger.warning(f"Could not create criteria evaluator: {e}")

        # Labeled criteria with rubric (for MCP awareness)
        try:
            evaluators.append(
                LangChainStringEvaluator(
                    "labeled_criteria",
                    config={
                        "criteria": {
                            "mcp_awareness": {
                                "0": "Doesn't mention MCP or tools",
                                "1": "Mentions MCP but incorrectly",
                                "2": "Correctly identifies MCP servers and tool count",
                            }
                        },
                        "llm": llm,
                    },
                )
            )
        except Exception as e:
            logger.warning(f"Could not create labeled_criteria evaluator: {e}")

    except Exception as e:
        logger.error(f"LLM evaluators not available: {e}")
        logger.info("Install langchain-openai with: pip install langchain-openai")

    return evaluators


# =============================================================================
# TARGET SYSTEM
# =============================================================================


async def code_chef_target(inputs: dict) -> dict:
    """
    Target system for evaluation - invokes code-chef orchestrator.

    Args:
        inputs: Dict with 'query' key containing user message

    Returns:
        Dict with 'output', 'agent', 'tokens' keys
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/api/execute",
                json={
                    "message": inputs["query"],
                    "user_id": inputs.get("user_id", "eval-user"),
                    "mode": inputs.get("mode", "auto"),
                },
            )
            response.raise_for_status()

            data = response.json()
            return {
                "output": data.get("response", ""),
                "agent": data.get("agent_used"),
                "tokens": data.get("token_usage"),
            }

        except Exception as e:
            logger.error(f"Target system error: {e}")
            return {
                "output": f"Error: {str(e)}",
                "agent": None,
                "tokens": None,
            }


async def baseline_target(inputs: dict) -> dict:
    """
    Baseline target for comparison - uses untrained LLM.

    Args:
        inputs: Dict with 'query' key containing user message

    Returns:
        Dict with 'output', 'agent', 'tokens' keys
    """
    # Use basic LLM without code-chef enhancements
    try:
        llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.7)
        response = await llm.ainvoke(inputs["query"])
        return {
            "output": response.content,
            "agent": "baseline_llm",
            "tokens": None,
        }
    except Exception as e:
        logger.error(f"Baseline system error: {e}")
        return {
            "output": f"Error: {str(e)}",
            "agent": "baseline_llm",
            "tokens": None,
        }


# =============================================================================
# EVALUATION RUNNER
# =============================================================================


async def run_evaluation(
    dataset_name: str,
    experiment_prefix: str = "eval",
    evaluators_only: str = "all",
    compare_baseline: bool = False,
    max_concurrency: int = 5,
) -> Dict[str, Any]:
    """
    Run LangSmith evaluation with evaluate() API.

    Args:
        dataset_name: Name of evaluation dataset
        experiment_prefix: Prefix for experiment name
        evaluators_only: 'all', 'custom', 'prebuilt', 'llm'
        compare_baseline: Whether to also run baseline comparison
        max_concurrency: Number of parallel evaluations

    Returns:
        Evaluation results summary
    """
    client = Client()

    # Build evaluator list based on selection
    evaluators = []

    if evaluators_only in ["all", "custom"]:
        # Add wrapped custom evaluators
        evaluators.extend([wrap_evaluator(e) for e in ALL_EVALUATORS])
        logger.info(f"Added {len(ALL_EVALUATORS)} custom evaluators")

    if evaluators_only in ["all", "prebuilt"]:
        # Add LangSmith prebuilt evaluators
        prebuilt = get_prebuilt_evaluators()
        evaluators.extend(prebuilt)
        logger.info(f"Added {len(prebuilt)} prebuilt evaluators")

    if evaluators_only in ["all", "llm"]:
        # Add LLM-as-judge evaluators
        llm_evals = get_llm_evaluators()
        evaluators.extend(llm_evals)
        logger.info(f"Added {len(llm_evals)} LLM evaluators")

    if not evaluators:
        raise ValueError(f"No evaluators selected for mode: {evaluators_only}")

    logger.info(f"Running evaluation with {len(evaluators)} total evaluators")

    # Generate experiment name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    experiment_name = f"{experiment_prefix}-{timestamp}"

    # Run code-chef evaluation
    logger.info(f"Running code-chef evaluation: {experiment_name}")
    codechef_results = await evaluate(
        code_chef_target,
        data=dataset_name,
        evaluators=evaluators,
        experiment_prefix=experiment_name,
        metadata={
            "experiment_group": "code-chef",
            "environment": "evaluation",
            "extension_version": os.getenv("EXTENSION_VERSION", "1.0.0"),
            "model_version": os.getenv("MODEL_VERSION", "production"),
        },
        max_concurrency=max_concurrency,
        client=client,
    )

    logger.info(f"Code-chef evaluation complete")
    logger.info(f"Results: {codechef_results['project_url']}")

    results = {
        "code_chef": {
            "experiment_name": experiment_name,
            "results": codechef_results,
        }
    }

    # Run baseline comparison if requested
    if compare_baseline:
        baseline_experiment = f"{experiment_prefix}-baseline-{timestamp}"
        logger.info(f"Running baseline evaluation: {baseline_experiment}")

        baseline_results = await evaluate(
            baseline_target,
            data=dataset_name,
            evaluators=evaluators,
            experiment_prefix=baseline_experiment,
            metadata={
                "experiment_group": "baseline",
                "environment": "evaluation",
                "extension_version": os.getenv("EXTENSION_VERSION", "1.0.0"),
                "model_version": "baseline",
            },
            max_concurrency=max_concurrency,
            client=client,
        )

        logger.info(f"Baseline evaluation complete")
        logger.info(f"Results: {baseline_results['project_url']}")

        results["baseline"] = {
            "experiment_name": baseline_experiment,
            "results": baseline_results,
        }

        # Calculate improvement
        results["comparison"] = calculate_improvement(
            baseline_results, codechef_results
        )

    return results


def calculate_improvement(
    baseline_results: Dict[str, Any], codechef_results: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate improvement metrics comparing baseline to code-chef.

    Args:
        baseline_results: Baseline evaluation results dict with 'results' key
        codechef_results: Code-chef evaluation results dict with 'results' key

    Returns:
        Comparison summary with improvement percentages
    """
    comparison = {
        "overall_improvement_pct": 0.0,
        "per_metric": {},
        "recommendation": "reject",
        "reasoning": "",
    }

    # Extract aggregate metrics - handle nested structure
    baseline_metrics = baseline_results.get("results", {})
    if "results" in baseline_metrics:
        baseline_metrics = baseline_metrics["results"]

    codechef_metrics = codechef_results.get("results", {})
    if "results" in codechef_metrics:
        codechef_metrics = codechef_metrics["results"]

    if not baseline_metrics or not codechef_metrics:
        comparison["reasoning"] = "Missing metrics for comparison"
        return comparison

    # Calculate per-metric improvements
    improvements = []
    for metric_name, baseline_score in baseline_metrics.items():
        if metric_name in codechef_metrics:
            codechef_score = codechef_metrics[metric_name]

            # Calculate percentage improvement
            if baseline_score > 0:
                improvement_pct = (
                    (codechef_score - baseline_score) / baseline_score * 100
                )
            else:
                improvement_pct = 0.0

            comparison["per_metric"][metric_name] = {
                "baseline": baseline_score,
                "codechef": codechef_score,
                "improvement_pct": round(improvement_pct, 2),
                "winner": (
                    "code-chef" if codechef_score > baseline_score else "baseline"
                ),
            }

            improvements.append(improvement_pct)

    # Calculate overall improvement (average across metrics)
    if improvements:
        comparison["overall_improvement_pct"] = round(
            sum(improvements) / len(improvements), 2
        )

    # Determine recommendation
    overall_improvement = comparison["overall_improvement_pct"]

    if overall_improvement >= DEPLOYMENT_THRESHOLD * 100:
        comparison["recommendation"] = "deploy"
        comparison["reasoning"] = (
            f"Significant improvement ({overall_improvement:.1f}%) across all metrics"
        )
    elif overall_improvement >= REGRESSION_THRESHOLD * 100:
        comparison["recommendation"] = "needs_review"
        comparison["reasoning"] = (
            f"Moderate improvement ({overall_improvement:.1f}%), manual validation recommended"
        )
    else:
        comparison["recommendation"] = "reject"
        comparison["reasoning"] = (
            f"Insufficient improvement ({overall_improvement:.1f}%) or regression detected"
        )

    return comparison


async def check_regression(results: Dict[str, Any]) -> bool:
    """
    Check for performance regression and create Linear issue if detected.

    Args:
        results: Evaluation results

    Returns:
        True if regression detected, False otherwise
    """
    if not TRACKER_AVAILABLE:
        logger.warning("Regression detection skipped - tracker not available")
        return False

    # Check if any metric dropped significantly
    comparison = results.get("comparison", {})
    overall_improvement = comparison.get("overall_improvement_pct", 0.0)

    if overall_improvement < -REGRESSION_THRESHOLD * 100:
        logger.error(
            f"Regression detected: {overall_improvement:.1f}% performance drop"
        )

        # Create Linear issue
        try:
            from shared.lib.linear_client import linear_client

            await linear_client.create_issue(
                title=f"Evaluation Regression Detected: {overall_improvement:.1f}% drop",
                description=f"""
Automated evaluation detected a performance regression:

**Overall Improvement**: {overall_improvement:.1f}%

**Per-Metric Results**:
{json.dumps(comparison.get('per_metric', {}), indent=2)}

**Recommendation**: {comparison.get('recommendation', 'N/A')}

**Action Required**: Investigate root cause and consider rollback.

**Evaluation Details**:
- Dataset: {results.get('code_chef', {}).get('experiment_name', 'N/A')}
- Timestamp: {datetime.now().isoformat()}
                """,
                project="CHEF",
                labels=["regression", "automated-eval", "urgent"],
            )
            logger.info("Created Linear issue for regression")
        except Exception as e:
            logger.error(f"Failed to create Linear issue: {e}")

        return True

    return False


# =============================================================================
# CLI
# =============================================================================


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run LangSmith evaluation with evaluate() API"
    )
    parser.add_argument(
        "--dataset",
        default=DEFAULT_DATASET,
        help=f"Dataset name (default: {DEFAULT_DATASET})",
    )
    parser.add_argument(
        "--experiment-prefix",
        default="eval",
        help="Experiment name prefix (default: eval)",
    )
    parser.add_argument(
        "--evaluators-only",
        choices=["all", "custom", "prebuilt", "llm"],
        default="all",
        help="Which evaluators to use (default: all)",
    )
    parser.add_argument(
        "--compare-baseline",
        action="store_true",
        help="Run baseline comparison (default: False)",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        default=5,
        help="Max concurrent evaluations (default: 5)",
    )
    parser.add_argument(
        "--output",
        help="Output file for results (JSON)",
    )

    args = parser.parse_args()

    # Run evaluation
    logger.info("Starting LangSmith evaluation...")
    results = await run_evaluation(
        dataset_name=args.dataset,
        experiment_prefix=args.experiment_prefix,
        evaluators_only=args.evaluators_only,
        compare_baseline=args.compare_baseline,
        max_concurrency=args.max_concurrency,
    )

    # Check for regression
    if args.compare_baseline:
        await check_regression(results)

    # Output results
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json.dumps(results, indent=2))
        logger.info(f"Results written to: {output_path}")
    else:
        print("\n" + "=" * 80)
        print("EVALUATION RESULTS")
        print("=" * 80)
        print(json.dumps(results, indent=2))

    logger.info("Evaluation complete!")


if __name__ == "__main__":
    asyncio.run(main())
