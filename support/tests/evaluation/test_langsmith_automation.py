"""
Test suite for LangSmith evaluation automation.

Tests:
- Evaluator wrappers
- Target system integration
- Regression detection
- Dataset sync logic

Run:
    pytest support/tests/evaluation/test_langsmith_automation.py -v
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from support.scripts.evaluation.detect_regression import RegressionDetector
from support.scripts.evaluation.sync_dataset_from_annotations import DatasetSyncer

# Import evaluators
from support.tests.evaluation.evaluators import (
    EvaluationResult,
    agent_routing_accuracy,
    token_efficiency,
)

# Import modules under test
from support.tests.evaluation.run_langsmith_evaluation import (
    calculate_improvement,
    get_llm_evaluators,
    get_prebuilt_evaluators,
    wrap_evaluator,
)

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_run():
    """Mock LangSmith Run object."""
    run = MagicMock()
    run.inputs = {"query": "Create JWT authentication"}
    run.outputs = {
        "output": "Implementation complete",
        "agent": "feature_dev",
        "tokens": 2500,
    }
    run.run_type = "chain"
    run.start_time = datetime.now()
    run.end_time = datetime.now() + timedelta(seconds=2)
    return run


@pytest.fixture
def mock_example():
    """Mock LangSmith Example object."""
    example = MagicMock()
    example.inputs = {"query": "Create JWT authentication"}
    example.outputs = {
        "expected_agent": "feature_dev",
        "expected_tokens": 3000,
    }
    example.metadata = {
        "category": "code_generation",
        "difficulty": "medium",
    }
    return example


@pytest.fixture
def sample_evaluation_results():
    """Sample evaluation results for testing."""
    return {
        "code_chef": {
            "experiment_name": "eval-test-20250115",
            "results": {
                "accuracy": 0.85,
                "latency": 1.8,
                "token_efficiency": 0.78,
            },
        },
        "baseline": {
            "experiment_name": "eval-baseline-20250115",
            "results": {
                "accuracy": 0.72,
                "latency": 2.1,
                "token_efficiency": 0.65,
            },
        },
        "comparison": {
            "overall_improvement_pct": 15.2,
            "per_metric": {
                "accuracy": {
                    "baseline": 0.72,
                    "codechef": 0.85,
                    "improvement_pct": 18.1,
                    "winner": "code-chef",
                },
                "latency": {
                    "baseline": 2.1,
                    "codechef": 1.8,
                    "improvement_pct": -14.3,
                    "winner": "code-chef",
                },
            },
        },
    }


# =============================================================================
# TEST EVALUATOR WRAPPERS
# =============================================================================


def test_wrap_evaluator_success(mock_run, mock_example):
    """Test successful evaluator wrapping."""
    # Wrap evaluator
    wrapped = wrap_evaluator(agent_routing_accuracy)

    # Call wrapped evaluator
    result = wrapped(mock_run, mock_example)

    # Verify result format
    assert isinstance(result, dict)
    assert "key" in result
    assert "score" in result
    assert "comment" in result
    assert 0.0 <= result["score"] <= 1.0


def test_wrap_evaluator_error_handling(mock_run, mock_example):
    """Test evaluator error handling."""

    def failing_evaluator(run, example):
        raise ValueError("Test error")

    # Wrap failing evaluator
    wrapped = wrap_evaluator(failing_evaluator)

    # Should return error result instead of raising
    result = wrapped(mock_run, mock_example)

    assert result["score"] == 0.0
    assert "Error" in result["comment"]


def test_wrap_evaluator_preserves_name():
    """Test that wrapped evaluator preserves function name."""
    wrapped = wrap_evaluator(agent_routing_accuracy)

    assert wrapped.__name__ == "wrapped_agent_routing_accuracy"


# =============================================================================
# TEST IMPROVEMENT CALCULATION
# =============================================================================


def test_calculate_improvement_positive():
    """Test improvement calculation for positive results."""
    baseline = {
        "results": {
            "accuracy": 0.70,
            "latency": 2.0,
        }
    }
    codechef = {
        "results": {
            "accuracy": 0.85,
            "latency": 1.5,
        }
    }

    comparison = calculate_improvement(baseline, codechef)

    # Check overall improvement
    assert comparison["overall_improvement_pct"] > 0

    # Check per-metric
    assert comparison["per_metric"]["accuracy"]["improvement_pct"] > 0
    assert comparison["per_metric"]["accuracy"]["winner"] == "code-chef"


def test_calculate_improvement_regression():
    """Test improvement calculation for regression."""
    baseline = {
        "results": {
            "accuracy": 0.85,
        }
    }
    codechef = {
        "results": {
            "accuracy": 0.70,
        }
    }

    comparison = calculate_improvement(baseline, codechef)

    # Should show negative improvement (regression)
    assert comparison["overall_improvement_pct"] < 0
    assert comparison["per_metric"]["accuracy"]["improvement_pct"] < 0
    assert comparison["per_metric"]["accuracy"]["winner"] == "baseline"


def test_calculate_improvement_recommendation():
    """Test deployment recommendation logic."""
    # Deploy case (>15% improvement)
    baseline = {"results": {"accuracy": 0.70}}
    codechef = {"results": {"accuracy": 0.85}}
    comparison = calculate_improvement(baseline, codechef)
    assert comparison["recommendation"] == "deploy"

    # Needs review case (5-15% improvement)
    baseline = {"results": {"accuracy": 0.75}}
    codechef = {"results": {"accuracy": 0.80}}
    comparison = calculate_improvement(baseline, codechef)
    assert comparison["recommendation"] == "needs_review"

    # Reject case (<5% improvement)
    baseline = {"results": {"accuracy": 0.80}}
    codechef = {"results": {"accuracy": 0.81}}
    comparison = calculate_improvement(baseline, codechef)
    assert comparison["recommendation"] == "reject"


# =============================================================================
# TEST REGRESSION DETECTION
# =============================================================================


def test_regression_detector_no_regression(sample_evaluation_results):
    """Test regression detector with good results."""
    detector = RegressionDetector(threshold=0.05)

    analysis = detector.analyze_results(sample_evaluation_results)

    assert not analysis["has_regression"]
    assert analysis["severity"] == "none"
    assert len(analysis["regressions"]) == 0


def test_regression_detector_with_regression():
    """Test regression detector with regression."""
    results = {
        "comparison": {
            "overall_improvement_pct": -12.5,
            "per_metric": {
                "accuracy": {
                    "baseline": 0.85,
                    "codechef": 0.72,
                    "improvement_pct": -15.3,
                    "winner": "baseline",
                }
            },
        }
    }

    detector = RegressionDetector(threshold=0.05)
    analysis = detector.analyze_results(results)

    assert analysis["has_regression"]
    assert len(analysis["regressions"]) > 0
    assert analysis["regressions"][0]["metric"] == "accuracy"
    assert analysis["severity"] in ["critical", "high", "medium"]


def test_regression_detector_severity_levels():
    """Test severity level calculation."""
    detector = RegressionDetector(threshold=0.05)

    # Critical (> -15%)
    assert detector._get_severity(-20.0) == "critical"

    # High (-10% to -15%)
    assert detector._get_severity(-12.0) == "high"

    # Medium (-5% to -10%)
    assert detector._get_severity(-7.0) == "medium"

    # Low (< -5%)
    assert detector._get_severity(-3.0) == "low"


# =============================================================================
# TEST DATASET SYNC
# =============================================================================


@pytest.fixture
def mock_langsmith_client():
    """Mock LangSmith client."""
    client = MagicMock()
    client.read_dataset = MagicMock()
    client.create_dataset = MagicMock()
    client.list_runs = MagicMock(return_value=[])
    client.list_examples = MagicMock(return_value=[])
    client.create_example = MagicMock()
    client.delete_example = MagicMock()
    return client


def test_dataset_syncer_initialization(mock_langsmith_client):
    """Test dataset syncer initialization."""
    syncer = DatasetSyncer(
        client=mock_langsmith_client,
        dataset_name="test-dataset",
        project_name="test-project",
    )

    assert syncer.dataset_name == "test-dataset"
    assert syncer.project_name == "test-project"
    assert syncer.client == mock_langsmith_client


def test_dataset_syncer_convert_run(mock_langsmith_client, mock_run):
    """Test run to example conversion."""
    syncer = DatasetSyncer(
        client=mock_langsmith_client,
        dataset_name="test-dataset",
        project_name="test-project",
    )

    # Add feedback to mock run
    mock_run.feedback_stats = [MagicMock(key="correctness", score=0.85)]
    mock_run.tags = ["agent_routing"]

    example = syncer.convert_run_to_example(mock_run)

    assert example is not None
    assert "inputs" in example
    assert "outputs" in example
    assert "metadata" in example
    assert example["metadata"]["category"] == "agent_routing"
    assert example["metadata"]["correctness"] == 0.85


def test_dataset_syncer_duplicate_detection(mock_langsmith_client):
    """Test duplicate example detection."""
    # Mock existing examples
    existing_example = MagicMock()
    existing_example.inputs = {"query": "Existing query"}

    mock_langsmith_client.list_examples.return_value = [existing_example]

    syncer = DatasetSyncer(
        client=mock_langsmith_client,
        dataset_name="test-dataset",
        project_name="test-project",
    )
    syncer.dataset = MagicMock(id="test-id")

    # Try to add duplicate
    new_examples = [
        {
            "inputs": {"query": "Existing query"},
            "outputs": {},
            "metadata": {},
        }
    ]

    added = syncer.add_examples_to_dataset(new_examples)

    # Should not add duplicate
    assert added == 0
    mock_langsmith_client.create_example.assert_not_called()


# =============================================================================
# TEST PREBUILT EVALUATORS
# =============================================================================


@patch("support.tests.evaluation.run_langsmith_evaluation.OpenAIEmbeddings")
def test_get_prebuilt_evaluators(mock_embeddings):
    """Test prebuilt evaluator creation."""
    evaluators = get_prebuilt_evaluators()

    # Should have at least exact_match and regex_match
    assert len(evaluators) >= 2

    # Check types
    from langsmith.evaluation import LangChainStringEvaluator

    for evaluator in evaluators:
        assert isinstance(evaluator, LangChainStringEvaluator)


@patch("support.tests.evaluation.run_langsmith_evaluation.ChatOpenAI")
def test_get_llm_evaluators(mock_chatgpt):
    """Test LLM evaluator creation."""
    evaluators = get_llm_evaluators()

    # Should have criteria and labeled_criteria
    assert len(evaluators) >= 2


# =============================================================================
# TEST INTEGRATION
# =============================================================================


@pytest.mark.asyncio
async def test_end_to_end_evaluation_flow(
    sample_evaluation_results,
    tmp_path,
):
    """Test complete evaluation flow."""
    # Write results to temp file
    results_file = tmp_path / "results.json"
    results_file.write_text(json.dumps(sample_evaluation_results))

    # Run regression detection
    detector = RegressionDetector(threshold=0.05)
    analysis = detector.analyze_results(sample_evaluation_results)

    # Verify no regression
    assert not analysis["has_regression"]
    assert analysis["recommendation"] == "deploy"

    # Verify improvement
    assert analysis["overall_change_pct"] > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_live_orchestrator_connection():
    """Test connection to live orchestrator (integration test)."""
    import httpx

    from support.tests.evaluation.run_langsmith_evaluation import code_chef_target

    # Test with simple query
    result = await code_chef_target({"query": "What is the current date?"})

    # Should get response
    assert "output" in result
    assert result["output"]  # Non-empty response


# =============================================================================
# RUN TESTS
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
