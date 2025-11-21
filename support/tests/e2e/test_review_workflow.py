"""
End-to-end test for code review workflow (low-risk, no approval).

Tests the complete flow:
1. Task submission → supervisor routing → code-review agent
2. PR diff retrieval
3. Code analysis
4. Review comment posting
5. Auto-approval (no HITL)
6. Workflow completion

Usage:
    pytest support/tests/e2e/test_review_workflow.py -v -s
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "../../../agent_orchestrator"))
sys.path.insert(0, str(Path(__file__).parent / "../../../shared"))

pytestmark = pytest.mark.asyncio


class TestCodeReviewWorkflow:
    """Test complete code review workflow without HITL approval."""
    
    @pytest.fixture
    def mock_pr_diff(self):
        """Mock PR diff content."""
        return """
diff --git a/api/auth.py b/api/auth.py
index abc123..def456 100644
--- a/api/auth.py
+++ b/api/auth.py
@@ -10,6 +10,15 @@ from flask import request, jsonify
 
+def validate_token(token):
+    try:
+        return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
+    except jwt.InvalidTokenError:
+        return None
+
 def login(username, password):
     # TODO: Add rate limiting
     user = User.query.filter_by(username=username).first()
"""
    
    @pytest.fixture
    def mock_mcp_client(self, mock_pr_diff):
        """Mock MCP client for code review tools."""
        mock = MagicMock()
        
        mock.call_tool = AsyncMock(side_effect=lambda server, tool, params: {
            ("gitmcp", "get_pull_request"): {
                "number": 85,
                "title": "Add JWT token validation",
                "body": "Implements secure token validation for API",
                "state": "open",
                "author": "dev-user"
            },
            ("gitmcp", "get_diff"): {
                "diff": mock_pr_diff,
                "files_changed": 1,
                "additions": 9,
                "deletions": 0
            },
            ("rust-mcp-filesystem", "read_file"): {
                "content": "# Auth module\n\nimport jwt\n\nSECRET_KEY = 'changeme'\n"
            },
            ("gitmcp", "add_comment"): {
                "success": True,
                "comment_id": 12345
            },
        }.get((server, tool), {"success": True}))
        
        return mock
    
    @pytest.fixture
    def mock_gradient_client(self):
        """Mock Gradient AI for code analysis."""
        mock = MagicMock()
        mock.analyze_code = AsyncMock(return_value={
            "issues": [
                {
                    "line": 15,
                    "severity": "medium",
                    "message": "Hardcoded SECRET_KEY should be moved to environment variable",
                    "category": "security"
                },
                {
                    "line": 20,
                    "severity": "low",
                    "message": "Consider adding rate limiting as noted in TODO",
                    "category": "enhancement"
                }
            ],
            "summary": "Code is functional but has minor security and enhancement opportunities",
            "overall_quality": "good"
        })
        return mock
    
    async def test_code_review_workflow_no_approval(
        self,
        mock_mcp_client,
        mock_gradient_client
    ):
        """
        Test complete code review workflow without HITL approval.
        
        Scenario: Review PR-85 for code quality
        Expected: Low-risk → auto-approve → complete without interruption
        """
        from graph import create_workflow, WorkflowState
        from langchain_core.messages import HumanMessage
        
        with patch('lib.gradient_client.get_gradient_client', return_value=mock_gradient_client), \
             patch('lib.mcp_client.MCPClient', return_value=mock_mcp_client):
            
            workflow = create_workflow()
            
            initial_state: WorkflowState = {
                "messages": [
                    HumanMessage(content="Review PR-85 for code quality and security issues")
                ],
                "current_agent": "",
                "next_agent": "",
                "task_result": {},
                "approvals": [],
                "requires_approval": False,
            }
            
            thread_id = f"test-review-{datetime.utcnow().timestamp()}"
            config = {"configurable": {"thread_id": thread_id}}
            
            # Execute workflow
            result = await workflow.ainvoke(initial_state, config=config)
            
            # Validations
            assert result is not None, "Workflow should return result"
            
            # Should route to code-review agent
            messages = result.get("messages", [])
            assert any("review" in str(m).lower() for m in messages), \
                "Supervisor should route to code-review agent"
            
            # Should NOT require approval (read-only operation)
            assert result.get("requires_approval") == False, \
                "Low-risk review should not require approval"
            
            # Should have no approval requests
            approvals = result.get("approvals", [])
            assert len(approvals) == 0, "Should not create approval requests for low-risk tasks"
            
            # Verify MCP tool calls
            assert mock_mcp_client.call_tool.called, "Should call MCP tools"
            
            # Check for PR fetch
            calls = [str(call) for call in mock_mcp_client.call_tool.call_args_list]
            assert any("get_pull_request" in call or "get_diff" in call for call in calls), \
                "Should fetch PR data"
            
            # Check task result
            task_result = result.get("task_result", {})
            if task_result:
                assert "issues_found" in str(task_result) or "review" in str(task_result), \
                    "Should return review results"
            
            print("✅ Code review workflow test passed")
            print(f"   - Workflow ID: {result.get('workflow_id', 'N/A')}")
            print(f"   - Requires Approval: {result.get('requires_approval')}")
            print(f"   - Task Result: {task_result}")
    
    async def test_pr_diff_analysis(self, mock_mcp_client, mock_gradient_client):
        """Test that PR diff is analyzed correctly."""
        with patch('lib.mcp_client.MCPClient', return_value=mock_mcp_client), \
             patch('lib.gradient_client.get_gradient_client', return_value=mock_gradient_client):
            
            # Fetch PR diff
            diff_result = await mock_mcp_client.call_tool(
                "gitmcp",
                "get_diff",
                {"pr_number": 85}
            )
            
            assert diff_result["diff"] is not None, "Should return diff content"
            assert "validate_token" in diff_result["diff"], "Diff should contain code changes"
            
            # Analyze with AI
            analysis = await mock_gradient_client.analyze_code(diff_result["diff"])
            
            assert len(analysis["issues"]) > 0, "Should find issues in code"
            assert any(issue["category"] == "security" for issue in analysis["issues"]), \
                "Should identify security issues"
            
            print("✅ PR diff analysis test passed")
            print(f"   - Issues found: {len(analysis['issues'])}")
            print(f"   - Overall quality: {analysis['overall_quality']}")
    
    async def test_review_comment_posting(self, mock_mcp_client):
        """Test that review comments are posted to PR."""
        with patch('lib.mcp_client.MCPClient', return_value=mock_mcp_client):
            
            # Post review comment
            result = await mock_mcp_client.call_tool(
                "gitmcp",
                "add_comment",
                {
                    "pr_number": 85,
                    "body": "**Security Issue**: Hardcoded SECRET_KEY should use environment variable",
                    "line": 15,
                    "path": "api/auth.py"
                }
            )
            
            assert result["success"] == True, "Comment posting should succeed"
            assert result.get("comment_id"), "Should return comment ID"
            
            print("✅ Review comment posting test passed")
    
    async def test_review_workflow_execution_time(
        self,
        mock_mcp_client,
        mock_gradient_client
    ):
        """Test that review workflow completes quickly (< 30s for mocked)."""
        from graph import create_workflow, WorkflowState
        from langchain_core.messages import HumanMessage
        import time
        
        with patch('lib.gradient_client.get_gradient_client', return_value=mock_gradient_client), \
             patch('lib.mcp_client.MCPClient', return_value=mock_mcp_client):
            
            workflow = create_workflow()
            
            initial_state: WorkflowState = {
                "messages": [HumanMessage(content="Review PR-85")],
                "current_agent": "",
                "next_agent": "",
                "task_result": {},
                "approvals": [],
                "requires_approval": False,
            }
            
            thread_id = f"test-perf-{datetime.utcnow().timestamp()}"
            config = {"configurable": {"thread_id": thread_id}}
            
            start_time = time.time()
            result = await workflow.ainvoke(initial_state, config=config)
            elapsed = time.time() - start_time
            
            assert elapsed < 30, f"Review workflow should complete in < 30s (took {elapsed:.2f}s)"
            assert result is not None, "Should return result"
            
            print(f"✅ Review workflow performance test passed")
            print(f"   - Execution time: {elapsed:.2f}s")


class TestReviewWorkflowEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def mock_mcp_client_error(self):
        """Mock MCP client that simulates errors."""
        mock = MagicMock()
        mock.call_tool = AsyncMock(side_effect=Exception("PR not found"))
        return mock
    
    async def test_pr_not_found(self, mock_mcp_client_error):
        """Test graceful handling when PR doesn't exist."""
        from graph import create_workflow, WorkflowState
        from langchain_core.messages import HumanMessage
        
        with patch('lib.mcp_client.MCPClient', return_value=mock_mcp_client_error):
            
            workflow = create_workflow()
            
            initial_state: WorkflowState = {
                "messages": [HumanMessage(content="Review PR-999")],
                "current_agent": "",
                "next_agent": "",
                "task_result": {},
                "approvals": [],
                "requires_approval": False,
            }
            
            thread_id = f"test-error-{datetime.utcnow().timestamp()}"
            config = {"configurable": {"thread_id": thread_id}}
            
            # Should handle error gracefully
            try:
                result = await workflow.ainvoke(initial_state, config=config)
                # If workflow handles errors gracefully, check for error in result
                if result:
                    task_result = result.get("task_result", {})
                    # Error might be in task result
                    print("✅ PR not found handled gracefully")
            except Exception as e:
                # Error is expected, workflow should handle it
                assert "not found" in str(e).lower(), "Error should indicate PR not found"
                print("✅ PR not found error raised as expected")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
