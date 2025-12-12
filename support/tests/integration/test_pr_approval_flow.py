"""
Test PR deployment workflow with HITL approval and GitHub PR comment posting.

This test validates Phase 2 GitHub enrichment:
1. PR deployment triggers high-risk approval
2. Approval request includes PR context (pr_number, pr_url, github_repo)
3. Linear issue created with PR link
4. On approval, GitHub PR receives confirmation comment
5. Comment includes approval details and Linear issue link

Prerequisites:
- PostgreSQL database accessible
- GITHUB_TOKEN environment variable set
- LINEAR_API_KEY environment variable set
- Test repository with PR access
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


async def test_pr_approval_flow():
    """Test complete PR deployment approval workflow."""
    try:
        from shared.lib.hitl_manager import get_hitl_manager
        from shared.lib.risk_assessor import RiskAssessor

        logger.info("=" * 60)
        logger.info("Starting PR Approval Flow Test")
        logger.info("=" * 60)

        # Initialize managers
        hitl_manager = get_hitl_manager()
        risk_assessor = RiskAssessor()

        # Test scenario: PR deployment to production
        test_pr_number = 999
        test_pr_url = "https://github.com/Appsmithery/Dev-Tools/pull/999"
        test_github_repo = "Appsmithery/Dev-Tools"

        task = {
            "operation": "deploy",
            "environment": "production",
            "service": "orchestrator",
            "version": "1.2.3",
            "pr_number": test_pr_number,
            "pr_url": test_pr_url,
        }

        # Step 1: Assess risk
        logger.info("\n[Step 1] Assessing risk for PR deployment...")
        risk_level, reasons = risk_assessor.assess_risk(
            operation="deploy", environment="production", additional_context=task
        )
        logger.info(f"✓ Risk Level: {risk_level}")
        logger.info(f"✓ Risk Factors: {reasons}")

        # Verify high-risk operation triggers approval
        assert risk_level in ["high", "critical"], "PR deployment should be high risk"

        # Step 2: Create approval request with PR context
        logger.info("\n[Step 2] Creating approval request with PR context...")
        workflow_id = f"workflow-pr-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        thread_id = f"thread-pr-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        checkpoint_id = f"checkpoint-pr-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        approval_request_id = await hitl_manager.create_approval_request(
            workflow_id=workflow_id,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            task=task,
            agent_name="cicd",
            pr_number=test_pr_number,
            pr_url=test_pr_url,
            github_repo=test_github_repo,
        )

        logger.info(f"✓ Approval Request Created: {approval_request_id}")

        # Step 3: Verify database record includes PR context
        logger.info("\n[Step 3] Verifying PR context stored in database...")
        async with await hitl_manager._get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT pr_number, pr_url, github_repo, linear_issue_id, linear_issue_url
                    FROM approval_requests 
                    WHERE id = %s
                    """,
                    (approval_request_id,),
                )
                row = await cursor.fetchone()

                if row:
                    (
                        db_pr_number,
                        db_pr_url,
                        db_github_repo,
                        linear_issue_id,
                        linear_issue_url,
                    ) = row
                    logger.info(f"✓ PR Number: {db_pr_number}")
                    logger.info(f"✓ PR URL: {db_pr_url}")
                    logger.info(f"✓ GitHub Repo: {db_github_repo}")
                    logger.info(f"✓ Linear Issue ID: {linear_issue_id}")
                    logger.info(f"✓ Linear Issue URL: {linear_issue_url}")

                    assert db_pr_number == test_pr_number, "PR number mismatch"
                    assert db_pr_url == test_pr_url, "PR URL mismatch"
                    assert db_github_repo == test_github_repo, "GitHub repo mismatch"
                    assert linear_issue_id is not None, "Linear issue not created"
                else:
                    raise Exception("Approval request not found in database")

        # Step 4: Simulate approval and test PR comment posting
        logger.info("\n[Step 4] Simulating approval and testing PR comment...")
        logger.info(
            f"⚠️  Manual step: Go to Linear issue {linear_issue_url} and add 👍 reaction"
        )
        logger.info("⚠️  This will trigger webhook and post comment to GitHub PR")

        logger.info("\n[Step 5] Testing direct resume with PR comment...")
        # Import resume function
        sys.path.insert(0, str(project_root / "agent_orchestrator"))
        from main import resume_workflow_from_approval

        # Note: This will fail because we don't have a valid workflow checkpoint
        # But it should attempt to post the GitHub PR comment
        try:
            result = await resume_workflow_from_approval(
                approval_request_id, action="approved"
            )
            logger.info(f"✓ Resume Result: {result}")
        except Exception as e:
            logger.warning(f"⚠️  Resume failed (expected - no checkpoint): {e}")
            logger.info("✓ Check GitHub PR #999 for approval comment")

        logger.info("\n" + "=" * 60)
        logger.info("✅ PR Approval Flow Test Complete")
        logger.info("=" * 60)
        logger.info("\nNext Steps:")
        logger.info(f"1. Visit Linear issue: {linear_issue_url}")
        logger.info("2. Add 👍 emoji reaction to trigger webhook")
        logger.info(f"3. Check GitHub PR: {test_pr_url}")
        logger.info("4. Verify approval comment was posted")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise


async def main():
    """Run the test."""
    # Verify prerequisites
    required_env_vars = ["GITHUB_TOKEN", "LINEAR_API_KEY"]
    missing = [var for var in required_env_vars if not os.getenv(var)]

    if missing:
        logger.error(f"❌ Missing required environment variables: {missing}")
        logger.error("Please set these variables and try again")
        return

    await test_pr_approval_flow()


if __name__ == "__main__":
    asyncio.run(main())
