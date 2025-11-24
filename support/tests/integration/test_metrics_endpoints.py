"""
Integration Tests for Metrics Endpoints

Tests /metrics/tokens (JSON) and /metrics (Prometheus) endpoints in orchestrator service.
"""

import pytest
import sys
import requests
import time
from pathlib import Path
from typing import Dict, Any

# Add paths
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root / "shared"))
sys.path.insert(0, str(repo_root / "agent_orchestrator"))

# Test configuration
ORCHESTRATOR_URL = "http://localhost:8001"
METRICS_TOKENS_ENDPOINT = f"{ORCHESTRATOR_URL}/metrics/tokens"
METRICS_PROMETHEUS_ENDPOINT = f"{ORCHESTRATOR_URL}/metrics"
HEALTH_ENDPOINT = f"{ORCHESTRATOR_URL}/health"


class TestMetricsTokensEndpoint:
    """Test /metrics/tokens JSON API endpoint"""

    @pytest.fixture(autouse=True)
    def check_service_health(self):
        """Verify orchestrator service is running before tests"""
        try:
            response = requests.get(HEALTH_ENDPOINT, timeout=5)
            if response.status_code != 200:
                pytest.skip("Orchestrator service not healthy")
        except requests.exceptions.RequestException:
            pytest.skip("Orchestrator service not reachable")

    def test_endpoint_accessible(self):
        """Test /metrics/tokens endpoint is accessible"""
        response = requests.get(METRICS_TOKENS_ENDPOINT, timeout=5)

        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"

    def test_response_structure(self):
        """Test JSON response has required structure"""
        response = requests.get(METRICS_TOKENS_ENDPOINT, timeout=5)
        data = response.json()

        # Check top-level keys
        assert "per_agent" in data
        assert "totals" in data
        assert "tracking_since" in data
        assert "uptime_seconds" in data
        assert "timestamp" in data

        # Check types
        assert isinstance(data["per_agent"], dict)
        assert isinstance(data["totals"], dict)
        assert isinstance(data["uptime_seconds"], (int, float))

    def test_per_agent_structure(self):
        """Test per-agent data has correct fields"""
        response = requests.get(METRICS_TOKENS_ENDPOINT, timeout=5)
        data = response.json()

        per_agent = data["per_agent"]

        if len(per_agent) == 0:
            pytest.skip("No agent data yet (no LLM calls made)")

        # Pick first agent
        agent_name = list(per_agent.keys())[0]
        agent_data = per_agent[agent_name]

        # Check required fields
        required_fields = [
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "total_cost",
            "call_count",
            "total_latency",
            "model",
            "avg_tokens_per_call",
            "avg_cost_per_call",
            "avg_latency_seconds",
        ]

        for field in required_fields:
            assert field in agent_data, f"Missing field: {field}"

        # Check types
        assert isinstance(agent_data["prompt_tokens"], int)
        assert isinstance(agent_data["completion_tokens"], int)
        assert isinstance(agent_data["total_tokens"], int)
        assert isinstance(agent_data["total_cost"], (int, float))
        assert isinstance(agent_data["call_count"], int)
        assert isinstance(agent_data["model"], str)

    def test_totals_structure(self):
        """Test totals aggregation"""
        response = requests.get(METRICS_TOKENS_ENDPOINT, timeout=5)
        data = response.json()

        totals = data["totals"]

        # Check required fields
        assert "total_tokens" in totals
        assert "total_cost" in totals
        assert "total_calls" in totals
        assert "total_latency" in totals

        # Check types
        assert isinstance(totals["total_tokens"], int)
        assert isinstance(totals["total_cost"], (int, float))
        assert isinstance(totals["total_calls"], int)

    def test_totals_match_per_agent_sum(self):
        """Test totals equal sum of per-agent values"""
        response = requests.get(METRICS_TOKENS_ENDPOINT, timeout=5)
        data = response.json()

        if len(data["per_agent"]) == 0:
            pytest.skip("No agent data yet")

        # Calculate sums from per_agent
        calculated_total_tokens = sum(
            agent["total_tokens"] for agent in data["per_agent"].values()
        )
        calculated_total_calls = sum(
            agent["call_count"] for agent in data["per_agent"].values()
        )

        # Compare with reported totals
        assert data["totals"]["total_tokens"] == calculated_total_tokens
        assert data["totals"]["total_calls"] == calculated_total_calls

        # Cost may have rounding differences
        calculated_total_cost = sum(
            agent["total_cost"] for agent in data["per_agent"].values()
        )
        assert abs(data["totals"]["total_cost"] - calculated_total_cost) < 0.001

    def test_efficiency_metrics_calculated_correctly(self):
        """Test avg_tokens_per_call and avg_cost_per_call are correct"""
        response = requests.get(METRICS_TOKENS_ENDPOINT, timeout=5)
        data = response.json()

        if len(data["per_agent"]) == 0:
            pytest.skip("No agent data yet")

        for agent_name, agent_data in data["per_agent"].items():
            if agent_data["call_count"] == 0:
                continue

            # Recalculate averages
            expected_avg_tokens = agent_data["total_tokens"] / agent_data["call_count"]
            expected_avg_cost = agent_data["total_cost"] / agent_data["call_count"]
            expected_avg_latency = (
                agent_data["total_latency"] / agent_data["call_count"]
            )

            # Check (allow small floating point errors)
            assert (
                abs(agent_data["avg_tokens_per_call"] - expected_avg_tokens) < 0.1
            ), f"{agent_name}: avg_tokens_per_call mismatch"

            assert (
                abs(agent_data["avg_cost_per_call"] - expected_avg_cost) < 0.000001
            ), f"{agent_name}: avg_cost_per_call mismatch"

            assert (
                abs(agent_data["avg_latency_seconds"] - expected_avg_latency) < 0.01
            ), f"{agent_name}: avg_latency_seconds mismatch"

    def test_uptime_increases(self):
        """Test uptime_seconds increases over time"""
        response1 = requests.get(METRICS_TOKENS_ENDPOINT, timeout=5)
        data1 = response1.json()

        time.sleep(1)

        response2 = requests.get(METRICS_TOKENS_ENDPOINT, timeout=5)
        data2 = response2.json()

        assert data2["uptime_seconds"] > data1["uptime_seconds"]
        assert data2["tracking_since"] == data1["tracking_since"]

    def test_cost_non_negative(self):
        """Test all cost values are non-negative"""
        response = requests.get(METRICS_TOKENS_ENDPOINT, timeout=5)
        data = response.json()

        # Check per-agent costs
        for agent_data in data["per_agent"].values():
            assert agent_data["total_cost"] >= 0
            assert agent_data["avg_cost_per_call"] >= 0

        # Check total cost
        assert data["totals"]["total_cost"] >= 0

    def test_note_field_present(self):
        """Test note field explains cost source"""
        response = requests.get(METRICS_TOKENS_ENDPOINT, timeout=5)
        data = response.json()

        assert "note" in data
        assert "config/agents/models.yaml" in data["note"]


class TestMetricsPrometheusEndpoint:
    """Test /metrics Prometheus format endpoint"""

    @pytest.fixture(autouse=True)
    def check_service_health(self):
        """Verify orchestrator service is running before tests"""
        try:
            response = requests.get(HEALTH_ENDPOINT, timeout=5)
            if response.status_code != 200:
                pytest.skip("Orchestrator service not healthy")
        except requests.exceptions.RequestException:
            pytest.skip("Orchestrator service not reachable")

    def test_endpoint_accessible(self):
        """Test /metrics endpoint is accessible"""
        response = requests.get(METRICS_PROMETHEUS_ENDPOINT, timeout=5)

        assert response.status_code == 200
        assert "text/plain" in response.headers["Content-Type"]

    def test_llm_metrics_present(self):
        """Test LLM-specific metrics are exported"""
        response = requests.get(METRICS_PROMETHEUS_ENDPOINT, timeout=5)
        text = response.text

        # Check for token metrics
        assert "llm_tokens_total" in text, "llm_tokens_total metric missing"
        assert "llm_cost_usd_total" in text, "llm_cost_usd_total metric missing"
        assert "llm_latency_seconds" in text, "llm_latency_seconds metric missing"
        assert "llm_calls_total" in text, "llm_calls_total metric missing"

    def test_metric_labels(self):
        """Test metrics have correct labels"""
        response = requests.get(METRICS_PROMETHEUS_ENDPOINT, timeout=5)
        text = response.text

        # llm_tokens_total should have agent and type labels
        if "llm_tokens_total{" in text:
            assert 'agent="' in text
            assert 'type="prompt"' in text or 'type="completion"' in text

        # llm_cost_usd_total should have agent label
        if "llm_cost_usd_total{" in text:
            assert 'agent="' in text

    def test_prometheus_format_valid(self):
        """Test metrics follow Prometheus text format"""
        response = requests.get(METRICS_PROMETHEUS_ENDPOINT, timeout=5)
        lines = response.text.split("\n")

        for line in lines:
            if not line or line.startswith("#"):
                continue  # Skip comments and empty lines

            # Should have metric_name{labels} value [timestamp]
            assert " " in line, f"Invalid format: {line}"

            parts = line.split(" ", 1)
            metric_name = parts[0]

            # Metric name should be valid
            assert metric_name, "Empty metric name"

    def test_histogram_buckets(self):
        """Test latency histogram has buckets"""
        response = requests.get(METRICS_PROMETHEUS_ENDPOINT, timeout=5)
        text = response.text

        if "llm_latency_seconds_bucket" not in text:
            pytest.skip("No latency data yet")

        # Should have multiple bucket labels
        assert 'le="0.1"' in text
        assert 'le="1.0"' in text
        assert 'le="5.0"' in text
        assert 'le="+Inf"' in text

    def test_http_metrics_present(self):
        """Test FastAPI HTTP metrics are present"""
        response = requests.get(METRICS_PROMETHEUS_ENDPOINT, timeout=5)
        text = response.text

        # FastAPI instrumentation metrics
        assert (
            "http_requests_total" in text or "http_request_duration_seconds" in text
        ), "HTTP metrics missing (prometheus-fastapi-instrumentator)"


class TestEndToEndTracking:
    """Test end-to-end token tracking flow"""

    @pytest.fixture(autouse=True)
    def check_service_health(self):
        """Verify orchestrator service is running before tests"""
        try:
            response = requests.get(HEALTH_ENDPOINT, timeout=5)
            if response.status_code != 200:
                pytest.skip("Orchestrator service not healthy")
        except requests.exceptions.RequestException:
            pytest.skip("Orchestrator service not reachable")

    @pytest.mark.slow
    def test_llm_call_updates_metrics(self):
        """Test LLM call increments token counters"""
        # Get baseline
        response1 = requests.get(METRICS_TOKENS_ENDPOINT, timeout=5)
        data1 = response1.json()
        baseline_calls = data1["totals"]["total_calls"]

        # Trigger LLM call (requires orchestrator to be running)
        orchestrate_payload = {
            "description": "Test task for metrics validation",
            "priority": "low",
        }

        try:
            requests.post(
                f"{ORCHESTRATOR_URL}/orchestrate",
                json=orchestrate_payload,
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Failed to trigger orchestration: {e}")

        # Wait for processing
        time.sleep(2)

        # Check metrics updated
        response2 = requests.get(METRICS_TOKENS_ENDPOINT, timeout=5)
        data2 = response2.json()

        assert (
            data2["totals"]["total_calls"] > baseline_calls
        ), "LLM call did not increment call counter"

    def test_metrics_consistency_across_endpoints(self):
        """Test /metrics/tokens and /metrics report consistent data"""
        # Get JSON metrics
        json_response = requests.get(METRICS_TOKENS_ENDPOINT, timeout=5)
        json_data = json_response.json()

        # Get Prometheus metrics
        prom_response = requests.get(METRICS_PROMETHEUS_ENDPOINT, timeout=5)
        prom_text = prom_response.text

        if json_data["totals"]["total_calls"] == 0:
            pytest.skip("No calls yet, cannot compare")

        # Parse Prometheus counters (simple extraction)
        for agent_name in json_data["per_agent"].keys():
            # Look for agent in Prometheus output
            agent_label = f'agent="{agent_name}"'
            assert agent_label in prom_text, f"Agent {agent_name} not in Prometheus"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
