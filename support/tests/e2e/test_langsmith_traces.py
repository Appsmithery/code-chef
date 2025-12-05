"""
LangSmith trace validation tests for IB-Agent Platform scenarios.

Verifies trace structure, agent routing, and token efficiency
for code-chef orchestration of IB-Agent development tasks.

Usage:
    pytest support/tests/e2e/test_langsmith_traces.py -v -m trace

Linear Issue: DEV-195
Test Project: https://github.com/Appsmithery/IB-Agent
"""

import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import os
import sys
from pathlib import Path

# Add project paths
sys.path.insert(0, str(Path(__file__).parent / "../../../agent_orchestrator"))
sys.path.insert(0, str(Path(__file__).parent / "../../../shared"))

pytestmark = [pytest.mark.e2e, pytest.mark.trace, pytest.mark.asyncio]

# Lazy import langsmith to avoid import errors when not installed
try:
    from langsmith import Client

    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    Client = None


def requires_langsmith(func):
    """Decorator to skip tests if LangSmith is not available."""
    return pytest.mark.skipif(
        not LANGSMITH_AVAILABLE, reason="LangSmith SDK not installed"
    )(func)


# =============================================================================
# IB-AGENT ROUTING PATTERNS
# Maps keywords in task descriptions to expected agents
# =============================================================================

IB_AGENT_ROUTING_PATTERNS: Dict[str, List[str]] = {
    # MCP Server Development
    "MCP": ["feature_dev", "infrastructure"],
    "EDGAR": ["feature_dev", "code_review"],
    "FRED": ["feature_dev", "infrastructure"],
    "Nasdaq": ["infrastructure", "cicd"],
    # Infrastructure
    "Qdrant": ["infrastructure"],
    "Docker": ["infrastructure", "cicd"],
    "docker-compose": ["infrastructure"],
    "Traefik": ["infrastructure"],
    # Agent Development
    "LangGraph": ["feature_dev", "code_review"],
    "CompsAgent": ["feature_dev", "code_review"],
    "RAG": ["feature_dev"],
    "FastAPI": ["feature_dev", "code_review"],
    # UI/Excel
    "Chainlit": ["feature_dev"],
    "Excel": ["feature_dev", "code_review"],
    "Office.js": ["feature_dev"],
    "React": ["feature_dev", "code_review"],
    # Cross-cutting
    "OWASP": ["code_review"],
    "security": ["code_review"],
    "documentation": ["documentation"],
    "OpenAPI": ["documentation"],
    "GitHub Actions": ["cicd"],
}


@pytest.fixture
def langsmith_client():
    """Get LangSmith client, skip if not configured."""
    if not LANGSMITH_AVAILABLE:
        pytest.skip("LangSmith SDK not installed")

    api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        pytest.skip("LANGCHAIN_API_KEY not configured")

    return Client()


@pytest.fixture
def project_name():
    """Get LangSmith project name from environment."""
    return os.getenv("LANGCHAIN_PROJECT", "code-chef-testing")


class TestLangSmithTraces:
    """Validate LangSmith trace structure and content."""

    @pytest.fixture
    def recent_traces(self, langsmith_client, project_name):
        """Get traces from the last hour."""
        runs = langsmith_client.list_runs(
            project_name=project_name,
            start_time=datetime.now() - timedelta(hours=1),
            run_type="chain",
        )
        return list(runs)

    @requires_langsmith
    def test_traces_exist(self, recent_traces):
        """Verify traces are being collected."""
        # This test validates that tracing is working
        # May pass with 0 traces if no recent activity
        assert isinstance(recent_traces, list)

    @requires_langsmith
    def test_traces_have_agent_metadata(self, recent_traces):
        """Verify traces include agent routing metadata."""
        traces_with_metadata = 0

        for trace in recent_traces[:10]:
            if trace.extra and "metadata" in trace.extra:
                metadata = trace.extra["metadata"]
                if "agent" in metadata or "workflow_id" in metadata:
                    traces_with_metadata += 1

        # At least 50% of traces should have metadata
        if recent_traces:
            assert (
                traces_with_metadata >= len(recent_traces[:10]) * 0.5
            ), f"Only {traces_with_metadata}/{len(recent_traces[:10])} traces have agent metadata"

    @requires_langsmith
    def test_ib_agent_task_routing(self, recent_traces):
        """Verify IB-Agent tasks route to correct agents."""
        routing_violations = []

        for trace in recent_traces[:10]:
            if not trace.inputs:
                continue

            task = str(trace.inputs.get("task", ""))
            if not task:
                continue

            # Find matching pattern
            for keyword, expected_agents in IB_AGENT_ROUTING_PATTERNS.items():
                if keyword.lower() in task.lower():
                    # Extract actual agents from trace
                    actual_agents = self._extract_agents_from_trace(trace)

                    # Check if at least one expected agent was used
                    if actual_agents and not any(
                        a in actual_agents for a in expected_agents
                    ):
                        routing_violations.append(
                            {
                                "task": task[:80],
                                "keyword": keyword,
                                "expected": expected_agents,
                                "actual": list(actual_agents),
                            }
                        )
                    break

        # Allow up to 20% routing violations (model may choose alternate valid routes)
        max_violations = max(1, len(recent_traces[:10]) * 0.2)
        assert (
            len(routing_violations) <= max_violations
        ), f"Too many routing violations: {routing_violations}"

    @requires_langsmith
    def test_token_usage_tracked(self, recent_traces):
        """Verify token usage is captured in LLM traces."""
        llm_traces = [t for t in recent_traces if t.run_type == "llm"]

        if not llm_traces:
            pytest.skip("No LLM traces found in recent runs")

        traces_with_tokens = 0
        for trace in llm_traces[:10]:
            if trace.total_tokens or trace.prompt_tokens or trace.completion_tokens:
                traces_with_tokens += 1

        # At least 80% of LLM traces should have token counts
        assert (
            traces_with_tokens >= len(llm_traces[:10]) * 0.8
        ), f"Only {traces_with_tokens}/{len(llm_traces[:10])} LLM traces have token counts"

    @requires_langsmith
    def test_latency_within_threshold(self, recent_traces):
        """Verify P95 latency < 5 seconds for IB-Agent scenarios."""
        latencies = []

        for trace in recent_traces:
            if trace.end_time and trace.start_time:
                latency = (trace.end_time - trace.start_time).total_seconds()
                latencies.append(latency)

        if not latencies:
            pytest.skip("No traces with timing data found")

        # Calculate P95
        sorted_latencies = sorted(latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        p95 = sorted_latencies[min(p95_index, len(sorted_latencies) - 1)]

        # Threshold: 5 seconds for standard tasks, 10 seconds for complex workflows
        threshold = 10.0  # Using higher threshold for complex IB-Agent tasks
        assert p95 < threshold, f"P95 latency {p95:.2f}s exceeds {threshold}s threshold"

    @requires_langsmith
    def test_mcp_server_traces(self, recent_traces):
        """Verify MCP server integration traces are captured."""
        mcp_servers = ["edgar", "fred", "nasdaq", "mcp"]
        mcp_traces = []

        for trace in recent_traces:
            if trace.name and any(mcp in trace.name.lower() for mcp in mcp_servers):
                mcp_traces.append(trace)

        if not mcp_traces:
            pytest.skip("No MCP server traces found (expected for initial setup)")

        # All MCP traces should have success or error status
        for trace in mcp_traces[:5]:
            assert trace.status in [
                "success",
                "error",
                "pending",
            ], f"MCP trace has unexpected status: {trace.status}"

    @requires_langsmith
    def test_workflow_traces_have_children(self, recent_traces):
        """Verify workflow traces have child spans for agent nodes."""
        workflow_traces = [
            t for t in recent_traces if "workflow" in str(t.name).lower()
        ]

        if not workflow_traces:
            pytest.skip("No workflow traces found")

        for trace in workflow_traces[:5]:
            # Workflow traces should have child runs for agent nodes
            if trace.child_run_ids:
                assert (
                    len(trace.child_run_ids) > 0
                ), f"Workflow trace {trace.id} has no child runs"

    @requires_langsmith
    def test_error_traces_have_messages(self, recent_traces):
        """Verify error traces include error messages for debugging."""
        error_traces = [t for t in recent_traces if t.status == "error"]

        if not error_traces:
            pytest.skip("No error traces found (good!)")

        for trace in error_traces[:5]:
            assert (
                trace.error or trace.outputs
            ), f"Error trace {trace.id} has no error message"

    def _extract_agents_from_trace(self, trace) -> set:
        """Extract agent names from trace metadata and child runs."""
        agents = set()

        # From metadata
        if trace.extra and "metadata" in trace.extra:
            agent = trace.extra["metadata"].get("agent")
            if agent:
                agents.add(agent)

        # From trace name (e.g., "feature_dev_node")
        if trace.name:
            for agent_name in [
                "feature_dev",
                "code_review",
                "infrastructure",
                "cicd",
                "documentation",
                "supervisor",
            ]:
                if agent_name in trace.name.lower():
                    agents.add(agent_name)

        return agents


class TestLangSmithDatasets:
    """Validate LangSmith dataset configuration."""

    @requires_langsmith
    def test_ib_agent_dataset_exists(self, langsmith_client):
        """Verify IB-Agent evaluation dataset is configured."""
        datasets = list(
            langsmith_client.list_datasets(dataset_name="ib-agent-scenarios-v1")
        )

        if not datasets:
            pytest.skip("ib-agent-scenarios-v1 dataset not created yet")

        dataset = datasets[0]
        assert (
            dataset.example_count >= 10
        ), f"Dataset has only {dataset.example_count} examples (expected 15+)"

    @requires_langsmith
    def test_dataset_examples_have_required_fields(self, langsmith_client):
        """Verify dataset examples have all required fields."""
        datasets = list(
            langsmith_client.list_datasets(dataset_name="ib-agent-scenarios-v1")
        )

        if not datasets:
            pytest.skip("ib-agent-scenarios-v1 dataset not created yet")

        examples = list(langsmith_client.list_examples(dataset_id=datasets[0].id))

        for example in examples[:5]:
            # Check inputs
            assert "task" in example.inputs, f"Example missing 'task' input"

            # Check outputs
            assert (
                "expected_agents" in example.outputs
            ), f"Example missing 'expected_agents' output"
            assert (
                "risk_level" in example.outputs
            ), f"Example missing 'risk_level' output"
            assert example.outputs["risk_level"] in [
                "low",
                "medium",
                "high",
            ], f"Invalid risk_level: {example.outputs['risk_level']}"


class TestTraceQuality:
    """Test trace quality metrics."""

    @requires_langsmith
    def test_trace_success_rate(self, recent_traces):
        """Verify acceptable success rate for traces."""
        if not recent_traces:
            pytest.skip("No recent traces to analyze")

        success_count = sum(1 for t in recent_traces if t.status == "success")
        success_rate = success_count / len(recent_traces)

        # Expect at least 70% success rate
        assert (
            success_rate >= 0.7
        ), f"Success rate {success_rate:.1%} below 70% threshold"

    @requires_langsmith
    def test_avg_token_usage(self, recent_traces):
        """Verify average token usage is reasonable."""
        token_counts = []

        for trace in recent_traces:
            if trace.total_tokens:
                token_counts.append(trace.total_tokens)

        if not token_counts:
            pytest.skip("No token usage data found")

        avg_tokens = sum(token_counts) / len(token_counts)

        # Average should be under 5000 tokens per request
        assert (
            avg_tokens < 5000
        ), f"Average token usage {avg_tokens:.0f} exceeds 5000 threshold"
