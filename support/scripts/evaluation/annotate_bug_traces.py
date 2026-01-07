"""Annotate bug traces with fix details for tracking and regression testing.

Run after fixing bugs to document which traces exposed the issues.
"""

import os

from langsmith import Client

# Initialize client (uses LANGCHAIN_API_KEY from environment)
client = Client()

# Traces that exposed bugs fixed in commit 7179f69
bug_traces = [
    {
        "trace_id": "019b9631-483c-7c03-8657-43a26864822d",
        "error_type": "json_validation",
        "description": "Pydantic ValidationError: Invalid JSON trailing characters",
        "root_cause": "Supervisor returning JSON + conversational text when invoked via supervisor_node with with_structured_output()",
        "fix": "Reverted system.prompt.md to JSON-only output; lowered confidence threshold to 0.65 for direct conversational routing",
    },
    {
        "trace_id": "9b23f75a-1e98-4b89-89b2-69fb458475d3",
        "error_type": "models_yaml_path",
        "description": "FileNotFoundError: Models config not found: /config/agents/models.yaml",
        "root_cause": "deployment.py path resolution going up 5 levels instead of 4, reaching filesystem root / instead of /app",
        "fix": "Changed base_path calculation from 5 parent levels to 4",
    },
]

print("Annotating bug traces with fix details...")
print("=" * 80)

for trace_info in bug_traces:
    trace_id = trace_info["trace_id"]

    try:
        # Update trace with metadata
        client.update_run(
            run_id=trace_id,
            tags=[
                "bug:fixed",
                f"error:{trace_info['error_type']}",
                "commit:7179f69",
                "date:2026-01-06",
            ],
            extra={
                "bug_report": {
                    "error_type": trace_info["error_type"],
                    "description": trace_info["description"],
                    "root_cause": trace_info["root_cause"],
                    "fix": trace_info["fix"],
                    "fixed_in_commit": "7179f69",
                    "commit_url": "https://github.com/Appsmithery/code-chef/commit/7179f69",
                    "date_fixed": "2026-01-06",
                }
            },
        )

        print(f"✅ Annotated trace: {trace_id}")
        print(f"   Error: {trace_info['error_type']}")
        print(f"   Description: {trace_info['description'][:60]}...")
        print()

    except Exception as e:
        print(f"❌ Failed to annotate trace {trace_id}: {e}")
        print()

print("=" * 80)
print("Annotation complete!")
print("\nNext steps:")
print("1. Add these traces to 'error-cases-regression-suite' dataset")
print("2. Run evaluation to verify fixes worked")
print("3. View annotated traces in LangSmith UI with 'bug:fixed' tag filter")
