#!/usr/bin/env python3
"""Check for traces in LangSmith project."""
import os

import requests

API_KEY = os.getenv("LANGCHAIN_API_KEY")
PROJECT = "code-chef-production"

headers = {"x-api-key": API_KEY}

print(f"Checking project: {PROJECT}")
print(f"API Key: {API_KEY[:30]}...")
print("=" * 80)

# Try to query sessions (projects)
print("\n1. Checking sessions endpoint...")
resp = requests.get(
    "https://api.smith.langchain.com/sessions",
    headers=headers,
    params={"name": PROJECT, "limit": 10},
)
print(f"   Status: {resp.status_code}")
if resp.status_code == 200:
    import json

    data = resp.json()
    print(f"   Found {len(data)} sessions")
    if data:
        print(f"   First session: {json.dumps(data[0], indent=2)[:500]}")

# Try runs query endpoint
print("\n2. Checking runs/query endpoint with session UUID...")
if resp.status_code == 200:
    import json

    data = resp.json()
    if data:
        session_id = data[0]["id"]
        print(f"   Using session ID: {session_id}")

        resp2 = requests.post(
            "https://api.smith.langchain.com/runs/query",
            headers=headers,
            json={"session": [session_id], "limit": 20},
        )
        print(f"   Status: {resp2.status_code}")
        if resp2.status_code == 200:
            data2 = resp2.json()
            print(f"   Response keys: {list(data2.keys())}")
            if "runs" in data2:
                print(f"   Found {len(data2['runs'])} runs in project")
                if data2["runs"]:
                    print(f"\n   Recent run names:")
                    for run in data2["runs"][:5]:
                        print(
                            f"     - {run.get('name', 'unnamed')} at {run.get('start_time', 'unknown')}"
                        )
        else:
            print(f"   Error: {resp2.text[:500]}")

print("\n" + "=" * 80)
