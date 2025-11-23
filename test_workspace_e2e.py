"""
End-to-End Test: Workspace-Aware Linear Project Auto-Creation

Simulates the full workflow:
1. Extension extracts workspace context (GitHub URL, commit SHA, project ID)
2. Orchestrator receives task with project_context
3. Orchestrator auto-creates Linear project (or finds existing)
4. Orchestrator enriches description with GitHub permalinks
5. Orchestrator returns project info to extension
"""

import asyncio
import json
from datetime import datetime

# Test configuration
ORCHESTRATOR_URL = "http://45.55.173.72:8001"
TEST_WORKSPACE = f"test-workspace-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
TEST_GITHUB_REPO = "https://github.com/Appsmithery/Dev-Tools"
TEST_COMMIT_SHA = "9f75ed7"  # Current commit with import fix


async def test_workspace_aware_workflow():
    """Test complete workspace-aware workflow against production."""
    import aiohttp

    print("=" * 60)
    print("E2E Test: Workspace-Aware Linear Project Auto-Creation")
    print("=" * 60)

    # Step 1: Simulate extension context extraction
    print("\n[1] Extension Context Extraction (simulated)")
    workspace_context = {
        "workspace_name": TEST_WORKSPACE,
        "github_repo_url": TEST_GITHUB_REPO,
        "github_commit_sha": TEST_COMMIT_SHA,
        "linear_project_id": None,  # First time - no cached project
    }
    print(f"   Workspace: {workspace_context['workspace_name']}")
    print(f"   GitHub Repo: {workspace_context['github_repo_url']}")
    print(f"   Commit SHA: {workspace_context['github_commit_sha']}")
    print(f"   Cached Project ID: {workspace_context['linear_project_id']}")

    # Step 2: Send task to orchestrator with workspace context
    print("\n[2] Sending Task to Orchestrator")
    task_payload = {
        "description": "Add JWT authentication to the REST API endpoints",
        "priority": "medium",
        "project_context": workspace_context,
    }

    async with aiohttp.ClientSession() as session:
        try:
            print(f"   POST {ORCHESTRATOR_URL}/orchestrate")
            async with session.post(
                f"{ORCHESTRATOR_URL}/orchestrate",
                json=task_payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"   ❌ FAIL: HTTP {resp.status}")
                    print(f"   Error: {error_text}")
                    return False

                result = await resp.json()
                print(f"   ✅ OK: HTTP {resp.status}")
        except Exception as e:
            print(f"   ❌ FAIL: {type(e).__name__}: {e}")
            return False

    # Step 3: Validate response structure
    print("\n[3] Validating Response Structure")
    print(f"   Received fields: {list(result.keys())}")
    expected_fields = ["task_id", "workspace_context", "linear_project"]

    for field in expected_fields:
        if field in result:
            print(f"   ✅ {field}: Present")
        else:
            print(f"   ❌ {field}: MISSING")
            return False

    # Step 4: Validate workspace context in response
    print("\n[4] Validating Workspace Context")
    returned_context = result.get("workspace_context", {})

    if returned_context.get("workspace_name") == TEST_WORKSPACE:
        print(f"   ✅ workspace_name: {returned_context['workspace_name']}")
    else:
        print(
            f"   ❌ workspace_name mismatch: {returned_context.get('workspace_name')}"
        )
        return False

    if returned_context.get("github_repo_url") == TEST_GITHUB_REPO:
        print(f"   ✅ github_repo_url: {returned_context['github_repo_url']}")
    else:
        print(
            f"   ❌ github_repo_url mismatch: {returned_context.get('github_repo_url')}"
        )
        return False

    # Step 5: Validate Linear project creation
    print("\n[5] Validating Linear Project Auto-Creation")
    linear_project = result.get("linear_project", {})

    if not linear_project:
        print("   ❌ linear_project: Empty or missing")
        return False

    project_id = linear_project.get("id")
    project_name = linear_project.get("name")
    project_url = linear_project.get("url")

    if project_id:
        print(f"   ✅ Project ID: {project_id}")
    else:
        print("   ❌ Project ID: MISSING")
        return False

    if project_name:
        print(f"   ✅ Project Name: {project_name}")
    else:
        print("   ❌ Project Name: MISSING")
        return False

    if project_url:
        print(f"   ✅ Project URL: {project_url}")
    else:
        print("   ⚠️  Project URL: Missing (non-critical)")

    # Step 6: Validate GitHub permalink enrichment (check subtasks)
    print("\n[6] Validating GitHub Permalink Enrichment")
    subtasks = result.get("subtasks", [])

    if not subtasks:
        print("   ⚠️  No subtasks generated (task may be simple)")
    else:
        print(f"   Found {len(subtasks)} subtasks")

        # Check if any descriptions contain GitHub permalinks
        permalink_found = False
        for i, subtask in enumerate(subtasks[:3], 1):  # Check first 3
            description = subtask.get("description", "")
            if "github.com" in description.lower():
                print(f"   ✅ Subtask {i}: Contains GitHub permalink")
                permalink_found = True
            else:
                print(f"   ℹ️  Subtask {i}: No permalink (may not reference code)")

        if not permalink_found:
            print("   ⚠️  No GitHub permalinks found (task may not reference code)")

    # Step 7: Simulate extension caching project ID
    print("\n[7] Extension Project ID Caching (simulated)")
    cached_project_id = project_id
    print(f"   Extension would save to .vscode/settings.json:")
    print(f"   'devtools.linearProjectId': '{cached_project_id}'")

    # Step 8: Test idempotency - send same task again
    print("\n[8] Testing Idempotency (2nd Request with Cached Project ID)")
    task_payload_2nd = {
        "description": "Add rate limiting to JWT endpoints",
        "priority": "medium",
        "project_context": {
            "workspace_name": TEST_WORKSPACE,
            "github_repo_url": TEST_GITHUB_REPO,
            "github_commit_sha": TEST_COMMIT_SHA,
            "linear_project_id": cached_project_id,  # Now cached
        },
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{ORCHESTRATOR_URL}/orchestrate",
                json=task_payload_2nd,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"   ❌ FAIL: HTTP {resp.status}")
                    print(f"   Error: {error_text}")
                    return False

                result_2nd = await resp.json()
                print(f"   ✅ OK: HTTP {resp.status}")
        except Exception as e:
            print(f"   ❌ FAIL: {type(e).__name__}: {e}")
            return False

    # Validate 2nd request used cached project
    linear_project_2nd = result_2nd.get("linear_project", {})
    if linear_project_2nd.get("id") == cached_project_id:
        print(f"   ✅ Project ID matched cached: {cached_project_id}")
        print("   ✅ Idempotency verified: Same project reused")
    else:
        print(
            f"   ❌ Project ID mismatch: {linear_project_2nd.get('id')} != {cached_project_id}"
        )
        return False

    # Final summary
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
    print(f"\nLinear Project Created:")
    print(f"   Name: {project_name}")
    print(f"   ID: {project_id}")
    print(f"   URL: {project_url or 'N/A'}")
    print(f"\nWorkspace: {TEST_WORKSPACE}")
    print(f"GitHub Repo: {TEST_GITHUB_REPO}")

    return True


async def test_health_endpoints():
    """Quick health check before full test."""
    import aiohttp

    print("\n[Pre-Test] Checking Service Health")
    services = [
        ("Gateway", "http://45.55.173.72:8000/health"),
        ("Orchestrator", "http://45.55.173.72:8001/health"),
        ("RAG", "http://45.55.173.72:8007/health"),
        ("State", "http://45.55.173.72:8008/health"),
    ]

    all_healthy = True
    async with aiohttp.ClientSession() as session:
        for name, url in services:
            try:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=5)
                ) as resp:
                    if resp.status == 200:
                        print(f"   ✅ {name}: Healthy")
                    else:
                        print(f"   ❌ {name}: HTTP {resp.status}")
                        all_healthy = False
            except Exception as e:
                print(f"   ❌ {name}: {type(e).__name__}")
                all_healthy = False

    return all_healthy


if __name__ == "__main__":

    async def main():
        # Health check
        if not await test_health_endpoints():
            print("\n❌ Services not healthy. Aborting test.")
            return

        # Full E2E test
        success = await test_workspace_aware_workflow()

        if not success:
            print("\n❌ TEST FAILED")
            exit(1)

        print("\n✅ TEST SUITE COMPLETE")

    asyncio.run(main())
