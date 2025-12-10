#!/usr/bin/env python3
"""Wait for Space to finish building and test health."""

import time

import httpx
from huggingface_hub import HfApi

api = HfApi()
space_id = "alextorelli/code-chef-modelops-trainer"
space_url = f"https://alextorelli-code-chef-modelops-trainer.hf.space"

print("Waiting for Space to be RUNNING...")
max_wait = 180
start = time.time()

while (time.time() - start) < max_wait:
    info = api.space_info(space_id)
    stage = info.runtime.stage if info.runtime else "UNKNOWN"
    print(f"  Stage: {stage}")

    if stage == "RUNNING":
        print("✓ Space is RUNNING!")

        # Test health endpoint
        print("\nTesting health endpoint...")
        try:
            response = httpx.get(f"{space_url}/health", timeout=30.0)
            print(f"  Status: {response.status_code}")
            if response.status_code == 200:
                print(f"  Health: {response.json()}")
                print("\n✓ Space is healthy and ready!")
                exit(0)
            else:
                print(f"  Response: {response.text[:200]}")
        except Exception as e:
            print(f"  Error: {e}")

        time.sleep(10)
        continue

    elif stage == "BUILD_ERROR":
        print("✗ Build failed")
        exit(1)

    time.sleep(15)

print(f"\n✗ Timeout after {max_wait}s - Space still not ready")
exit(1)
