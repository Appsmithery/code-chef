"""Shared business logic for the Infrastructure agent."""

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

mcp_client = MCPClient(agent_name="infrastructure")
gradient_client = get_gradient_client("infrastructure")
guardrail_orchestrator = GuardrailOrchestrator()


class InfraRequest(BaseModel):
    """Infrastructure generation request payload."""

    task_id: str
    infrastructure_type: str = Field(..., description="docker, kubernetes, terraform, cloudformation")
    requirements: Dict[str, Any]


class InfraArtifact(BaseModel):
    """Generated infrastructure artifact."""

    file_path: str
    content: str
    template_used: Optional[str] = None


class InfraResponse(BaseModel):
    """Infrastructure agent response payload."""

    infra_id: str
    artifacts: List[InfraArtifact]
    validation_status: str
    estimated_tokens: int
    template_reuse_pct: float
    guardrail_report: GuardrailReport
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GuardrailViolation(Exception):
    """Raised when guardrail enforcement blocks the workflow."""

    def __init__(self, report: GuardrailReport):
        super().__init__("Guardrail checks failed")
        self.report = report


INFRA_TEMPLATES = {
    "docker": "docker-compose-standard",
    "kubernetes": "k8s-deployment-basic",
    "terraform": "terraform-aws-vpc",
}


def list_templates() -> Dict[str, List[Dict[str, Any]]]:
    """Expose available templates for FastAPI endpoints and LangGraph nodes."""

    return {
        "templates": [
            {"name": "docker-compose-standard", "usage_count": 145},
            {"name": "k8s-deployment-basic", "usage_count": 89},
            {"name": "terraform-aws-vpc", "usage_count": 67},
        ]
    }


def generate_from_template(request: InfraRequest) -> List[InfraArtifact]:
    """Simple template customization placeholder until LLM wiring completes."""

    template_name = INFRA_TEMPLATES.get(request.infrastructure_type, "docker-compose-standard")
    return [
        InfraArtifact(
            file_path="docker-compose.yml" if request.infrastructure_type == "docker" else "infra/main.tf",
            content="# Generated infrastructure config\n# Production version should be generated via LLM",
            template_used=template_name,
        )
    ]


async def process_infra_request(
    request: InfraRequest,
    *,
    infra_id: Optional[str] = None,
) -> InfraResponse:
    """Run guardrails and template generation in a shared service layer."""

    infra_id = infra_id or str(uuid.uuid4())

    guardrail_report = await guardrail_orchestrator.run(
        "infrastructure",
        task_id=request.task_id or infra_id,
        context={
            "endpoint": "generate",
            "infrastructure_type": request.infrastructure_type,
        },
    )

    if guardrail_orchestrator.should_block_failures and guardrail_report.status == GuardrailStatus.FAILED:
        raise GuardrailViolation(guardrail_report)

    artifacts = generate_from_template(request)

    if guardrail_report.status == GuardrailStatus.FAILED:
        validation_status = "guardrail_failed"
    elif guardrail_report.status == GuardrailStatus.WARNINGS:
        validation_status = "guardrail_warnings"
    else:
        validation_status = "passed"

    response = InfraResponse(
        infra_id=infra_id,
        artifacts=artifacts,
        validation_status=validation_status,
        estimated_tokens=len(str(request.requirements)) * 3,
        template_reuse_pct=0.80,
        guardrail_report=guardrail_report,
    )

    await mcp_client.log_event(
        "infrastructure_generated",
        metadata={
            "infra_id": infra_id,
            "task_id": request.task_id,
            "artifacts": [artifact.file_path for artifact in artifacts],
            "infrastructure_type": request.infrastructure_type,
            "status": validation_status,
            "guardrail_report_id": guardrail_report.report_id,
            "guardrail_status": guardrail_report.status,
            "llm_enabled": gradient_client.is_enabled(),
        },
    )

    return response
