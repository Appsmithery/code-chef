"""
Documentation Agent

Primary Role: Documentation generation and maintenance
- Generates README files, API documentation, and user guides
- Creates inline code comments and docstrings
- Updates documentation for code changes
- Maintains documentation templates and style guides
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
import uvicorn
import os
from prometheus_fastapi_instrumentator import Instrumentator

from agents._shared.mcp_client import MCPClient
from agents._shared.gradient_client import get_gradient_client
from agents._shared.guardrail import GuardrailOrchestrator, GuardrailReport, GuardrailStatus

app = FastAPI(
    title="Documentation Agent",
    description="Documentation generation and maintenance",
    version="1.0.0"
)

# Enable Prometheus metrics collection
Instrumentator().instrument(app).expose(app)

# Shared MCP client for tool access and telemetry
mcp_client = MCPClient(agent_name="documentation")

# Gradient AI client for LLM inference (with Langfuse tracing)
gradient_client = get_gradient_client("documentation")

# Guardrail orchestrator for compliance checks
guardrail_orchestrator = GuardrailOrchestrator()

class DocRequest(BaseModel):
    task_id: str
    doc_type: str = Field(..., description="readme, api-docs, guide, comments")
    context_refs: Optional[List[str]] = None
    target_audience: str = Field(default="developers")

class DocArtifact(BaseModel):
    file_path: str
    content: str
    doc_type: str

class DocResponse(BaseModel):
    doc_id: str
    artifacts: List[DocArtifact]
    estimated_tokens: int
    template_used: Optional[str] = None
    guardrail_report: GuardrailReport
    timestamp: datetime = Field(default_factory=datetime.utcnow)

@app.get("/health")
async def health_check():
    gateway_health = await mcp_client.get_gateway_health()
    return {
        "status": "ok",
        "service": "documentation",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "mcp": {
            "gateway": gateway_health,
            "recommended_tool_servers": [entry.get("server") for entry in mcp_client.recommended_tools],
            "shared_tool_servers": mcp_client.shared_tools,
            "capabilities": mcp_client.capabilities,
        },
    }

@app.post("/generate", response_model=DocResponse)
async def generate_documentation(request: DocRequest):
    """
    Generate documentation
    - Uses documentation templates for consistent formatting
    - Queries RAG for context about code to document
    - Generates user-friendly explanations and examples
    """
    import uuid
    
    doc_id = str(uuid.uuid4())

    guardrail_report = await guardrail_orchestrator.run(
        "documentation",
        task_id=request.task_id,
        context={
            "endpoint": "generate",
            "doc_type": request.doc_type,
        },
    )

    if guardrail_orchestrator.should_block_failures and guardrail_report.status == GuardrailStatus.FAILED:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Guardrail checks failed",
                "report": guardrail_report.model_dump(mode="json"),
            },
        )
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
        },
    )

    return response

@app.get("/templates")
async def list_doc_templates():
    return {
        "templates": [
            {"name": "readme-standard", "sections": ["overview", "installation", "usage", "api"]},
            {"name": "api-docs-openapi", "format": "OpenAPI 3.0"},
            {"name": "guide-tutorial", "style": "step-by-step"}
        ]
    }

def generate_docs(request: DocRequest) -> List[DocArtifact]:
    # Placeholder implementation (intentional for MVP demo)
    # In production, this would analyze code and generate comprehensive documentation
    return [
        DocArtifact(
            file_path="README.md",
            content="# Generated Documentation\n\n<!-- Production: Replace with LLM-generated documentation -->",
            doc_type=request.doc_type
        )
    ]

if __name__ == '__main__':
    port = int(os.getenv("PORT", "8006"))
    uvicorn.run(app, host="0.0.0.0", port=port)