# Orchestrator Agent

Central command layer that interprets incoming work, breaks it into autonomous subtasks, and supervises execution across every downstream agent.

## Overview

The Orchestrator Agent is the first touchpoint for any automation request. It performs natural-language intent parsing, plans a multi-step workflow, assigns each unit of work to the most capable specialist agent, and aggregates progress back into a single timeline. This README is optimized for both human operators and AI-driven orchestrators consuming metadata about the agent.

### MCP Integration Architecture

The orchestrator leverages the **Model Context Protocol (MCP)** through a centralized HTTP gateway at `http://gateway-mcp:8000`. It has access to 150+ tools across 17 MCP servers.

**Recommended Tool Servers:**

- `memory` (create_entities, create_relations, read_graph, search_nodes) - Task graph persistence and context management
- `context7` (search_docs, list_docs) - Documentation and knowledge base access
- `notion` (create_page, update_page, search_pages, query_database) - Planning artifacts and team collaboration
- `gitmcp` (clone, commit, push, status, diff) - Repository operations and version control
- `dockerhub` (list_tags, inspect_image, search_images) - Container image registry queries
- `playwright` (navigate, click, screenshot, pdf) - UI validation and workflow testing
- `rust-mcp-filesystem` (read_file, write_file, list_directory, search) - Workspace file operations

**Shared Tool Servers:** `time`, `fetch`, additional filesystem/context tools

#### Progressive Tool Disclosure with LangChain Integration

To manage the 150+ available tools efficiently, the orchestrator implements **progressive tool disclosure** with **LangChain function calling**:

**Architecture (3-Layer Approach):**

1. **Discovery Layer** (`progressive_mcp_loader.py`):

   - Filters 150+ tools → 10-30 relevant tools based on task description
   - Keyword-based matching (60+ keyword mappings)
   - 80-90% token reduction in LLM context

2. **Conversion Layer** (`mcp_client.to_langchain_tools()`):

   - Converts MCP tool schemas to LangChain `BaseTool` instances
   - Wraps MCP gateway calls in async Python functions
   - Each tool becomes callable via function calling protocol

3. **Binding Layer** (`gradient_client.get_llm_with_tools()`):
   - Binds tools to LLM via `llm.bind_tools(tools)`
   - Enables LangChain function calling
   - LLM can request tool invocations in responses

**Key Innovation:** LLM can now **INVOKE** tools via function calling, not just read tool documentation.

**Tool Loading Strategies:**

- `MINIMAL`: Keyword-based filtering (80-95% savings, default for decomposition)
- `AGENT_PROFILE`: Agent manifest-based (60-80% savings)
- `PROGRESSIVE`: Minimal + high-priority agent tools (70-85% savings)
- `FULL`: All 150+ tools (0% savings, debugging only)

**Implementation:** The orchestrator uses the **MCPClient** from `lib.mcp_client` to invoke tools, log telemetry, and validate agent capabilities. Tool allocations are pre-loaded from `shared/lib/agents-manifest.json` for zero-latency routing decisions.

#### Week 5: Zen Pattern Integration (November 2025)

The orchestrator incorporates battle-tested patterns from the Zen MCP Server, a production multi-model orchestration system managing 1000+ conversation turns:

**1. Parent Workflow Chains** (`shared/lib/workflow_reducer.py`):

- Hierarchical workflow composition via `parent_workflow_id` field
- Complete audit trails across workflow boundaries (e.g., PR deployment → hotfix)
- Circular reference detection with 20-level max depth protection
- Functions: `get_workflow_chain()`, `get_workflow_chain_ids()`, `get_workflow_depth()`

**2. Resource Deduplication** (`agent_orchestrator/workflows/workflow_engine.py`):

- Newest-first priority: walk events backwards to find latest resource versions
- **80-90% token savings** when resources modified multiple times (proven in Zen production)
- Real-world example: `docker-compose.yml` modified 5x → 1 file in context (5000 tokens → 1000 tokens)
- Functions: `_deduplicate_workflow_resources()`, `build_workflow_context()`

**3. Workflow TTL Management** (`agent_orchestrator/workflows/workflow_engine.py`):

- Auto-expiration prevents memory leaks: abandoned workflows expire after configurable TTL
- Event-based TTL refresh: active workflows stay alive indefinitely (Zen pattern: 100+ concurrent conversations)
- Environment-specific defaults: dev (3h), staging (12h), production (24h)
- PostgreSQL tracking: `workflow_ttl` table with `expires_at` timestamps
- Cleanup function: `cleanup_expired_workflows()` (run via cron hourly)
- Configuration: `WORKFLOW_TTL_HOURS` in `.env` (default: 24)

**Impact:**

- Token cost reduction: 80-90% via resource deduplication
- Memory leak prevention: automatic workflow expiration
- Complete audit trails: parent workflow chains enable root cause analysis
- Battle-tested reliability: patterns proven in 1000+ production conversations

**Database Schema:** See `config/state/workflow_events.sql` for migration commands and view definitions.

## Core Responsibilities

- **Task understanding:** Use LLM-powered parsing with LangChain tool binding to convert free-form requests into structured objectives, constraints, and acceptance criteria.
- **Plan synthesis:** Derive a MECE (mutually exclusive, collectively exhaustive) subtask plan, sequencing steps with dependencies and approval gates.
- **Agent brokerage:** Match each subtask to the appropriate specialist agent using capability tags, SLAs, and current load.
- **Context propagation:** Maintain a shared execution context (task graph, artifacts, audit trail) and forward the minimal necessary data to each agent.
- **Runtime governance:** Track status, handle retries or escalations, and emit heartbeat updates for observability and SLA monitoring.
- **Tool orchestration:** Progressive tool disclosure reduces token costs by 80-90% while enabling actual tool invocation via LangChain function calling.

## Chat Request Flow & Intent-Aware Optimization

The orchestrator implements **intent-aware context extraction** for optimal performance in the VS Code chat interface. This optimization reduces latency by **60-80%** for conversational queries while maintaining full context for task execution.

### Request Flow (December 2025)

```
User types message → handleChatRequest()
  ├─ Check if command? → handleCommand()
  │    └─ /execute → Extract full context + force Agent mode
  │
  ├─ [1] Health check (200ms) ✅ Always run - fast safety check
  │
  ├─ [2] Quick intent detection (LOCAL, <10ms)
  │    ├─ Pattern match: "hello|hi|hey|what can you do|explain X"
  │    └─ If conversational → SKIP CONTEXT EXTRACTION
  │
  ├─ If conversational:
  │    ├─ [3] Create session (fast)
  │    └─ [4] Stream from orchestrator (minimal payload)
  │         └─ Backend: conversational_handler_node → fast response
  │
  └─ If task execution:
       ├─ [3] Extract workspace context (ONLY NOW) ⚠️ 500-2000ms
       ├─ [4] Extract chat references (#file, symbols)
       ├─ [5] Extract Copilot model metadata
       ├─ [6] Create session
       └─ [7] Stream from orchestrator (full payload)
            └─ Backend: intent_recognizer → workflow_router → specialist agents
```

### Performance Impact

| Query Type             | Before Optimization | After Optimization | Improvement |
| ---------------------- | ------------------- | ------------------ | ----------- |
| "hello"                | 2500ms              | 400ms              | **84%**     |
| "what can you do?"     | 2300ms              | 350ms              | **85%**     |
| "explain JWT"          | 2400ms              | 800ms              | **67%**     |
| "implement feature X"  | 2500ms              | 2500ms             | Same        |
| `/execute implement X` | 2500ms              | 2500ms             | Same        |

### Intent Detection Strategy

**Client-Side Pre-Filter** (`chatParticipant.ts`):

- Regex pattern matching for high-confidence conversational/task signals
- Decision made in <10ms before any backend communication
- Falls back to full context extraction when uncertain (safe default)

**Backend Integration** (`main.py`):

- Receives `intent_hint` and `context_extracted` metadata from client
- Uses hints to resolve ambiguity when LLM confidence is low (<0.85)
- Tracks optimization metrics via Prometheus

**System Prompt Awareness**:

- Supervisor and specialist agents check `context_extracted` flag
- Gracefully degrade by requesting clarification when context is missing
- No breaking changes to existing workflows

### Metrics

**Prometheus Endpoints** (`http://localhost:8001/metrics`):

- `orchestrator_context_extraction_skipped_total` - Tracks optimization wins
- `orchestrator_context_extraction_duration_seconds` - Measures extraction time
- `orchestrator_intent_override_total` - Monitors client hint usage vs LLM classification

**LangSmith Traces**: Filter by `context_extracted: false` to identify optimized queries.

## Decision Model & State

- **Planning heuristic:** Hybrid rule-based + LLM planner with guardrails for scope, prerequisites, and termination conditions.
- **State store:** Task graph persisted in Postgres via the shared workflow schema; ephemeral execution notes cached in Redis.
- **Idempotency:** All orchestration commands are keyed by `task_id`; duplicate submissions return the existing plan and status.

## API Surface

| Method | Path                 | Purpose                                                                                                                           | Primary Request Fields                                                       | Success Response Snapshot                                                                                         |
| ------ | -------------------- | --------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `POST` | `/orchestrate`       | Submit a new high-level task and trigger decomposition (may return `approval_pending` with Linear sub-issue created under DEV-68) | `task_id`, `title`, `description`, `priority`, `metadata.context`            | `{ "task_id": "...", "status": "planned" \| "approval_pending", "approval_issue": "DEV-133", "subtasks": [...] }` |
| `POST` | `/chat/stream`       | Stream conversational responses with intent-aware optimization (Ask mode, 60-80% faster for queries)                              | `message`, `session_id`, `context` (with `intent_hint`, `context_extracted`) | SSE stream: `data: {"type": "content", "content": "..."}\n\n`                                                     |
| `POST` | `/execute/stream`    | Stream task execution with full agent workflow (Agent mode, full context required)                                                | `message`, `session_id`, `context` (full workspace context)                  | SSE stream: `data: {"type": "agent_complete", "agent": "feature-dev"}\n\n`                                        |
| `POST` | `/resume/{task_id}`  | Resume a workflow once its approval request is approved (via Linear issue status change)                                          | `task_id` (path)                                                             | `{ "task_id": "...", "status": "planned", "subtasks": [...] }`                                                    |
| `POST` | `/execute/{task_id}` | Begin or resume execution of a planned workflow                                                                                   | `execution_mode` (`auto`/`manual`), optional checkpoints                     | `{ "task_id": "...", "status": "running" }`                                                                       |
| `GET`  | `/tasks/{task_id}`   | Fetch real-time status, agent assignments, and artifacts                                                                          | n/a                                                                          | `{ "task_id": "...", "status": "running", "subtasks": [...], "metrics": {...} }`                                  |
| `GET`  | `/agents`            | Discover available specialist agents and their declared skills                                                                    | query filters: `domain`, `capability`, `health`                              | `{ "agents": [{"name": "code-review", "skills": [...]}] }`                                                        |
| `GET`  | `/health`            | Service health check with dependency status                                                                                       | n/a                                                                          | `{ "status": "ok", "service": "orchestrator", "dependencies": {...} }`                                            |

### Sample: `POST /orchestrate`

```json
{
  "task_id": "feature-1087",
  "title": "Implement invoice PDF export",
  "description": "Add PDF export support to the billing dashboard including automated regression tests.",
  "priority": "high",
  "metadata": {
    "repository": "git@github.com:appsmithery/dev-tools.git",
    "requester": "product-management",
    "due_date": "2025-11-22"
  }
}
```

### Sample: `POST /chat/stream` (Conversational)

```json
{
  "message": "What can you do?",
  "session_id": "session-abc123",
  "context": {
    "intent_hint": "conversational",
    "context_extracted": false,
    "session_mode": "ask",
    "copilot_model": {
      "vendor": "microsoft",
      "family": "gpt-4o"
    }
  }
}
```

**Response** (SSE stream):

```
data: {"type": "content", "content": "I can help you with:\n\n"}

data: {"type": "content", "content": "1. **Code Implementation** - Feature development, bug fixes\n"}

data: {"type": "content", "content": "2. **Code Review** - Security analysis, quality checks\n"}

data: {"type": "done", "session_id": "session-abc123"}

data: [DONE]
```

### Sample: `POST /execute/stream` (Task Execution)

```json
{
  "message": "Add JWT authentication to the API",
  "session_id": "session-xyz789",
  "context": {
    "intent_hint": "task",
    "context_extracted": true,
    "session_mode": "agent",
    "workspace_root": "/home/user/project",
    "git_branch": "main",
    "chat_references": {
      "files": ["/home/user/project/api/auth.py"]
    }
  }
}
```

**Response** (SSE stream):

```
data: {"type": "workflow_status", "workflow": "feature_development"}

data: {"type": "content", "content": "🔧 Routing to feature-dev agent...\n\n"}

data: {"type": "agent_complete", "agent": "feature-dev", "outputs": {"files_created": ["api/middleware/jwt.py"]}}

data: {"type": "done", "session_id": "session-xyz789", "workflow_id": "wf-12345"}

data: [DONE]
```

### Sample Status Response

```json
{
  "task_id": "feature-1087",
  "status": "running",
  "subtasks": [
    {
      "subtask_id": "feature-dev::feature-1087::1",
      "agent": "feature-dev",
      "state": "completed",
      "outputs": {
        "branch": "feature/invoice-pdf",
        "pull_request": "https://github.com/.../pull/412"
      }
    },
    {
      "subtask_id": "code-review::feature-1087::1",
      "agent": "code-review",
      "state": "running"
    }
  ],
  "metrics": {
    "elapsed_seconds": 1482,
    "on_time": true
  }
}
```

## HITL Workflow Runbook

Certain tasks (production deploys, destructive DB work, secrets rotation) require a human approval gate. The orchestrator enforces this by returning `routing_plan.status = "approval_pending"` along with an `approval_request_id`.

1. Initialize the approval schema once per environment:

```powershell
task workflow:init-db
```

2. Submit a high-risk task. Capture both the `task_id` and `approval_request_id` returned by `/orchestrate`.
3. Inspect the queue:

```powershell
task workflow:list-pending
```

4. Approve or reject:

```powershell
task workflow:approve REQUEST_ID=<uuid>
task workflow:reject REQUEST_ID=<uuid> REASON="Need rollback plan"
```

5. Resume orchestration once approved:

```powershell
Invoke-RestMethod -Uri http://localhost:8001/resume/<task_id> -Method Post
```

Rejections or expirations propagate back as HTTP errors (403/410) so the requester can re-plan safely.

### Approval Notifications

The orchestrator emits real-time notifications for approval requests using an event-driven architecture:

**Architecture:**

- **Event Bus**: In-memory async pub/sub (singleton per agent)
- **Linear Integration**: Posts formatted comments to workspace approval hub (PR-68)
- **Email Fallback**: SMTP-based notifications (optional, requires SMTP config)

**Notification Flow:**

1. High/critical risk task submitted → Approval created in PostgreSQL
2. `approval_required` event emitted → 2 subscribers (Linear + Email)
3. Linear notifier posts comment to PR-68 with @mentions
4. Operator receives Linear notification (email/mobile/desktop) in <1 second

**Configuration** (`config/env/.env`):

```bash
LINEAR_API_KEY=lin_oauth_...              # OAuth token for GraphQL API
LINEAR_APPROVAL_HUB_ISSUE_ID=PR-68        # Workspace approval hub issue
SMTP_HOST=smtp.gmail.com                  # Optional email fallback
SMTP_USER=your-email@gmail.com
SMTP_PASS=app-password
NOTIFICATION_EMAIL_TO=ops-team@company.com
```

**API Endpoints:**

- `POST /approve/{approval_id}?approver_id=...&approver_role=...&justification=...` — Approve request
- `POST /reject/{approval_id}?approver_id=...&approver_role=...&reason=...` — Reject request
- `GET /approvals/pending` — List pending approvals
- `GET /approvals/{approval_id}` — Get approval details

**Example Usage:**

```powershell
# Approve via API
Invoke-WebRequest -Uri "http://localhost:8001/approve/<approval-id>?approver_id=alex@example.com&approver_role=tech_lead&justification=Reviewed+and+approved" -Method POST

# Check Linear workspace hub (PR-68) for notification comment
# Comment includes: risk emoji, approval ID, task description, action commands
```

**Documentation**: See `support/docs/NOTIFICATION_SYSTEM.md` for complete architecture and troubleshooting.

## Context Contracts

- **Inbound context:** Free-form natural language, project metadata, optional repo pointers, SLA hints.
- **Shared context schema:** JSON task graph persisted with fields `task_id`, `subtasks`, `dependencies`, `artifacts`, `status_history`.
- **Outbound payloads:** Minimal subtask brief + references to shared context and artifact storage locations.

## Observability

- Emits structured logs to `logs/orchestrator.log` with correlation IDs per `task_id` and `subtask_id`.
- **LangSmith Tracing**: Automatic LLM tracing for all LangGraph workflows and agent nodes (project: "agents", workspace: 5029c640-3f73-480c-82f3-58e402ed4207).
  - Filter by `context_extracted: false` to identify intent-optimized conversational queries
  - Filter by `intent_hint: conversational` to track client-side pre-filter effectiveness
- **Prometheus Metrics**: Exposed at `http://localhost:8001/metrics` via prometheus-fastapi-instrumentator. Key metrics include:
  - `http_request_duration_seconds`: HTTP request latencies
  - `http_requests_total`: Total HTTP requests by method/status
  - `orchestrator_context_extraction_skipped_total`: Context extractions skipped due to intent optimization
  - `orchestrator_context_extraction_duration_seconds`: Time spent extracting workspace context
  - `orchestrator_intent_override_total`: Times client intent hint overrode backend classification
  - `orchestrator_intent_recognition_total`: Intent recognition attempts by mode and type
  - `orchestrator_intent_recognition_confidence`: Intent recognition confidence scores
  - `python_gc_objects_collected_total`: Python garbage collection metrics
  - `process_cpu_seconds_total`: CPU usage
  - `process_resident_memory_bytes`: Memory usage
- **Grafana Cloud**: Metrics collected by Grafana Alloy (15s scrape interval) and pushed to https://appsmithery.grafana.net.
- **Health Endpoint**: `GET /health` returns service status, timestamp, and dependency health checks.

## Integration Notes

- Use exponential backoff when polling `GET /tasks/{task_id}`; prefer webhook callbacks where available.
- Always provide deterministic `task_id` inputs to ensure idempotent reruns.
- Provide capability tags when registering downstream agents so the orchestrator can maintain accurate routing tables.

## Failure Modes & Recovery

- **Validation error (400):** Input missing required fields; the orchestrator returns structured diagnostics with `fields[].issue`.
- **Agent unavailable (503):** The orchestrator marks the subtask as `blocked` and emits an alert for manual routing.
- **Timeout escalation:** If a subtask exceeds SLA, the orchestrator auto-retries (up to 3 attempts) then flags the workflow for human review.
