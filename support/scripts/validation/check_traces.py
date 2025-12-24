#!/usr/bin/env python3
"""Check for traces in LangSmith project."""
import os
import requests

API_KEY = os.getenv("LANGCHAIN_API_KEY")
PROJECT = "code-chef-production"

headers = {"x-api-key": API_KEY}

# Query runs
resp = requests.get(
    "https://api.smith.langchain.com/runs",
    headers=headers,
    params={"project": PROJECT, "limit": 20}
)

print(f"Status: {resp.status_code}")
print(f"Response length: {len(resp.text)}")
print(f"\nFirst 2000 chars:")
print(resp.text[:2000])
