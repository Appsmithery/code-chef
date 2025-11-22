#!/usr/bin/env python3
"""
Test reaction processing by creating a fresh HITL approval comment.

Usage:
    python test_reaction_processing.py

Then manually react with 👍 in Linear to test the workflow.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add shared lib to path
shared_lib = Path(__file__).parent / "shared" / "lib"
sys.path.insert(0, str(shared_lib))
sys.path.insert(0, str(Path(__file__).parent / "shared"))

from lib.linear_workspace_client import LinearWorkspaceClient


async def create_test_approval():
    """Create a test HITL approval request in DEV-68."""

    # Initialize Linear client
    client = LinearWorkspaceClient()

    print("Creating test approval comment in DEV-68...")

    try:
        comment = await client.create_approval_comment(
            agent_name="test-reaction-processing",
            task_description=(
                "Testing the newly implemented `_handle_reaction_event()` method to ensure:\n"
                "- Reaction.create events are properly routed\n"
                "- 👍 emoji triggers workflow resumption\n"
                "- 👎 emoji triggers workflow cancellation\n"
                "- Confirmation comments are posted back to Linear"
            ),
            risk_level="low",
            approval_id="test-reaction-001",
            metadata={
                "test_purpose": "Validate Reaction webhook processing",
                "expected_behavior": [
                    "Reaction webhook sent to orchestrator",
                    "_handle_reaction_event() parses reaction",
                    "Approval confirmation comment posted",
                    "Workflow resumes (when LangGraph integration complete)",
                ],
            },
        )

        comment_id = comment.get("comment_id")
        comment_url = comment.get("url")

        print(f"✅ Test approval created successfully!")
        print(f"   Comment ID: {comment_id}")
        print(f"   URL: {comment_url}")
        print()
        print("Next steps:")
        print("1. Open the comment in Linear")
        print("2. React with 👍 to test approval workflow")
        print("3. Check orchestrator logs for reaction processing")
        print()
        print("Expected behavior:")
        print("- Reaction webhook will be sent to orchestrator")
        print("- _handle_reaction_event() will parse the reaction")
        print("- Approval confirmation comment will be posted")
        print("- Workflow will resume (when LangGraph integration complete)")

        return comment

    except Exception as e:
        print(f"❌ Failed to create approval comment: {e}")
        import traceback

        traceback.print_exc()
        return None


async def main():
    """Main entry point."""

    # Check for Linear API key
    api_key = os.getenv("LINEAR_API_KEY")
    if not api_key:
        print("❌ LINEAR_API_KEY environment variable not set")
        print("   Set with: $env:LINEAR_API_KEY='lin_oauth_...'")
        return 1

    await create_test_approval()
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
