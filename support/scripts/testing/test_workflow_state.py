#!/usr/bin/env python3
"""
Test workflow state management.

Quick validation script to ensure WorkflowStateManager is working correctly.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from shared.lib.workflow_state import WorkflowStateManager


async def test_workflow_state():
    """Test basic workflow state operations."""
    print("="*60)
    print("Testing Workflow State Management")
    print("="*60)
    
    # Connection string
    db_conn = os.getenv(
        "DATABASE_URL",
        "postgresql://devtools:changeme@localhost:5432/devtools"
    )
    
    state_mgr = WorkflowStateManager(db_conn)
    await state_mgr.connect()
    
    try:
        # Test 1: Create workflow
        print("\n1. Creating workflow...")
        workflow_id = await state_mgr.create_workflow(
            workflow_type="test_workflow",
            initial_state={"test": "data", "step": 1},
            participating_agents=["test-agent-1", "test-agent-2"]
        )
        print(f"   ✓ Created workflow: {workflow_id}")
        
        # Test 2: Get workflow
        print("\n2. Retrieving workflow...")
        workflow = await state_mgr.get_workflow(workflow_id)
        print(f"   ✓ Retrieved workflow: {workflow.workflow_type}")
        print(f"     Status: {workflow.status}")
        print(f"     Agents: {', '.join(workflow.participating_agents)}")
        
        # Test 3: Update state
        print("\n3. Updating state...")
        await state_mgr.update_state(
            workflow_id=workflow_id,
            updates={"step": 2, "progress": "50%"},
            agent_id="test-agent-1"
        )
        print("   ✓ State updated")
        
        # Test 4: Create checkpoint
        print("\n4. Creating checkpoint...")
        checkpoint_id = await state_mgr.checkpoint(
            workflow_id=workflow_id,
            step_name="step1",
            agent_id="test-agent-1",
            data={"result": "success", "output": "test output"},
            duration_ms=123,
            status="success"
        )
        print(f"   ✓ Checkpoint created: {checkpoint_id}")
        
        # Test 5: Get checkpoints
        print("\n5. Retrieving checkpoints...")
        checkpoints = await state_mgr.get_checkpoints(workflow_id)
        print(f"   ✓ Found {len(checkpoints)} checkpoint(s)")
        for cp in checkpoints:
            print(f"     - {cp.step_name} by {cp.agent_id} ({cp.status})")
        
        # Test 6: Update step
        print("\n6. Updating workflow step...")
        await state_mgr.update_step(
            workflow_id=workflow_id,
            current_step="step2",
            agent_id="test-agent-2"
        )
        print("   ✓ Step updated")
        
        # Test 7: Complete workflow
        print("\n7. Completing workflow...")
        await state_mgr.complete_workflow(
            workflow_id=workflow_id,
            final_state={"final_result": "all tests passed"}
        )
        print("   ✓ Workflow completed")
        
        # Test 8: List active workflows
        print("\n8. Listing active workflows...")
        active = await state_mgr.list_active_workflows()
        print(f"   ✓ Found {len(active)} active workflow(s)")
        
        # Test 9: Get statistics
        print("\n9. Getting workflow statistics...")
        stats = await state_mgr.get_workflow_statistics()
        print(f"   ✓ Statistics retrieved")
        for stat in stats:
            print(f"     - {stat['workflow_type']}: {stat['total_workflows']} total, "
                  f"{stat['completed_count']} completed")
        
        print("\n" + "="*60)
        print("✓ All tests passed!")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await state_mgr.close()
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_workflow_state())
    sys.exit(0 if success else 1)
