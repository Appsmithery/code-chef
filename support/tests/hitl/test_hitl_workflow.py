"""
Test suite for Human-in-the-Loop (HITL) approval workflow system.

Tests:
- Risk assessment accuracy
- Approval policy enforcement
- Database persistence
- LangGraph interrupt/resume flow
- Timeout/expiration handling
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict

# Configure pytest-anyio to use only asyncio backend
pytest_plugins = ('pytest_anyio',)
pytestmark = pytest.mark.anyio(backend='asyncio')

# Add shared lib to path
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'shared')))

from lib.risk_assessor import get_risk_assessor, RiskLevel
from lib.hitl_manager import get_hitl_manager


class TestRiskAssessor:
    """Test risk assessment logic"""
    
    def setup_method(self):
        self.assessor = get_risk_assessor()
    
    def test_critical_production_delete(self):
        """Production delete operations should be critical risk"""
        task = {
            "operation": "delete",
            "environment": "production",
            "resource_type": "database",
            "description": "Delete user_sessions table"
        }
        
        risk = self.assessor.assess_task(task)
        assert risk == "critical", "Production deletes must be critical risk"
    
    def test_low_dev_read(self):
        """Dev environment read operations should be low risk"""
        task = {
            "operation": "read",
            "environment": "dev",
            "resource_type": "file",
            "description": "Read configuration file"
        }
        
        risk = self.assessor.assess_task(task)
        assert risk == "low", "Dev reads should be low risk"
    
    def test_high_security_findings(self):
        """Tasks with high severity security findings should be high risk"""
        task = {
            "operation": "deploy",
            "environment": "staging",
            "resource_type": "application",
            "security_findings": [
                {"severity": "high", "description": "SQL injection vulnerability"}
            ]
        }
        
        risk = self.assessor.assess_task(task)
        assert risk == "high", "High security findings elevate risk"
    
    def test_critical_sensitive_data_export(self):
        """Sensitive data exports should be critical"""
        task = {
            "operation": "export",
            "environment": "production",
            "resource_type": "data",
            "data_sensitive": True,
            "description": "Export customer PII"
        }
        
        risk = self.assessor.assess_task(task)
        assert risk == "critical", "Sensitive data operations are critical"
    
    def test_auto_approve_low_risk(self):
        """Low risk tasks should auto-approve"""
        assert self.assessor.requires_approval("low") == False
        assert self.assessor.requires_approval("medium") == True
    
    def test_timeout_scaling(self):
        """Timeout should increase with risk level"""
        low_timeout = self.assessor.get_timeout_minutes("low")
        medium_timeout = self.assessor.get_timeout_minutes("medium")
        critical_timeout = self.assessor.get_timeout_minutes("critical")
        
        assert low_timeout < medium_timeout < critical_timeout


class TestHITLManager:
    """Test approval request management"""
    
    @pytest.fixture
    def manager(self):
        """Provide HITLManager instance"""
        return get_hitl_manager()
    
    @pytest.mark.anyio
    async def test_create_approval_request(self, manager):
        """Create approval request for high-risk operation"""
        task = {
            "operation": "deploy",
            "environment": "production",
            "resource_type": "application",
            "description": "Deploy JWT authentication to production",
            "estimated_cost": 50,
            "security_findings": []
        }
        
        request_id = await manager.create_approval_request(
            workflow_id="test-workflow-123",
            thread_id="thread-abc",
            checkpoint_id="checkpoint-xyz",
            task=task,
            agent_name="feature-dev"
        )
        
        assert request_id is not None, "High-risk task should create approval request"
        
        # Check status
        status = await manager.check_approval_status(request_id)
        assert status["status"] == "pending"
    
    @pytest.mark.anyio
    async def test_auto_approve_low_risk(self, manager):
        """Low risk tasks should not create approval requests"""
        task = {
            "operation": "read",
            "environment": "dev",
            "resource_type": "file",
            "description": "Read config file"
        }
        
        request_id = await manager.create_approval_request(
            workflow_id="test-workflow-456",
            thread_id="thread-def",
            checkpoint_id="checkpoint-uvw",
            task=task,
            agent_name="feature-dev"
        )
        
        assert request_id is None, "Low risk task should auto-approve (no request created)"
    
    @pytest.mark.anyio
    async def test_approve_request(self, manager):
        """Approve a pending request"""
        # Create request
        task = {
            "operation": "deploy",
            "environment": "staging",
            "resource_type": "application",
            "description": "Deploy to staging"
        }
        
        request_id = await manager.create_approval_request(
            workflow_id="test-workflow-789",
            thread_id="thread-ghi",
            checkpoint_id="checkpoint-rst",
            task=task,
            agent_name="cicd"
        )
        
        # Approve
        success = await manager.approve_request(
            request_id=request_id,
            approver_id="john.doe",
            approver_role="tech_lead",
            justification="Reviewed deployment plan"
        )
        
        assert success == True, "Approval should succeed"
        
        # Check status
        status = await manager.check_approval_status(request_id)
        assert status["status"] == "approved"
        assert status["approver_id"] == "john.doe"
    
    @pytest.mark.anyio
    async def test_reject_request(self, manager):
        """Reject a pending request"""
        task = {
            "operation": "delete",
            "environment": "production",
            "resource_type": "database"
        }
        
        request_id = await manager.create_approval_request(
            workflow_id="test-workflow-101",
            thread_id="thread-jkl",
            checkpoint_id="checkpoint-mno",
            task=task,
            agent_name="infrastructure"
        )
        
        # Reject
        success = await manager.reject_request(
            request_id=request_id,
            rejector_id="jane.smith",
            reason="Insufficient justification for production deletion"
        )
        
        assert success == True
        
        status = await manager.check_approval_status(request_id)
        assert status["status"] == "rejected"
        assert "insufficient" in status["rejection_reason"].lower()
    
    @pytest.mark.anyio
    async def test_authorization_check(self, manager):
        """Developers cannot approve critical risk requests"""
        task = {
            "operation": "delete",
            "environment": "production",
            "resource_type": "database",
            "data_sensitive": True
        }
        
        request_id = await manager.create_approval_request(
            workflow_id="test-workflow-202",
            thread_id="thread-pqr",
            checkpoint_id="checkpoint-stu",
            task=task,
            agent_name="infrastructure"
        )
        
        # Try to approve as developer (insufficient permission)
        success = await manager.approve_request(
            request_id=request_id,
            approver_id="junior.dev",
            approver_role="developer"
        )
        
        assert success == False, "Developer cannot approve critical risk"
        
        # Approve as devops engineer (sufficient permission)
        success = await manager.approve_request(
            request_id=request_id,
            approver_id="senior.devops",
            approver_role="devops_engineer"
        )
        
        assert success == True, "DevOps engineer can approve critical risk"


class TestWorkflowIntegration:
    """Test LangGraph workflow integration"""
    
    @pytest.mark.anyio
    async def test_interrupt_before_approval_gate(self):
        """Workflow should interrupt at approval gate for high-risk ops"""
        from interrupt_nodes import create_approval_workflow
        
        workflow = create_approval_workflow("test-agent")
        
        initial_state = {
            "workflow_id": "test-interrupt-1",
            "thread_id": "thread-test-1",
            "agent_name": "test-agent",
            "pending_operation": {
                "operation": "deploy",
                "environment": "production",
                "resource_type": "application",
                "description": "Test production deployment"
            }
        }
        
        # First invocation should interrupt
        result = await workflow.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": "thread-test-1"}}
        )
        
        assert result["approval_status"] == "pending"
        assert result["approval_request_id"] is not None
        
        # TODO: Complete test with approval and resumption
    
    @pytest.mark.anyio
    async def test_auto_approve_low_risk_workflow(self):
        """Low risk operations should not interrupt workflow"""
        from interrupt_nodes import create_approval_workflow
        
        workflow = create_approval_workflow("test-agent")
        
        initial_state = {
            "workflow_id": "test-auto-approve-1",
            "thread_id": "thread-test-2",
            "agent_name": "test-agent",
            "pending_operation": {
                "operation": "read",
                "environment": "dev",
                "resource_type": "file",
                "description": "Read config file"
            }
        }
        
        result = await workflow.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": "thread-test-2"}}
        )
        
        assert result["approval_status"] == "approved"
        assert result["approval_request_id"] is None


# Pytest configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
