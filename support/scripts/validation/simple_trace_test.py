"""
Simple LangSmith Trace Generation

Validates that LangSmith tracing is working with proper metadata.
Runs independently without requiring full code-chef orchestrator.

Usage: python simple_trace_test.py
"""

import os
import time
from langsmith import Client, traceable

# Configure LangSmith
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "code-chef-production"

# Configure metadata
TRACE_METADATA = {
    "environment": "manual-validation",
    "experiment_group": "code-chef",
    "extension_version": "2.0.0",
    "model_version": "qwen-2.5-coder-7b-test",
    "test_type": "simple_validation"
}

print("\n" + "="*80)
print("SIMPLE LANGSMITH TRACE VALIDATION")
print("="*80)
print(f"\nEnvironment Variables:")
print(f"  LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2')}")
print(f"  LANGCHAIN_API_KEY: {'✓ Set' if os.getenv('LANGCHAIN_API_KEY') else '✗ NOT SET'}")
print(f"  LANGCHAIN_PROJECT: {os.getenv('LANGCHAIN_PROJECT')}")
print(f"\nTrace Metadata:")
for key, value in TRACE_METADATA.items():
    print(f"  {key}: {value}")

# Check if LangSmith is configured
if not os.getenv("LANGCHAIN_API_KEY"):
    print("\n❌ ERROR: LANGCHAIN_API_KEY not set")
    print("Please set it in your environment or config/env/.env file")
    exit(1)

# Initialize client
try:
    client = Client()
    print("\n✓ LangSmith client initialized successfully")
except Exception as e:
    print(f"\n❌ Failed to initialize LangSmith client: {e}")
    exit(1)


@traceable(name="test_scenario")
def run_test_scenario(scenario_name: str, message: str):
    """Simulate intent recognition scenario."""
    # Attach metadata to run
    from langsmith import get_current_run_tree
    run = get_current_run_tree()
    if run:
        run.extra = {
            **TRACE_METADATA,
            "scenario_name": scenario_name,
            "message": message
        }
    
    print(f"\n{'='*80}")
    print(f"Testing: {scenario_name}")
    print(f"Message: {message}")
    print(f"{'='*80}")
    
    # Simulate intent recognition
    time.sleep(0.1)  # Simulate processing
    
    # Simulate compressed prompt usage (metadata tracking)
    prompt_tokens = 320  # Compressed vs 800 baseline
    completion_tokens = 50
    
    result = {
        "intent": "task_submission",
        "confidence": 0.92,
        "agent": "feature_dev",
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "baseline_tokens": 850,  # What it would have been without optimization
        "savings_pct": ((850 - 370) / 850) * 100
    }
    
    print(f"\n✓ Results:")
    print(f"  Intent: {result['intent']}")
    print(f"  Confidence: {result['confidence']:.2f}")
    print(f"  Agent: {result['agent']}")
    print(f"  Tokens Used: {result['total_tokens']} (vs {result['baseline_tokens']} baseline)")
    print(f"  Token Savings: {result['savings_pct']:.1f}%")
    
    return result


# Test scenarios
test_cases = [
    {
        "name": "High Confidence Feature Request",
        "message": "Implement JWT authentication middleware with refresh tokens"
    },
    {
        "name": "Code Review Task",
        "message": "Review authentication logic in src/auth/login.py for security issues"
    },
    {
        "name": "Infrastructure Deployment",
        "message": "Deploy application to Kubernetes with horizontal pod autoscaling"
    },
    {
        "name": "CI/CD Setup",
        "message": "Configure GitHub Actions workflow for automated testing"
    },
    {
        "name": "Documentation Request",
        "message": "Create API documentation for user authentication endpoints"
    }
]

print("\n" + "="*80)
print(f"Running {len(test_cases)} test scenarios...")
print("="*80)

results = []
for i, test in enumerate(test_cases, 1):
    print(f"\n[{i}/{len(test_cases)}]")
    result = run_test_scenario(
        scenario_name=test["name"],
        message=test["message"]
    )
    results.append(result)
    time.sleep(0.5)  # Brief pause between tests

# Summary
print("\n" + "="*80)
print("VALIDATION SUMMARY")
print("="*80)

total_tokens = sum(r["total_tokens"] for r in results)
baseline_tokens = sum(r["baseline_tokens"] for r in results)
total_savings = ((baseline_tokens - total_tokens) / baseline_tokens) * 100

print(f"\n✓ All {len(results)} scenarios completed successfully")
print(f"\nToken Usage:")
print(f"  Total Used: {total_tokens}")
print(f"  Baseline (without optimization): {baseline_tokens}")
print(f"  Total Savings: {total_savings:.1f}%")

# LangSmith information
print(f"\n" + "="*80)
print("VIEW TRACES IN LANGSMITH")
print("="*80)
print(f"\n🔗 https://smith.langchain.com/")
print(f"\nProject: {os.getenv('LANGCHAIN_PROJECT')}")
print(f"Filter: environment:\"manual-validation\" AND test_type:\"simple_validation\"")
print(f"Time Range: Last 5 minutes")

print(f"\n📋 What to verify in traces:")
print(f"  1. All {len(results)} traces visible")
print(f"  2. Metadata includes: environment, experiment_group, extension_version, model_version")
print(f"  3. Each trace shows scenario_name and message")
print(f"  4. Token usage information captured")
print(f"  5. Traces are in code-chef-production project")

print("\n" + "="*80)
print("✓ Validation Complete")
print("="*80 + "\n")
