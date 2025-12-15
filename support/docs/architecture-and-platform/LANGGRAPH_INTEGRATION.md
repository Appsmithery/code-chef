---
status: active
category: architecture-and-platform
last_updated: 2025-12-09
---

# LangGraph Integration Guide

## Overview

The Dev-Tools platform uses **LangGraph** for multi-agent workflow orchestration. This document covers architecture, usage, and deployment of the LangGraph workflow service.

## Architecture

### Core Components

1. **State Management** (`agents/langgraph/state.py`)

   - `AgentState` TypedDict defines canonical state schema
   - Request/response fields for each agent (feature_dev, code_review, etc.)
   - State reducers for list accumulation and deduplication
   - Pydantic validation via `AgentStateModel`

2. **Workflow Compilation** (`agents/langgraph/workflow.py`)

   - `StateGraph` with conditional routing
   - PostgreSQL checkpointer for state persistence
   - Streaming support via `astream` and `astream_events`
   - Request payload injection system

3. **Node Implementations** (`agents/langgraph/nodes/`)

   - Router node for task classification
   - Specialized nodes (feature-dev, code-review, infrastructure, cicd, documentation)
   - Each node calls corresponding agent service module
   - Nodes populate state with structured responses

4. **FastAPI Server** (`agents/langgraph/main.py`)
   - HTTP endpoints for workflow invocation
   - Server-Sent Events (SSE) streaming
   - Health checks with PostgreSQL status
   - Port 8009

### Dependencies

```
langgraph>=0.1.7
langchain-core>=0.2.34
langgraph-checkpoint-postgres>=1.0.0
psycopg[binary]>=3.1.0
langchain-openai>=0.1.0
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
langfuse>=2.0.0
```

### Observability

**Automatic Langfuse Tracing:**

- All LLM calls traced with prompts, completions, and token counts
- Workflow executions tracked end-to-end
- Node transitions and state changes captured
- Metadata includes agent_name, task_id, thread_id, model
- Traces viewable at https://us.cloud.langfuse.com

**Configuration:**

```env
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=https://us.cloud.langfuse.com
```

Tracing activates automatically when these variables are set. No code changes required.

## Usage

### HTTP Endpoints

#### POST /workflow/invoke

Execute workflow end-to-end and return final state.

**Request:**

```json
{
  "task_description": "Implement user authentication service",
  "request_payloads": {
    "feature_request": {
      "feature_name": "auth-service",
      "requirements": ["JWT tokens", "password hashing"]
    }
  },
  "thread_id": "optional-resume-id",
  "enable_checkpointing": true
}
```

**Response:**

```json
{
  "state": {
    "task_id": "abc123",
    "task_description": "...",
    "feature_response": {...},
    "artifacts": [...]
  },
  "task_id": "abc123",
  "status": "completed"
}
```

#### POST /workflow/stream

Stream workflow state updates in real-time via SSE.

**Request:**

```json
{
  "task_description": "Implement user authentication service",
  "stream_mode": "values"
}
```

**Stream modes:**

- `values`: Full state after each node
- `updates`: Only state changes from each node
- `debug`: Detailed execution events

**Response (SSE):**

```
data: {"router": {...}}

data: {"feature-dev": {"feature_response": {...}}}

data: {"task_id": "abc123", "status": "completed"}
```

#### POST /workflow/stream-events

Stream detailed execution events including LLM calls and node transitions.

**Events:**

- `on_chain_start`: Node execution begins
- `on_chain_end`: Node execution completes
- `on_llm_start`: LLM invocation begins
- `on_llm_end`: LLM invocation completes

#### GET /health

Health check with dependency status.

**Response:**

```json
{
  "status": "healthy",
  "postgres_checkpointer": "connected",
  "mcp_gateway": "configured"
}
```

### Programmatic Usage

```python
from agents.langgraph.workflow import build_workflow, invoke_workflow
from agents.feature_dev.service import FeatureRequest

# Build workflow once
graph = build_workflow(enable_checkpointing=True)

# Invoke with request payloads
result = invoke_workflow(
    graph=graph,
    task_description="Build REST API",
    request_payloads={
        "feature_request": FeatureRequest(
            feature_name="api-service",
            requirements=["FastAPI", "PostgreSQL"]
        )
    },
    thread_id="workflow-123"
)

print(result["feature_response"])
```

### Streaming Example

```python
from agents.langgraph.workflow import build_workflow, stream_workflow

graph = build_workflow()

async for event in stream_workflow(
    graph=graph,
    task_description="Build REST API",
    stream_mode="updates"
):
    print(f"Node update: {event}")
```

## State Persistence

### PostgreSQL Checkpointer

The workflow uses **PostgreSQL** for state persistence via `langgraph-checkpoint-postgres`.

**Benefits:**

- Resume interrupted workflows
- State history and rollback
- Concurrent workflow isolation via thread IDs
- Query workflow execution logs

**Configuration:**

Environment variables:

```bash
DB_HOST=postgres
DB_PORT=5432
DB_NAME=devtools
DB_USER=devtools
DB_PASSWORD=changeme
```

**Schema:**

The checkpointer automatically creates a `checkpoints` table:

```sql
CREATE TABLE checkpoints (
    thread_id TEXT,
    checkpoint_id TEXT,
    parent_checkpoint_id TEXT,
    checkpoint JSONB,
    metadata JSONB,
    PRIMARY KEY (thread_id, checkpoint_id)
);
```

### Thread IDs

Thread IDs isolate concurrent workflows:

```python
# Start new workflow
invoke_workflow(
    task_description="Build API",
    thread_id="api-v1"
)

# Resume from checkpoint
invoke_workflow(
    task_description="Continue API work",
    thread_id="api-v1"  # Loads previous state
)
```

## LangChain Integration

### Gradient LLM Wrapper

The `GradientLLM` class wraps `gradient_client` for use with LangChain tools:

```python
from agents._shared.llm_providers import get_llm

llm = get_gradient_llm(
    agent_name="orchestrator",
    model="llama-3.1-70b-instruct",
    temperature=0.7
)

# Use with LangChain
result = await llm.ainvoke("Explain LangGraph workflows")
```

**Features:**

- Async interface via `_acall`
- Token usage reporting
- Automatic Langfuse tracing
- Compatible with LangChain tools, prompts, agents

## Deployment

### Docker Compose

The LangGraph service is defined in `deploy/docker-compose.yml`:

```yaml
langgraph:
  image: registry.digitalocean.com/the-shop-infra/langgraph:latest
  ports:
    - "8009:8009"
  environment:
    - DB_HOST=postgres
    - DB_PASSWORD=${DB_PASSWORD}
    - MCP_GATEWAY_URL=http://gateway-mcp:8000
    - GRADIENT_MODEL_ACCESS_KEY=${GRADIENT_MODEL_ACCESS_KEY}
  depends_on:
    - postgres
    - gateway-mcp
```

### Build and Deploy

```bash
# Build container
cd compose
docker-compose build langgraph

# Deploy stack
docker-compose up -d langgraph

# Check health
curl http://localhost:8009/health

# View logs
docker-compose logs -f langgraph
```

### Remote Deployment

```powershell
# Use deploy script with remote target
./support/scripts/deploy.ps1 -Target remote

# Or SSH manually
ssh alex@45.55.173.72
cd /opt/Dev-Tools
git pull
docker-compose up -d langgraph
```

## Observability

### Langfuse Tracing

All LLM calls are automatically traced via Langfuse:

**Configuration:**

```bash
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_HOST=https://us.cloud.langfuse.com
```

**Trace data:**

- Prompts and completions
- Token counts and costs
- Execution times
- Grouped by task_id and agent_name

**Dashboard:** https://us.cloud.langfuse.com

### Prometheus Metrics

Metrics scraped by Prometheus at `http://langgraph:8009/metrics`:

- `http_request_duration_seconds`: Request latency histogram
- `http_requests_total`: Total requests counter
- `http_request_size_bytes`: Request size histogram
- `http_response_size_bytes`: Response size histogram

**Grafana dashboards:** Available at `http://localhost:9090`

## Testing

### Unit Tests

Run pytest suite:

```bash
cd /path/to/Dev-Tools
python -m pytest tests/test_langgraph_*.py -v
```

**Test coverage:**

- State schema validation
- Request payload injection
- Workflow invocation
- Node routing logic

### Integration Tests

Test against live service:

```bash
# Start stack
docker-compose up -d langgraph postgres gateway-mcp

# Invoke workflow
curl -X POST http://localhost:8009/workflow/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "task_description": "Build REST API",
    "request_payloads": {
      "feature_request": {
        "feature_name": "api-service",
        "requirements": ["FastAPI"]
      }
    }
  }'

# Stream workflow
curl -X POST http://localhost:8009/workflow/stream \
  -H "Content-Type: application/json" \
  -d '{
    "task_description": "Build REST API",
    "stream_mode": "values"
  }'
```

## Troubleshooting

### Checkpointer Not Connected

**Symptom:** Health check shows `postgres_checkpointer: "disconnected"`

**Cause:** Missing or invalid `DB_PASSWORD` environment variable

**Fix:**

```bash
# Set password in .env
echo "DB_PASSWORD=your_secure_password" >> config/env/.env

# Restart services
docker-compose restart postgres langgraph
```

### Workflow Hangs

**Symptom:** Request to `/workflow/invoke` never returns

**Cause:** Node implementation not returning state update

**Fix:**

1. Check node logs: `docker-compose logs langgraph`
2. Verify MCP gateway is running: `curl http://localhost:8000/health`
3. Test node directly: `curl http://localhost:8002/process-feature`

### State Not Persisting

**Symptom:** Workflow state resets between invocations with same `thread_id`

**Cause:** Checkpointer disabled or database connection failed

**Fix:**

1. Verify `enable_checkpointing=true` in request
2. Check PostgreSQL health: `docker-compose ps postgres`
3. Inspect checkpointer initialization logs

## Future Enhancements

### Multi-Hop Workflows

Extend workflow to support multi-step agent chaining:

```python
workflow.add_edge("feature-dev", "code-review")
workflow.add_edge("code-review", "cicd")
```

### Human-in-the-Loop

Add approval nodes for human review:

```python
workflow.add_node("human-approval", human_approval_node)
workflow.add_conditional_edges(
    "code-review",
    should_approve,
    {"approve": "cicd", "reject": "feature-dev"}
)
```

### A2A Protocol Integration

Integrate Agent-to-Agent (A2A) protocol for standardized inter-agent communication.

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [PostgreSQL Checkpointer](https://langchain-ai.github.io/langgraph/how-tos/persistence/)
- [Streaming Guide](https://langchain-ai.github.io/langgraph/how-tos/streaming/)
- [Dev-Tools Architecture](./ARCHITECTURE.md)
