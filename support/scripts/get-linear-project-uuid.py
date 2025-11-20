#!/usr/bin/env python3
"""Get the full UUID for AI DevOps Agent Platform project."""

import os
import requests

LINEAR_API_KEY = os.environ.get("LINEAR_API_KEY")
if not LINEAR_API_KEY:
    print("❌ LINEAR_API_KEY environment variable not set")
    exit(1)

GRAPHQL_ENDPOINT = "https://api.linear.app/graphql"

query = """
query GetProjects {
    projects {
        nodes {
            id
            name
            slugId
            url
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
    json={"query": query}
)

if response.status_code != 200:
    print(f"❌ Failed: {response.status_code}")
    print(response.text)
    exit(1)

data = response.json()
if "errors" in data:
    print(f"❌ Errors: {data['errors']}")
    exit(1)

projects = data.get("data", {}).get("projects", {}).get("nodes", [])

print("\n📁 All Projects:\n")
for p in projects:
    print(f"  Name: {p['name']}")
    print(f"  ID (UUID): {p['id']}")
    print(f"  Slug ID: {p['slugId']}")
    print(f"  URL: {p['url']}")
    print()

# Find AI DevOps Agent Platform
for p in projects:
    if "AI DevOps" in p['name'] or "Agent Platform" in p['name']:
        print(f"✅ Found target project!")
        print(f"   Full UUID: {p['id']}")
        print(f"   Use this in scripts instead of: 78b3b839d36b")
