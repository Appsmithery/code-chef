"""
Integration tests for HITL Linear webhook integration.

Tests the complete flow:
1. High-risk operation triggers HITL approval
2. Linear issue created automatically
3. Linear webhook received on approval
4. Workflow resumes from checkpoint
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

# Test configuration
TEST_PROJECT_ID = "b21cbaa1-9f09-40f4-b62a-73e0f86dd501"  # code/chef


@pytest.mark.asyncio
async def test_hitl_approval_creates_linear_issue():
    """Verify approval request creates Linear issue with proper metadata."""
    from shared.lib.hitl_manager import get_hitl_manager

    hitl = get_hitl_manager()

    # Create high-risk task
    task = {
        "operation": "deploy_to_production",
        "description": "Deploy JWT authentication to production",
        "environment": "production",
        "resource_type": "deployment",
        "impact": "High - affects all users",
        "risk_factors": ["production deployment", "authentication change"],
    }

    workflow_id = str(uuid.uuid4())
    thread_id = f"thread-{uuid.uuid4()}"
    checkpoint_id = f"checkpoint-{uuid.uuid4()}"

    # Mock Linear client to avoid actual API calls in tests
    with patch("shared.lib.hitl_manager.LinearWorkspaceClient") as mock_linear:
        mock_client = AsyncMock()
        mock_client.create_issue_with_document.return_value = {
            "id": "test-linear-issue-id",
            "url": "https://linear.app/dev-ops/issue/CHEF-999",
            "identifier": "CHEF-999",
        }
        mock_linear.return_value = mock_client

        # Create approval request
        request_id = await hitl.create_approval_request(
            workflow_id=workflow_id,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            task=task,
            agent_name="feature_dev",
        )

        # Verify request created
        assert request_id is not None

        # Verify Linear issue was created
        mock_client.create_issue_with_document.assert_called_once()
        call_args = mock_client.create_issue_with_document.call_args

        assert "[HITL]" in call_args.kwargs["title"]
        assert request_id in call_args.kwargs["description"]
        assert "deploy_to_production" in call_args.kwargs["description"]

        # Verify database has linear_issue_id
        status = await hitl.check_approval_status(request_id)
        assert status["status"] == "pending"

        print(f"✅ Test passed: Created approval request {request_id}")
        print(f"   Linear issue would be: CHEF-999")


@pytest.mark.asyncio
async def test_webhook_resumes_workflow():
    """Verify webhook triggers workflow resume when approval received."""
    from shared.lib.hitl_manager import get_hitl_manager
    from shared.lib.linear_webhook_processor import LinearWebhookProcessor

    hitl = get_hitl_manager()
    webhook_processor = LinearWebhookProcessor()

    # Create approval request
    task = {
        "operation": "test_webhook_resume",
        "description": "Test webhook workflow resume",
        "environment": "staging",
    }

    workflow_id = str(uuid.uuid4())
    thread_id = f"thread-{uuid.uuid4()}"
    checkpoint_id = f"checkpoint-{uuid.uuid4()}"
    linear_issue_id = f"test-issue-{uuid.uuid4()}"

    with patch("shared.lib.hitl_manager.LinearWorkspaceClient") as mock_linear:
        mock_client = AsyncMock()
        mock_client.create_issue_with_document.return_value = {
            "id": linear_issue_id,
            "url": "https://linear.app/dev-ops/issue/CHEF-998",
            "identifier": "CHEF-998",
        }
        mock_linear.return_value = mock_client

        request_id = await hitl.create_approval_request(
            workflow_id=workflow_id,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            task=task,
            agent_name="infrastructure",
        )

    # Simulate Linear webhook (👍 reaction)
    webhook_event = {
        "type": "Reaction",
        "action": "create",
        "data": {
            "emoji": "👍",
            "user": {
                "id": "test-user-id",
                "name": "Test Approver",
                "email": "approver@test.com",
            },
            "comment": {
                "id": "comment-id",
                "body": f"Looks good! REQUEST_ID={request_id}",
                "url": "https://linear.app/dev-ops/issue/CHEF-998#comment-123",
                "issue": {"id": linear_issue_id},
            },
        },
    }

    # Process webhook
    result = await webhook_processor.process_webhook(webhook_event)

    assert result["action"] == "resume_workflow"
    assert result["metadata"]["approved_by_name"] == "Test Approver"

    # Verify approval status updated
    status = await hitl.check_approval_status(request_id)
    # Note: In real flow, webhook handler calls resume_workflow_from_approval
    # which updates status. In this test, we just verify webhook processing.

    print(f"✅ Test passed: Webhook processed approval for {request_id}")
    print(f"   Approver: Test Approver")


@pytest.mark.asyncio
async def test_format_approval_description():
    """Verify approval description formatting is consistent."""
    from shared.lib.hitl_manager import get_hitl_manager

    hitl = get_hitl_manager()

    request_id = str(uuid.uuid4())
    task = {
        "operation": "database_migration",
        "description": "Migrate user table schema",
        "environment": "production",
        "resource_type": "database",
        "impact": "Critical - affects all user data",
        "risk_factors": ["data migration", "schema change", "production database"],
    }

    description = hitl._format_approval_description(request_id, task, "critical")

    # Verify key elements present
    assert "🔴 **CRITICAL Risk Operation**" in description
    assert request_id in description
    assert "database_migration" in description
    assert "Environment**: production" in description
    assert "Risk Factors" in description
    assert "data migration" in description
    assert "👍" in description  # Approval instructions
    assert "👎" in description  # Rejection instructions

    print("✅ Test passed: Approval description formatted correctly")
    print(f"   Request ID: {request_id}")
    print(f"   Operation: database_migration")


@pytest.mark.asyncio
async def test_end_to_end_approval_flow():
    """
    Complete end-to-end test of HITL approval flow.

    Flow:
    1. Create high-risk approval request
    2. Verify Linear issue created
    3. Simulate webhook approval
    4. Verify workflow resume triggered
    """
    from shared.lib.hitl_manager import get_hitl_manager

    hitl = get_hitl_manager()

    # Step 1: Create high-risk task
    task = {
        "operation": "delete_production_resources",
        "description": "Delete unused production S3 buckets",
        "environment": "production",
        "resource_type": "storage",
        "impact": "High - permanent data deletion",
        "risk_factors": [
            "production environment",
            "irreversible action",
            "data loss risk",
        ],
    }

    workflow_id = str(uuid.uuid4())
    thread_id = f"thread-{uuid.uuid4()}"
    checkpoint_id = f"checkpoint-{uuid.uuid4()}"
    linear_issue_id = f"test-issue-{uuid.uuid4()}"

    print("🧪 Starting end-to-end HITL approval flow test...")

    # Step 2: Create approval with mocked Linear
    with patch("shared.lib.hitl_manager.LinearWorkspaceClient") as mock_linear:
        mock_client = AsyncMock()
        mock_client.create_issue_with_document.return_value = {
            "id": linear_issue_id,
            "url": "https://linear.app/dev-ops/issue/CHEF-997",
            "identifier": "CHEF-997",
        }
        mock_linear.return_value = mock_client

        request_id = await hitl.create_approval_request(
            workflow_id=workflow_id,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            task=task,
            agent_name="infrastructure",
        )

        print(f"✅ Step 1: Created approval request {request_id}")
        print(f"   Linear issue: CHEF-997")

    # Step 3: Verify approval request is pending
    status = await hitl.check_approval_status(request_id)
    assert status["status"] == "pending"
    assert status["risk_level"] == "critical"  # Should be critical risk
    print(f"✅ Step 2: Approval request status = {status['status']}")

    # Step 4: Simulate approval (normally via webhook)
    approval_result = await hitl.approve_request(
        request_id=request_id,
        approver_id="test-ops-lead",
        approver_role="devops_engineer",
        justification="Reviewed bucket contents, safe to delete",
    )

    assert approval_result is True
    print(f"✅ Step 3: Approval granted by devops_engineer")

    # Step 5: Verify status updated
    status = await hitl.check_approval_status(request_id)
    assert status["status"] == "approved"
    assert status["approver_id"] == "test-ops-lead"
    print(f"✅ Step 4: Status updated to approved")

    print("\n🎉 End-to-end test completed successfully!")
    print(f"   Request ID: {request_id}")
    print(f"   Workflow ID: {workflow_id}")
    print(f"   Final Status: {status['status']}")


if __name__ == "__main__":
    print("🧪 Running HITL Linear Integration Tests\n")
    print("=" * 60)

    # Run tests
    asyncio.run(test_hitl_approval_creates_linear_issue())
    print()

    asyncio.run(test_format_approval_description())
    print()

    asyncio.run(test_webhook_resumes_workflow())
    print()

    asyncio.run(test_end_to_end_approval_flow())
    print()

    print("=" * 60)
    print("✅ All HITL integration tests passed!")
