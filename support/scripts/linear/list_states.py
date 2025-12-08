#!/usr/bin/env python3
"""List Linear workflow states for CHEF team."""

import os
from dotenv import load_dotenv
import requests

load_dotenv("config/env/.env")
LINEAR_API_KEY = os.environ.get("LINEAR_CHEF_API_KEY")
HEADERS = {"Authorization": LINEAR_API_KEY, "Content-Type": "application/json"}

# Get all workflow states
states_query = """query GetWorkflowStates { workflowStates(first: 50) { nodes { id name type team { key } } } }"""
response = requests.post("https://api.linear.app/graphql", headers=HEADERS, json={"query": states_query})
states = response.json().get("data", {}).get("workflowStates", {}).get("nodes", [])

chef_states = [s for s in states if s.get("team", {}).get("key") == "CHEF"]
print("CHEF team workflow states:")
for s in chef_states:
    print(f"  - {s['name']} (type: {s['type']}, id: {s['id']})")
