"""Shared business logic for the Code Review agent."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from lib.gradient_client import get_gradient_client
from lib.guardrail import GuardrailOrchestrator, GuardrailReport, GuardrailStatus
from lib.mcp_client import MCPClient

logger = logging.getLogger(__name__)

mcp_client = MCPClient(agent_name="code-review")
gradient_client = get_gradient_client("code-review")
guardrail_orchestrator = GuardrailOrchestrator()


class ReviewRequest(BaseModel):
    """Code review request payload."""

    diff_content: str = Field(..., description="Git diff or code changes to review")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    task_id: Optional[str] = Field(default=None, description="Parent task ID from orchestrator")


class ReviewIssue(BaseModel):
    """Individual code review issue."""

    severity: str = Field(..., description="critical, warning, info")
    category: str = Field(..., description="security, style, logic, performance")
    line_number: Optional[int] = None
    message: str
    suggestion: Optional[str] = None


class ReviewResponse(BaseModel):
    """Code review response."""

    review_id: str
    status: str = Field(..., description="approved, needs_changes, rejected")
    issues: List[ReviewIssue]
    summary: str
    quality_score: float = Field(..., ge=0.0, le=100.0)
    guardrail_report: GuardrailReport
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GuardrailViolation(Exception):
    """Raised when guardrail enforcement blocks code review."""

    def __init__(self, report: GuardrailReport):
        super().__init__("Guardrail checks failed")
        self.report = report


async def analyze_code_with_llm(
    request: ReviewRequest,
    review_id: str,
) -> List[ReviewIssue]:
    """Analyze code using Gradient AI with LangSmith tracing."""

    system_prompt = """You are an expert code reviewer. Analyze the provided code diff for:
- Security vulnerabilities
- Code quality issues
- Performance problems
- Style violations
- Logic errors

Return your response as JSON with this structure:
{
  "issues": [
    {
      "severity": "critical|warning|info",
      "category": "security|style|logic|performance",
      "line_number": 42,
      "message": "Description of the issue",
      "suggestion": "How to fix it"
    }
  ]
}"""

    user_prompt = f"""Review this code diff:

```diff
{request.diff_content}
```

Context: {request.context or 'General code review'}

Provide detailed analysis with actionable suggestions."""

    try:
        logger.info("[Code-Review] Attempting LLM-powered code analysis for review %s", review_id)
        result = await gradient_client.complete_structured(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=2000,
            metadata={
                "task_id": review_id,
                "diff_size": len(request.diff_content),
            },
        )

        logger.info(
            "[Code-Review] LLM analysis successful: %s tokens used",
            result.get("tokens", 0),
        )

        llm_issues = result["content"].get("issues", [])
        issues = [
            ReviewIssue(
                severity=issue["severity"],
                category=issue["category"],
                line_number=issue.get("line_number"),
                message=issue["message"],
                suggestion=issue.get("suggestion"),
            )
            for issue in llm_issues
        ]

        return issues
    except Exception as exc:  # noqa: BLE001
        logger.error("[Code-Review] LLM analysis failed: %s", exc, exc_info=True)
        return [
            ReviewIssue(
                severity="info",
                category="general",
                message="Code review completed (LLM unavailable, using basic analysis)",
            )
        ]


def calculate_quality_score(issues: List[ReviewIssue]) -> float:
    """Calculate overall quality score from issues."""

    if not issues:
        return 100.0

    severity_weights = {"critical": 30, "warning": 10, "info": 3}
    total_penalty = sum(severity_weights.get(issue.severity, 5) for issue in issues)

    return max(0.0, 100.0 - total_penalty)


async def process_review_request(
    request: ReviewRequest,
    *,
    review_id: Optional[str] = None,
) -> ReviewResponse:
    """Execute the code review workflow and return the response payload."""

    review_id = review_id or str(uuid.uuid4())

    guardrail_report = await guardrail_orchestrator.run(
        "code-review",
        task_id=request.task_id or review_id,
        context={"endpoint": "review", "diff_size": len(request.diff_content)},
    )

    if guardrail_orchestrator.should_block_failures and guardrail_report.status == GuardrailStatus.FAILED:
        raise GuardrailViolation(guardrail_report)

    if gradient_client.is_enabled():
        issues = await analyze_code_with_llm(request, review_id)
    else:
        issues = [
            ReviewIssue(
                severity="info",
                category="general",
                message="Code review completed (LLM disabled, basic analysis only)",
            )
        ]

    quality_score = calculate_quality_score(issues)
    critical_issues = [i for i in issues if i.severity == "critical"]

    if critical_issues:
        status = "rejected"
        summary = f"Found {len(critical_issues)} critical issues that must be addressed"
    elif len(issues) > 5:
        status = "needs_changes"
        summary = f"Found {len(issues)} issues that should be addressed"
    else:
        status = "approved"
        summary = "Code quality meets standards" if issues else "No issues found"

    response = ReviewResponse(
        review_id=review_id,
        status=status,
        issues=issues,
        summary=summary,
        quality_score=quality_score,
        guardrail_report=guardrail_report,
    )

    await mcp_client.log_event(
        "code_reviewed",
        metadata={
            "review_id": review_id,
            "issue_count": len(issues),
            "status": status,
            "quality_score": quality_score,
            "llm_enabled": gradient_client.is_enabled(),
            "guardrail_report_id": guardrail_report.report_id,
            "guardrail_status": guardrail_report.status,
        },
    )

    return response
