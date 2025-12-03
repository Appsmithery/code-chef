#!/usr/bin/env python3
"""
Test emoji reaction-based HITL approval flow.

This script validates:
1. High-priority approval comment creation
2. Emoji reaction instructions visible
3. Comment posted to DEV-68 approval hub
4. Webhook integration ready

Usage:
    python support/scripts/linear/test-emoji-approval.py
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Add shared/lib to Python path
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root / "shared"))

# Load .env file
env_path = repo_root / "config" / "env" / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✓ Loaded environment from: {env_path}\n")
else:
    print(f"✗ ERROR: .env file not found at {env_path}")
    sys.exit(1)

from lib.linear_config import get_linear_config
from lib.linear_workspace_client import LinearWorkspaceClient


async def test_high_priority_approval():
    """Test creating high-priority approval with emoji reactions"""
    print("=" * 80)
    print("TEST: High-Priority HITL Approval with Emoji Reactions")
    print("=" * 80)
    print()

    try:
        # Initialize client
        client = LinearWorkspaceClient()
        print(f"✓ Linear client initialized")
        print(f"  Webhook URL: {os.getenv('LINEAR_WEBHOOK_URL')}")
        print(
            f"  Webhook configured: {bool(os.getenv('LINEAR_WEBHOOK_SIGNING_SECRET'))}"
        )
        print()

        # Create high-priority approval comment
        print("Creating HIGH-PRIORITY approval comment...")
        print()

        approval_data = await client.create_approval_comment(
            agent_name="orchestrator",
            task_description="Deploy emoji reaction-based HITL approval system to production",
            risk_level="high",
            approval_id="emoji-approval-test-001",
            metadata={
                "risk_factors": [
                    "New webhook endpoint deployment",
                    "Emoji reaction processing logic",
                    "Linear API integration changes",
                    "Production orchestrator restart",
                ],
                "estimated_cost": 500,
                "deployment_target": "codechef.appsmithery.co (production)",
            },
        )

        print("✅ Approval comment created successfully!")
        print()
        print(f"📝 Comment ID: {approval_data['comment_id']}")
        print(f"📍 Issue: {approval_data['issue_id']}")
        print(f"🔗 URL: {approval_data['url']}")
        print()

        print("=" * 80)
        print("NEXT STEPS")
        print("=" * 80)
        print()
        print("1. Open the comment in Linear:")
        print(f"   {approval_data['url']}")
        print()
        print("2. React with an emoji:")
        print("   👍 - Approve (workflow resumes)")
        print("   👎 - Deny (workflow cancels)")
        print("   💬 - Reply (request more info)")
        print()
        print("3. Watch the orchestrator logs for webhook events:")
        print(
            '   ssh do-mcp-gateway "docker logs deploy-orchestrator-1 -f | grep -i webhook"'
        )
        print()
        print("4. The webhook will:")
        print("   - Detect your emoji reaction")
        print("   - Resume/cancel the workflow automatically")
        print("   - Add a confirmation comment")
        print()

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_medium_priority_approval():
    """Test creating medium-priority approval"""
    print("\n" + "=" * 80)
    print("TEST: Medium-Priority HITL Approval")
    print("=" * 80)
    print()

    try:
        client = LinearWorkspaceClient()

        approval_data = await client.create_approval_comment(
            agent_name="feature-dev",
            task_description="Update Linear configuration docs with emoji reaction flow",
            risk_level="medium",
            approval_id="emoji-approval-test-002",
            metadata={
                "risk_factors": [
                    "Documentation update",
                    "Workflow diagram changes",
                ],
                "estimated_cost": 150,
            },
        )

        print("✅ Medium-priority approval comment created")
        print(f"🔗 URL: {approval_data['url']}")
        print()

        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False


async def main():
    """Run all approval tests"""
    print("\n" + "=" * 80)
    print("EMOJI REACTION APPROVAL - PRODUCTION TEST")
    print("=" * 80)
    print()

    results = []

    # Test 1: High-priority approval
    high_priority_ok = await test_high_priority_approval()
    results.append(("High-Priority Approval", high_priority_ok))

    # Test 2: Medium-priority approval
    medium_priority_ok = await test_medium_priority_approval()
    results.append(("Medium-Priority Approval", medium_priority_ok))

    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name:.<50} {status}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        print("\nApproval comments are now live in DEV-68.")
        print("Go approve or deny them with emoji reactions!")
        return 0
    else:
        print(f"\n⚠ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
