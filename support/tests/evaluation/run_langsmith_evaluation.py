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

# LangSmith Project Configuration
# Production Project: code-chef-production (4c4a4e10-9d58-4ca1-a111-82893d6ad495)
DEFAULT_PROJECT = "code-chef-production"
PRODUCTION_PROJECT_ID = "4c4a4e10-9d58-4ca1-a111-82893d6ad495"
EVALUATION_PROJECT = "code-chef-evaluation"

# Dataset Configuration (use existing datasets)
DEFAULT_DATASET = "ib-agent-scenarios-v1"  # Existing dataset with 15 examples
GOLD_STANDARD_DATASET = "code-chef-gold-standard-v1"  # For future use

# Infrastructure Configuration
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "https://codechef.appsmithery.co")
QDRANT_ENDPOINT = os.getenv("QDRANT_CLUSTER_ENDPOINT")
HUGGINGFACE_SPACE = "alextorelli/code-chef-modelops-trainer"

# Regression thresholds
REGRESSION_THRESHOLD = 0.05  # 5% drop triggers alert
DEPLOYMENT_THRESHOLD = 0.15  # 15% improvement triggers deploy recommendation

# Metrics where lower values are better (need to invert improvement calculation)
LOWER_IS_BETTER_METRICS = {"latency", "latency_p95", "latency_p99", "cost", "tokens"}


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

    # Exact match evaluator - Simple string comparison
    def exact_match_evaluator(run: Run, example: Example) -> dict:
        """Exact match evaluator for structured outputs."""
        try:
            prediction = str(run.outputs.get("output", "")).strip().lower()
            reference = (
                str(
                    example.outputs.get(
                        "expected_output", example.outputs.get("output", "")
                    )
                )
                .strip()
                .lower()
            )

            is_match = prediction == reference

            return {
                "key": "exact_match",
                "score": 1.0 if is_match else 0.0,
                "comment": "Exact match" if is_match else "No match",
            }
        except Exception as e:
            return {"key": "exact_match", "score": 0.0, "comment": f"Error: {str(e)}"}

    evaluators.append(exact_match_evaluator)
    logger.info("Added exact_match evaluator")

    # Regex match evaluator - Pattern matching
    def regex_match_evaluator(run: Run, example: Example) -> dict:
        """Regex pattern match evaluator for expected formats."""
        import re

        try:
            output = str(run.outputs.get("output", ""))

            # Patterns to check for code-chef specific content
            patterns = [
                (
                    r"(?i)(agent|supervisor|feature[-_]dev|code[-_]review|infrastructure|cicd|documentation)",
                    "Agent routing",
                ),
                (r"(?i)(mcp|tool|server)", "MCP awareness"),
                (r"(?i)(workflow|task|execution)", "Workflow mention"),
                (r"\d+\s*(token|ms|second)", "Metrics reported"),
            ]

            matches = []
            for pattern, description in patterns:
                if re.search(pattern, output):
                    matches.append(description)

            # Check for errors (should not match)
            has_errors = bool(
                re.search(r"(?i)(error|exception|failed|traceback)", output)
            )

            score = len(matches) / len(patterns)
            if has_errors:
                score *= 0.5  # Penalize errors

            return {
                "key": "regex_match",
                "score": score,
                "comment": f"Matched: {', '.join(matches) if matches else 'none'}"
                + (" (has errors)" if has_errors else ""),
            }
        except Exception as e:
            return {"key": "regex_match", "score": 0.0, "comment": f"Error: {str(e)}"}

    evaluators.append(regex_match_evaluator)
    logger.info("Added regex_match evaluator")

    # Embedding distance evaluator - Semantic similarity
    try:
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

        def embedding_distance_evaluator(run: Run, example: Example) -> dict:
            """Embedding distance evaluator for semantic similarity."""
            try:
                prediction = str(run.outputs.get("output", ""))
                reference = str(
                    example.outputs.get(
                        "expected_output", example.outputs.get("output", "")
                    )
                )

                if not prediction or not reference:
                    return {
                        "key": "embedding_distance",
                        "score": 0.0,
                        "comment": "Missing prediction or reference",
                    }

                # Get embeddings
                pred_embedding = embeddings.embed_query(prediction)
                ref_embedding = embeddings.embed_query(reference)

                # Calculate cosine similarity
                import numpy as np

                pred_vec = np.array(pred_embedding)
                ref_vec = np.array(ref_embedding)

                similarity = np.dot(pred_vec, ref_vec) / (
                    np.linalg.norm(pred_vec) * np.linalg.norm(ref_vec)
                )

                # Convert similarity to distance (0 = identical, 1 = completely different)
                # Then invert for score (higher = better)
                score = float(
                    similarity
                )  # Similarity is already 0-1 with 1 being identical

                return {
                    "key": "embedding_distance",
                    "score": max(0.0, min(1.0, score)),
                    "comment": f"Similarity: {score:.3f}",
                }
            except Exception as e:
                return {
                    "key": "embedding_distance",
                    "score": 0.0,
                    "comment": f"Error: {str(e)}",
                }

        evaluators.append(embedding_distance_evaluator)
        logger.info("Added embedding_distance evaluator")
    except Exception as e:
        logger.warning(f"Could not create embedding_distance evaluator: {e}")

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
        llm = ChatOpenAI(model="gpt-4", temperature=0.0)

        # Helpfulness evaluator
        def helpfulness_evaluator(run: Run, example: Example) -> dict:
            """Evaluate helpfulness using GPT-4."""
            try:
                output = str(run.outputs.get("output", "") if run.outputs else "")
                query = example.inputs.get("query", "") if example.inputs else ""

                if not output or not query:
                    return {
                        "key": "helpfulness",
                        "score": 0.0,
                        "comment": "Missing output or query",
                    }

                prompt = f"""Rate the helpfulness of this response on a scale of 0.0 to 1.0.

Query: {query}

Response: {output}

Is the response helpful and actionable? Respond with ONLY a number between 0.0 and 1.0."""

                result = llm.invoke(prompt)
                score_text = result.content.strip()

                try:
                    score = float(score_text)
                    score = max(0.0, min(1.0, score))  # Clamp to [0, 1]
                except ValueError:
                    # Try to extract number from text
                    import re

                    match = re.search(r"(\d+\.?\d*)", score_text)
                    score = float(match.group(1)) if match else 0.5
                    score = max(0.0, min(1.0, score))

                return {
                    "key": "helpfulness",
                    "score": score,
                    "comment": f"Helpfulness: {score:.2f}",
                }
            except Exception as e:
                return {
                    "key": "helpfulness",
                    "score": 0.0,
                    "comment": f"Error: {str(e)}",
                }

        evaluators.append(helpfulness_evaluator)
        logger.info("Added helpfulness evaluator")

        # Accuracy evaluator
        def accuracy_evaluator(run: Run, example: Example) -> dict:
            """Evaluate technical accuracy using GPT-4."""
            try:
                output = str(run.outputs.get("output", "") if run.outputs else "")
                query = example.inputs.get("query", "") if example.inputs else ""
                expected = (
                    example.outputs.get("expected_output", "")
                    if example.outputs
                    else ""
                )

                if not output or not query:
                    return {
                        "key": "accuracy",
                        "score": 0.0,
                        "comment": "Missing output or query",
                    }

                expected_context = (
                    f"\n\nExpected output: {expected}" if expected else ""
                )

                prompt = f"""Rate the technical accuracy of this response on a scale of 0.0 to 1.0.

Query: {query}

Response: {output}{expected_context}

Is the response technically accurate and free of errors? Respond with ONLY a number between 0.0 and 1.0."""

                result = llm.invoke(prompt)
                score_text = result.content.strip()

                try:
                    score = float(score_text)
                    score = max(0.0, min(1.0, score))
                except ValueError:
                    import re

                    match = re.search(r"(\d+\.?\d*)", score_text)
                    score = float(match.group(1)) if match else 0.5
                    score = max(0.0, min(1.0, score))

                return {
                    "key": "accuracy",
                    "score": score,
                    "comment": f"Accuracy: {score:.2f}",
                }
            except Exception as e:
                return {"key": "accuracy", "score": 0.0, "comment": f"Error: {str(e)}"}

        evaluators.append(accuracy_evaluator)
        logger.info("Added accuracy evaluator")

        # MCP tool awareness evaluator
        def mcp_awareness_evaluator(run: Run, example: Example) -> dict:
            """Evaluate MCP tool usage awareness."""
            try:
                output = str(run.outputs.get("output", "") if run.outputs else "")

                # Check for MCP tool mentions
                import re

                mcp_patterns = [
                    r"(?i)(mcp[\s_-]?(server|tool|client))",
                    r"(?i)(github|linear|filesystem|memory|docker)[\s_-]?(tool|server)",
                    r"(?i)tool[\s_-]?(invoke|call|execution)",
                    r"(?i)(progressive|dynamic)[\s_-]?tool[\s_-]?loading",
                ]

                mentions = sum(
                    1 for pattern in mcp_patterns if re.search(pattern, output)
                )

                if mentions == 0:
                    score = 0.0
                    comment = "No MCP awareness (0/4 indicators)"
                elif mentions == 1:
                    score = 0.33
                    comment = "Basic MCP awareness (1/4 indicators)"
                elif mentions == 2:
                    score = 0.66
                    comment = "Good MCP awareness (2/4 indicators)"
                else:
                    score = 1.0
                    comment = f"Advanced MCP awareness ({mentions}/4 indicators)"

                return {"key": "mcp_awareness", "score": score, "comment": comment}
            except Exception as e:
                return {
                    "key": "mcp_awareness",
                    "score": 0.0,
                    "comment": f"Error: {str(e)}",
                }

        evaluators.append(mcp_awareness_evaluator)
        logger.info("Added mcp_awareness evaluator")

    except Exception as e:
        logger.error(f"Error creating LLM evaluators: {e}")
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
    logger.info(f"Using project: {EVALUATION_PROJECT}")
    logger.info(f"Dataset: {dataset_name}")
    logger.info(f"Evaluators: {len(evaluators)}")

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
            "project_id": PRODUCTION_PROJECT_ID,
            "qdrant_endpoint": QDRANT_ENDPOINT,
            "hf_space": HUGGINGFACE_SPACE,
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
            # For metrics where lower is better (latency, cost), invert the calculation
            if baseline_score > 0:
                raw_improvement_pct = (
                    (codechef_score - baseline_score) / baseline_score * 100
                )

                # Invert for "lower is better" metrics
                if metric_name.lower() in LOWER_IS_BETTER_METRICS:
                    improvement_pct = -raw_improvement_pct  # Lower is better
                    winner = (
                        "code-chef" if codechef_score < baseline_score else "baseline"
                    )
                else:
                    improvement_pct = raw_improvement_pct  # Higher is better
                    winner = (
                        "code-chef" if codechef_score > baseline_score else "baseline"
                    )
            else:
                improvement_pct = 0.0
                winner = "tie"

            comparison["per_metric"][metric_name] = {
                "baseline": baseline_score,
                "codechef": codechef_score,
                "improvement_pct": round(improvement_pct, 2),
                "winner": winner,
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
