#!/usr/bin/env python3
"""Get complete project overview including all issues."""

import os
import sys
import requests
import json

LINEAR_API_KEY = os.environ.get("LINEAR_API_KEY")
if not LINEAR_API_KEY:
    print("ERROR: LINEAR_API_KEY not set")
    sys.exit(1)

GRAPHQL_ENDPOINT = "https://api.linear.app/graphql"
PROJECT_UUID = "b21cbaa1-9f09-40f4-b62a-73e0f86dd501"

query = """
query GetAllIssues($projectId: ID!) {
  issues(
    filter: {
      project: {id: {eq: $projectId}}
    }
    first: 200
    orderBy: createdAt
  ) {
    nodes {
      identifier
      title
      state {
        name
        type
      }
    }
  }
}
"""

response = requests.post(
    GRAPHQL_ENDPOINT,
    headers={
        "Authorization": LINEAR_API_KEY,
        "Content-Type": "application/json"
    },
    json={
        "query": query,
        "variables": {"projectId": PROJECT_UUID}
    }
)

data = response.json()
if "errors" in data:
    print(f"Errors: {data['errors']}")
    sys.exit(1)

issues = data.get("data", {}).get("issues", {}).get("nodes", [])

# Count by status
status_counts = {}
completed_count = 0
for issue in issues:
    state = issue["state"]["name"]
    state_type = issue["state"]["type"]
    status_counts[state] = status_counts.get(state, 0) + 1
    if state_type == "completed":
        completed_count += 1

print("=== AI DevOps Agent Platform - PROJECT OVERVIEW ===")
print(f"Total Issues: {len(issues)}")
print(f"Completed: {completed_count}")
print(f"Open: {len(issues) - completed_count}")
print()
print("By Status:")
for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
    print(f"  {status}: {count}")
