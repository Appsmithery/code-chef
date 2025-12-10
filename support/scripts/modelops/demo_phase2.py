#!/usr/bin/env python3
"""Quick example demonstrating Phase 2 registry and evaluation functionality."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from agent_orchestrator.agents.infrastructure.modelops import (
    ModelEvaluator,
    ModelRegistry,
)


def demo_registry():
    """Demonstrate registry operations."""
    print("=== Registry Demo ===\n")

    registry = ModelRegistry()

    # 1. Add a new model version
    print("1. Adding model version...")
    version = registry.add_model_version(
        agent_name="feature_dev",
        version="v2.0.0-demo",
        model_id="alextorelli/codechef-feature-dev-demo",
        training_config={
            "base_model": "microsoft/Phi-3-mini-4k-instruct",
            "training_method": "sft",
            "training_dataset": "ls://demo-train",
            "eval_dataset": "ls://demo-eval",
            "num_epochs": 3,
            "is_demo": True,
        },
        job_id="job_demo_123",
    )
    print(f"   ✓ Added version: {version.version}")
    print(f"   ✓ Model ID: {version.model_id}")
    print(f"   ✓ Status: {version.deployment_status}")

    # 2. Add evaluation scores
    print("\n2. Adding evaluation scores...")
    registry.update_evaluation_scores(
        agent_name="feature_dev",
        version="v2.0.0-demo",
        eval_scores={
            "accuracy": 0.87,
            "workflow_completeness": 0.91,
            "token_efficiency": 0.82,
            "latency_threshold": 0.90,
            "mcp_integration_quality": 0.75,
            "baseline_improvement_pct": 15.0,
        },
    )
    print("   ✓ Evaluation scores stored")

    # 3. Deploy as canary
    print("\n3. Deploying as 20% canary...")
    registry.set_canary_model("feature_dev", "v2.0.0-demo", canary_pct=20)
    canary = registry.get_canary_model("feature_dev")
    if canary:
        print(f"   ✓ Canary deployed: {canary.version}")
        print(f"   ✓ Status: {canary.deployment_status}")
    else:
        print("   ⚠ Canary not found")

    # 4. List versions
    print("\n4. Listing model versions...")
    versions = registry.list_versions("feature_dev", limit=5)
    print(f"   ✓ Found {len(versions)} versions:")
    for v in versions:
        print(f"      - {v.version}: {v.deployment_status}")


def demo_evaluation():
    """Demonstrate evaluation and comparison."""
    print("\n\n=== Evaluation Demo ===\n")

    registry = ModelRegistry()
    evaluator = ModelEvaluator(registry=registry)

    # Add baseline model
    print("1. Setting up baseline model...")
    registry.add_model_version(
        agent_name="code_review",
        version="v1.0.0-baseline",
        model_id="microsoft/Phi-3-mini-4k-instruct",
        training_config={
            "base_model": "microsoft/Phi-3-mini-4k-instruct",
            "training_method": "sft",
            "training_dataset": "ls://baseline-train",
        },
    )
    registry.update_evaluation_scores(
        "code_review",
        "v1.0.0-baseline",
        {
            "accuracy": 0.75,
            "workflow_completeness": 0.80,
            "token_efficiency": 0.70,
            "latency_threshold": 0.85,
        },
    )
    registry.set_current_model("code_review", "v1.0.0-baseline")
    print("   ✓ Baseline model configured")

    # Add candidate model
    print("\n2. Adding candidate model...")
    registry.add_model_version(
        agent_name="code_review",
        version="v2.0.0-candidate",
        model_id="alextorelli/codechef-code-review-v2",
        training_config={
            "base_model": "microsoft/Phi-3-mini-4k-instruct",
            "training_method": "sft",
            "training_dataset": "ls://improved-train",
            "eval_dataset": "ls://eval-dataset",
        },
    )
    registry.update_evaluation_scores(
        "code_review",
        "v2.0.0-candidate",
        {
            "accuracy": 0.87,  # +16% improvement
            "workflow_completeness": 0.91,  # +13.75% improvement
            "token_efficiency": 0.82,  # +17% improvement
            "latency_threshold": 0.90,  # +5.9% improvement
        },
    )
    print("   ✓ Candidate model configured")

    # Compare models
    print("\n3. Comparing candidate vs baseline...")
    comparison = evaluator.compare_models(
        agent_name="code_review",
        candidate_version="v2.0.0-candidate",
        baseline_version="v1.0.0-baseline",
    )

    print(f"\n   === Comparison Results ===")
    print(f"   Overall improvement: {comparison.overall_improvement_pct:+.1f}%")
    print(f"   Recommendation: {comparison.recommendation.upper()}")
    print(f"   Reasoning: {comparison.reasoning}")

    print(f"\n   Improvements:")
    for metric, pct in comparison.improvements.items():
        baseline = comparison.baseline_scores[metric]
        candidate = comparison.candidate_scores[metric]
        print(f"      ✓ {metric}: {baseline:.3f} → {candidate:.3f} (+{pct:.1f}%)")

    if comparison.degradations:
        print(f"\n   Degradations:")
        for metric, pct in comparison.degradations.items():
            baseline = comparison.baseline_scores[metric]
            candidate = comparison.candidate_scores[metric]
            print(f"      ⚠ {metric}: {baseline:.3f} → {candidate:.3f} (-{pct:.1f}%)")

    # Generate report
    print("\n4. Generating comparison report...")
    report = evaluator.generate_comparison_report(comparison)
    print("   ✓ Report generated (markdown)")
    print("\n   === Report Preview ===")
    print(report[:500] + "...\n")


if __name__ == "__main__":
    print("ModelOps Phase 2: Registry & Evaluation Demo")
    print("=" * 60)

    try:
        demo_registry()
        demo_evaluation()

        print("\n" + "=" * 60)
        print("✅ Demo complete!")
        print("\nNext steps:")
        print("  1. Phase 3 will add deployment automation")
        print("  2. Infrastructure agent integration")
        print("  3. VS Code commands (Phase 4)")

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        raise
