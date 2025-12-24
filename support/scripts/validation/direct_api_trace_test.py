#!/usr/bin/env python3
"""
Direct LangSmith API trace upload without SDK batching.
Uses REST API directly to bypass multipart endpoint restrictions.
"""
import os
import time
import uuid
from datetime import datetime

import requests

# Get configuration
API_KEY = os.getenv("LANGCHAIN_API_KEY")
PROJECT_NAME = os.getenv("LANGCHAIN_PROJECT", "code-chef-production")
API_BASE = "https://api.smith.langchain.com"

print("=" * 80)
print("DIRECT LANGSMITH API TRACE TEST")
print("=" * 80)
print(f"\nAPI Key: {API_KEY[:30] if API_KEY else 'NOT SET'}...")
print(f"Project: {PROJECT_NAME}")
print(f"API Base: {API_BASE}")

if not API_KEY:
    print("\n❌ ERROR: LANGCHAIN_API_KEY not set")
    exit(1)

headers = {"x-api-key": API_KEY, "Content-Type": "application/json"}

# Test scenarios
scenarios = [
    "Implement JWT authentication middleware",
    "Review security vulnerabilities in auth code",
    "Deploy to Kubernetes with autoscaling",
    "Setup GitHub Actions CI/CD pipeline",
    "Create API documentation",
]

print(f"\nTesting {len(scenarios)} trace uploads...")
print("=" * 80)

successful_uploads = 0

for i, scenario in enumerate(scenarios, 1):
    run_id = str(uuid.uuid4())

    # Create run payload (single trace, not batched)
    run_data = {
        "id": run_id,
        "name": f"trace_test_{i}",
        "run_type": "chain",
        "project_name": PROJECT_NAME,
        "inputs": {"message": scenario},
        "outputs": {
            "intent": "task_submission",
            "confidence": 0.92,
            "tokens_used": 370,
            "tokens_saved": 480,
        },
        "start_time": datetime.utcnow().isoformat() + "Z",
        "end_time": datetime.utcnow().isoformat() + "Z",
        "extra": {
            "metadata": {
                "environment": "direct-api-test",
                "test_type": "direct_upload",
                "scenario": scenario,
                "experiment_group": "code-chef",
                "extension_version": "2.0.0",
                "model_version": "qwen-2.5-coder-7b",
            }
        },
    }

    try:
        # POST to /runs endpoint (not multipart)
        response = requests.post(
            f"{API_BASE}/runs", headers=headers, json=run_data, timeout=10
        )

        if response.status_code in [200, 201, 202]:
            print(f"✓ [{i}/{len(scenarios)}] Uploaded: {scenario[:50]}...")
            successful_uploads += 1
        else:
            print(
                f"✗ [{i}/{len(scenarios)}] Failed ({response.status_code}): {response.text[:100]}"
            )

    except Exception as e:
        print(f"✗ [{i}/{len(scenarios)}] Error: {str(e)[:100]}")

    time.sleep(0.5)

print("\n" + "=" * 80)
print("RESULTS")
print("=" * 80)
print(f"\nSuccessful uploads: {successful_uploads}/{len(scenarios)}")

if successful_uploads > 0:
    print(f"\n✓ Check LangSmith project '{PROJECT_NAME}' for traces")
    print(f'Filter: environment:"direct-api-test"')
    print(f"Time range: Last 5 minutes")
else:
    print("\n✗ No traces uploaded successfully")
    print("Check service key permissions for /runs endpoint")

print("=" * 80 + "\n")
