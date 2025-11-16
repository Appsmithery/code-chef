"""
Code Review Agent

Primary Role: Quality assurance, static analysis, and security scanning
- Performs static code analysis on diffs (not full codebases)
- Executes security vulnerability scanning and dependency checks
- Validates coding standards compliance and best practices
- Reviews test coverage and test quality metrics
"""

from fastapi import FastAPI, HTTPException
from datetime import datetime
import uvicorn
import os
import logging
from prometheus_fastapi_instrumentator import Instrumentator

from service import (
    GuardrailViolation,
    ReviewRequest,
    ReviewResponse,
    mcp_client,
    process_review_request,
)

# LangGraph Infrastructure
try:
    import sys
    sys.path.insert(0, '/app')
    from agents._shared.langgraph_base import get_postgres_checkpointer, create_workflow_config
    from agents._shared.qdrant_client import get_qdrant_client
    from agents._shared.langchain_memory import create_hybrid_memory
    
    checkpointer = get_postgres_checkpointer()
    qdrant_client = get_qdrant_client()
    hybrid_memory = create_hybrid_memory()
    logger.info("✓ LangGraph infrastructure initialized (PostgreSQL checkpointer + Qdrant Cloud + Hybrid memory)")
except Exception as e:
    logger.warning(f"LangGraph infrastructure unavailable: {e}")
    checkpointer = None
    qdrant_client = None
    hybrid_memory = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Code Review Agent",
    description="Quality assurance, static analysis, and security scanning",
    version="1.0.0"
)

# Enable Prometheus metrics collection
Instrumentator().instrument(app).expose(app)

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
    try:
        return await process_review_request(request)
    except GuardrailViolation as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Guardrail checks failed",
                "report": exc.report.model_dump(mode="json"),
            },
        )

if __name__ == '__main__':
    port = int(os.getenv("PORT", "8003"))
    uvicorn.run(app, host="0.0.0.0", port=port)