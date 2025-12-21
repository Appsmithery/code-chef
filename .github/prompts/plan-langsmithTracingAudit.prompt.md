# Plan: Comprehensive LangSmith Tracing Audit & Implementation

**TL;DR**: Code-chef has solid LangGraph node tracing but critical gaps at HTTP entry points, LLM client calls, and tool invocations. Adding `@traceable` decorators to ~25 functions will provide end-to-end visibility from VS Code extension → orchestrator → agents → LLMs → tools.

## Steps

### 1. Add tracing to FastAPI endpoints in `agent_orchestrator/main.py`

- Wrap `/chat`, `/chat/stream`, `/execute/stream` with `@traceable` decorators (lines 3192, 3499, 3966)
- Add metadata: `user_id`, `command_type`, `thread_id` to trace context
- Tag with `["http", "entrypoint", "streaming"]` for filtering

### 2. Instrument LLM client in `shared/lib/llm_client.py`

- Add `@traceable` to `acomplete()`, `acomplete_structured()` methods (~lines 100-250)
- Capture model name, token counts, latency in trace metadata
- Enables cost tracking and performance analysis per model

### 3. Trace agent invocations in `agent_orchestrator/agents/_shared/base_agent.py`

- Decorate `invoke()` method (~line 781) with `@traceable(name="agent_invoke")`
- Include agent name, task type, workflow_id in metadata
- Links HTTP request → specific agent execution

### 4. Capture MCP tool calls in `agent_orchestrator/main.py`

- Add `@traceable` to `/tools/{tool_name}` endpoint (line 2363)
- Log tool name, parameters, execution time
- Trace relationship: agent → tool → result

### 5. Verify environment propagation across all services

- Confirm `LANGCHAIN_TRACING_V2=true` in `deploy/docker-compose.yml` for orchestrator ✅
- Add tracing env vars to `rag-context`, `state-persistence`, `agent-registry` services if they make LLM calls
- Test with `curl` to orchestrator health endpoint, verify traces appear in LangSmith

### 6. Enrich trace metadata using `config/observability/tracing-schema.yaml`

- Add `experiment_group`, `model_version`, `config_hash` to all `@traceable` decorators
- Enables A/B testing comparison (baseline vs trained models)
- Use `longitudinal_tracker` for regression detection across extension versions

## Further Considerations

### 1. Sampling strategy

Currently set to 100% for agent invocations, 10% for HITL polling (`config/observability/tracing.yaml`). Should we reduce production sampling to 50% to minimize LangSmith costs while maintaining visibility?

### 2. Trace relationships

How should we structure parent-child relationships?

- **Option A**: HTTP request as root span, with agent → LLM → tool as children
- **Option B**: Separate top-level traces for each layer (easier filtering but loses causality)
- **Option C**: Hybrid - use `run_tree` context manager for explicit parent linking

### 3. Error capture

Should we add try/except wrappers with `traceable(capture_exceptions=True)` or rely on LangSmith's automatic error detection?

---

## Audit Findings Summary

### Current Tracing Coverage

- **Total `@traceable` imports found**: 21 files
- **LangGraph nodes traced**: 7/7 (100%) ✅
- **Workflow operations traced**: ~80% ✅
- **HTTP endpoints traced**: 0/20 (0%) ❌
- **LLM client methods traced**: 0/4 (0%) ❌
- **Agent invoke methods traced**: 0/1 (0%) ❌
- **Tool invocations traced**: 0/1 (0%) ❌

**Overall Coverage**: ~60% (good foundation, critical gaps in entry points)

### Critical Gaps Identified

#### ❌ Missing Tracing on FastAPI Endpoints

**Major Gap**: Main orchestrator endpoints have **NO** `@traceable` decorators

**Affected Endpoints** (`agent_orchestrator/main.py`):

- `@app.post("/chat")` - Line 3192
- `@app.post("/chat/stream")` - Line 3499
- `@app.post("/execute/stream")` - Line 3966
- `@app.post("/orchestrate")` - Line 1349
- `@app.post("/orchestrate/langgraph")` - Line 4675
- `@app.post("/orchestrate/langgraph/resume/{thread_id}")` - Line 4884
- `@app.post("/workflow/smart-execute")` - Line 5347
- `@app.post("/workflow/execute")` - Line 5445
- `@app.post("/workflow/resume/{workflow_id}")` - Line 5575

**Impact**: No end-to-end trace visibility from HTTP request → LangGraph execution

#### ❌ Missing Tracing in LLM Client

**File**: `shared/lib/llm_client.py`

The `LLMClient` class has:

- ✅ Comments mentioning LangSmith tracing
- ❌ **NO** `@traceable` decorators on methods
- ❌ Methods not traced:
  - `complete()` - Line ~100
  - `complete_structured()` - Line ~150
  - `acomplete()` - Line ~200
  - `acomplete_structured()` - Line ~250

**Impact**: Direct LLM calls bypassing LangChain (if any) are not traced

#### ❌ Missing Tracing in Base Agent

**File**: `agent_orchestrator/agents/_shared/base_agent.py`

The `invoke()` method (**line ~781**):

```python
# MISSING @traceable
async def invoke(self, messages, config=None):
    response = await executor.ainvoke(messages, config=config)
    return response
```

**Impact**: Agent invocations not wrapped in dedicated traces (relies only on LangChain's internal tracing)

#### ❌ Missing Tracing in Tool Invocations

**File**: `agent_orchestrator/main.py`

```python
@app.post("/tools/{tool_name}") # Line 2363
async def invoke_tool(tool_name: str, request: ToolInvocationRequest):
    # NO @traceable decorator
    result = await mcp_tool_client.invoke_tool(...)
```

**Impact**: MCP tool calls not individually traced

### Files Needing @traceable Decorators

| Priority        | File                                              | Functions Needing Decoration                                           | Lines            |
| --------------- | ------------------------------------------------- | ---------------------------------------------------------------------- | ---------------- |
| **🔴 CRITICAL** | `agent_orchestrator/main.py`                      | `/chat`, `/orchestrate`, `/chat`                                       | 1547, 1351, 3192 |
| **🔴 CRITICAL** | `agent_orchestrator/main.py`                      | Streaming endpoints: `/chat/stream`, `/execute/stream`                 | 3499, 3966       |
| **🔴 CRITICAL** | `shared/lib/llm_client.py`                        | `complete`, `complete_structured`, `acomplete`, `acomplete_structured` | ~100-250         |
| **🟡 HIGH**     | `agent_orchestrator/agents/_shared/base_agent.py` | `invoke` method                                                        | ~781             |
| **🟡 HIGH**     | `agent_orchestrator/main.py`                      | `/tools/{tool_name}`                                                   | 2363             |
| **🟢 MEDIUM**   | `agent_orchestrator/workflows/*.py`               | Workflow execution methods                                             | 4727, 4962, 5194 |
| **🟢 MEDIUM**   | `shared/lib/linear_client.py`                     | Linear webhook handler                                                 | 1172             |

### Well-Traced Components ✅

- **LangGraph nodes** (`agent_orchestrator/graph.py`): All 7 nodes decorated
  - `delegate_task`, `execute_task`, `analyze_results`, `decide_next`, `handle_approval`, `handle_error`, `finalize_workflow`
- **Workflow operations** (`agent_orchestrator/workflows/workflow_engine.py`, `workflow_router.py`)
- **Agent memory operations** (`shared/lib/agent_memory.py`)
- **HITL operations** (`shared/lib/hitl_manager.py`)
- **Linear integration** (`shared/lib/linear_project_manager.py`)
- **GitHub permalink generation** (`shared/lib/github_permalink_generator.py`)
- **Dependency handling** (`agent_orchestrator/agents/_shared/dependency_manager.py`)

### Environment Configuration ✅

**Location**: `deploy/docker-compose.yml`

Environment variables configured in orchestrator service:

```yaml
LANGCHAIN_TRACING_V2: ${LANGCHAIN_TRACING_V2:-true}
LANGCHAIN_PROJECT: ${LANGCHAIN_PROJECT:-code-chef-production}
TRACE_ENVIRONMENT: ${TRACE_ENVIRONMENT:-production}
EXPERIMENT_GROUP: ${EXPERIMENT_GROUP:-code-chef}
```

### Configuration Files Status

#### ✅ Properly Configured

1. **Tracing Schema** (`config/observability/tracing-schema.yaml`)
   - Complete metadata schema defined
   - Supports A/B testing, longitudinal tracking, RAG isolation
2. **Tracing Config** (`config/observability/tracing.yaml`)
   - Sampling rates configured
   - Per-operation sampling policies
3. **Docker Compose** (`deploy/docker-compose.yml`)
   - Environment variables set for orchestrator service

#### ⚠️ Documentation Status

- **LLM Operations Guide** (`support/docs/operations/LLM_OPERATIONS.md`)
  - Comprehensive documentation exists
  - Documents new project structure (Dec 10, 2025)
  - Metadata schema examples provided
