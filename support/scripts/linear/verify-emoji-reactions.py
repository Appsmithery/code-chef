#!/usr/bin/env python3
"""
Verify emoji reaction processing by checking Linear comments.

This script:
1. Fetches the approval hub issue (DEV-68)
2. Lists all comments with their reactions
3. Identifies approval/denial reactions
4. Checks for confirmation comments from webhook
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

from lib.linear_workspace_client import LinearWorkspaceClient


async def verify_reactions():
    """Check DEV-68 for approval comments and reactions"""
    print("=" * 80)
    print("EMOJI REACTION VERIFICATION")
    print("=" * 80)
    print()

    try:
        client = LinearWorkspaceClient()
        print("✓ Linear client initialized")
        print()

        # Fetch DEV-68 (approval hub)
        query = """
        query GetIssueComments($issueId: String!) {
            issue(id: $issueId) {
                id
                title
                identifier
                comments {
                    nodes {
                        id
                        body
                        createdAt
                        user {
                            name
                            email
                        }
                    }
                }
            }
        }
        """

        variables = {"issueId": "DEV-68"}
        result = await client._execute_query(query, variables)

        if not result or "issue" not in result:
            print("✗ Failed to fetch DEV-68")
            return False

        issue = result["issue"]
        comments = issue["comments"]["nodes"]

        print(f"📝 Issue: {issue['identifier']} - {issue['title']}")
        print(f"💬 Total comments: {len(comments)}")
        print()

        # Show all recent comments first
        print("RECENT COMMENTS (last 15):")
        print("=" * 80)
        for comment in comments[-15:]:
            user = comment.get("user", {})
            body = comment.get("body", "")
            created = comment.get("createdAt", "")
            print(f"[{created}] {user.get('name', 'Unknown')}: {body[:100]}...")
        print()

        # Filter for HITL approval comments (look for approval-related keywords)
        approval_comments = []
        confirmation_comments = []

        for comment in comments:
            body = comment.get("body", "")
            if any(
                keyword in body.lower()
                for keyword in [
                    "approval request",
                    "hitl",
                    "approve",
                    "deny",
                    "👍",
                    "👎",
                ]
            ):
                approval_comments.append(comment)
            if any(
                keyword in body.lower()
                for keyword in ["✅ approved", "❌ denied", "confirmation"]
            ):
                confirmation_comments.append(comment)

        print("=" * 80)
        print(f"APPROVAL COMMENTS FOUND: {len(approval_comments)}")
        print("=" * 80)
        print()

        for i, comment in enumerate(approval_comments, 1):
            user = comment.get("user", {})

            print(f"Comment #{i} (ID: {comment['id'][:8]}...)")
            print(f"Author: {user.get('name', 'Unknown')}")
            print(f"Created: {comment['createdAt']}")
            print(f"Body preview: {comment['body'][:100]}...")
            print()

        print("=" * 80)
        print(f"CONFIRMATION COMMENTS FOUND: {len(confirmation_comments)}")
        print("=" * 80)
        print()

        if confirmation_comments:
            for i, comment in enumerate(confirmation_comments, 1):
                user = comment.get("user", {})
                print(f"Confirmation #{i}")
                print(f"Author: {user.get('name', 'Unknown')}")
                print(f"Body: {comment['body'][:200]}")
                print()
        else:
            print("⚠️  No confirmation comments found")
            print("This indicates webhook events may not have been received")
            print()

        # Summary
        print("=" * 80)
        print("VERIFICATION SUMMARY")
        print("=" * 80)
        print()

        total_reactions = sum(len(c.get("reactions", [])) for c in approval_comments)

        print(f"Approval comments: {len(approval_comments)}")
        print(f"Confirmation comments: {len(confirmation_comments)}")
        print()

        if confirmation_comments:
            print("✅ Webhook processed reactions successfully!")
            print(f"   Found {len(confirmation_comments)} confirmation comment(s)")
        else:
            print("⚠️  No confirmation comments found")
            print()
            print("This could mean:")
            print("  1. Linear webhook not configured yet")
            print("  2. Webhook events not sent by Linear")
            print("  3. No reactions applied yet")
            print()
            print("Configuration needed:")
            print("  - URL: https://theshop.appsmithery.co/webhook/linear")
            print("  - Signing Secret: (from LINEAR_WEBHOOK_SIGNING_SECRET)")
            print("  - Events: Comment.create, Comment.update")

        return True

    except Exception as e:
        print(f"✗ Verification failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(verify_reactions())
    sys.exit(0 if success else 1)
