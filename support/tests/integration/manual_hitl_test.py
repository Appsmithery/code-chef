"""
Manual E2E test for HITL Linear webhook integration.

Run this to verify the complete flow works end-to-end.
"""
import asyncio
import sys
import os
import uuid

# Fix Windows event loop for psycopg
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))


async def test_approval_flow():
    """Test complete HITL approval flow."""
    from shared.lib.hitl_manager import get_hitl_manager
    
    print("🧪 Testing HITL Linear Integration")
    print("=" * 60)
    
    hitl = get_hitl_manager()
    
    # Create a high-risk task
    task = {
        "operation": "deploy",  # Changed to deploy for high risk
        "description": "Manual test of HITL Linear webhook integration",
        "environment": "production",  # production + deploy = high risk
        "resource_type": "deployment",
        "impact": "High - production deployment test",
        "risk_factors": ["production environment", "manual verification", "infrastructure change"],
    }
    
    workflow_id = str(uuid.uuid4())
    thread_id = f"thread-{uuid.uuid4()}"
    checkpoint_id = f"checkpoint-{uuid.uuid4()}"
    
    print("\n📋 Step 1: Creating approval request...")
    print(f"   Workflow ID: {workflow_id}")
    print(f"   Thread ID: {thread_id}")
    
    try:
        request_id = await hitl.create_approval_request(
            workflow_id=workflow_id,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            task=task,
            agent_name="test_agent",
        )
        
        if request_id:
            print(f"✅ Created approval request: {request_id}")
        else:
            print("⚠️  No approval required (low risk)")
            return
        
    except Exception as e:
        print(f"❌ Failed to create approval request: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Check status
    print("\n📋 Step 2: Checking approval status...")
    try:
        status = await hitl.check_approval_status(request_id)
        print(f"✅ Status: {status['status']}")
        print(f"   Risk Level: {status['risk_level']}")
        if status.get('expired'):
            print(f"   ⚠️  Expired: {status['expired']}")
    except Exception as e:
        print(f"❌ Failed to check status: {e}")
        return
    
    # Check if Linear issue was created
    print("\n📋 Step 3: Verifying Linear issue creation...")
    try:
        async with await hitl._get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT linear_issue_id, linear_issue_url FROM approval_requests WHERE id = %s",
                    (request_id,)
                )
                row = await cursor.fetchone()
                if row and row[0]:
                    print(f"✅ Linear issue created!")
                    print(f"   Issue ID: {row[0]}")
                    print(f"   Issue URL: {row[1]}")
                else:
                    print("⚠️  No Linear issue ID found")
    except Exception as e:
        print(f"❌ Failed to check Linear issue: {e}")
    
    print("\n📋 Step 4: Testing approval description formatting...")
    try:
        description = hitl._format_approval_description(request_id, task, "high")
        print("✅ Approval description formatted")
        print(f"   Length: {len(description)} characters")
        print(f"   Contains request ID: {'Yes' if request_id in description else 'No'}")
        print(f"   Contains operation: {'Yes' if 'test_hitl_integration' in description else 'No'}")
    except Exception as e:
        print(f"❌ Failed to format description: {e}")
    
    print("\n" + "=" * 60)
    print("✅ HITL Integration Test Completed")
    print("\nNext steps:")
    print("1. Check Linear for the created issue")
    print("2. Add a 👍 reaction to test webhook")
    print("3. Monitor orchestrator logs for webhook event")
    print(f"\nApproval Request ID: {request_id}")


if __name__ == "__main__":
    asyncio.run(test_approval_flow())
