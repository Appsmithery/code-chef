# Streaming Chat Configuration Guide

**Version**: 1.0.0  
**Last Updated**: December 13, 2025  
**Status**: Production Ready

---

## Overview

This document describes the configuration and architecture of code-chef's streaming chat functionality, which powers the @chef chat participant in VS Code and the web interface.

---

## Architecture

### Components

```
User Message
    ↓
FastAPI /chat/stream (SSE)
    ↓
LangGraph StateGraph
    ↓
Supervisor Agent (Claude 3.5 Sonnet)
    ↓
├─→ Feature Dev (Qwen 2.5 Coder)
├─→ Code Review (DeepSeek V3)
├─→ Infrastructure (Gemini 2.0 Flash)
├─→ CI/CD (Gemini 2.0 Flash)
└─→ Documentation (DeepSeek V3)
    ↓
Streamed Response (SSE)
```

### Streaming Flow

1. **Request Reception**: FastAPI endpoint receives ChatStreamRequest
2. **Context Enrichment**: Extract project_context and workspace_config
3. **State Initialization**: Create WorkflowState with HumanMessage
4. **Graph Execution**: LangGraph.astream_events() begins streaming
5. **Supervisor Routing**: Supervisor analyzes intent and routes to specialist
6. **Agent Processing**: Specialist agent generates response with tool usage
7. **Event Streaming**: Chunks flow to client via Server-Sent Events
8. **Completion**: Session ID returned for multi-turn conversations

---

## Configuration Files

### Supervisor Agent

**File**: `agent_orchestrator/agents/supervisor/tools.yaml`

**Key Settings**:

```yaml
agent:
  name: supervisor
  model: anthropic/claude-3-5-sonnet
  provider: openrouter
  temperature: 0.3 # Low for consistent routing
  max_tokens: 2000
  system_prompt: |
    Conversational AI system prompt optimized for:
    - Natural language understanding
    - Intent detection from casual messages
    - Context-aware routing
    - Multi-turn conversation support
    - Risk assessment for HITL approvals
```

**Why Claude 3.5 Sonnet?**

- Best-in-class reasoning for complex routing decisions
- Excellent instruction following
- Strong multi-turn conversation memory
- Cost: $3.00/1M tokens (justified for routing accuracy)

### Specialized Agents

| Agent          | Model              | Temperature | Max Tokens | Use Case                   |
| -------------- | ------------------ | ----------- | ---------- | -------------------------- |
| Feature Dev    | Qwen 2.5 Coder 32B | 0.3         | 4000       | Code generation, bug fixes |
| Code Review    | DeepSeek V3        | 0.2         | 4000       | Security, quality analysis |
| Infrastructure | Gemini 2.0 Flash   | 0.4         | 8000       | IaC, cloud configs         |
| CI/CD          | Gemini 2.0 Flash   | 0.4         | 8000       | Pipelines, deployments     |
| Documentation  | DeepSeek V3        | 0.5         | 4000       | READMEs, API docs          |

**Temperature Guidelines**:

- **Low (0.2-0.3)**: Code generation, security analysis (deterministic)
- **Medium (0.4-0.5)**: Documentation, infrastructure (some creativity)
- **High (0.6-0.8)**: [NOT USED] Creative writing (not needed for dev tools)

### LangGraph Configuration

**File**: `agent_orchestrator/graph.py`

**Key Functions**:

```python
def get_graph() -> CompiledGraph:
    """
    Singleton pattern for expensive graph compilation.

    Returns cached _compiled_graph to avoid re-compilation on every request.
    Critical for streaming performance (<50ms overhead).
    """
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = create_workflow()
    return _compiled_graph
```

**Routing Logic** (`supervisor_node`):

```python
async def supervisor_node(state: WorkflowState) -> WorkflowState:
    """
    1. Receives HumanMessage with user's request
    2. Appends routing_prompt with conversational instructions
    3. Invokes SupervisorAgent with full message history
    4. Parses structured response:
       NEXT_AGENT: <agent-name>
       REQUIRES_APPROVAL: <true|false>
       REASONING: <explanation>
    5. Returns updated state with routing decision
    """
```

**Why This Architecture?**

- **Flexibility**: Supervisor can route to any agent dynamically
- **Context Preservation**: Full message history passed to each agent
- **Observability**: LangSmith traces every routing decision
- **Safety**: HITL approvals integrated at supervisor level

---

## Streaming Endpoint

### Request Model

**File**: `agent_orchestrator/main.py`

```python
class ChatStreamRequest(BaseModel):
    message: str  # User's message (conversational or formal)
    session_id: Optional[str]  # For multi-turn conversations
    user_id: Optional[str]  # User identifier
    context: Optional[Dict[str, Any]]  # Generic metadata
    workspace_config: Optional[Dict[str, Any]]  # VS Code workspace info
    project_context: Optional[Dict[str, Any]]  # Linear/GitHub project info
```

**Field Usage**:

- `message`: Only required field. Can be casual ("fix the bug") or specific
- `session_id`: Auto-generated if omitted. Include in follow-up messages
- `project_context`: Enables RAG isolation (queries scoped to project)
- `workspace_config`: Provides file context from VS Code

### Response Format (SSE)

**Event Structure**:

```javascript
// Content chunk (many per response)
data: {"type": "content", "content": "I'll help you"}

// Agent completion (progress indicator)
data: {"type": "agent_complete", "agent": "feature_dev"}

// Tool invocation (transparency)
data: {"type": "tool_call", "tool": "filesystem:read_file"}

// Stream complete (includes session_id for follow-up)
data: {"type": "done", "session_id": "stream-abc123"}

// Error (user-friendly message)
data: {"type": "error", "error": "Rate limit exceeded. Please wait a moment."}
```

**Client Implementation Example**:

```typescript
const eventSource = new EventSource(
  "https://codechef.appsmithery.co/api/chat/stream",
  {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify({
      message: "Review this code for security issues",
      session_id: sessionId, // Optional
    }),
  }
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case "content":
      appendToChat(data.content);
      break;
    case "agent_complete":
      showAgentBadge(data.agent);
      break;
    case "done":
      sessionId = data.session_id; // Save for next message
      break;
    case "error":
      showError(data.error);
      break;
  }
};
```

---

## Error Handling

### User-Friendly Error Messages

The endpoint transforms technical errors into actionable messages:

| Technical Error         | User Message                                                  |
| ----------------------- | ------------------------------------------------------------- |
| `401 Unauthorized`      | "Authentication failed. Please check your API configuration." |
| `429 Too Many Requests` | "Rate limit exceeded. Please wait a moment and try again."    |
| `Timeout`               | "Request timed out. Please try a simpler task or try again."  |
| `Model not found`       | "Model configuration error. Please contact support."          |
| Generic exception       | Full error in DEBUG mode, sanitized in PRODUCTION             |

**Why User-Friendly Errors?**

- Reduces support burden (users understand what to do)
- Improves UX (no cryptic stack traces in chat)
- Security (doesn't expose internal implementation details)

---

## Context Management

### Project Context Isolation

**Purpose**: Ensure RAG queries only return relevant documentation for the current project.

**Implementation**:

```python
project_context = {
    "project_id": linear_project_id or github_repo_url,
    "repository_url": github_repo_url,
    "workspace_name": workspace_name
}
```

**Effect**:

- RAG queries filtered by project_id
- Prevents cross-project information leakage
- Improves response relevance

### Multi-Turn Conversations

**Stateless Design**: Each request contains full context.

**Session Continuity**:

1. Client saves `session_id` from "done" event
2. Client includes `session_id` in next ChatStreamRequest
3. LangGraph retrieves checkpoint from PostgreSQL via thread_id
4. Supervisor has access to full conversation history

**Why PostgreSQL Checkpointing?**

- Persistent across container restarts
- Enables "resume conversation" feature
- Supports debugging (inspect conversation state)
- Required for HITL approvals (pause/resume workflow)

---

## Performance Optimization

### Graph Compilation Caching

**Problem**: LangGraph compilation takes ~500ms per request.

**Solution**: `get_graph()` singleton with `_compiled_graph` global.

**Impact**:

- First request: 500ms compilation + execution
- Subsequent requests: <50ms overhead + execution
- 90% reduction in cold-start latency

### Progressive Tool Loading

**Problem**: 178+ MCP tools consume 8000+ tokens of context.

**Solution**: Load only relevant tools per task.

**Implementation**:

```python
relevant_toolsets = progressive_loader.get_tools_for_task(
    task_description=request.message,
    strategy=ToolLoadingStrategy.MINIMAL  # 10-30 tools
)
```

**Impact**:

- Token savings: ~6000 tokens per request
- Cost savings: ~$0.018 per request (at $3/1M tokens)
- Context window savings: More room for conversation history

### Streaming Backpressure

**Implementation**:

```python
async for event in graph.astream_events(state, config):
    yield sse_event
    await asyncio.sleep(0.01)  # Prevent overwhelming client
```

**Why 10ms Delay?**

- Prevents TCP buffer overflow on slow clients
- Allows browser JS event loop to process chunks
- Minimal impact on perceived latency (<1% slower)

---

## Monitoring & Observability

### LangSmith Tracing

**Project**: `code-chef-production`

**Key Traces**:

- `chat_stream`: Top-level endpoint invocation
- `supervisor_node`: Routing decisions with NEXT_AGENT
- `feature_dev_node`, `code_review_node`, etc.: Agent executions
- Tool calls: MCP tool invocations

**Filter Examples**:

```python
# Recent chat sessions
environment:"production" AND module:"chat" AND start_time > now-1h

# Routing decisions
event_name:"supervisor_node" AND environment:"production"

# Agent performance
event_name:"feature_dev_node" AND latency > 5s
```

### Prometheus Metrics

**Endpoint**: `http://localhost:8001/metrics`

**Key Metrics**:

```promql
# Streaming sessions
http_requests_total{endpoint="/chat/stream", status="200"}

# Token usage by agent
llm_tokens_total{agent="supervisor", type="prompt"}

# Response latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{endpoint="/chat/stream"}[5m]))

# Error rate
rate(http_requests_total{endpoint="/chat/stream", status="500"}[5m])
```

### Grafana Dashboards

**Dashboard**: "LLM Token Metrics" + "Chat Performance"

**Panels**:

- **Active Sessions**: Current concurrent chat streams
- **Tokens per Session**: Avg token usage by conversation length
- **Agent Distribution**: Which agents get routed to most often
- **Error Rate**: Errors per 1000 requests
- **P95 Latency**: 95th percentile response time

---

## Security & Rate Limiting

### API Key Authentication

**Header**: `X-API-Key: <orchestrator-api-key>`

**Validation**:

```python
@app.middleware("http")
async def validate_api_key(request: Request, call_next):
    if request.url.path.startswith("/chat"):
        api_key = request.headers.get("X-API-Key")
        if api_key != ORCHESTRATOR_API_KEY:
            return JSONResponse(status_code=401, content={"error": "Invalid API key"})
    return await call_next(request)
```

### Rate Limiting

**Provider**: OpenRouter handles rate limiting.

**Retry Logic**: Built into LangChain OpenRouter client.

**User-Facing**: "Rate limit exceeded. Please wait a moment and try again."

### Content Safety

**Input Validation**:

- Max message length: 10,000 characters (prevents abuse)
- Session ID validation: UUID format only
- Project context sanitization: Prevent injection attacks

**Output Filtering**:

- No raw error stack traces in production
- Sensitive data (API keys, credentials) redacted from logs
- HITL approval required for destructive operations

---

## Deployment Checklist

### Pre-Deployment

- [ ] All agent models configured in `config/agents/models.yaml`
- [ ] OpenRouter API key in `deploy/.env`
- [ ] PostgreSQL checkpointer connection tested
- [ ] LangSmith project created with correct API key
- [ ] Grafana dashboards imported

### Deployment

```bash
# Pull latest code
cd /opt/Dev-Tools
git pull origin main

# Rebuild orchestrator
docker compose build orchestrator

# Deploy with zero-downtime (if using load balancer)
docker compose up -d orchestrator

# Verify health
curl http://localhost:8001/health

# Test streaming
curl -X POST http://localhost:8001/chat/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $ORCHESTRATOR_API_KEY" \
  -d '{"message": "Hello, test streaming"}'
```

### Post-Deployment

- [ ] Health endpoint returns 200 OK
- [ ] Streaming test returns SSE events
- [ ] LangSmith traces appear in production project
- [ ] Prometheus metrics updating
- [ ] No errors in container logs

---

## Troubleshooting

### Issue: No streaming output

**Symptoms**: Request hangs, no SSE events

**Check**:

```bash
# Container logs
docker logs deploy-orchestrator-1 --tail=100 -f

# LangGraph compilation
# Should see: "Initialized get_graph() singleton"

# LangSmith traces
# Filter: event_name:"chat_stream" AND status:"error"
```

**Solution**: Verify `get_graph()` returns compiled graph, check PostgreSQL connection.

---

### Issue: Slow first response

**Symptoms**: First message takes >5 seconds

**Cause**: Graph compilation + model cold start

**Solution**: Pre-warm cache by sending test message on deployment:

```bash
curl -X POST http://localhost:8001/chat/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $ORCHESTRATOR_API_KEY" \
  -d '{"message": "test"}' > /dev/null &
```

---

### Issue: Authentication errors

**Symptoms**: 401 from OpenRouter

**Check**:

```bash
# Verify API key
echo $OPENROUTER_API_KEY

# Test directly
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"
```

**Solution**: Regenerate API key, update `.env`, restart container.

---

## Best Practices

### For Chat Clients

1. **Always save session_id** from "done" event for multi-turn conversations
2. **Handle all event types** (content, agent_complete, tool_call, done, error)
3. **Implement exponential backoff** for rate limit errors
4. **Show typing indicators** during `agent_complete` events
5. **Display agent badges** to show which specialist is helping

### For Agent Developers

1. **Use conversational system prompts** (friendly tone, not robotic)
2. **Keep responses concise** (streaming works best with short chunks)
3. **Log routing decisions** (helps debug intent detection)
4. **Test multi-turn flows** (ensure context preserved across messages)
5. **Add LangSmith tags** for filtering traces by feature

---

## Cost Optimization

### Token Usage

**Average Chat Session**:

- Supervisor routing: ~500 tokens
- Agent response: ~1500 tokens
- Total: ~2000 tokens per message

**Cost per Message**:

- Supervisor (Claude 3.5): 500 tokens × $3/1M = $0.0015
- Specialist (avg): 1500 tokens × $0.50/1M = $0.00075
- **Total**: ~$0.00225 per message

**Monthly Cost** (1000 users, 10 messages/day):

- 10M messages/month
- $22,500/month
- **Can reduce by 30%** with better prompt engineering

### Optimization Strategies

1. **Compress system prompts** (remove verbose examples)
2. **Use smaller models** for simple tasks (e.g., Gemini for docs)
3. **Cache frequent responses** (e.g., "how do I...?" questions)
4. **Implement prompt templates** (reduce redundant text)
5. **Monitor token efficiency** (target <2000 tokens/message)

---

## Future Enhancements

### Planned Features

- [ ] **Streaming with vision** (send screenshots/diagrams to agents)
- [ ] **Voice input** (transcribe audio to text, stream TTS response)
- [ ] **Multi-modal responses** (code + diagrams in one stream)
- [ ] **Collaborative sessions** (multiple users in one conversation)
- [ ] **Conversation branching** (fork conversation at any point)

### Under Consideration

- [ ] **Streaming file edits** (see code changes in real-time)
- [ ] **Live terminal output** (stream command execution)
- [ ] **Approval flows in chat** (HITL decisions via buttons)
- [ ] **Agent handoff transparency** (show when switching agents)

---

## Reference Links

### Documentation

- [LLM Operations Guide](./llm-operations.md) - Model selection, training, deployment
- [LangSmith Tracing Guide](../integrations/langsmith-tracing.md) - Observability setup
- [Architecture Overview](./ARCHITECTURE.md) - System design

### External Resources

- [OpenRouter API Docs](https://openrouter.ai/docs) - Model pricing, rate limits
- [LangGraph Streaming Guide](https://langchain-ai.github.io/langgraph/how-tos/stream-values/) - astream_events API
- [Server-Sent Events Spec](https://html.spec.whatwg.org/multipage/server-sent-events.html) - SSE protocol

---

**Questions?** File an issue in [Linear](https://linear.app/dev-ops/project/codechef-78b3b839d36b) with label `streaming-chat`.
