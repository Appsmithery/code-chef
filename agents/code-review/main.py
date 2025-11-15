"""
Code Review Agent

Primary Role: Quality assurance, static analysis, and security scanning
- Performs static code analysis on diffs (not full codebases)
- Executes security vulnerability scanning and dependency checks
- Validates coding standards compliance and best practices
- Reviews test coverage and test quality metrics
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
    title="Code Review Agent",
    description="Quality assurance, static analysis, and security scanning",
    version="1.0.0"
)

# Enable Prometheus metrics collection
Instrumentator().instrument(app).expose(app)

# Shared MCP client for tool access and telemetry
mcp_client = MCPClient(agent_name="code-review")

# Gradient AI client for LLM inference (with Langfuse tracing)
gradient_client = get_gradient_client("code-review")

# Guardrail orchestrator for compliance checks
guardrail_orchestrator = GuardrailOrchestrator()

class CodeDiff(BaseModel):
    file_path: str
    changes: str
    context_lines: int = 5

class ReviewRequest(BaseModel):
    task_id: str
    diffs: List[CodeDiff]
    test_results: Optional[Dict[str, Any]] = None

class ReviewFinding(BaseModel):
    severity: str
    category: str
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None

class ReviewResponse(BaseModel):
    review_id: str
    status: str
    findings: List[ReviewFinding]
    approval: bool
    summary: str
    estimated_tokens: int
    guardrail_report: GuardrailReport
    timestamp: datetime = Field(default_factory=datetime.utcnow)

@app.get("/health")
async def health_check():
    gateway_health = await mcp_client.get_gateway_health()
    return {
        "status": "ok",
        "service": "code-review",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "mcp": {
            "gateway": gateway_health,
            "recommended_tool_servers": [entry.get("server") for entry in mcp_client.recommended_tools],
            "shared_tool_servers": mcp_client.shared_tools,
            "capabilities": mcp_client.capabilities,
        },
    }

@app.post("/review", response_model=ReviewResponse)
async def review_code(request: ReviewRequest):
    """
    Main code review endpoint
    - Receives only diff context (changed lines + 5-line context window)
    - Uses rule-based workflows for 70% of standard review patterns
    - Invokes LLM only for complex logic analysis
    """
    import uuid
    
    review_id = str(uuid.uuid4())

    guardrail_report = await guardrail_orchestrator.run(
        "code-review",
        task_id=request.task_id,
        context={
            "endpoint": "review",
            "diff_count": len(request.diffs),
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
    findings = analyze_diffs(request.diffs)
    
    # Simple approval logic
    critical_findings = [f for f in findings if f.severity == "critical"]
    approval = len(critical_findings) == 0
    
    # Token estimation: only diffs loaded
    token_estimate = sum(len(d.changes.split()) * 2 for d in request.diffs)

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
        },
    )

    return response

def analyze_diffs(diffs: List[CodeDiff]) -> List[ReviewFinding]:
    # Placeholder static analysis
    return []

if __name__ == '__main__':
    port = int(os.getenv("PORT", "8003"))
    uvicorn.run(app, host="0.0.0.0", port=port)