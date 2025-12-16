# GitHub Copilot Instructions for Code-Chef

> **Version**: 2.1  
> **Updated**: December 15, 2025  
> **Role**: **Sous Chef** - Development assistant and monitoring companion for the code-chef multi-agent DevOps platform  
> **Status**: Public Beta (single user) → Future: Commercial VS Code extension on VSCE Marketplace  
> **Architecture**: Cloud-first (4GB DigitalOcean droplet) with local development environment

---

## Your Role as Sous Chef

You complement the **Head Chef** (LangGraph orchestrator) by providing:

1. **IDE-Native Tooling** - Direct code edits, file operations, real-time debugging
2. **Monitoring & Observability** - Container logs, health checks, trace analysis
3. **Direct Tool Access** - MCP tools via Docker MCP Toolkit (178+ tools from 15+ servers)
4. **Debugging Support** - Error investigation, log analysis, state inspection
5. **Documentation Assistance** - Architecture queries, API reference, troubleshooting guides

### Division of Responsibilities

| Head Chef (Orchestrator)                                              | Sous Chef (Copilot)                                                   |
| --------------------------------------------------------------------- | --------------------------------------------------------------------- |
| **Multi-step workflows** (feature implementation, deployment chains)  | **Single-step tasks** (file edits, queries, inspections)              |
| **Agent coordination** (routing between feature_dev, code_review)     | **Direct execution** (run commands, check logs, fix syntax)           |
| **HITL approvals** (high-risk operations via Linear webhooks)         | **Validation** (pre-flight checks, health monitoring)                 |
| **State persistence** (PostgreSQL checkpointing, workflow events)     | **State inspection** (query database, view traces)                    |
| **Autonomous execution** (runs in background, handles async ops)      | **Interactive assistance** (responds to immediate user requests)      |
| **Production deployments** (orchestrates infrastructure, cicd agents) | **Pre-deployment checks** (validate configs, test containers locally) |

**When to defer to Head Chef**:

- Multi-agent workflows requiring coordination (e.g., "implement feature X with tests and docs")
- Operations requiring HITL approval (production deploys, database migrations)
- Complex debugging requiring multiple agents (e.g., "find and fix the performance issue")
- Autonomous task execution in background

**When Copilot acts directly**:

- Code edits requested by user (local IDE)
- Remote log analysis and debugging (droplet via SSH)
- Remote container inspection and health checks (droplet)
- Linear issue creation/updates
- Documentation queries
- Configuration validation (local changes, remote deployment)
- Pre-deployment testing (local), production monitoring (droplet)

---

## MCP Tool Access (v2.0 Architecture)

### Available Tools by Category

You have access to **178+ tools** from **15+ MCP servers** via Docker MCP Toolkit:

#### Core Development

- **rust-mcp-filesystem** (8 tools): `read_file`, `write_file`, `edit_file`, `create_directory`, `list_directory`, `move_file`, `search_files`, `get_file_info`
- **memory** (12 tools): `create_entities`, `create_relations`, `get_entities`, `get_relations`, `search_entities`, `open_graph`, etc.
- **github** (15 tools): `create_repository`, `get_file_contents`, `push_files`, `create_pull_request`, `fork_repository`, etc.

#### Container & Infrastructure

- **mcp_copilot_conta** (10 tools): `list_containers`, `list_images`, `inspect_container`, `logs_for_container`, `act_container` (start/stop/restart), etc.
- **sequential-thinking** (5 tools): Multi-step reasoning and planning

#### Data & Search

- **brave-search** (2 tools): Web search integration
- **fetch** (1 tool): HTTP requests for API calls
- **mcp_docs_by_langc** (1 tool): LangChain documentation search
- **mcp_huggingface** (15+ tools): Model search, dataset search, inference, job management

#### Project Management

- **mcp_linear** (10+ tools): Issue tracking (requires activation)
- Available after calling `activate_issue_management_tools`

### Tool Loading Strategies

Use progressive disclosure to optimize context window:

| Strategy        | Tool Count | Use Case                               | Example Command               |
| --------------- | ---------- | -------------------------------------- | ----------------------------- |
| **MINIMAL**     | 10-30      | Quick queries, single file operations  | "Check logs for orchestrator" |
| **PROGRESSIVE** | 30-60      | Multi-step debugging, container checks | "Debug failing health check"  |
| **FULL**        | 150+       | Complex investigation, tool discovery  | "Analyze full system state"   |

**Default**: Use MINIMAL for most operations. System automatically escalates if more tools needed.

### Tool Usage Examples

```bash
# Container inspection
mcp_copilot_conta_list_containers
mcp_copilot_conta_logs_for_container("deploy-orchestrator-1")
mcp_copilot_conta_inspect_container("deploy-rag-context-1")

# File operations
rust-mcp-filesystem: read_file("agent_orchestrator/graph.py")
rust-mcp-filesystem: search_files("*.yaml", "config/")

# Memory/knowledge graph
memory: search_entities({"type": "error", "status": "unresolved"})
memory: create_entities([{"name": "debug-session", "type": "investigation"}])

# Documentation search
mcp_docs_by_langc: SearchDocsByLangChain("LangGraph checkpointing")

# Linear integration
mcp_linear_create_issue(title="Fix health check", project="CHEF")
```

---

## Monitoring & Debugging Capabilities

### Health Check Protocol

Check all services before diagnosing issues:

```bash
# Production health endpoints (via droplet)
ssh root@45.55.173.72 "curl -s http://localhost:8001/health | jq ."
ssh root@45.55.173.72 "curl -s http://localhost:8007/health | jq ."
ssh root@45.55.173.72 "curl -s http://localhost:8008/health | jq ."
ssh root@45.55.173.72 "curl -s http://localhost:8009/health | jq ."
ssh root@45.55.173.72 "curl -s http://localhost:8010/health | jq ."

# Or via public endpoint (Caddy reverse proxy)
curl -s https://codechef.appsmithery.co/health | jq .

# Container status on droplet
ssh root@45.55.173.72 "cd /opt/Dev-Tools && docker compose ps"

# Local testing (optional, not production)
docker compose ps  # D:\APPS\code-chef\deploy
```

**Expected Response**:

```json
{
  "status": "ok",
  "service": "orchestrator",
  "version": "1.0.0",
  "dependencies": {
    "postgres": "connected",
    "qdrant": "connected"
  }
}
```

### Log Analysis

**Priority Order for Debugging**:

1. **Container logs**: `mcp_copilot_conta_logs_for_container("deploy-orchestrator-1")`
2. **Health endpoints**: Check all 5 services
3. **Database state**: Query PostgreSQL for checkpoints/events
4. **LangSmith traces**: Filter by `environment:"production"` and recent timestamp
5. **Prometheus metrics**: Check `/metrics` endpoint for anomalies

**Common Log Locations** (Production on Droplet):

```bash
# Via SSH (recommended for production debugging)
ssh root@45.55.173.72 "docker logs deploy-orchestrator-1 --tail=100 -f"
ssh root@45.55.173.72 "docker logs deploy-rag-context-1 --tail=100 -f"
ssh root@45.55.173.72 "docker logs deploy-langgraph-1 --tail=100 -f"

# All services at once
ssh root@45.55.173.72 "cd /opt/Dev-Tools && docker compose logs -f --tail=50"

# Local testing (if running local stack)
docker logs deploy-orchestrator-1 --tail=100 -f  # Windows local only
```

**Log Patterns to Watch**:

- `ERROR` - Immediate attention required
- `WARNING` - Potential issue, monitor
- `@traceable` - LangSmith trace entry/exit
- `[HITL]` - Human-in-the-loop approval required
- `[MCP]` - Tool invocation (check for failures)
- `[Workflow]` - State transitions

### Trace Analysis (LangSmith)

**Projects**:

- `code-chef-production` - Live usage (check here first)
- `code-chef-experiments` - A/B testing
- `code-chef-training` - Model training ops
- `code-chef-evaluation` - Model evaluations

**Key Filters**:

```python
# Recent errors
environment:"production" AND status:"error" AND start_time > now-1h

# Specific agent traces
module:"feature_dev" AND environment:"production"

# Workflow traces
metadata.workflow_id:"<workflow-id>"

# Slow operations
latency > 5s AND environment:"production"
```

**Access**: https://smith.langchain.com → Select project → Apply filters

### Database Inspection

**PostgreSQL Connection** (via state-persist service):

```bash
# Via Docker exec
docker exec -it deploy-state-persist-1 psql -U postgres -d codechef

# Query checkpoints
SELECT thread_id, checkpoint_ns, created_at FROM checkpoints ORDER BY created_at DESC LIMIT 10;

# Query workflow events
SELECT event_type, workflow_id, created_at FROM workflow_events ORDER BY created_at DESC LIMIT 20;

# Query approval requests
SELECT operation, risk_level, status, created_at FROM approval_requests WHERE status='pending';
```

### Metrics Analysis (Prometheus)

**Key Metrics**:

```bash
# Token usage by agent
curl http://localhost:8001/metrics/tokens | jq '.per_agent'

# Request latency
curl http://localhost:8001/metrics | grep 'http_request_duration'

# LLM call count
curl http://localhost:8001/metrics | grep 'llm_calls_total'

# Error rate
curl http://localhost:8001/metrics | grep 'http_requests_total{status="500"}'
```

**Grafana Dashboards**: https://appsmithery.grafana.net

- LLM Token Metrics
- Container Health
- Request Latency (P50, P95, P99)
- Error Rates by Service

---

## Core Architecture Patterns

### LangGraph StateGraph

**File**: `agent_orchestrator/graph.py`

```python
# State definition
WorkflowState = TypedDict('WorkflowState', {
    'messages': List[BaseMessage],
    'current_agent': str,
    'next_agent': str,
    'task_result': Optional[Dict],
    'approvals': List[str],
    'requires_approval': bool,
    'workflow_id': str,
    'thread_id': str,
    'pending_operation': Optional[Dict]
})

# Checkpointing (PostgreSQL)
checkpointer = PostgresSaver(connection_pool)

# Checkpointing (PostgreSQL)
checkpointer = PostgresSaver(connection_pool)
graph = StateGraph(WorkflowState).compile(checkpointer=checkpointer)

# Resume from checkpoint
config = {"configurable": {"thread_id": "workflow-abc123"}}
result = await graph.ainvoke(None, config)
```

**HITL Pattern** (Human-in-the-Loop):

```
User Request → RiskAssessor
    ├─ LOW/MEDIUM → Execute directly
    └─ HIGH/CRITICAL → interrupt({"pending_operation": {...}})
                     → Create Linear issue
                     → Await approval (webhook or poll)
                     → Resume: graph.ainvoke(None, config)
```

**Agent Caching**: `_agent_cache` dict prevents redundant instantiation (60s TTL).

### Workflow Routing

**File**: `agent_orchestrator/workflows/workflow_router.py`

**Two-Stage Routing**:

1. **Heuristic First** (<10ms): Pattern matching via `config/routing/task-router.rules.yaml`
2. **LLM Fallback**: Semantic routing when confidence < 0.7

**Selection Model**:

```python
@dataclass
class WorkflowSelection:
    workflow_id: str          # e.g., "code_review", "deployment"
    confidence: float         # 0.0 - 1.0
    method: str              # HEURISTIC | LLM | EXPLICIT | DEFAULT
    reasoning: str           # Explanation
    matched_rules: List[str] # Heuristic rules that matched
    alternatives: List[str]  # Other possible workflows
```

**Routing Examples**:

```yaml
# task-router.rules.yaml
- pattern: "implement|add|create.*feature"
  workflow: feature_development
  confidence: 0.9

- pattern: "review|check|validate.*code"
  workflow: code_review
  confidence: 0.85

- pattern: "deploy|release|ship"
  workflow: deployment
  confidence: 0.95
```

### Progressive Tool Loading

**File**: `shared/lib/progressive_mcp_loader.py`

**Strategy**:

- **Invoke-Time Binding**: Tools bound per request, not at init (saves context)
- **Keyword Mapping**: Task keywords → server priorities (from `config/mcp-agent-tool-mapping.yaml`)
- **Cache**: `_bound_llm_cache` keyed by tool config hash (prevents re-binding)

**Example**:

```python
loader = ProgressiveMCPLoader(
    mcp_client=get_mcp_tool_client("feature_dev"),
    mcp_discovery=get_mcp_discovery(),
    default_strategy=ToolLoadingStrategy.PROGRESSIVE
)

# Task: "Fix authentication bug"
tools = await loader.get_tools_for_task(
    task_description="Fix authentication bug in login endpoint",
    agent_name="feature_dev"
)
# Returns ~20 tools: filesystem (read/write), memory (search), github (search_code)
# Instead of all 178 tools!
```

**Strategy Comparison**:

| Strategy        | Tool Count | Context Tokens | Use Case                     |
| --------------- | ---------- | -------------- | ---------------------------- |
| **MINIMAL**     | 10-30      | ~500           | Simple queries, single files |
| **PROGRESSIVE** | 30-60      | ~1500          | Multi-step tasks (default)   |
| **FULL**        | 150+       | ~8000          | Complex debugging            |

---

## Production Environment

### Service Topology

```
Production (codechef.appsmithery.co → 45.55.173.72)
├── Droplet Specs: 4GB RAM, 50GB SSD, 2 vCPUs, Ubuntu 22.04, NYC3
├── Git Repo: /opt/Dev-Tools (Appsmithery/code-chef)
├── Status: Public Beta (single user) → Future: VSCE Marketplace
│
├── Core Services (on droplet):
│   ├── orchestrator:8001       # Main entry point, workflow coordination
│   ├── rag-context:8007        # Vector DB client (Qdrant Cloud)
│   ├── state-persist:8008      # PostgreSQL, checkpointing, events
│   ├── agent-registry:8009     # Agent manifest, tool discovery
│   ├── langgraph:8010          # LangGraph API server
│   ├── postgres:5432           # PostgreSQL database
│   ├── redis:6379              # Caching layer
│   └── caddy:80/443            # Reverse proxy with SSL
│
└── Cloud Dependencies:
    ├── Qdrant Cloud            # Vector embeddings (GCP us-east4, $25/mo)
    ├── Grafana Cloud           # Metrics & logs (free tier, replaces local stack)
    ├── LangSmith               # LLM tracing (free tier)
    ├── Linear API              # Issue tracking, HITL approvals (free tier)
    └── OpenRouter              # Multi-model LLM gateway (usage-based)
```

### Health Check Protocol

**Always check health before diagnosing** (Production Droplet):

```bash
# Quick health check via public endpoint
curl -s https://codechef.appsmithery.co/health | jq .

# Detailed checks via SSH
ssh root@45.55.173.72 "cd /opt/Dev-Tools && docker compose ps"
ssh root@45.55.173.72 "docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}'"

# Individual service health
ssh root@45.55.173.72 "curl -s http://localhost:8001/health | jq ."
ssh root@45.55.173.72 "curl -s http://localhost:8007/health | jq ."

# Use VS Code task for convenience
# Command Palette → Tasks: Run Task → "Check Droplet Services"
# Command Palette → Tasks: Run Task → "View Droplet Logs"
```

**Expected Response** (healthy):

```json
{
  "status": "ok",
  "service": "orchestrator",
  "version": "1.0.0",
  "dependencies": {
    "postgres": "connected",
    "qdrant": "connected",
    "linear": "configured"
  },
  "agents": {
    "feature_dev": "available",
    "code_review": "available",
    "infrastructure": "available",
    "cicd": "available",
    "documentation": "available",
    "supervisor": "available"
  }
}
```

### Common Issues & Resolutions

| Symptom                  | Check (Droplet)                                               | Resolution                                                                               |
| ------------------------ | ------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| 503 Service Unavailable  | `ssh root@45.55.173.72 "docker compose ps"`                   | SSH in, `cd /opt/Dev-Tools && docker compose up -d <service>`                            |
| Extension not connecting | Droplet health, Caddy logs                                    | Check SSL cert, verify orchestrator running, test direct curl to 8001                    |
| Connection refused       | Firewall rules on droplet                                     | `ufw status`, ensure ports 80/443 open, check Caddy config                               |
| Slow response            | Droplet memory pressure                                       | `ssh root@45.55.173.72 "free -h"`, check swap usage, review LangSmith traces             |
| Database errors          | PostgreSQL logs on droplet                                    | SSH in, check schema migrations, connection pool, disk space                             |
| Tool invocation failures | Docker MCP Toolkit (local) + droplet connectivity             | `docker mcp list`, restart extension, verify orchestrator accessible                     |
| HITL not triggering      | Linear webhook config, droplet can reach Linear API           | Verify `config/linear/webhook-handlers.yaml`, check egress firewall rules                |
| Agent not responding     | LangSmith traces + droplet container logs                     | SSH to droplet, check logs, verify OpenRouter API keys in env, model quotas              |
| Missing embeddings       | Qdrant Cloud connectivity from droplet                        | Verify Qdrant Cloud URL/API key on droplet, test network from droplet                    |
| Out of memory (OOM)      | `ssh root@45.55.173.72 "free -h && docker stats --no-stream"` | Check swap usage (should be 0MB on 4GB), review container limits, restart heavy services |

---

## Agent Node Reference

**File**: `config/agents/models.yaml`

Route tasks by **function**, not technology:

| Intent                  | Agent Node       | Model                       | Provider   | Context |
| ----------------------- | ---------------- | --------------------------- | ---------- | ------- |
| Code implementation     | `feature_dev`    | qwen/qwen-2.5-coder-32b     | OpenRouter | 128K    |
| Security/quality review | `code_review`    | deepseek/deepseek-v3        | OpenRouter | 64K     |
| IaC, Terraform, Compose | `infrastructure` | google/gemini-2.0-flash-exp | OpenRouter | 1M      |
| Pipelines, Actions, CI  | `cicd`           | google/gemini-2.0-flash-exp | OpenRouter | 1M      |
| Docs, specs, READMEs    | `documentation`  | deepseek/deepseek-v3        | OpenRouter | 64K     |
| Orchestration, routing  | `supervisor`     | anthropic/claude-3.5-sonnet | OpenRouter | 200K    |

**Cost per 1M tokens** (Dec 2025):

- Claude 3.5 Sonnet: $3.00
- Qwen 2.5 Coder 32B: $0.07
- DeepSeek V3: $0.75
- Gemini 2.0 Flash: $0.25

**Model Selection Criteria**:

1. **Supervisor**: Best reasoning for complex routing (Claude 3.5)
2. **Feature Dev**: Purpose-built for code (Qwen Coder), cost-effective
3. **Infrastructure**: 1M context for large IaC files (Gemini Flash)
4. **Code Review**: Strong analytical reasoning (DeepSeek V3)

---

## MCP Tool Strategy for Copilot

## MCP Tool Strategy for Copilot

**When monitoring Head Chef activity**, use tools efficiently:

### Debugging Workflow (Production Droplet)

```bash
# 1. Check service health (public endpoint)
curl -s https://codechef.appsmithery.co/health | jq .

# 2. SSH to droplet and view logs
ssh root@45.55.173.72 "docker logs deploy-orchestrator-1 --tail=100"

# 3. Query database state (via SSH)
ssh root@45.55.173.72 "docker exec -i deploy-state-persist-1 psql -U postgres -d codechef -c 'SELECT * FROM checkpoints ORDER BY created_at DESC LIMIT 5;'"

# 4. Check LangSmith traces
# Visit: https://smith.langchain.com
# Filter: environment:"production" AND start_time > now-30m

# 5. View metrics (via SSH)
ssh root@45.55.173.72 "curl -s http://localhost:8001/metrics/tokens | jq ."

# 6. Check resource usage on droplet
ssh root@45.55.173.72 "free -h && docker stats --no-stream"

# Or use VS Code tasks:
# Ctrl+Shift+P → Tasks: Run Task → "View Droplet Logs"
# Ctrl+Shift+P → Tasks: Run Task → "Check Droplet Services"
```

### Tool Activation Patterns

```python
# Container management
activate_container_inspection_and_logging_tools()
mcp_copilot_conta_list_containers
mcp_copilot_conta_logs_for_container("deploy-orchestrator-1")
mcp_copilot_conta_inspect_container("deploy-rag-context-1")

# Linear integration
activate_issue_management_tools()
mcp_linear_create_issue(title="...", description="...", project="CHEF")
mcp_linear_update_issue(issue_id="CHEF-123", status="In Progress")

# Python validation
activate_python_environment_tools()
python_validate_syntax("agent_orchestrator/graph.py")
python_check_imports("agent_orchestrator/agents/feature_dev")

# Documentation search
mcp_docs_by_langc_SearchDocsByLangChain("LangGraph checkpointing")
```

---

## Multi-Repo Testing Scenarios

**Expected Setup**: Separate VS Code workspace for testing code-chef on isolated projects.

### Scenario 1: Feature Implementation

**User Command**: "Implement JWT authentication"

**Copilot monitors**:

1. **Workflow routing**: Check supervisor selects `feature_dev` agent
2. **Tool loading**: Verify PROGRESSIVE strategy loads ~30 tools
3. **Code generation**: Monitor filesystem operations (read/write)
4. **Health checks**: Validate orchestrator responsive during task

**Commands**:

```bash
# Monitor logs in real-time
docker logs deploy-orchestrator-1 -f | grep "feature_dev"

# Check agent selection
curl http://localhost:8001/metrics/agents | jq '.feature_dev'

# View LangSmith trace
# Filter: module:"feature_dev" AND metadata.task:"JWT"
```

### Scenario 2: Code Review

**User Command**: "Review PR #42"

**Copilot monitors**:

1. **GitHub integration**: Verify PR fetched via MCP github tools
2. **Code quality checks**: Monitor code_review agent invocation
3. **Linear issue creation**: Verify feedback logged to Linear
4. **HITL trigger**: Check if high-risk changes flagged

**Commands**:

```bash
# Check GitHub tool usage
mcp_copilot_conta_logs_for_container("deploy-orchestrator-1") | grep "github"

# Query approval requests
docker exec -it deploy-state-persist-1 psql -U postgres -d codechef \
  -c "SELECT * FROM approval_requests WHERE status='pending';"
```

### Scenario 3: Infrastructure Changes

**User Command**: "Deploy new Kubernetes service"

**Copilot monitors**:

1. **Risk assessment**: Verify RiskAssessor scores as HIGH/CRITICAL
2. **HITL approval**: Confirm Linear issue created for approval
3. **Workflow pause**: Check interrupt() called, checkpoint saved
4. **Resume after approval**: Monitor webhook trigger or poll resume

**Commands**:

```bash
# View risk assessment logs
docker logs deploy-orchestrator-1 | grep "RiskAssessor"

# Check HITL state
curl http://localhost:8001/workflows/status/<workflow-id>

# Query Linear for approval issue
# (Use Linear web UI or mcp_linear_search_issues)
```

### Scenario 4: Multi-Agent Workflow

**User Command**: "Implement feature, test, document, deploy"

**Copilot monitors**:

1. **Supervisor coordination**: Track agent handoffs (feature_dev → cicd → documentation)
2. **Workflow events**: Query workflow_events table for state transitions
3. **Checkpointing**: Verify checkpoint saved between agent transitions
4. **Error recovery**: Monitor for failures, check interrupt/resume logic

**Commands**:

```bash
# View workflow progression
docker exec -it deploy-state-persist-1 psql -U postgres -d codechef \
  -c "SELECT event_type, agent_name, created_at FROM workflow_events WHERE workflow_id='<id>' ORDER BY created_at;"

# Check current agent
curl http://localhost:8001/workflows/<workflow-id> | jq '.current_agent'

# View LangSmith workflow trace
# Filter: metadata.workflow_id:"<id>"
```

---

## Observability & Tracing

### LangSmith Integration

**Projects** (Purpose-Based):

- **code-chef-production** - Live extension usage (primary monitoring target)
- **code-chef-experiments** - A/B testing (compare baseline vs trained models)
- **code-chef-training** - Model training operations (track AutoTrain jobs)
- **code-chef-evaluation** - Model evaluations (review metrics, recommendations)

**Trace Metadata Schema** (`config/observability/tracing-schema.yaml`):

```python
{
    "experiment_group": "code-chef",  # or "baseline" for A/B testing
    "environment": "production",      # or training, evaluation, test
    "module": "feature_dev",          # agent or module name
    "extension_version": "1.2.3",     # VS Code extension version
    "model_version": "qwen-coder-32b-v2",
    "experiment_id": "exp-2025-01-001",  # Correlate A/B runs
    "task_id": "task-uuid",              # Correlate across groups
    "config_hash": "sha256:..."          # Config fingerprint
}
```

**Common Queries**:

```python
# Recent errors in production
environment:"production" AND status:"error" AND start_time > now-1h

# Specific agent performance
module:"feature_dev" AND environment:"production" AND latency > 5s

# Workflow execution
metadata.workflow_id:"<workflow-id>"

# A/B testing comparison
experiment_id:"exp-2025-01-001" AND experiment_group:"code-chef"
```

**Access**: https://smith.langchain.com → Select project → Apply filters

### Prometheus Metrics

**Key Metrics** (available at `/metrics`):

```bash
# Token usage by agent
llm_tokens_total{agent="feature_dev", type="prompt"}
llm_tokens_total{agent="feature_dev", type="completion"}

# Cost tracking
llm_cost_usd_total{agent="feature_dev"}

# Request latency
http_request_duration_seconds{endpoint="/execute", method="POST"}

# LLM call count
llm_calls_total{agent="feature_dev", model="qwen-coder-32b"}

# Error rate
http_requests_total{status="500", service="orchestrator"}
```

**Grafana Dashboards**: https://appsmithery.grafana.net

- **LLM Token Metrics** - Token usage, cost tracking, efficiency
- **Container Health** - CPU, memory, restart count
- **Request Latency** - P50, P95, P99 percentiles
- **Error Rates** - By service, endpoint, status code

---

## Production Rules (Non-Negotiable)

### Linear Issue Tracking

**Every production change** requires a Linear issue:

```python
# Create issue for changes
mcp_linear_create_issue(
    title="Fix authentication timeout",
    description="...",
    project="CHEF",
    labels=["bug", "high-priority"]
)

# Update issue with GitHub permalink
mcp_linear_update_issue(
    issue_id="CHEF-123",
    description="Fix implemented in https://github.com/Appsmithery/Dev-Tools/blob/abc123/agent_orchestrator/graph.py#L45"
)
```

**GitHub Permalinks** (not relative paths):

```bash
# Get commit SHA
git log -1 --format="%H" -- "agent_orchestrator/graph.py"

# Format: https://github.com/Appsmithery/Dev-Tools/blob/<commit-sha>/<path>#L<line>
# Example: https://github.com/Appsmithery/Dev-Tools/blob/abc123def456/agent_orchestrator/graph.py#L45
```

### Deployment Validation

**Always validate after deploys to droplet**:

```bash
# 1. Push changes from local
cd D:\APPS\code-chef
git add -A
git commit -m "<describe changes>"
git push origin main

# 2. Pull and restart on droplet
ssh root@45.55.173.72 "cd /opt/Dev-Tools && git pull && docker compose down && docker compose up -d"

# 3. Wait for services to start (30-60 seconds)
sleep 60

# 4. Health checks via SSH
ssh root@45.55.173.72 "docker compose ps && curl -s http://localhost:8001/health | jq ."

# 5. Public endpoint check
curl -s https://codechef.appsmithery.co/health | jq .

# 6. Test workflow routing (via extension or curl)
curl -X POST https://codechef.appsmithery.co/execute \
  -H "Content-Type: application/json" \
  -d '{"message": "Implement hello world", "user_id": "test"}'

# 7. Check metrics and resource usage
ssh root@45.55.173.72 "free -h && docker stats --no-stream"
ssh root@45.55.173.72 "curl -s http://localhost:8001/metrics/tokens | jq ."

# 8. Monitor logs for errors (first 5 minutes)
ssh root@45.55.173.72 "docker compose logs -f --tail=50"
```

### Cleanup Protocol

**Production Droplet** (⚠️ USE WITH CAUTION):

```bash
# Clean up orphaned resources (safe)
ssh root@45.55.173.72 "docker system prune -f"

# Restart specific service (minimal downtime)
ssh root@45.55.173.72 "cd /opt/Dev-Tools && docker compose restart orchestrator"

# Full restart (30-60s downtime, use during off-hours)
ssh root@45.55.173.72 "cd /opt/Dev-Tools && docker compose down && docker compose up -d"

# Nuclear option: Remove volumes (⚠️ DATA LOSS - backup first!)
# ssh root@45.55.173.72 "cd /opt/Dev-Tools && docker compose down -v"
```

**Local Development** (safe to experiment):

```bash
# Full cleanup
docker compose down --remove-orphans --volumes

# Restart clean
docker compose up -d
```

**Docker Resource Management**:

- **Production**: Treat with care, monitor resource usage, schedule maintenance windows
- **Local**: Treat containers as disposable, experiment freely
- Leave stacks **fully running** or **fully stopped** (never partial)
- Clean up orphaned volumes: `docker volume prune` (safe on droplet)
- Monitor disk usage: `ssh root@45.55.173.72 "docker system df"`
- **4GB RAM guideline**: Keep container total <2.5GB actual usage, leave 1.5GB for system

---

## Development Workflow (Public Beta → Commercial)

### Current State (December 2025)

- **Status**: Public Beta with single user (you)
- **Deployment**: Production on 4GB DigitalOcean droplet (45.55.173.72)
- **Architecture**: Cloud-first with optional local testing
- **Extension**: In development, preparing for VSCE Marketplace
- **Repository**: Public (Appsmithery/code-chef), will remain open-source

### Local → Production Workflow

```bash
# 1. Make changes locally (Windows)
cd D:\APPS\code-chef
# Edit files in VS Code

# 2. Test locally (optional)
cd deploy
docker compose up -d
# Test changes
docker compose down

# 3. Commit and push
git add -A
git commit -m "<describe changes>"
git push origin main

# 4. Deploy to droplet
ssh root@45.55.173.72 "cd /opt/Dev-Tools && git pull && docker compose down && docker compose up -d"

# 5. Validate
curl -s https://codechef.appsmithery.co/health | jq .
```

### VS Code Extension Development

**Location**: `extensions/vscode-codechef/`

```bash
# Install dependencies
cd extensions/vscode-codechef
npm install

# Run in debug mode (F5 or Run → Start Debugging)
# Opens new VS Code window with extension loaded

# Package for marketplace
vsce package
# Creates vscode-codechef-<version>.vsix

# Future: Publish to VSCE Marketplace
vsce publish
```

### Preparing for Commercial Launch

**Checklist** (Future Work):

- [ ] **Extension**: Polish UI/UX, add onboarding wizard
- [ ] **Documentation**: User guides, video tutorials, API docs
- [ ] **Infrastructure**: Multi-tenant support, user authentication
- [ ] **Billing**: Stripe integration, tiered pricing model
- [ ] **Support**: Help desk, community forum, status page
- [ ] **Marketing**: Landing page, SEO, social media presence
- [ ] **Legal**: Terms of service, privacy policy, GDPR compliance
- [ ] **Monitoring**: Enhanced observability, uptime monitoring
- [ ] **Security**: Penetration testing, vulnerability scanning
- [ ] **Performance**: Load testing, auto-scaling, CDN

**Business Model Options**:

1. **Freemium**: Free tier (limited requests/month) + Paid tiers
2. **Subscription**: Monthly/annual plans ($9.99, $29.99, $99.99/mo)
3. **Usage-based**: Pay per LLM call/token (cost + markup)
4. **Enterprise**: Custom pricing, SLA, dedicated support

**Current Focus**: Stabilize single-user beta, optimize costs, refine UX

---

## Repository Structure

```
code-chef/
├── agent_orchestrator/
│   ├── agents/
│   │   ├── supervisor/          # Task routing, workflow coordination
│   │   ├── feature_dev/         # Code implementation
│   │   ├── code_review/         # Security, quality checks
│   │   ├── infrastructure/      # IaC, Terraform, ModelOps
│   │   ├── cicd/                # Pipelines, GitHub Actions
│   │   ├── documentation/       # Specs, READMEs, API docs
│   │   └── _shared/
│   │       └── base_agent.py    # BaseAgent with progressive tool loading
│   ├── workflows/
│   │   ├── workflow_engine.py   # Event-sourced execution
│   │   ├── workflow_router.py   # Heuristic + LLM routing
│   │   └── templates/           # Declarative workflow YAML
│   ├── graph.py                 # LangGraph StateGraph
│   └── main.py                  # FastAPI app, webhooks
├── shared/
│   ├── lib/
│   │   ├── mcp_client.py        # Agent manifest loading
│   │   ├── mcp_tool_client.py   # Direct MCP tool invocation
│   │   ├── mcp_discovery.py     # Server/tool enumeration
│   │   ├── progressive_mcp_loader.py  # Token-efficient loading
│   │   ├── hitl_manager.py      # HITL approvals + Linear
│   │   ├── linear_client.py     # Linear GraphQL API
│   │   ├── checkpoint_connection.py  # PostgreSQL checkpointer
│   │   ├── token_tracker.py     # LLM cost tracking
│   │   └── longitudinal_tracker.py   # A/B testing metrics
│   ├── services/
│   │   ├── rag/                 # Vector DB (Qdrant)
│   │   ├── state-persist/       # PostgreSQL, checkpoints
│   │   ├── agent-registry/      # Agent manifest API
│   │   └── langgraph/           # LangGraph API server
│   └── mcp/
│       ├── README.md            # MCP architecture guide
│       └── gateway/             # Linear OAuth (Node.js)
├── config/
│   ├── agents/models.yaml       # Model configs (OpenRouter)
│   ├── routing/task-router.rules.yaml
│   ├── mcp-agent-tool-mapping.yaml
│   ├── hitl/
│   │   ├── approval-policies.yaml
│   │   └── risk-assessment-rules.yaml
│   ├── linear/
│   │   ├── agent-project-mapping.yaml
│   │   └── project-registry.yaml
│   ├── observability/
│   │   └── tracing-schema.yaml
│   └── rag/
│       └── indexing.yaml
├── deploy/
│   └── docker-compose.yml
├── extensions/
│   └── vscode-codechef/         # VS Code extension
└── support/
    ├── docs/                     # Architecture, deployment guides
    ├── scripts/                  # Indexing, Linear, validation
    └── tests/                    # Unit, integration, E2E tests
```

---

## Key Files for Copilot Reference

### Configuration

### Configuration

| File                                       | Purpose                                |
| ------------------------------------------ | -------------------------------------- |
| `config/agents/models.yaml`                | Model selection per agent (OpenRouter) |
| `config/routing/task-router.rules.yaml`    | Heuristic routing patterns             |
| `config/mcp-agent-tool-mapping.yaml`       | Tool priorities per agent              |
| `config/hitl/approval-policies.yaml`       | HITL approval rules                    |
| `config/hitl/risk-assessment-rules.yaml`   | Risk scoring logic                     |
| `config/linear/agent-project-mapping.yaml` | Agent→Linear project mapping           |
| `config/observability/tracing-schema.yaml` | LangSmith metadata schema              |

### Core Modules

| File                                              | Purpose                             |
| ------------------------------------------------- | ----------------------------------- |
| `agent_orchestrator/graph.py`                     | LangGraph StateGraph, checkpointing |
| `agent_orchestrator/workflows/workflow_router.py` | Task→workflow routing               |
| `agent_orchestrator/workflows/workflow_engine.py` | Event-sourced execution             |
| `agent_orchestrator/agents/_shared/base_agent.py` | Progressive tool loading            |
| `shared/lib/mcp_tool_client.py`                   | Direct MCP tool invocation          |
| `shared/lib/hitl_manager.py`                      | HITL approvals + Linear webhooks    |
| `shared/lib/progressive_mcp_loader.py`            | Token-efficient tool selection      |

### Documentation

| File                                                     | Purpose                                 |
| -------------------------------------------------------- | --------------------------------------- |
| `support/docs/architecture-and-platform/ARCHITECTURE.md` | System architecture overview            |
| `support/docs/getting-started/DEPLOYMENT.md`             | Deployment procedures                   |
| `support/docs/operations/LLM_OPERATIONS.md`              | ModelOps guide (training, eval, deploy) |
| `shared/mcp/README.md`                                   | MCP v2.0 architecture guide             |
| `shared/lib/README.md`                                   | Shared library reference                |
| `shared/services/rag/README.md`                          | RAG service documentation               |

---

## ModelOps Extension

> **📘 Complete Documentation**: See [LLM Operations Guide](../support/docs/operations/LLM_OPERATIONS.md) for comprehensive procedures.

The Infrastructure agent supports full model lifecycle management:

### Training

**HuggingFace Space**: `alextorelli/code-chef-modelops-trainer`

| Mode       | Cost  | Duration | Dataset Size | Use Case          |
| ---------- | ----- | -------- | ------------ | ----------------- |
| Demo       | $0.50 | 5 min    | 100 examples | Quick validation  |
| Production | $3.50 | 60 min   | 1000+        | Full improvement  |
| Extended   | $15   | 90 min   | 5000+        | High-quality tune |

**Features**:

- AutoTrain handles GPU selection, LoRA config
- Real-time progress monitoring in VS Code
- TensorBoard integration for metrics
- Automatic model upload to HuggingFace

### Evaluation

**LangSmith-Based Comparison**:

- Weighted scoring: 30% accuracy, 25% completeness, 20% efficiency, 15% latency, 10% integration
- Baseline vs candidate comparison
- Automatic recommendations: **deploy** (>15%), **needs_review** (5-15%), **reject** (<5%)

**A/B Testing**:

- Baseline: Untrained model
- Code-chef: Fine-tuned model
- Same tasks, different experiment_group metadata
- PostgreSQL storage via `longitudinal_tracker`

### Deployment

**Immediate Deployment** with rollback:

- Updates `config/agents/models.yaml` automatically
- Creates backup before changes
- Restarts affected services (30s downtime)
- Rollback in <60 seconds if issues detected

**Version Tracking**:

- Registry: `config/models/registry.json`
- Pydantic validation
- Deployment history with timestamps

### VS Code Commands

| Command                           | Purpose                    |
| --------------------------------- | -------------------------- |
| `codechef.modelops.train`         | Launch training wizard     |
| `codechef.modelops.evaluate`      | Compare model performance  |
| `codechef.modelops.deploy`        | Deploy to production       |
| `codechef.modelops.rollback`      | Revert to previous version |
| `codechef.modelops.modelVersions` | View deployment history    |

**Key Files**:

- `agent_orchestrator/agents/infrastructure/modelops/coordinator.py`
- `agent_orchestrator/agents/infrastructure/modelops/training.py`
- `agent_orchestrator/agents/infrastructure/modelops/evaluation.py`
- `agent_orchestrator/agents/infrastructure/modelops/deployment.py`

---

## Quality Bar

### Code Standards

- ✅ **Type hints** on all function signatures
- ✅ **Pydantic models** for data validation
- ✅ **@traceable decorators** for LangGraph nodes/workflows
- ✅ **Docstrings** with Args, Returns, Raises sections
- ✅ **Error handling** with graceful fallbacks
- ✅ **Logging** at appropriate levels (DEBUG, INFO, WARNING, ERROR)

### Health Endpoints

All services must return:

```json
{
  "status": "ok",
  "service": "<service-name>",
  "version": "<semver>",
  "dependencies": {
    "<dep-name>": "connected" | "error"
  }
}
```

### Documentation Rules

- **DO NOT create summary markdown files** unless explicitly requested
- Update existing docs in `support/docs/` when architecture changes
- Use GitHub permalinks (not relative paths) in Linear issues
- Keep README.md files concise and actionable

### Linear Integration

- **Every production change** requires a Linear issue
- Use `mcp_linear_*` tools or `activate_issue_management_tools`
- Link implementation files with GitHub permalinks
- Update issue status after completion

---

## Troubleshooting Quick Reference

### Service Won't Start

```bash
# Check logs
docker logs deploy-<service>-1 --tail=100

# Verify ports available
netstat -ano | findstr :<port>

# Check dependencies
docker compose ps
curl http://localhost:5432  # PostgreSQL
curl https://83b61795-7dbd-4477-890e-edce352a00e2.us-east4-0.gcp.cloud.qdrant.io:6333/collections  # Qdrant
```

### Agent Not Responding

```bash
# Check model API keys
echo $OPENROUTER_API_KEY

# Verify agent in manifest
cat agents-manifest.json | jq '.profiles[] | select(.name=="feature_dev")'

# Check LangSmith traces
# Filter: module:"feature_dev" AND status:"error"

# Review container logs
docker logs deploy-orchestrator-1 | grep "feature_dev"
```

### HITL Not Triggering

```bash
# Verify Linear webhook config
cat config/linear/webhook-handlers.yaml

# Check approval policies
cat config/hitl/approval-policies.yaml

# Query pending approvals
docker exec -it deploy-state-persist-1 psql -U postgres -d codechef \
  -c "SELECT * FROM approval_requests WHERE status='pending';"

# Test Linear API connectivity
curl -H "Authorization: $LINEAR_API_KEY" https://api.linear.app/graphql \
  -d '{"query": "{ viewer { id name } }"}'
```

### MCP Tools Failing

```bash
# List available servers
docker mcp list

# Test tool invocation
docker mcp invoke memory create_entities \
  --params '{"entities": [{"name": "test", "type": "debug"}]}'

# Check Docker MCP Toolkit extension
# VS Code: Extensions → Search "Docker MCP Toolkit" → Reload

# Verify stdio transport
cat ~/.config/mcp-docker/config.json
```

### Database Connection Issues

```bash
# Check PostgreSQL status
docker exec -it deploy-state-persist-1 pg_isready

# Test connection
docker exec -it deploy-state-persist-1 psql -U postgres -d codechef -c "SELECT 1;"

# View connection pool
curl http://localhost:8008/health | jq '.dependencies.postgres'

# Check migrations
docker exec -it deploy-state-persist-1 psql -U postgres -d codechef \
  -c "\dt"  # List tables
```

---

## Testing Strategy

### Unit Tests

```bash
# Run all tests
pytest support/tests -v

# Test specific module
pytest support/tests/unit/shared/lib/test_progressive_mcp_loader.py -v

# With coverage
pytest support/tests --cov=agent_orchestrator --cov=shared --cov-report=html
```

### Integration Tests

```bash
# Requires Docker
pytest support/tests/integration -v

# Test MCP tool client
pytest support/tests/integration/test_mcp_tool_client.py -v

# Test workflow engine
pytest support/tests/integration/test_workflow_engine.py -v
```

### Property-Based Tests

```bash
# Default profile (100 examples per property)
pytest support/tests/evaluation/test_property_based.py -v

# CI profile (fast, 20 examples)
HYPOTHESIS_PROFILE=ci pytest support/tests/evaluation/test_property_based.py -v

# Thorough profile (500 examples)
HYPOTHESIS_PROFILE=thorough pytest support/tests/evaluation/test_property_based.py -v
```

### E2E Tests

```bash
# Full workflow execution
pytest support/tests/e2e -v -s

# Test specific workflow
pytest support/tests/e2e/test_feature_development_workflow.py -v
```

---

## When to Defer to Head Chef

**Copilot should suggest using the orchestrator** when:

1. **Multi-agent coordination** needed (e.g., "implement feature X, review it, deploy it")
2. **Complex workflows** with multiple steps (e.g., "refactor codebase and update docs")
3. **Background execution** required (e.g., "train model and notify when done")
4. **HITL approvals** needed (e.g., "deploy to production")
5. **Long-running operations** (e.g., "index entire GitHub repository")

**Example Response**:

```
This task requires multi-agent coordination (feature_dev → code_review → cicd).
I'll invoke the Head Chef orchestrator to handle this workflow:

[Shows command to trigger orchestrator]

Once started, I can monitor progress via:
- Container logs: mcp_copilot_conta_logs_for_container("deploy-orchestrator-1")
- LangSmith traces: https://smith.langchain.com (filter: workflow_id:"<id>")
- Database state: Query workflow_events table for progression
```

---

## Summary

You are **Sous Chef** - the monitoring and debugging companion to code-chef's Head Chef orchestrator. Your primary responsibilities:

1. **Monitor** orchestrator activity via logs, traces, metrics
2. **Debug** issues using container inspection, database queries
3. **Validate** configurations, health checks, deployments
4. **Assist** with direct code edits, file operations, Linear updates
5. **Defer** complex workflows to the orchestrator

Use the full suite of MCP tools (178+), progressive loading strategies, and comprehensive observability stack to complement the Head Chef's autonomous operations.

**Key Resources**:

- LangSmith: https://smith.langchain.com
- Grafana: https://appsmithery.grafana.net
- Linear: https://linear.app/dev-ops/project/codechef-78b3b839d36b
- Production: https://codechef.appsmithery.co (45.55.173.72)
- Documentation: `support/docs/` directory

When in doubt, check health endpoints first, then logs, then traces, then metrics. Always validate changes in non-production environments before deploying to production.
