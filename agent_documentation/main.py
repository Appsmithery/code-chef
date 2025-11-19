"""
Documentation Agent

Primary Role: Documentation generation and maintenance
- Generates README files, API documentation, and user guides
- Creates inline code comments and docstrings
- Updates documentation for code changes
- Maintains documentation templates and style guides
"""

from fastapi import FastAPI, HTTPException
from datetime import datetime
import uvicorn
import os
import logging
from prometheus_fastapi_instrumentator import Instrumentator

from service import (
    GuardrailViolation,
    DocRequest,
    DocResponse,
    list_doc_templates,
    mcp_client,
    process_doc_request,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# LangGraph Infrastructure
try:
    import sys
    sys.path.insert(0, '/app')
    from lib.langgraph_base import get_postgres_checkpointer, create_workflow_config
    from lib.qdrant_client import get_qdrant_client
    from lib.langchain_memory import create_hybrid_memory
    
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
    title="Documentation Agent",
    description="Documentation generation and maintenance",
    version="1.0.0"
)

# Enable Prometheus metrics collection
Instrumentator().instrument(app).expose(app)

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
    try:
        return await process_doc_request(request)
    except GuardrailViolation as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Guardrail checks failed",
                "report": exc.report.model_dump(mode="json"),
            },
        )

@app.get("/templates")
async def list_doc_templates_endpoint():
    return list_doc_templates()


# === Agent-to-Agent Communication (Phase 6) ===

from lib.agent_events import AgentRequestEvent, AgentResponseEvent, AgentRequestType
from lib.agent_request_handler import handle_agent_request
from typing import Dict, Any

@app.post("/agent-request", response_model=AgentResponseEvent, tags=["agent-communication"])
async def agent_request_endpoint(request: AgentRequestEvent):
    """
    Handle requests from other agents.
    
    Supports:
    - GENERATE_DOCS: Generate documentation from code
    - UPDATE_README: Update README with new content
    - EXPLAIN_CODE: Explain code in natural language
    - GET_STATUS: Query agent health
    """
    return await handle_agent_request(
        request=request,
        handler=handle_documentation_request,
        agent_name="documentation"
    )


async def handle_documentation_request(request: AgentRequestEvent) -> Dict[str, Any]:
    """
    Process agent requests for documentation tasks.
    
    Args:
        request: AgentRequestEvent with request_type and payload
    
    Returns:
        Dict with result data
    
    Raises:
        ValueError: If request type not supported
    """
    request_type = request.request_type
    payload = request.payload
    
    if request_type == AgentRequestType.GENERATE_DOCS:
        code = payload.get("code", "")
        format_type = payload.get("format", "markdown")
        
        if not code:
            raise ValueError("code required for GENERATE_DOCS")
        
        # Generate documentation (placeholder)
        return {
            "documentation": f"# Documentation\n\nGenerated docs for code",
            "format": format_type,
            "sections": ["overview", "usage", "examples"]
        }
    
    elif request_type == AgentRequestType.UPDATE_README:
        content = payload.get("content", "")
        section = payload.get("section", "")
        
        if not content:
            raise ValueError("content required for UPDATE_README")
        
        return {
            "updated": True,
            "section": section,
            "preview": content[:100]
        }
    
    elif request_type == AgentRequestType.EXPLAIN_CODE:
        code = payload.get("code", "")
        detail_level = payload.get("detail_level", "medium")
        
        if not code:
            raise ValueError("code required for EXPLAIN_CODE")
        
        return {
            "explanation": f"Code explanation at {detail_level} detail level",
            "complexity": "medium",
            "key_concepts": ["functions", "classes", "data structures"]
        }
    
    elif request_type == AgentRequestType.GET_STATUS:
        return {
            "status": "healthy",
            "capabilities": ["generate_docs", "update_readme", "explain_code"],
            "templates_available": True
        }
    
    else:
        raise ValueError(f"Unsupported request type: {request_type}")


if __name__ == '__main__':
    port = int(os.getenv("PORT", "8006"))
    uvicorn.run(app, host="0.0.0.0", port=port)