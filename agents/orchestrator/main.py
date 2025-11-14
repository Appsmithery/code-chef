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
from prometheus_fastapi_instrumentator import Instrumentator

from agents._shared.mcp_client import MCPClient

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

# In-memory task registry (in production, this would use State Persistence Layer)
task_registry: Dict[str, TaskResponse] = {}

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
    manifest_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "agents-manifest.json")
    )
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load agent manifest: {e}")
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
    gateway_health = await mcp_client.get_gateway_health()
    return {
        "status": "ok",
        "service": "orchestrator",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "mcp": {
            "gateway": gateway_health,
            "recommended_tool_servers": [entry.get("server") for entry in mcp_client.recommended_tools],
            "shared_tool_servers": mcp_client.shared_tools,
            "capabilities": mcp_client.capabilities,
        },
    }

@app.post("/orchestrate", response_model=TaskResponse)
async def orchestrate_task(request: TaskRequest):
    """
    Main orchestration endpoint with tool-aware routing
    - Analyzes request and decomposes into subtasks
    - Validates tool availability before routing
    - Routes to appropriate specialized agents
    - Returns routing plan with minimal context pointers
    
    Token Optimization: Processes only task metadata (< 500 tokens per routing decision)
    """
    import uuid
    
    task_id = str(uuid.uuid4())
    
    # Analyze required tools for this task
    required_tools = get_required_tools_for_task(request.description)
    
    # Simple rule-based task decomposition (in production, would use Task Router)
    subtasks = decompose_request(request)
    
    # Validate tool availability for each subtask
    validation_results = {}
    for subtask in subtasks:
        # Determine required tools for this specific subtask
        subtask_required_tools = get_required_tools_for_task(subtask.description)
        availability = await check_agent_tool_availability(subtask.agent_type, subtask_required_tools)
        validation_results[subtask.id] = availability
        
        # Log warning if tools are missing (but don't block - fallback available)
        if not availability["available"]:
            print(f"Warning: Agent {subtask.agent_type} missing tools for subtask {subtask.id}: {availability['missing_tools']}")
            await mcp_client.log_event(
                "tool_availability_warning",
                metadata={
                    "task_id": task_id,
                    "subtask_id": subtask.id,
                    "agent": subtask.agent_type.value,
                    "missing_tools": availability["missing_tools"],
                },
                entity_type="orchestrator_warning",
            )
    
    # Create routing plan with tool availability info
    routing_plan = {
        "execution_order": [st.id for st in subtasks],
        "parallel_groups": identify_parallel_tasks(subtasks),
        "estimated_duration_minutes": estimate_duration(subtasks),
        "tool_validation": validation_results,
        "required_tools": required_tools
    }
    
    # Estimate token usage (orchestrator uses minimal tokens)
    estimated_tokens = len(request.description.split()) * 2  # Rough estimate
    
    response = TaskResponse(
        task_id=task_id,
        subtasks=subtasks,
        routing_plan=routing_plan,
        estimated_tokens=estimated_tokens
    )
    
    # Store in registry (in-memory fallback)
    task_registry[task_id] = response
    
    # Persist to state database
    await persist_task_state(task_id, request, response)

    await mcp_client.log_event(
        "task_orchestrated",
        metadata={
            "task_id": task_id,
            "subtask_count": len(subtasks),
            "priority": request.priority,
            "agent": "orchestrator",
            "tools_validated": all(v["available"] for v in validation_results.values()),
        },
    )
    
    return response


async def persist_task_state(task_id: str, request: TaskRequest, response: TaskResponse):
    """Persist task state to State Persistence Layer"""
    try:
        async with httpx.AsyncClient() as client:
            # Create task record
            task_payload = {
                "task_id": task_id,
                "type": "orchestration",
                "status": "pending",
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
                "status": "pending"
            }
            
            await client.post(
                f"{STATE_SERVICE_URL}/workflows",
                json=workflow_payload,
                timeout=5.0
            )
            
            await mcp_client.log_event(
                "orchestrator_state_persisted",
                metadata={
                    "task_id": task_id,
                    "workflow_steps": len(response.subtasks),
                    "status": "pending",
                },
            )

    except Exception as e:
        print(f"State persistence failed (non-critical): {e}")
        await mcp_client.log_event(
            "orchestrator_state_persistence_failed",
            metadata={
                "task_id": task_id,
                "error": str(e),
            },
            entity_type="orchestrator_error",
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
    Decompose incoming request into discrete subtasks
    Uses simple keyword matching for MVP (production would use Task Router)
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

if __name__ == '__main__':
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run(app, host="0.0.0.0", port=port)