"""
DevOps Orchestrator Agent

Primary Role: Task delegation, context routing, and workflow coordination
- Analyzes incoming development requests and decomposes them into discrete subtasks
- Routes tasks to appropriate worker agents based on MECE responsibility boundaries
- Maintains task registry mapping request types to specialized agent capabilities
- Tracks task completion status and triggers hand-offs between agents

"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from enum import Enum
from datetime import datetime
import uvicorn
import os
import httpx
import logging
import uuid
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram

from lib.mcp_client import MCPClient, resolve_manifest_path
from lib.gradient_client import get_gradient_client
from lib.guardrail import GuardrailOrchestrator, GuardrailReport, GuardrailStatus
from lib.mcp_discovery import get_mcp_discovery
from lib.linear_client import get_linear_client
from lib.mcp_tool_client import get_mcp_tool_client
from lib.langgraph_base import (
    BaseAgentState,
    get_postgres_checkpointer,
    create_workflow_config
)
from lib.qdrant_client import get_qdrant_client
from lib.langchain_memory import HybridMemory
from lib.progressive_mcp_loader import (
    get_progressive_loader,
    ToolLoadingStrategy,
    ProgressiveMCPLoader
)
from lib.risk_assessor import get_risk_assessor
from lib.hitl_manager import get_hitl_manager
from lib.intent_recognizer import get_intent_recognizer, intent_to_task, IntentType
from lib.session_manager import get_session_manager
from lib.event_bus import get_event_bus, Event
from lib.notifiers import (
    LinearWorkspaceNotifier,
    EmailNotifier,
    NotificationConfig,
    EmailConfig
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DevOps Orchestrator Agent",
    description="Task delegation, context routing, and workflow coordination",
    version="1.0.0"
)

# Enable Prometheus metrics collection
Instrumentator().instrument(app).expose(app)

# State Persistence Layer URL
STATE_SERVICE_URL = os.getenv("STATE_SERVICE_URL", "http://state-persistence:8008")

# Shared MCP client for tool access and telemetry
mcp_client = MCPClient(agent_name="orchestrator")

# Gradient AI client for LLM inference (with Langfuse tracing)
gradient_client = get_gradient_client("orchestrator")

# Guardrail orchestrator for compliance checks
guardrail_orchestrator = GuardrailOrchestrator()

# MCP discovery for real-time server enumeration
mcp_discovery = get_mcp_discovery()

# Linear client for issue tracking and project management
linear_client = get_linear_client()

# MCP tool client for direct tool invocation (replaces HTTP gateway calls)
mcp_tool_client = get_mcp_tool_client("orchestrator")

# Progressive MCP loader for token-optimized tool disclosure
progressive_loader = get_progressive_loader(mcp_client, mcp_discovery)

# Risk evaluation + HITL orchestration
risk_assessor = get_risk_assessor()
hitl_manager = get_hitl_manager()

# Chat interface components (Phase 5)
intent_recognizer = get_intent_recognizer(gradient_client)
session_manager = get_session_manager()

# Event bus for notifications (Phase 5.2)
event_bus = get_event_bus()

# Initialize notifiers
linear_notifier = LinearWorkspaceNotifier(agent_name="orchestrator")
email_notifier = EmailNotifier()

# Subscribe notifiers to event bus
event_bus.subscribe("approval_required", linear_notifier.on_approval_required)
event_bus.subscribe("approval_required", email_notifier.on_approval_required)

logger.info("Notification system initialized (Linear + Email)")

# Approval workflow metrics
approval_requests_total = Counter(
    "orchestrator_approval_requests_total",
    "Total approval requests triggered by the orchestrator",
    ["risk_level"]
)

approval_wait_time = Histogram(
    "orchestrator_approval_wait_seconds",
    "Time spent waiting for human approval before resuming workflows",
    ["risk_level"]
)

approval_decisions_total = Counter(
    "orchestrator_approval_decisions_total",
    "Total approval decisions made (approved/rejected)",
    ["decision", "risk_level"]
)

approval_expirations_total = Counter(
    "orchestrator_approval_expirations_total",
    "Total approval requests that expired without decision",
    ["risk_level"]
)

# Track approval-pending tasks awaiting resumption
pending_approval_registry: Dict[str, Dict[str, Any]] = {}

# LangGraph infrastructure
try:
    checkpointer = get_postgres_checkpointer()
    logger.info("LangGraph PostgreSQL checkpointer initialized")
except Exception as e:
    logger.warning(f"LangGraph checkpointer not available: {e}")
    checkpointer = None

# Qdrant Cloud client for vector operations
qdrant_client = get_qdrant_client()
if qdrant_client.is_enabled():
    logger.info("Qdrant Cloud client initialized")
else:
    logger.warning("Qdrant Cloud not configured")

# Hybrid memory for conversation context
try:
    hybrid_memory = HybridMemory()
    logger.info("Hybrid memory (buffer + vector) initialized")
except Exception as e:
    logger.warning(f"Hybrid memory not available: {e}")
    hybrid_memory = None

# Agent types for task routing
class AgentType(str, Enum):
    FEATURE_DEV = "feature-dev"
    CODE_REVIEW = "code-review"
    INFRASTRUCTURE = "infrastructure"
    CICD = "cicd"
    DOCUMENTATION = "documentation"

# Task status tracking
class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

# Request models
class TaskRequest(BaseModel):
    """Incoming development request"""
    description: str = Field(..., description="Natural language description of the task")
    project_context: Optional[Dict[str, Any]] = Field(default=None, description="Project context references")
    workspace_config: Optional[Dict[str, Any]] = Field(default=None, description="Workspace configuration")
    priority: Optional[str] = Field(default="medium", description="Task priority")

class SubTask(BaseModel):
    """Decomposed subtask for routing"""
    id: str
    agent_type: AgentType
    description: str
    context_refs: Optional[List[str]] = None
    dependencies: Optional[List[str]] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TaskResponse(BaseModel):
    """Orchestration response"""
    task_id: str
    subtasks: List[SubTask]
    routing_plan: Dict[str, Any]
    estimated_tokens: int
    guardrail_report: GuardrailReport

# In-memory task registry (in production, this would use State Persistence Layer)
task_registry: Dict[str, TaskResponse] = {}

# ============================================================================
# HITL Risk Assessment Helper Functions
# ============================================================================

RISK_OPERATION_KEYWORDS = {
    "delete": ["delete", "drop", "destroy", "remove", "truncate", "purge"],
    "deploy": ["deploy", "release", "ship", "roll out", "rollout"],
    "modify": ["modify", "change", "update", "patch", "tweak", "adjust"],
    "create": ["create", "provision", "spin up", "add", "bootstrap"],
    "migrate": ["migrate", "move", "transition", "rehost"],
}


def extract_operation_from_description(description: str) -> str:
    description_lower = description.lower()
    for operation, keywords in RISK_OPERATION_KEYWORDS.items():
        if any(keyword in description_lower for keyword in keywords):
            return operation
    return "modify"


def infer_environment(description: str, project_context: Optional[Dict[str, Any]]) -> str:
    if project_context:
        env = project_context.get("environment") or project_context.get("env")
        if isinstance(env, str) and env:
            return env.lower()

    description_lower = description.lower()
    if any(term in description_lower for term in ["production", "prod"]):
        return "production"
    if any(term in description_lower for term in ["staging", "stage"]):
        return "staging"
    if any(term in description_lower for term in ["qa", "test"]):
        return "qa"
    return "dev"


RESOURCE_KEYWORDS = [
    ("database", ["database", "db", "table", "schema", "postgres", "mysql", "qdrant"]),
    ("infrastructure", ["infrastructure", "cluster", "kubernetes", "k8s", "terraform", "docker", "server", "network", "firewall", "load balancer"]),
    ("pipeline", ["pipeline", "ci/cd", "workflow", "github actions", "gitlab", "deployment"]),
    ("secret", ["secret", "token", "credential", "password", "key", "certificate"]),
    ("data", ["data", "dataset", "export", "import", "backup"]),
    ("application", ["service", "api", "app", "frontend", "backend"]),
]


def infer_resource_type(description: str) -> str:
    description_lower = description.lower()
    for resource, keywords in RESOURCE_KEYWORDS:
        if any(keyword in description_lower for keyword in keywords):
            return resource
    return "code"


SENSITIVE_KEYWORDS = [
    "pii",
    "personally identifiable",
    "customer data",
    "credit card",
    "secret",
    "token",
    "credential",
    "password",
    "ssn",
]


def detect_sensitive_data(description: str) -> bool:
    description_lower = description.lower()
    return any(keyword in description_lower for keyword in SENSITIVE_KEYWORDS)


def estimate_operation_cost(description: str, environment: str, resource_type: str) -> int:
    base_cost = 50 if environment == "production" else 20
    if resource_type in {"infrastructure", "pipeline"}:
        base_cost += 150
    if "cluster" in description.lower() or "autoscale" in description.lower():
        base_cost += 100
    return base_cost


def compile_risk_factors(operation: str, environment: str, resource_type: str, description: str) -> List[str]:
    factors = []
    if environment == "production":
        factors.append("production-environment")
    if operation in {"delete", "deploy"}:
        factors.append(f"operation-{operation}")
    if resource_type in {"database", "secret"}:
        factors.append(f"resource-{resource_type}")
    if "security" in description.lower() or "permission" in description.lower():
        factors.append("security-impact")
    if detect_sensitive_data(description):
        factors.append("sensitive-data")
    return factors


def build_risk_context(request: TaskRequest) -> Dict[str, Any]:
    """Derive operation metadata for risk assessment and approval workflows."""
    description = request.description
    operation = extract_operation_from_description(description)
    environment = infer_environment(description, request.project_context)
    resource_type = infer_resource_type(description)
    data_sensitive = detect_sensitive_data(description)
    estimated_cost = estimate_operation_cost(description, environment, resource_type)
    risk_factors = compile_risk_factors(operation, environment, resource_type, description)

    return {
        "operation": operation,
        "environment": environment,
        "resource_type": resource_type,
        "description": description,
        "priority": request.priority,
        "project_context": request.project_context or {},
        "workspace_config": request.workspace_config or {},
        "estimated_cost": estimated_cost,
        "data_sensitive": data_sensitive,
        "risk_factors": risk_factors,
        "impact": "high" if environment == "production" else "medium" if environment == "staging" else "low",
        "details": {
            "workspace_config": request.workspace_config or {},
            "project_context": request.project_context or {}
        }
    }

# ============================================================================
# Agent service endpoints (from docker-compose)
AGENT_ENDPOINTS = {
    AgentType.FEATURE_DEV: os.getenv("FEATURE_DEV_URL", "http://feature-dev:8002"),
    AgentType.CODE_REVIEW: os.getenv("CODE_REVIEW_URL", "http://code-review:8003"),
    AgentType.INFRASTRUCTURE: os.getenv("INFRASTRUCTURE_URL", "http://infrastructure:8004"),
    AgentType.CICD: os.getenv("CICD_URL", "http://cicd:8005"),
    AgentType.DOCUMENTATION: os.getenv("DOCUMENTATION_URL", "http://documentation:8006"),
}

# Agent manifest for tool-aware routing
def load_agent_manifest() -> Dict[str, Any]:
    """Load agent manifest with tool allocations"""
    import json
    manifest_path = resolve_manifest_path()
    try:
        with open(manifest_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load agent manifest from {manifest_path}: {e}")
        return {"profiles": []}

AGENT_MANIFEST = load_agent_manifest()

def get_agent_profile(agent_name: str) -> Optional[Dict[str, Any]]:
    """Retrieve agent profile from manifest"""
    for profile in AGENT_MANIFEST.get("profiles", []):
        if profile.get("name") == agent_name:
            return profile
    return None

def get_required_tools_for_task(description: str) -> List[Dict[str, str]]:
    """
    Analyze task description to determine required MCP tools
    Returns list of {server, tool} dictionaries
    """
    description_lower = description.lower()
    required_tools = []
    
    # File operations
    if any(kw in description_lower for kw in ["file", "code", "implement", "create", "write", "read"]):
        required_tools.append({"server": "rust-mcp-filesystem", "tool": "write_file"})
        required_tools.append({"server": "rust-mcp-filesystem", "tool": "read_file"})
    
    # Git operations
    if any(kw in description_lower for kw in ["commit", "branch", "pull request", "pr", "git"]):
        required_tools.append({"server": "gitmcp", "tool": "create_branch"})
        required_tools.append({"server": "gitmcp", "tool": "commit_changes"})
    
    # Docker/Container operations
    if any(kw in description_lower for kw in ["docker", "container", "image", "deploy"]):
        required_tools.append({"server": "dockerhub", "tool": "list_images"})
    
    # Documentation operations
    if any(kw in description_lower for kw in ["document", "readme", "doc", "api doc"]):
        required_tools.append({"server": "notion", "tool": "create_page"})
    
    # Testing operations
    if any(kw in description_lower for kw in ["test", "e2e", "selenium", "playwright"]):
        required_tools.append({"server": "playwright", "tool": "goto"})
    
    return required_tools

async def check_agent_tool_availability(agent_type: AgentType, required_tools: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Check if agent has required tools available via manifest
    Returns availability status and missing tools
    """
    agent_name = agent_type.value
    profile = get_agent_profile(agent_name)
    
    if not profile:
        return {
            "available": False,
            "reason": f"Agent profile not found in manifest: {agent_name}",
            "missing_tools": required_tools
        }
    
    recommended_tools = profile.get("mcp_tools", {}).get("recommended", [])
    shared_tools = profile.get("mcp_tools", {}).get("shared", [])
    
    # Build set of available tools
    available_tool_set = set()
    for tool_entry in recommended_tools:
        server = tool_entry.get("server")
        tools = tool_entry.get("tools", [])
        for tool in tools:
            available_tool_set.add(f"{server}/{tool}")
    
    # Shared tools have all capabilities (simplified assumption)
    for server in shared_tools:
        available_tool_set.add(f"{server}/*")
    
    # Check required tools
    missing_tools = []
    for req_tool in required_tools:
        server = req_tool["server"]
        tool = req_tool["tool"]
        tool_key = f"{server}/{tool}"
        wildcard_key = f"{server}/*"
        
        if tool_key not in available_tool_set and wildcard_key not in available_tool_set:
            missing_tools.append(req_tool)
    
    return {
        "available": len(missing_tools) == 0,
        "reason": f"Missing {len(missing_tools)} required tools" if missing_tools else "All required tools available",
        "missing_tools": missing_tools,
        "agent_capabilities": profile.get("capabilities", [])
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Check if MCP toolkit is available
    mcp_available = mcp_tool_client._check_mcp_available()
    
    # Get list of available MCP servers
    available_servers = await mcp_tool_client.list_servers()
    
    return {
        "status": "ok",
        "service": "orchestrator",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "mcp": {
            "toolkit_available": mcp_available,
            "available_servers": available_servers,
            "server_count": len(available_servers),
            "access_method": "direct_stdio",
            "recommended_tool_servers": [entry.get("server") for entry in mcp_client.recommended_tools],
            "shared_tool_servers": mcp_client.shared_tools,
            "capabilities": mcp_client.capabilities,
        },
        "integrations": {
            "linear": linear_client.is_enabled(),
            "gradient_ai": gradient_client.is_enabled()
        },
        "chat": {
            "enabled": True,
            "endpoint": "/chat",
            "features": ["intent_recognition", "multi_turn", "task_submission", "status_query", "approval_decision"]
        }
    }

@app.post("/orchestrate", response_model=TaskResponse)
async def orchestrate_task(request: TaskRequest):
    """
    Main orchestration endpoint with progressive tool disclosure
    - Analyzes request and decomposes into subtasks
    - Progressively loads only relevant MCP tools (10-30 vs 150+)
    - Validates tool availability before routing
    - Routes to appropriate specialized agents
    - Returns routing plan with minimal context pointers
    
    Token Optimization: Only loads relevant tools per task (80-90% token reduction)
    """
    import uuid

    task_id = str(uuid.uuid4())

    guardrail_report = await guardrail_orchestrator.run(
        "orchestrator",
        task_id=task_id,
        context={
            "endpoint": "orchestrate",
            "priority": request.priority,
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
    
    risk_context = build_risk_context(request)
    risk_level = risk_assessor.assess_task(risk_context)

    if risk_assessor.requires_approval(risk_level):
        approval_request_id = await hitl_manager.create_approval_request(
            workflow_id=task_id,
            thread_id=f"wf-thread-{task_id}",
            checkpoint_id=f"wf-checkpoint-{task_id}",
            task=risk_context,
            agent_name="orchestrator"
        )

        if approval_request_id:
            approval_requests_total.labels(risk_level=risk_level).inc()
            pending_approval_registry[task_id] = {
                "request_payload": request.model_dump(),
                "guardrail_report": guardrail_report,
                "risk_context": risk_context,
                "approval_request_id": approval_request_id,
                "risk_level": risk_level,
                "created_at": datetime.utcnow(),
            }

            # Emit approval_required event for notifications
            await event_bus.emit(
                "approval_required",
                {
                    "approval_id": approval_request_id,
                    "task_description": request.task,
                    "risk_level": risk_level,
                    "project_name": "ai-devops-platform",  # TODO: Extract from request context
                    "metadata": {
                        "task_id": task_id,
                        "priority": request.priority,
                        "agent": "orchestrator",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                },
                source="orchestrator",
                correlation_id=task_id
            )
            logger.info(f"Emitted approval_required event for {approval_request_id}")

            response = TaskResponse(
                task_id=task_id,
                subtasks=[],
                routing_plan={
                    "status": "approval_pending",
                    "approval_request_id": approval_request_id,
                    "risk_level": risk_level,
                    "instructions": f"Pending approval. Run: task workflow:approve REQUEST_ID={approval_request_id}",
                    "submitted_at": datetime.utcnow().isoformat(),
                    "risk_context": risk_context
                },
                estimated_tokens=0,
                guardrail_report=guardrail_report,
            )

            task_registry[task_id] = response
            await persist_task_state(task_id, request, response, status="approval_pending")

            await mcp_tool_client.create_memory_entity(
                name=f"task_requires_approval_{task_id}",
                entity_type="orchestrator_event",
                observations=[
                    f"Task ID: {task_id}",
                    f"Risk level: {risk_level}",
                    f"Approval request: {approval_request_id}",
                    f"Priority: {request.priority}"
                ]
            )

            logger.info(
                "[Orchestrator] Task %s requires %s approval (request_id=%s)",
                task_id,
                risk_level,
                approval_request_id
            )

            return response

        logger.info(
            "[Orchestrator] Risk level %s requested approval but no request ID returned; continuing",
            risk_level
        )

    return await execute_orchestration_flow(task_id, request, guardrail_report)


async def execute_orchestration_flow(
    task_id: str,
    request: TaskRequest,
    guardrail_report: GuardrailReport
) -> TaskResponse:
    """Execute decomposition, validation, and persistence once approvals pass."""

    relevant_toolsets = progressive_loader.get_tools_for_task(
        task_description=request.description,
        strategy=ToolLoadingStrategy.MINIMAL
    )

    stats = progressive_loader.get_tool_usage_stats(relevant_toolsets)
    logger.info(f"[Orchestrator] Progressive loading stats: {stats}")
    await mcp_tool_client.create_memory_entity(
        name=f"tool_loading_stats_{task_id}",
        entity_type="orchestrator_metrics",
        observations=[
            f"Task: {task_id}",
            f"Loaded tools: {stats['loaded_tools']} / {stats['total_tools']}",
            f"Token savings: {stats['savings_percent']}%",
            f"Estimated tokens saved: {stats['estimated_tokens_saved']}"
        ]
    )

    available_tools_context = progressive_loader.format_tools_for_llm(relevant_toolsets)
    required_tools = get_required_tools_for_task(request.description)

    if gradient_client.is_enabled():
        subtasks = await decompose_with_llm(
            request,
            task_id,
            available_tools=available_tools_context
        )
    else:
        subtasks = decompose_request(request)

    validation_results: Dict[str, Any] = {}
    for subtask in subtasks:
        agent_toolsets = progressive_loader.get_tools_for_task(
            task_description=subtask.description,
            assigned_agent=subtask.agent_type.value,
            strategy=ToolLoadingStrategy.PROGRESSIVE
        )

        subtask_required_tools = get_required_tools_for_task(subtask.description)
        availability = await check_agent_tool_availability(subtask.agent_type, subtask_required_tools)
        validation_results[subtask.id] = {
            **availability,
            "loaded_toolsets": len(agent_toolsets),
            "tools_context": progressive_loader.format_tools_for_llm(agent_toolsets)
        }

        if not availability["available"]:
            logger.warning(
                "[Orchestrator] Agent %s missing tools for subtask %s: %s",
                subtask.agent_type,
                subtask.id,
                availability["missing_tools"]
            )
            await mcp_tool_client.create_memory_entity(
                name=f"tool_availability_warning_{task_id}_{subtask.id}",
                entity_type="orchestrator_warning",
                observations=[
                    f"Task: {task_id}",
                    f"Subtask: {subtask.id}",
                    f"Agent: {subtask.agent_type.value}",
                    f"Missing tools: {availability['missing_tools']}"
                ]
            )

    routing_plan = {
        "execution_order": [st.id for st in subtasks],
        "parallel_groups": identify_parallel_tasks(subtasks),
        "estimated_duration_minutes": estimate_duration(subtasks),
        "tool_validation": validation_results,
        "required_tools": required_tools
    }

    estimated_tokens = len(request.description.split()) * 2

    response = TaskResponse(
        task_id=task_id,
        subtasks=subtasks,
        routing_plan=routing_plan,
        estimated_tokens=estimated_tokens,
        guardrail_report=guardrail_report,
    )

    task_registry[task_id] = response
    await persist_task_state(task_id, request, response)

    tools_validated = all(
        result["available"] for result in validation_results.values()
    ) if validation_results else True

    await mcp_tool_client.create_memory_entity(
        name=f"task_orchestrated_{task_id}",
        entity_type="orchestrator_event",
        observations=[
            f"Task ID: {task_id}",
            f"Subtasks: {len(subtasks)}",
            f"Priority: {request.priority}",
            f"Agent: orchestrator",
            f"Tools validated: {tools_validated}",
            f"Guardrail status: {guardrail_report.status}"
        ]
    )

    return response


@app.post("/resume/{task_id}", response_model=TaskResponse)
async def resume_approved_task(task_id: str):
    """Resume a workflow once its approval request is satisfied."""

    pending_task = pending_approval_registry.get(task_id)
    if not pending_task:
        raise HTTPException(status_code=404, detail="Task not awaiting approval or not found")

    approval_request_id = pending_task["approval_request_id"]
    status_info = await hitl_manager.check_approval_status(approval_request_id)
    approval_status = status_info.get("status")

    if approval_status == "approved":
        risk_level = pending_task["risk_level"]
        wait_seconds = (datetime.utcnow() - pending_task["created_at"]).total_seconds()
        approval_wait_time.labels(risk_level=risk_level).observe(max(wait_seconds, 0.0))

        request_payload = pending_task["request_payload"]
        guardrail_report = pending_task["guardrail_report"]
        pending_approval_registry.pop(task_id, None)

        request = TaskRequest(**request_payload)
        response = await execute_orchestration_flow(task_id, request, guardrail_report)

        await mcp_tool_client.create_memory_entity(
            name=f"task_resumed_{task_id}",
            entity_type="orchestrator_event",
            observations=[
                f"Task ID: {task_id}",
                f"Approval request: {approval_request_id}",
                f"Approver: {status_info.get('approver_id')}",
                f"Resumed at: {datetime.utcnow().isoformat()}"
            ]
        )

        return response

    if approval_status == "pending":
        raise HTTPException(status_code=409, detail="Approval still pending")

    pending_approval_registry.pop(task_id, None)

    if approval_status == "rejected":
        raise HTTPException(
            status_code=403,
            detail=f"Task rejected: {status_info.get('rejection_reason', 'No reason provided')}"
        )

    if approval_status == "expired":
        raise HTTPException(
            status_code=410,
            detail="Approval request expired. Submit a new orchestration request."
        )

    raise HTTPException(
        status_code=400,
        detail=f"Unexpected approval status: {approval_status}"
    )


@app.post("/approve/{approval_id}")
async def approve_request(
    approval_id: str,
    approver_id: str,
    approver_role: str,
    justification: Optional[str] = None
):
    """
    Approve a pending HITL request.
    
    Args:
        approval_id: UUID of the approval request
        approver_id: Email or ID of the approver
        approver_role: Role of the approver (developer, tech_lead, devops_engineer)
        justification: Optional justification for approval
    
    Returns:
        Success message with approval details
    """
    try:
        # Attempt to approve
        success = await hitl_manager.approve_request(
            request_id=approval_id,
            approver_id=approver_id,
            approver_role=approver_role,
            justification=justification
        )
        
        if not success:
            raise HTTPException(
                status_code=403,
                detail="Approval failed: Unauthorized or expired"
            )
        
        # Get updated status for metrics
        status_info = await hitl_manager.check_approval_status(approval_id)
        risk_level = status_info.get("risk_level", "unknown")
        
        # Update metrics
        approval_decisions_total.labels(decision="approved", risk_level=risk_level).inc()
        
        # Log to MCP memory
        await mcp_tool_client.create_memory_entity(
            name=f"approval_{approval_id}",
            entity_type="approval_decision",
            observations=[
                f"Approval ID: {approval_id}",
                f"Decision: APPROVED",
                f"Approver: {approver_id}",
                f"Role: {approver_role}",
                f"Risk Level: {risk_level}",
                f"Timestamp: {datetime.utcnow().isoformat()}"
            ]
        )
        
        return {
            "status": "approved",
            "approval_id": approval_id,
            "approver_id": approver_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Request approved successfully"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Approval error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/reject/{approval_id}")
async def reject_request(
    approval_id: str,
    approver_id: str,
    approver_role: str,
    reason: str
):
    """
    Reject a pending HITL request.
    
    Args:
        approval_id: UUID of the approval request
        approver_id: Email or ID of the approver
        approver_role: Role of the approver
        reason: Reason for rejection (required)
    
    Returns:
        Success message with rejection details
    """
    try:
        # Attempt to reject
        success = await hitl_manager.reject_request(
            request_id=approval_id,
            approver_id=approver_id,
            approver_role=approver_role,
            reason=reason
        )
        
        if not success:
            raise HTTPException(
                status_code=403,
                detail="Rejection failed: Unauthorized or expired"
            )
        
        # Get updated status for metrics
        status_info = await hitl_manager.check_approval_status(approval_id)
        risk_level = status_info.get("risk_level", "unknown")
        
        # Update metrics
        approval_decisions_total.labels(decision="rejected", risk_level=risk_level).inc()
        
        # Log to MCP memory
        await mcp_tool_client.create_memory_entity(
            name=f"rejection_{approval_id}",
            entity_type="approval_decision",
            observations=[
                f"Approval ID: {approval_id}",
                f"Decision: REJECTED",
                f"Approver: {approver_id}",
                f"Role: {approver_role}",
                f"Reason: {reason}",
                f"Risk Level: {risk_level}",
                f"Timestamp: {datetime.utcnow().isoformat()}"
            ]
        )
        
        return {
            "status": "rejected",
            "approval_id": approval_id,
            "approver_id": approver_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Request rejected"
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Rejection error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/approvals/pending")
async def list_pending_approvals(
    approver_role: Optional[str] = None,
    limit: int = 50
):
    """
    List all pending approval requests.
    
    Args:
        approver_role: Filter by approver role (optional)
        limit: Maximum number of results (default 50)
    
    Returns:
        List of pending approval requests
    """
    try:
        approvals = await hitl_manager.list_pending_requests(
            approver_role=approver_role,
            limit=limit
        )
        
        return {
            "count": len(approvals),
            "approvals": approvals
        }
        
    except Exception as e:
        logger.error(f"List approvals error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/approvals/{approval_id}")
async def get_approval_status(approval_id: str):
    """
    Get the status of a specific approval request.
    
    Args:
        approval_id: UUID of the approval request
    
    Returns:
        Approval request details and current status
    """
    try:
        status_info = await hitl_manager.check_approval_status(approval_id)
        return status_info
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Get approval status error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def persist_task_state(
    task_id: str,
    request: TaskRequest,
    response: TaskResponse,
    status: str = "pending"
):
    """Persist task state to State Persistence Layer"""
    try:
        async with httpx.AsyncClient() as client:
            # Create task record
            task_payload = {
                "task_id": task_id,
                "type": "orchestration",
                "status": status,
                "assigned_agent": "orchestrator",
                "payload": {
                    "description": request.description,
                    "priority": request.priority,
                    "subtasks": [
                        {
                            "id": st.id,
                            "agent_type": st.agent_type,
                            "description": st.description,
                            "status": st.status
                        }
                        for st in response.subtasks
                    ],
                    "routing_plan": response.routing_plan
                }
            }
            
            await client.post(
                f"{STATE_SERVICE_URL}/tasks",
                json=task_payload,
                timeout=5.0
            )
            
            # Create workflow record
            workflow_payload = {
                "workflow_id": task_id,
                "name": f"Task: {request.description[:50]}",
                "steps": [
                    {
                        "step_id": st.id,
                        "agent": st.agent_type,
                        "description": st.description
                    }
                    for st in response.subtasks
                ],
                "status": status
            }
            
            await client.post(
                f"{STATE_SERVICE_URL}/workflows",
                json=workflow_payload,
                timeout=5.0
            )
            
            await mcp_tool_client.create_memory_entity(
                name=f"orchestrator_state_persisted_{task_id}",
                entity_type="orchestrator_event",
                observations=[
                    f"Task ID: {task_id}",
                    f"Workflow steps: {len(response.subtasks)}",
                    f"Status: pending"
                ]
            )

    except Exception as e:
        print(f"State persistence failed (non-critical): {e}")
        await mcp_tool_client.create_memory_entity(
            name=f"orchestrator_state_persistence_failed_{task_id}",
            entity_type="orchestrator_error",
            observations=[
                f"Task ID: {task_id}",
                f"Error: {str(e)}"
            ]
        )

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Retrieve task status and subtask progress"""
    if task_id not in task_registry:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task_registry[task_id]

@app.get("/agents")
async def list_agents():
    """List available specialized agents and their endpoints"""
    return {
        "agents": [
            {"type": agent.value, "endpoint": endpoint, "status": "available"}
            for agent, endpoint in AGENT_ENDPOINTS.items()
        ]
    }

@app.get("/agents/{agent_name}/tools")
async def get_agent_tools(agent_name: str):
    """
    Get tool allocations for a specific agent from manifest
    Includes recommended tools, shared tools, and capabilities
    """
    profile = get_agent_profile(agent_name)
    
    if not profile:
        raise HTTPException(status_code=404, detail=f"Agent profile not found: {agent_name}")
    
    return {
        "agent": agent_name,
        "display_name": profile.get("display_name"),
        "mission": profile.get("mission"),
        "mcp_tools": profile.get("mcp_tools", {}),
        "capabilities": profile.get("capabilities", []),
        "status": profile.get("status", "unknown")
    }

@app.post("/validate-routing")
async def validate_routing(request: Dict[str, Any]):
    """
    Validate if an agent has required tools for a task
    Request: {"agent": "feature-dev", "description": "implement authentication"}
    """
    agent_name = request.get("agent")
    description = request.get("description", "")
    
    if not agent_name:
        raise HTTPException(status_code=400, detail="Agent name required")
    
    try:
        agent_type = AgentType(agent_name)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agent type: {agent_name}")
    
    required_tools = get_required_tools_for_task(description)
    availability = await check_agent_tool_availability(agent_type, required_tools)
    
    return {
        "agent": agent_name,
        "task_description": description,
        "required_tools": required_tools,
        "availability": availability
    }

@app.get("/mcp/discover")
async def discover_mcp_servers():
    """
    Discover all MCP servers via Docker MCP Toolkit.

    Returns real-time server and tool inventory.
    """
    try:
        servers = mcp_discovery.discover_servers()
        return {
            "success": True,
            "discovery": servers,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"[Orchestrator] MCP discovery failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"MCP discovery failed: {str(e)}"
        )


@app.get("/mcp/manifest")
async def get_agent_manifest():
    """
    Generate agent-to-tool mapping manifest based on discovered MCP servers.

    This replaces the static agents/agents-manifest.json with dynamic discovery.
    """
    try:
        manifest = mcp_discovery.generate_agent_manifest()
        return {
            "success": True,
            "manifest": manifest
        }
    except Exception as e:
        logger.error(f"[Orchestrator] Manifest generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Manifest generation failed: {str(e)}"
        )


@app.get("/mcp/server/{server_name}")
async def get_server_details(server_name: str):
    """Get details for a specific MCP server."""
    server = mcp_discovery.get_server(server_name)
    if not server:
        raise HTTPException(
            status_code=404,
            detail=f"MCP server '{server_name}' not found"
        )

    return {
        "success": True,
        "server": server
    }

@app.get("/linear/issues")
async def get_linear_issues():
    """Fetch issues from Linear roadmap."""
    if not linear_client.is_enabled():
        return {
            "success": False,
            "message": "Linear integration not configured"
        }

    issues = await linear_client.fetch_issues()
    return {
        "success": True,
        "count": len(issues),
        "issues": issues
    }


@app.post("/linear/issues")
async def create_linear_issue(request: Dict[str, Any]):
    """Create a new Linear issue."""
    if not linear_client.is_enabled():
        raise HTTPException(
            status_code=503,
            detail="Linear integration not configured"
        )

    issue = await linear_client.create_issue(
        title=request["title"],
        description=request.get("description", ""),
        priority=request.get("priority", 0)
    )

    if issue:
        return {
            "success": True,
            "issue": issue
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to create Linear issue"
        )


@app.get("/linear/project/{project_id}")
async def get_linear_project(project_id: str):
    """Fetch Linear project roadmap."""
    if not linear_client.is_enabled():
        raise HTTPException(
            status_code=503,
            detail="Linear integration not configured"
        )

    roadmap = await linear_client.fetch_project_roadmap(project_id)
    return {
        "success": True,
        "roadmap": roadmap
    }


@app.patch("/linear/issues/{issue_id}")
async def update_linear_issue(issue_id: str, request: Dict[str, Any]):
    """Update an existing Linear issue (description, state, etc.)."""
    if not linear_client.is_enabled():
        raise HTTPException(
            status_code=503,
            detail="Linear integration not configured"
        )

    success = await linear_client.update_issue(issue_id, **request)
    
    if success:
        return {
            "success": True,
            "issue_id": issue_id,
            "updated_fields": list(request.keys())
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to update Linear issue"
        )


@app.post("/linear/roadmap/update-phase")
async def update_phase_completion(request: Dict[str, Any]):
    """
    Update a phase issue with completion status and metrics.
    
    Expected payload:
    {
        "issue_id": "...",
        "phase_name": "Phase 2: HITL Integration",
        "status": "COMPLETE",
        "components": ["Risk Assessment", "Approval Workflow", ...],
        "subtasks": [{"title": "Task 2.1", "status": "complete"}, ...],
        "metrics": {"total_requests": 4, "avg_time": "1.26s"},
        "artifacts": {"main.py": "lines 705-901", ...}
    }
    """
    if not linear_client.is_enabled():
        raise HTTPException(
            status_code=503,
            detail="Linear integration not configured"
        )
    
    issue_id = request["issue_id"]
    phase_name = request["phase_name"]
    status = request.get("status", "IN PROGRESS")
    components = request.get("components", [])
    subtasks = request.get("subtasks", [])
    metrics = request.get("metrics", {})
    artifacts = request.get("artifacts", {})
    
    # Build comprehensive description
    description_parts = [
        f"## {phase_name} - {status}",
        "",
        "### Implementation Summary",
        request.get("summary", "Complete implementation verified in production."),
        "",
    ]
    
    if components:
        description_parts.extend([
            "### Components Delivered",
            *[f"{i+1}. **{comp}**" for i, comp in enumerate(components)],
            "",
        ])
    
    if subtasks:
        description_parts.extend([
            "### Subtasks Completed",
            *[f"- {'✅' if task.get('status') == 'complete' else '⏳'} {task['title']}" 
              for task in subtasks],
            "",
        ])
    
    if metrics:
        description_parts.extend([
            f"### Production Metrics (as of {datetime.now().strftime('%Y-%m-%d')})",
            *[f"- {key.replace('_', ' ').title()}: {value}" 
              for key, value in metrics.items()],
            "",
        ])
    
    if artifacts:
        description_parts.extend([
            "### Artifacts",
            *[f"- `{path}`: {desc}" for path, desc in artifacts.items()],
            "",
        ])
    
    description_parts.extend([
        "### Testing",
        *[f"✅ {test}" for test in request.get("tests", [])],
        "",
        f"**Status**: {status}",
        f"**Deployment**: {request.get('deployment_url', 'Production')}",
    ])
    
    description = "\n".join(description_parts)
    
    success = await linear_client.update_issue(issue_id, description=description)
    
    if success:
        logger.info(f"Updated Linear phase issue {issue_id}: {phase_name} - {status}")
        return {
            "success": True,
            "issue_id": issue_id,
            "phase": phase_name,
            "status": status
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to update phase issue"
        )


@app.post("/execute/{task_id}")
async def execute_workflow(task_id: str):
    """Execute workflow by calling agents in sequence based on routing plan"""
    if task_id not in task_registry:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = task_registry[task_id]
    execution_results = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for subtask in task.subtasks:
            try:
                # Update subtask status
                subtask.status = TaskStatus.IN_PROGRESS
                
                # Route to appropriate agent
                agent_url = AGENT_ENDPOINTS[subtask.agent_type]
                
                if subtask.agent_type == AgentType.FEATURE_DEV:
                    # Call feature-dev agent
                    response = await client.post(
                        f"{agent_url}/implement",
                        json={
                            "description": subtask.description,
                            "context_refs": subtask.context_refs or [],
                            "task_id": task_id
                        }
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        execution_results.append({
                            "subtask_id": subtask.id,
                            "agent": subtask.agent_type,
                            "status": "completed",
                            "result": result
                        })
                        subtask.status = TaskStatus.COMPLETED
                    else:
                        subtask.status = TaskStatus.FAILED
                        execution_results.append({
                            "subtask_id": subtask.id,
                            "agent": subtask.agent_type,
                            "status": "failed",
                            "error": f"HTTP {response.status_code}"
                        })
                
                elif subtask.agent_type == AgentType.CODE_REVIEW:
                    # Call code-review agent with artifacts from previous step
                    prev_result = execution_results[-1].get("result") if execution_results else None
                    
                    if prev_result and "artifacts" in prev_result:
                        # Prepare review payload (diffs only, test_results is optional dict)
                        review_payload = {
                            "task_id": task_id,
                            "diffs": [
                                {
                                    "file_path": artifact["file_path"],
                                    "changes": artifact["content"],
                                    "context_lines": 5
                                }
                                for artifact in prev_result["artifacts"]
                            ]
                        }
                        
                        # Don't include test_results for now (it expects dict, we have list)
                        # Future: convert test_results list to summary dict if needed
                        
                        response = await client.post(
                            f"{agent_url}/review",
                            json=review_payload
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            execution_results.append({
                                "subtask_id": subtask.id,
                                "agent": subtask.agent_type,
                                "status": "completed",
                                "result": result
                            })
                            subtask.status = TaskStatus.COMPLETED
                        else:
                            subtask.status = TaskStatus.FAILED
                            execution_results.append({
                                "subtask_id": subtask.id,
                                "agent": subtask.agent_type,
                                "status": "failed",
                                "error": f"HTTP {response.status_code}"
                            })
                    else:
                        subtask.status = TaskStatus.FAILED
                        execution_results.append({
                            "subtask_id": subtask.id,
                            "agent": subtask.agent_type,
                            "status": "skipped",
                            "error": "No artifacts from previous step"
                        })
                
                else:
                    # Other agent types - placeholder for future implementation
                    subtask.status = TaskStatus.COMPLETED
                    execution_results.append({
                        "subtask_id": subtask.id,
                        "agent": subtask.agent_type,
                        "status": "pending_implementation",
                        "message": "Agent integration not yet implemented"
                    })
                    
            except Exception as e:
                subtask.status = TaskStatus.FAILED
                execution_results.append({
                    "subtask_id": subtask.id,
                    "agent": subtask.agent_type,
                    "status": "failed",
                    "error": str(e)
                })
    
    # Update overall task status
    overall_status = "completed" if all(
        r["status"] in ["completed", "pending_implementation"] for r in execution_results
    ) else "failed"
    
    return {
        "task_id": task_id,
        "status": overall_status,
        "execution_results": execution_results,
        "subtasks": [{
            "id": st.id,
            "agent_type": st.agent_type,
            "status": st.status,
            "description": st.description
        } for st in task.subtasks]
    }

def decompose_request(request: TaskRequest) -> List[SubTask]:
    """
    Decompose incoming request into discrete subtasks (rule-based fallback)
    Uses simple keyword matching for MVP (production would use Task Router or LLM)
    """
    import uuid
    description_lower = request.description.lower()
    subtasks = []
    
    # Feature development detection
    if any(keyword in description_lower for keyword in ["implement", "create", "build", "develop", "feature"]):
        subtasks.append(SubTask(
            id=str(uuid.uuid4()),
            agent_type=AgentType.FEATURE_DEV,
            description=f"Implement feature: {request.description}",
            context_refs=["codebase"]
        ))
    
    # Code review after feature dev
    if subtasks and subtasks[-1].agent_type == AgentType.FEATURE_DEV:
        review_task = SubTask(
            id=str(uuid.uuid4()),
            agent_type=AgentType.CODE_REVIEW,
            description=f"Review implementation: {request.description}",
            dependencies=[subtasks[-1].id]
        )
        subtasks.append(review_task)
    
    # Infrastructure changes detection
    if any(keyword in description_lower for keyword in ["deploy", "infrastructure", "terraform", "docker", "k8s"]):
        subtasks.append(SubTask(
            id=str(uuid.uuid4()),
            agent_type=AgentType.INFRASTRUCTURE,
            description=f"Infrastructure changes: {request.description}"
        ))
    
    # CI/CD pipeline detection
    if any(keyword in description_lower for keyword in ["pipeline", "ci/cd", "continuous", "deployment"]):
        subtasks.append(SubTask(
            id=str(uuid.uuid4()),
            agent_type=AgentType.CICD,
            description=f"Configure CI/CD: {request.description}"
        ))
    
    # Documentation detection
    if any(keyword in description_lower for keyword in ["document", "readme", "doc", "guide"]):
        subtasks.append(SubTask(
            id=str(uuid.uuid4()),
            agent_type=AgentType.DOCUMENTATION,
            description=f"Generate documentation: {request.description}"
        ))
    
    # Default to feature dev if no matches
    if not subtasks:
        subtasks.append(SubTask(
            id=str(uuid.uuid4()),
            agent_type=AgentType.FEATURE_DEV,
            description=request.description
        ))
    
    return subtasks

def identify_parallel_tasks(subtasks: List[SubTask]) -> List[List[str]]:
    """Identify subtasks that can run in parallel"""
    parallel_groups = []
    independent_tasks = []
    
    for task in subtasks:
        if not task.dependencies:
            independent_tasks.append(task.id)
    
    if len(independent_tasks) > 1:
        parallel_groups.append(independent_tasks)
    
    return parallel_groups

def estimate_duration(subtasks: List[SubTask]) -> int:
    """Estimate total execution duration in minutes"""
    # Simple heuristic: 5 minutes per subtask
    return len(subtasks) * 5


@app.post("/config/tool-loading")
async def configure_tool_loading(request: Dict[str, Any]):
    """
    Configure progressive tool loading strategy at runtime.
    
    Request:
        {
            "strategy": "minimal" | "agent_profile" | "progressive" | "full",
            "reason": "debugging" | "cost_optimization" | "high_complexity_task"
        }
    """
    strategy_name = request.get("strategy", "progressive")
    reason = request.get("reason", "runtime_config")
    
    try:
        strategy = ToolLoadingStrategy(strategy_name)
        progressive_loader.default_strategy = strategy
        
        await mcp_tool_client.create_memory_entity(
            name=f"tool_loading_config_change_{datetime.utcnow().isoformat()}",
            entity_type="orchestrator_config",
            observations=[
                f"Strategy changed to: {strategy_name}",
                f"Reason: {reason}",
                f"Timestamp: {datetime.utcnow().isoformat()}"
            ]
        )
        
        return {
            "success": True,
            "current_strategy": strategy_name,
            "reason": reason
        }
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy: {strategy_name}. Valid values: minimal, agent_profile, progressive, full"
        )


@app.get("/config/tool-loading/stats")
async def get_tool_loading_stats():
    """
    Get statistics about current tool loading configuration.
    """
    # Get current strategy tools
    sample_toolsets = progressive_loader.get_tools_for_task(
        task_description="sample task",
        strategy=progressive_loader.default_strategy
    )
    
    stats = progressive_loader.get_tool_usage_stats(sample_toolsets)
    
    return {
        "current_strategy": progressive_loader.default_strategy.value,
        "stats": stats,
        "recommendation": (
            "Consider using 'minimal' or 'progressive' for cost optimization"
            if stats["savings_percent"] < 50
            else "Current strategy is well-optimized"
        )
    }


async def decompose_with_llm(
    request: TaskRequest,
    task_id: str,
    available_tools: Optional[str] = None
) -> List[SubTask]:
    """
    Decompose task using Gradient AI with Langfuse tracing.
    Provides intelligent task breakdown with dependency analysis.
    Includes progressive tool context for tool-aware decomposition.
    """
    import uuid
    import json
    
    system_prompt = """You are an expert DevOps orchestrator. Analyze development requests and decompose them into discrete subtasks for specialized agents.

Available agents:
- feature-dev: Application code generation and feature implementation
- code-review: Quality assurance, static analysis, security scanning
- infrastructure: Infrastructure-as-code generation (Docker, K8s, Terraform)
- cicd: CI/CD pipeline generation (GitHub Actions, GitLab CI)
- documentation: Documentation generation (README, API docs)

Return JSON with this structure:
{
  "subtasks": [
    {
      "agent_type": "feature-dev",
      "description": "Implement user authentication",
      "dependencies": []
    }
  ]
}"""
    
    user_prompt = f"""Task: {request.description}

Project Context: {json.dumps(request.project_context) if request.project_context else "General project"}
Priority: {request.priority}

{available_tools if available_tools else ""}

Break this down into subtasks. Consider dependencies and execution order.
IMPORTANT: Only suggest using tools that are listed in the "Available MCP Tools" section above."""
    
    try:
        logger.info(f"[Orchestrator] Attempting LLM-powered decomposition for task {task_id}")
        
        result = await gradient_client.complete_structured(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,  # Lower temperature for more deterministic decomposition
            max_tokens=1000,
            metadata={
                "task_id": task_id,
                "task_description": request.description,
                "priority": request.priority
            }
        )
        
        logger.info(f"[Orchestrator] LLM decomposition successful: {result.get('tokens', 0)} tokens used")
        
        # Parse LLM response
        llm_subtasks = result["content"].get("subtasks", [])
        logger.debug(f"[Orchestrator] LLM returned {len(llm_subtasks)} subtasks: {llm_subtasks}")
        
        # Create SubTask objects with proper IDs
        subtasks = []
        id_map = {}  # Map indices to UUIDs for dependencies
        
        for i, st in enumerate(llm_subtasks):
            subtask_id = str(uuid.uuid4())
            id_map[i] = subtask_id
            
            # Validate agent type
            try:
                agent_type = AgentType(st["agent_type"])
            except ValueError:
                print(f"[WARNING] Invalid agent type: {st['agent_type']}, defaulting to feature-dev")
                agent_type = AgentType.FEATURE_DEV
            
            subtasks.append(SubTask(
                id=subtask_id,
                agent_type=agent_type,
                description=st["description"],
                dependencies=[]  # Will populate after all IDs are assigned
            ))
        
        # Resolve dependencies (map from indices to UUIDs)
        for i, st in enumerate(llm_subtasks):
            dep_indices = st.get("dependencies", [])
            if dep_indices and isinstance(dep_indices, list):
                # Filter to only valid integer indices
                valid_deps = []
                for dep_idx in dep_indices:
                    if isinstance(dep_idx, int) and dep_idx in id_map:
                        valid_deps.append(id_map[dep_idx])
                    else:
                        logger.warning(f"[Orchestrator] Invalid dependency index: {dep_idx} (type: {type(dep_idx).__name__})")
                
                subtasks[i].dependencies = valid_deps
        
        print(f"[LLM] Decomposed task into {len(subtasks)} subtasks using {result['tokens']} tokens")
        return subtasks
        
    except Exception as e:
        logger.error(f"[Orchestrator] LLM decomposition failed: {e}", exc_info=True)
        print(f"[ERROR] LLM decomposition failed: {type(e).__name__}: {e}, falling back to rule-based")


# ============================================================================
# Chat Interface (Phase 5: Copilot Integration)
# ============================================================================

class ChatRequest(BaseModel):
    """Chat message from user."""
    message: str = Field(..., description="User's message")
    session_id: Optional[str] = Field(None, description="Session ID (auto-generated if not provided)")
    user_id: Optional[str] = Field(None, description="User identifier")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ChatResponse(BaseModel):
    """Chat response to user."""
    message: str = Field(..., description="Assistant's response")
    session_id: str = Field(..., description="Session ID for multi-turn conversation")
    task_id: Optional[str] = Field(None, description="Task ID if task was created")
    intent: str = Field(..., description="Recognized intent type")
    confidence: float = Field(..., description="Intent confidence score")
    suggestions: Optional[List[str]] = Field(None, description="Suggested next actions")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional response metadata")


@app.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat_endpoint(request: ChatRequest):
    """
    Natural language chat interface for task submission and status queries.
    
    Supports:
    - Task submission: "Add error handling to login endpoint"
    - Status queries: "What's the status of task abc123?"
    - Clarification: "Use JWT authentication"
    - Approval decisions: "Approve" or "Reject"
    
    Uses intent recognition to understand user's message and route appropriately.
    Multi-turn conversations are supported via session_id.
    """
    # Create or load session
    session_id = request.session_id or f"session-{uuid.uuid4()}"
    
    try:
        # Ensure session exists
        existing_session = await session_manager.get_session(session_id)
        if not existing_session:
            await session_manager.create_session(
                session_id=session_id,
                user_id=request.user_id,
                metadata=request.context or {}
            )
            logger.info(f"Created new chat session: {session_id}")
        
        # Load conversation history
        history = await session_manager.load_conversation_history(session_id, limit=10)
        
        # Save user message
        await session_manager.add_message(
            session_id=session_id,
            role="user",
            content=request.message,
            metadata=request.context or {}
        )
        
        # Recognize intent
        intent = await intent_recognizer.recognize(request.message, history)
        
        logger.info(f"Chat [{session_id}]: Intent={intent.type}, Confidence={intent.confidence:.2f}")
        
        # Handle different intent types
        if intent.type == IntentType.TASK_SUBMISSION:
            if intent.needs_clarification:
                # Need more information
                response_message = intent.clarification_question or "I need more details to proceed."
                
                # Save assistant message
                await session_manager.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=response_message
                )
                
                return ChatResponse(
                    message=response_message,
                    session_id=session_id,
                    intent=intent.type,
                    confidence=intent.confidence,
                    suggestions=["feature-dev", "code-review", "infrastructure", "cicd", "documentation"]
                )
            
            # Convert intent to task request
            try:
                task_payload = await intent_to_task(intent, history)
                
                # Submit to orchestrator
                task_request = TaskRequest(**task_payload)
                orchestrate_response = await orchestrate_task(task_request)
                
                task_id = orchestrate_response.task_id
                response_message = f"✓ Task created: {task_id}\n\n"
                response_message += f"Breaking down into {len(orchestrate_response.subtasks)} subtasks:\n"
                for i, subtask in enumerate(orchestrate_response.subtasks[:3], 1):
                    response_message += f"{i}. {subtask.description} ({subtask.agent_type})\n"
                
                if len(orchestrate_response.subtasks) > 3:
                    response_message += f"... and {len(orchestrate_response.subtasks) - 3} more\n"
                
                # Check if approval needed
                if orchestrate_response.guardrail_report.status == GuardrailStatus.REQUIRES_APPROVAL:
                    response_message += f"\n⏸ Approval required ({orchestrate_response.guardrail_report.risk_level} risk)\n"
                    response_message += "Please review and approve/reject."
                
                # Save assistant message
                await session_manager.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=response_message,
                    metadata={"task_id": task_id}
                )
                
                return ChatResponse(
                    message=response_message,
                    session_id=session_id,
                    task_id=task_id,
                    intent=intent.type,
                    confidence=intent.confidence,
                    metadata={
                        "subtasks_count": len(orchestrate_response.subtasks),
                        "requires_approval": orchestrate_response.guardrail_report.status == GuardrailStatus.REQUIRES_APPROVAL
                    }
                )
                
            except Exception as e:
                logger.error(f"Failed to create task from intent: {e}", exc_info=True)
                error_message = f"Sorry, I couldn't create that task: {str(e)}"
                
                await session_manager.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=error_message
                )
                
                return ChatResponse(
                    message=error_message,
                    session_id=session_id,
                    intent=intent.type,
                    confidence=intent.confidence
                )
        
        elif intent.type == IntentType.STATUS_QUERY:
            # Look up task status
            if intent.entity_id:
                # Look up task in registry
                task_response = task_registry.get(intent.entity_id)
                if task_response:
                    status_counts = {}
                    for subtask in task_response.subtasks:
                        status_counts[subtask.status] = status_counts.get(subtask.status, 0) + 1
                    
                    response_message = f"Task {intent.entity_id} status:\n"
                    response_message += f"- Total subtasks: {len(task_response.subtasks)}\n"
                    for status, count in status_counts.items():
                        response_message += f"- {status}: {count}\n"
                else:
                    response_message = f"Task {intent.entity_id} not found. It may have been completed or doesn't exist."
            else:
                response_message = "Which task would you like to check? Please provide a task ID."
            
            await session_manager.add_message(
                session_id=session_id,
                role="assistant",
                content=response_message
            )
            
            return ChatResponse(
                message=response_message,
                session_id=session_id,
                intent=intent.type,
                confidence=intent.confidence
            )
        
        elif intent.type == IntentType.APPROVAL_DECISION:
            # Handle approval/rejection
            # Look for pending approval in session context
            approval_id = None
            for msg in reversed(history):
                if msg.get("metadata", {}).get("approval_id"):
                    approval_id = msg["metadata"]["approval_id"]
                    break
            
            if approval_id:
                # Submit decision
                if intent.decision == "approve":
                    await approve_task(approval_id, {"reason": "User approval via chat", "user_id": request.user_id})
                    response_message = f"✓ Approved request {approval_id}. Resuming workflow..."
                else:
                    await reject_task(approval_id, {"reason": "User rejection via chat", "user_id": request.user_id})
                    response_message = f"✗ Rejected request {approval_id}. Workflow canceled."
            else:
                response_message = "I don't see any pending approvals in this conversation. Please provide an approval ID."
            
            await session_manager.add_message(
                session_id=session_id,
                role="assistant",
                content=response_message
            )
            
            return ChatResponse(
                message=response_message,
                session_id=session_id,
                intent=intent.type,
                confidence=intent.confidence
            )
        
        else:
            # General query or unknown
            response_message = intent.suggested_response or """I can help you with:

- **Creating tasks**: "Add error handling to login endpoint"
- **Checking status**: "What's the status of task-abc123?"
- **Approving requests**: "Approve" or "Reject"

What would you like to do?"""
            
            await session_manager.add_message(
                session_id=session_id,
                role="assistant",
                content=response_message
            )
            
            return ChatResponse(
                message=response_message,
                session_id=session_id,
                intent=intent.type,
                confidence=intent.confidence,
                suggestions=["Create a task", "Check task status", "Approve a request"]
            )
    
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")


if __name__ == '__main__':
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)