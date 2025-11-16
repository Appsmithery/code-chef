"""
Infrastructure Agent

Primary Role: Infrastructure-as-code generation and deployment configuration
- Generates Docker Compose files, Dockerfiles, and container configurations
- Creates Kubernetes manifests, Helm charts, and orchestration configs
- Manages Terraform/CloudFormation templates for cloud infrastructure
- Maintains template library for 80% of common deployment patterns
"""

from fastapi import FastAPI, HTTPException
from datetime import datetime
import uvicorn
import os
import logging
from prometheus_fastapi_instrumentator import Instrumentator

from agents.infrastructure.service import (
    GuardrailViolation,
    InfraRequest,
    InfraResponse,
    list_templates,
    mcp_client,
    process_infra_request,
)

# LangGraph Infrastructure
try:
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
    title="Infrastructure Agent",
    description="Infrastructure-as-code generation and deployment configuration",
    version="1.0.0"
)

# Enable Prometheus metrics collection
Instrumentator().instrument(app).expose(app)

@app.get("/health")
async def health_check():
    gateway_health = await mcp_client.get_gateway_health()
    return {
        "status": "ok",
        "service": "infrastructure",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "mcp": {
            "gateway": gateway_health,
            "recommended_tool_servers": [entry.get("server") for entry in mcp_client.recommended_tools],
            "shared_tool_servers": mcp_client.shared_tools,
            "capabilities": mcp_client.capabilities,
        },
    }


@app.post("/generate", response_model=InfraResponse)
async def generate_infrastructure(request: InfraRequest):
    """
    Generate infrastructure-as-code
    - Template-first generation: customizes parameters vs full generation (70-85% token reduction)
    - Loads only infrastructure specifications
    - Generates configurations incrementally with validation checkpoints
    """
    try:
        return await process_infra_request(request)
    except GuardrailViolation as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Guardrail checks failed",
                "report": exc.report.model_dump(mode="json"),
            },
        )

@app.get("/templates")
async def list_infra_templates():
    """Expose available infrastructure templates."""

    return list_templates()


if __name__ == '__main__':
    port = int(os.getenv("PORT", "8004"))
    uvicorn.run(app, host="0.0.0.0", port=port)