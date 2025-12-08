#!/usr/bin/env python3
"""Test Linear API search."""

import os
from dotenv import load_dotenv
import requests

load_dotenv("config/env/.env")
LINEAR_API_KEY = os.environ.get("LINEAR_CHEF_API_KEY")
HEADERS = {"Authorization": LINEAR_API_KEY, "Content-Type": "application/json"}

query = """
query SearchIssues($filter: IssueFilter) {
  issues(filter: $filter, first: 20) {
    nodes {
      id
      identifier
      title
    }
  }
}
"""
variables = {"filter": {"title": {"containsIgnoreCase": "error"}}}
response = requests.post("https://api.linear.app/graphql", headers=HEADERS, json={"query": query, "variables": variables})
print(response.json())
