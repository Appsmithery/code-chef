#!/usr/bin/env python3
"""Delete test issue DEV-138 from Linear."""

import os
import requests

LINEAR_API_KEY = os.getenv(
    "LINEAR_API_KEY",
    "lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571",
)
ISSUE_ID = "e7c038ce-0b2c-4716-9af9-96fcdfb7b907"

mutation = (
    """
mutation {
  issueDelete(id: "%s") {
    success
  }
}
"""
    % ISSUE_ID
)

response = requests.post(
    "https://api.linear.app/graphql",
    headers={
        "Authorization": f"Bearer {LINEAR_API_KEY}",
        "Content-Type": "application/json",
    },
    json={"query": mutation},
)

result = response.json()
if result.get("data", {}).get("issueDelete", {}).get("success"):
    print("✓ Test issue DEV-138 deleted successfully")
else:
    print(f"Error: {response.text}")
