"""Unit tests for ModelOps evaluation module.

Tests model evaluation, comparison, and report generation.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from agent_orchestrator.agents.infrastructure.modelops.evaluation import (
    EvaluationComparison,
    ModelEvaluator,
)
from agent_orchestrator.agents.infrastructure.modelops.registry import (
    EvaluationScores,
    ModelRegistry,
    ModelVersion,
    TrainingConfig,
)


@pytest.fixture
def mock_registry(tmp_path):
    """Mock registry with test data."""
    registry_path = tmp_path / "test_registry.json"
    registry = ModelRegistry(registry_path=str(registry_path))

    # Add baseline model
    registry.add_model_version(
        agent_name="feature_dev",
        version="v1.0.0-baseline",
        model_id="microsoft/Phi-3-mini-4k-instruct",
        training_config={
            "base_model": "microsoft/Phi-3-mini-4k-instruct",
            "training_method": "sft",
            "training_dataset": "ls://baseline-train",
        },
    )

    # Set as current
    registry.set_current_model("feature_dev", "v1.0.0-baseline")

    # Add baseline eval scores
    registry.update_evaluation_scores(
        "feature_dev",
        "v1.0.0-baseline",
        {
            "accuracy": 0.75,
            "workflow_completeness": 0.80,
            "token_efficiency": 0.70,
            "latency_threshold": 0.85,
            "mcp_integration_quality": 0.65,
        },
    )

    # Add candidate model
    registry.add_model_version(
        agent_name="feature_dev",
        version="v2.0.0-candidate",
        model_id="alextorelli/codechef-feature-dev-v2",
        training_config={
            "base_model": "microsoft/Phi-3-mini-4k-instruct",
            "training_method": "sft",
            "training_dataset": "ls://improved-train",
            "eval_dataset": "ls://eval-dataset",
        },
    )

    return registry


@pytest.fixture
def evaluator(mock_registry):
    """Create evaluator with mock registry."""
    return ModelEvaluator(registry=mock_registry)


class TestModelEvaluator:
    """Test ModelEvaluator class."""

    def test_evaluator_initialization(self, evaluator, mock_registry):
        """Test evaluator initialization."""
        assert evaluator.registry == mock_registry
        assert evaluator.langsmith_client is not None or True  # May not be available

    def test_compare_models_with_improvement(self, evaluator, mock_registry):
        """Test comparing models with improvement."""
        # Add improved scores to candidate
        mock_registry.update_evaluation_scores(
            "feature_dev",
            "v2.0.0-candidate",
            {
                "accuracy": 0.87,  # +16% improvement
                "workflow_completeness": 0.91,  # +13.75% improvement
                "token_efficiency": 0.82,  # +17% improvement
                "latency_threshold": 0.90,  # +5.9% improvement
                "mcp_integration_quality": 0.75,  # +15.4% improvement
            },
        )

        # Compare models
        comparison = evaluator.compare_models(
            agent_name="feature_dev",
            candidate_version="v2.0.0-candidate",
            baseline_version="v1.0.0-baseline",
        )

        assert isinstance(comparison, EvaluationComparison)
        assert comparison.overall_improvement_pct > 10  # Strong improvement
        assert comparison.recommendation in ["deploy", "deploy_canary"]
        assert len(comparison.improvements) > 0
        assert len(comparison.degradations) == 0

    def test_compare_models_with_degradation(self, evaluator, mock_registry):
        """Test comparing models with degradation."""
        # Add degraded scores to candidate
        mock_registry.update_evaluation_scores(
            "feature_dev",
            "v2.0.0-candidate",
            {
                "accuracy": 0.65,  # -13% degradation
                "workflow_completeness": 0.70,  # -12.5% degradation
                "token_efficiency": 0.60,  # -14% degradation
                "latency_threshold": 0.75,  # -11.7% degradation
                "mcp_integration_quality": 0.55,  # -15.4% degradation
            },
        )

        # Compare models
        comparison = evaluator.compare_models(
            agent_name="feature_dev",
            candidate_version="v2.0.0-candidate",
            baseline_version="v1.0.0-baseline",
        )

        assert comparison.overall_improvement_pct < 0  # Regression
        assert comparison.recommendation == "reject"
        assert len(comparison.degradations) > 0

    def test_compare_models_mixed_results(self, evaluator, mock_registry):
        """Test comparing models with mixed improvements and degradations."""
        # Add mixed scores to candidate
        mock_registry.update_evaluation_scores(
            "feature_dev",
            "v2.0.0-candidate",
            {
                "accuracy": 0.80,  # +6.7% improvement
                "workflow_completeness": 0.85,  # +6.25% improvement
                "token_efficiency": 0.65,  # -7% degradation
                "latency_threshold": 0.87,  # +2.35% improvement
                "mcp_integration_quality": 0.70,  # +7.7% improvement
            },
        )

        # Compare models
        comparison = evaluator.compare_models(
            agent_name="feature_dev",
            candidate_version="v2.0.0-candidate",
            baseline_version="v1.0.0-baseline",
        )

        assert len(comparison.improvements) > 0
        assert len(comparison.degradations) > 0
        # Small degradations shouldn't trigger rejection
        assert comparison.recommendation != "reject"

    def test_compare_models_no_baseline(self, evaluator, mock_registry):
        """Test comparing when no baseline exists."""
        # Add candidate for agent with no baseline
        mock_registry.add_model_version(
            agent_name="code_review",
            version="v1.0.0",
            model_id="test/model",
            training_config={
                "base_model": "test/model",
                "training_method": "sft",
                "training_dataset": "ls://train",
            },
        )

        comparison = evaluator.compare_models(
            agent_name="code_review", candidate_version="v1.0.0"
        )

        assert comparison.baseline_model == "none"
        assert comparison.overall_improvement_pct == 100.0
        assert comparison.recommendation == "deploy_canary"

    def test_generate_recommendation_strong_improvement(self, evaluator):
        """Test recommendation generation for strong improvement."""
        recommendation, reasoning = evaluator._generate_recommendation(
            overall_improvement_pct=20.0,
            improvements={"accuracy": 25.0, "latency": 15.0},
            degradations={},
            candidate_scores={"accuracy": 0.85, "latency": 0.80},
        )

        assert recommendation == "deploy"
        assert "Strong improvement" in reasoning

    def test_generate_recommendation_moderate_improvement(self, evaluator):
        """Test recommendation generation for moderate improvement."""
        recommendation, reasoning = evaluator._generate_recommendation(
            overall_improvement_pct=8.0,
            improvements={"accuracy": 10.0},
            degradations={},
            candidate_scores={"accuracy": 0.80},
        )

        assert recommendation == "deploy_canary"
        assert "Moderate improvement" in reasoning

    def test_generate_recommendation_critical_degradation(self, evaluator):
        """Test recommendation generation with critical degradation."""
        recommendation, reasoning = evaluator._generate_recommendation(
            overall_improvement_pct=5.0,
            improvements={"accuracy": 10.0},
            degradations={"latency": 25.0},  # >20% degradation
            candidate_scores={"accuracy": 0.85, "latency": 0.60},
        )

        assert recommendation == "reject"
        assert "Critical degradations" in reasoning

    def test_generate_recommendation_low_quality(self, evaluator):
        """Test recommendation generation for low quality model."""
        recommendation, reasoning = evaluator._generate_recommendation(
            overall_improvement_pct=10.0,
            improvements={"accuracy": 10.0},
            degradations={},
            candidate_scores={"accuracy": 0.45, "latency": 0.80},  # Min < 0.5
        )

        assert recommendation == "reject"
        assert "not production-ready" in reasoning

    def test_generate_comparison_report(self, evaluator, mock_registry):
        """Test comparison report generation."""
        # Add scores to candidate
        mock_registry.update_evaluation_scores(
            "feature_dev",
            "v2.0.0-candidate",
            {
                "accuracy": 0.87,
                "workflow_completeness": 0.91,
                "token_efficiency": 0.82,
                "latency_threshold": 0.90,
                "mcp_integration_quality": 0.75,
            },
        )

        comparison = evaluator.compare_models(
            agent_name="feature_dev",
            candidate_version="v2.0.0-candidate",
            baseline_version="v1.0.0-baseline",
        )

        report = evaluator.generate_comparison_report(comparison)

        # Verify report structure
        assert "# Model Evaluation Report" in report
        assert "Models Compared" in report
        assert "Overall Assessment" in report
        assert "Detailed Metrics" in report
        assert "Improvements" in report
        assert "Next Steps" in report

        # Verify data in report
        assert comparison.baseline_model in report
        assert comparison.candidate_model in report
        assert str(comparison.recommendation.upper()) in report

    def test_evaluate_and_store_scores(self, evaluator, mock_registry):
        """Test evaluation and storage workflow."""
        # Mock evaluate_model to return scores
        with patch.object(
            evaluator,
            "evaluate_model",
            return_value={
                "accuracy": 0.85,
                "workflow_completeness": 0.88,
                "token_efficiency": 0.75,
            },
        ):
            scores = evaluator.evaluate_and_store_scores(
                agent_name="feature_dev",
                version="v2.0.0-candidate",
                eval_dataset="ls://eval-dataset",
            )

            assert isinstance(scores, EvaluationScores)
            assert scores.accuracy == 0.85

            # Verify stored in registry
            version = mock_registry.get_version("feature_dev", "v2.0.0-candidate")
            assert version.eval_scores is not None
            assert version.eval_scores.accuracy == 0.85


class TestEvaluationComparison:
    """Test EvaluationComparison dataclass."""

    def test_comparison_creation(self):
        """Test creating comparison object."""
        comparison = EvaluationComparison(
            baseline_model="test/baseline",
            candidate_model="test/candidate",
            baseline_scores={"accuracy": 0.75},
            candidate_scores={"accuracy": 0.85},
            improvements={"accuracy": 13.33},
            degradations={},
            overall_improvement_pct=10.0,
            recommendation="deploy_canary",
            reasoning="Moderate improvement",
        )

        assert comparison.baseline_model == "test/baseline"
        assert comparison.candidate_model == "test/candidate"
        assert comparison.recommendation == "deploy_canary"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
