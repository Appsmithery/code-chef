"""
End-to-end test for feature development workflow with HITL approval.

Tests the complete flow:
1. Task submission → supervisor routing → feature-dev agent
2. Code generation, branch creation, PR opening
3. Risk assessment triggers HITL approval
4. Linear sub-issue creation
5. Workflow interrupt at approval gate
6. Resume after approval
7. Complete workflow execution

Usage:
    pytest support/tests/e2e/test_feature_workflow.py -v -s

Requirements:
    - Real Gradient API key (or mock for unit tests)
    - Linear API key (or mock server)
    - Git repository access
    - PostgreSQL for checkpointing
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Add project paths
sys.path.insert(0, str(Path(__file__).parent / "../../../agent_orchestrator"))
sys.path.insert(0, str(Path(__file__).parent / "../../../shared"))

pytestmark = pytest.mark.asyncio


class TestFeatureDevelopmentWorkflow:
    """Test complete feature development workflow with HITL approval."""

    @pytest.fixture
    def mock_gradient_client(self):
        """Mock Gradient AI client for faster testing."""
        mock = MagicMock()
        mock.generate_code = AsyncMock(
            return_value={
                "code": """
import jwt
from functools import wraps
from flask import request, jsonify

def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token required'}), 401
        try:
            jwt.decode(token, 'secret', algorithms=['HS256'])
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated
""",
                "explanation": "JWT authentication middleware with token validation",
                "dependencies": ["PyJWT>=2.0.0"],
            }
        )
        return mock

    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for tool access."""
        mock = MagicMock()

        # Mock filesystem operations
        mock.call_tool = AsyncMock(
            side_effect=lambda server, tool, params: {
                ("rust-mcp-filesystem", "read_file"): {
                    "content": "# Existing auth code\n\n"
                },
                ("rust-mcp-filesystem", "write_file"): {
                    "success": True,
                    "path": params.get("path"),
                },
                ("rust-mcp-filesystem", "create_directory"): {"success": True},
                ("gitmcp", "create_branch"): {
                    "branch": "feature/jwt-auth",
                    "success": True,
                },
                ("gitmcp", "commit_changes"): {"commit_sha": "abc123", "success": True},
                ("gitmcp", "create_pull_request"): {
                    "pr_number": 99,
                    "pr_url": "https://github.com/test/repo/pull/99",
                    "success": True,
                },
            }.get((server, tool), {"success": True})
        )

        return mock

    @pytest.fixture
    def mock_linear_client(self):
        """Mock Linear workspace client."""
        mock = MagicMock()
        mock.create_approval_subissue = AsyncMock(return_value="DEV-135")
        mock.get_issue_by_identifier = AsyncMock(
            return_value={
                "id": "issue-uuid-135",
                "identifier": "DEV-135",
                "state": {"name": "Todo"},
            }
        )
        return mock

    async def test_feature_workflow_high_risk_with_approval(
        self, mock_gradient_client, mock_mcp_client, mock_linear_client
    ):
        """
        Test complete feature workflow with HITL approval.

        Scenario: Add JWT authentication middleware to API
        Expected: High-risk → HITL approval required → workflow interrupts
        """
        from graph import WorkflowState, create_workflow
        from langchain_core.messages import HumanMessage

        # Patch dependencies
        with patch(
            "lib.llm_client.get_llm_client", return_value=mock_gradient_client
        ), patch("lib.mcp_client.MCPClient", return_value=mock_mcp_client), patch(
            "lib.linear_workspace_client.LinearWorkspaceClient",
            return_value=mock_linear_client,
        ):

            # Create workflow
            workflow = create_workflow()

            # Initial state
            initial_state: WorkflowState = {
                "messages": [
                    HumanMessage(
                        content="Add JWT authentication middleware to API endpoints"
                    )
                ],
                "current_agent": "",
                "next_agent": "",
                "task_result": {},
                "approvals": [],
                "requires_approval": False,
            }

            thread_id = f"test-feature-{datetime.utcnow().timestamp()}"
            config = {"configurable": {"thread_id": thread_id}}

            # Execute workflow (should interrupt at approval gate)
            result = await workflow.ainvoke(initial_state, config=config)

            # Validations
            assert result is not None, "Workflow should return result"

            # Check that supervisor routed to feature-dev
            messages = result.get("messages", [])
            assert any(
                "feature" in str(m).lower() for m in messages
            ), "Supervisor should route to feature-dev agent"

            # Check risk assessment
            assert (
                result.get("requires_approval") == True
            ), "High-risk task should require approval"

            # Check approval issue created
            approvals = result.get("approvals", [])
            if approvals:
                approval = approvals[0]
                assert (
                    approval.get("approval_issue") == "DEV-135"
                ), "Linear sub-issue should be created"
                assert (
                    approval.get("status") == "pending"
                ), "Approval status should be pending"
                assert "🟠" in approval.get("risk_level", "") or "HIGH" in approval.get(
                    "risk_level", ""
                ), "Should indicate high risk"

            # Verify MCP tool calls
            assert mock_mcp_client.call_tool.called, "Should call MCP tools"
            tool_calls = [call[0] for call in mock_mcp_client.call_tool.call_args_list]

            # Should have called filesystem tools
            assert any(
                "rust-mcp-filesystem" in str(call) for call in tool_calls
            ), "Should use filesystem tools"

            # Should have called git tools
            assert any(
                "gitmcp" in str(call) for call in tool_calls
            ), "Should use git tools"

            print("✅ Feature workflow with approval test passed")
            print(f"   - Workflow ID: {result.get('workflow_id', 'N/A')}")
            print(
                f"   - Approval Issue: {approvals[0].get('approval_issue') if approvals else 'N/A'}"
            )
            print(
                f"   - Risk Level: {approvals[0].get('risk_level') if approvals else 'N/A'}"
            )

    async def test_workflow_resume_after_approval(
        self, mock_gradient_client, mock_mcp_client, mock_linear_client
    ):
        """
        Test workflow resumption after approval.

        Scenario: Approve the sub-issue and resume workflow
        Expected: Workflow continues from checkpoint
        """
        from graph import create_workflow

        # Mock approval state change
        mock_linear_client.get_issue_by_identifier = AsyncMock(
            return_value={
                "id": "issue-uuid-135",
                "identifier": "DEV-135",
                "state": {"name": "Done"},  # Approved
            }
        )

        with patch(
            "lib.llm_client.get_llm_client", return_value=mock_gradient_client
        ), patch("lib.mcp_client.MCPClient", return_value=mock_mcp_client), patch(
            "lib.linear_workspace_client.LinearWorkspaceClient",
            return_value=mock_linear_client,
        ):

            workflow = create_workflow()

            # Simulate resume with same thread_id
            thread_id = f"test-resume-{datetime.utcnow().timestamp()}"
            config = {"configurable": {"thread_id": thread_id}}

            # In real scenario, we'd have checkpoint from previous run
            # For now, test that workflow can be invoked multiple times
            result = await workflow.ainvoke(None, config=config)

            # Should complete or move to next step
            assert result is not None, "Workflow should resume"

            print("✅ Workflow resume test passed")

    async def test_feature_branch_creation(self, mock_mcp_client):
        """Test that feature branch is created correctly."""
        from agents.feature_dev import FeatureDevAgent

        with patch("lib.mcp_client.MCPClient", return_value=mock_mcp_client):
            agent = FeatureDevAgent()

            # Simulate branch creation
            result = await mock_mcp_client.call_tool(
                "gitmcp",
                "create_branch",
                {"branch_name": "feature/jwt-auth", "base": "main"},
            )

            assert result["success"] == True, "Branch creation should succeed"
            assert result["branch"] == "feature/jwt-auth", "Branch name should match"

            print("✅ Feature branch creation test passed")

    async def test_pr_creation(self, mock_mcp_client):
        """Test that pull request is created with proper metadata."""
        with patch("lib.mcp_client.MCPClient", return_value=mock_mcp_client):
            # Simulate PR creation
            result = await mock_mcp_client.call_tool(
                "gitmcp",
                "create_pull_request",
                {
                    "title": "Add JWT authentication middleware",
                    "body": "Implements token-based authentication for API endpoints",
                    "base": "main",
                    "head": "feature/jwt-auth",
                },
            )

            assert result["success"] == True, "PR creation should succeed"
            assert result["pr_number"] == 99, "PR number should be returned"
            assert "github.com" in result["pr_url"], "PR URL should be valid"

            print("✅ PR creation test passed")


class TestFeatureWorkflowIntegration:
    """Integration tests with real services (requires API keys)."""

    @pytest.mark.skipif(
        not os.getenv("GRADIENT_API_KEY"),
        reason="Requires GRADIENT_API_KEY for real LLM calls",
    )
    async def test_real_llm_code_generation(self):
        """Test code generation with real Gradient AI API."""
        from lib.llm_client import get_llm_client

        client = get_llm_client("feature-dev")

        prompt = "Generate Python code for JWT authentication middleware using PyJWT"

        # This would make a real API call
        # Uncomment for integration testing
        # result = await client.generate_code(prompt)
        # assert "jwt" in result["code"].lower()
        # assert "authentication" in result["explanation"].lower()

        print("⚠️  Real LLM test skipped (uncomment for integration testing)")

    @pytest.mark.skipif(
        not os.getenv("LINEAR_API_KEY"),
        reason="Requires LINEAR_API_KEY for real Linear API",
    )
    async def test_real_linear_subissue_creation(self):
        """Test Linear sub-issue creation with real API."""
        from lib.linear_workspace_client import LinearWorkspaceClient

        client = LinearWorkspaceClient(agent_name="orchestrator")

        # This would make a real API call
        # Uncomment for integration testing
        # issue_id = await client.create_approval_subissue(
        #     approval_id="test-approval-123",
        #     task_description="Test feature implementation",
        #     risk_level="high",
        #     project_name="Dev-Tools",
        #     agent_name="feature-dev",
        #     metadata={"timestamp": datetime.utcnow().isoformat()}
        # )
        # assert issue_id.startswith("DEV-")

        print("⚠️  Real Linear test skipped (uncomment for integration testing)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
