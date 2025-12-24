#!/usr/bin/env python3
"""Test the /chat endpoint to generate rich LangSmith traces."""
import os
import requests

# Get API key from environment
API_KEY = os.getenv("ORCHESTRATOR_API_KEY")
if not API_KEY:
    print("❌ ORCHESTRATOR_API_KEY not set")
    exit(1)

# Make chat request
payload = {
    "message": "Test trace with full LLM call details",
    "user_id": "test-uat"
}

headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

print("Making request to /chat endpoint...")
print(f"API Key: {API_KEY[:20]}...")

response = requests.post(
    "http://localhost:8001/chat",
    headers=headers,
    json=payload,
    timeout=60
)

print(f"\nStatus: {response.status_code}")
print(f"Response: {response.text[:1000]}")

if response.status_code == 200:
    data = response.json()
    print(f"\n✓ Success!")
    print(f"Response contains: {list(data.keys())}")
    if "session_id" in data:
        print(f"Session ID: {data['session_id']}")
    print(f"\n🔍 Check LangSmith for rich traces with nested LLM calls!")
else:
    print(f"\n❌ Request failed")
