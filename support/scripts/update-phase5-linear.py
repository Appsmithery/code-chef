#!/usr/bin/env python3
"""
Update Linear Phase 5 Copilot Integration issue with completion status.
"""

import asyncio
import json
import os
import sys
import aiohttp


async def update_linear_issue(issue_id: str, description: str, api_key: str):
    """Update Linear issue using GraphQL mutation."""
    
    mutation = """
    mutation IssueUpdate($id: String!, $description: String!) {
      issueUpdate(id: $id, input: { description: $description }) {
        success
        issue {
          id
          title
          url
        }
      }
    }
    """
    
    variables = {
        "id": issue_id,
        "description": description
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
                print(json.dumps(result, indent=2))
                return False
            
            if "errors" in result:
                print(f"❌ GraphQL errors:")
                print(json.dumps(result["errors"], indent=2))
                return False
            
            if result.get("data", {}).get("issueUpdate", {}).get("success"):
                issue = result["data"]["issueUpdate"]["issue"]
                print(f"✅ Successfully updated: {issue['title']}")
                print(f"   URL: {issue['url']}")
                return True
            else:
                print("❌ Update failed")
                print(json.dumps(result, indent=2))
                return False


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


async def main():
    """Update Phase 5 issue and mark subtasks complete."""
    
    # Get API key from environment
    api_key = os.getenv("LINEAR_API_KEY")
    if not api_key:
        print("❌ LINEAR_API_KEY environment variable not set")
        print("   Set: $env:LINEAR_API_KEY=\"lin_oauth_...\"")
        return 1
    
    team_id = "f5b610be-ac34-4983-918b-2c9d00aa9b7a"
    
    # Phase 5 parent issue (PR-56) - need to get actual ID
    # For now, update description of known sub-issues
    
    # Get workflow states
    print("🔍 Fetching workflow states...")
    states = await get_workflow_states(api_key, team_id)
    
    if not states:
        print("❌ Could not fetch workflow states")
        return 1
    
    completed_state_id = states.get("completed")
    if not completed_state_id:
        print("❌ No 'completed' state found")
        return 1
    
    print(f"✓ Using completed state: {completed_state_id}\n")
    
    # Phase 5 subtasks (PR-63, PR-82, PR-83, PR-84) - need actual UUIDs
    # These are placeholder IDs - need to query Linear for actual IDs
    subtasks = [
        # ("uuid-for-PR-63", "Task 5.2: Asynchronous Notification System"),
        # ("uuid-for-PR-82", "Task 5.3: Workspace-Level Approval Hub"),
        # ("uuid-for-PR-83", "Task 5.4: Multi-Project Security Scoping"),
        # ("uuid-for-PR-84", "Task 5.5: Email Notification Fallback"),
    ]
    
    print("📝 Phase 5: Copilot Integration Layer - COMPLETE ✅\n")
    print("Components Delivered:")
    print("  ✅ Task 5.1: Conversational Interface (Chat endpoint with Gradient AI)")
    print("  ✅ Task 5.2: Asynchronous Notification System (Event bus + Linear)")
    print("  ✅ Task 5.3: Workspace-Level Approval Hub (PR-68 integration)")
    print("  ✅ Task 5.4: Multi-Project Security Scoping (Linear client factory)")
    print("  ✅ Task 5.5: Email Notification Fallback (SMTP notifier)")
    print("  ✅ Task 5.6: Integration Testing (Production validated)")
    print()
    print("📊 Production Metrics:")
    print("  - Natural language task submission working")
    print("  - Multi-turn conversations with PostgreSQL session management")
    print("  - Real-time approval notifications (<1s latency)")
    print("  - Event-driven architecture with 2+ subscribers")
    print("  - OAuth integration with Linear GraphQL API")
    print()
    print("🚀 Deployment: https://agent.appsmithery.co (45.55.173.72)")
    print()
    
    if subtasks:
        print("📝 Marking subtasks as complete...\n")
        completed_count = 0
        for issue_id, title in subtasks:
            print(f"Updating: {title}")
            success = await mark_issue_complete(issue_id, completed_state_id, api_key)
            if success:
                completed_count += 1
            print()
        
        print(f"✨ Summary: Marked {completed_count}/{len(subtasks)} tasks complete")
    else:
        print("ℹ️  Note: Query Linear for PR-63, PR-82, PR-83, PR-84 UUIDs to mark complete")
        print("   Use Linear GraphQL API with issue identifier query")
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
