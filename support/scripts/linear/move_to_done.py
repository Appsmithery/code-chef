#!/usr/bin/env python3
"""Move CHEF-209 to Done state."""

import os
from dotenv import load_dotenv
import requests

load_dotenv("config/env/.env")
LINEAR_API_KEY = os.environ.get("LINEAR_CHEF_API_KEY")
HEADERS = {"Authorization": LINEAR_API_KEY, "Content-Type": "application/json"}

ISSUE_ID = "745524b1-dba0-420d-bc1f-11bab2f1bc76"
DONE_STATE_ID = "d202b359-862b-4ce5-8b0a-972bf046250a"

mutation = """
mutation UpdateIssue($id: String!, $stateId: String!) {
  issueUpdate(id: $id, input: { stateId: $stateId }) {
    success
    issue {
      identifier
      state { name }
      url
    }
  }
}
"""

response = requests.post(
    "https://api.linear.app/graphql",
    headers=HEADERS,
    json={"query": mutation, "variables": {"id": ISSUE_ID, "stateId": DONE_STATE_ID}}
)
result = response.json()

if result.get("data", {}).get("issueUpdate", {}).get("success"):
    issue = result["data"]["issueUpdate"]["issue"]
    print(f"Issue {issue['identifier']} moved to: {issue['state']['name']}")
    print(f"URL: {issue['url']}")
else:
    print(f"Failed: {result}")
