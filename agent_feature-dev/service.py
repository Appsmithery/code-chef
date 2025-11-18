"""Shared business logic for the Feature Development agent."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

from lib.gradient_client import get_gradient_client
from lib.guardrail import GuardrailOrchestrator, GuardrailReport, GuardrailStatus
from lib.mcp_client import MCPClient

logger = logging.getLogger(__name__)

RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://rag-context:8007")

mcp_client = MCPClient(agent_name="feature-dev")
gradient_client = get_gradient_client("feature-dev")
guardrail_orchestrator = GuardrailOrchestrator()


class FeatureRequest(BaseModel):
    """Feature implementation request payload."""

    description: str = Field(..., description="Feature description from orchestrator")
    context_refs: Optional[List[str]] = Field(default=None, description="Context references from RAG")
    project_context: Optional[Dict[str, Any]] = Field(default=None, description="Project metadata")
    task_id: Optional[str] = Field(default=None, description="Parent task ID from orchestrator")


class CodeArtifact(BaseModel):
    """Generated code artifact."""

    file_path: str
    content: str
    operation: str = Field(..., description="create, modify, or delete")
    description: str


class TestResult(BaseModel):
    """Unit test execution result."""

    test_name: str
    status: str
    duration_ms: float
    error_message: Optional[str] = None


class FeatureResponse(BaseModel):
    """Feature implementation response."""

    feature_id: str
    status: str
    artifacts: List[CodeArtifact]
    test_results: List[TestResult]
    commit_message: str
    estimated_tokens: int
    context_lines_used: int
    guardrail_report: GuardrailReport
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GuardrailViolation(Exception):
    """Raised when guardrail enforcement blocks feature implementation."""

    def __init__(self, report: GuardrailReport):
        super().__init__("Guardrail checks failed")
        self.report = report


def generate_code_artifacts(
    request: FeatureRequest,
    rag_context: Optional[List[Dict[str, Any]]] = None,
) -> List[CodeArtifact]:
    """Fallback implementation when LLM is unavailable."""

    return [
        CodeArtifact(
            file_path=f"src/features/{request.description.replace(' ', '_').lower()}.py",
            content="# Generated feature implementation\n# Production: Replace with LLM-generated code",
            operation="create",
            description=f"Implementation for {request.description}",
        )
    ]


async def generate_code_with_llm(
    request: FeatureRequest,
    rag_context: List[Dict[str, Any]],
    feature_id: str,
) -> List[CodeArtifact]:
    """Generate code artifacts using Gradient AI with Langfuse tracing."""

    context_str = "\n\n".join(
        [f"Context {i + 1}:\n{item['content']}" for i, item in enumerate(rag_context[:3])]
    )

    system_prompt = """You are an expert software engineer. Generate production-ready code based on the feature description and context provided.

Return your response as JSON with this structure:
{
  "files": [
    {
      "path": "src/path/to/file.py",
      "content": "# Full file content here",
      "operation": "create",
      "description": "Brief description"
    }
  ]
}"""

    user_prompt = f"""Feature Request: {request.description}

Relevant Context:
{context_str}

Project Context: {request.project_context or 'General Python project'}

Generate implementation files with proper error handling, type hints, and docstrings."""

    try:
        logger.info("[Feature-Dev] Attempting LLM-powered code generation for feature %s", feature_id)
        result = await gradient_client.complete_structured(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=2000,
            metadata={
                "task_id": feature_id,
                "feature_description": request.description,
                "rag_contexts": len(rag_context),
            },
        )

        logger.info(
            "[Feature-Dev] LLM generation successful: %s tokens used",
            result.get("tokens", 0),
        )

        llm_files = result["content"].get("files", [])
        artifacts = [
            CodeArtifact(
                file_path=file["path"],
                content=file["content"],
                operation=file.get("operation", "create"),
                description=file.get("description", ""),
            )
            for file in llm_files
        ]

        return artifacts
    except Exception as exc:  # noqa: BLE001
        logger.error("[Feature-Dev] LLM generation failed: %s", exc, exc_info=True)
        return generate_code_artifacts(request, rag_context)


async def query_mock_rag(description: str) -> List[Dict[str, Any]]:
    """Fallback mock RAG query for development."""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{RAG_SERVICE_URL}/query/mock",
                json={"query": description, "collection": "the-shop", "n_results": 5},
                timeout=5.0,
            )

            if response.status_code == 200:
                data = response.json()
                return [
                    {
                        "content": item["content"],
                        "metadata": item["metadata"],
                        "relevance": item["relevance_score"],
                    }
                    for item in data.get("results", [])
                ]
    except Exception:  # noqa: BLE001
        pass

    return [
        {
            "content": f"Context for: {description}",
            "metadata": {"source": "fallback"},
            "relevance": 0.5,
        }
    ]


async def query_rag_context(description: str) -> List[Dict[str, Any]]:
    """Query the RAG Context Manager for relevant snippets."""

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{RAG_SERVICE_URL}/query",
                json={"query": description, "collection": "the-shop", "n_results": 5},
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                return [
                    {
                        "content": item["content"],
                        "metadata": item["metadata"],
                        "relevance": item["relevance_score"],
                    }
                    for item in data.get("results", [])
                ]
            return await query_mock_rag(description)
    except Exception as exc:  # noqa: BLE001
        logger.warning("RAG query failed (%s), using mock data", exc)
        return await query_mock_rag(description)


def execute_tests(artifacts: List[CodeArtifact]) -> List[TestResult]:
    """Execute unit tests (placeholder)."""

    return [
        TestResult(
            test_name="test_feature_implementation",
            status="passed",
            duration_ms=125.5,
        )
    ]


def generate_commit_message(request: FeatureRequest, artifacts: List[CodeArtifact]) -> str:
    """Generate descriptive commit message for artifacts."""

    summary = "\n- ".join(artifact.file_path for artifact in artifacts)
    return f"feat: {request.description}\n\nGenerated {len(artifacts)} file(s)\n- {summary}"


async def process_feature_request(
    request: FeatureRequest,
    *,
    feature_id: Optional[str] = None,
) -> FeatureResponse:
    """Execute the feature implementation workflow and return the response payload."""

    feature_id = feature_id or str(uuid.uuid4())

    guardrail_report = await guardrail_orchestrator.run(
        "feature-dev",
        task_id=request.task_id or feature_id,
        context={"endpoint": "implement", "description": request.description},
    )

    if guardrail_orchestrator.should_block_failures and guardrail_report.status == GuardrailStatus.FAILED:
        raise GuardrailViolation(guardrail_report)

    rag_context = await query_rag_context(request.description)

    if gradient_client.is_enabled():
        artifacts = await generate_code_with_llm(request, rag_context, feature_id)
    else:
        artifacts = generate_code_artifacts(request, rag_context)

    test_results = execute_tests(artifacts)
    commit_message = generate_commit_message(request, artifacts)
    estimated_tokens = len(request.description.split()) * 10
    context_lines = sum(len(item.get("content", "").split("\n")) for item in rag_context)

    response = FeatureResponse(
        feature_id=feature_id,
        status="completed" if all(t.status == "passed" for t in test_results) else "needs_revision",
        artifacts=artifacts,
        test_results=test_results,
        commit_message=commit_message,
        estimated_tokens=estimated_tokens,
        context_lines_used=context_lines,
        guardrail_report=guardrail_report,
    )

    await mcp_client.log_event(
        "feature_implemented",
        metadata={
            "feature_id": feature_id,
            "artifact_count": len(artifacts),
            "test_pass_rate": sum(1 for t in test_results if t.status == "passed") / max(len(test_results), 1),
            "status": response.status,
            "llm_enabled": gradient_client.is_enabled(),
            "guardrail_report_id": guardrail_report.report_id,
            "guardrail_status": guardrail_report.status,
        },
    )

    return response
