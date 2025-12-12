"""Phase 2: GitHub PR enrichment tests.

Tests GitHub PR context integration with HITL:
- PR comment posting on approval
- PR status check integration
- Multi-PR scenario handling
- GitHub API failure graceful degradation
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from shared.lib.hitl_manager import HITLManager


class TestPhase2GitHubEnrichment:
    """Test GitHub PR context integration with HITL."""

    @pytest.mark.asyncio
    @pytest.mark.hitl
    async def test_pr_comment_posting_on_approval(
        self, hitl_manager, mock_github_client
    ):
        """Test GitHub PR comment posted when approval granted."""
        # Create approval request with PR context
        request_id = await hitl_manager.create_approval_request(
            workflow_id="test-wf-001",
            thread_id="test-thread-001",
            checkpoint_id="test-cp-001",
            task={
                "operation": "deploy",
                "environment": "production",
                "description": "Deploy Redis cache to production",
            },
            agent_name="infrastructure",
            pr_number=142,
            pr_url="https://github.com/Appsmithery/Dev-Tools/pull/142",
            github_repo="Appsmithery/Dev-Tools",
        )

        assert request_id is not None

        # Mock approval
        with patch.object(hitl_manager, "github_client", mock_github_client):
            approval_result = await hitl_manager.approve_request(
                request_id=request_id,
                approver="tech-lead@example.com",
                comment="Approved for production deployment",
            )

            assert approval_result["status"] == "approved"

            # Verify PR comment posted
            mock_github_client.create_comment.assert_called_once()

            # Verify comment content
            call_args = mock_github_client.create_comment.call_args
            pr_number = call_args.kwargs.get("pr_number") or call_args[0][0]
            comment_body = call_args.kwargs.get("body") or call_args[0][1]

            assert pr_number == 142
            assert "Approval granted" in comment_body
            assert "CHEF-" in comment_body  # Linear issue ID
            assert "tech-lead@example.com" in comment_body

    @pytest.mark.asyncio
    @pytest.mark.hitl
    async def test_pr_status_check_integration(self, hitl_manager, mock_github_client):
        """Test GitHub PR status check updated with approval status."""
        # Create approval request with PR
        request_id = await hitl_manager.create_approval_request(
            workflow_id="test-wf-002",
            thread_id="test-thread-002",
            checkpoint_id="test-cp-002",
            task={
                "operation": "merge",
                "environment": "production",
                "description": "Merge security hotfix",
            },
            agent_name="infrastructure",
            pr_number=143,
            pr_url="https://github.com/Appsmithery/Dev-Tools/pull/143",
            github_repo="Appsmithery/Dev-Tools",
        )

        with patch.object(hitl_manager, "github_client", mock_github_client):
            # Verify status check created: "code-chef/approval" = "pending"
            initial_status_calls = mock_github_client.create_status.call_count

            # Approve request
            await hitl_manager.approve_request(
                request_id=request_id, approver="security-team@example.com"
            )

            # Verify status check updated: "code-chef/approval" = "success"
            assert mock_github_client.create_status.call_count > initial_status_calls

            # Get last status call
            last_call = mock_github_client.create_status.call_args
            status_context = last_call.kwargs.get("context") or last_call[0][1]
            status_state = last_call.kwargs.get("state") or last_call[0][2]

            assert status_context == "code-chef/approval"
            assert status_state == "success"

    @pytest.mark.asyncio
    @pytest.mark.hitl
    async def test_multi_pr_scenario_handling(self, hitl_manager, mock_github_client):
        """Test handling multiple PRs requiring approval simultaneously."""
        # Create 3 approval requests for different PRs
        pr_requests = []

        for i in range(3):
            pr_number = 200 + i
            request_id = await hitl_manager.create_approval_request(
                workflow_id=f"test-wf-{pr_number}",
                thread_id=f"test-thread-{pr_number}",
                checkpoint_id=f"test-cp-{pr_number}",
                task={
                    "operation": "deploy",
                    "environment": "production",
                    "description": f"Deploy changes from PR #{pr_number}",
                },
                agent_name="infrastructure",
                pr_number=pr_number,
                pr_url=f"https://github.com/Appsmithery/Dev-Tools/pull/{pr_number}",
                github_repo="Appsmithery/Dev-Tools",
            )

            pr_requests.append({"request_id": request_id, "pr_number": pr_number})

        # Verify each has correct PR context
        for req in pr_requests:
            approval_request = await hitl_manager.get_approval_request(
                req["request_id"]
            )
            assert approval_request["pr_number"] == req["pr_number"]
            assert f"pull/{req['pr_number']}" in approval_request["pr_url"]

        # Approve in different order (2, 0, 1)
        approval_order = [1, 0, 2]

        with patch.object(hitl_manager, "github_client", mock_github_client):
            for idx in approval_order:
                await hitl_manager.approve_request(
                    request_id=pr_requests[idx]["request_id"],
                    approver=f"approver-{idx}@example.com",
                )

        # Verify correct PR updated for each
        # Check all comment calls
        comment_calls = mock_github_client.create_comment.call_args_list
        assert len(comment_calls) == 3, "Expected 3 PR comments (one per approval)"

        # Verify each comment went to correct PR
        commented_pr_numbers = []
        for call in comment_calls:
            pr_number = call.kwargs.get("pr_number") or call[0][0]
            commented_pr_numbers.append(pr_number)

        # All 3 PRs should have received comments
        expected_prs = {200, 201, 202}
        assert (
            set(commented_pr_numbers) == expected_prs
        ), f"Expected comments on PRs {expected_prs}, got {commented_pr_numbers}"

    @pytest.mark.asyncio
    @pytest.mark.hitl
    async def test_github_api_failure_graceful_degradation(
        self, hitl_manager, mock_github_client_with_failures
    ):
        """Test graceful handling of GitHub API failures."""
        # Mock GitHub API to return 403 (rate limit)
        mock_github_client_with_failures.create_comment.side_effect = Exception(
            "GitHub API rate limit exceeded (403)"
        )

        # Create approval request with PR context
        request_id = await hitl_manager.create_approval_request(
            workflow_id="test-wf-ratelimit",
            thread_id="test-thread-ratelimit",
            checkpoint_id="test-cp-ratelimit",
            task={
                "operation": "deploy",
                "environment": "production",
                "description": "Deploy with rate-limited GitHub API",
            },
            agent_name="infrastructure",
            pr_number=999,
            pr_url="https://github.com/Appsmithery/Dev-Tools/pull/999",
            github_repo="Appsmithery/Dev-Tools",
        )

        # Verify approval still created despite GitHub API issues
        assert request_id is not None

        approval_request = await hitl_manager.get_approval_request(request_id)
        assert approval_request["status"] == "pending"

        # Approve with failing GitHub API
        with patch.object(
            hitl_manager, "github_client", mock_github_client_with_failures
        ):
            # This should NOT raise exception
            approval_result = await hitl_manager.approve_request(
                request_id=request_id, approver="approver@example.com"
            )

            # Verify approval succeeded
            assert approval_result["status"] == "approved"

        # Verify Linear issue still created
        approval_request = await hitl_manager.get_approval_request(request_id)
        assert approval_request["linear_issue_id"] is not None
        assert approval_request["linear_issue_id"].startswith("CHEF-")

        # Verify PR comment failure logged but not fatal
        # Check that workflow can continue despite GitHub failure
        assert approval_request["github_comment_posted"] is False
        assert "github_error" in approval_request.get("metadata", {})

    @pytest.mark.asyncio
    @pytest.mark.hitl
    async def test_pr_context_enrichment_in_linear_issue(
        self, hitl_manager, mock_linear_client, mock_github_client
    ):
        """Test Linear issue includes rich PR context."""
        # Create approval request with comprehensive PR context
        request_id = await hitl_manager.create_approval_request(
            workflow_id="test-wf-enrichment",
            thread_id="test-thread-enrichment",
            checkpoint_id="test-cp-enrichment",
            task={
                "operation": "deploy",
                "environment": "production",
                "description": "Deploy feature with PR context",
                "pr_context": {
                    "author": "developer@example.com",
                    "title": "Add Redis caching layer",
                    "branch": "feature/redis-cache",
                    "files_changed": 12,
                    "additions": 245,
                    "deletions": 38,
                },
            },
            agent_name="infrastructure",
            pr_number=144,
            pr_url="https://github.com/Appsmithery/Dev-Tools/pull/144",
            github_repo="Appsmithery/Dev-Tools",
        )

        with patch.object(hitl_manager, "linear_client", mock_linear_client):
            # Trigger Linear issue creation
            await hitl_manager._create_linear_approval_issue(request_id)

            # Verify Linear issue created
            assert mock_linear_client.create_issue.called

            # Verify issue includes PR context
            call_args = mock_linear_client.create_issue.call_args
            issue_description = call_args.kwargs.get("description")

            assert "PR #144" in issue_description
            assert "developer@example.com" in issue_description
            assert "Add Redis caching layer" in issue_description
            assert "feature/redis-cache" in issue_description
            assert "12 files" in issue_description


# Fixtures


@pytest.fixture
async def hitl_manager():
    """Provide HITLManager instance."""
    manager = HITLManager()
    yield manager

    # Cleanup
    # (HITLManager handles cleanup in production via database)


@pytest.fixture
def mock_github_client():
    """Provide mocked GitHub client."""
    client = Mock()
    client.create_comment = Mock(return_value={"id": "comment-123"})
    client.create_status = Mock(return_value={"state": "success"})
    client.get_pull_request = Mock(
        return_value={
            "number": 142,
            "title": "Test PR",
            "user": {"login": "developer"},
            "state": "open",
        }
    )
    return client


@pytest.fixture
def mock_github_client_with_failures():
    """Provide mocked GitHub client that simulates API failures."""
    client = Mock()
    client.create_comment = Mock(side_effect=Exception("Rate limit exceeded"))
    client.create_status = Mock(side_effect=Exception("Rate limit exceeded"))
    client.get_pull_request = Mock(side_effect=Exception("Rate limit exceeded"))
    return client


@pytest.fixture
def mock_linear_client():
    """Provide mocked Linear client."""
    client = Mock()
    client.create_issue = Mock(
        return_value={
            "id": "issue-abc123",
            "identifier": "CHEF-500",
            "url": "https://linear.app/dev-ops/issue/CHEF-500",
        }
    )
    client.update_issue = Mock(return_value={"id": "issue-abc123"})
    return client
