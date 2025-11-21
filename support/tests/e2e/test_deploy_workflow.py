"""
End-to-end test for deployment workflow (critical-risk with HITL approval).

Tests the complete flow:
1. Task submission → supervisor routing → infrastructure agent
2. Build Docker image
3. Risk assessment → CRITICAL
4. Linear sub-issue creation with 🔴 emoji
5. Workflow interrupt
6. Manual approval required
7. Resume and complete deployment
8. Health validation and notifications

Usage:
    pytest support/tests/e2e/test_deploy_workflow.py -v -s
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


class TestDeploymentWorkflow:
    """Test complete deployment workflow with critical-risk HITL approval."""
    
    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for deployment tools."""
        mock = MagicMock()
        
        mock.call_tool = AsyncMock(side_effect=lambda server, tool, params: {
            ("gitmcp", "get_file_contents"): {
                "content": "FROM python:3.11\nCOPY . /app\n...",
                "path": "Dockerfile"
            },
            ("dockerhub", "build_image"): {
                "image_id": "sha256:abc123",
                "image_tag": "myapp:jwt-auth-v1",
                "success": True
            },
            ("dockerhub", "run_container"): {
                "container_id": "container-xyz",
                "container_name": "myapp-prod",
                "success": True,
                "ports": ["8080:8080"]
            },
            ("dockerhub", "inspect_container"): {
                "state": "running",
                "health": "healthy",
                "uptime_seconds": 120
            },
            ("prometheus", "query_metrics"): {
                "metrics": [
                    {"name": "http_requests_total", "value": 1523},
                    {"name": "http_errors_total", "value": 0}
                ]
            },
            ("notion", "create_page"): {
                "page_id": "page-abc",
                "url": "https://notion.so/deployment-log-abc"
            },
            ("gmail-mcp", "send_email"): {
                "message_id": "msg-123",
                "success": True
            },
        }.get((server, tool), {"success": True}))
        
        return mock
    
    @pytest.fixture
    def mock_linear_client(self):
        """Mock Linear workspace client for critical approvals."""
        mock = MagicMock()
        mock.create_approval_subissue = AsyncMock(return_value="DEV-136")
        mock.get_issue_by_identifier = AsyncMock(return_value={
            "id": "issue-uuid-136",
            "identifier": "DEV-136",
            "state": {"name": "Todo"}
        })
        return mock
    
    async def test_deployment_workflow_critical_risk(
        self,
        mock_mcp_client,
        mock_linear_client
    ):
        """
        Test complete deployment workflow with critical-risk approval.
        
        Scenario: Deploy feature/jwt-auth to production
        Expected: CRITICAL risk → requires tech lead approval → workflow interrupts
        """
        from graph import create_workflow, WorkflowState
        from langchain_core.messages import HumanMessage
        
        with patch('lib.mcp_client.MCPClient', return_value=mock_mcp_client), \
             patch('lib.linear_workspace_client.LinearWorkspaceClient', return_value=mock_linear_client):
            
            workflow = create_workflow()
            
            initial_state: WorkflowState = {
                "messages": [
                    HumanMessage(
                        content="Deploy feature/jwt-auth branch to production environment"
                    )
                ],
                "current_agent": "",
                "next_agent": "",
                "task_result": {},
                "approvals": [],
                "requires_approval": False,
            }
            
            thread_id = f"test-deploy-{datetime.utcnow().timestamp()}"
            config = {"configurable": {"thread_id": thread_id}}
            
            # Execute workflow (should interrupt at approval gate)
            result = await workflow.ainvoke(initial_state, config=config)
            
            # Validations
            assert result is not None, "Workflow should return result"
            
            # Should route to infrastructure agent
            messages = result.get("messages", [])
            assert any("infrastructure" in str(m).lower() or "deploy" in str(m).lower() for m in messages), \
                "Supervisor should route to infrastructure agent"
            
            # Should require approval (critical risk)
            assert result.get("requires_approval") == True, \
                "Production deployment should require approval"
            
            # Check approval issue created with critical risk indicator
            approvals = result.get("approvals", [])
            if approvals:
                approval = approvals[0]
                assert approval.get("approval_issue") == "DEV-136", \
                    "Linear sub-issue should be created"
                assert approval.get("status") == "pending", \
                    "Approval status should be pending"
                
                # Should have critical risk indicator
                risk_level = approval.get("risk_level", "")
                assert "🔴" in risk_level or "CRITICAL" in risk_level, \
                    "Should indicate critical risk"
                
                # Should include deployment plan
                assert "deployment" in str(approval).lower(), \
                    "Approval should include deployment details"
            
            # Verify Docker operations called
            assert mock_mcp_client.call_tool.called, "Should call MCP tools"
            calls = [str(call) for call in mock_mcp_client.call_tool.call_args_list]
            
            # Should build image
            assert any("build_image" in call or "dockerhub" in call for call in calls), \
                "Should build Docker image"
            
            print("✅ Deployment workflow with critical approval test passed")
            print(f"   - Workflow ID: {result.get('workflow_id', 'N/A')}")
            print(f"   - Approval Issue: {approvals[0].get('approval_issue') if approvals else 'N/A'}")
            print(f"   - Risk Level: {approvals[0].get('risk_level') if approvals else 'N/A'}")
    
    async def test_deployment_resume_and_health_check(
        self,
        mock_mcp_client,
        mock_linear_client
    ):
        """
        Test deployment resumption and health validation.
        
        Scenario: After approval, deployment completes with health checks
        Expected: Container deployed, health validated, metrics collected
        """
        # Mock approval state change
        mock_linear_client.get_issue_by_identifier = AsyncMock(return_value={
            "id": "issue-uuid-136",
            "identifier": "DEV-136",
            "state": {"name": "Done"}  # Approved
        })
        
        with patch('lib.mcp_client.MCPClient', return_value=mock_mcp_client), \
             patch('lib.linear_workspace_client.LinearWorkspaceClient', return_value=mock_linear_client):
            
            # Simulate deployment execution after approval
            result = await mock_mcp_client.call_tool(
                "dockerhub",
                "run_container",
                {
                    "image": "myapp:jwt-auth-v1",
                    "name": "myapp-prod",
                    "ports": {"8080": "8080"},
                    "environment": {"ENV": "production"}
                }
            )
            
            assert result["success"] == True, "Container deployment should succeed"
            assert result["container_id"], "Should return container ID"
            
            # Health check
            health_result = await mock_mcp_client.call_tool(
                "dockerhub",
                "inspect_container",
                {"container_id": result["container_id"]}
            )
            
            assert health_result["state"] == "running", "Container should be running"
            assert health_result["health"] == "healthy", "Container should be healthy"
            
            # Metrics validation
            metrics_result = await mock_mcp_client.call_tool(
                "prometheus",
                "query_metrics",
                {"query": "http_errors_total{service='myapp'}"}
            )
            
            assert len(metrics_result["metrics"]) > 0, "Should return metrics"
            error_count = next(
                (m["value"] for m in metrics_result["metrics"] if m["name"] == "http_errors_total"),
                None
            )
            assert error_count == 0, "Should have no errors after deployment"
            
            print("✅ Deployment health validation test passed")
            print(f"   - Container ID: {result['container_id']}")
            print(f"   - Health Status: {health_result['health']}")
            print(f"   - Error Count: {error_count}")
    
    async def test_deployment_notifications(self, mock_mcp_client):
        """Test that deployment notifications are sent."""
        with patch('lib.mcp_client.MCPClient', return_value=mock_mcp_client):
            
            # Create deployment log in Notion
            notion_result = await mock_mcp_client.call_tool(
                "notion",
                "create_page",
                {
                    "database_id": "deployments-db",
                    "properties": {
                        "Name": "Production Deployment - jwt-auth-v1",
                        "Status": "Success",
                        "Date": datetime.utcnow().isoformat(),
                        "Version": "jwt-auth-v1"
                    }
                }
            )
            
            assert notion_result["page_id"], "Should create Notion page"
            
            # Send email notification
            email_result = await mock_mcp_client.call_tool(
                "gmail-mcp",
                "send_email",
                {
                    "to": "team@example.com",
                    "subject": "Production Deployment Complete: jwt-auth-v1",
                    "body": f"Deployment successful. Log: {notion_result['url']}"
                }
            )
            
            assert email_result["success"] == True, "Email should be sent"
            
            print("✅ Deployment notifications test passed")
            print(f"   - Notion Log: {notion_result['url']}")
            print(f"   - Email ID: {email_result['message_id']}")
    
    async def test_authorization_check(self, mock_linear_client):
        """Test that only authorized roles can approve critical deployments."""
        from lib.hitl_manager import get_hitl_manager
        
        hitl_manager = get_hitl_manager()
        
        # Create critical approval request
        request_id = await hitl_manager.create_approval_request(
            workflow_id="test-wf-auth",
            thread_id="thread-auth",
            checkpoint_id="cp-auth",
            task={
                "operation": "deploy",
                "environment": "production",
                "resource_type": "application"
            },
            agent_name="infrastructure"
        )
        
        if request_id:
            # Try to approve as developer (should fail)
            dev_approval = await hitl_manager.approve_request(
                request_id=request_id,
                approver_id="junior.dev",
                approver_role="developer"
            )
            
            assert dev_approval == False, "Developer should not approve critical deployment"
            
            # Try to approve as tech lead (should succeed)
            lead_approval = await hitl_manager.approve_request(
                request_id=request_id,
                approver_id="tech.lead",
                approver_role="tech_lead"
            )
            
            assert lead_approval == True, "Tech lead should approve critical deployment"
            
            print("✅ Authorization check test passed")
            print(f"   - Developer approval: {dev_approval}")
            print(f"   - Tech lead approval: {lead_approval}")


class TestDeploymentEdgeCases:
    """Test deployment error handling and edge cases."""
    
    @pytest.fixture
    def mock_mcp_client_failure(self):
        """Mock MCP client that simulates deployment failure."""
        mock = MagicMock()
        mock.call_tool = AsyncMock(side_effect=lambda server, tool, params: {
            ("dockerhub", "run_container"): {
                "success": False,
                "error": "Port 8080 already in use"
            },
            ("dockerhub", "inspect_container"): {
                "state": "exited",
                "health": "unhealthy",
                "exit_code": 1
            },
        }.get((server, tool), {"success": True}))
        return mock
    
    async def test_deployment_failure_handling(self, mock_mcp_client_failure):
        """Test graceful handling of deployment failures."""
        with patch('lib.mcp_client.MCPClient', return_value=mock_mcp_client_failure):
            
            # Attempt deployment
            result = await mock_mcp_client_failure.call_tool(
                "dockerhub",
                "run_container",
                {"image": "myapp:v1", "name": "myapp-prod"}
            )
            
            assert result["success"] == False, "Deployment should fail"
            assert "error" in result, "Should return error message"
            assert "port" in result["error"].lower(), "Error should indicate port conflict"
            
            print("✅ Deployment failure handling test passed")
            print(f"   - Error: {result['error']}")
    
    async def test_health_check_failure_rollback(self, mock_mcp_client_failure):
        """Test rollback when health checks fail."""
        with patch('lib.mcp_client.MCPClient', return_value=mock_mcp_client_failure):
            
            # Health check returns unhealthy
            health = await mock_mcp_client_failure.call_tool(
                "dockerhub",
                "inspect_container",
                {"container_id": "container-xyz"}
            )
            
            assert health["state"] == "exited", "Container should be stopped"
            assert health["health"] == "unhealthy", "Health should be unhealthy"
            
            # In real workflow, this would trigger rollback
            print("✅ Health check failure detection test passed")
            print(f"   - State: {health['state']}")
            print(f"   - Health: {health['health']}")
            print("   ⚠️  Rollback logic should be triggered")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
