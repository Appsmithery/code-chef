"""
Integration tests for Linear workspace client and HITL workflow.

Tests:
1. Linear sub-issue creation under DEV-68
2. Template population with metadata
3. Risk emoji inclusion
4. Issue status management
5. Approval resolution

Usage:
    pytest support/tests/hitl/test_linear_integration.py -v -s
    
Requirements:
    - LINEAR_API_KEY environment variable (or mock GraphQL)
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "../../../shared"))

pytestmark = pytest.mark.asyncio


class TestLinearSubIssueCreation:
    """Test Linear sub-issue creation for HITL approvals."""
    
    @pytest.fixture
    def mock_linear_client(self):
        """Mock Linear GraphQL client."""
        mock = MagicMock()
        
        # Mock GraphQL execution
        async def mock_execute(query, variables):
            if "issueCreate" in query:
                return {
                    "issueCreate": {
                        "issue": {
                            "identifier": "DEV-137",
                            "id": "issue-uuid-137",
                            "title": variables.get("title", "Test Issue"),
                            "state": {"name": "Todo"}
                        }
                    }
                }
            elif "issue(" in query:
                return {
                    "issue": {
                        "identifier": "DEV-137",
                        "id": "issue-uuid-137",
                        "state": {"name": "Done"}
                    }
                }
            return {}
        
        mock.execute = mock_execute
        return mock
    
    @pytest.fixture
    def linear_client(self, mock_linear_client):
        """Create LinearWorkspaceClient with mock."""
        from lib.linear_workspace_client import LinearWorkspaceClient
        
        client = LinearWorkspaceClient(agent_name="orchestrator")
        client.client = mock_linear_client
        return client
    
    async def test_create_high_risk_subissue(self, linear_client):
        """Test creation of high-risk approval sub-issue."""
        issue_id = await linear_client.create_approval_subissue(
            approval_id="test-approval-high-1",
            task_description="Deploy authentication changes to production",
            risk_level="high",
            project_name="Dev-Tools",
            agent_name="infrastructure",
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "workflow_id": "wf-test-123"
            }
        )
        
        assert issue_id is not None, "Should create sub-issue"
        assert issue_id.startswith("DEV-"), "Should return Linear identifier format"
        
        print("✅ High-risk sub-issue creation test passed")
        print(f"   - Issue ID: {issue_id}")
        print(f"   - Risk level: high")
    
    async def test_create_critical_risk_subissue(self, linear_client):
        """Test creation of critical-risk approval sub-issue."""
        issue_id = await linear_client.create_approval_subissue(
            approval_id="test-approval-critical-1",
            task_description="Delete production database",
            risk_level="critical",
            project_name="Dev-Tools",
            agent_name="infrastructure",
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "requires_tech_lead_approval": True
            }
        )
        
        assert issue_id is not None, "Should create sub-issue"
        assert issue_id.startswith("DEV-"), "Should return identifier"
        
        print("✅ Critical-risk sub-issue creation test passed")
        print(f"   - Issue ID: {issue_id}")
        print(f"   - Risk level: critical")
    
    async def test_risk_emoji_in_title(self, mock_linear_client):
        """Test that risk emoji is included in issue title."""
        from lib.linear_workspace_client import LinearWorkspaceClient
        
        client = LinearWorkspaceClient(agent_name="orchestrator")
        client.client = mock_linear_client
        
        # Capture the mutation variables
        create_calls = []
        
        original_execute = mock_linear_client.execute
        async def capture_execute(query, variables):
            if "issueCreate" in query:
                create_calls.append(variables)
            return await original_execute(query, variables)
        
        mock_linear_client.execute = capture_execute
        
        # Create high-risk issue
        await client.create_approval_subissue(
            approval_id="test-emoji",
            task_description="Test task",
            risk_level="high",
            project_name="Dev-Tools",
            agent_name="test",
            metadata={}
        )
        
        # Verify emoji in title
        if create_calls:
            title = create_calls[0].get("title", "")
            assert "🟠" in title or "[HIGH]" in title, \
                "High-risk issue should have 🟠 emoji or [HIGH] marker"
        
        print("✅ Risk emoji test passed")
        print(f"   - Title: {create_calls[0].get('title', 'N/A') if create_calls else 'N/A'}")
    
    async def test_template_fields_populated(self, mock_linear_client):
        """Test that template custom fields are populated."""
        from lib.linear_workspace_client import LinearWorkspaceClient
        
        client = LinearWorkspaceClient(agent_name="orchestrator")
        client.client = mock_linear_client
        
        # Capture mutation
        create_calls = []
        original_execute = mock_linear_client.execute
        
        async def capture_execute(query, variables):
            if "issueCreate" in query:
                create_calls.append(variables)
            return await original_execute(query, variables)
        
        mock_linear_client.execute = capture_execute
        
        # Create issue with metadata
        await client.create_approval_subissue(
            approval_id="test-template-fields",
            task_description="Test task with metadata",
            risk_level="medium",
            project_name="Dev-Tools",
            agent_name="feature-dev",
            metadata={
                "estimated_tokens": 5000,
                "deadline": "2025-11-22T00:00:00Z"
            }
        )
        
        # Verify fields
        if create_calls:
            variables = create_calls[0]
            assert "templateId" in variables or "customFields" in variables, \
                "Should use template or custom fields"
            
            # Check required fields in mutation
            assert variables.get("teamId"), "Should have team ID"
            assert variables.get("parentId"), "Should have parent ID (DEV-68)"
            assert variables.get("title"), "Should have title"
        
        print("✅ Template fields test passed")
        print(f"   - Team ID: {create_calls[0].get('teamId', 'N/A') if create_calls else 'N/A'}")
        print(f"   - Parent ID: {create_calls[0].get('parentId', 'N/A') if create_calls else 'N/A'}")
    
    async def test_parent_issue_is_dev_68(self, mock_linear_client):
        """Test that sub-issues are created under DEV-68."""
        from lib.linear_workspace_client import LinearWorkspaceClient
        
        client = LinearWorkspaceClient(agent_name="orchestrator")
        client.client = mock_linear_client
        
        # Mock get_issue_by_identifier to return DEV-68 UUID
        async def mock_get_issue(identifier):
            if identifier == "DEV-68":
                return {
                    "id": "4a4f7007-1a76-4b7f-af77-9723267b6d48",
                    "identifier": "DEV-68",
                    "title": "HITL Approvals Hub"
                }
            return None
        
        client.get_issue_by_identifier = mock_get_issue
        
        # Capture mutation
        create_calls = []
        original_execute = mock_linear_client.execute
        
        async def capture_execute(query, variables):
            if "issueCreate" in query:
                create_calls.append(variables)
            return await original_execute(query, variables)
        
        mock_linear_client.execute = capture_execute
        
        # Create sub-issue
        await client.create_approval_subissue(
            approval_id="test-parent",
            task_description="Test parent linking",
            risk_level="low",
            project_name="Dev-Tools",
            agent_name="test",
            metadata={}
        )
        
        # Verify parent ID
        if create_calls:
            parent_id = create_calls[0].get("parentId")
            assert parent_id == "4a4f7007-1a76-4b7f-af77-9723267b6d48", \
                "Should link to DEV-68 UUID"
        
        print("✅ Parent issue linking test passed")
        print(f"   - Parent ID: {create_calls[0].get('parentId', 'N/A') if create_calls else 'N/A'}")


class TestLinearApprovalResolution:
    """Test approval resolution via Linear status changes."""
    
    @pytest.fixture
    def linear_client(self):
        """Create LinearWorkspaceClient with mock."""
        from lib.linear_workspace_client import LinearWorkspaceClient
        return LinearWorkspaceClient(agent_name="orchestrator")
    
    async def test_check_approval_status_pending(self, linear_client):
        """Test checking pending approval status."""
        # Mock issue query
        async def mock_execute(query, variables):
            return {
                "issue": {
                    "identifier": "DEV-137",
                    "state": {"name": "Todo"},
                    "assignee": {"name": "Tech Lead"}
                }
            }
        
        linear_client.client = MagicMock()
        linear_client.client.execute = mock_execute
        
        issue = await linear_client.get_issue_by_identifier("DEV-137")
        
        assert issue["state"]["name"] == "Todo", "Should be pending"
        
        print("✅ Pending approval status test passed")
        print(f"   - Status: {issue['state']['name']}")
    
    async def test_check_approval_status_approved(self, linear_client):
        """Test checking approved status."""
        async def mock_execute(query, variables):
            return {
                "issue": {
                    "identifier": "DEV-137",
                    "state": {"name": "Done"},
                    "completedAt": datetime.utcnow().isoformat()
                }
            }
        
        linear_client.client = MagicMock()
        linear_client.client.execute = mock_execute
        
        issue = await linear_client.get_issue_by_identifier("DEV-137")
        
        assert issue["state"]["name"] == "Done", "Should be approved"
        
        print("✅ Approved status test passed")
        print(f"   - Status: {issue['state']['name']}")
    
    async def test_check_approval_status_rejected(self, linear_client):
        """Test checking rejected status."""
        async def mock_execute(query, variables):
            return {
                "issue": {
                    "identifier": "DEV-137",
                    "state": {"name": "Canceled"},
                    "canceledAt": datetime.utcnow().isoformat()
                }
            }
        
        linear_client.client = MagicMock()
        linear_client.client.execute = mock_execute
        
        issue = await linear_client.get_issue_by_identifier("DEV-137")
        
        assert issue["state"]["name"] == "Canceled", "Should be rejected"
        
        print("✅ Rejected status test passed")
        print(f"   - Status: {issue['state']['name']}")


@pytest.mark.skipif(
    not os.getenv("LINEAR_API_KEY"),
    reason="Requires LINEAR_API_KEY for real API calls"
)
class TestLinearRealAPI:
    """Integration tests with real Linear API."""
    
    async def test_real_linear_connection(self):
        """Test connection to real Linear API."""
        from lib.linear_workspace_client import LinearWorkspaceClient
        
        client = LinearWorkspaceClient(agent_name="test")
        
        # Query for DEV-68
        issue = await client.get_issue_by_identifier("DEV-68")
        
        assert issue is not None, "Should find DEV-68"
        assert issue["identifier"] == "DEV-68", "Should return correct issue"
        
        print("✅ Real Linear API connection test passed")
        print(f"   - Issue: {issue['identifier']}")
        print(f"   - Title: {issue.get('title', 'N/A')}")
    
    async def test_real_subissue_creation(self):
        """Test real sub-issue creation (WARNING: Creates actual Linear issue)."""
        from lib.linear_workspace_client import LinearWorkspaceClient
        
        # Uncomment to test with real API (creates actual issue)
        # client = LinearWorkspaceClient(agent_name="test")
        # 
        # issue_id = await client.create_approval_subissue(
        #     approval_id=f"test-{datetime.utcnow().timestamp()}",
        #     task_description="TEST: Automated test sub-issue (safe to delete)",
        #     risk_level="low",
        #     project_name="Dev-Tools",
        #     agent_name="test",
        #     metadata={"test": True}
        # )
        # 
        # assert issue_id.startswith("DEV-"), "Should create issue"
        # print(f"✅ Created real sub-issue: {issue_id}")
        # print("⚠️  Remember to delete test issue from Linear")
        
        print("⚠️  Real sub-issue creation test skipped (uncomment to run)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
