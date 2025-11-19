"""Code review node implementation backed by the shared service layer."""

from __future__ import annotations

from langchain_core.messages import HumanMessage
from pydantic import ValidationError
import sys
from pathlib import Path

# Add agent_code-review to path (hyphens not allowed in Python imports)
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "agent_code-review"))
from service import (
    CodeDiff,
    GuardrailViolation,
    ReviewRequest,
    process_review_request,
)
sys.path.pop(0)
from services.langgraph.state import AgentState, ensure_agent_state

from .base import agent_response


async def code_review_node(state: AgentState) -> AgentState:
    """Execute the real code review workflow via the shared service layer."""

    normalized = ensure_agent_state(state)
    description = normalized["task_description"]

    latest_diff_request = next(
        (msg for msg in reversed(normalized["messages"]) if isinstance(msg, HumanMessage)),
        None,
    )
    fallback_changes = latest_diff_request.content if latest_diff_request else description

    review_request: ReviewRequest
    request_payload = normalized.get("code_review_request")
    if request_payload:
        try:
            review_request = ReviewRequest.model_validate(request_payload)
        except ValidationError:
            review_request = ReviewRequest(
                task_id=request_payload.get("task_id") or normalized.get("linear_issue_id") or "code-review-task",
                diffs=[
                    CodeDiff(
                        file_path=request_payload.get("diff_file", "workspace/diff.patch"),
                        changes=request_payload.get("changes", fallback_changes),
                        context_lines=request_payload.get("context_lines", 5),
                    )
                ],
                test_results=request_payload.get("test_results"),
            )
    else:
        review_request = ReviewRequest(
            task_id=normalized.get("linear_issue_id") or "code-review-task",
            diffs=[
                CodeDiff(
                    file_path="workspace/diff.patch",
                    changes=fallback_changes,
                    context_lines=5,
                )
            ],
        )

    try:
        response = await process_review_request(review_request)
        critical_count = sum(1 for finding in response.findings if finding.severity == "critical")
        content = (
            f"[code-review] Review {response.review_id} {response.status}. "
            f"Findings: {len(response.findings)} (critical={critical_count})."
        )

        update = agent_response(normalized, agent_name="code-review", content=content)
        update["code_review_request"] = review_request.model_dump(mode="json")
        update["code_review_response"] = response.model_dump(mode="json")
        return update
    except GuardrailViolation as exc:
        content = (
            "[code-review] Guardrails blocked the review workflow. "
            f"Status: {exc.report.status}."
        )
        update = agent_response(normalized, agent_name="code-review", content=content)
        update["guardrail_report"] = exc.report.model_dump(mode="json")
        return update
    except Exception as exc:  # noqa: BLE001
        content = (
            f"[code-review] Encountered an error while reviewing '{description}': {exc}."
        )
        update = agent_response(normalized, agent_name="code-review", content=content)
        update["error"] = str(exc)
        return update
