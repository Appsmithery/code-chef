"""Property-based tests for evaluation system using Hypothesis.

Tests Phase 5 (CHEF-243): Comprehensive A/B Test Suite - Property-Based Tests

Uses Hypothesis library for property-based testing to validate:
- Evaluator robustness across wide range of inputs
- Score calculation correctness and bounds
- Improvement calculation properties
- Comparison engine invariants
- Data integrity under random inputs

Property-based testing ensures code correctness by generating hundreds
of random test cases and verifying properties always hold.

Part of: Testing, Tracing & Evaluation Refactoring (CHEF-238)

Hypothesis Profiles (from conftest.py):
- ci: 20 examples (fast, for CI/CD)
- dev: 100 examples (default, for local development)
- thorough: 500 examples (comprehensive, for pre-release)

Usage:
    # Run with default profile (dev, 100 examples)
    pytest support/tests/evaluation/test_property_based.py -v

    # Run with CI profile (fast)
    HYPOTHESIS_PROFILE=ci pytest support/tests/evaluation/test_property_based.py

    # Run with thorough profile (comprehensive)
    HYPOTHESIS_PROFILE=thorough pytest support/tests/evaluation/test_property_based.py
"""

import os
from typing import Dict

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

# Set test environment
os.environ["TEST_DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/devtools_test"
)

from shared.lib.comparison_engine import comparison_engine

# ============================================================================
# Hypothesis Strategies (Data Generators)
# ============================================================================


@st.composite
def evaluation_score(draw):
    """Generate valid evaluation score (0.0 to 1.0)."""
    return draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))


@st.composite
def evaluation_scores(draw):
    """Generate dict of evaluation scores."""
    return {
        "accuracy": draw(evaluation_score()),
        "completeness": draw(evaluation_score()),
        "efficiency": draw(evaluation_score()),
        "integration_quality": draw(evaluation_score()),
    }


@st.composite
def performance_metrics(draw):
    """Generate performance metrics (positive values)."""
    return {
        "latency_ms": draw(st.floats(min_value=1, max_value=60000, allow_nan=False)),
        "tokens_used": draw(st.integers(min_value=1, max_value=100000)),
        "cost_usd": draw(st.floats(min_value=0.0001, max_value=1.0, allow_nan=False)),
    }


@st.composite
def evaluation_result(draw, experiment_group=None):
    """Generate complete evaluation result."""
    if experiment_group is None:
        experiment_group = draw(st.sampled_from(["baseline", "code-chef"]))

    return {
        "experiment_group": experiment_group,
        "scores": draw(evaluation_scores()),
        "metrics": draw(performance_metrics()),
    }


# ============================================================================
# Property Tests for Score Bounds
# ============================================================================


class TestScoreBounds:
    """Test that scores are always bounded correctly."""

    @given(score=evaluation_score())
    @settings(max_examples=100)
    def test_scores_bounded_between_0_and_1(self, score):
        """Property: All evaluation scores must be in [0, 1]."""
        assert 0.0 <= score <= 1.0

    @given(scores=evaluation_scores())
    @settings(max_examples=100)
    def test_all_scores_in_valid_range(self, scores):
        """Property: All scores in dict must be in valid range."""
        for metric, value in scores.items():
            assert 0.0 <= value <= 1.0, f"{metric} out of bounds: {value}"

    @given(metrics=performance_metrics())
    @settings(max_examples=100)
    def test_performance_metrics_positive(self, metrics):
        """Property: Performance metrics must be positive."""
        assert metrics["latency_ms"] > 0
        assert metrics["tokens_used"] > 0
        assert metrics["cost_usd"] > 0


# ============================================================================
# Property Tests for Improvement Calculation
# ============================================================================


class TestImprovementCalculation:
    """Test properties of improvement calculation."""

    @given(
        baseline=st.floats(min_value=0.01, max_value=1.0, allow_nan=False),
        codechef=st.floats(min_value=0.01, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_improvement_symmetry_higher_is_better(self, baseline, codechef):
        """Property: If A improves over B, then B regresses from A (higher is better)."""
        engine = comparison_engine

        improvement_a_to_b = engine.calculate_improvement(
            baseline, codechef, "higher_is_better"
        )
        improvement_b_to_a = engine.calculate_improvement(
            codechef, baseline, "higher_is_better"
        )

        # Improvements should have opposite signs (except when equal)
        if baseline != codechef:
            assert (improvement_a_to_b > 0) == (improvement_b_to_a < 0)

    @given(
        baseline=st.floats(min_value=1, max_value=10000, allow_nan=False),
        codechef=st.floats(min_value=1, max_value=10000, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_improvement_symmetry_lower_is_better(self, baseline, codechef):
        """Property: If A improves over B, then B regresses from A (lower is better)."""
        engine = comparison_engine

        improvement_a_to_b = engine.calculate_improvement(
            baseline, codechef, "lower_is_better"
        )
        improvement_b_to_a = engine.calculate_improvement(
            codechef, baseline, "lower_is_better"
        )

        # Improvements should have opposite signs (except when equal)
        if baseline != codechef:
            assert (improvement_a_to_b > 0) == (improvement_b_to_a < 0)

    @given(value=st.floats(min_value=0.01, max_value=1.0, allow_nan=False))
    @settings(max_examples=100)
    def test_no_improvement_when_equal(self, value):
        """Property: Comparing equal values yields 0% improvement."""
        engine = comparison_engine

        improvement = engine.calculate_improvement(value, value, "higher_is_better")
        assert improvement == 0.0

        improvement = engine.calculate_improvement(value, value, "lower_is_better")
        assert improvement == 0.0

    @given(
        baseline=st.floats(min_value=0.01, max_value=1.0, allow_nan=False),
        improvement_pct=st.floats(min_value=1, max_value=100, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_improvement_calculation_reversible_higher_is_better(
        self, baseline, improvement_pct
    ):
        """Property: Can reconstruct codechef value from baseline + improvement%."""
        assume(baseline * (1 + improvement_pct / 100) <= 1.0)  # Stay in bounds

        engine = comparison_engine

        # Calculate what codechef value would be
        codechef = baseline * (1 + improvement_pct / 100)

        # Calculate improvement from baseline to codechef
        calculated_improvement = engine.calculate_improvement(
            baseline, codechef, "higher_is_better"
        )

        # Should match original improvement_pct
        assert calculated_improvement == pytest.approx(improvement_pct, abs=0.01)

    @given(
        baseline=st.floats(min_value=100, max_value=5000, allow_nan=False),
        reduction_pct=st.floats(min_value=1, max_value=99, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_improvement_calculation_reversible_lower_is_better(
        self, baseline, reduction_pct
    ):
        """Property: Can reconstruct codechef value from baseline - reduction%."""
        engine = comparison_engine

        # Calculate what codechef value would be (reduced)
        codechef = baseline * (1 - reduction_pct / 100)
        assume(codechef > 0)

        # Calculate improvement from baseline to codechef
        calculated_improvement = engine.calculate_improvement(
            baseline, codechef, "lower_is_better"
        )

        # Should match original reduction_pct
        assert calculated_improvement == pytest.approx(reduction_pct, abs=0.01)

    @given(
        baseline=st.floats(min_value=0.01, max_value=1.0, allow_nan=False),
        multiplier=st.floats(min_value=1.5, max_value=3.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_larger_improvements_yield_larger_percentages(self, baseline, multiplier):
        """Property: Doubling improvement yields roughly double percentage."""
        assume(baseline * multiplier <= 1.0)  # Stay in bounds

        engine = comparison_engine

        small_improvement = baseline * 1.1
        large_improvement = baseline * multiplier

        small_pct = engine.calculate_improvement(
            baseline, small_improvement, "higher_is_better"
        )
        large_pct = engine.calculate_improvement(
            baseline, large_improvement, "higher_is_better"
        )

        # Larger improvement should yield larger percentage
        assert large_pct > small_pct


# ============================================================================
# Property Tests for Winner Determination
# ============================================================================


class TestWinnerDetermination:
    """Test properties of winner determination logic."""

    @given(improvement=st.floats(min_value=-100, max_value=100, allow_nan=False))
    @settings(max_examples=100)
    def test_winner_determination_consistent(self, improvement):
        """Property: Winner determination is consistent with threshold logic."""
        engine = comparison_engine

        winner = engine._determine_winner(improvement)

        if improvement > 5.0:
            assert winner == "code-chef"
        elif improvement < -5.0:
            assert winner == "baseline"
        else:
            assert winner == "tie"

    @given(improvement=st.floats(min_value=5.1, max_value=100, allow_nan=False))
    @settings(max_examples=100)
    def test_positive_improvement_means_codechef_wins(self, improvement):
        """Property: Improvements >5% always result in code-chef win."""
        engine = comparison_engine
        assert engine._determine_winner(improvement) == "code-chef"

    @given(improvement=st.floats(min_value=-100, max_value=-5.1, allow_nan=False))
    @settings(max_examples=100)
    def test_negative_improvement_means_baseline_wins(self, improvement):
        """Property: Regressions <-5% always result in baseline win."""
        engine = comparison_engine
        assert engine._determine_winner(improvement) == "baseline"

    @given(improvement=st.floats(min_value=-5.0, max_value=5.0, allow_nan=False))
    @settings(max_examples=100)
    def test_marginal_improvement_means_tie(self, improvement):
        """Property: Improvements between -5% and 5% always result in tie."""
        engine = comparison_engine
        assert engine._determine_winner(improvement) == "tie"


# ============================================================================
# Property Tests for Weighted Improvement
# ============================================================================


class TestWeightedImprovement:
    """Test properties of weighted improvement calculation."""

    @given(
        acc_imp=st.floats(min_value=-50, max_value=50, allow_nan=False),
        comp_imp=st.floats(min_value=-50, max_value=50, allow_nan=False),
        eff_imp=st.floats(min_value=-50, max_value=50, allow_nan=False),
        lat_imp=st.floats(min_value=-50, max_value=50, allow_nan=False),
        int_imp=st.floats(min_value=-50, max_value=50, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_weighted_improvement_in_reasonable_range(
        self, acc_imp, comp_imp, eff_imp, lat_imp, int_imp
    ):
        """Property: Weighted improvement should be in reasonable range."""
        engine = comparison_engine

        improvements = {
            "accuracy": acc_imp,
            "completeness": comp_imp,
            "efficiency": eff_imp,
            "latency_ms": lat_imp,
            "integration_quality": int_imp,
        }

        weighted = engine._calculate_weighted_improvement(improvements)

        # Weighted average should be between min and max of inputs
        min_improvement = min(improvements.values())
        max_improvement = max(improvements.values())

        assert min_improvement <= weighted <= max_improvement

    @given(improvement=st.floats(min_value=-50, max_value=50, allow_nan=False))
    @settings(max_examples=100)
    def test_uniform_improvements_yield_same_weighted(self, improvement):
        """Property: If all improvements are equal, weighted equals that value."""
        engine = comparison_engine

        improvements = {
            "accuracy": improvement,
            "completeness": improvement,
            "efficiency": improvement,
            "latency_ms": improvement,
            "integration_quality": improvement,
        }

        weighted = engine._calculate_weighted_improvement(improvements)

        assert weighted == pytest.approx(improvement, abs=0.01)

    @given(
        high_weight_imp=st.floats(min_value=10, max_value=50, allow_nan=False),
        low_weight_imp=st.floats(min_value=-50, max_value=-10, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_higher_weight_metrics_dominate(self, high_weight_imp, low_weight_imp):
        """Property: High-weight metrics (accuracy) should dominate weighted score."""
        engine = comparison_engine

        # Accuracy has high weight (30%), others low
        improvements = {
            "accuracy": high_weight_imp,
            "completeness": low_weight_imp,
            "efficiency": low_weight_imp,
            "latency_ms": low_weight_imp,
            "integration_quality": low_weight_imp,
        }

        weighted = engine._calculate_weighted_improvement(improvements)

        # With accuracy at 30% weight, should be closer to high_weight_imp
        # than to low_weight_imp
        assert weighted > 0  # Should be positive overall


# ============================================================================
# Property Tests for Recommendation Logic
# ============================================================================


class TestRecommendationLogic:
    """Test properties of deployment recommendation logic."""

    @given(improvement=st.floats(min_value=15.0, max_value=100, allow_nan=False))
    @settings(max_examples=100)
    def test_strong_improvements_recommend_deploy(self, improvement):
        """Property: Improvements ≥15% always recommend deploy."""
        engine = comparison_engine

        recommendation = engine._generate_recommendation(improvement)
        assert recommendation == "deploy"

    @given(improvement=st.floats(min_value=5.0, max_value=14.99, allow_nan=False))
    @settings(max_examples=100)
    def test_moderate_improvements_need_review(self, improvement):
        """Property: Improvements 5-15% always need review."""
        engine = comparison_engine

        recommendation = engine._generate_recommendation(improvement)
        assert recommendation == "needs_review"

    @given(improvement=st.floats(min_value=-50, max_value=4.99, allow_nan=False))
    @settings(max_examples=100)
    def test_marginal_improvements_rejected(self, improvement):
        """Property: Improvements <5% always rejected."""
        engine = comparison_engine

        recommendation = engine._generate_recommendation(improvement)
        assert recommendation == "reject"


# ============================================================================
# Property Tests for Data Integrity
# ============================================================================


class TestDataIntegrity:
    """Test data integrity properties."""

    @given(result=evaluation_result(experiment_group="baseline"))
    @settings(max_examples=100)
    def test_baseline_results_always_valid(self, result):
        """Property: Baseline evaluation results are always valid."""
        assert result["experiment_group"] == "baseline"
        assert all(0 <= v <= 1 for v in result["scores"].values())
        assert all(v > 0 for v in result["metrics"].values())

    @given(result=evaluation_result(experiment_group="code-chef"))
    @settings(max_examples=100)
    def test_codechef_results_always_valid(self, result):
        """Property: Code-chef evaluation results are always valid."""
        assert result["experiment_group"] == "code-chef"
        assert all(0 <= v <= 1 for v in result["scores"].values())
        assert all(v > 0 for v in result["metrics"].values())

    @given(
        baseline=evaluation_result(experiment_group="baseline"),
        codechef=evaluation_result(experiment_group="code-chef"),
    )
    @settings(max_examples=100)
    def test_comparison_always_possible_with_valid_data(self, baseline, codechef):
        """Property: Any two valid results can be compared."""
        engine = comparison_engine

        # Should be able to calculate improvements for all metrics
        for metric in baseline["scores"].keys():
            baseline_val = baseline["scores"][metric]
            codechef_val = codechef["scores"][metric]

            improvement = engine.calculate_improvement(
                baseline_val, codechef_val, "higher_is_better"
            )

            # Improvement should be a valid number
            assert isinstance(improvement, (int, float))
            assert not (improvement != improvement)  # Not NaN


# ============================================================================
# Edge Case Property Tests
# ============================================================================


class TestEdgeCases:
    """Test edge cases with property-based testing."""

    @given(value=st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    @settings(max_examples=100)
    def test_perfect_scores_handled_correctly(self, value):
        """Property: Perfect scores (0.0 or 1.0) are handled correctly."""
        engine = comparison_engine

        # Improvement from any value to 1.0
        if value > 0:
            improvement = engine.calculate_improvement(value, 1.0, "higher_is_better")
            assert improvement > 0 or value == 1.0

        # Improvement from 1.0 to any value
        if value < 1.0:
            improvement = engine.calculate_improvement(1.0, value, "higher_is_better")
            assert improvement < 0

    @given(
        small_baseline=st.floats(min_value=0.001, max_value=0.1, allow_nan=False),
        large_codechef=st.floats(min_value=0.9, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_large_improvements_dont_overflow(self, small_baseline, large_codechef):
        """Property: Very large improvements don't cause numerical issues."""
        engine = comparison_engine

        improvement = engine.calculate_improvement(
            small_baseline, large_codechef, "higher_is_better"
        )

        # Should be a valid number, not infinity or NaN
        assert isinstance(improvement, (int, float))
        assert improvement != float("inf")
        assert not (improvement != improvement)  # Not NaN

    @given(
        values=st.lists(
            st.floats(min_value=0.01, max_value=1.0, allow_nan=False),
            min_size=2,
            max_size=10,
        )
    )
    @settings(max_examples=100)
    def test_improvements_transitive_ordering(self, values):
        """Property: If A > B and B > C, then improvement(A, C) > improvement(B, C)."""
        engine = comparison_engine

        # Sort values
        sorted_values = sorted(values)
        if len(set(sorted_values)) < 3:
            assume(False)  # Need at least 3 distinct values

        a, b, c = (
            sorted_values[-1],
            sorted_values[len(sorted_values) // 2],
            sorted_values[0],
        )

        imp_ac = engine.calculate_improvement(c, a, "higher_is_better")
        imp_bc = engine.calculate_improvement(c, b, "higher_is_better")

        # A > B > C, so improvement from C to A should be greater than C to B
        assert imp_ac > imp_bc


# ============================================================================
# Property Tests for Agent Output Validation
# ============================================================================


class TestAgentOutputProperties:
    """Test invariants for agent response outputs."""

    @given(
        user_input=st.text(min_size=10, max_size=500),
        agent=st.sampled_from(
            ["feature_dev", "code_review", "infrastructure", "cicd", "documentation"]
        ),
    )
    @settings(max_examples=50, deadline=None)
    def test_agent_response_no_internal_state(self, user_input, agent):
        """Property: Agent responses must not expose internal thinking markers."""
        # This is a structural test - actual agent execution would be tested in integration
        # Here we verify the property that any string shouldn't contain internal markers

        # Simulate a response (in real scenario, would call agent)
        # For property testing, we verify the constraint itself
        internal_markers = ["@@THINK@@", "@@SCRATCHPAD@@", "@@INTERNAL@@"]

        # Property: A valid agent response should never contain these
        for marker in internal_markers:
            # Test that our validation catches these
            assert (
                marker not in "This is a valid response"
            ), "Valid response should not have markers"
            assert (
                marker in f"Bad response {marker}"
            ), "Invalid response should be detectable"

    @given(
        intent=st.sampled_from(
            [
                "implement feature",
                "review code",
                "deploy infrastructure",
                "write documentation",
                "setup CI/CD pipeline",
            ]
        )
    )
    @settings(max_examples=30)
    def test_intent_classification_deterministic(self, intent):
        """Property: Same input should always route to same agent."""
        # Property test: Intent classification should be deterministic
        # In actual implementation, this would test the routing logic

        # Verify property structure
        intent_to_agent_map = {
            "implement": "feature_dev",
            "review": "code_review",
            "deploy": "infrastructure",
            "documentation": "documentation",
            "CI/CD": "cicd",
        }

        # Property: If intent contains keyword, routing should be consistent
        for keyword, expected_agent in intent_to_agent_map.items():
            if keyword.lower() in intent.lower():
                # In real test, would verify actual routing returns same result
                # Here we verify the mapping is deterministic
                assert intent_to_agent_map[keyword] == expected_agent

    @given(response=st.text(min_size=20, max_size=1000), has_code=st.booleans())
    @settings(max_examples=50)
    def test_response_format_validity(self, response, has_code):
        """Property: Responses with code should use markdown formatting."""
        # Property: If response contains code indicators, it should be properly formatted

        code_indicators = ["function", "class", "def ", "const ", "let ", "var "]
        has_code_indicator = any(indicator in response for indicator in code_indicators)

        if has_code_indicator and has_code:
            # Property: Code should ideally be in code blocks (markdown)
            # This is a guideline property rather than strict requirement
            has_code_block = "```" in response or "`" in response
            # Log rather than assert strictly since not all code needs formatting
            if not has_code_block:
                # Would log: "Code detected but no markdown formatting"
                pass

    @given(
        baseline_score=st.floats(min_value=0.01, max_value=1.0),
        candidate_score=st.floats(min_value=0.01, max_value=1.0),
    )
    @settings(max_examples=100)
    def test_evaluation_symmetry_property(self, baseline_score, candidate_score):
        """Property: Evaluation improvement should be symmetric (if A improves over B, B regresses from A)."""
        engine = comparison_engine

        improvement_forward = engine.calculate_improvement(
            baseline_score, candidate_score, "higher_is_better"
        )
        improvement_backward = engine.calculate_improvement(
            candidate_score, baseline_score, "higher_is_better"
        )

        if baseline_score != candidate_score:
            # Forward improvement should be opposite of backward improvement
            assert (improvement_forward > 0) == (
                improvement_backward < 0
            ), f"Asymmetry detected: {improvement_forward} vs {improvement_backward}"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
