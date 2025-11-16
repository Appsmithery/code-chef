# LangGraph Service Quick Reference

## Service Information

- **Port:** 8009
- **Container:** `langgraph`
- **Image:** `registry.digitalocean.com/the-shop-infra/langgraph:latest`
- **Dependencies:** postgres, gateway-mcp

## Endpoints

### GET /health

Health check with dependency status.

**Response:**

```json
{
  "status": "healthy",
  "postgres_checkpointer": "connected|disconnected",
  "mcp_gateway": "configured|not_configured"
}
```

### POST /workflow/invoke

Execute workflow synchronously (blocks until completion).

**Request:**

```json
{
  "task_description": "Build REST API with authentication",
  "request_payloads": {
    "feature_request": {
      "feature_name": "auth-service",
      "description": "User authentication API",
      "requirements": ["FastAPI", "JWT", "PostgreSQL"]
    }
  },
  "thread_id": "optional-thread-id",
  "enable_checkpointing": true
}
```

**Response:**

```json
{
  "state": {
    "task_description": "...",
    "feature_response": {...},
    "artifacts": [...]
  },
  "task_id": "abc123",
  "status": "completed"
}
```

### POST /workflow/stream

Stream workflow state updates via Server-Sent Events.

**Request:**

```json
{
  "task_description": "Build REST API",
  "request_payloads": {...},
  "thread_id": "optional",
  "enable_checkpointing": true,
  "stream_mode": "values"
}
```

**Stream Modes:**

- `values` - Full state after each node
- `updates` - Only state changes
- `debug` - Detailed execution info

**Response (SSE):**

```
data: {"router": {...}}

data: {"feature-dev": {"feature_response": {...}}}

data: {"status": "completed"}
```

### POST /workflow/stream-events

Stream detailed execution events (node transitions, LLM calls).

**Request:**

```json
{
  "task_description": "Build REST API",
  "thread_id": "optional"
}
```

**Event Types:**

- `on_chain_start` - Node begins execution
- `on_chain_end` - Node completes
- `on_llm_start` - LLM invocation begins
- `on_llm_end` - LLM invocation completes

## Docker Commands

```bash
# Build container
docker-compose build langgraph

# Start service
docker-compose up -d langgraph

# View logs
docker-compose logs -f langgraph

# Restart service
docker-compose restart langgraph

# Stop service
docker-compose stop langgraph

# Check status
docker-compose ps langgraph

# Execute command in container
docker-compose exec langgraph python -c "import langgraph; print(langgraph.__version__)"
```

## cURL Examples

```bash
# Health check
curl http://localhost:8009/health

# Invoke workflow
curl -X POST http://localhost:8009/workflow/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "task_description": "Build REST API",
    "request_payloads": {
      "feature_request": {
        "feature_name": "api",
        "description": "REST API service",
        "requirements": ["FastAPI"]
      }
    }
  }'

# Stream workflow (SSE)
curl -X POST http://localhost:8009/workflow/stream \
  -H "Content-Type: application/json" \
  -d '{
    "task_description": "Build REST API",
    "stream_mode": "values"
  }'

# Stream events
curl -X POST http://localhost:8009/workflow/stream-events \
  -H "Content-Type: application/json" \
  -d '{
    "task_description": "Build REST API"
  }'
```

## Environment Variables

**Required:**

- `GRADIENT_MODEL_ACCESS_KEY` - Gradient AI API key
- `DB_PASSWORD` - PostgreSQL password (for checkpointing)

**Optional:**

- `PORT=8009` - HTTP server port
- `HOST=0.0.0.0` - Bind address
- `LOG_LEVEL=info` - Logging level
- `GRADIENT_MODEL=llama-3.1-8b-instruct` - LLM model
- `MCP_GATEWAY_URL=http://gateway-mcp:8000` - MCP gateway
- `LANGFUSE_SECRET_KEY` - Langfuse tracing secret
- `LANGFUSE_PUBLIC_KEY` - Langfuse tracing public key
- `LANGFUSE_HOST=https://us.cloud.langfuse.com` - Langfuse host

## Troubleshooting

### Service Not Starting

```bash
# Check logs
docker-compose logs langgraph

# Verify dependencies
docker-compose ps postgres gateway-mcp

# Check environment variables
docker-compose exec langgraph env | grep GRADIENT
```

### Checkpointer Not Connected

**Symptom:** Health check shows `postgres_checkpointer: "disconnected"`

**Fix:**

1. Verify `DB_PASSWORD` is set in `.env`
2. Restart postgres: `docker-compose restart postgres`
3. Restart langgraph: `docker-compose restart langgraph`

### Workflow Hangs

**Symptom:** Request to `/workflow/invoke` never returns

**Fix:**

1. Check node logs: `docker-compose logs langgraph`
2. Verify MCP gateway: `curl http://localhost:8000/health`
3. Test agents directly: `curl http://localhost:8002/health`

### State Not Persisting

**Symptom:** State resets between invocations with same `thread_id`

**Fix:**

1. Ensure `enable_checkpointing=true` in request
2. Check PostgreSQL: `docker-compose ps postgres`
3. Verify checkpointer logs

## Python SDK Usage

```python
from agents.langgraph.workflow import build_workflow, stream_workflow
from agents.feature_dev.service import FeatureRequest

# Build workflow
graph = build_workflow(enable_checkpointing=True)

# Stream execution
async for event in stream_workflow(
    graph=graph,
    task_description="Build REST API",
    request_payloads={
        "feature_request": FeatureRequest(
            feature_name="api",
            description="REST API service",
            requirements=["FastAPI"]
        )
    },
    stream_mode="updates"
):
    print(event)
```

## Monitoring

### Prometheus Metrics

Available at `http://langgraph:8009/metrics`:

- `http_request_duration_seconds` - Request latency
- `http_requests_total` - Total requests
- `http_request_size_bytes` - Request size
- `http_response_size_bytes` - Response size

### Langfuse Tracing

Dashboard: https://us.cloud.langfuse.com

**Trace Data:**

- Prompts and completions
- Token counts and costs
- Execution times
- Grouped by task_id and agent_name

### Service Logs

```bash
# Tail logs
docker-compose logs -f langgraph

# Last 100 lines
docker-compose logs --tail=100 langgraph

# Filter by level
docker-compose logs langgraph | grep ERROR
```

## Documentation

- **Integration Guide:** `docs/LANGGRAPH_INTEGRATION.md`
- **Test Suite:** `test_langgraph_integration.py`
- **Architecture:** `docs/ARCHITECTURE.md`
- **Agent Endpoints:** `docs/AGENT_ENDPOINTS.md`
