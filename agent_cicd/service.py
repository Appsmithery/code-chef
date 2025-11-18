"""Shared business logic for the CI/CD agent."""

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

mcp_client = MCPClient(agent_name="cicd")
gradient_client = get_gradient_client("cicd")
guardrail_orchestrator = GuardrailOrchestrator()


class PipelineRequest(BaseModel):
    """CI/CD pipeline generation request payload."""

    description: str = Field(..., description="Pipeline requirement description")
    platform: str = Field(default="github-actions", description="CI/CD platform")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    task_id: Optional[str] = Field(default=None, description="Parent task ID from orchestrator")


class PipelineStage(BaseModel):
    """Individual pipeline stage."""

    name: str
    steps: List[str]
    environment: Optional[Dict[str, str]] = None


class PipelineResponse(BaseModel):
    """CI/CD pipeline generation response."""

    pipeline_id: str
    status: str
    config_file: str
    content: str
    stages: List[PipelineStage]
    estimated_duration: int = Field(default=0, description="Estimated pipeline duration in seconds")
    guardrail_report: GuardrailReport
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GuardrailViolation(Exception):
    """Raised when guardrail enforcement blocks pipeline generation."""

    def __init__(self, report: GuardrailReport):
        super().__init__("Guardrail checks failed")
        self.report = report


async def generate_pipeline_with_llm(
    request: PipelineRequest,
    pipeline_id: str,
) -> Dict[str, Any]:
    """Generate CI/CD pipeline using Gradient AI with LangSmith tracing."""

    system_prompt = """You are an expert DevOps engineer. Generate production-ready CI/CD pipeline configurations.

Return your response as JSON with this structure:
{
  "config_file": ".github/workflows/main.yml",
  "content": "# Full pipeline YAML here",
  "stages": [
    {
      "name": "build",
      "steps": ["checkout", "install deps", "build"],
      "environment": {"NODE_ENV": "production"}
    }
  ]
}"""

    user_prompt = f"""Pipeline Request: {request.description}

Platform: {request.platform}
Context: {request.context or 'General CI/CD pipeline'}

Generate pipeline configuration with proper testing, security scanning, and deployment stages."""

    try:
        logger.info("[CI/CD] Attempting LLM-powered pipeline generation for %s", pipeline_id)
        result = await gradient_client.complete_structured(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=3000,
            metadata={
                "task_id": pipeline_id,
                "platform": request.platform,
            },
        )

        logger.info(
            "[CI/CD] LLM generation successful: %s tokens used",
            result.get("tokens", 0),
        )

        return result["content"]
    except Exception as exc:  # noqa: BLE001
        logger.error("[CI/CD] LLM generation failed: %s", exc, exc_info=True)
        return {
            "config_file": ".github/workflows/main.yml",
            "content": "# Generated CI/CD pipeline\n# Production: Replace with LLM-generated pipeline",
            "stages": [
                {
                    "name": "build",
                    "steps": ["Checkout code", "Install dependencies", "Build"],
                }
            ],
        }


async def process_pipeline_request(
    request: PipelineRequest,
    *,
    pipeline_id: Optional[str] = None,
) -> PipelineResponse:
    """Execute the pipeline generation workflow and return the response payload."""

    pipeline_id = pipeline_id or str(uuid.uuid4())

    guardrail_report = await guardrail_orchestrator.run(
        "cicd",
        task_id=request.task_id or pipeline_id,
        context={"endpoint": "generate", "platform": request.platform},
    )

    if guardrail_orchestrator.should_block_failures and guardrail_report.status == GuardrailStatus.FAILED:
        raise GuardrailViolation(guardrail_report)

    if gradient_client.is_enabled():
        pipeline_data = await generate_pipeline_with_llm(request, pipeline_id)
    else:
        pipeline_data = {
            "config_file": ".github/workflows/main.yml",
            "content": "# Basic pipeline configuration\n# LLM disabled",
            "stages": [
                {"name": "build", "steps": ["Build application"]},
                {"name": "test", "steps": ["Run tests"]},
            ],
        }

    stages = [
        PipelineStage(
            name=stage["name"],
            steps=stage.get("steps", []),
            environment=stage.get("environment"),
        )
        for stage in pipeline_data.get("stages", [])
    ]

    response = PipelineResponse(
        pipeline_id=pipeline_id,
        status="completed",
        config_file=pipeline_data.get("config_file", ".github/workflows/main.yml"),
        content=pipeline_data.get("content", ""),
        stages=stages,
        estimated_duration=len(stages) * 120,
        guardrail_report=guardrail_report,
    )

    await mcp_client.log_event(
        "pipeline_generated",
        metadata={
            "pipeline_id": pipeline_id,
            "stage_count": len(stages),
            "platform": request.platform,
            "status": response.status,
            "llm_enabled": gradient_client.is_enabled(),
            "guardrail_report_id": guardrail_report.report_id,
            "guardrail_status": guardrail_report.status,
        },
    )

    return response


async def trigger_deployment(
    pipeline_id: str,
    environment: str = "production",
) -> Dict[str, Any]:
    """Trigger pipeline deployment (placeholder)."""

    logger.info("[CI/CD] Triggering deployment for pipeline %s to %s", pipeline_id, environment)

    return {
        "deployment_id": str(uuid.uuid4()),
        "pipeline_id": pipeline_id,
        "environment": environment,
        "status": "triggered",
        "timestamp": datetime.utcnow().isoformat(),
    }
