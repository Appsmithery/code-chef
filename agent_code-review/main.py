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
from typing import Optional
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Agent Registry Client (Phase 6)
try:
    import sys
    sys.path.insert(0, '/app')
    from lib.registry_client import RegistryClient, AgentCapability
    
    registry_client: Optional[RegistryClient] = None
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Lifespan event handler for startup/shutdown"""
        # Startup: Register with agent registry
        registry_url = os.getenv("AGENT_REGISTRY_URL", "http://agent-registry:8009")
        agent_id = "code-review"
        agent_name = "Code Review Agent"
        base_url = f"http://code-review:{os.getenv('PORT', '8003')}"
        
        global registry_client
        registry_client = RegistryClient(
            registry_url=registry_url,
            agent_id=agent_id,
            agent_name=agent_name,
            base_url=base_url
        )
        
        # Define capabilities
        capabilities = [
            AgentCapability(
                name="review_pr",
                description="Review pull request for code quality and security",
                parameters={"repo_url": "str", "pr_number": "int"},
                cost_estimate="~100 tokens",
                tags=["git", "security", "code-quality"]
            ),
            AgentCapability(
                name="static_analysis",
                description="Perform static code analysis on diffs",
                parameters={"diff": "str", "language": "str"},
                cost_estimate="~50 tokens",
                tags=["analysis", "code-quality"]
            )
        ]
        
        # Register and start heartbeat
        try:
            await registry_client.register(capabilities)
            await registry_client.start_heartbeat()
            logger.info(f"✅ Registered {agent_id} with agent registry")
        except Exception as e:
            logger.warning(f"⚠️  Failed to register with agent registry: {e}")
        
        yield
        
        # Shutdown: Stop heartbeat
        try:
            await registry_client.stop_heartbeat()
            await registry_client.close()
            logger.info(f"🛑 Unregistered {agent_id} from agent registry")
        except Exception as e:
            logger.warning(f"⚠️  Failed to unregister from agent registry: {e}")
except ImportError:
    logger.warning("Registry client not available")
    lifespan = None

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
    title="Code Review Agent",
    description="Quality assurance, static analysis, and security scanning",
    version="1.0.0",
    lifespan=lifespan if lifespan else None
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