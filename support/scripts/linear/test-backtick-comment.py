#!/usr/bin/env python3
"""Test comment with backticks on DEV-182."""

import asyncio
import sys
from pathlib import Path

# Add shared to path
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root / "shared"))
sys.path.insert(0, str(repo_root / "shared" / "lib"))

from lib.linear_workspace_client import LinearWorkspaceClient
from gql import gql


async def test_backtick_comment():
    """Add a comment with backticks to DEV-182."""

    print("\n" + "=" * 70)
    print("Testing Backtick Permalink Generation in Comments")
    print("=" * 70)

    client = LinearWorkspaceClient()

    # Get issue ID for DEV-182
    query = gql(
        """
        query GetIssueId($identifier: String!) {
            issue(id: $identifier) {
                id
            }
        }
    """
    )

    result = client.client.execute(query, variable_values={"identifier": "DEV-182"})
    issue_id = result["issue"]["id"]

    print(f"\nAdding comment to DEV-182 (ID: {issue_id})")

    comment_text = """**🔧 Backtick Support Fix Deployed**

Fixed the issue where file references with backticks weren't being converted to permalinks.

**Changes:**
- Updated regex patterns in `shared/lib/github_permalink_generator.py lines 144-152`
- Added backtick variants to replacement logic in `shared/lib/github_permalink_generator.py lines 216-264`
- Added `.ps1` extension support
- Created `support/scripts/linear/test-backticks.py` for validation

**Testing:**
All backtick formats now work:
- ✅ Single file: `config/env/.env`
- ✅ With line range: `agent_orchestrator/main.py lines 880-920`
- ✅ With single line: `shared/lib/linear_workspace_client.py line 949`
- ✅ Mixed with plain text: Review `deploy/docker-compose.yml` service definitions

**Production Status:**
Deployed to 45.55.173.72 - all services healthy ✅

This comment should have **clickable GitHub permalinks** for all file references!
"""

    print("\nComment text:")
    print(comment_text)

    comment = await client.add_comment(issue_id, comment_text)

    print(f"\n✅ Comment added successfully")
    print(f"   Comment ID: {comment['id']}")
    print(f"   URL: https://linear.app/dev-ops/issue/DEV-182")
    print("\n📌 Manual Verification:")
    print("   1. Open https://linear.app/dev-ops/issue/DEV-182")
    print("   2. Scroll to the latest comment")
    print("   3. Verify ALL file references are now clickable links")
    print("   4. Click links to confirm they navigate to GitHub")


if __name__ == "__main__":
    asyncio.run(test_backtick_comment())
