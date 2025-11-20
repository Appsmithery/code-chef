#!/usr/bin/env python3
"""Create Phase 5 sub-issues for PR-56."""
import os
import requests
import time

LINEAR_API_KEY = "lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571"
GRAPHQL_URL = "https://api.linear.app/graphql"
TEAM_ID = "f5b610be-ac34-4983-918b-2c9d00aa9b7a"
BACKLOG_STATE_ID = "21046e8e-4fc7-4977-82b7-552e501b2f8a"

headers = {
    "Authorization": f"Bearer {LINEAR_API_KEY}",
    "Content-Type": "application/json"
}

# Get PR-56 UUID
query = """
query {
  issue(id: "PR-56") {
    id
    identifier
    title
  }
}
"""
response = requests.post(GRAPHQL_URL, json={"query": query}, headers=headers)
parent_uuid = response.json()["data"]["issue"]["id"]
print(f"PR-56 UUID: {parent_uuid}\n")

# Define sub-issues
sub_issues = [
    {
        "title": "Task 5.3: Workspace-Level Approval Hub",
        "description": "Create workspace-level approval hub (PR-68 ✅), configure LinearWorkspaceClient for workspace-scoped operations, implement posting logic. **Status**: Completed - PR-68 operational with @lead-minion mentions working",
        "priority": 2
    },
    {
        "title": "Task 5.4: Multi-Project Security Scoping",
        "description": "Implement LinearClientFactory with orchestrator/subagent routing, enforce project-scoped access for subagents, add security tests for cross-project isolation. Ensures subagents cannot access approval hub or other projects.",
        "priority": 1
    },
    {
        "title": "Task 5.5: Email Notification Fallback",
        "description": "Implement EmailNotifier for critical approvals, configure SMTP settings (smtp.gmail.com:587), add email templates for approval requests. Fallback for when Linear notifications are insufficient.",
        "priority": 3
    },
    {
        "title": "Task 5.6: Integration Testing and Documentation",
        "description": "End-to-end testing for approval workflow across multiple projects, multi-project isolation tests, operator guide for workspace hub setup, deployment documentation for droplet.",
        "priority": 2
    }
]

print("Creating sub-issues...\n")
for task in sub_issues:
    mutation = """
    mutation($teamId: String!, $parentId: String!, $title: String!, $description: String!, $priority: Int!, $stateId: String!) {
      issueCreate(input: {
        teamId: $teamId
        parentId: $parentId
        title: $title
        description: $description
        priority: $priority
        stateId: $stateId
      }) {
        success
        issue {
          identifier
          title
          url
        }
      }
    }
    """
    
    variables = {
        "teamId": TEAM_ID,
        "parentId": parent_uuid,
        "title": task["title"],
        "description": task["description"],
        "priority": task["priority"],
        "stateId": BACKLOG_STATE_ID
    }
    
    response = requests.post(
        GRAPHQL_URL,
        json={"query": mutation, "variables": variables},
        headers=headers
    )
    
    result = response.json()
    if "errors" in result:
        print(f"❌ Failed: {task['title']}")
        print(f"   Error: {result['errors']}")
    elif result["data"]["issueCreate"]["success"]:
        issue = result["data"]["issueCreate"]["issue"]
        print(f"✅ {issue['identifier']}: {issue['title']}")
        print(f"   URL: {issue['url']}")
    
    time.sleep(0.5)

print("\n✨ Phase 5 sub-issues created successfully!")
