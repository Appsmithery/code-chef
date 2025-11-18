"""Shared business logic for the Documentation agent."""

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

mcp_client = MCPClient(agent_name="documentation")
gradient_client = get_gradient_client("documentation")
guardrail_orchestrator = GuardrailOrchestrator()


class DocRequest(BaseModel):
    """Documentation generation request payload."""

    description: str = Field(..., description="Documentation requirement description")
    doc_type: str = Field(default="markdown", description="Documentation type")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    task_id: Optional[str] = Field(default=None, description="Parent task ID from orchestrator")


class DocSection(BaseModel):
    """Individual documentation section."""

    title: str
    content: str
    level: int = Field(default=2, description="Heading level")


class DocResponse(BaseModel):
    """Documentation generation response."""

    doc_id: str
    status: str
    file_path: str
    content: str
    sections: List[DocSection]
    word_count: int
    guardrail_report: GuardrailReport
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GuardrailViolation(Exception):
    """Raised when guardrail enforcement blocks documentation generation."""

    def __init__(self, report: GuardrailReport):
        super().__init__("Guardrail checks failed")
        self.report = report


def list_doc_templates() -> List[Dict[str, str]]:
    """List available documentation templates."""

    return [
        {"name": "api-reference", "description": "API documentation with endpoints"},
        {"name": "user-guide", "description": "User-facing documentation"},
        {"name": "technical-spec", "description": "Technical specification document"},
        {"name": "readme", "description": "Project README with quick start"},
    ]


async def generate_docs_with_llm(
    request: DocRequest,
    doc_id: str,
) -> Dict[str, Any]:
    """Generate documentation using Gradient AI with LangSmith tracing."""

    system_prompt = """You are an expert technical writer. Generate clear, comprehensive documentation.

Return your response as JSON with this structure:
{
  "file_path": "docs/README.md",
  "content": "# Full markdown content here",
  "sections": [
    {
      "title": "Introduction",
      "content": "Section content",
      "level": 2
    }
  ]
}"""

    user_prompt = f"""Documentation Request: {request.description}

Type: {request.doc_type}
Context: {request.context or 'General documentation'}

Generate well-structured documentation with clear examples and proper formatting."""

    try:
        logger.info("[Documentation] Attempting LLM-powered doc generation for %s", doc_id)
        result = await gradient_client.complete_structured(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=4000,
            metadata={
                "task_id": doc_id,
                "doc_type": request.doc_type,
            },
        )

        logger.info(
            "[Documentation] LLM generation successful: %s tokens used",
            result.get("tokens", 0),
        )

        return result["content"]
    except Exception as exc:  # noqa: BLE001
        logger.error("[Documentation] LLM generation failed: %s", exc, exc_info=True)
        return {
            "file_path": "docs/README.md",
            "content": f"# {request.description}\n\n<!-- Generated documentation -->\n<!-- Production: Replace with LLM-generated content -->",
            "sections": [
                {
                    "title": "Overview",
                    "content": f"Documentation for {request.description}",
                    "level": 2,
                }
            ],
        }


async def process_doc_request(
    request: DocRequest,
    *,
    doc_id: Optional[str] = None,
) -> DocResponse:
    """Execute the documentation generation workflow and return the response payload."""

    doc_id = doc_id or str(uuid.uuid4())

    guardrail_report = await guardrail_orchestrator.run(
        "documentation",
        task_id=request.task_id or doc_id,
        context={"endpoint": "generate", "doc_type": request.doc_type},
    )

    if guardrail_orchestrator.should_block_failures and guardrail_report.status == GuardrailStatus.FAILED:
        raise GuardrailViolation(guardrail_report)

    if gradient_client.is_enabled():
        doc_data = await generate_docs_with_llm(request, doc_id)
    else:
        doc_data = {
            "file_path": "docs/README.md",
            "content": f"# {request.description}\n\n<!-- Basic documentation -->\n<!-- LLM disabled -->",
            "sections": [
                {"title": "Overview", "content": request.description, "level": 2}
            ],
        }

    sections = [
        DocSection(
            title=section["title"],
            content=section.get("content", ""),
            level=section.get("level", 2),
        )
        for section in doc_data.get("sections", [])
    ]

    content = doc_data.get("content", "")
    word_count = len(content.split())

    response = DocResponse(
        doc_id=doc_id,
        status="completed",
        file_path=doc_data.get("file_path", "docs/README.md"),
        content=content,
        sections=sections,
        word_count=word_count,
        guardrail_report=guardrail_report,
    )

    await mcp_client.log_event(
        "documentation_generated",
        metadata={
            "doc_id": doc_id,
            "section_count": len(sections),
            "word_count": word_count,
            "doc_type": request.doc_type,
            "status": response.status,
            "llm_enabled": gradient_client.is_enabled(),
            "guardrail_report_id": guardrail_report.report_id,
            "guardrail_status": guardrail_report.status,
        },
    )

    return response
