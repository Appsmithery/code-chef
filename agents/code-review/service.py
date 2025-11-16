"""Shared business logic for the Code Review agent."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from agents._shared.gradient_client import get_gradient_client
from agents._shared.guardrail import GuardrailOrchestrator, GuardrailReport, GuardrailStatus
from agents._shared.mcp_client import MCPClient

logger = logging.getLogger(__name__)

mcp_client = MCPClient(agent_name="code-review")
gradient_client = get_gradient_client("code-review")
guardrail_orchestrator = GuardrailOrchestrator()


class CodeDiff(BaseModel):
    """Represents a single diff chunk submitted for review."""

    file_path: str
    changes: str
    context_lines: int = Field(default=5, ge=0, le=50)


class ReviewRequest(BaseModel):
    """Review request payload passed between services."""

    task_id: str
    diffs: List[CodeDiff]
    test_results: Optional[Dict[str, Any]] = None


class ReviewFinding(BaseModel):
    """Represents an issue identified during review."""

    severity: str
    category: str
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None


class ReviewResponse(BaseModel):
    """Structured output returned by the code review workflow."""

    review_id: str
    status: str
    findings: List[ReviewFinding]
    approval: bool
    summary: str
    estimated_tokens: int
    guardrail_report: GuardrailReport
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GuardrailViolation(Exception):
    """Raised when guardrails fail and are configured to block execution."""

    def __init__(self, report: GuardrailReport):
        super().__init__("Guardrail checks failed")
        self.report = report


def analyze_diffs(diffs: List[CodeDiff]) -> List[ReviewFinding]:
    """Very small heuristic analyzer until LLM integration is enabled."""

    findings: List[ReviewFinding] = []
    for diff in diffs:
        if "TODO" in diff.changes:
            findings.append(
                ReviewFinding(
                    severity="medium",
                    category="style",
                    message="TODOs should be resolved before merge",
                    file_path=diff.file_path,
                )
            )
        if "print(" in diff.changes:
            findings.append(
                ReviewFinding(
                    severity="low",
                    category="debug",
                    message="Remove debug print statements",
                    file_path=diff.file_path,
                )
            )
    return findings


async def process_review_request(
    request: ReviewRequest,
    *,
    review_id: Optional[str] = None,
) -> ReviewResponse:
    """Execute guardrails, run analysis, and emit standardized review results."""

    review_id = review_id or str(uuid.uuid4())

    guardrail_report = await guardrail_orchestrator.run(
        "code-review",
        task_id=request.task_id or review_id,
        context={
            "endpoint": "review",
            "diff_count": len(request.diffs),
        },
    )

    if guardrail_orchestrator.should_block_failures and guardrail_report.status == GuardrailStatus.FAILED:
        raise GuardrailViolation(guardrail_report)

    findings = analyze_diffs(request.diffs)
    critical_findings = [finding for finding in findings if finding.severity == "critical"]
    approval = not critical_findings
    token_estimate = sum(len(diff.changes.split()) * 2 for diff in request.diffs)

    response = ReviewResponse(
        review_id=review_id,
        status="approved" if approval else "revision_required",
        findings=findings,
        approval=approval,
        summary=f"Found {len(findings)} issue(s), {len(critical_findings)} critical",
        estimated_tokens=token_estimate,
        guardrail_report=guardrail_report,
    )

    await mcp_client.log_event(
        "code_review_completed",
        metadata={
            "review_id": review_id,
            "task_id": request.task_id,
            "finding_count": len(findings),
            "critical_findings": len(critical_findings),
            "approved": approval,
            "guardrail_report_id": guardrail_report.report_id,
            "guardrail_status": guardrail_report.status,
            "llm_enabled": gradient_client.is_enabled(),
        },
    )

    return response
