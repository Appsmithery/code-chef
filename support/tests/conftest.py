"""
Shared pytest fixtures and configuration for Dev-Tools test suite.

This module provides:
- Reusable test fixtures for agents, clients, databases
- Mock configurations for LLM, MCP, Linear clients
- Database setup/teardown helpers
- Common test utilities

Usage:
    Fixtures are automatically discovered by pytest.
    Import in test files via: from conftest import fixture_name
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import asyncpg
import pytest

# Add shared and agent paths
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

sys.path.insert(0, str(REPO_ROOT / "shared"))
sys.path.insert(0, str(REPO_ROOT / "agent_orchestrator"))


# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers and environment."""
    # Add custom markers
    config.addinivalue_line("markers", "unit: Unit tests (fast, mocked)")
    config.addinivalue_line("markers", "integration: Integration tests (real services)")
    config.addinivalue_line("markers", "e2e: End-to-end workflow tests")
    config.addinivalue_line("markers", "performance: Performance and load tests")
    config.addinivalue_line("markers", "hitl: Human-in-the-loop approval tests")
    config.addinivalue_line("markers", "slow: Tests that take >10 seconds")
    config.addinivalue_line("markers", "asyncio: Async tests using pytest-asyncio")

    # Set environment variables for test tracing
    # This ensures all test traces are properly tagged and isolated
    os.environ["TRACE_ENVIRONMENT"] = "test"
    os.environ["EXPERIMENT_GROUP"] = "code-chef"
    os.environ["EXTENSION_VERSION"] = os.getenv("EXTENSION_VERSION", "test")

    # Use test-specific LangSmith project if available
    if not os.getenv("LANGSMITH_PROJECT"):
        os.environ["LANGSMITH_PROJECT"] = "code-chef-test"

    # IB-Agent Phase markers
    config.addinivalue_line("markers", "phase1: Phase 1 - Data Layer Foundation tests")
    config.addinivalue_line("markers", "phase2: Phase 2 - Core Agent Development tests")
    config.addinivalue_line("markers", "phase3: Phase 3 - UI Integration tests")
    config.addinivalue_line("markers", "phase4: Phase 4 - Excel Add-in tests")

    # LangSmith trace markers
    config.addinivalue_line("markers", "trace: Tests that generate LangSmith traces")
    config.addinivalue_line("markers", "mcp: MCP server integration tests")
    config.addinivalue_line("markers", "langgraph: LangGraph workflow tests")
    config.addinivalue_line("markers", "rag: RAG pipeline tests")
    config.addinivalue_line("markers", "infra: Infrastructure/Docker tests")
    config.addinivalue_line("markers", "api: FastAPI endpoint tests")


# ============================================================================
# LangSmith Configuration
# ============================================================================

# Check if LangSmith is available
try:
    from langsmith import Client as LangSmithClient

    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    LangSmithClient = None


@pytest.fixture(scope="session")
def langsmith_client():
    """Provide LangSmith client for trace evaluation tests."""
    if not LANGSMITH_AVAILABLE:
        pytest.skip("LangSmith SDK not installed")

    api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        pytest.skip("LANGCHAIN_API_KEY not set")

    return LangSmithClient()


@pytest.fixture
def langsmith_project():
    """Get current LangSmith project for test isolation."""
    return os.getenv("LANGCHAIN_PROJECT", "code-chef-testing")


@pytest.fixture
def langsmith_test_metadata(request):
    """Generate metadata for trace tagging based on test markers."""
    markers = [m.name for m in request.node.iter_markers()]
    return {
        "test_name": request.node.name,
        "test_file": request.node.fspath.basename,
        "markers": markers,
        "phase": next((m for m in markers if m.startswith("phase")), None),
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================================
# Hypothesis Configuration (Property-Based Testing)
# ============================================================================

from hypothesis import Verbosity, settings

# Register profiles for different test scenarios
settings.register_profile("ci", max_examples=20, verbosity=Verbosity.verbose)
settings.register_profile("dev", max_examples=100, verbosity=Verbosity.normal)
settings.register_profile("thorough", max_examples=500, verbosity=Verbosity.verbose)

# Default profile
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))


# ============================================================================
# Event Loop Configuration
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Mock Clients
# ============================================================================


@pytest.fixture
def mock_gradient_client():
    """Mock Gradient AI client for LLM testing."""
    mock = MagicMock()

    # Mock chat completion
    async def mock_chat(messages, **kwargs):
        return {
            "id": "chatcmpl-test",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Mock LLM response: Task decomposed successfully.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        }

    mock.chat = mock_chat
    mock.is_enabled = lambda: True

    return mock


@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for tool testing."""
    mock = MagicMock()

    # Mock tool call
    async def mock_call_tool(server: str, tool: str, arguments: dict):
        # Return server-specific mock responses
        if server == "rust-mcp-filesystem":
            if tool == "read_file":
                return {
                    "content": "// Mock file content\nfunction test() { return true; }"
                }
            elif tool == "write_file":
                return {"success": True, "bytes_written": 123}
            elif tool == "list_directory":
                return {"entries": ["file1.py", "file2.py", "folder1/"]}

        elif server == "gitmcp":
            if tool == "git_status":
                return {"branch": "feature/test", "changes": 5}
            elif tool == "git_diff":
                return {"diff": "+added line\n-removed line"}
            elif tool == "create_pr":
                return {
                    "pr_url": "https://github.com/test/repo/pull/123",
                    "pr_number": 123,
                }

        elif server == "dockerhub":
            if tool == "build":
                return {"image_id": "sha256:abc123", "success": True}
            elif tool == "run":
                return {"container_id": "container-xyz", "status": "running"}

        return {"success": True, "result": f"Mock result for {server}/{tool}"}

    # Mock server discovery
    async def mock_discover_servers():
        return [
            "rust-mcp-filesystem",
            "gitmcp",
            "dockerhub",
            "gmail-mcp",
            "notion",
            "hugging-face",
            "context7",
            "memory",
        ]

    # Mock tool enumeration
    async def mock_list_tools(server: str):
        tools_by_server = {
            "rust-mcp-filesystem": [
                "read_file",
                "write_file",
                "list_directory",
                "create_directory",
            ],
            "gitmcp": ["git_status", "git_diff", "git_commit", "create_pr", "git_push"],
            "dockerhub": ["build", "run", "stop", "logs", "exec"],
            "gmail-mcp": ["send_email", "read_email"],
            "notion": ["create_page", "update_page", "query_database"],
        }
        return tools_by_server.get(server, [])

    mock.call_tool = mock_call_tool
    mock.discover_servers = mock_discover_servers
    mock.list_tools = mock_list_tools

    return mock


@pytest.fixture
def mock_linear_client():
    """Mock Linear GraphQL client for HITL testing."""
    mock = MagicMock()

    # Mock GraphQL execution
    async def mock_execute(query: str, variables: dict = None):
        if "issueCreate" in query:
            issue_num = variables.get("title", "").split()[-1] if variables else "137"
            return {
                "issueCreate": {
                    "issue": {
                        "identifier": f"DEV-{issue_num}",
                        "id": f"issue-uuid-{issue_num}",
                        "title": variables.get("title", "Test Issue"),
                        "state": {"name": "Todo"},
                    }
                }
            }

        elif "issue(" in query:
            return {
                "issue": {
                    "identifier": "DEV-68",
                    "id": "4a4f7007-1a76-4b7f-af77-9723267b6d48",
                    "title": "HITL Approvals Hub",
                    "state": {"name": "In Progress"},
                }
            }

        return {}

    # Mock sub-issue creation
    async def mock_create_approval_subissue(
        approval_id: str,
        task_description: str,
        risk_level: str,
        project_name: str,
        agent_name: str,
        metadata: dict,
    ):
        risk_emojis = {"low": "🟢", "medium": "🟡", "high": "🟠", "critical": "🔴"}
        emoji = risk_emojis.get(risk_level, "⚪")
        return f"DEV-{hash(approval_id) % 1000}"

    mock.execute = mock_execute
    mock.create_approval_subissue = mock_create_approval_subissue

    return mock


# ============================================================================
# Database Fixtures
# ============================================================================


@pytest.fixture
async def db_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """Create PostgreSQL connection pool for testing."""
    db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/test_devtools",
    )

    pool = await asyncpg.create_pool(db_url, min_size=2, max_size=10)

    try:
        # Setup: Create test schema
        async with pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS langgraph_checkpoints (
                    thread_id TEXT NOT NULL,
                    checkpoint_id TEXT NOT NULL,
                    parent_checkpoint_id TEXT,
                    state JSONB NOT NULL,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    version INTEGER DEFAULT 1,
                    PRIMARY KEY (thread_id, checkpoint_id)
                )
            """
            )

        yield pool

    finally:
        # Teardown: Clean test data
        async with pool.acquire() as conn:
            await conn.execute("TRUNCATE TABLE langgraph_checkpoints CASCADE")

        await pool.close()


@pytest.fixture
async def clean_db(db_pool: asyncpg.Pool):
    """Clean database before each test."""
    async with db_pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE langgraph_checkpoints CASCADE")

    yield

    # Cleanup after test
    async with db_pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE langgraph_checkpoints CASCADE")


# ============================================================================
# HTTP Client Fixtures
# ============================================================================


@pytest.fixture
def orchestrator_url() -> str:
    """Orchestrator agent base URL."""
    return os.getenv("ORCHESTRATOR_URL", "http://localhost:8001")


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def secret_key() -> str:
    """HMAC secret key for event signatures."""
    return "test-secret-key-do-not-use-in-production"


@pytest.fixture
def sample_workflow_template():
    """Sample workflow template for testing."""
    return {
        "template_name": "test-workflow",
        "steps": [
            {
                "step_id": "code_review",
                "agent": "code_review",
                "depends_on": [],
                "max_retries": 3,
            },
            {
                "step_id": "deploy",
                "agent": "infrastructure",
                "depends_on": ["code_review"],
                "max_retries": 2,
            },
            {
                "step_id": "verify",
                "agent": "infrastructure",
                "depends_on": ["deploy"],
                "max_retries": 1,
            },
        ],
    }


@pytest.fixture
def sample_workflow_context():
    """Sample workflow context for testing."""
    return {
        "pr_number": 123,
        "repo": "test-repo",
        "branch": "feature/test",
        "author": "test@example.com",
    }


@pytest.fixture
def sample_task_request():
    """Sample task request payload."""
    return {
        "task": "Implement JWT authentication middleware",
        "priority": "high",
        "deadline": "2025-11-30",
        "context": {
            "repo": "github.com/test/repo",
            "branch": "feature/jwt-auth",
            "language": "Python",
        },
    }


@pytest.fixture
def sample_approval_request():
    """Sample approval request payload."""
    return {
        "approval_id": "test-approval-1",
        "task_description": "Deploy authentication changes to production",
        "risk_level": "high",
        "requested_by": "agent_infrastructure",
        "metadata": {
            "pr_number": 123,
            "services_affected": ["auth-service", "api-gateway"],
            "estimated_downtime": "5 minutes",
        },
    }


@pytest.fixture
def sample_workflow_state():
    """Sample LangGraph workflow state."""
    return {
        "messages": ["Implement feature X"],
        "agents": ["supervisor", "feature-dev"],
        "results": {
            "supervisor": {
                "routing_decision": "feature-dev",
                "timestamp": datetime.utcnow().isoformat(),
            }
        },
        "approvals": [],
    }


# ============================================================================
# Environment Utilities
# ============================================================================


@pytest.fixture
def skip_if_no_api_keys():
    """Skip test if required API keys are missing."""
    required_keys = ["GRADIENT_API_KEY", "LINEAR_API_KEY", "LANGSMITH_API_KEY"]
    missing = [key for key in required_keys if not os.getenv(key)]

    if missing:
        pytest.skip(f"Missing API keys: {', '.join(missing)}")


@pytest.fixture
def skip_if_services_unavailable():
    """Skip test if required services are unavailable."""
    import httpx

    services = {
        "MCP Gateway": "http://localhost:8000/health",
        "Orchestrator": "http://localhost:8001/health",
        "PostgreSQL": "postgresql://localhost:5432",
        "Qdrant": "http://localhost:6333/health",
    }

    unavailable = []
    for name, url in services.items():
        if url.startswith("http"):
            try:
                response = httpx.get(url, timeout=2.0)
                if response.status_code != 200:
                    unavailable.append(name)
            except Exception:
                unavailable.append(name)

    if unavailable:
        pytest.skip(f"Services unavailable: {', '.join(unavailable)}")


# ============================================================================
# Cleanup Utilities
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_artifacts():
    """Clean up test artifacts after test session."""
    yield

    # Cleanup logic runs after all tests
    test_dirs = [
        Path(__file__).parent / "__pycache__",
        Path(__file__).parent / ".pytest_cache",
    ]

    for dir_path in test_dirs:
        if dir_path.exists():
            import shutil

            shutil.rmtree(dir_path, ignore_errors=True)
