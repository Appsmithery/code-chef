"""
Graph trajectory evaluation for LangGraph agent routing quality.

Tests supervisor agent routing decisions using AgentEvals trajectory matching.

Usage:
    pytest support/tests/evaluation/test_graph_trajectory.py -v
"""

import os
from datetime import datetime, timedelta

import pytest

try:
    from langsmith import Client

    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    pytestmark = pytest.mark.skip("LangSmith not available")

try:
    from agentevals import (
        create_graph_trajectory_llm_as_judge,
        extract_langgraph_trajectory_from_thread,
    )

    AGENTEVALS_AVAILABLE = True
except ImportError:
    AGENTEVALS_AVAILABLE = False
    pytestmark = pytest.mark.skip("AgentEvals not available")


# Graph schema for code-chef orchestrator
ORCHESTRATOR_GRAPH_SCHEMA = {
    "nodes": [
        "supervisor",
        "feature_dev",
        "code_review",
        "infrastructure",
        "cicd",
        "documentation",
    ],
    "edges": [
        ("supervisor", "feature_dev"),
        ("supervisor", "code_review"),
        ("supervisor", "infrastructure"),
        ("supervisor", "cicd"),
        ("supervisor", "documentation"),
        ("feature_dev", "END"),
        ("code_review", "END"),
        ("infrastructure", "END"),
        ("cicd", "END"),
        ("documentation", "END"),
        # Allow feature_dev -> code_review handoff
        ("feature_dev", "code_review"),
        ("code_review", "feature_dev"),
    ],
}


@pytest.fixture
def langsmith_client():
    """Get LangSmith client."""
    if not LANGSMITH_AVAILABLE:
        pytest.skip("LangSmith not available")
    return Client()


@pytest.mark.skipif(
    not LANGSMITH_AVAILABLE or not AGENTEVALS_AVAILABLE,
    reason="LangSmith or AgentEvals not available",
)
def test_supervisor_routing_quality(langsmith_client):
    """Evaluate supervisor agent routing decisions."""
    # Get recent threads from supervisor
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)

    threads = list(
        langsmith_client.list_runs(
            project_name="code-chef-production",
            filter='eq(metadata.module, "supervisor")',
            start_time=start_time,
            end_time=end_time,
            limit=20,
        )
    )

    if not threads:
        pytest.skip("No supervisor traces found in last 24 hours")

    # Create evaluator
    evaluator = create_graph_trajectory_llm_as_judge(
        graph_schema=ORCHESTRATOR_GRAPH_SCHEMA,
        criteria=(
            "Agent routing should be efficient (no unnecessary hops) and "
            "correct (task matched to appropriate specialist agent). "
            "Single-agent tasks should route directly without supervisor loops."
        ),
    )

    # Evaluate trajectories
    results = []
    for thread in threads:
        try:
            trajectory = extract_langgraph_trajectory_from_thread(thread)
            result = evaluator(thread)
            results.append(
                {
                    "thread_id": thread.id,
                    "score": result.get("score", 0.0),
                    "reasoning": result.get("reasoning", ""),
                    "trajectory": trajectory,
                }
            )
            print(
                f"Thread {thread.id}: {result.get('score', 0.0):.2f} - {result.get('reasoning', '')}"
            )
        except Exception as e:
            print(f"Warning: Failed to evaluate thread {thread.id}: {e}")

    # Assert average quality
    if results:
        avg_score = sum(r["score"] for r in results) / len(results)
        print(f"\nAverage routing quality: {avg_score:.2f}")
        assert avg_score >= 0.7, f"Average routing quality too low: {avg_score:.2f}"
    else:
        pytest.skip("No threads could be evaluated")


@pytest.mark.skipif(
    not LANGSMITH_AVAILABLE or not AGENTEVALS_AVAILABLE,
    reason="LangSmith or AgentEvals not available",
)
def test_no_unnecessary_supervisor_loops(langsmith_client):
    """Check for unnecessary supervisor routing loops."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)

    threads = list(
        langsmith_client.list_runs(
            project_name="code-chef-production",
            start_time=start_time,
            end_time=end_time,
            limit=50,
        )
    )

    if not threads:
        pytest.skip("No traces found in last 24 hours")

    excessive_loops = []

    for thread in threads:
        # Count supervisor invocations
        child_runs = list(
            langsmith_client.list_runs(
                project_name="code-chef-production",
                filter=f'eq(parent_run_id, "{thread.id}")',
            )
        )

        supervisor_count = sum(
            1
            for r in child_runs
            if r.extra.get("metadata", {}).get("module") == "supervisor"
        )

        # Flag if more than 2 supervisor calls for a single thread
        if supervisor_count > 2:
            excessive_loops.append(
                {"thread_id": thread.id, "supervisor_calls": supervisor_count}
            )

    if excessive_loops:
        print(
            f"\n⚠️  Found {len(excessive_loops)} threads with excessive supervisor loops:"
        )
        for loop in excessive_loops:
            print(
                f"   Thread {loop['thread_id']}: {loop['supervisor_calls']} supervisor calls"
            )

    # Allow up to 10% of threads to have excessive loops (tolerance for complex tasks)
    excessive_rate = len(excessive_loops) / len(threads) if threads else 0
    assert (
        excessive_rate < 0.1
    ), f"Too many threads with excessive supervisor loops: {excessive_rate:.1%}"


@pytest.mark.skipif(
    not LANGSMITH_AVAILABLE or not AGENTEVALS_AVAILABLE,
    reason="LangSmith or AgentEvals not available",
)
def test_expected_trajectories_for_common_tasks(langsmith_client):
    """Test that common task types follow expected trajectories."""
    # Define expected patterns
    expected_patterns = {
        "code_implementation": ["supervisor", "feature_dev"],
        "code_review_only": ["supervisor", "code_review"],
        "deployment": ["supervisor", "infrastructure"],
        "ci_cd_setup": ["supervisor", "cicd"],
        "documentation": ["supervisor", "documentation"],
    }

    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)

    # Check each pattern
    for task_type, expected_path in expected_patterns.items():
        threads = list(
            langsmith_client.list_runs(
                project_name="code-chef-production",
                filter=f'contains(metadata.task_category, "{task_type}")',
                start_time=start_time,
                end_time=end_time,
                limit=10,
            )
        )

        if not threads:
            continue

        matching = 0
        for thread in threads:
            child_runs = list(
                langsmith_client.list_runs(
                    project_name="code-chef-production",
                    filter=f'eq(parent_run_id, "{thread.id}")',
                )
            )

            actual_path = [
                r.extra.get("metadata", {}).get("module", "unknown")
                for r in sorted(child_runs, key=lambda x: x.start_time)
            ]

            # Check if expected path is subset of actual path
            if all(node in actual_path for node in expected_path):
                matching += 1

        if threads:
            match_rate = matching / len(threads)
            print(f"{task_type}: {match_rate:.1%} matching expected trajectory")
            assert (
                match_rate >= 0.6
            ), f"Low trajectory match rate for {task_type}: {match_rate:.1%}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
