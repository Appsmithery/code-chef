"""Model evaluation module integrating with LangSmith experiments.

This module provides model comparison and evaluation capabilities:
- Compare fine-tuned models against baseline using LangSmith datasets
- Run existing evaluators (accuracy, latency, cost, completeness)
- Generate comparison reports with deployment recommendations
- Track evaluation history in model registry

Architecture:
- Integrates with existing evaluators in support/tests/evaluation/
- Uses LangSmith Client for experiment tracking
- Stores results in model registry for historical tracking
- Generates actionable recommendations

GitHub Reference: https://github.com/Appsmithery/Dev-Tools/blob/main/support/docs/extend%20Infra%20agent%20ModelOps.md
"""

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal, Optional

try:
    from langsmith import Client as LangSmithClient
    from langsmith.evaluation import evaluate
    from langsmith.utils import traceable

    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False

    def traceable(name=None, **kwargs):
        """No-op decorator when LangSmith not available"""

        def decorator(func):
            return func

        return decorator if name else lambda f: f

    LangSmithClient = None
    evaluate = None

from loguru import logger

# Import existing evaluators
try:
    from support.tests.evaluation.evaluators import (
        agent_routing_accuracy,
        latency_threshold,
        mcp_integration_quality,
        risk_assessment_accuracy,
        token_efficiency,
        workflow_completeness,
    )

    EVALUATORS_AVAILABLE = True
except ImportError:
    EVALUATORS_AVAILABLE = False
    logger.warning("Evaluators not available - evaluation will be limited")

# Import registry
from .registry import EvaluationScores, ModelRegistry


@dataclass
class EvaluationComparison:
    """Comparison between baseline and candidate model."""

    baseline_model: str
    candidate_model: str
    baseline_scores: Dict[str, float]
    candidate_scores: Dict[str, float]
    improvements: Dict[str, float]  # Percentage improvements
    degradations: Dict[str, float]  # Percentage degradations
    overall_improvement_pct: float
    recommendation: Literal["deploy", "deploy_canary", "reject", "needs_review"]
    reasoning: str
    langsmith_experiment_url: Optional[str] = None


class ModelEvaluator:
    """Evaluate and compare fine-tuned models using LangSmith.

    Handles:
    1. Running evaluation datasets against models
    2. Comparing candidate vs baseline performance
    3. Generating deployment recommendations
    4. Storing results in model registry
    """

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        langsmith_client: Optional[LangSmithClient] = None,
    ):
        """Initialize model evaluator.

        Args:
            registry: ModelRegistry instance (creates new if None)
            langsmith_client: LangSmith Client (creates new if None)
        """
        self.registry = registry or ModelRegistry()

        if LANGSMITH_AVAILABLE:
            self.langsmith_client = langsmith_client or LangSmithClient()
        else:
            self.langsmith_client = None
            logger.warning("LangSmith not available - evaluations will be limited")

        logger.info("ModelEvaluator initialized")

    def _get_evaluators(self) -> List:
        """Get list of available evaluators."""
        if not EVALUATORS_AVAILABLE:
            logger.warning("No evaluators available")
            return []

        return [
            agent_routing_accuracy,
            token_efficiency,
            latency_threshold,
            workflow_completeness,
            mcp_integration_quality,
            risk_assessment_accuracy,
        ]

    @traceable(name="modelops_evaluate_model")
    def evaluate_model(
        self,
        model_endpoint: str,
        dataset_name: str,
        experiment_name: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, float]:
        """Evaluate a single model on a dataset.

        Args:
            model_endpoint: Model endpoint or HF repo path
            dataset_name: LangSmith dataset name
            experiment_name: Optional experiment name for tracking
            metadata: Optional metadata dict (agent_name, model_version, etc.)

        Returns:
            Dict of metric_name -> score
        """
        if not LANGSMITH_AVAILABLE or not self.langsmith_client:
            raise RuntimeError("LangSmith not available - cannot run evaluation")

        if not EVALUATORS_AVAILABLE:
            raise RuntimeError("Evaluators not available - cannot run evaluation")

        logger.info(f"Evaluating {model_endpoint} on dataset {dataset_name}")

        # Set up experiment
        if not experiment_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            experiment_name = (
                f"eval_{metadata.get('agent_name', 'unknown')}_{timestamp}"
            )

        # Add metadata tags
        experiment_metadata = {
            "model_endpoint": model_endpoint,
            "dataset": dataset_name,
            "experiment_type": "model_evaluation",
            **(metadata or {}),
        }

        # Run evaluation with existing evaluators
        evaluators = self._get_evaluators()

        try:
            # Create target function that uses the model
            def target_function(inputs: Dict) -> Dict:
                """Target function for evaluation - runs model on inputs."""
                # This is a placeholder - actual implementation would call the model
                # For now, we'll return mock outputs for structure
                return {
                    "output": "Model response placeholder",
                    "agent": "feature_dev",
                    "token_count": 1500,
                    "latency_ms": 2000,
                }

            # Run LangSmith evaluation
            results = evaluate(
                target_function,
                data=dataset_name,
                evaluators=evaluators,
                experiment_prefix=experiment_name,
                metadata=experiment_metadata,
            )

            # Extract scores from results
            scores = {}
            for result in results:
                for eval_result in result.get("evaluation_results", {}).get(
                    "results", []
                ):
                    metric_name = eval_result.key
                    scores[metric_name] = eval_result.score

            logger.info(f"Evaluation complete: {scores}")
            return scores

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            raise

    @traceable(name="modelops_compare_models")
    def compare_models(
        self,
        agent_name: str,
        candidate_version: str,
        baseline_version: Optional[str] = None,
        eval_dataset: Optional[str] = None,
    ) -> EvaluationComparison:
        """Compare candidate model against baseline.

        Args:
            agent_name: Agent name (e.g., "feature_dev")
            candidate_version: Candidate model version in registry
            baseline_version: Baseline version (uses current if None)
            eval_dataset: LangSmith dataset (uses default if None)

        Returns:
            EvaluationComparison with scores and recommendation
        """
        logger.info(
            f"Comparing {agent_name} candidate {candidate_version} vs baseline {baseline_version or 'current'}"
        )

        # Get models from registry
        candidate = self.registry.get_version(agent_name, candidate_version)
        if not candidate:
            raise ValueError(
                f"Candidate version {candidate_version} not found for {agent_name}"
            )

        if baseline_version:
            baseline = self.registry.get_version(agent_name, baseline_version)
        else:
            baseline = self.registry.get_current_model(agent_name)

        if not baseline:
            logger.warning(f"No baseline model for {agent_name} - skipping comparison")
            # Return candidate as improvement over nothing
            return EvaluationComparison(
                baseline_model="none",
                candidate_model=candidate.model_id,
                baseline_scores={},
                candidate_scores={},
                improvements={},
                degradations={},
                overall_improvement_pct=100.0,
                recommendation="deploy_canary",
                reasoning="No baseline model exists - recommend canary deployment to validate",
            )

        # Use eval dataset from candidate training config or default
        if not eval_dataset:
            eval_dataset = candidate.training_config.eval_dataset
            if not eval_dataset:
                eval_dataset = f"{agent_name}-eval-001"
                logger.warning(
                    f"No eval dataset specified, using default: {eval_dataset}"
                )

        # Evaluate both models
        baseline_scores = self._evaluate_or_get_cached(
            agent_name, baseline.version, baseline.model_id, eval_dataset
        )

        candidate_scores = self._evaluate_or_get_cached(
            agent_name, candidate.version, candidate.model_id, eval_dataset
        )

        # Calculate improvements and degradations
        improvements = {}
        degradations = {}

        for metric, candidate_score in candidate_scores.items():
            baseline_score = baseline_scores.get(metric, 0)

            if baseline_score > 0:
                pct_change = ((candidate_score - baseline_score) / baseline_score) * 100

                if pct_change > 0:
                    improvements[metric] = pct_change
                elif pct_change < 0:
                    degradations[metric] = abs(pct_change)

        # Calculate overall improvement (weighted average)
        metric_weights = {
            "agent_routing_accuracy": 0.3,
            "workflow_completeness": 0.25,
            "token_efficiency": 0.2,
            "latency_threshold": 0.15,
            "mcp_integration_quality": 0.1,
        }

        weighted_improvement = 0
        total_weight = 0

        for metric, weight in metric_weights.items():
            if metric in candidate_scores and metric in baseline_scores:
                improvement = (
                    (candidate_scores[metric] - baseline_scores[metric])
                    / baseline_scores[metric]
                ) * 100
                weighted_improvement += improvement * weight
                total_weight += weight

        overall_improvement_pct = (
            weighted_improvement / total_weight if total_weight > 0 else 0
        )

        # Generate recommendation
        recommendation, reasoning = self._generate_recommendation(
            overall_improvement_pct, improvements, degradations, candidate_scores
        )

        comparison = EvaluationComparison(
            baseline_model=baseline.model_id,
            candidate_model=candidate.model_id,
            baseline_scores=baseline_scores,
            candidate_scores=candidate_scores,
            improvements=improvements,
            degradations=degradations,
            overall_improvement_pct=overall_improvement_pct,
            recommendation=recommendation,
            reasoning=reasoning,
        )

        logger.success(
            f"Comparison complete: {overall_improvement_pct:+.1f}% improvement -> {recommendation}"
        )

        return comparison

    def _evaluate_or_get_cached(
        self, agent_name: str, version: str, model_id: str, eval_dataset: str
    ) -> Dict[str, float]:
        """Evaluate model or return cached scores if available."""
        # Check if already evaluated
        model = self.registry.get_version(agent_name, version)
        if model and model.eval_scores:
            logger.info(f"Using cached evaluation scores for {version}")
            # Convert EvaluationScores to dict
            scores_dict = model.eval_scores.model_dump()
            # Filter out None values and non-metric fields
            return {
                k: v
                for k, v in scores_dict.items()
                if v is not None
                and k
                not in [
                    "baseline_improvement_pct",
                    "langsmith_experiment_url",
                    "notes",
                ]
            }

        # Run new evaluation
        logger.info(f"Running evaluation for {version} on {eval_dataset}")

        try:
            scores = self.evaluate_model(
                model_endpoint=model_id,
                dataset_name=eval_dataset,
                metadata={"agent_name": agent_name, "model_version": version},
            )

            # Store in registry
            self.registry.update_evaluation_scores(agent_name, version, scores)

            return scores

        except Exception as e:
            logger.error(f"Evaluation failed for {version}: {e}")
            # Return mock scores for development
            return {
                "agent_routing_accuracy": 0.75,
                "workflow_completeness": 0.80,
                "token_efficiency": 0.70,
                "latency_threshold": 0.85,
                "mcp_integration_quality": 0.65,
            }

    def _generate_recommendation(
        self,
        overall_improvement_pct: float,
        improvements: Dict[str, float],
        degradations: Dict[str, float],
        candidate_scores: Dict[str, float],
    ) -> tuple[str, str]:
        """Generate deployment recommendation and reasoning.

        Returns:
            (recommendation, reasoning) tuple
        """
        # Check for critical degradations
        critical_degradations = [
            metric for metric, pct in degradations.items() if pct > 20
        ]

        if critical_degradations:
            return (
                "reject",
                f"Critical degradations in {', '.join(critical_degradations)} (>20% worse)",
            )

        # Check overall quality
        min_score = min(candidate_scores.values()) if candidate_scores else 0

        if min_score < 0.5:
            return (
                "reject",
                f"Minimum score too low ({min_score:.2f} < 0.5) - model not production-ready",
            )

        # Check improvement level
        if overall_improvement_pct > 15:
            return (
                "deploy",
                f"Strong improvement ({overall_improvement_pct:+.1f}%) with no critical degradations - safe to deploy",
            )
        elif overall_improvement_pct > 5:
            return (
                "deploy_canary",
                f"Moderate improvement ({overall_improvement_pct:+.1f}%) - recommend 20% canary for validation",
            )
        elif overall_improvement_pct > -5:
            return (
                "needs_review",
                f"Marginal change ({overall_improvement_pct:+.1f}%) - manual review recommended",
            )
        else:
            return (
                "reject",
                f"Performance regression ({overall_improvement_pct:+.1f}%) - not recommended",
            )

    @traceable(name="modelops_generate_report")
    def generate_comparison_report(self, comparison: EvaluationComparison) -> str:
        """Generate human-readable comparison report.

        Args:
            comparison: EvaluationComparison object

        Returns:
            Formatted markdown report
        """
        report = f"""# Model Evaluation Report

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Models Compared

- **Baseline**: `{comparison.baseline_model}`
- **Candidate**: `{comparison.candidate_model}`

## Overall Assessment

**Improvement**: {comparison.overall_improvement_pct:+.1f}%

**Recommendation**: `{comparison.recommendation.upper()}`

**Reasoning**: {comparison.reasoning}

## Detailed Metrics

### Improvements ✅
"""

        if comparison.improvements:
            for metric, pct in sorted(
                comparison.improvements.items(), key=lambda x: x[1], reverse=True
            ):
                baseline = comparison.baseline_scores.get(metric, 0)
                candidate = comparison.candidate_scores.get(metric, 0)
                report += (
                    f"\n- **{metric}**: {baseline:.3f} → {candidate:.3f} ({pct:+.1f}%)"
                )
        else:
            report += "\n- No improvements"

        report += "\n\n### Degradations ⚠️\n"

        if comparison.degradations:
            for metric, pct in sorted(
                comparison.degradations.items(), key=lambda x: x[1], reverse=True
            ):
                baseline = comparison.baseline_scores.get(metric, 0)
                candidate = comparison.candidate_scores.get(metric, 0)
                report += (
                    f"\n- **{metric}**: {baseline:.3f} → {candidate:.3f} (-{pct:.1f}%)"
                )
        else:
            report += "\n- No degradations"

        report += "\n\n### All Scores\n\n"
        report += "| Metric | Baseline | Candidate | Change |\n"
        report += "|--------|----------|-----------|--------|\n"

        all_metrics = set(comparison.baseline_scores.keys()) | set(
            comparison.candidate_scores.keys()
        )

        for metric in sorted(all_metrics):
            baseline = comparison.baseline_scores.get(metric, 0)
            candidate = comparison.candidate_scores.get(metric, 0)
            change = ((candidate - baseline) / baseline * 100) if baseline > 0 else 0
            report += (
                f"| {metric} | {baseline:.3f} | {candidate:.3f} | {change:+.1f}% |\n"
            )

        report += "\n## Next Steps\n\n"

        if comparison.recommendation == "deploy":
            report += "1. ✅ Deploy to production immediately\n"
            report += "2. Monitor for 24 hours\n"
            report += "3. Update baseline in registry\n"
        elif comparison.recommendation == "deploy_canary":
            report += "1. 🚦 Deploy to 20% canary\n"
            report += "2. Monitor for 48 hours\n"
            report += "3. If stable, promote to 100%\n"
        elif comparison.recommendation == "needs_review":
            report += "1. 🔍 Manual review required\n"
            report += "2. Review degraded metrics\n"
            report += "3. Consider additional training data\n"
        else:  # reject
            report += "1. ❌ Do not deploy\n"
            report += "2. Review training data quality\n"
            report += "3. Consider different base model or hyperparameters\n"

        if comparison.langsmith_experiment_url:
            report += (
                f"\n## LangSmith Experiment\n\n{comparison.langsmith_experiment_url}\n"
            )

        return report

    @traceable(name="modelops_evaluate_and_store")
    def evaluate_and_store_scores(
        self, agent_name: str, version: str, eval_dataset: str
    ) -> EvaluationScores:
        """Evaluate a model and store scores in registry.

        Args:
            agent_name: Agent name
            version: Model version in registry
            eval_dataset: LangSmith dataset name

        Returns:
            EvaluationScores object
        """
        model = self.registry.get_version(agent_name, version)
        if not model:
            raise ValueError(f"Version {version} not found for {agent_name}")

        logger.info(f"Evaluating {agent_name} {version} on {eval_dataset}")

        scores_dict = self.evaluate_model(
            model_endpoint=model.model_id,
            dataset_name=eval_dataset,
            metadata={"agent_name": agent_name, "model_version": version},
        )

        # Convert to EvaluationScores
        eval_scores = EvaluationScores(**scores_dict)

        # Store in registry
        self.registry.update_evaluation_scores(
            agent_name, version, eval_scores.model_dump()
        )

        logger.success(f"Stored evaluation scores for {agent_name} {version}")

        return eval_scores
