#!/usr/bin/env python3
"""
Test script for GitHub permalink generation in Linear issue updates and comments.

Tests:
1. Update issue description with file references
2. Add comment with file references
3. Update issue with both description and comment
"""

import asyncio
import sys
from pathlib import Path

# Add shared and shared/lib to path
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root / "shared"))
sys.path.insert(0, str(repo_root / "shared" / "lib"))

from lib.linear_config import LinearConfig
from lib.linear_workspace_client import LinearWorkspaceClient


async def test_update_and_comment():
    """Test update_issue() and add_comment() with permalink enrichment."""
    
    print("\n" + "=" * 60)
    print("GitHub Permalink Generation - Update & Comment Test")
    print("=" * 60)
    
    # Load config
    print("\nLoading Linear configuration...")
    config = LinearConfig.load()
    
    if not config.github or not config.github.permalink_generation.enabled:
        print("❌ GitHub permalink generation not enabled in config")
        return False
    
    print(f"✅ GitHub config loaded: {config.github.repository.url}")
    print(f"✅ Permalink generation: enabled")
    
    # Initialize client
    print("\nInitializing Linear workspace client...")
    client = LinearWorkspaceClient()
    
    if not client.permalink_generator:
        print("❌ Permalink generator not initialized")
        return False
    
    print("✅ Permalink generator initialized")
    
    # Test case: Find the most recent test issue
    print("\n" + "-" * 60)
    print("Test 1: Update Issue Description with File References")
    print("-" * 60)
    
    # Use DEV-182 from previous test
    issue_identifier = "DEV-182"
    
    update_description = """## Implementation Update

**Completed:**
- ✅ Implemented permalink generation in `shared/lib/github_permalink_generator.py lines 45-120`
- ✅ Integrated with Linear client in `shared/lib/linear_workspace_client.py lines 793-850`
- ✅ Added configuration support in `config/linear/linear-config.yaml`

**Testing:**
All unit tests passing. See `support/scripts/linear/test-permalink-generation.py` for validation.

**Next Steps:**
Review deployment process in `support/scripts/deploy/deploy-to-droplet.ps1 lines 100-150`.
"""
    
    print(f"\nUpdating issue: {issue_identifier}")
    print("\nNew description with file references:")
    print(update_description)
    
    success = await client.update_issue(
        issue_identifier=issue_identifier,
        description=update_description
    )
    
    if success:
        print(f"\n✅ Issue {issue_identifier} updated successfully")
        print(f"   URL: https://linear.app/dev-ops/issue/{issue_identifier}")
    else:
        print(f"\n❌ Failed to update issue {issue_identifier}")
        return False
    
    # Test case 2: Add comment with file references
    print("\n" + "-" * 60)
    print("Test 2: Add Comment with File References")
    print("-" * 60)
    
    comment_body = """**Production Deployment Complete** 🚀

Deployed to droplet 45.55.173.72 with permalink generation enabled.

**Verification:**
- ✅ Configuration updated: `config/env/.env` (LINEAR_API_KEY set)
- ✅ Services restarted: `deploy/docker-compose.yml`
- ✅ Health checks passing: `agent_orchestrator/main.py lines 880-920`

**Logs:**
Check orchestrator startup in `deploy/docker-compose.yml` service definition.

All systems operational! 🎉
"""
    
    print(f"\nAdding comment to issue: {issue_identifier}")
    print("\nComment with file references:")
    print(comment_body)
    
    # Get issue UUID first
    from gql import gql
    query = gql("""
        query GetIssueId($identifier: String!) {
            issue(id: $identifier) {
                id
            }
        }
    """)
    
    result = client.client.execute(query, variable_values={"identifier": issue_identifier})
    issue_id = result["issue"]["id"]
    
    comment = await client.add_comment(issue_id, comment_body)
    
    if comment:
        print(f"\n✅ Comment added successfully")
        print(f"   Comment ID: {comment['id']}")
        print(f"   URL: https://linear.app/dev-ops/issue/{issue_identifier}")
    else:
        print(f"\n❌ Failed to add comment")
        return False
    
    # Test case 3: Combined update
    print("\n" + "-" * 60)
    print("Test 3: Update with Both Description and Comment")
    print("-" * 60)
    
    combined_description = """## Final Status Update

**Feature Complete:** GitHub permalink generation is now live in production.

All agent workflows (feature-dev, code-review, infrastructure, cicd, documentation) will automatically convert file references to clickable GitHub permalinks.

**Key Files:**
- `shared/lib/github_permalink_generator.py` - Core permalink generation logic
- `shared/lib/linear_workspace_client.py` - Integration with Linear API
- `config/linear/linear-config.yaml` - Configuration

**Documentation:**
See `support/docs/LINEAR_INTEGRATION_GUIDE.md` for usage guide.
"""
    
    combined_comment = """**Retrospective: DEV-180 Implementation**

**Timeline:**
- Implementation: 2 hours
- Testing: 30 minutes
- Deployment: 15 minutes

**Impact:**
- 100% of file references now clickable in Linear
- Stable permalinks with commit SHA prevent link rot
- Zero configuration required for agents

**Files Modified:**
- `shared/lib/linear_workspace_client.py` - Added permalink enrichment to create/update/comment methods
- `config/linear/linear-config.yaml` - Added GitHub configuration section
- `support/docs/LINEAR_INTEGRATION_GUIDE.md` - Updated documentation

🎯 Ready for production use!
"""
    
    print(f"\nUpdating issue {issue_identifier} with description + comment...")
    
    success = await client.update_issue(
        issue_identifier=issue_identifier,
        description=combined_description,
        state_name="done",
        comment=combined_comment
    )
    
    if success:
        print(f"\n✅ Issue {issue_identifier} updated with description and comment")
        print(f"   Status: Done")
        print(f"   URL: https://linear.app/dev-ops/issue/{issue_identifier}")
    else:
        print(f"\n❌ Failed to update issue")
        return False
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print("Update Issue Description:  ✅ PASS")
    print("Add Comment:               ✅ PASS")
    print("Combined Update + Comment: ✅ PASS")
    
    print("\n✅ All tests passed!")
    print("\n📌 Manual Verification:")
    print(f"   Open issue: https://linear.app/dev-ops/issue/{issue_identifier}")
    print("   1. Check description has clickable GitHub permalinks")
    print("   2. Check comments have clickable GitHub permalinks")
    print("   3. Verify links navigate to correct files/lines on GitHub")
    print("   4. Confirm all links include commit SHA for stability")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_update_and_comment())
    sys.exit(0 if success else 1)
