# Phase 6: Multi-Agent Collaboration

**Status**: Planning  
**Priority**: High  
**Estimated Duration**: 12 days  
**Dependencies**: Phase 5 (Complete ✅)

---

## 🎯 Overview

Enable agents to collaborate on complex, multi-step tasks through event-driven coordination, shared state management, and inter-agent communication. This phase transforms the agent fleet from independent services into a coordinated system capable of handling workflows that span multiple domains.

### Key Objectives

1. **Agent Discovery**: Central registry for finding agents by capability
2. **Inter-Agent Communication**: Event-driven messaging protocol for agent-to-agent requests
3. **Shared Task Context**: LangGraph checkpointing for multi-agent workflow state
4. **Resource Locking**: Prevent concurrent modifications to shared resources
5. **Workflow Orchestration**: Complex multi-step tasks coordinated across agents

### Success Metrics

- **Agent Response Time**: <2s for agent-to-agent communication
- **Workflow Completion Rate**: >95% for multi-agent tasks
- **State Consistency**: 100% accuracy in shared context
- **Resource Conflicts**: <1% collision rate with locking
- **Discovery Accuracy**: 100% capability matching precision

---

## 🏗️ Architecture

### Current State (Phase 5)

```
┌─────────────────────────────────────────────────────────────┐
│                        Orchestrator                         │
│  - Natural language task parsing (Gradient AI)              │
│  - Task decomposition (LLM-powered)                         │
│  - Direct agent invocation (HTTP calls)                     │
│  - HITL approval workflow                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
          ┌───────────────────────────────────────┐
          │         MCP Gateway (150+ tools)      │
          └───────────────────────────────────────┘
                              │
          ┌───────┬───────┬───────┬───────┬───────┐
          ▼       ▼       ▼       ▼       ▼       ▼
       Feature  Code   Infra   CI/CD   Docs    (5 Agents)
         Dev   Review
```

**Limitations**:

- Orchestrator must know all agent URLs
- No agent-to-agent communication
- No shared context between agents
- No dynamic agent discovery
- Linear workflows only (no branching/parallelism)

### Target State (Phase 6)

```
┌──────────────────────────────────────────────────────────────┐
│                       Orchestrator                           │
│  - Multi-agent workflow graphs (LangGraph)                   │
│  - Shared state management (PostgreSQL checkpointing)        │
│  - Event bus coordination (async pub/sub)                    │
│  - Dynamic agent discovery (registry queries)                │
└──────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┴───────────────────┐
          ▼                                       ▼
┌─────────────────────┐               ┌─────────────────────┐
│   Agent Registry    │               │     Event Bus       │
│  - Capability DB    │               │  - Pub/Sub routing  │
│  - Health checks    │               │  - Agent messaging  │
│  - Discovery API    │               │  - Workflow events  │
└─────────────────────┘               └─────────────────────┘
          │                                       │
          └───────────────────┬───────────────────┘
                              ▼
          ┌───────────────────────────────────────┐
          │         MCP Gateway (150+ tools)      │
          └───────────────────────────────────────┘
                              │
          ┌───────┬───────┬───────┬───────┬───────┐
          ▼       ▼       ▼       ▼       ▼       ▼
       Feature  Code   Infra   CI/CD   Docs    (5 Agents)
         Dev   Review                           + Registry
                                                 + Event Bus

       Each agent can:
       - Query registry for peer agents
       - Emit events to request help
       - Subscribe to relevant events
       - Share state via LangGraph
       - Lock resources for exclusive access
```

**Capabilities Unlocked**:

- Agents discover each other dynamically
- Agents can delegate subtasks to peers
- Parallel execution of independent tasks
- Shared context across agent boundaries
- Automatic resource conflict prevention

---

## 📋 Implementation Plan

### Task 6.1: Agent Registry Service (2 days)

**Goal**: Central registry for agent discovery and health monitoring

**Components**:

1. **Registry Service** (`shared/services/agent-registry/`)

   - FastAPI service on port 8009
   - PostgreSQL backend for persistence
   - REST API for registration/discovery
   - Automatic health check polling (30s interval)

2. **Agent Registration Client** (`shared/lib/registry_client.py`)

   - Auto-register on agent startup
   - Heartbeat loop (30s interval)
   - Capability declaration DSL

3. **Capability Schema**
   ```python
   class AgentCapability(BaseModel):
       name: str                    # "code_review", "deploy_service"
       description: str             # Human-readable description
       parameters: Dict[str, str]   # {"repo_url": "str", "pr_number": "int"}
       cost_estimate: str           # "~100 tokens" or "~30s compute"
       tags: List[str]              # ["git", "security", "performance"]
   ```

**API Endpoints**:

- `POST /register` - Register/update agent
- `GET /agents` - List all agents
- `GET /agents/{agent_id}` - Get agent details
- `POST /agents/{agent_id}/heartbeat` - Update heartbeat
- `GET /capabilities/search?q={keyword}` - Search by capability
- `GET /health/{agent_id}` - Check agent health status

**Database Schema**:

```sql
CREATE TABLE agent_registry (
    agent_id VARCHAR(64) PRIMARY KEY,
    agent_name VARCHAR(128) NOT NULL,
    base_url VARCHAR(256) NOT NULL,
    status VARCHAR(32) NOT NULL,  -- active, busy, offline
    last_heartbeat TIMESTAMP NOT NULL,
    capabilities JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_agent_status ON agent_registry(status);
CREATE INDEX idx_agent_heartbeat ON agent_registry(last_heartbeat);
CREATE INDEX idx_agent_capabilities ON agent_registry USING GIN(capabilities);
```

**Deliverables**:

- [ ] `shared/services/agent-registry/main.py`
- [ ] `shared/services/agent-registry/Dockerfile`
- [ ] `shared/lib/registry_client.py`
- [ ] `config/state/agent_registry.sql`
- [ ] Docker Compose service definition
- [ ] Integration tests

**Acceptance Criteria**:

- Registry service starts and accepts registrations
- Agents auto-register on startup
- Health checks detect offline agents within 60s
- Capability search returns accurate matches
- Prometheus metrics exported

---

### Task 6.2: Inter-Agent Event Protocol (3 days)

**Goal**: Standardized event-driven communication between agents

**Event Schema**:

```python
class AgentRequestEvent(BaseModel):
    """Agent-to-agent request event"""
    event_type: Literal["agent_request"]
    event_id: str                    # UUID
    source_agent: str                # Sending agent ID
    target_agent: str                # Receiving agent ID (or "*" for broadcast)
    action: str                      # Action to perform
    parameters: Dict[str, Any]       # Action parameters
    callback_url: Optional[str]      # URL for response
    priority: Literal["low", "medium", "high", "critical"]
    timeout_seconds: int             # Max time to wait
    correlation_id: Optional[str]    # Link to parent task
    created_at: datetime

class AgentResponseEvent(BaseModel):
    """Agent-to-agent response event"""
    event_type: Literal["agent_response"]
    event_id: str                    # UUID
    request_id: str                  # Original request event_id
    source_agent: str                # Responding agent
    target_agent: str                # Original requester
    status: Literal["success", "error", "timeout"]
    result: Optional[Dict[str, Any]] # Response data
    error: Optional[str]             # Error message if failed
    duration_ms: int                 # Processing time
    created_at: datetime
```

**Event Bus Enhancements** (`shared/lib/event_bus.py`):

```python
class EventBus:
    """Enhanced event bus with agent messaging"""

    async def request_agent_action(
        self,
        target_agent: str,
        action: str,
        parameters: Dict[str, Any],
        timeout: int = 300,
        priority: str = "medium"
    ) -> Dict[str, Any]:
        """
        Send request to another agent and wait for response.

        Returns:
            Response data from target agent

        Raises:
            TimeoutError: If agent doesn't respond in time
            AgentError: If agent returns error
        """
        pass

    async def broadcast_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        exclude_agents: Optional[List[str]] = None
    ):
        """Broadcast event to all registered agents."""
        pass
```

**Agent Request Handlers**:

Each agent implements a `/agent-request` endpoint:

```python
# Example: agent_code-review/main.py
@app.post("/agent-request")
async def handle_agent_request(request: AgentRequestEvent):
    """Handle incoming agent-to-agent requests."""

    if request.action == "review_pr":
        result = await review_pull_request(
            repo_url=request.parameters["repo_url"],
            pr_number=request.parameters["pr_number"]
        )
        return AgentResponseEvent(
            event_id=str(uuid.uuid4()),
            request_id=request.event_id,
            source_agent="code-review",
            target_agent=request.source_agent,
            status="success",
            result=result,
            duration_ms=calculate_duration(),
            created_at=datetime.utcnow()
        )
    else:
        return AgentResponseEvent(
            event_id=str(uuid.uuid4()),
            request_id=request.event_id,
            source_agent="code-review",
            target_agent=request.source_agent,
            status="error",
            error=f"Unknown action: {request.action}",
            duration_ms=0,
            created_at=datetime.utcnow()
        )
```

**Example Workflow**:

```python
# Orchestrator coordinates code review → tests → deployment

# Step 1: Request code review
review_result = await event_bus.request_agent_action(
    target_agent="code-review",
    action="review_pr",
    parameters={"repo_url": "...", "pr_number": 123},
    timeout=300
)

# Step 2: If review passes, request tests
if review_result["approved"]:
    test_result = await event_bus.request_agent_action(
        target_agent="cicd",
        action="run_tests",
        parameters={"repo_url": "...", "commit_sha": "..."},
        timeout=600
    )

    # Step 3: If tests pass, request deployment approval
    if test_result["all_passed"]:
        await event_bus.emit_event("hitl_approval_required", {
            "reason": "Deploy to production",
            "context": {"pr": 123, "tests": test_result}
        })
```

**Deliverables**:

- [ ] Enhanced `shared/lib/event_bus.py` with agent messaging
- [ ] `shared/lib/agent_request_handler.py` (mixin for agents)
- [ ] `/agent-request` endpoint in all 6 agents
- [ ] Event schema Pydantic models
- [ ] Integration tests for request/response flow
- [ ] Prometheus metrics (request latency, error rate)

**Acceptance Criteria**:

- Agent can request action from another agent
- Response returned within timeout period
- Errors handled gracefully with retries
- Broadcast events reach all agents
- Request/response correlation working

---

### Task 6.3: Shared State Management (2 days)

**Goal**: LangGraph checkpointing for multi-agent workflow state

**Architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Workflow                       │
│                                                             │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐            │
│   │  Review  │────▶│  Tests   │────▶│  Deploy  │           │
│   │  (Agent) │     │  (Agent) │     │  (Agent) │            │
│   └──────────┘     └──────────┘     └──────────┘            │
│         │                │                 │                │
│         └────────────────┴─────────────────┘                │
│                          ▼                                  │
│              ┌────────────────────────┐                     │
│              │   Shared State Store   │                     │
│              │   (PostgreSQL)         │                     │
│              └────────────────────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

**Shared State Schema**:

```sql
CREATE TABLE workflow_state (
    workflow_id VARCHAR(64) PRIMARY KEY,
    workflow_type VARCHAR(64) NOT NULL,
    current_step VARCHAR(128) NOT NULL,
    state_data JSONB NOT NULL,
    participating_agents TEXT[],
    started_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR(32) NOT NULL  -- running, paused, completed, failed
);

CREATE TABLE workflow_checkpoints (
    checkpoint_id SERIAL PRIMARY KEY,
    workflow_id VARCHAR(64) REFERENCES workflow_state(workflow_id),
    step_name VARCHAR(128) NOT NULL,
    agent_id VARCHAR(64) NOT NULL,
    checkpoint_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_workflow_status ON workflow_state(status);
CREATE INDEX idx_workflow_updated ON workflow_state(updated_at);
CREATE INDEX idx_checkpoint_workflow ON workflow_checkpoints(workflow_id);
```

**LangGraph Integration**:

```python
# agent_orchestrator/workflows/shared_state_workflow.py
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

class MultiAgentState(TypedDict):
    """Shared state across agents"""
    task_id: str
    task_description: str
    current_agent: str
    agent_results: Dict[str, Any]
    shared_context: Dict[str, Any]
    error_log: List[str]

# Use PostgreSQL checkpointing
checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@state:5432/devtools"
)

workflow = StateGraph(MultiAgentState)

# Each step updates shared state
def code_review_step(state: MultiAgentState) -> MultiAgentState:
    result = call_agent("code-review", state["shared_context"])
    state["agent_results"]["code_review"] = result
    state["current_agent"] = "cicd"
    return state

workflow.add_node("code_review", code_review_step)
# ... more nodes

# Compile with checkpointing
app = workflow.compile(checkpointer=checkpointer)

# Execute workflow with persistent state
result = await app.ainvoke(
    {"task_id": "task-123", "task_description": "..."},
    config={"configurable": {"thread_id": "task-123"}}
)
```

**State Management API**:

```python
# shared/lib/workflow_state.py
class WorkflowStateManager:
    """Manage shared workflow state"""

    async def create_workflow(
        self,
        workflow_id: str,
        workflow_type: str,
        initial_state: Dict[str, Any]
    ):
        """Create new workflow with initial state."""
        pass

    async def get_state(self, workflow_id: str) -> Dict[str, Any]:
        """Get current workflow state."""
        pass

    async def update_state(
        self,
        workflow_id: str,
        updates: Dict[str, Any],
        agent_id: str
    ):
        """Update workflow state from agent."""
        pass

    async def checkpoint(
        self,
        workflow_id: str,
        step_name: str,
        agent_id: str,
        data: Dict[str, Any]
    ):
        """Create checkpoint at current step."""
        pass

    async def restore_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: int
    ) -> Dict[str, Any]:
        """Restore workflow to previous checkpoint."""
        pass
```

**Deliverables**:

- [ ] `config/state/workflow_state.sql`
- [ ] `shared/lib/workflow_state.py`
- [ ] LangGraph PostgreSQL checkpointer integration
- [ ] Example multi-agent workflows
- [ ] State recovery tests
- [ ] Documentation

**Acceptance Criteria**:

- Workflow state persists across agent invocations
- Checkpoints created at each step
- State recovery works after failure
- Concurrent workflows don't interfere
- State queries under 50ms

---

### Task 6.4: Resource Locking (2 days)

**Goal**: Prevent concurrent modifications to shared resources

**Use Cases**:

- Multiple agents editing same file
- Concurrent database migrations
- Overlapping deployments to same environment
- Race conditions on shared configuration

**Locking Mechanism**:

```python
# shared/lib/resource_lock.py
import asyncio
from datetime import datetime, timedelta
from typing import Optional

class ResourceLockManager:
    """Distributed resource locking using PostgreSQL advisory locks."""

    def __init__(self, db_conn_string: str):
        self.db = create_async_engine(db_conn_string)

    async def acquire_lock(
        self,
        resource_id: str,
        agent_id: str,
        timeout_seconds: int = 60,
        wait: bool = True
    ) -> bool:
        """
        Acquire exclusive lock on resource.

        Args:
            resource_id: Resource identifier (e.g., "repo:owner/name")
            agent_id: Agent requesting lock
            timeout_seconds: Lock auto-release timeout
            wait: Block until lock available (vs. immediate return)

        Returns:
            True if lock acquired, False otherwise
        """
        pass

    async def release_lock(self, resource_id: str, agent_id: str):
        """Release lock held by agent."""
        pass

    async def check_lock(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """Check if resource is locked."""
        pass

    async def force_release(self, resource_id: str, reason: str):
        """Force release lock (admin operation)."""
        pass
```

**Database Schema**:

```sql
CREATE TABLE resource_locks (
    resource_id VARCHAR(256) PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL,
    acquired_at TIMESTAMP NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    reason VARCHAR(512),
    metadata JSONB
);

CREATE INDEX idx_lock_expiry ON resource_locks(expires_at);
CREATE INDEX idx_lock_agent ON resource_locks(agent_id);

-- Auto-cleanup expired locks
CREATE OR REPLACE FUNCTION cleanup_expired_locks()
RETURNS TRIGGER AS $$
BEGIN
    DELETE FROM resource_locks WHERE expires_at < NOW();
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_cleanup_locks
    AFTER INSERT OR UPDATE ON resource_locks
    EXECUTE FUNCTION cleanup_expired_locks();
```

**Usage Pattern**:

```python
# agent_infrastructure/main.py
@app.post("/deploy")
async def deploy_service(request: DeployRequest):
    resource_id = f"deployment:{request.environment}:{request.service}"

    # Try to acquire lock
    lock_acquired = await lock_manager.acquire_lock(
        resource_id=resource_id,
        agent_id="infrastructure",
        timeout_seconds=300,
        wait=True  # Block until available
    )

    if not lock_acquired:
        raise HTTPException(
            status_code=409,
            detail=f"Resource {resource_id} is locked by another agent"
        )

    try:
        # Perform deployment
        result = await perform_deployment(request)
        return result
    finally:
        # Always release lock
        await lock_manager.release_lock(resource_id, "infrastructure")
```

**Deliverables**:

- [ ] `shared/lib/resource_lock.py`
- [ ] `config/state/resource_locks.sql`
- [ ] Lock acquisition tests (concurrent scenarios)
- [ ] Auto-cleanup of expired locks
- [ ] Prometheus metrics (lock contention, wait time)
- [ ] Documentation with examples

**Acceptance Criteria**:

- Lock prevents concurrent resource access
- Expired locks auto-released within 5s
- Deadlock detection and prevention
- Lock wait time tracked in metrics
- Force-release works for stuck locks

---

### Task 6.5: Multi-Agent Workflow Examples (3 days)

**Goal**: Reference implementations of common multi-agent patterns

**Example 1: PR Review → Test → Deploy Workflow**

```python
# agent_orchestrator/workflows/pr_deployment.py
from langgraph.graph import StateGraph, END
from typing import TypedDict

class PRDeploymentState(TypedDict):
    pr_number: int
    repo_url: str
    review_comments: List[Dict]
    test_results: Dict
    approval_status: str
    deployment_status: str

async def code_review_step(state: PRDeploymentState) -> PRDeploymentState:
    """Request code review from code-review agent."""
    result = await event_bus.request_agent_action(
        target_agent="code-review",
        action="review_pr",
        parameters={
            "repo_url": state["repo_url"],
            "pr_number": state["pr_number"]
        }
    )
    state["review_comments"] = result["comments"]
    return state

async def test_step(state: PRDeploymentState) -> PRDeploymentState:
    """Request test run from cicd agent."""
    result = await event_bus.request_agent_action(
        target_agent="cicd",
        action="run_tests",
        parameters={
            "repo_url": state["repo_url"],
            "pr_number": state["pr_number"]
        }
    )
    state["test_results"] = result
    return state

async def approval_step(state: PRDeploymentState) -> PRDeploymentState:
    """Request HITL approval."""
    approval = await hitl_manager.request_approval(
        action="deploy_to_production",
        context={
            "pr": state["pr_number"],
            "review": state["review_comments"],
            "tests": state["test_results"]
        }
    )
    state["approval_status"] = approval["status"]
    return state

async def deployment_step(state: PRDeploymentState) -> PRDeploymentState:
    """Request deployment from infrastructure agent."""
    result = await event_bus.request_agent_action(
        target_agent="infrastructure",
        action="deploy_service",
        parameters={
            "repo_url": state["repo_url"],
            "environment": "production",
            "version": f"pr-{state['pr_number']}"
        }
    )
    state["deployment_status"] = result["status"]
    return state

# Build workflow
workflow = StateGraph(PRDeploymentState)
workflow.add_node("code_review", code_review_step)
workflow.add_node("test", test_step)
workflow.add_node("approval", approval_step)
workflow.add_node("deploy", deployment_step)

workflow.add_edge("code_review", "test")
workflow.add_edge("test", "approval")
workflow.add_conditional_edges(
    "approval",
    lambda state: "deploy" if state["approval_status"] == "approved" else END,
    {"deploy": "deploy", END: END}
)
workflow.add_edge("deploy", END)

workflow.set_entry_point("code_review")
```

**Example 2: Parallel Documentation Generation**

```python
# agent_orchestrator/workflows/parallel_docs.py
async def generate_api_docs(state: DocsState) -> DocsState:
    """Generate API documentation."""
    result = await event_bus.request_agent_action(
        target_agent="documentation",
        action="generate_api_docs",
        parameters={"repo_url": state["repo_url"]}
    )
    state["api_docs"] = result
    return state

async def generate_user_guide(state: DocsState) -> DocsState:
    """Generate user guide."""
    result = await event_bus.request_agent_action(
        target_agent="documentation",
        action="generate_user_guide",
        parameters={"repo_url": state["repo_url"]}
    )
    state["user_guide"] = result
    return state

async def generate_deployment_guide(state: DocsState) -> DocsState:
    """Generate deployment guide."""
    result = await event_bus.request_agent_action(
        target_agent="documentation",
        action="generate_deployment_guide",
        parameters={"repo_url": state["repo_url"]}
    )
    state["deployment_guide"] = result
    return state

# Parallel execution
workflow = StateGraph(DocsState)
workflow.add_node("api_docs", generate_api_docs)
workflow.add_node("user_guide", generate_user_guide)
workflow.add_node("deployment_guide", generate_deployment_guide)
workflow.add_node("merge", merge_documentation)

# All three run in parallel
workflow.add_edge(START, "api_docs")
workflow.add_edge(START, "user_guide")
workflow.add_edge(START, "deployment_guide")

# Merge results
workflow.add_edge("api_docs", "merge")
workflow.add_edge("user_guide", "merge")
workflow.add_edge("deployment_guide", "merge")
workflow.add_edge("merge", END)
```

**Example 3: Self-Healing Infrastructure**

```python
# agent_orchestrator/workflows/self_healing.py
async def detect_issue(state: HealingState) -> HealingState:
    """Query infrastructure agent for health issues."""
    result = await event_bus.request_agent_action(
        target_agent="infrastructure",
        action="health_check",
        parameters={"environment": "production"}
    )
    state["issues"] = result["issues"]
    return state

async def diagnose_issue(state: HealingState) -> HealingState:
    """Ask multiple agents to diagnose."""
    # Broadcast diagnostic request
    results = await event_bus.broadcast_request(
        action="diagnose",
        parameters={"issue": state["issues"][0]},
        target_agents=["code-review", "cicd", "infrastructure"]
    )
    state["diagnosis"] = aggregate_diagnoses(results)
    return state

async def apply_fix(state: HealingState) -> HealingState:
    """Apply recommended fix."""
    fix_agent = state["diagnosis"]["recommended_agent"]
    result = await event_bus.request_agent_action(
        target_agent=fix_agent,
        action="apply_fix",
        parameters=state["diagnosis"]["fix_parameters"]
    )
    state["fix_result"] = result
    return state

async def verify_fix(state: HealingState) -> HealingState:
    """Verify issue resolved."""
    result = await event_bus.request_agent_action(
        target_agent="infrastructure",
        action="health_check",
        parameters={"environment": "production"}
    )
    state["is_resolved"] = len(result["issues"]) == 0
    return state

# Build self-healing loop
workflow = StateGraph(HealingState)
workflow.add_node("detect", detect_issue)
workflow.add_node("diagnose", diagnose_issue)
workflow.add_node("apply_fix", apply_fix)
workflow.add_node("verify", verify_fix)

workflow.add_edge("detect", "diagnose")
workflow.add_edge("diagnose", "apply_fix")
workflow.add_edge("apply_fix", "verify")
workflow.add_conditional_edges(
    "verify",
    lambda state: END if state["is_resolved"] else "detect",
    {END: END, "detect": "detect"}
)
```

**Deliverables**:

- [ ] `agent_orchestrator/workflows/pr_deployment.py`
- [ ] `agent_orchestrator/workflows/parallel_docs.py`
- [ ] `agent_orchestrator/workflows/self_healing.py`
- [ ] Integration tests for each workflow
- [ ] Performance benchmarks
- [ ] Documentation with diagrams

**Acceptance Criteria**:

- All three workflows execute successfully
- Parallel execution 2-3x faster than sequential
- Self-healing loop detects and fixes issues
- Workflow state persists across failures
- Clear documentation with usage examples

---

## 🧪 Testing Strategy

### Unit Tests

- Agent registry CRUD operations
- Event serialization/deserialization
- Lock acquisition/release logic
- State checkpoint save/restore

### Integration Tests

- Agent-to-agent communication
- Multi-agent workflow execution
- Lock contention scenarios
- State recovery after crash

### Performance Tests

- Registry lookup latency (<50ms)
- Inter-agent request time (<2s)
- Lock acquisition under contention (<100ms)
- Workflow throughput (5+ concurrent workflows)

### End-to-End Tests

- Full PR deployment workflow
- Parallel documentation generation
- Self-healing infrastructure scenario

---

## 📊 Monitoring & Observability

### Prometheus Metrics

**Agent Registry**:

- `agent_registry_size` - Number of registered agents
- `agent_registry_lookups_total` - Registry queries
- `agent_registry_lookup_duration_seconds` - Query latency
- `agent_heartbeat_lag_seconds` - Time since last heartbeat

**Inter-Agent Communication**:

- `agent_requests_total` - Total agent-to-agent requests
- `agent_request_duration_seconds` - Request latency
- `agent_request_errors_total` - Failed requests
- `agent_request_timeouts_total` - Timed out requests

**Resource Locking**:

- `resource_locks_active` - Currently held locks
- `resource_lock_wait_seconds` - Time waiting for lock
- `resource_lock_contentions_total` - Lock conflicts
- `resource_lock_timeouts_total` - Lock acquisition failures

**Workflow State**:

- `workflows_active` - Running workflows
- `workflow_duration_seconds` - Workflow execution time
- `workflow_steps_total` - Steps executed
- `workflow_failures_total` - Failed workflows

### LangSmith Tracing

- Tag multi-agent workflows with `workflow_type`
- Trace each agent invocation as a span
- Capture state transitions
- Link approval requests to workflow

### Grafana Dashboards

1. **Agent Fleet Overview**

   - Registry health
   - Active workflows
   - Inter-agent traffic

2. **Multi-Agent Workflows**

   - Workflow duration by type
   - Success/failure rates
   - Bottleneck identification

3. **Resource Management**
   - Lock contention heatmap
   - State storage usage
   - Checkpoint frequency

---

## 🚀 Deployment Plan

### Phase 1: Registry Service (Day 1-2)

1. Deploy agent-registry service
2. Update all agents to auto-register
3. Verify health checks working
4. Test capability search

### Phase 2: Event Protocol (Day 3-5)

1. Deploy enhanced event bus
2. Add `/agent-request` endpoints to all agents
3. Test request/response flow
4. Implement retry logic

### Phase 3: Shared State (Day 6-7)

1. Deploy workflow state tables
2. Integrate LangGraph checkpointing
3. Test state persistence
4. Verify checkpoint recovery

### Phase 4: Resource Locking (Day 8-9)

1. Deploy lock management tables
2. Add locking to critical operations
3. Test concurrent scenarios
4. Configure auto-cleanup

### Phase 5: Workflows (Day 10-12)

1. Deploy PR deployment workflow
2. Deploy parallel docs workflow
3. Deploy self-healing workflow
4. End-to-end testing
5. Documentation and training

---

## 📝 Documentation Deliverables

1. **Architecture Overview** (`MULTI_AGENT_ARCHITECTURE.md`)

   - System diagram
   - Component responsibilities
   - Data flow diagrams

2. **Agent Registry Guide** (`AGENT_REGISTRY.md`)

   - Registration process
   - Capability definition
   - Discovery API

3. **Inter-Agent Events** (`INTER_AGENT_EVENTS.md`)

   - Event schema reference
   - Request/response patterns
   - Error handling

4. **Workflow Development** (`WORKFLOW_DEVELOPMENT.md`)

   - LangGraph patterns
   - State management
   - Testing workflows

5. **Resource Locking** (`RESOURCE_LOCKING.md`)
   - Locking strategies
   - Deadlock prevention
   - Troubleshooting

---

## 🎯 Success Criteria

**Functional Requirements**:

- ✅ Agents discover each other via registry
- ✅ Agents communicate via event bus
- ✅ Workflow state persists across agents
- ✅ Resources locked during exclusive operations
- ✅ 3 example workflows implemented and tested

**Performance Requirements**:

- ✅ Agent discovery < 50ms
- ✅ Inter-agent request < 2s
- ✅ Lock acquisition < 100ms
- ✅ 5+ concurrent workflows supported

**Reliability Requirements**:

- ✅ Workflow recovery after agent crash
- ✅ Automatic lock cleanup
- ✅ Expired registrations detected
- ✅ Graceful degradation on agent failure

**Observability Requirements**:

- ✅ All components export Prometheus metrics
- ✅ LangSmith traces multi-agent workflows
- ✅ Grafana dashboards operational
- ✅ Alert rules for critical failures

---

## 🔗 Dependencies & Risks

### External Dependencies

- PostgreSQL (state storage, checkpointing, locking)
- Gradient AI (LLM for orchestrator decisions)
- Linear API (approval notifications)
- Existing event bus (`shared/lib/event_bus.py`)

### Internal Dependencies

- Phase 5 Copilot Integration (COMPLETE ✅)
- LangGraph service (`shared/services/langgraph/`)
- State service (`shared/services/state/`)

### Risks & Mitigations

| Risk                             | Impact         | Mitigation                            |
| -------------------------------- | -------------- | ------------------------------------- |
| Agent communication overhead     | High latency   | Use async, implement caching          |
| State database bottleneck        | Slow workflows | Connection pooling, read replicas     |
| Lock deadlocks                   | Workflow hangs | Timeout all locks, deadlock detection |
| Event bus scaling                | Message loss   | Add Redis backend if >1000 events/min |
| Registry single point of failure | No discovery   | Add Redis cache for redundancy        |

---

## 🎉 Next Phase Preview: Phase 7 (Autonomous Operations)

After Phase 6 completes, the system will have:

- ✅ Multi-agent coordination
- ✅ Shared workflow state
- ✅ Resource conflict prevention

**Phase 7 Goals**:

- **Autonomous Decision Making**: Agents make decisions without HITL approval for low-risk tasks
- **Learning from Outcomes**: Adjust risk thresholds based on success/failure history
- **Predictive Task Routing**: ML model predicts best agent for task
- **Proactive Issue Detection**: Agents monitor and fix issues before they impact users
- **Cost Optimization**: Intelligent model selection based on task complexity

---

**Ready to start implementation!** 🚀
