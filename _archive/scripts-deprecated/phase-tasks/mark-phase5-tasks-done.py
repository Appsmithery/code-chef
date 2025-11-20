#!/usr/bin/env python3
"""Mark completed Phase 5 tasks as Done."""
import requests

LINEAR_API_KEY = "lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571"
GRAPHQL_URL = "https://api.linear.app/graphql"
DONE_STATE_ID = "d202b359-862b-4ce5-8b0a-972bf046250a"

headers = {
    "Authorization": f"Bearer {LINEAR_API_KEY}",
    "Content-Type": "application/json"
}

completed_tasks = [
    ("PR-64", "Task 5.2: Asynchronous Notification System"),
    ("PR-81", "Task 5.3: Workspace-Level Approval Hub")
]

print("Marking completed tasks as Done...\n")

for issue_id, title in completed_tasks:
    mutation = """
    mutation($issueId: String!, $stateId: String!) {
      issueUpdate(id: $issueId, input: { stateId: $stateId }) {
        success
        issue {
          identifier
          title
          state {
            name
          }
        }
      }
    }
    """
    
    variables = {
        "issueId": issue_id,
        "stateId": DONE_STATE_ID
    }
    
    response = requests.post(
        GRAPHQL_URL,
        json={"query": mutation, "variables": variables},
        headers=headers
    )
    
    result = response.json()
    if "errors" in result:
        print(f"❌ Failed: {issue_id} - {title}")
        print(f"   Error: {result['errors']}")
    elif result["data"]["issueUpdate"]["success"]:
        issue = result["data"]["issueUpdate"]["issue"]
        print(f"✅ {issue['identifier']}: {issue['title']}")
        print(f"   State: {issue['state']['name']}")

print("\n✨ Completed tasks marked as Done!")
