#!/usr/bin/env python3
"""
Test GitHub Permalink Generation in Linear Issues

Tests the automatic permalink generation feature for Linear issues.
Validates that file references in issue descriptions are converted to clickable GitHub permalinks.

Usage:
    # Set environment variable
    $env:LINEAR_API_KEY="lin_oauth_***"

    # Run test
    python support/scripts/linear/test-permalink-generation.py

Expected Behavior:
    - Creates test issue with file references
    - File references should be converted to GitHub permalinks
    - Permalinks should include commit SHA for stability
    - Permalinks should be clickable in Linear UI
"""

import os
import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "shared"))

from lib.linear_workspace_client import LinearWorkspaceClient
from lib.linear_config import get_linear_config


async def test_permalink_generation():
    """Test permalink generation in Linear issue creation."""

    print("\n" + "=" * 60)
    print("GitHub Permalink Generation Test")
    print("=" * 60 + "\n")

    # Load configuration
    print("Loading Linear configuration...")
    config = get_linear_config()

    if not config.github:
        print("❌ GitHub configuration not found in linear-config.yaml")
        print("   Please ensure github section is configured.")
        return False

    if not config.github.permalink_generation.enabled:
        print("❌ GitHub permalink generation is disabled")
        print("   Set github.permalink_generation.enabled: true in linear-config.yaml")
        return False

    print(f"✅ GitHub config loaded: {config.github.repository.url}")
    print(
        f"✅ Permalink generation: {'enabled' if config.github.permalink_generation.enabled else 'disabled'}"
    )
    print(f"✅ Default branch: {config.github.permalink_generation.default_branch}")
    print(
        f"✅ Include commit SHA: {config.github.permalink_generation.include_commit_sha}"
    )

    # Initialize client
    print("\nInitializing Linear workspace client...")
    client = LinearWorkspaceClient()

    if not client.permalink_generator:
        print("❌ Permalink generator not initialized")
        return False

    print("✅ Permalink generator initialized")

    # Test 1: Create issue with file references
    print("\n" + "-" * 60)
    print("Test 1: Create Issue with File References")
    print("-" * 60 + "\n")

    test_description = """
This is a test issue to validate GitHub permalink generation.

**File References to Convert:**
- Review agent_orchestrator/main.py lines 45-67
- Check shared/lib/linear_workspace_client.py line 123
- Update config/linear/linear-config.yaml
- Fix bug in shared/lib/github_permalink_generator.py lines 200-250

**Expected Behavior:**
All file references above should be converted to clickable GitHub permalinks with commit SHA.
"""

    print("Creating test issue with file references...")
    print(f"Original description:\n{test_description}\n")

    try:
        issue = await client.create_issue_from_template(
            template_id=config.templates["task_orchestrator"].uuid,
            template_variables={
                "test_type": "Permalink Generation",
                "description": test_description,
                "expected_result": "File references converted to GitHub permalinks",
            },
            title_override="[TEST] GitHub Permalink Generation Validation",
            team_id=config.workspace.team_id,
            assignee_id=config.default_assignee.id,
            label_ids=[config.labels.orchestrator],
        )

        print(f"✅ Issue created: {issue['identifier']}")
        print(f"   URL: {issue['url']}")
        print(f"   Title: {issue['title']}")

        print("\n📋 Manual Verification Steps:")
        print(f"   1. Open issue in Linear: {issue['url']}")
        print("   2. Check that file references are clickable links")
        print("   3. Verify links point to GitHub with commit SHA")
        print("   4. Click links to confirm they navigate to correct files/lines")

        return True

    except Exception as e:
        print(f"❌ Failed to create test issue: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_manual_permalink_generation():
    """Test manual permalink generation (without creating Linear issue)."""

    print("\n" + "-" * 60)
    print("Test 2: Manual Permalink Generation")
    print("-" * 60 + "\n")

    config = get_linear_config()
    client = LinearWorkspaceClient()

    if not client.permalink_generator:
        print("❌ Permalink generator not available")
        return False

    test_cases = [
        {
            "description": "Review agent_orchestrator/main.py lines 45-67",
            "expected": "Permalink with line range L45-L67",
        },
        {
            "description": "Check shared/lib/mcp_client.py line 123",
            "expected": "Permalink with single line L123",
        },
        {
            "description": "Update config/linear/linear-config.yaml",
            "expected": "Permalink to file (no line numbers)",
        },
    ]

    print("Testing permalink generation on sample descriptions:\n")

    for i, test_case in enumerate(test_cases, 1):
        print(f"Test Case {i}:")
        print(f"  Input:    {test_case['description']}")

        try:
            enriched = client.permalink_generator.enrich_markdown_with_permalinks(
                test_case["description"]
            )
            print(f"  Output:   {enriched}")
            print(f"  Expected: {test_case['expected']}")

            if "https://github.com" in enriched:
                print("  Status:   ✅ PASS - Permalink generated")
            else:
                print("  Status:   ❌ FAIL - No permalink found")

        except Exception as e:
            print(f"  Status:   ❌ ERROR - {e}")

        print()

    return True


async def main():
    """Run all tests."""

    # Check environment
    if not os.getenv("LINEAR_API_KEY"):
        print("❌ LINEAR_API_KEY environment variable not set")
        print('   Set it with: $env:LINEAR_API_KEY="lin_oauth_***"')
        sys.exit(1)

    # Run tests
    try:
        # Test manual generation first (no Linear API calls)
        success1 = await test_manual_permalink_generation()

        # Test actual issue creation
        success2 = await test_permalink_generation()

        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        print(f"Manual Permalink Generation: {'✅ PASS' if success1 else '❌ FAIL'}")
        print(f"Linear Issue Creation:       {'✅ PASS' if success2 else '❌ FAIL'}")
        print()

        if success1 and success2:
            print("✅ All tests passed!")
            print("\n📌 Next Steps:")
            print("   1. Open the created Linear issue and verify permalinks")
            print("   2. Test with feature-dev agent workflow")
            print("   3. Mark DEV-180 as complete")
            return 0
        else:
            print("❌ Some tests failed. See output above for details.")
            return 1

    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
