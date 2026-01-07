"""
Set up trajectory evaluators for regression testing with AgentEvals.

This script creates trajectory match evaluators that check if agents
follow expected tool call sequences for common scenarios.
"""

import os

from langsmith import Client
from langsmith.evaluation import evaluate


def setup_trajectory_evaluators():
    """Create and apply trajectory evaluators for regression tests."""
    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        raise ValueError("LANGCHAIN_API_KEY environment variable not set")

    client = Client(api_key=api_key)

    # Define expected tool call sequences for regression tests
    EXPECTED_TRAJECTORIES = {
        "feature_implementation": [
            ("semantic_search", {"query": "*"}),  # Search for similar code
            ("read_file", {"filePath": "*"}),  # Read existing files
            ("replace_string_in_file", {"filePath": "*"}),  # Implement change
        ],
        "bug_investigation": [
            ("grep_search", {"query": "*", "isRegexp": False}),  # Search for error
            ("get_errors", {}),  # Check linter errors
            ("read_file", {"filePath": "*"}),  # Read problematic file
        ],
        "code_review": [
            ("read_file", {"filePath": "*"}),  # Read code
            ("get_errors", {}),  # Check for issues
            ("semantic_search", {"query": "*"}),  # Search for patterns
        ],
        "deployment_workflow": [
            ("read_file", {"filePath": "*"}),  # Read config
            ("replace_string_in_file", {"filePath": "*"}),  # Update config
            ("run_in_terminal", {"command": "*"}),  # Deploy
        ],
    }

    print("=" * 60)
    print("Setting up trajectory evaluators...")
    print("=" * 60)

    # Note: AgentEvals may need to be installed separately
    try:
        from agentevals import create_trajectory_match_evaluator
    except ImportError:
        print("⚠️  agentevals library not found. Install with:")
        print("    pip install agentevals")
        print("\nContinuing with trajectory definitions (for reference)...")
        print("\nExpected trajectories:")
        for scenario, trajectory in EXPECTED_TRAJECTORIES.items():
            print(f"\n{scenario}:")
            for tool, args in trajectory:
                print(f"  - {tool}({args})")
        return

    # Create evaluators
    results_summary = []

    for scenario, trajectory in EXPECTED_TRAJECTORIES.items():
        try:
            evaluator = create_trajectory_match_evaluator(
                expected_trajectory=trajectory,
                mode="subset",  # Allow extra tools, but must include expected
                name=f"trajectory_{scenario}",
            )

            print(f"\n✅ Created evaluator: trajectory_{scenario}")

            # Apply to existing dataset if it exists
            try:
                dataset_name = "error-cases-regression-suite"
                results = evaluate(
                    lambda inputs: client.get_run(inputs["run_id"]),
                    data=dataset_name,
                    evaluators=[evaluator],
                    experiment_prefix=f"regression_{scenario}",
                )

                print(f"   📊 Evaluated {scenario}: {results}")
                results_summary.append(
                    {"scenario": scenario, "status": "success", "results": str(results)}
                )

            except Exception as dataset_error:
                print(f"   ⚠️  Dataset '{dataset_name}' not found or empty")
                print(f"      Evaluator created but not applied yet")
                results_summary.append(
                    {
                        "scenario": scenario,
                        "status": "created_not_applied",
                        "error": str(dataset_error),
                    }
                )

        except Exception as e:
            print(f"\n❌ Error creating evaluator for {scenario}: {e}")
            results_summary.append(
                {"scenario": scenario, "status": "failed", "error": str(e)}
            )

    # Print summary
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    for result in results_summary:
        status_emoji = (
            "✅"
            if result["status"] == "success"
            else "⚠️" if result["status"] == "created_not_applied" else "❌"
        )
        print(f"{status_emoji} {result['scenario']}: {result['status']}")

    print("\n" + "=" * 60)
    print("Next steps:")
    print("=" * 60)
    print("1. Create regression test dataset: error-cases-regression-suite")
    print("2. Populate with known bug traces from LangSmith")
    print("3. Re-run this script to apply evaluators")
    print("4. Add to CI/CD pipeline for pre-deployment checks")


if __name__ == "__main__":
    setup_trajectory_evaluators()
