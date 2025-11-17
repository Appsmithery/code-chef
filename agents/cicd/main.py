"""
CI/CD Pipeline Agent

Primary Role: Automation workflow generation and deployment orchestration
- Generates GitHub Actions workflows, GitLab CI, or Jenkins pipelines
- Creates deployment automation scripts and rollback procedures
- Implements build, test, deploy sequences for approved changes
- Handles conditional deployments based on branch strategies
"""

from fastapi import FastAPI, HTTPException
from datetime import datetime
from typing import Any, Dict
import uvicorn
import os
import logging
from prometheus_fastapi_instrumentator import Instrumentator

from service import (
    GuardrailViolation,
    PipelineRequest,
    PipelineResponse,
    mcp_client,
    process_pipeline_request,
    trigger_deployment,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

app = FastAPI(
    title="CI/CD Pipeline Agent",
    description="Automation workflow generation and deployment orchestration",
    version="1.0.0"
)

# Enable Prometheus metrics collection
Instrumentator().instrument(app).expose(app)

@app.get("/health")
async def health_check():
    gateway_health = await mcp_client.get_gateway_health()
    return {
        "status": "ok",
        "service": "cicd",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "mcp": {
            "gateway": gateway_health,
            "recommended_tool_servers": [entry.get("server") for entry in mcp_client.recommended_tools],
            "shared_tool_servers": mcp_client.shared_tools,
            "capabilities": mcp_client.capabilities,
        },
    }


@app.post("/generate", response_model=PipelineResponse)
async def generate_pipeline(request: PipelineRequest):
    """
    Generate CI/CD pipeline configuration
    - Maintains pipeline template library for standard sequences
    - Invokes LLM only for dynamic decision points
    - Reduces generation tokens by 75% via template customization
    """
    try:
        return await process_pipeline_request(request)
    except GuardrailViolation as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Guardrail checks failed",
                "report": exc.report.model_dump(mode="json"),
            },
        )


@app.post("/deploy")
async def execute_deployment(deployment: Dict[str, Any]):
    return await trigger_deployment(deployment)


if __name__ == '__main__':
    port = int(os.getenv("PORT", "8005"))
    uvicorn.run(app, host="0.0.0.0", port=port)