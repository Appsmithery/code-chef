#!/usr/bin/env python3
"""Basic LangSmith connection test without multipart ingestion."""
import os

from langsmith import Client
from langsmith.run_trees import RunTree

# Test connection
print("Testing LangSmith API connection...")
print(f"API Key: {os.getenv('LANGCHAIN_API_KEY', 'NOT SET')[:25]}...")
print(f"Project: {os.getenv('LANGCHAIN_PROJECT', 'NOT SET')}")

try:
    client = Client()
    print("✓ Client initialized")

    # Create a simple run using RunTree (avoids multipart)
    run = RunTree(
        name="basic_connection_test",
        run_type="chain",
        inputs={"message": "Testing basic trace upload"},
        project_name=os.getenv("LANGCHAIN_PROJECT", "code-chef-production"),
        extra={
            "metadata": {"test_type": "basic_connection", "timestamp": "2025-12-23"}
        },
    )

    run.end(outputs={"status": "success", "message": "Basic trace test completed"})
    run.post()

    print("✓ Trace posted successfully!")
    print(f"Check LangSmith project '{os.getenv('LANGCHAIN_PROJECT')}' for the trace")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback

    traceback.print_exc()
