# 🎯 Phase 6 Overview

Enable autonomous collaboration between agents through shared state, event-driven communication, and coordinated workflows. Build on Phase 5's notification system to create a robust inter-agent coordination layer.

---

## 📋 Phase 6 Objectives

1. **Agent Discovery & Registry** - Dynamic agent registration and capability discovery
2. **Inter-Agent Event Protocol** - Standardized event schema for agent-to-agent communication
3. **Shared State Management** - LangGraph-backed workflow state with conflict resolution
4. **Resource Locking** - Prevent concurrent modification conflicts
5. **Multi-Agent Workflows** - Coordinated task execution patterns

---

## 🏗️ Architecture Components

### 1. Agent Registry Service

**New Service**: `shared/services/agent-registry/`

```python
# shared/services/agent-registry/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Optional

class AgentCapability(BaseModel):
    name: str
    description: str
    input_schema: Dict
    output_schema: Dict
    estimated_duration: Optional[int]  # seconds

class AgentRegistration(BaseModel):
    agent_id: str
    agent_name: str
    base_url: str
    capabilities: List[AgentCapability]
    status: str  # "active", "busy", "offline"
    last_heartbeat: datetime

app = FastAPI()

# Registry storage (Redis-backed)
registry: Dict[str, AgentRegistration] = {}

@app.post("/register")
async def register_agent(agent: AgentRegistration):
    """Register agent and its capabilities"""
    registry[agent.agent_id] = agent
    await event_bus.emit("agent.registered", agent.dict())
    return {"status": "registered", "agent_id": agent.agent_id}

@app.get("/discover")
async def discover_agents(capability: Optional[str] = None):
    """Discover agents by capability"""
    if capability:
        return [a for a in registry.values()
                if any(c.name == capability for c in a.capabilities)]
    return list(registry.values())

@app.post("/heartbeat/{agent_id}")
async def heartbeat(agent_id: str):
    """Update agent status"""
    if agent_id in registry:
        registry[agent_id].last_heartbeat = datetime.utcnow()
        return {"status": "acknowledged"}
    return {"error": "agent not found"}, 404
```

**Docker Service** (`deploy/docker-compose.yml`):

```yaml
agent-registry:
  build: ./shared/services/agent-registry
  ports:
    - "8009:8000"
  environment:
    - REDIS_URL=redis://redis:6379
    - EVENT_BUS_URL=redis://redis:6379
  depends_on:
    - redis
  networks:
    - agent-network
```

---

### 2. Inter-Agent Event Protocol

**Enhanced Event Bus** (`shared/lib/event_bus.py`):

```python
# Inter-agent event schema
class InterAgentEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str  # "task.delegated", "task.completed", "resource.locked"
    source_agent: str
    target_agent: Optional[str]  # None = broadcast
    payload: Dict
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str  # Links related events
    priority: int = 0  # Higher = more urgent

# New event types
EVENT_TYPES = {
    "task.delegated": "Agent delegates subtask to another agent",
    "task.accepted": "Agent accepts delegated task",
    "task.rejected": "Agent rejects delegated task",
    "task.completed": "Agent completes delegated task",
    "task.failed": "Agent fails delegated task",
    "resource.locked": "Agent locks shared resource",
    "resource.unlocked": "Agent unlocks shared resource",
    "agent.status_change": "Agent status changes (busy/available)",
    "workflow.checkpoint": "Multi-agent workflow checkpoint",
}

# Event routing
async def route_event(event: InterAgentEvent):
    """Route event to target agent or broadcast"""
    if event.target_agent:
        # Direct message via agent registry
        agent = await registry_client.get_agent(event.target_agent)
        await httpx.post(f"{agent.base_url}/events", json=event.dict())
    else:
        # Broadcast via Redis pub/sub
        await redis.publish("agent-events", event.json())
```

---

### 3. Shared State Management

**LangGraph State Extensions** (`shared/services/langgraph/state.py`):

```python
from typing import TypedDict, Annotated, Sequence
import operator

class MultiAgentState(TypedDict):
    task_id: str
    workflow_type: str  # "sequential", "parallel", "map-reduce"

    # Task decomposition
    subtasks: Annotated[Sequence[dict], operator.add]
    subtask_status: dict  # {subtask_id: "pending"|"in_progress"|"completed"|"failed"}

    # Agent assignments
    agent_assignments: dict  # {subtask_id: agent_id}
    agent_status: dict  # {agent_id: "idle"|"busy"}

    # Coordination
    locks: dict  # {resource_id: agent_id}
    checkpoints: Annotated[Sequence[dict], operator.add]

    # Results aggregation
    partial_results: dict  # {subtask_id: result}
    final_result: Optional[dict]

    # Metadata
    started_at: datetime
    updated_at: datetime
    error_log: Annotated[Sequence[str], operator.add]

# State persistence (PostgreSQL)
async def save_state(task_id: str, state: MultiAgentState):
    """Persist state with optimistic locking"""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO workflow_state (task_id, state_data, version)
            VALUES ($1, $2, 1)
            ON CONFLICT (task_id) DO UPDATE
            SET state_data = $2, version = workflow_state.version + 1,
                updated_at = NOW()
            WHERE workflow_state.version = $3
            """,
            task_id, json.dumps(state), state.get("_version", 0)
        )
```

**State Schema Migration** (`config/state/schema.sql`):

```sql
-- Multi-agent workflow state
CREATE TABLE workflow_state (
    task_id VARCHAR(255) PRIMARY KEY,
    state_data JSONB NOT NULL,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Resource locks
CREATE TABLE resource_locks (
    resource_id VARCHAR(255) PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    locked_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    CONSTRAINT fk_agent FOREIGN KEY (agent_id) REFERENCES agent_registry(agent_id)
);

-- Agent status tracking
CREATE TABLE agent_status (
    agent_id VARCHAR(255) PRIMARY KEY,
    status VARCHAR(50) NOT NULL,
    current_task_id VARCHAR(255),
    last_heartbeat TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (current_task_id) REFERENCES workflow_state(task_id)
);
```

---

### 4. Resource Locking

**Distributed Lock Manager** (`shared/lib/resource_lock.py`):

```python
from contextlib import asynccontextmanager
import asyncio

class ResourceLockManager:
    def __init__(self, redis_client):
        self.redis = redis_client

    @asynccontextmanager
    async def acquire(self, resource_id: str, agent_id: str, timeout: int = 300):
        """Acquire distributed lock with timeout"""
        lock_key = f"lock:{resource_id}"
        lock_acquired = False

        try:
            # Try to acquire lock (Redis SET NX EX)
            lock_acquired = await self.redis.set(
                lock_key, agent_id, nx=True, ex=timeout
            )

            if not lock_acquired:
                raise ResourceLockError(f"Resource {resource_id} already locked")

            # Emit lock event
            await event_bus.emit("resource.locked", {
                "resource_id": resource_id,
                "agent_id": agent_id,
                "expires_at": datetime.utcnow() + timedelta(seconds=timeout)
            })

            yield  # Context manager body executes

        finally:
            if lock_acquired:
                # Release lock
                await self.redis.delete(lock_key)
                await event_bus.emit("resource.unlocked", {
                    "resource_id": resource_id,
                    "agent_id": agent_id
                })

    async def is_locked(self, resource_id: str) -> bool:
        """Check if resource is locked"""
        return await self.redis.exists(f"lock:{resource_id}")
```

**Agent Integration**:

```python
# Example: Agent acquiring lock before modifying shared state
from shared.lib.resource_lock import ResourceLockManager

lock_manager = ResourceLockManager(redis_client)

async with lock_manager.acquire(f"file:{file_path}", agent_name):
    # Modify file safely
    await modify_file(file_path)
    await commit_changes()
```

---

### 5. Multi-Agent Workflows

**Workflow Patterns** (`shared/services/langgraph/workflows/`):

#### 5.1 Sequential Workflow

```python
# workflows/sequential.py
from langgraph.graph import StateGraph

def create_sequential_workflow():
    """Tasks executed in order by different agents"""
    workflow = StateGraph(MultiAgentState)

    workflow.add_node("design", call_agent_feature_dev)
    workflow.add_node("implement", call_agent_code_review)
    workflow.add_node("test", call_agent_cicd)
    workflow.add_node("deploy", call_agent_infrastructure)

    workflow.set_entry_point("design")
    workflow.add_edge("design", "implement")
    workflow.add_edge("implement", "test")
    workflow.add_edge("test", "deploy")
    workflow.add_edge("deploy", END)

    return workflow.compile()
```

#### 5.2 Parallel Workflow

```python
# workflows/parallel.py
def create_parallel_workflow():
    """Tasks executed concurrently by multiple agents"""
    workflow = StateGraph(MultiAgentState)

    workflow.add_node("decompose", decompose_task)
    workflow.add_node("delegate", delegate_to_agents)
    workflow.add_node("aggregate", aggregate_results)

    workflow.set_entry_point("decompose")
    workflow.add_edge("decompose", "delegate")
    workflow.add_edge("delegate", "aggregate")
    workflow.add_edge("aggregate", END)

    return workflow.compile()

async def delegate_to_agents(state: MultiAgentState):
    """Delegate subtasks to available agents"""
    agents = await registry_client.discover_agents()

    tasks = []
    for subtask in state["subtasks"]:
        # Find available agent with capability
        agent = next(a for a in agents
                    if a.status == "active" and
                    subtask["capability"] in [c.name for c in a.capabilities])

        # Emit delegation event
        event = InterAgentEvent(
            event_type="task.delegated",
            source_agent="orchestrator",
            target_agent=agent.agent_id,
            payload=subtask,
            correlation_id=state["task_id"]
        )
        await event_bus.emit("task.delegated", event.dict())

        # Track assignment
        state["agent_assignments"][subtask["id"]] = agent.agent_id

        tasks.append(wait_for_completion(subtask["id"], agent.agent_id))

    # Wait for all subtasks
    await asyncio.gather(*tasks)
    return state
```

#### 5.3 Map-Reduce Workflow

```python
# workflows/map_reduce.py
def create_map_reduce_workflow():
    """Distribute work, process in parallel, aggregate results"""
    workflow = StateGraph(MultiAgentState)

    workflow.add_node("map", map_tasks)
    workflow.add_node("reduce", reduce_results)

    workflow.set_entry_point("map")
    workflow.add_edge("map", "reduce")
    workflow.add_edge("reduce", END)

    return workflow.compile()

async def map_tasks(state: MultiAgentState):
    """Distribute data chunks to agents"""
    data_chunks = split_data(state["input_data"])

    for i, chunk in enumerate(data_chunks):
        agent = await registry_client.get_available_agent("data_processor")

        subtask = {
            "id": f"chunk_{i}",
            "data": chunk,
            "operation": state["operation"]
        }

        await delegate_subtask(agent.agent_id, subtask)

    return state

async def reduce_results(state: MultiAgentState):
    """Aggregate partial results"""
    results = []
    for subtask_id, result in state["partial_results"].items():
        results.append(result)

    state["final_result"] = combine_results(results)
    return state
```

---

## 📁 File Structure

```
Dev-Tools/
├── shared/
│   ├── lib/
│   │   ├── event_bus.py          # ✅ Enhanced with inter-agent events
│   │   ├── resource_lock.py      # 🆕 Distributed locking
│   │   └── registry_client.py    # 🆕 Agent registry client
│   ├── services/
│   │   ├── agent-registry/       # 🆕 Agent discovery service
│   │   │   ├── main.py
│   │   │   ├── Dockerfile
│   │   │   └── requirements.txt
│   │   └── langgraph/
│   │       ├── workflows/        # 🆕 Multi-agent workflows
│   │       │   ├── sequential.py
│   │       │   ├── parallel.py
│   │       │   └── map_reduce.py
│   │       └── state.py          # ✅ Enhanced with MultiAgentState
├── agent_orchestrator/
│   ├── workflows.py              # 🆕 Workflow orchestration logic
│   └── delegation.py             # 🆕 Task delegation logic
├── config/
│   └── state/
│       └── schema.sql            # ✅ Enhanced with multi-agent tables
└── support/
    ├── docs/
    │   ├── PHASE_6_PLAN.md       # 🆕 This document
    │   └── MULTI_AGENT_EXAMPLES.md  # 🆕 Workflow examples
    └── tests/
        └── test_multi_agent.py   # 🆕 Integration tests
```

---

## 🚀 Implementation Phases

### Phase 6.1: Foundation (Week 1)

**Deliverables:**

- ✅ Agent registry service (discovery, heartbeat, status)
- ✅ Enhanced event bus with inter-agent events
- ✅ Redis integration for pub/sub and locking
- ✅ PostgreSQL schema for workflow state

**Validation:**

- All agents register on startup
- Heartbeat monitoring detects offline agents
- Events route correctly between agents

### Phase 6.2: Coordination (Week 2)

**Deliverables:**

- ✅ Resource locking (distributed locks via Redis)
- ✅ MultiAgentState LangGraph schema
- ✅ State persistence with optimistic locking
- ✅ Conflict resolution strategies

**Validation:**

- Concurrent state modifications handled gracefully
- Locks prevent race conditions
- State checkpoints recoverable

### Phase 6.3: Workflows (Week 3)

**Deliverables:**

- ✅ Sequential workflow pattern
- ✅ Parallel workflow pattern
- ✅ Map-reduce workflow pattern
- ✅ Task delegation logic in orchestrator

**Validation:**

- End-to-end multi-agent workflows complete successfully
- Failures handled with retries/fallbacks
- Results aggregated correctly

### Phase 6.4: Production Hardening (Week 4)

**Deliverables:**

- ✅ Observability (Prometheus metrics for delegation)
- ✅ LangSmith multi-agent trace visualization
- ✅ Chaos testing (agent failures, network partitions)
- ✅ Documentation and runbooks

**Validation:**

- System handles 3+ agent failures gracefully
- Traces show full workflow execution
- Runbooks cover common failure scenarios

---

## 🧪 Example: Multi-Agent Code Review Workflow

```python
# User request: "Review this PR with full test coverage"

# 1. Orchestrator decomposes task
subtasks = [
    {"id": "static_analysis", "agent": "code-review", "capability": "lint"},
    {"id": "security_scan", "agent": "code-review", "capability": "security"},
    {"id": "unit_tests", "agent": "cicd", "capability": "test"},
    {"id": "integration_tests", "agent": "cicd", "capability": "test"},
    {"id": "docs_update", "agent": "documentation", "capability": "generate"},
]

# 2. Orchestrator delegates in parallel
for subtask in subtasks:
    agent = await registry.get_agent_by_capability(subtask["capability"])
    await event_bus.emit("task.delegated", {
        "subtask_id": subtask["id"],
        "target_agent": agent.agent_id,
        "payload": subtask
    })

# 3. Agents execute and report back
# (code-review agent runs lint + security scan)
# (cicd agent runs unit + integration tests)
# (documentation agent updates README)

# 4. Orchestrator aggregates results
results = {
    "static_analysis": {"status": "passed", "warnings": 2},
    "security_scan": {"status": "passed", "vulnerabilities": 0},
    "unit_tests": {"status": "passed", "coverage": 92},
    "integration_tests": {"status": "passed", "duration": 45},
    "docs_update": {"status": "completed", "files": ["README.md"]}
}

# 5. Post approval notification to Linear
await linear_client.post_comment(
    issue_id="PR-68",
    comment=f"Multi-agent review complete. Results: {results}. @alex approve?"
)
```

---

## 📊 Success Metrics

- **Agent Discovery**: <100ms to discover agents by capability
- **Event Latency**: <50ms event routing (agent-to-agent)
- **Lock Acquisition**: <10ms distributed lock overhead
- **Workflow Execution**: 3+ agents coordinating on 10+ tasks/min
- **Failure Recovery**: <5s to detect and reassign failed tasks
- **Trace Completeness**: 100% multi-agent workflows visible in LangSmith

---

## ⚠️ Risks & Mitigations

| Risk                              | Impact | Mitigation                               |
| --------------------------------- | ------ | ---------------------------------------- |
| Agent goes offline mid-task       | High   | Heartbeat monitoring + task reassignment |
| State conflicts (race conditions) | High   | Optimistic locking + conflict resolution |
| Deadlock on resources             | Medium | Lock timeouts + deadlock detection       |
| Event ordering issues             | Medium | Correlation IDs + event versioning       |
| Registry single point of failure  | High   | Redis persistence + backup registry      |

---

## 🔧 Configuration

**Environment Variables** (`config/env/.env`):

```bash
# Agent Registry
AGENT_REGISTRY_URL=http://agent-registry:8000
REGISTRY_HEARTBEAT_INTERVAL=30  # seconds

# Redis (for locks + pub/sub)
REDIS_URL=redis://redis:6379
LOCK_TIMEOUT=300  # seconds
EVENT_TTL=3600  # seconds

# LangGraph State
STATE_DB_URL=postgresql://user:pass@postgres:5432/workflow_state
STATE_VERSION_RETENTION=10  # Keep last N versions

# Multi-Agent Workflows
WORKFLOW_TYPE=parallel  # sequential, parallel, map_reduce
MAX_CONCURRENT_DELEGATES=5
TASK_TIMEOUT=600  # seconds
```

---

## 📚 Documentation Updates

1. **`support/docs/MULTI_AGENT_WORKFLOWS.md`**: Workflow patterns and examples
2. **`support/docs/AGENT_REGISTRY.md`**: Discovery and registration guide
3. **`support/docs/RESOURCE_LOCKING.md`**: Lock semantics and best practices
4. **`support/docs/EVENT_PROTOCOL.md`**: Inter-agent event schema reference
5. **`.github/copilot-instructions.md`**: Update with Phase 6 architecture

---

## ✅ Acceptance Criteria

- [ ] Agent registry service running with health endpoint
- [ ] All 6 agents register on startup
- [ ] Inter-agent events routed with <50ms latency
- [ ] Resource locks prevent concurrent modification
- [ ] Sequential workflow completes end-to-end
- [ ] Parallel workflow handles 5+ concurrent subtasks
- [ ] Map-reduce workflow aggregates results correctly
- [ ] LangSmith traces show full multi-agent execution
- [ ] Prometheus metrics track delegation success/failure
- [ ] Documentation complete with runbooks

---

**Phase 6 Status**: 📋 Planned (awaiting Phase 5 validation)  
**Estimated Duration**: 4 weeks  
**Complexity**: High (distributed systems, coordination, state management)
