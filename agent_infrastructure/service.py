"""Shared business logic for the Infrastructure agent."""

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

mcp_client = MCPClient(agent_name="infrastructure")
gradient_client = get_gradient_client("infrastructure")
guardrail_orchestrator = GuardrailOrchestrator()


class InfraRequest(BaseModel):
    """Infrastructure provisioning request payload."""

    description: str = Field(..., description="Infrastructure requirement description")
    provider: str = Field(default="docker-compose", description="Infrastructure provider")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    task_id: Optional[str] = Field(default=None, description="Parent task ID from orchestrator")


class InfraArtifact(BaseModel):
    """Generated infrastructure artifact."""

    file_path: str
    content: str
    artifact_type: str = Field(..., description="docker-compose, terraform, kubernetes")
    description: str


class InfraResponse(BaseModel):
    """Infrastructure provisioning response."""

    infra_id: str
    status: str
    artifacts: List[InfraArtifact]
    estimated_cost: float = Field(default=0.0, description="Estimated monthly cost USD")
    deployment_steps: List[str]
    guardrail_report: GuardrailReport
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GuardrailViolation(Exception):
    """Raised when guardrail enforcement blocks infrastructure provisioning."""

    def __init__(self, report: GuardrailReport):
        super().__init__("Guardrail checks failed")
        self.report = report


def list_templates() -> List[Dict[str, str]]:
    """List available infrastructure templates."""

    return [
        {"name": "docker-compose-basic", "description": "Basic Docker Compose stack"},
        {"name": "kubernetes-deployment", "description": "Kubernetes deployment manifests"},
        {"name": "terraform-aws", "description": "AWS infrastructure with Terraform"},
    ]


async def generate_infra_with_llm(
    request: InfraRequest,
    infra_id: str,
) -> List[InfraArtifact]:
    """Generate infrastructure artifacts using Gradient AI with LangSmith tracing."""

    system_prompt = """You are an expert DevOps engineer. Generate production-ready infrastructure configurations.

Return your response as JSON with this structure:
{
  "artifacts": [
    {
      "file_path": "docker-compose.yml",
      "content": "# Full file content here",
      "artifact_type": "docker-compose",
      "description": "Brief description"
    }
  ],
  "deployment_steps": ["Step 1", "Step 2"]
}"""

    user_prompt = f"""Infrastructure Request: {request.description}

Provider: {request.provider}
Context: {request.context or 'General infrastructure'}

Generate configuration files with proper security, networking, and resource limits."""

    try:
        logger.info("[Infrastructure] Attempting LLM-powered infrastructure generation for %s", infra_id)
        result = await gradient_client.complete_structured(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=3000,
            metadata={
                "task_id": infra_id,
                "provider": request.provider,
            },
        )

        logger.info(
            "[Infrastructure] LLM generation successful: %s tokens used",
            result.get("tokens", 0),
        )

        llm_artifacts = result["content"].get("artifacts", [])
        artifacts = [
            InfraArtifact(
                file_path=artifact["file_path"],
                content=artifact["content"],
                artifact_type=artifact.get("artifact_type", "docker-compose"),
                description=artifact.get("description", ""),
            )
            for artifact in llm_artifacts
        ]

        return artifacts
    except Exception as exc:  # noqa: BLE001
        logger.error("[Infrastructure] LLM generation failed: %s", exc, exc_info=True)
        return [
            InfraArtifact(
                file_path="docker-compose.yml",
                content="# Generated infrastructure configuration\n# Production: Replace with LLM-generated config",
                artifact_type="docker-compose",
                description=f"Infrastructure for {request.description}",
            )
        ]


async def process_infra_request(
    request: InfraRequest,
    *,
    infra_id: Optional[str] = None,
) -> InfraResponse:
    """Execute the infrastructure provisioning workflow and return the response payload."""

    infra_id = infra_id or str(uuid.uuid4())

    guardrail_report = await guardrail_orchestrator.run(
        "infrastructure",
        task_id=request.task_id or infra_id,
        context={"endpoint": "provision", "provider": request.provider},
    )

    if guardrail_orchestrator.should_block_failures and guardrail_report.status == GuardrailStatus.FAILED:
        raise GuardrailViolation(guardrail_report)

    if gradient_client.is_enabled():
        artifacts = await generate_infra_with_llm(request, infra_id)
    else:
        artifacts = [
            InfraArtifact(
                file_path="docker-compose.yml",
                content="# Basic infrastructure configuration\n# LLM disabled",
                artifact_type="docker-compose",
                description=request.description,
            )
        ]

    deployment_steps = [
        f"Review generated {request.provider} configuration",
        "Validate security and resource settings",
        "Deploy to target environment",
        "Verify service health",
    ]

    response = InfraResponse(
        infra_id=infra_id,
        status="completed",
        artifacts=artifacts,
        estimated_cost=0.0,
        deployment_steps=deployment_steps,
        guardrail_report=guardrail_report,
    )

    await mcp_client.log_event(
        "infrastructure_provisioned",
        metadata={
            "infra_id": infra_id,
            "artifact_count": len(artifacts),
            "provider": request.provider,
            "status": response.status,
            "llm_enabled": gradient_client.is_enabled(),
            "guardrail_report_id": guardrail_report.report_id,
            "guardrail_status": guardrail_report.status,
        },
    )

    return response
