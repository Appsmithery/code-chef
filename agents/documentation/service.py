"""Shared business logic for the Documentation agent."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from agents._shared.gradient_client import get_gradient_client
from agents._shared.guardrail import GuardrailOrchestrator, GuardrailReport, GuardrailStatus
from agents._shared.mcp_client import MCPClient

logger = logging.getLogger(__name__)

mcp_client = MCPClient(agent_name="documentation")
gradient_client = get_gradient_client("documentation")
guardrail_orchestrator = GuardrailOrchestrator()


class DocRequest(BaseModel):
    """Documentation generation request payload."""

    task_id: str
    doc_type: str = Field(..., description="readme, api-docs, guide, comments")
    context_refs: Optional[List[str]] = None
    target_audience: str = Field(default="developers")


class DocArtifact(BaseModel):
    """Generated documentation artifact."""

    file_path: str
    content: str
    doc_type: str


class DocResponse(BaseModel):
    """Documentation agent response payload."""

    doc_id: str
    artifacts: List[DocArtifact]
    estimated_tokens: int
    template_used: Optional[str] = None
    guardrail_report: GuardrailReport
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GuardrailViolation(Exception):
    """Raised when documentation guardrails block generation."""

    def __init__(self, report: GuardrailReport):
        super().__init__("Guardrail checks failed")
        self.report = report


def list_doc_templates() -> Dict[str, List[Dict[str, str]]]:
    """Expose documentation templates for API consumers."""

    return {
        "templates": [
            {"name": "readme-standard", "sections": ["overview", "installation", "usage", "api"]},
            {"name": "api-docs-openapi", "format": "OpenAPI 3.0"},
            {"name": "guide-tutorial", "style": "step-by-step"},
        ]
    }


def generate_docs(request: DocRequest) -> List[DocArtifact]:
    """Placeholder documentation generator until RAG + LLM wiring completes."""

    return [
        DocArtifact(
            file_path="README.md",
            content="# Generated Documentation\n\n<!-- Production: Replace with LLM-generated documentation -->",
            doc_type=request.doc_type,
        )
    ]


async def process_doc_request(
    request: DocRequest,
    *,
    doc_id: Optional[str] = None,
) -> DocResponse:
    """Execute guardrail checks and generate documentation artifacts."""

    doc_id = doc_id or str(uuid.uuid4())

    guardrail_report = await guardrail_orchestrator.run(
        "documentation",
        task_id=request.task_id or doc_id,
        context={
            "endpoint": "generate",
            "doc_type": request.doc_type,
        },
    )

    if guardrail_orchestrator.should_block_failures and guardrail_report.status == GuardrailStatus.FAILED:
        raise GuardrailViolation(guardrail_report)

    artifacts = generate_docs(request)

    response = DocResponse(
        doc_id=doc_id,
        artifacts=artifacts,
        estimated_tokens=len(request.doc_type) * 100,
        template_used=f"{request.doc_type}-standard",
        guardrail_report=guardrail_report,
    )

    await mcp_client.log_event(
        "documentation_generated",
        metadata={
            "doc_id": doc_id,
            "task_id": request.task_id,
            "doc_type": request.doc_type,
            "artifact_count": len(artifacts),
            "target_audience": request.target_audience,
            "guardrail_report_id": guardrail_report.report_id,
            "guardrail_status": guardrail_report.status,
            "llm_enabled": gradient_client.is_enabled(),
        },
    )

    return response
