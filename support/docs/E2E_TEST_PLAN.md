# End-to-End Testing Plan: Multi-Agent LangGraph Workflow

**Generated**: November 21, 2025  
**Target System**: LangGraph Single-Orchestrator Architecture  
**Trace Reference**: https://smith.langchain.com/public/6c4fb824-4ba6-4d73-a4c9-7779283b63a5/r  
**Deployment**: Production droplet (45.55.173.72)

---

## Executive Summary

This plan validates the complete LangGraph multi-agent workflow system through systematic end-to-end testing, covering:

1. **Agent Functionality**: All 6 agents (supervisor + 5 specialists) execute tasks correctly
2. **MCP Tool Access**: 150+ tools across 17 servers accessible via progressive disclosure
3. **Memory & Context**: PostgreSQL checkpointing, Qdrant vector memory, hybrid memory system
4. **HITL Workflow**: Sub-issue creation, approval handling, workflow resumption
5. **LLM Integration**: Gradient AI function calling with proper tool binding
6. **Observability**: LangSmith tracing, Prometheus metrics, Linear notifications

---

## Test Architecture

### Testing Layers

```
Layer 1: Unit Tests (Per-Agent)
    ├── Agent initialization
    ├── Tool binding verification
    ├── Configuration validation
    └── Isolated node execution

Layer 2: Integration Tests (Multi-Agent)
    ├── Supervisor routing
    ├── Agent handoffs
    ├── Shared state management
    └── Tool discovery

Layer 3: Workflow Tests (End-to-End)
    ├── Complete task decomposition
    ├── Sequential execution
    ├── Parallel execution
    ├── HITL interruption/resumption
    └── Error recovery

Layer 4: Production Validation
    ├── Real LLM calls
    ├── Actual Linear API
    ├── Live MCP servers
    └── Full observability stack
```

### Test Environment Matrix

| Environment           | LLM Provider  | MCP Gateway     | Linear API  | State DB   | Purpose                 |
| --------------------- | ------------- | --------------- | ----------- | ---------- | ----------------------- |
| **Local Mock**        | Mocked        | Mocked          | Mocked      | SQLite     | Fast unit tests         |
| **Local Integration** | Gradient Dev  | Docker Compose  | OAuth Token | PostgreSQL | Integration tests       |
| **Staging**           | Gradient Prod | Droplet Gateway | OAuth Token | Droplet PG | Pre-prod validation     |
| **Production**        | Gradient Prod | Droplet Gateway | OAuth Token | Droplet PG | Real workflow execution |

---

## Phase 1: Agent Unit Tests (Existing Tests)

**Location**: `support/tests/`, `test_langgraph_workflow.py`  
**Duration**: 2-5 minutes  
**Status**: ✅ Mostly complete

### 1.1 Agent Initialization Test

**File**: `test_langgraph_workflow.py::test_agent_initialization()`

Validates:

- All 6 agents (supervisor, feature-dev, code-review, infrastructure, cicd, documentation) instantiate correctly
- Agent names match expected values
- LLM clients initialized (Gradient AI)
- Configuration loaded from `config/mcp-agent-tool-mapping.yaml`

**Expected Output**:

```
✅ supervisor: SupervisorAgent(agent_name='supervisor')
✅ feature-dev: FeatureDevAgent(agent_name='feature-dev')
✅ code-review: CodeReviewAgent(agent_name='code-review')
✅ infrastructure: InfrastructureAgent(agent_name='infrastructure')
✅ cicd: CICDAgent(agent_name='cicd')
✅ documentation: DocumentationAgent(agent_name='documentation')
```

**Run Command**:

```powershell
python test_langgraph_workflow.py
```

---

### 1.2 Tool Binding Verification Test

**File**: `test_langgraph_workflow.py::test_tool_binding()`

Validates:

- Each agent has access to its configured MCP tools
- Progressive tool loading strategy configured
- Tool manifests loaded from `config/mcp-agent-tool-mapping.yaml`
- Agent executors initialized with tool chains

**Example Assertions**:

```python
feature_dev = get_agent("feature-dev")
assert "rust-mcp-filesystem" in feature_dev.config["tools"]["allowed_servers"]
assert "gitmcp" in feature_dev.config["tools"]["allowed_servers"]
assert feature_dev.config["tools"]["progressive_strategy"] == "MINIMAL"
```

**Expected Tools Per Agent** (from `mcp-agent-tool-mapping.yaml`):

- **Supervisor**: memory, context7, notion, sequentialthinking (orchestration focus)
- **Feature-Dev**: rust-mcp-filesystem, gitmcp, playwright, hugging-face (code generation)
- **Code-Review**: gitmcp, rust-mcp-filesystem, hugging-face, context7 (analysis focus)
- **Infrastructure**: dockerhub, rust-mcp-filesystem, gitmcp, prometheus (IaC/deployment)
- **CI/CD**: gitmcp, dockerhub, playwright, rust-mcp-filesystem (pipeline automation)
- **Documentation**: rust-mcp-filesystem, notion, context7, hugging-face (docs generation)

---

### 1.3 Workflow Compilation Test

**File**: `test_langgraph_workflow.py::test_workflow_compilation()`

Validates:

- LangGraph app compiles without errors
- All 7 nodes registered (6 agents + approval node)
- Entry point set to supervisor
- Conditional edges configured for routing

**Expected Graph Structure**:

```
START → supervisor_node
supervisor_node → {feature-dev, code-review, infrastructure, cicd, documentation}
{specialist nodes} → approval_node (if high-risk)
approval_node → END (if approved)
approval_node → __interrupt__ (if pending)
```

---

## Phase 2: Multi-Agent Integration Tests

**Location**: `support/tests/workflows/test_multi_agent_workflows.py`  
**Duration**: 10-15 minutes  
**Status**: ⚠️ Needs update for LangGraph architecture

### 2.1 Supervisor Routing Test

**File**: `test_langgraph_workflow.py::test_supervisor_routing()`

Validates:

- Supervisor analyzes task description
- Routes to correct specialist agent
- Sets requires_approval flag for high-risk tasks
- Updates workflow state correctly

**Test Cases**:

| Task Description                      | Expected Route | Requires Approval       |
| ------------------------------------- | -------------- | ----------------------- |
| "Implement OAuth2 authentication"     | feature-dev    | Yes (production code)   |
| "Review PR-42 for security issues"    | code-review    | No (read-only)          |
| "Deploy to production"                | infrastructure | Yes (production change) |
| "Update CI pipeline to run E2E tests" | cicd           | No (pipeline config)    |
| "Generate API documentation"          | documentation  | No (docs only)          |

**Run Command**:

```bash
pytest test_langgraph_workflow.py::test_supervisor_routing -v
```

---

### 2.2 Agent Handoff Test

**New Test Required**: `support/tests/workflows/test_agent_handoff.py`

Validates:

- Feature-dev completes implementation → code-review agent receives PR context
- Code-review approves → cicd agent triggers tests
- CI/CD passes tests → infrastructure agent deploys
- Documentation agent updates docs after deployment

**Workflow**:

```
supervisor → feature-dev (implement)
  ↓ (state: code_url, pr_number)
code-review (analyze)
  ↓ (state: review_result, approval_status)
cicd (run tests)
  ↓ (state: test_results, coverage)
infrastructure (deploy)
  ↓ (state: deployment_url, version)
documentation (update docs)
  ↓ (state: docs_url)
END
```

**Key Validations**:

- State carries forward correctly between agents
- Each agent receives necessary context from previous agent
- Messages array accumulates all agent outputs
- Final state contains complete workflow history

---

### 2.3 Parallel Execution Test

**File**: `support/tests/workflows/test_multi_agent_workflows.py::TestParallelDocsWorkflow::test_parallel_docs_workflow()`

Validates:

- Supervisor can route to multiple agents simultaneously
- Parallel tasks execute concurrently (not sequentially)
- Results aggregated correctly
- No race conditions in shared state

**Test Scenario**: Generate 3 documentation types in parallel

- API reference docs
- User guide
- Deployment guide

**Expected Behavior**:

- Total execution time < 1s (not 3s)
- All 3 docs generated successfully
- No state corruption
- Memory correctly tracks all parallel operations

**Current Status**: ✅ Exists, needs adaptation for LangGraph

---

### 2.4 MCP Tool Discovery Test

**New Test Required**: `support/tests/integration/test_mcp_gateway.py`

Validates:

- MCP gateway reachable at `http://gateway-mcp:8000`
- All 17 servers discoverable
- 150+ tools enumerated correctly
- Progressive tool loader filters correctly

**Test Steps**:

1. Query gateway `/mcp/servers` endpoint
2. Verify 17 servers returned (see `mcp-agent-tool-mapping.yaml`)
3. Query `/mcp/tools` for each server
4. Validate tool counts match manifest
5. Test progressive loader with sample task:
   - "Deploy to production" → should load: dockerhub, rust-mcp-filesystem, gitmcp, prometheus
   - "Write README.md" → should load: rust-mcp-filesystem, context7, notion

**Expected Tool Counts** (from manifest):

```yaml
context7: 2
dockerhub: 13
fetch: 1
gitmcp: 5
gmail-mcp: 3
google-maps: 8
hugging-face: 9
memory: 9
next-devtools: 5
notion: 19
perplexity: 3
playwright: 21
rust-mcp-filesystem: 24
sequentialthinking: 1
stripe: 22
time: 2
youtube_transcript: 3
```

---

## Phase 3: Workflow End-to-End Tests

**Location**: `support/tests/e2e/`  
**Duration**: 20-30 minutes  
**Status**: 🆕 New test suite required

### 3.1 Feature Development Workflow (High-Risk)

**New Test**: `support/tests/e2e/test_feature_workflow.py`

**Scenario**: "Add JWT authentication middleware to API"

**Expected Flow**:

```
1. POST /orchestrate/langgraph {"task": "Add JWT authentication..."}
2. Supervisor analyzes → routes to feature-dev
3. Feature-dev:
   - Reads existing auth code (rust-mcp-filesystem)
   - Generates JWT middleware (hugging-face code generation)
   - Creates feature branch (gitmcp create_branch)
   - Writes implementation files (rust-mcp-filesystem write_file)
   - Commits changes (gitmcp commit_changes)
   - Opens draft PR (gitmcp create_pull_request)
4. Risk Assessment: HIGH (production code change)
5. Approval Node:
   - Creates Linear sub-issue under DEV-68
   - Returns: {"approval_issue": "DEV-133", "status": "pending"}
   - Workflow INTERRUPTS (LangGraph __interrupt__)
6. Manual Approval: Change Linear issue status to "Done"
7. Resume: POST /orchestrate/langgraph/resume {"thread_id": "...", "checkpoint_id": "..."}
8. Workflow continues → code-review agent analyzes PR
9. END: Final state includes PR URL, approval details, review summary
```

**Validations**:

- ✅ Feature branch created in git
- ✅ Implementation files written with correct structure
- ✅ PR created with descriptive title/body
- ✅ Linear sub-issue created with 🟠 emoji (high risk)
- ✅ Workflow interrupts at approval gate
- ✅ PostgreSQL checkpoint persisted
- ✅ Workflow resumes after approval
- ✅ LangSmith trace shows complete workflow

**Mock Points** (for faster testing):

- Hugging-face code generation → pre-generated template
- Linear API → mock server returning DEV-133
- Git operations → local test repo (not main)

---

### 3.2 PR Review Workflow (Low-Risk)

**New Test**: `support/tests/e2e/test_review_workflow.py`

**Scenario**: "Review PR-85 for code quality"

**Expected Flow**:

```
1. POST /orchestrate/langgraph {"task": "Review PR-85 for code quality"}
2. Supervisor → code-review agent
3. Code-review:
   - Fetches PR-85 diff (gitmcp get_diff)
   - Reads modified files (rust-mcp-filesystem read_file)
   - Analyzes code patterns (hugging-face analyze_code)
   - Checks against standards (context7 search_docs)
   - Posts review comments (gitmcp add_comment)
4. Risk Assessment: LOW (read-only operation)
5. Auto-Approve: No HITL required
6. END: {"review_comments": [...], "issues_found": 2, "severity": "low"}
```

**Validations**:

- ✅ PR-85 diff fetched correctly
- ✅ All modified files analyzed
- ✅ Review comments posted to PR
- ✅ No approval request created (low risk)
- ✅ Workflow completes without interruption
- ✅ Execution time < 30s

---

### 3.3 Deployment Workflow (Critical-Risk)

**New Test**: `support/tests/e2e/test_deploy_workflow.py`

**Scenario**: "Deploy feature/jwt-auth branch to production"

**Expected Flow**:

```
1. POST /orchestrate/langgraph {"task": "Deploy feature/jwt-auth to production"}
2. Supervisor → infrastructure agent
3. Infrastructure:
   - Pulls latest code (gitmcp)
   - Builds Docker image (dockerhub)
   - Generates docker-compose.yml update (rust-mcp-filesystem)
   - Validates deployment config (context7)
4. Risk Assessment: CRITICAL (production deployment)
5. Approval Node:
   - Creates Linear sub-issue: "🔴 [CRITICAL] HITL Approval: Deploy feature/jwt-auth to production"
   - Includes: deployment plan, rollback procedure, estimated downtime
   - Workflow INTERRUPTS
6. Manual Approval Required: Tech Lead or DevOps Engineer
7. Resume after approval
8. Infrastructure completes deployment:
   - Runs docker-compose up (dockerhub run_container)
   - Validates health endpoints (prometheus query_metrics)
   - Updates deployment log (notion create_page)
   - Sends notification (gmail-mcp send_email)
9. END: {"deployment_status": "success", "version": "jwt-auth-v1", "url": "https://prod.example.com"}
```

**Validations**:

- ✅ Linear sub-issue created with 🔴 emoji (critical risk)
- ✅ Approval includes detailed deployment plan
- ✅ Workflow interrupts before deployment
- ✅ Only authorized roles can approve
- ✅ Deployment executes after approval
- ✅ Health checks validate deployment
- ✅ Prometheus metrics show no errors
- ✅ Notification sent to stakeholders
- ✅ Complete audit trail in Linear + LangSmith

---

### 3.4 Self-Healing Workflow (Retry Logic)

**File**: `support/tests/workflows/test_multi_agent_workflows.py::TestSelfHealingWorkflow::test_self_healing_workflow()`

**Scenario**: Service health check detects issue → diagnose → fix → verify

**Expected Flow**:

```
Loop (max 3 attempts):
1. Infrastructure agent runs health check (dockerhub inspect_container)
2. If issue detected:
   - Code-review agent diagnoses root cause (analyze logs)
   - Infrastructure agent applies fix (restart service)
   - Re-run health check
3. If resolved: EXIT
4. If max retries reached: ESCALATE to HITL
```

**Validations**:

- ✅ Detects simulated service failure
- ✅ Diagnoses correct root cause
- ✅ Applies appropriate fix
- ✅ Verifies resolution
- ✅ Exits on success (not max retries)
- ✅ Escalates if unresolved after 3 attempts

**Current Status**: ✅ Test exists, needs LangGraph adaptation

---

## Phase 4: Memory & Context Tests

**Location**: `support/tests/integration/test_memory.py`  
**Duration**: 5-10 minutes  
**Status**: 🆕 New test suite required

### 4.1 PostgreSQL Checkpointing Test

**New Test**: `support/tests/integration/test_postgres_checkpointing.py`

Validates:

- Workflow state persisted at each node transition
- Checkpoint IDs generated correctly
- State retrievable by thread_id + checkpoint_id
- Optimistic locking prevents conflicts

**Test Steps**:

1. Start workflow with unique thread_id
2. Execute 3 nodes (supervisor → feature-dev → code-review)
3. Query database for checkpoints:
   ```sql
   SELECT * FROM langgraph_checkpoints WHERE thread_id = ?
   ```
4. Verify 3 checkpoints exist
5. Retrieve checkpoint 2 and verify state matches expected
6. Test concurrent update (optimistic locking):
   - Thread A updates checkpoint N
   - Thread B tries to update checkpoint N with old version
   - B fails with version conflict error

**Schema** (from `shared/services/langgraph/postgres_checkpointer.py`):

```sql
CREATE TABLE langgraph_checkpoints (
    thread_id TEXT,
    checkpoint_id TEXT,
    parent_checkpoint_id TEXT,
    state JSONB,
    metadata JSONB,
    created_at TIMESTAMP,
    version INTEGER,
    PRIMARY KEY (thread_id, checkpoint_id)
);
```

---

### 4.2 Qdrant Vector Memory Test

**New Test**: `support/tests/integration/test_qdrant_memory.py`

Validates:

- Agent observations embedded and stored
- Semantic search retrieves relevant context
- Memory persists across workflow invocations
- Collections properly namespaced by agent

**Test Steps**:

1. Feature-dev agent completes task: "Add OAuth2 middleware"
2. Store observation in Qdrant:
   ```python
   memory.add_observation(
       agent_name="feature-dev",
       observation="Implemented OAuth2 middleware using jwt-python library. Added token validation to /api/* routes.",
       metadata={"task_id": "task-123", "timestamp": "..."}
   )
   ```
3. Query memory with semantic search:
   ```python
   results = memory.search(
       query="How did we implement authentication?",
       agent_name="feature-dev",
       top_k=3
   )
   ```
4. Verify OAuth2 observation returned in top results
5. Check Qdrant collection: `devtools-feature-dev`
6. Verify vector dimensions match embedding model (e.g., 768 for sentence-transformers)

**Expected Qdrant Collections**:

- `devtools-supervisor`
- `devtools-feature-dev`
- `devtools-code-review`
- `devtools-infrastructure`
- `devtools-cicd`
- `devtools-documentation`

---

### 4.3 Hybrid Memory System Test

**New Test**: `support/tests/integration/test_hybrid_memory.py`

Validates:

- Buffer memory tracks recent conversation (last 10 messages)
- Vector memory provides long-term context retrieval
- Hybrid query combines both sources
- Memory correctly prioritizes recent + relevant context

**Test Scenario**:

1. Execute 15 tasks (exceeds buffer size of 10)
2. Query: "What was the last deployment we did?"
   - Buffer memory: Returns most recent deployment (task 15)
3. Query: "Have we ever implemented OAuth before?"
   - Vector memory: Returns task 5 (OAuth implementation from history)
4. Query: "Show me recent authentication work"
   - Hybrid: Returns task 15 (recent) + task 5 (relevant historical context)

**Validation Criteria**:

- Buffer memory limited to 10 most recent tasks
- Vector memory retrieves from full history
- Hybrid query returns combined results (deduplicated)
- Context window stays within LLM limits (8K tokens)

---

## Phase 5: HITL Workflow Tests

**Location**: `support/tests/hitl/test_hitl_workflow.py`  
**Duration**: 10-15 minutes  
**Status**: ✅ Exists, needs Linear integration tests

### 5.1 Risk Assessment Test

**File**: `support/tests/hitl/test_hitl_workflow.py::TestRiskAssessor`

Validates:

- Production delete operations → CRITICAL risk
- Dev environment reads → LOW risk
- Security findings → elevate to HIGH risk
- Sensitive data operations → CRITICAL risk

**Current Tests** (all passing):

- ✅ `test_critical_production_delete()`
- ✅ `test_low_dev_read()`
- ✅ `test_high_security_findings()`
- ✅ `test_critical_sensitive_data_export()`
- ✅ `test_auto_approve_low_risk()`
- ✅ `test_timeout_scaling()`

**Run Command**:

```bash
pytest support/tests/hitl/test_hitl_workflow.py::TestRiskAssessor -v
```

---

### 5.2 Approval Request Creation Test

**File**: `support/tests/hitl/test_hitl_workflow.py::TestHITLManager::test_create_approval_request()`

Validates:

- High-risk tasks create approval requests
- Low-risk tasks auto-approve (no request)
- Request stored in PostgreSQL
- Timeout set based on risk level

**Current Tests**:

- ✅ `test_create_approval_request()` - High-risk creates request
- ✅ `test_auto_approve_low_risk()` - Low-risk skips request

---

### 5.3 Linear Sub-Issue Creation Test (NEW)

**New Test**: `support/tests/hitl/test_linear_integration.py`

Validates:

- Linear sub-issue created under DEV-68
- Template populated correctly (HITL_ORCHESTRATOR_TEMPLATE_UUID)
- Risk emoji included in title (🔴 🟠 🟡 🟢)
- All metadata fields set:
  - agent_name
  - task_id (approval_id)
  - context_description
  - reasoning
  - metadata (timestamp, workflow_id)
  - deadline
  - estimated_tokens

**Test Steps**:

1. Mock Linear GraphQL API
2. Call `linear_client.create_approval_subissue(...)`
3. Verify GraphQL mutation:
   ```graphql
   mutation {
     issueCreate(input: {
       teamId: "f5b610be-ac34-4983-918b-2c9d00aa9b7a"
       parentId: "4a4f7007-1a76-4b7f-af77-9723267b6d48"  # DEV-68 UUID
       title: "🟠 [HIGH] HITL Approval: Deploy to production"
       templateId: "8881211a-7b9c-42ab-a178-608ddf1f6665"  # HITL template
       customFields: { ... }
     }) {
       issue { identifier }
     }
   }
   ```
4. Verify returned identifier format: `DEV-###`
5. Query Linear API to confirm sub-issue exists under DEV-68

**Run Command**:

```bash
$env:LINEAR_API_KEY="lin_oauth_..."; python -m pytest support/tests/hitl/test_linear_integration.py -v
```

---

### 5.4 Workflow Interrupt/Resume Test

**File**: `support/tests/hitl/test_hitl_workflow.py::TestWorkflowIntegration`

Validates:

- LangGraph workflow interrupts at approval gate
- PostgreSQL checkpoint persisted
- Workflow resumes from checkpoint after approval
- State preserved across interrupt/resume

**Test Flow**:

```python
# Initial invocation (should interrupt)
result = await workflow.ainvoke(
    {"task": "Deploy to production"},
    config={"configurable": {"thread_id": "test-123"}}
)
assert result["approval_status"] == "pending"
assert result["approval_request_id"] is not None

# Simulate approval
await hitl_manager.approve_request(
    request_id=result["approval_request_id"],
    approver_id="tech.lead",
    approver_role="tech_lead"
)

# Resume workflow
resumed_result = await workflow.ainvoke(
    None,  # No new input
    config={"configurable": {"thread_id": "test-123"}}
)
assert resumed_result["approval_status"] == "approved"
assert resumed_result["deployment_status"] == "success"
```

**Current Status**: ⚠️ Partially implemented, needs completion

---

## Phase 6: Production Validation

**Location**: Manual testing on droplet (45.55.173.72)  
**Duration**: 30-45 minutes  
**Status**: 🆕 Manual test checklist

### 6.1 Full Feature Workflow (Real LLM + Linear)

**Execute on Production**:

```bash
# SSH to droplet
ssh root@45.55.173.72

# Submit real task
curl -X POST http://localhost:8001/orchestrate/langgraph \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Add rate limiting middleware to /api/auth endpoints",
    "context": "Implement token bucket algorithm with Redis backend. Limit: 10 requests/minute per IP."
  }'
```

**Expected Response**:

```json
{
  "workflow_id": "wf-20251121-...",
  "thread_id": "thread-...",
  "status": "pending_approval",
  "approval_issue": "DEV-134",
  "next_steps": "Approve DEV-134 in Linear to continue"
}
```

**Manual Validation Steps**:

1. ✅ Check LangSmith trace: Verify supervisor → feature-dev routing
2. ✅ Verify MCP tool calls in trace:
   - `rust-mcp-filesystem:read_file` (read existing auth code)
   - `hugging-face:generate_code` (generate rate limiter)
   - `gitmcp:create_branch` (create feature branch)
   - `rust-mcp-filesystem:write_file` (write implementation)
   - `gitmcp:commit_changes` (commit code)
3. ✅ Check Linear: DEV-134 exists under DEV-68 with 🟠 emoji
4. ✅ Check PostgreSQL: Verify checkpoint stored
   ```sql
   SELECT * FROM langgraph_checkpoints WHERE thread_id = 'thread-...' ORDER BY created_at DESC;
   ```
5. ✅ Approve in Linear: Change status to "Done"
6. ✅ Resume workflow:
   ```bash
   curl -X POST http://localhost:8001/orchestrate/langgraph/resume \
     -H "Content-Type: application/json" \
     -d '{"thread_id": "thread-...", "checkpoint_id": "checkpoint-..."}'
   ```
7. ✅ Verify completion in LangSmith trace
8. ✅ Check Prometheus metrics:
   - `langgraph_workflow_duration_seconds`
   - `langgraph_approval_wait_time_seconds`
   - `mcp_tool_call_total` (should show filesystem, git, hugging-face calls)
9. ✅ Check Qdrant: Verify observation stored
   ```bash
   curl http://localhost:6333/collections/devtools-feature-dev/points/count
   ```

---

### 6.2 Low-Risk Task (No Approval)

**Execute**:

```bash
curl -X POST http://localhost:8001/orchestrate/langgraph \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Generate API documentation for /api/auth endpoints",
    "context": "Use existing OpenAPI spec from code comments"
  }'
```

**Expected Response**:

```json
{
  "workflow_id": "wf-20251121-...",
  "status": "completed",
  "result": {
    "docs_url": "docs/api/auth.md",
    "pages_generated": 3
  }
}
```

**Validation**:

- ✅ No approval issue created (low risk)
- ✅ Workflow completes in <30s
- ✅ Documentation files created
- ✅ LangSmith trace shows: supervisor → documentation
- ✅ No workflow interruption

---

### 6.3 Multi-Agent Handoff (Code Review)

**Execute**:

```bash
curl -X POST http://localhost:8001/orchestrate/langgraph \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Review PR-85 for security vulnerabilities and code quality",
    "context": "Focus on authentication logic and input validation"
  }'
```

**Expected Flow**:

```
supervisor → code-review
```

**Validation**:

- ✅ LangSmith trace shows single agent execution
- ✅ MCP tools called:
  - `gitmcp:get_pull_request` (fetch PR-85)
  - `gitmcp:get_diff` (get changes)
  - `rust-mcp-filesystem:read_file` (read modified files)
  - `hugging-face:analyze_code` (security analysis)
  - `gitmcp:add_comment` (post review comments)
- ✅ Review comments posted to PR-85
- ✅ Response includes: `{"issues_found": 2, "severity": "medium"}`

---

### 6.4 Observability Validation

**Check LangSmith Dashboard**:

1. Navigate to: https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects/p/f967bb5e-2e61-434f-8ee1-0df8c22bc046
2. Filter traces by: `tags: "production"`
3. Verify trace includes:
   - All agent node executions
   - Tool calls with parameters
   - Approval node interrupt
   - Workflow resume
   - Total token usage
   - Latency per node

**Check Prometheus Metrics**:

```bash
ssh root@45.55.173.72
curl http://localhost:9090/api/v1/query?query=langgraph_workflow_total
curl http://localhost:9090/api/v1/query?query=mcp_tool_call_total
curl http://localhost:9090/api/v1/query?query=agent_node_duration_seconds
```

**Expected Metrics**:

- `langgraph_workflow_total{status="completed"}` > 0
- `langgraph_workflow_total{status="pending_approval"}` > 0
- `mcp_tool_call_total{server="gitmcp"}` > 0
- `agent_node_duration_seconds{agent="feature-dev"}` histogram populated

---

## Phase 7: Stress & Performance Tests

**Location**: `support/tests/performance/`  
**Duration**: 1-2 hours  
**Status**: 🆕 New test suite required

### 7.1 Concurrent Workflow Test

**New Test**: `support/tests/performance/test_concurrent_workflows.py`

Validates:

- 10 concurrent workflows execute without conflicts
- PostgreSQL checkpointing handles concurrency
- Resource locks prevent race conditions
- No memory leaks or connection pool exhaustion

**Test Scenario**:

```python
tasks = [
    "Implement feature A",
    "Review PR-1",
    "Deploy service B",
    "Generate docs for module C",
    # ... 6 more tasks
]

# Execute all 10 in parallel
results = await asyncio.gather(*[
    workflow.ainvoke({"task": task}, config={"configurable": {"thread_id": f"t-{i}"}})
    for i, task in enumerate(tasks)
])

# Verify all completed or pending_approval
assert all(r["status"] in ["completed", "pending_approval"] for r in results)
```

**Validation**:

- ✅ All 10 workflows complete within 2 minutes
- ✅ No database deadlocks
- ✅ No duplicate checkpoint IDs
- ✅ Memory usage < 2GB
- ✅ Prometheus shows 10 separate workflow traces

---

### 7.2 Large Context Test

**New Test**: `support/tests/performance/test_large_context.py`

Validates:

- Workflow handles large codebases (10K+ files)
- Vector memory efficiently retrieves relevant context
- Token limits respected (8K context window)
- Progressive tool disclosure reduces token overhead

**Test Scenario**:

```python
task = {
    "task": "Refactor authentication module",
    "context": {
        "repo_files": 12000,  # Large codebase
        "relevant_files": ["auth.py", "middleware.py", "utils/jwt.py"],
        "dependencies": ["jwt-python", "bcrypt", "redis"]
    }
}
```

**Validation**:

- ✅ Only relevant files loaded (not all 12K)
- ✅ Token usage < 8K per agent call
- ✅ Progressive loader uses MINIMAL strategy (10-30 tools, not 150)
- ✅ Execution time < 60s

---

### 7.3 Memory Persistence Test

**New Test**: `support/tests/performance/test_memory_persistence.py`

Validates:

- Workflow state persists across service restarts
- Vector memory survives Qdrant restart
- Checkpoints recoverable after PostgreSQL restart
- No data loss on crash

**Test Steps**:

1. Start workflow with thread_id="persistence-test"
2. Execute 3 nodes (supervisor → feature-dev → approval)
3. Restart orchestrator service:
   ```bash
   docker compose restart orchestrator
   ```
4. Resume workflow:
   ```python
   result = await workflow.ainvoke(
       None,
       config={"configurable": {"thread_id": "persistence-test"}}
   )
   ```
5. Verify state matches pre-restart
6. Repeat with PostgreSQL restart
7. Repeat with Qdrant restart

**Validation**:

- ✅ Workflow resumes correctly after each restart
- ✅ No state corruption
- ✅ All checkpoints intact
- ✅ Vector memory queries return same results

---

## Test Execution Guide

### Prerequisites

**Local Development**:

```powershell
# Install dependencies
pip install -r agent_orchestrator/requirements.txt
pip install -r support/tests/requirements.txt

# Set environment variables
$env:GRADIENT_API_KEY="gk_..."
$env:LINEAR_API_KEY="lin_oauth_..."
$env:DATABASE_URL="postgresql://postgres:devtools@localhost:5432/devtools"
$env:QDRANT_URL="http://localhost:6333"

# Start services
cd deploy
docker compose up -d postgres redis qdrant gateway-mcp
```

**Production Droplet**:

```bash
ssh root@45.55.173.72
cd /opt/Dev-Tools
# Services already running
docker compose ps
```

---

### Running Tests

**Phase 1: Unit Tests** (5 minutes):

```powershell
# All unit tests
python test_langgraph_workflow.py

# Specific test
python test_langgraph_workflow.py -k test_agent_initialization
```

**Phase 2: Integration Tests** (15 minutes):

```powershell
pytest support/tests/workflows/test_multi_agent_workflows.py -v -s

# Specific workflow
pytest support/tests/workflows/test_multi_agent_workflows.py::TestPRDeploymentWorkflow -v
```

**Phase 3: E2E Tests** (30 minutes):

```powershell
# Feature workflow (requires real LLM)
pytest support/tests/e2e/test_feature_workflow.py -v -s

# Review workflow
pytest support/tests/e2e/test_review_workflow.py -v -s

# Deployment workflow (requires approval)
pytest support/tests/e2e/test_deploy_workflow.py -v -s
```

**Phase 4: Memory Tests** (10 minutes):

```powershell
pytest support/tests/integration/test_postgres_checkpointing.py -v
pytest support/tests/integration/test_qdrant_memory.py -v
pytest support/tests/integration/test_hybrid_memory.py -v
```

**Phase 5: HITL Tests** (15 minutes):

```powershell
pytest support/tests/hitl/test_hitl_workflow.py -v
pytest support/tests/hitl/test_linear_integration.py -v
```

**Phase 6: Production Validation** (45 minutes):

```bash
# Execute manual test checklist (see Section 6.1-6.4)
# Use curl commands against droplet
ssh root@45.55.173.72
# Follow validation steps
```

**Phase 7: Performance Tests** (2 hours):

```powershell
pytest support/tests/performance/ -v -s --timeout=7200
```

---

### Test Report Format

**Generate HTML Report**:

```powershell
pytest --html=support/reports/test_report.html --self-contained-html
```

**Coverage Report**:

```powershell
pytest --cov=agent_orchestrator --cov=shared/lib --cov-report=html
```

**Expected Coverage Targets**:

- Agent modules: >80%
- Shared libraries: >70%
- Integration tests: >60%
- E2E tests: >40% (focus on critical paths)

---

## Success Criteria

### Phase 1: Unit Tests

- [x] All 6 agents initialize successfully
- [x] Tool binding configured per agent
- [x] LangGraph app compiles without errors
- [x] Supervisor routes correctly

### Phase 2: Integration Tests

- [ ] Agent handoffs preserve state
- [ ] Parallel execution works correctly
- [ ] MCP gateway returns 17 servers
- [ ] Progressive loader reduces token usage by 80%

### Phase 3: E2E Workflows

- [ ] Feature workflow executes end-to-end
- [ ] High-risk tasks trigger HITL approval
- [ ] Low-risk tasks auto-approve
- [ ] Deployment workflow completes successfully

### Phase 4: Memory & Context

- [ ] PostgreSQL checkpointing works
- [ ] Qdrant vector search retrieves context
- [ ] Hybrid memory combines buffer + vector
- [ ] Optimistic locking prevents conflicts

### Phase 5: HITL Workflows

- [ ] Risk assessment categorizes correctly
- [ ] Linear sub-issues created under DEV-68
- [ ] Workflow interrupts at approval gate
- [ ] Workflow resumes after approval

### Phase 6: Production Validation

- [ ] Real LLM calls execute successfully
- [ ] Actual Linear API creates issues
- [ ] MCP tools called correctly
- [ ] LangSmith traces captured
- [ ] Prometheus metrics recorded

### Phase 7: Performance

- [ ] 10 concurrent workflows execute without errors
- [ ] Large context handled efficiently
- [ ] Memory persists across restarts
- [ ] No memory leaks or resource exhaustion

---

## Known Issues & Mitigations

### Issue 1: MCP Server Connection Failures

**Symptom**: Some MCP servers unreachable (e.g., prometheus)  
**Impact**: Reduced tool availability for agents  
**Mitigation**: Agents should gracefully degrade; log warning but continue  
**Test**: `test_mcp_gateway_resilience.py` - verify agents handle missing tools

### Issue 2: Linear API Rate Limits

**Symptom**: 429 errors during bulk testing  
**Impact**: HITL workflow tests may fail  
**Mitigation**: Use mock Linear server for integration tests; only test real API in Phase 6  
**Test**: Rate limit backoff in `linear_workspace_client.py`

### Issue 3: Gradient AI Latency

**Symptom**: LLM calls take 5-10s on 70B model  
**Impact**: E2E tests slow  
**Mitigation**: Use smaller models (8B/13B) for non-critical tests; mock LLM for unit tests  
**Test**: `test_gradient_fallback.py` - verify smaller models work

### Issue 4: PostgreSQL Connection Pool Exhaustion

**Symptom**: `connection pool exhausted` error under load  
**Impact**: Concurrent workflow tests fail  
**Mitigation**: Increase pool size in `docker-compose.yml` (default: 20 → 50)  
**Test**: `test_concurrent_workflows.py` with 50 parallel tasks

---

## Next Steps

### Immediate (Week 1)

1. **Create E2E test suite** (`support/tests/e2e/`)

   - `test_feature_workflow.py`
   - `test_review_workflow.py`
   - `test_deploy_workflow.py`

2. **Add Linear integration tests** (`support/tests/hitl/test_linear_integration.py`)

   - Mock GraphQL API
   - Validate sub-issue creation
   - Test approval resolution

3. **Update multi-agent tests** for LangGraph architecture
   - Adapt `test_multi_agent_workflows.py` to use LangGraph app
   - Replace event bus patterns with LangGraph state

### Short-term (Week 2-3)

4. **Memory tests** (`support/tests/integration/`)

   - PostgreSQL checkpointing
   - Qdrant vector memory
   - Hybrid memory system

5. **MCP gateway tests** (`support/tests/integration/test_mcp_gateway.py`)

   - Server discovery
   - Tool enumeration
   - Progressive loader validation

6. **Performance tests** (`support/tests/performance/`)
   - Concurrent workflows
   - Large context handling
   - Memory persistence

### Long-term (Week 4+)

7. **CI/CD integration**

   - Add tests to GitHub Actions workflow
   - Nightly E2E tests against droplet
   - Coverage reporting to PR comments

8. **Chaos testing** (`support/tests/chaos/`)

   - Service restart scenarios
   - Network partitions
   - Database failures
   - Timeout handling

9. **Documentation**
   - Test result dashboards
   - Performance benchmarks
   - Known issues registry

---

## References

- **LangSmith Trace**: https://smith.langchain.com/public/6c4fb824-4ba6-4d73-a4c9-7779283b63a5/r
- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/
- **MCP Gateway**: `shared/gateway/README.md`
- **Agent Endpoints**: `support/docs/AGENT_ENDPOINTS.md`
- **Linear API**: https://developers.linear.app/docs/graphql/working-with-the-graphql-api
- **Deployment Guide**: `support/docs/DEPLOYMENT_GUIDE.md`

---

**Document Version**: 1.0.0  
**Last Updated**: November 21, 2025  
**Maintainer**: Dev-Tools Testing Team  
**Review Schedule**: Weekly during active development
