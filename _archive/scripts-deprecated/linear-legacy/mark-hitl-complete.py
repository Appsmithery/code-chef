#!/usr/bin/env python3
"""
Mark all HITL subtasks as complete in Linear.
"""

import asyncio
import json
import os
import sys
import aiohttp


async def get_workflow_states(api_key: str, team_id: str):
    """Get workflow states for the team."""
    
    query = """
    query WorkflowStates($teamId: String!) {
      team(id: $teamId) {
        states {
          nodes {
            id
            name
            type
          }
        }
      }
    }
    """
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}" if not api_key.startswith("Bearer ") else api_key
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.linear.app/graphql",
            json={"query": query, "variables": {"teamId": team_id}},
            headers=headers
        ) as response:
            result = await response.json()
            
            if response.status == 200 and "data" in result:
                states = result["data"]["team"]["states"]["nodes"]
                return {state["type"]: state["id"] for state in states}
            
            return {}


async def mark_issue_complete(issue_id: str, state_id: str, api_key: str):
    """Mark an issue as complete."""
    
    mutation = """
    mutation IssueUpdate($id: String!, $stateId: String!) {
      issueUpdate(id: $id, input: { stateId: $stateId }) {
        success
        issue {
          id
          title
          state {
            name
          }
        }
      }
    }
    """
    
    variables = {
        "id": issue_id,
        "stateId": state_id
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}" if not api_key.startswith("Bearer ") else api_key
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.linear.app/graphql",
            json={"query": mutation, "variables": variables},
            headers=headers
        ) as response:
            result = await response.json()
            
            if response.status != 200:
                print(f"❌ API error: {response.status}")
                return False
            
            if "errors" in result:
                print(f"❌ GraphQL errors: {result['errors']}")
                return False
            
            if result.get("data", {}).get("issueUpdate", {}).get("success"):
                issue = result["data"]["issueUpdate"]["issue"]
                print(f"✅ {issue['title']} → {issue['state']['name']}")
                return True
            
            return False


async def main():
    """Mark all HITL tasks as complete."""
    
    # Get API key from environment
    api_key = os.getenv("LINEAR_API_KEY")
    if not api_key:
        print("❌ LINEAR_API_KEY environment variable not set")
        return 1
    
    team_id = "f5b610be-ac34-4983-918b-2c9d00aa9b7a"
    
    # Get workflow states
    print("🔍 Fetching workflow states...")
    states = await get_workflow_states(api_key, team_id)
    
    if not states:
        print("❌ Could not fetch workflow states")
        return 1
    
    print("📋 Available states:")
    for state_type, state_id in states.items():
        print(f"   - {state_type}: {state_id}")
    
    completed_state_id = states.get("completed")
    if not completed_state_id:
        print("❌ No 'completed' state found")
        return 1
    
    print(f"\n✓ Using completed state: {completed_state_id}\n")
    
    # All HITL subtasks
    subtasks = [
        ("931ab455-a187-4596-9d0a-19c55cdc1394", "Task 2.1: Interrupt Configuration"),
        ("59553a7b-4a6f-4951-b77b-9930d40d92c0", "Task 2.2: Taskfile Commands for HITL Operations"),
        # New tasks just created - we'll need their IDs
    ]
    
    print("📝 Marking subtasks as complete...\n")
    
    completed_count = 0
    for issue_id, title in subtasks:
        print(f"Updating: {title}")
        success = await mark_issue_complete(issue_id, completed_state_id, api_key)
        if success:
            completed_count += 1
        print()
    
    print(f"✨ Summary: Marked {completed_count}/{len(subtasks)} tasks complete")
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
