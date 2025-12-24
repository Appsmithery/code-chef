"""
Droplet Integration Tests - Live Workflow Validation

Tests deployed workflows on production droplet via SSH/HTTP.
Validates actual deployed code without import path issues.

Run with: pytest support/tests/integration/test_droplet_workflows.py -v
Requires: SSH access to 45.55.173.72 (configured in ~/.ssh/config)
"""

import json
import subprocess
from typing import Dict

import pytest
import requests


class TestDropletHealth:
    """Validate droplet services are healthy."""

    DROPLET_HOST = "45.55.173.72"
    BASE_URL = "https://codechef.appsmithery.co"

    def test_public_health_endpoint(self):
        """Test public health endpoint via HTTPS."""
        response = requests.get(f"{self.BASE_URL}/health", timeout=10)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"
        assert "orchestrator" in data.get("service", "").lower()

    def test_api_health_endpoint(self):
        """Test API health endpoint."""
        response = requests.get(f"{self.BASE_URL}/api/health", timeout=10)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "ok"

    def test_all_services_running(self):
        """Test all 8 services are running on droplet."""
        result = subprocess.run(
            [
                "ssh",
                f"root@{self.DROPLET_HOST}",
                "cd /opt/code-chef/deploy && docker compose ps",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"SSH command failed: {result.stderr}"

        # Parse output - simple check for service names
        output = result.stdout.lower()

        # Expected 8 services
        expected_services = [
            "orchestrator",
            "caddy",
            "postgres",
            "redis",
            "rag-context",
            "state-persistence",
            "agent-registry",
            "langgraph",
        ]

        for service in expected_services:
            assert service in output, f"Service {service} not found in running services"

    def test_orchestrator_logs_no_errors(self):
        """Check orchestrator logs for recent errors."""
        result = subprocess.run(
            [
                "ssh",
                f"root@{self.DROPLET_HOST}",
                "docker logs deploy-orchestrator-1 --tail=100",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0

        # Check for critical errors (allow warnings)
        error_lines = [
            line
            for line in result.stdout.split("\n")
            if "ERROR" in line and "OPENAI_API_KEY" not in line
        ]

        assert (
            len(error_lines) == 0
        ), f"Found {len(error_lines)} errors in logs:\n" + "\n".join(error_lines[:5])


class TestDropletWorkflows:
    """Validate workflow components in production."""

    DROPLET_HOST = "45.55.173.72"

    def test_workflow_router_imports(self):
        """Test WorkflowRouter can be imported in production."""
        result = subprocess.run(
            [
                "ssh",
                f"root@{self.DROPLET_HOST}",
                "docker exec deploy-orchestrator-1 python -c "
                "'from workflows.workflow_router import WorkflowRouter; "
                "router = WorkflowRouter(); "
                "print(len(router.rules))'",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Import failed: {result.stderr}"

        # Should print number of rules
        rules_count = int(result.stdout.strip())
        assert rules_count > 0, "WorkflowRouter has no rules loaded"

    def test_supervisor_agent_imports(self):
        """Test SupervisorAgent imports correctly."""
        result = subprocess.run(
            [
                "ssh",
                f"root@{self.DROPLET_HOST}",
                "docker exec deploy-orchestrator-1 python -c "
                "'from agents.supervisor import SupervisorAgent; "
                'print("OK")\'',
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Import failed: {result.stderr}"
        assert "OK" in result.stdout

    def test_graph_imports(self):
        """Test graph.py imports successfully."""
        result = subprocess.run(
            [
                "ssh",
                f"root@{self.DROPLET_HOST}",
                "docker exec deploy-orchestrator-1 python -c "
                "'import graph; print(\"OK\")'",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Import failed: {result.stderr}"
        assert "OK" in result.stdout

    def test_workflow_templates_exist(self):
        """Verify workflow templates are present."""
        result = subprocess.run(
            [
                "ssh",
                f"root@{self.DROPLET_HOST}",
                "docker exec deploy-orchestrator-1 ls workflows/templates/*.yaml",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, f"Template listing failed: {result.stderr}"

        # Should have multiple workflow templates
        templates = result.stdout.strip().split("\n")
        assert len(templates) > 0, "No workflow templates found"

    def test_git_status_clean(self):
        """Verify droplet has latest deployment."""
        result = subprocess.run(
            [
                "ssh",
                f"root@{self.DROPLET_HOST}",
                "cd /opt/code-chef && git status --porcelain",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0

        # Should have clean working directory
        assert (
            result.stdout.strip() == ""
        ), f"Droplet has uncommitted changes:\n{result.stdout}"


class TestDropletMetrics:
    """Validate observability endpoints."""

    BASE_URL = "https://codechef.appsmithery.co"

    @pytest.mark.skip(reason="Metrics endpoint may require auth")
    def test_prometheus_metrics_available(self):
        """Test Prometheus metrics endpoint."""
        response = requests.get(f"{self.BASE_URL}/metrics", timeout=10)
        assert response.status_code in [200, 401]  # 401 if auth required

    @pytest.mark.skip(reason="Token endpoint may require auth")
    def test_token_metrics_available(self):
        """Test token usage metrics."""
        response = requests.get(f"{self.BASE_URL}/metrics/tokens", timeout=10)
        assert response.status_code in [200, 401]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
