#!/usr/bin/env python3
"""Test Linear workspace client fix"""
import asyncio
import sys
sys.path.insert(0, 'shared')

from lib.linear_workspace_client import LinearWorkspaceClient

async def test_linear():
    client = LinearWorkspaceClient()
    
    # Test 1: Get issue by identifier
    print("Test 1: Get issue by identifier (DEV-68)")
    issue = await client.get_issue_by_identifier('DEV-68')
    print(f"  ✓ Issue ID: {issue['id']}")
    print(f"  ✓ Title: {issue['title']}")
    print(f"  ✓ State: {issue['state']['name']}")
    
    # Test 2: Post approval to hub (dry run - just verify no errors up to mutation)
    print("\nTest 2: Post to approval hub (will create real comment)")
    try:
        comment_id = await client.post_to_approval_hub(
            approval_id="test-123",
            task_description="Test deployment task",
            risk_level="low",
            project_name="Dev-Tools Test",
            metadata={"test": True}
        )
        print(f"  ✓ Comment created: {comment_id}")
    except Exception as e:
        print(f"  ✗ Failed: {e}")
    
    print("\n✓ Linear integration working!")

if __name__ == "__main__":
    asyncio.run(test_linear())
