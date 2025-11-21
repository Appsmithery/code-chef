#!/usr/bin/env python3
"""Test HITL approval sub-issue creation with Linear templates"""
import asyncio
import sys
import uuid
from datetime import datetime
sys.path.insert(0, 'shared')

from lib.linear_workspace_client import LinearWorkspaceClient

async def test_hitl_subissue():
    """Test creating HITL approval sub-issue under DEV-68"""
    client = LinearWorkspaceClient()
    
    # Test data
    approval_id = f"test-approval-{uuid.uuid4()}"
    task_description = "Deploy database schema changes to production with new user_permissions table"
    
    print("=" * 80)
    print("Testing HITL Approval Sub-Issue Creation")
    print("=" * 80)
    print(f"\nApproval ID: {approval_id}")
    print(f"Task: {task_description}")
    print(f"Parent Issue: DEV-68 (HITL Approvals Hub)")
    
    try:
        # Create sub-issue
        print("\nCreating sub-issue...")
        issue = await client.create_approval_subissue(
            approval_id=approval_id,
            task_description=task_description,
            risk_level="high",
            project_name="Dev-Tools",
            agent_name="orchestrator",
            metadata={
                "timestamp": datetime.now().isoformat(),
                "priority": "high",
                "environment": "production",
                "estimated_cost": 250
            }
        )
        
        print("\n✓ Sub-issue created successfully!")
        print(f"  Issue ID: {issue['id']}")
        print(f"  Identifier: {issue['identifier']}")
        print(f"  Title: {issue['title']}")
        print(f"  URL: {issue['url']}")
        
        # Verify it's a sub-issue of DEV-68
        print("\n✓ Verifying parent relationship...")
        parent_issue = await client.get_issue_by_identifier('DEV-68')
        print(f"  Parent: DEV-68 ({parent_issue['title']})")
        
        print("\n" + "=" * 80)
        print("Test completed successfully!")
        print("=" * 80)
        print(f"\nView issue: {issue['url']}")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_hitl_subissue())
