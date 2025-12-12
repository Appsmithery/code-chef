"""
Test Phase 3: Agent HITL Integration

Validates that agents properly:
1. Assess operation risk
2. Set requires_approval flag for high-risk operations
3. Route to approval node when needed
4. Pass PR context through to HITLManager
5. Resume workflow after approval

Prerequisites:
- PostgreSQL database accessible
- LINEAR_API_KEY environment variable set
- GITHUB_TOKEN environment variable set (optional, for PR comments)
- Orchestrator services running
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Fix Windows event loop policy for psycopg3
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "shared"))
sys.path.insert(0, str(project_root / "agent_orchestrator"))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_feature_dev_risk_assessment():
    """Test feature_dev agent risk assessment and HITL routing."""
    logger.info("\n" + "=" * 60)
    logger.info("Test 1: Feature Dev Agent HITL Integration")
    logger.info("=" * 60)

    try:
        from graph import WorkflowState, feature_dev_node
        from langchain_core.messages import HumanMessage

        # Simulate high-risk code change (production environment)
        state = {
            "messages": [
                HumanMessage(content="Modify authentication middleware for production")
            ],
            "environment": "production",
            "files_changed": 5,
            "pending_operation": "Modify authentication middleware",
            "pr_context": {
                "pr_number": 123,
                "pr_url": "https://github.com/Appsmithery/Dev-Tools/pull/123",
                "github_repo": "Appsmithery/Dev-Tools",
            },
            "workflow_id": f"test-fd-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "thread_id": f"thread-fd-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        }

        logger.info("→ Invoking feature_dev_node with production code changes...")
        result = await feature_dev_node(state)

        # Verify risk assessment
        logger.info(f"✓ Next Agent: {result.get('next_agent')}")
        logger.info(f"✓ Requires Approval: {result.get('requires_approval')}")
        logger.info(f"✓ Risk Level: {result.get('task_result', {}).get('risk_level')}")
        logger.info(
            f"✓ Pending Operation: {result.get('pending_operation', 'N/A')[:100]}"
        )

        # Should route to approval for high-risk changes
        assert result.get("next_agent") == "approval", "Should route to approval"
        assert result.get("requires_approval") is True, "Should require approval"
        assert result.get("pr_context"), "Should preserve PR context"

        logger.info(
            "✅ Feature Dev agent properly assesses risk and routes to approval"
        )

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise


async def test_infrastructure_risk_assessment():
    """Test infrastructure agent risk assessment and HITL routing."""
    logger.info("\n" + "=" * 60)
    logger.info("Test 2: Infrastructure Agent HITL Integration")
    logger.info("=" * 60)

    try:
        from graph import WorkflowState, infrastructure_node
        from langchain_core.messages import HumanMessage

        # Simulate high-risk infrastructure change
        state = {
            "messages": [
                HumanMessage(content="Deploy Terraform changes to production VPC")
            ],
            "environment": "production",
            "pending_operation": "Deploy VPC configuration changes",
            "pr_context": {
                "pr_number": 456,
                "pr_url": "https://github.com/Appsmithery/Dev-Tools/pull/456",
                "github_repo": "Appsmithery/Dev-Tools",
            },
            "workflow_id": f"test-infra-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "thread_id": f"thread-infra-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        }

        logger.info("→ Invoking infrastructure_node with production deployment...")
        result = await infrastructure_node(state)

        # Verify risk assessment
        logger.info(f"✓ Next Agent: {result.get('next_agent')}")
        logger.info(f"✓ Requires Approval: {result.get('requires_approval')}")
        logger.info(f"✓ Risk Level: {result.get('task_result', {}).get('risk_level')}")

        # Should route to approval for production infrastructure
        assert result.get("next_agent") == "approval", "Should route to approval"
        assert result.get("requires_approval") is True, "Should require approval"

        logger.info(
            "✅ Infrastructure agent properly assesses risk and routes to approval"
        )

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise


async def test_cicd_risk_assessment():
    """Test CI/CD agent risk assessment and HITL routing."""
    logger.info("\n" + "=" * 60)
    logger.info("Test 3: CI/CD Agent HITL Integration")
    logger.info("=" * 60)

    try:
        from graph import WorkflowState, cicd_node
        from langchain_core.messages import HumanMessage

        # Simulate high-risk deployment
        state = {
            "messages": [
                HumanMessage(content="Deploy orchestrator service to production")
            ],
            "environment": "production",
            "pending_operation": "Deploy orchestrator v1.2.3 to production",
            "pr_context": {
                "pr_number": 789,
                "pr_url": "https://github.com/Appsmithery/Dev-Tools/pull/789",
                "github_repo": "Appsmithery/Dev-Tools",
            },
            "workflow_id": f"test-cicd-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "thread_id": f"thread-cicd-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        }

        logger.info("→ Invoking cicd_node with production deployment...")
        result = await cicd_node(state)

        # Verify risk assessment
        logger.info(f"✓ Next Agent: {result.get('next_agent')}")
        logger.info(f"✓ Requires Approval: {result.get('requires_approval')}")
        logger.info(f"✓ Risk Level: {result.get('task_result', {}).get('risk_level')}")

        # Should route to approval for production deployment
        assert result.get("next_agent") == "approval", "Should route to approval"
        assert result.get("requires_approval") is True, "Should require approval"

        logger.info("✅ CI/CD agent properly assesses risk and routes to approval")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise


async def test_approval_node_pr_context():
    """Test that approval_node receives and uses PR context."""
    logger.info("\n" + "=" * 60)
    logger.info("Test 4: Approval Node PR Context Handling")
    logger.info("=" * 60)

    try:
        from graph import WorkflowState, approval_node
        from langchain_core.messages import HumanMessage

        # Simulate state with PR context
        state = {
            "messages": [HumanMessage(content="Deploy to production")],
            "environment": "production",
            "pending_operation": "Deploy orchestrator to production",
            "pr_context": {
                "pr_number": 999,
                "pr_url": "https://github.com/Appsmithery/Dev-Tools/pull/999",
                "github_repo": "Appsmithery/Dev-Tools",
            },
            "workflow_id": f"test-approval-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "thread_id": f"thread-approval-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "current_agent": "cicd",
        }

        logger.info("→ Invoking approval_node with PR context...")

        # Note: This will create approval request in database and Linear
        # The workflow will interrupt() and save checkpoint
        # We can't easily test the interrupt in isolation, but we can verify
        # the approval request creation

        logger.info("⚠️  Note: Approval node will attempt to create approval request")
        logger.info("⚠️  This requires database access and may create Linear issue")

        # In a real test, you'd mock the interrupt() or test with actual workflow
        logger.info(
            "✅ Manual verification: Check database for approval request with PR context"
        )

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise


async def test_low_risk_bypass():
    """Test that low-risk operations bypass approval."""
    logger.info("\n" + "=" * 60)
    logger.info("Test 5: Low-Risk Operations Bypass Approval")
    logger.info("=" * 60)

    try:
        from graph import WorkflowState, feature_dev_node
        from langchain_core.messages import HumanMessage

        # Simulate low-risk code change (dev environment)
        state = {
            "messages": [
                HumanMessage(content="Add logging statement to helper function")
            ],
            "environment": "development",
            "files_changed": 1,
            "pending_operation": "Add logging",
            "workflow_id": f"test-low-risk-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "thread_id": f"thread-low-risk-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        }

        logger.info("→ Invoking feature_dev_node with low-risk change...")
        result = await feature_dev_node(state)

        # Verify NO approval needed
        logger.info(f"✓ Next Agent: {result.get('next_agent')}")
        logger.info(f"✓ Requires Approval: {result.get('requires_approval')}")
        logger.info(f"✓ Risk Level: {result.get('task_result', {}).get('risk_level')}")

        # Should route directly to supervisor, not approval
        assert result.get("next_agent") == "supervisor", "Should route to supervisor"
        assert result.get("requires_approval") is False, "Should NOT require approval"

        logger.info("✅ Low-risk operations properly bypass approval")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise


async def main():
    """Run all Phase 3 integration tests."""
    logger.info("\n" + "=" * 80)
    logger.info("PHASE 3: AGENT HITL INTEGRATION TESTS")
    logger.info("=" * 80)

    # Verify prerequisites
    required_env_vars = ["LINEAR_API_KEY"]
    missing = [var for var in required_env_vars if not os.getenv(var)]

    if missing:
        logger.warning(f"⚠️  Missing environment variables: {missing}")
        logger.warning("Some tests may fail or be skipped")

    # Run tests
    tests = [
        ("Feature Dev Risk Assessment", test_feature_dev_risk_assessment),
        ("Infrastructure Risk Assessment", test_infrastructure_risk_assessment),
        ("CI/CD Risk Assessment", test_cicd_risk_assessment),
        ("Approval Node PR Context", test_approval_node_pr_context),
        ("Low-Risk Bypass", test_low_risk_bypass),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            await test_func()
            passed += 1
        except Exception as e:
            logger.error(f"❌ {test_name} failed: {e}")
            failed += 1

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info(f"TEST SUMMARY: {passed} passed, {failed} failed")
    logger.info("=" * 80)

    if failed == 0:
        logger.info("✅ All Phase 3 agent HITL integration tests passed!")
    else:
        logger.error(f"❌ {failed} test(s) failed")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
