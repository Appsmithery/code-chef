# Agent Endpoints

Complete API reference for all Dev-Tools agents.

**Status:** Phase 2 implementation complete (2025-11-13)  
**Architecture:** FastAPI-based microservices with MECE responsibility segregation  
**Token Optimization:** Minimal context loading, template-first generation, incremental processing

---

## MCP Gateway

**Base URL:** `http://gateway-mcp:8000`  
**Port:** 8000  
**Status:** ✅ Operational

### Endpoints

- `GET /health` — Service heartbeat and status check
- `GET /.well-known/oauth-protected-resource/mcp` — MCP metadata and service discovery
- `GET /oauth/linear/install` — Redirects workspace admins to Linear OAuth (actor=`app`)
- `GET /oauth/linear/callback` — Handles Linear OAuth return, stores workspace token
- `GET /oauth/linear/status` — Returns current token status (workspace, expiry, fallback info)
- `GET /api/linear-issues` — Fetches roadmap issues (default filters: started, unstarted, backlog)
- `GET /api/linear-project/:projectId` — Fetches a specific project with roadmap issues

---

## Orchestrator Agent

**Base URL:** `http://orchestrator:8001`  
**Port:** 8001  
**Status:** ✅ Implemented & Tested

**Primary Role:** Task delegation, context routing, and workflow coordination

### Endpoints

- `GET /health` — Service heartbeat and version check

  - Returns: `{"status": "ok", "service": "orchestrator", "timestamp": "ISO8601", "version": "1.0.0"}`

- `POST /orchestrate` — Submit development request for task decomposition and routing

  - Body: `{"description": "string", "project_context": {}, "workspace_config": {}, "priority": "string"}`
  - Returns: `{"task_id": "uuid", "subtasks": [...], "routing_plan": {...}, "estimated_tokens": number}`
  - **HITL Behavior:** When a request is flagged as high/critical risk, the response includes `routing_plan.status = "approval_pending"` plus an `approval_request_id`. Operators must approve via `task workflow:approve REQUEST_ID=<id>` before resuming.
  - **Token Usage:** < 500 tokens per routing decision

- `POST /resume/{task_id}` — Resume an approval-gated workflow after human approval

  - Usage: `curl -X POST http://localhost:8001/resume/<task_id>` once the corresponding approval request shows `status=approved`
  - Returns the same payload schema as `/orchestrate`, but now with populated subtasks/routing plan
  - Errors: `409` (still pending), `403` (rejected), `410` (expired)

- `GET /tasks/{task_id}` — Retrieve task status and subtask progress

  - Returns: Full task response with subtask statuses and routing plan

- `GET /agents` — List available specialized agents and their endpoints
  - Returns: `{"agents": [{"type": "string", "endpoint": "url", "status": "string"}]}`

**Hand-off Protocol:**  
Receives user requests → Decomposes into subtasks → Routes to specialized agents → Tracks completion

---

## Feature Development Agent

**Base URL:** `http://feature-dev:8002`  
**Port:** 8002  
**Status:** ✅ Implemented & Tested

**Primary Role:** Application code generation and feature implementation

### Endpoints

- `GET /health` — Service heartbeat and version check

  - Returns: `{"status": "ok", "service": "feature-dev", "timestamp": "ISO8601", "version": "1.0.0"}`

- `POST /implement` — Implement feature with code generation and testing

  - Body: `{"description": "string", "context_refs": [...], "project_context": {}, "task_id": "uuid"}`
  - Returns: `{"feature_id": "uuid", "status": "string", "artifacts": [...], "test_results": [...], "commit_message": "string", "estimated_tokens": number, "context_lines_used": number}`
  - **Token Usage:** Minimal context (10-50 relevant lines), incremental generation

- `GET /patterns` — Retrieve cached coding patterns for token optimization

  - Returns: `{"patterns": [...], "cache_hit_rate": number, "token_savings": "string"}`

- `POST /query-rag` — Query RAG Context Manager for relevant code snippets
  - Body: `{"query": "string"}`
  - Returns: `{"query": "string", "results": [...], "total_lines": number, "token_estimate": number}`

**Hand-off Protocol:**  
Receives feature requirements → Queries RAG → Generates code → Tests → Delegates to Code Review

---

## Code Review Agent

**Base URL:** `http://code-review:8003`  
**Port:** 8003  
**Status:** ✅ Implemented

**Primary Role:** Quality assurance, static analysis, and security scanning

### Endpoints

- `GET /health` — Service heartbeat and version check

  - Returns: `{"status": "ok", "service": "code-review", "timestamp": "ISO8601", "version": "1.0.0"}`

- `POST /review` — Review code changes with static analysis and security scanning
  - Body: `{"task_id": "string", "diffs": [{"file_path": "string", "changes": "string", "context_lines": number}], "test_results": {}}`
  - Returns: `{"review_id": "uuid", "status": "string", "findings": [...], "approval": boolean, "summary": "string", "estimated_tokens": number}`
  - **Token Usage:** Only diff context (changed lines + 5-line context window), ~60% reduction

**Hand-off Protocol:**  
Receives code diffs + test results → Analyzes → Approves or requests revisions → Delegates to CI/CD or back to Feature Dev

---

## Infrastructure Agent

**Base URL:** `http://infrastructure:8004`  
**Port:** 8004  
**Status:** ✅ Implemented

**Primary Role:** Infrastructure-as-code generation and deployment configuration

### Endpoints

- `GET /health` — Service heartbeat and version check

  - Returns: `{"status": "ok", "service": "infrastructure", "timestamp": "ISO8601", "version": "1.0.0"}`

- `POST /generate` — Generate infrastructure-as-code configurations

  - Body: `{"task_id": "string", "infrastructure_type": "docker|kubernetes|terraform|cloudformation", "requirements": {}}`
  - Returns: `{"infra_id": "uuid", "artifacts": [...], "validation_status": "string", "estimated_tokens": number, "template_reuse_pct": number}`
  - **Token Usage:** Template-first generation, 70-85% token reduction via parameter customization

- `GET /templates` — List available infrastructure templates
  - Returns: `{"templates": [{"name": "string", "usage_count": number}]}`

**Hand-off Protocol:**  
Receives infrastructure requirements → Customizes templates → Validates → Delegates to CI/CD for deployment

---

## CI/CD Agent

**Base URL:** `http://cicd:8005`  
**Port:** 8005  
**Status:** ✅ Implemented

**Primary Role:** Automation workflow generation and deployment orchestration

### Endpoints

- `GET /health` — Service heartbeat and version check

  - Returns: `{"status": "ok", "service": "cicd", "timestamp": "ISO8601", "version": "1.0.0"}`

- `POST /generate` — Generate CI/CD pipeline configuration

  - Body: `{"task_id": "string", "pipeline_type": "github-actions|gitlab-ci|jenkins", "stages": [...], "deployment_strategy": "string"}`
  - Returns: `{"pipeline_id": "uuid", "artifacts": [...], "validation_status": "string", "estimated_tokens": number, "template_reuse_pct": number}`
  - **Token Usage:** Template library, 75% token reduction via customization

- `POST /deploy` — Execute deployment workflow
  - Body: Deployment configuration
  - Returns: `{"deployment_id": "string", "status": "string"}`

**Hand-off Protocol:**  
Receives approved changes + infra configs → Generates pipeline → Executes deployment → Monitors execution

---

## Documentation Agent

**Base URL:** `http://documentation:8006`  
**Port:** 8006  
**Status:** ✅ Implemented

**Primary Role:** Documentation generation and maintenance

### Endpoints

- `GET /health` — Service heartbeat and version check

  - Returns: `{"status": "ok", "service": "documentation", "timestamp": "ISO8601", "version": "1.0.0"}`

- `POST /generate` — Generate documentation artifacts

  - Body: `{"task_id": "string", "doc_type": "readme|api-docs|guide|comments", "context_refs": [...], "target_audience": "string"}`
  - Returns: `{"doc_id": "uuid", "artifacts": [...], "estimated_tokens": number, "template_used": "string"}`
  - **Token Usage:** Template-based generation with RAG context queries

- `GET /templates` — List available documentation templates
  - Returns: `{"templates": [{"name": "string", "sections": [...], "format": "string"}]}`

**Hand-off Protocol:**  
Receives documentation request → Queries RAG for context → Generates docs → Returns artifacts

---

## RAG Context Manager

**Base URL:** `http://rag-context:8007`  
**Port:** 8007  
**Status:** ✅ Backed by Qdrant Cloud + Gradient embeddings

**Primary Role:** Semantic code/document retrieval sourced from DigitalOcean KB exports and repository docs.

### Endpoints

- `GET /health` — Service heartbeat plus Qdrant + MCP connectivity status.
- `POST /query` — Retrieve top-N chunks from `the-shop` (or any configured collection). Body: `{"query": "string", "collection": "the-shop", "n_results": 5}`.
- `POST /index` — Upsert documents with automatic Gradient embeddings. Body mirrors the FastAPI `IndexRequest` schema.
- `POST /query/mock` — Deterministic fixtures when Gradient/Qdrant credentials are absent (local testing).

**Support Script:** `scripts/sync_kb_to_qdrant.py` triggers Gradient indexing jobs, downloads signed exports, and mirrors embeddings into Qdrant Cloud.

---

## Service Discovery

All agents expose consistent health check endpoints at `GET /health` with the following response format:

```json
{
  "status": "ok",
  "service": "<agent-name>",
  "timestamp": "2025-11-13T04:00:00.000000",
  "version": "1.0.0"
}
```

## Token Optimization Strategy

- **Orchestrator:** Processes only metadata (< 500 tokens/decision)
- **Feature Dev:** Minimal context spans (10-50 lines), incremental generation (60-70% savings)
- **Code Review:** Diff-only context with 5-line window (~60% reduction)
- **Infrastructure:** Template-first customization (70-85% reduction)
- **CI/CD:** Template library (75% reduction)
- **Documentation:** Template-based with targeted RAG queries
- **RAG:** Offloads similarity search to Qdrant Cloud so agents fetch <1 KB payloads per query

## Architecture Notes

- All agents are FastAPI-based microservices
- MECE responsibility boundaries enforced
- Hand-off protocol uses minimal context pointers
- State persistence via shared layer (future integration)
- RAG Context Manager streams Gradient embeddings into Qdrant Cloud and serves all semantic lookups
