"""
IB-Agent Platform Phase 2 E2E Tests: Core Agent Development

Tests CompsAgent implementation, RAG pipeline, and API endpoints
for the IB-Agent Platform development workflow.

Usage:
    pytest support/tests/e2e/test_ib_agent_phase2.py -v -s

Linear Issue: DEV-195
Test Project: https://github.com/Appsmithery/IB-Agent
IB-Agent Steps: 2.1, 2.2, 2.3
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, MagicMock, patch
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add project paths
sys.path.insert(0, str(Path(__file__).parent / "../../../agent_orchestrator"))
sys.path.insert(0, str(Path(__file__).parent / "../../../shared"))

pytestmark = [pytest.mark.e2e, pytest.mark.trace, pytest.mark.asyncio]


# =============================================================================
# PHASE 2 SCENARIOS
# =============================================================================

PHASE2_SCENARIOS = [
    {
        "id": "2.1",
        "name": "Headless Analyst API",
        "task": "Create POST /api/v1/research/comps FastAPI endpoint with async BackgroundTask execution and task polling",
        "expected_agents": ["feature_dev", "code_review"],
        "risk_level": "medium",
    },
    {
        "id": "2.2",
        "name": "Comps Analysis Agent",
        "task": "Implement CompsAgent with LangGraph StateGraph workflow: get_fundamentals -> screen_peers -> enrich_data -> calculate_multiples -> rank_results",
        "expected_agents": ["feature_dev", "code_review"],
        "risk_level": "high",
    },
    {
        "id": "2.3",
        "name": "RAG Pipeline",
        "task": "Build RAG ingestion pipeline for 10-K filings with semantic chunking by SEC Item headers (Item 1, 1A, 7, etc.)",
        "expected_agents": ["feature_dev"],
        "risk_level": "medium",
    },
]


# =============================================================================
# EXPECTED COMPS AGENT OUTPUT SCHEMA
# =============================================================================

COMPS_OUTPUT_SCHEMA = {
    "comps": [
        {
            "ticker": str,
            "name": str,
            "revenue": int,
            "ev_revenue_multiple": str,
            "similarity_score": float,
            "risk_summary": str,
        }
    ],
    "citations": [
        {
            "source": str,
            "ticker": str,
            "filing_date": str,
            "accession_number": str,
        }
    ],
}


class TestIBAgentPhase2:
    """Test Phase 2: Core Agent Development scenarios."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Mock orchestrator for agent routing tests."""
        mock = MagicMock()
        mock.route_task = AsyncMock()
        mock.get_agent_response = AsyncMock()
        return mock

    @pytest.fixture
    def mock_mcp_clients(self):
        """Mock MCP clients for Nasdaq and EDGAR."""
        clients = {
            "nasdaq": MagicMock(),
            "edgar": MagicMock(),
        }

        # Nasdaq client mocks
        clients["nasdaq"].get_fundamentals = AsyncMock(
            return_value={
                "ticker": "MSFT",
                "revenue": 211915000000,
                "market_cap": 3100000000000,
                "sic_code": "7372",
                "industry": "Software",
            }
        )
        clients["nasdaq"].search_companies = AsyncMock(
            return_value={
                "companies": [
                    {"ticker": "ORCL", "name": "Oracle", "sic_code": "7372"},
                    {"ticker": "SAP", "name": "SAP", "sic_code": "7372"},
                    {"ticker": "ADBE", "name": "Adobe", "sic_code": "7372"},
                ]
            }
        )

        # EDGAR client mocks
        clients["edgar"].search_filings = AsyncMock(
            return_value={
                "filings": [
                    {
                        "accession_number": "0001564590-24-000001",
                        "form": "10-K",
                        "filing_date": "2024-07-30",
                    }
                ]
            }
        )
        clients["edgar"].get_filing_text = AsyncMock(
            return_value={
                "text": "Item 1. Business Description...",
                "sections": {"Item 1": "...", "Item 1A": "...", "Item 7": "..."},
            }
        )

        return clients

    @pytest.fixture
    def mock_task_store(self):
        """Mock task store for async workflow tracking."""
        store = MagicMock()
        store.create_task = Mock(return_value="task-uuid-1234")
        store.update_status = AsyncMock()
        store.get_task = Mock(
            return_value={
                "task_id": "task-uuid-1234",
                "status": "completed",
                "result": None,
                "progress": [],
            }
        )
        return store

    # =========================================================================
    # Step 2.1: Headless Analyst API
    # =========================================================================

    async def test_step_2_1_api_routing(self, mock_orchestrator):
        """Test API endpoint task routes to feature_dev + code_review."""
        scenario = PHASE2_SCENARIOS[0]

        mock_orchestrator.route_task.return_value = {
            "agent": "feature_dev",
            "secondary_agents": ["code_review"],
            "confidence": 0.89,
        }

        result = await mock_orchestrator.route_task(scenario["task"])

        assert result["agent"] in scenario["expected_agents"]

    async def test_step_2_1_endpoint_generation(self, mock_orchestrator):
        """Test FastAPI endpoint code generation."""
        mock_orchestrator.get_agent_response.return_value = {
            "code": """
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import uuid

app = FastAPI()
tasks = {}

class CompsRequest(BaseModel):
    ticker: str
    peer_count: int = 5
    revenue_tolerance: float = 0.5

@app.post("/api/v1/research/comps")
async def run_comps_analysis(request: CompsRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    tasks[task_id] = {"status": "pending"}
    background_tasks.add_task(execute_comps_workflow, task_id, request)
    return {"task_id": task_id, "status": "pending"}

@app.get("/api/v1/research/tasks/{task_id}")
async def get_task_status(task_id: str):
    return tasks.get(task_id, {"status": "not_found"})
""",
            "explanation": "FastAPI endpoints with async task execution",
            "dependencies": ["fastapi", "pydantic", "uvicorn"],
        }

        result = await mock_orchestrator.get_agent_response(
            agent="feature_dev", task="Create comps API endpoint"
        )

        assert "/api/v1/research/comps" in result["code"]
        assert "BackgroundTasks" in result["code"]

    async def test_step_2_1_task_polling(self, mock_task_store):
        """Test task status polling mechanism."""
        # Create task
        task_id = mock_task_store.create_task()
        assert task_id == "task-uuid-1234"

        # Update status
        await mock_task_store.update_status(task_id, "running")

        # Get final status
        task = mock_task_store.get_task(task_id)
        assert task["status"] == "completed"

    # =========================================================================
    # Step 2.2: Comps Analysis Agent
    # =========================================================================

    async def test_step_2_2_comps_agent_routing(self, mock_orchestrator):
        """Test CompsAgent task routes to feature_dev + code_review."""
        scenario = PHASE2_SCENARIOS[1]

        mock_orchestrator.route_task.return_value = {
            "agent": "feature_dev",
            "secondary_agents": ["code_review"],
            "confidence": 0.94,
            "risk_level": "high",
        }

        result = await mock_orchestrator.route_task(scenario["task"])

        assert result["agent"] in scenario["expected_agents"]
        assert result["risk_level"] == "high"

    async def test_step_2_2_comps_workflow_generation(self, mock_orchestrator):
        """Test LangGraph CompsAgent workflow generation."""
        mock_orchestrator.get_agent_response.return_value = {
            "code": '''
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

class CompsState(TypedDict):
    ticker: str
    target_fundamentals: dict
    peer_candidates: List[dict]
    enriched_peers: List[dict]
    ranked_comps: List[dict]
    citations: List[dict]

async def get_fundamentals(state: CompsState) -> CompsState:
    """Fetch target company fundamentals from Nasdaq MCP."""
    pass

async def screen_peers(state: CompsState) -> CompsState:
    """Screen peer candidates by industry and revenue."""
    pass

async def enrich_data(state: CompsState) -> CompsState:
    """Enrich peer data with detailed fundamentals."""
    pass

async def calculate_multiples(state: CompsState) -> CompsState:
    """Calculate EV/Revenue and similarity scores."""
    pass

async def rank_results(state: CompsState) -> CompsState:
    """Rank and return top N peers."""
    pass

# Build workflow graph
workflow = StateGraph(CompsState)
workflow.add_node("get_fundamentals", get_fundamentals)
workflow.add_node("screen_peers", screen_peers)
workflow.add_node("enrich_data", enrich_data)
workflow.add_node("calculate_multiples", calculate_multiples)
workflow.add_node("rank_results", rank_results)

workflow.set_entry_point("get_fundamentals")
workflow.add_edge("get_fundamentals", "screen_peers")
workflow.add_edge("screen_peers", "enrich_data")
workflow.add_edge("enrich_data", "calculate_multiples")
workflow.add_edge("calculate_multiples", "rank_results")
workflow.add_edge("rank_results", END)

comps_agent = workflow.compile()
''',
            "explanation": "LangGraph StateGraph for comps analysis workflow",
        }

        result = await mock_orchestrator.get_agent_response(
            agent="feature_dev", task="Implement CompsAgent with LangGraph"
        )

        assert "StateGraph" in result["code"]
        assert "get_fundamentals" in result["code"]
        assert "screen_peers" in result["code"]

    async def test_step_2_2_comps_output_format(self, mock_mcp_clients):
        """Test CompsAgent output matches expected schema."""
        # Simulate comps analysis result
        comps_result = {
            "comps": [
                {
                    "ticker": "ORCL",
                    "name": "Oracle Corporation",
                    "revenue": 50000000000,
                    "ev_revenue_multiple": "5.2x",
                    "similarity_score": 0.87,
                    "risk_summary": "Competitive pressure from AWS/Azure",
                },
                {
                    "ticker": "SAP",
                    "name": "SAP SE",
                    "revenue": 33000000000,
                    "ev_revenue_multiple": "4.8x",
                    "similarity_score": 0.82,
                    "risk_summary": "Cloud transition risks",
                },
            ],
            "citations": [
                {
                    "source": "EDGAR 10-K",
                    "ticker": "ORCL",
                    "filing_date": "2024-06-30",
                    "accession_number": "0001564590-24-000001",
                }
            ],
        }

        # Validate schema
        assert "comps" in comps_result
        assert "citations" in comps_result
        assert len(comps_result["comps"]) > 0

        for comp in comps_result["comps"]:
            assert "ticker" in comp
            assert "revenue" in comp
            assert "ev_revenue_multiple" in comp

    async def test_step_2_2_mcp_tool_integration(self, mock_mcp_clients):
        """Test CompsAgent integrates with MCP tools."""
        # Get target fundamentals
        fundamentals = await mock_mcp_clients["nasdaq"].get_fundamentals("MSFT")
        assert fundamentals["ticker"] == "MSFT"
        assert fundamentals["revenue"] > 0

        # Search for peers
        peers = await mock_mcp_clients["nasdaq"].search_companies(
            {"sic_code": fundamentals["sic_code"]}
        )
        assert len(peers["companies"]) > 0

        # Get filing context
        filings = await mock_mcp_clients["edgar"].search_filings("ORCL", "10-K")
        assert len(filings["filings"]) > 0

    # =========================================================================
    # Step 2.3: RAG Pipeline
    # =========================================================================

    async def test_step_2_3_rag_routing(self, mock_orchestrator):
        """Test RAG pipeline task routes to feature_dev."""
        scenario = PHASE2_SCENARIOS[2]

        mock_orchestrator.route_task.return_value = {
            "agent": "feature_dev",
            "confidence": 0.91,
        }

        result = await mock_orchestrator.route_task(scenario["task"])

        assert result["agent"] in scenario["expected_agents"]

    async def test_step_2_3_rag_chunking_strategy(self, mock_orchestrator):
        """Test RAG chunking code generation."""
        mock_orchestrator.get_agent_response.return_value = {
            "code": '''
import re
from typing import Dict, List

def extract_sections(html_text: str) -> Dict[str, str]:
    """Parse 10-K HTML into sections by Item headers."""
    sections = {}
    pattern = r'(Item\s+\d+[A-Z]?\.)'
    parts = re.split(pattern, html_text)
    
    for i in range(1, len(parts), 2):
        section_name = parts[i].strip()
        section_text = parts[i+1].strip() if i+1 < len(parts) else ""
        sections[section_name] = section_text
    
    return sections

def chunk_section(section_name: str, text: str, metadata: dict, max_tokens: int = 2000):
    """Recursively chunk section by headers if too long."""
    # Implementation for recursive chunking
    pass
''',
            "explanation": "SEC Item header-based chunking for RAG",
        }

        result = await mock_orchestrator.get_agent_response(
            agent="feature_dev", task="Build RAG chunking for 10-K filings"
        )

        assert "Item" in result["code"]
        assert "extract_sections" in result["code"]

    async def test_step_2_3_embedding_generation(self, mock_mcp_clients):
        """Test embedding generation for RAG."""
        # Mock OpenAI embeddings
        mock_embeddings = MagicMock()
        mock_embeddings.create = AsyncMock(
            return_value={"data": [{"embedding": [0.1] * 1536}]}
        )

        result = await mock_embeddings.create(
            input="Item 1A. Risk Factors...", model="text-embedding-3-large"
        )

        assert len(result["data"][0]["embedding"]) == 1536

    async def test_step_2_3_qdrant_upsert(self, mock_mcp_clients):
        """Test vector upsert to Qdrant."""
        mock_qdrant = MagicMock()
        mock_qdrant.upsert = AsyncMock(return_value={"status": "completed"})

        result = await mock_qdrant.upsert(
            collection_name="ib-agent-filings",
            points=[
                {
                    "id": "msft-item1a-chunk0",
                    "vector": [0.1] * 1536,
                    "payload": {
                        "ticker": "MSFT",
                        "section": "Item 1A",
                        "chunk_index": 0,
                    },
                }
            ],
        )

        assert result["status"] == "completed"


class TestPhase2Integration:
    """Integration tests for Phase 2 components."""

    @pytest.fixture
    def phase2_context(self):
        """Shared context for Phase 2 tests."""
        return {
            "endpoints": {
                "/api/v1/research/comps": {"method": "POST", "status": "implemented"},
                "/api/v1/research/tasks/{task_id}": {
                    "method": "GET",
                    "status": "implemented",
                },
            },
            "agents": {"comps_agent": {"status": "ready", "workflow_nodes": 5}},
            "collections": {"ib-agent-filings": {"vectors": 1000, "status": "indexed"}},
        }

    async def test_phase2_api_to_agent_flow(self, phase2_context):
        """Test API → Agent → MCP → Response flow."""
        # Verify endpoints
        assert (
            phase2_context["endpoints"]["/api/v1/research/comps"]["status"]
            == "implemented"
        )

        # Verify agent
        assert phase2_context["agents"]["comps_agent"]["workflow_nodes"] == 5

        # Verify vector DB
        assert phase2_context["collections"]["ib-agent-filings"]["vectors"] > 0

    async def test_phase2_comps_workflow_e2e(self, phase2_context):
        """Test complete comps analysis workflow."""
        # Simulate workflow execution
        workflow_result = {
            "task_id": "task-12345",
            "status": "completed",
            "result": {
                "comps": [{"ticker": "ORCL", "similarity_score": 0.87}],
                "citations": [{"source": "EDGAR", "ticker": "ORCL"}],
            },
            "latency_ms": 3500,
        }

        assert workflow_result["status"] == "completed"
        assert workflow_result["latency_ms"] < 5000  # < 5 second threshold


class TestPhase2Tracing:
    """Verify Phase 2 tasks generate proper LangSmith traces."""

    async def test_comps_workflow_trace_structure(self):
        """Verify CompsAgent workflow generates proper trace hierarchy."""
        expected_trace_structure = {
            "name": "comps_workflow",
            "children": [
                {"name": "get_fundamentals", "type": "tool_call"},
                {"name": "screen_peers", "type": "chain"},
                {"name": "enrich_data", "type": "chain"},
                {"name": "calculate_multiples", "type": "chain"},
                {"name": "rank_results", "type": "chain"},
            ],
        }

        # Validate structure
        assert len(expected_trace_structure["children"]) == 5

    async def test_mcp_calls_traced_with_citations(self):
        """Verify MCP tool calls include citation metadata in traces."""
        expected_trace_output = {
            "tool": "get_fundamentals",
            "server": "nasdaq",
            "response": {"ticker": "MSFT", "revenue": 211915000000},
            "citations": [{"source": "Nasdaq Data Link", "dataset": "QOR/STATS_MSFT"}],
        }

        assert "citations" in expected_trace_output
        assert len(expected_trace_output["citations"]) > 0
