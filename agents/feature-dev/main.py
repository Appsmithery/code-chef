"""FastAPI service wrapper for the Feature Development agent."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Dict

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator

from service import (
    FeatureRequest,
    FeatureResponse,
    GuardrailViolation,
    mcp_client,
    process_feature_request,
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Feature Development Agent",
    description="Application code generation and feature implementation",
    version="1.0.0",
)

Instrumentator().instrument(app).expose(app)


@app.get("/health")
async def health_check():
    """Health check endpoint."""

    gateway_health = await mcp_client.get_gateway_health()
    return {
        "status": "ok",
        "service": "feature-dev",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "mcp": {
            "gateway": gateway_health,
            "recommended_tool_servers": [entry.get("server") for entry in mcp_client.recommended_tools],
            "shared_tool_servers": mcp_client.shared_tools,
            "capabilities": mcp_client.capabilities,
        },
    }


@app.post("/implement", response_model=FeatureResponse)
async def implement_feature(request: FeatureRequest):
    """Execute the feature implementation workflow."""

    try:
        return await process_feature_request(request)
    except GuardrailViolation as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Guardrail checks failed",
                "report": exc.report.model_dump(mode="json"),
            },
        ) from exc


@app.post("/implement-and-review", response_model=Dict[str, Any])
async def implement_and_review(request: FeatureRequest):
    """Implement feature and automatically trigger code review."""

    try:
        feature_result = await process_feature_request(request)
    except GuardrailViolation as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Guardrail checks failed",
                "report": exc.report.model_dump(mode="json"),
            },
        ) from exc

    code_review_url = os.getenv("CODE_REVIEW_URL", "http://code-review:8003")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            review_response = await client.post(
                f"{code_review_url}/review",
                json={
                    "task_id": request.task_id or feature_result.feature_id,
                    "diffs": [
                        {
                            "file_path": artifact.file_path,
                            "changes": artifact.content,
                            "context_lines": 5,
                        }
                        for artifact in feature_result.artifacts
                    ],
                    "test_results": {
                        "results": [result.dict() for result in feature_result.test_results]
                    },
                },
            )

            if review_response.status_code == 200:
                review_data = review_response.json()
                await mcp_client.log_event(
                    "feature_review_completed",
                    metadata={
                        "feature_id": feature_result.feature_id,
                        "approval": review_data.get("approval", False),
                        "findings": review_data.get("findings"),
                    },
                )
                return {
                    "feature_implementation": feature_result.dict(),
                    "code_review": review_data,
                    "workflow_status": "completed",
                    "approval": review_data.get("approval", False),
                }

            await mcp_client.log_event(
                "feature_review_failed",
                metadata={
                    "feature_id": feature_result.feature_id,
                    "status_code": review_response.status_code,
                },
                entity_type="feature_dev_error",
            )
            return {
                "feature_implementation": feature_result.dict(),
                "code_review": {"error": f"Review failed with status {review_response.status_code}"},
                "workflow_status": "partial",
                "approval": False,
            }
    except Exception as exc:  # noqa: BLE001
        await mcp_client.log_event(
            "feature_review_exception",
            metadata={"feature_id": feature_result.feature_id, "error": str(exc)},
            entity_type="feature_dev_error",
        )
        return {
            "feature_implementation": feature_result.dict(),
            "code_review": {"error": str(exc)},
            "workflow_status": "partial",
            "approval": False,
        }


@app.get("/patterns")
async def get_coding_patterns():
    """Retrieve cached coding patterns for token optimization."""

    return {
        "patterns": [
            {"name": "rest_api_handler", "description": "Standard REST API endpoint pattern"},
            {"name": "data_model", "description": "Pydantic data model with validation"},
            {"name": "service_layer", "description": "Business logic service pattern"},
            {"name": "repository_pattern", "description": "Data access layer pattern"},
        ],
        "cache_hit_rate": 0.72,
        "token_savings": "60-70%",
    }


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8002"))
    uvicorn.run(app, host="0.0.0.0", port=port)