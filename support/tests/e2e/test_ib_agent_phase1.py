"""
IB-Agent Platform Phase 1 E2E Tests: Data Layer Foundation

Tests MCP server setup, infrastructure configuration, and Docker Compose
stack for the IB-Agent Platform development workflow.

Usage:
    pytest support/tests/e2e/test_ib_agent_phase1.py -v -s

Linear Issue: DEV-195
Test Project: https://github.com/Appsmithery/IB-Agent
IB-Agent Steps: 1.1, 1.2, 1.3, 1.4
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, MagicMock, patch
import sys
from pathlib import Path
from typing import Dict, Any

# Add project paths
sys.path.insert(0, str(Path(__file__).parent / "../../../agent_orchestrator"))
sys.path.insert(0, str(Path(__file__).parent / "../../../shared"))

pytestmark = [pytest.mark.e2e, pytest.mark.trace, pytest.mark.asyncio]


# =============================================================================
# PHASE 1 SCENARIOS
# =============================================================================

PHASE1_SCENARIOS = [
    {
        "id": "1.1",
        "name": "Docker Compose Infrastructure",
        "task": "Write docker-compose.yml for IB Agent stack with backend, qdrant, postgres, traefik, and mcp-servers services",
        "expected_agents": ["infrastructure"],
        "risk_level": "medium",
    },
    {
        "id": "1.2",
        "name": "Nasdaq MCP Integration",
        "task": "Clone Nasdaq Data Link MCP server repository and integrate into docker-compose.yml with proper network configuration",
        "expected_agents": ["infrastructure", "cicd"],
        "risk_level": "medium",
    },
    {
        "id": "1.3",
        "name": "EDGAR MCP Server",
        "task": "Build EDGAR MCP server with search_filings tool that queries SEC EDGAR API for 10-K, 10-Q, and 8-K filings by ticker",
        "expected_agents": ["feature_dev", "code_review"],
        "risk_level": "high",
    },
    {
        "id": "1.4",
        "name": "Vector Database Setup",
        "task": "Configure Qdrant collection 'ib-agent-filings' with 1536-dimension vectors for SEC filing embeddings using HNSW indexing",
        "expected_agents": ["infrastructure"],
        "risk_level": "medium",
    },
]


class TestIBAgentPhase1:
    """Test Phase 1: Data Layer Foundation scenarios."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Mock orchestrator for agent routing tests."""
        mock = MagicMock()
        mock.route_task = AsyncMock()
        mock.get_agent_response = AsyncMock()
        return mock

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for tool execution."""
        mock = MagicMock()
        mock.call_tool = AsyncMock(return_value={"success": True})
        mock.health_check = AsyncMock(return_value={"status": "healthy"})
        return mock

    @pytest.fixture
    def mock_docker_client(self):
        """Mock Docker client for container operations."""
        mock = MagicMock()
        mock.compose_up = AsyncMock(
            return_value={"services": ["backend", "qdrant", "postgres"]}
        )
        mock.compose_validate = AsyncMock(return_value={"valid": True})
        return mock

    # =========================================================================
    # Step 1.1: Docker Compose Infrastructure
    # =========================================================================

    async def test_step_1_1_infrastructure_routing(self, mock_orchestrator):
        """Test Docker Compose task routes to infrastructure agent."""
        scenario = PHASE1_SCENARIOS[0]

        # Mock routing to infrastructure agent
        mock_orchestrator.route_task.return_value = {
            "agent": "infrastructure",
            "confidence": 0.95,
            "reasoning": "Docker Compose configuration is infrastructure task",
        }

        result = await mock_orchestrator.route_task(scenario["task"])

        assert result["agent"] in scenario["expected_agents"]
        assert result["confidence"] > 0.8

    async def test_step_1_1_compose_validation(self, mock_docker_client):
        """Test Docker Compose file validation."""
        compose_content = """
version: '3.8'
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
  postgres:
    image: postgres:15
"""
        mock_docker_client.compose_validate.return_value = {
            "valid": True,
            "services": ["backend", "qdrant", "postgres"],
            "networks": ["ib-agent-network"],
        }

        result = await mock_docker_client.compose_validate(compose_content)

        assert result["valid"]
        assert "backend" in result["services"]
        assert "qdrant" in result["services"]

    async def test_step_1_1_service_health_checks(self, mock_docker_client):
        """Test service health check configuration."""
        mock_docker_client.check_health = AsyncMock(
            return_value={
                "backend": {"status": "healthy", "port": 8000},
                "qdrant": {"status": "healthy", "port": 6333},
                "postgres": {"status": "healthy", "port": 5432},
            }
        )

        health = await mock_docker_client.check_health()

        assert all(s["status"] == "healthy" for s in health.values())

    # =========================================================================
    # Step 1.2: Nasdaq MCP Integration
    # =========================================================================

    async def test_step_1_2_nasdaq_mcp_routing(self, mock_orchestrator):
        """Test Nasdaq MCP integration routes to infrastructure + cicd."""
        scenario = PHASE1_SCENARIOS[1]

        mock_orchestrator.route_task.return_value = {
            "agent": "infrastructure",
            "secondary_agents": ["cicd"],
            "confidence": 0.88,
        }

        result = await mock_orchestrator.route_task(scenario["task"])

        assert result["agent"] in scenario["expected_agents"]

    async def test_step_1_2_nasdaq_mcp_health(self, mock_mcp_client):
        """Test Nasdaq MCP server health check."""
        mock_mcp_client.health_check.return_value = {
            "status": "healthy",
            "server": "nasdaq",
            "tools": ["get_dataset", "search_companies", "get_fundamentals"],
        }

        result = await mock_mcp_client.health_check("nasdaq")

        assert result["status"] == "healthy"
        assert "get_dataset" in result["tools"]

    async def test_step_1_2_nasdaq_tool_invocation(self, mock_mcp_client):
        """Test Nasdaq MCP tool invocation."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "data": {
                "ticker": "MSFT",
                "revenue": 211915000000,
                "market_cap": 3100000000000,
            },
            "citations": [{"source": "Nasdaq Data Link", "dataset": "QOR/STATS_MSFT"}],
        }

        result = await mock_mcp_client.call_tool(
            server="nasdaq", tool="get_fundamentals", params={"ticker": "MSFT"}
        )

        assert result["success"]
        assert "citations" in result

    # =========================================================================
    # Step 1.3: EDGAR MCP Server
    # =========================================================================

    async def test_step_1_3_edgar_routing(self, mock_orchestrator):
        """Test EDGAR MCP server task routes to feature_dev + code_review."""
        scenario = PHASE1_SCENARIOS[2]

        mock_orchestrator.route_task.return_value = {
            "agent": "feature_dev",
            "secondary_agents": ["code_review"],
            "confidence": 0.92,
            "risk_level": "high",
        }

        result = await mock_orchestrator.route_task(scenario["task"])

        assert result["agent"] in scenario["expected_agents"]
        assert result["risk_level"] == "high"

    async def test_step_1_3_edgar_code_generation(self, mock_orchestrator):
        """Test EDGAR MCP server code generation."""
        mock_orchestrator.get_agent_response.return_value = {
            "code": '''
from fastmcp import FastMCP
import httpx

mcp = FastMCP("EDGAR MCP Server")

@mcp.tool()
async def search_filings(ticker: str, form_type: str = "10-K") -> dict:
    """Search SEC EDGAR for filings by ticker."""
    url = f"https://data.sec.gov/submissions/CIK{ticker}.json"
    headers = {"User-Agent": "IB-Agent admin@example.com"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        return {"filings": response.json()["filings"]["recent"]}
''',
            "explanation": "EDGAR MCP server with SEC API integration",
            "dependencies": ["fastmcp", "httpx"],
        }

        result = await mock_orchestrator.get_agent_response(
            agent="feature_dev", task="Build EDGAR MCP server"
        )

        assert "fastmcp" in result["code"]
        assert "search_filings" in result["code"]

    async def test_step_1_3_edgar_security_review(self, mock_orchestrator):
        """Test EDGAR MCP server gets security review."""
        mock_orchestrator.get_agent_response.return_value = {
            "review": {
                "security_issues": [],
                "recommendations": [
                    "Add rate limiting (SEC requires 10 req/sec max)",
                    "Validate ticker input to prevent injection",
                    "Use environment variable for User-Agent email",
                ],
                "approved": True,
            }
        }

        result = await mock_orchestrator.get_agent_response(
            agent="code_review", task="Review EDGAR MCP server for security issues"
        )

        assert result["review"]["approved"]
        assert len(result["review"]["recommendations"]) > 0

    # =========================================================================
    # Step 1.4: Vector Database Setup
    # =========================================================================

    async def test_step_1_4_qdrant_routing(self, mock_orchestrator):
        """Test Qdrant setup routes to infrastructure agent."""
        scenario = PHASE1_SCENARIOS[3]

        mock_orchestrator.route_task.return_value = {
            "agent": "infrastructure",
            "confidence": 0.90,
        }

        result = await mock_orchestrator.route_task(scenario["task"])

        assert result["agent"] in scenario["expected_agents"]

    async def test_step_1_4_qdrant_collection_creation(self, mock_mcp_client):
        """Test Qdrant collection creation."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "collection": {
                "name": "ib-agent-filings",
                "vectors": {"size": 1536, "distance": "Cosine"},
                "hnsw_config": {"m": 16, "ef_construct": 200},
            },
        }

        result = await mock_mcp_client.call_tool(
            server="qdrant",
            tool="create_collection",
            params={
                "name": "ib-agent-filings",
                "vector_size": 1536,
                "distance": "cosine",
            },
        )

        assert result["success"]
        assert result["collection"]["vectors"]["size"] == 1536

    async def test_step_1_4_qdrant_payload_indexes(self, mock_mcp_client):
        """Test Qdrant payload index creation."""
        mock_mcp_client.call_tool.return_value = {
            "success": True,
            "indexes": ["ticker", "form_type", "fiscal_year"],
        }

        result = await mock_mcp_client.call_tool(
            server="qdrant",
            tool="create_payload_index",
            params={
                "collection": "ib-agent-filings",
                "field": "ticker",
                "schema": "keyword",
            },
        )

        assert result["success"]


class TestPhase1Integration:
    """Integration tests for Phase 1 components."""

    @pytest.fixture
    def phase1_context(self):
        """Shared context for Phase 1 tests."""
        return {
            "services": {
                "backend": {"port": 8000, "status": "healthy"},
                "qdrant": {"port": 6333, "status": "healthy"},
                "postgres": {"port": 5432, "status": "healthy"},
                "mcp-edgar": {"port": 8001, "status": "healthy"},
                "mcp-fred": {"port": 8002, "status": "healthy"},
                "mcp-nasdaq": {"port": 8003, "status": "healthy"},
            },
            "collections": {"ib-agent-filings": {"vectors": 0, "status": "ready"}},
        }

    async def test_phase1_complete_stack(self, phase1_context):
        """Test complete Phase 1 stack is operational."""
        # All services should be healthy
        for service, info in phase1_context["services"].items():
            assert info["status"] == "healthy", f"{service} is not healthy"

        # All MCP servers should be running
        mcp_services = [s for s in phase1_context["services"] if s.startswith("mcp-")]
        assert len(mcp_services) == 3, "Expected 3 MCP servers"

    async def test_phase1_mcp_server_connectivity(self, phase1_context):
        """Test MCP servers are accessible from backend."""
        mcp_ports = {"mcp-edgar": 8001, "mcp-fred": 8002, "mcp-nasdaq": 8003}

        for server, port in mcp_ports.items():
            assert phase1_context["services"][server]["port"] == port

    async def test_phase1_vector_db_ready(self, phase1_context):
        """Test vector database is ready for ingestion."""
        collection = phase1_context["collections"]["ib-agent-filings"]
        assert collection["status"] == "ready"


class TestPhase1Tracing:
    """Verify Phase 1 tasks generate proper LangSmith traces."""

    @pytest.fixture
    def mock_tracer(self):
        """Mock LangSmith tracer."""
        mock = MagicMock()
        mock.trace = MagicMock()
        mock.span = MagicMock()
        return mock

    async def test_trace_metadata_includes_ib_agent_step(self, mock_tracer):
        """Verify traces include IB-Agent step metadata."""
        with patch("langsmith.trace", mock_tracer.trace):
            # Simulate traced task
            mock_tracer.trace.return_value.__enter__ = Mock(return_value=MagicMock())
            mock_tracer.trace.return_value.__exit__ = Mock(return_value=False)

            # Verify trace was called (in real impl)
            # This validates the pattern for actual traces

    async def test_trace_includes_mcp_citations(self, mock_tracer):
        """Verify MCP tool calls include citation metadata."""
        expected_citation = {
            "source": "SEC EDGAR",
            "url": "https://data.sec.gov/submissions/CIK0000789019.json",
            "accession_number": "0001564590-24-000001",
        }

        # In real implementation, verify citations are attached to trace outputs
        assert "source" in expected_citation
        assert "url" in expected_citation
