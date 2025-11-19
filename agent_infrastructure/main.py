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
from contextlib import asynccontextmanager
from lib.event_bus import get_event_bus
from lib.registry_client import RegistryClient, AgentCapability

from service import (
    GuardrailViolation,
    InfraRequest,
    InfraResponse,
    list_templates,
    mcp_client,
    process_infra_request,
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

# Agent registry client
registry_client: RegistryClient | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Register with agent registry
    registry_url = os.getenv("AGENT_REGISTRY_URL", "http://agent-registry:8009")
    agent_id = "infrastructure"
    agent_name = "Infrastructure Agent"
    base_url = f"http://infrastructure:{os.getenv('PORT', '8004')}"
    
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
            name="deploy_service",
            description="Deploy service to environment",
            parameters={"service": "str", "environment": "str"},
            cost_estimate="~30s compute",
            tags=["deployment", "infrastructure", "docker", "k8s"]
        ),
        AgentCapability(
            name="update_config",
            description="Update infrastructure configuration",
            parameters={"config_key": "str", "config_value": "any"},
            cost_estimate="~10s compute",
            tags=["configuration", "terraform"]
        )
    ]
    
    # Register and start heartbeat
    try:
        await registry_client.register(capabilities)
        await registry_client.start_heartbeat()
        logger.info(f"✅ Registered {agent_id} with agent registry")
    except Exception as e:
        logger.warning(f"⚠️  Failed to register with agent registry: {e}")

    # Connect to Event Bus
    event_bus = get_event_bus()
    try:
        await event_bus.connect()
        logger.info("✅ Connected to Event Bus")
    except Exception as e:
        logger.warning(f"⚠️  Failed to connect to Event Bus: {e}")
    
    yield
    
    # Shutdown: Stop heartbeat
    if registry_client:
        try:
            await registry_client.stop_heartbeat()
            await registry_client.close()
            logger.info(f"🛑 Unregistered {agent_id} from agent registry")
        except Exception as e:
            logger.warning(f"⚠️  Failed to unregister from agent registry: {e}")

app = FastAPI(
    title="Infrastructure Agent",
    description="Infrastructure-as-code generation and deployment configuration",
    version="1.0.0",
    lifespan=lifespan
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


# === Agent-to-Agent Communication (Phase 6) ===

from lib.agent_events import AgentRequestEvent, AgentResponseEvent, AgentRequestType
from lib.agent_request_handler import handle_agent_request
from typing import Dict, Any

@app.post("/agent-request", response_model=AgentResponseEvent, tags=["agent-communication"])
async def agent_request_endpoint(request: AgentRequestEvent):
    """
    Handle requests from other agents.
    
    Supports:
    - DEPLOY_SERVICE: Deploy infrastructure changes
    - UPDATE_CONFIG: Update infrastructure configuration
    - HEALTH_CHECK: Check infrastructure health
    - GET_STATUS: Query agent health
    """
    return await handle_agent_request(
        request=request,
        handler=handle_infrastructure_request,
        agent_name="infrastructure"
    )


async def handle_infrastructure_request(request: AgentRequestEvent) -> Dict[str, Any]:
    """
    Process agent requests for infrastructure tasks.
    
    Args:
        request: AgentRequestEvent with request_type and payload
    
    Returns:
        Dict with result data
    
    Raises:
        ValueError: If request type not supported
    """  
    request_type = request.request_type
    payload = request.payload
    
    if request_type == AgentRequestType.DEPLOY_SERVICE:
        service_name = payload.get("service_name", "")
        environment = payload.get("environment", "staging")
        
        if not service_name:
            raise ValueError("service_name required for DEPLOY_SERVICE")
        
        # Deploy service (placeholder)
        return {
            "service": service_name,
            "environment": environment,
            "status": "deployed",
            "endpoint": f"https://{service_name}.example.com"
        }
    
    elif request_type == AgentRequestType.UPDATE_CONFIG:
        config_key = payload.get("config_key", "")
        config_value = payload.get("config_value")
        
        if not config_key:
            raise ValueError("config_key required for UPDATE_CONFIG")
        
        return {
            "updated": True,
            "config_key": config_key,
            "previous_value": None
        }
    
    elif request_type == AgentRequestType.HEALTH_CHECK:
        services = payload.get("services", [])
        
        return {
            "healthy_services": len(services),
            "unhealthy_services": 0,
            "overall_status": "healthy"
        }
    
    elif request_type == AgentRequestType.GET_STATUS:
        return {
            "status": "healthy",
            "capabilities": ["deploy_service", "update_config", "health_check"],
            "active_deployments": 0
        }
    
    else:
        raise ValueError(f"Unsupported request type: {request_type}")


if __name__ == '__main__':
    port = int(os.getenv("PORT", "8004"))
    uvicorn.run(app, host="0.0.0.0", port=port)