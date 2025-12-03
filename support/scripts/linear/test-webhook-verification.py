#!/usr/bin/env python3
"""
Create a fresh approval request and wait for webhook confirmation.
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root / "shared"))

env_path = repo_root / "config" / "env" / ".env"
load_dotenv(env_path)

from lib.linear_workspace_client import LinearWorkspaceClient


async def create_test_approval():
    """Create a test approval with webhook verification instructions"""
    client = LinearWorkspaceClient()

    print("Creating test approval for webhook verification...")
    print()

    approval_data = await client.create_approval_comment(
        agent_name="orchestrator",
        task_description="Verify Linear webhook integration with emoji reaction system",
        risk_level="low",
        approval_id="webhook-test-" + str(int(asyncio.get_event_loop().time())),
        metadata={
            "test_type": "webhook_integration",
            "expected_behavior": "Webhook should trigger on emoji reaction",
            "verification_steps": [
                "React with 👍 to approve",
                "Check orchestrator logs for webhook POST",
                "Verify confirmation comment appears",
            ],
        },
    )

    print("✅ Test approval created!")
    print()
    print(f"🔗 URL: {approval_data['url']}")
    print(f"📝 Comment ID: {approval_data['comment_id']}")
    print()
    print("=" * 80)
    print("VERIFICATION STEPS")
    print("=" * 80)
    print()
    print("1. Open the comment in Linear:")
    print(f"   {approval_data['url']}")
    print()
    print("2. React with 👍 emoji")
    print()
    print("3. Watch orchestrator logs (run in separate terminal):")
    print(
        '   ssh do-mcp-gateway "docker logs deploy-orchestrator-1 -f | grep -i webhook"'
    )
    print()
    print("4. Expected webhook flow:")
    print("   - Linear sends POST to /webhooks/linear")
    print("   - Orchestrator verifies HMAC signature")
    print("   - Webhook processor detects 👍 reaction")
    print("   - Confirmation comment posted back to Linear")
    print()


if __name__ == "__main__":
    asyncio.run(create_test_approval())
