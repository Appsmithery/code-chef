"""Shared business logic for the CI/CD agent."""

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

mcp_client = MCPClient(agent_name="cicd")
gradient_client = get_gradient_client("cicd")
guardrail_orchestrator = GuardrailOrchestrator()


class PipelineRequest(BaseModel):
    """Pipeline generation request."""

    task_id: str
    pipeline_type: str = Field(..., description="github-actions, gitlab-ci, jenkins")
    stages: List[str] = Field(default_factory=lambda: ["build", "test", "deploy"])
    deployment_strategy: Optional[str] = None


class PipelineArtifact(BaseModel):
    """Represents a generated pipeline artifact."""

    file_path: str
    content: str
    stage: str


class PipelineResponse(BaseModel):
    """Pipeline generation response payload."""

    pipeline_id: str
    artifacts: List[PipelineArtifact]
    validation_status: str
    estimated_tokens: int
    template_reuse_pct: float
    guardrail_report: GuardrailReport
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GuardrailViolation(Exception):
    """Raised when guardrail enforcement blocks execution."""

    def __init__(self, report: GuardrailReport):
        super().__init__("Guardrail checks failed")
        self.report = report


def generate_pipeline_config(request: PipelineRequest) -> List[PipelineArtifact]:
    """Placeholder template customization for pipelines."""

    filename = {
        "github-actions": ".github/workflows/ci.yml",
        "gitlab-ci": ".gitlab-ci.yml",
        "jenkins": "Jenkinsfile",
    }.get(request.pipeline_type, ".github/workflows/ci.yml")

    content = "# Generated pipeline config\n# Replace with LLM-generated workflow"
    return [
        PipelineArtifact(
            file_path=filename,
            content=content,
            stage=request.stages[0] if request.stages else "build",
        )
    ]


async def process_pipeline_request(
    request: PipelineRequest,
    *,
    pipeline_id: Optional[str] = None,
) -> PipelineResponse:
    """Run guardrails and produce pipeline artifacts."""

    pipeline_id = pipeline_id or str(uuid.uuid4())

    guardrail_report = await guardrail_orchestrator.run(
        "cicd",
        task_id=request.task_id or pipeline_id,
        context={
            "endpoint": "generate",
            "pipeline_type": request.pipeline_type,
            "stages": request.stages,
        },
    )

    if guardrail_orchestrator.should_block_failures and guardrail_report.status == GuardrailStatus.FAILED:
        raise GuardrailViolation(guardrail_report)

    artifacts = generate_pipeline_config(request)

    if guardrail_report.status == GuardrailStatus.FAILED:
        validation_status = "guardrail_failed"
    elif guardrail_report.status == GuardrailStatus.WARNINGS:
        validation_status = "guardrail_warnings"
    else:
        validation_status = "passed"

    response = PipelineResponse(
        pipeline_id=pipeline_id,
        artifacts=artifacts,
        validation_status=validation_status,
        estimated_tokens=len(request.stages) * 50,
        template_reuse_pct=0.75,
        guardrail_report=guardrail_report,
    )

    await mcp_client.log_event(
        "pipeline_generated",
        metadata={
            "pipeline_id": pipeline_id,
            "task_id": request.task_id,
            "stages": request.stages,
            "deployment_strategy": request.deployment_strategy,
            "artifact_count": len(artifacts),
            "guardrail_report_id": guardrail_report.report_id,
            "guardrail_status": guardrail_report.status,
            "llm_enabled": gradient_client.is_enabled(),
        },
    )

    return response


async def trigger_deployment(deployment: Dict[str, Any]) -> Dict[str, Any]:
    """Shared helper for invoking deployments via FastAPI or LangGraph."""

    deployment_id = f"dep-{uuid.uuid4().hex[:8]}"
    await mcp_client.log_event(
        "deployment_triggered",
        metadata={
            "deployment_id": deployment_id,
            "deployment": deployment,
        },
    )
    return {"deployment_id": deployment_id, "status": "in_progress"}
