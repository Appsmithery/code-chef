# GitHub Copilot Instructions for Dev-Tools

## System Overview

**Production**: Multi-agent DevOps automation platform on DigitalOcean droplet 45.55.173.72

**Core Architecture**:

- Single orchestrator (`agent_orchestrator/`) with 6 agent nodes (supervisor, feature_dev, code_review, infrastructure, cicd, documentation)
- LangGraph StateGraph workflow with LangChain tool binding
- MCP gateway (port 8000): 150+ tools across 17 servers, progressive disclosure (80-90% token savings)
- LLM: DigitalOcean Gradient AI (llama3.3-70b orchestrator, per-node optimization)
- Observability: LangSmith tracing, Grafana/Prometheus metrics
- HITL: Risk-based approvals via Linear (DEV-68 hub), LangGraph checkpointing
- Service ports: gateway:8000, orchestrator:8001, rag:8007, state:8008, langgraph:8010
- **Zen Pattern Integration (DEV-175, completed Nov 2025)**: Parent workflow chains, resource deduplication (80-90% token savings), workflow TTL management

## Repository Navigation

```
Dev-Tools/
├── agent_orchestrator/
│   ├── agents/              # Agent-centric organization (12-Factor Agents)
│   │   ├── _shared/         # base_agent.py, tool_guides/*.prompt.md
│   │   ├── supervisor/      # __init__.py, system.prompt.md, tools.yaml, workflows/
│   │   ├── feature_dev/     # Code generation agent
│   │   ├── code_review/     # Security/quality analysis
│   │   ├── infrastructure/  # IaC generation
│   │   ├── cicd/            # Pipeline automation
│   │   └── documentation/   # Technical writing
│   ├── workflows/           # Multi-agent workflows
│   │   ├── templates/       # pr-deployment.workflow.yaml, hotfix.workflow.yaml
│   │   └── *.py             # Workflow implementations
│   ├── graph.py             # LangGraph StateGraph definition
│   └── main.py              # Orchestrator FastAPI service
├── shared/
│   ├── lib/                 # Core libraries (mcp_client, gradient_client, progressive_mcp_loader)
│   ├── services/            # langgraph:8010, rag:8007, state:8008
│   ├── gateway/             # MCP gateway:8000
│   └── mcp/servers/         # 17 MCP servers
├── config/
│   ├── env/.env             # Secrets (gitignored, use .env.template)
│   ├── linear/              # linear-config.yaml, project-registry.yaml
│   ├── agents/models.yaml   # LLM configuration
│   ├── hitl/                # risk-assessment-rules.yaml, approval-policies.yaml
│   └── state/schema.sql     # PostgreSQL schema
├── deploy/
│   └── docker-compose.yml   # Service definitions
└── support/
    ├── scripts/
    │   ├── deploy/deploy-to-droplet.ps1  # Deployment (config/full/auto)
    │   └── linear/agent-linear-update.py # Linear roadmap management
    ├── docs/                # QUICKSTART.md, ARCHITECTURE.md, DEPLOYMENT.md
    └── tests/               # Test suites
```

## Configuration

- **Secrets**: `config/env/.env` (gitignored) - Copy from `.env.template`, populate API keys
- **Linear**: `config/linear/linear-config.yaml` (structure), `config/linear/project-registry.yaml` (projects)
- **LLM**: `config/agents/models.yaml` - All agent models, costs, parameters; hot-reload on restart
- **HITL**: `config/hitl/risk-assessment-rules.yaml`, `config/hitl/approval-policies.yaml`
- **State**: `config/state/schema.sql` - PostgreSQL schema for checkpointing
- **Observability**: LangSmith (`.env` keys), Prometheus (`config/prometheus/prometheus.yml`)

## Linear Integration

### Roadmap Management (CRITICAL WORKFLOW)

When user says _"update linear roadmap"_ → Update Linear project issues via API, NOT markdown files

**Commands:**

```bash
# Update project descriptions
python support/scripts/linear/agent-linear-update.py update-project --project-id "UUID"

# Create issue
python support/scripts/linear/agent-linear-update.py create-issue --project-id "UUID" --title "..." --description "..."

# Update issue status
python support/scripts/linear/agent-linear-update.py update-status --issue-id "PR-XX" --status "done"

# Create sub-issues (3-5 tasks for complex features)
python support/scripts/linear/agent-linear-update.py create-phase --project-id "UUID"
```

**Environment:** Set `$env:LINEAR_API_KEY="lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571"` before running

**Key Details:**

- **Project UUID**: AI DevOps Agent Platform = `b21cbaa1-9f09-40f4-b62a-73e0f86dd501`
- **Team ID**: Project Roadmaps (PR) = `f5b610be-ac34-4983-918b-2c9d00aa9b7a`
- **HITL Hub**: DEV-68 (workspace-wide approval notifications only)
- **Status Values**: todo, in_progress, done
- **Retrospective Updates**: Always mark completed work as "done"
- **Decompose Tasks**: Create sub-issues for complex features (3-5 tasks each)
- **Dependency Awareness**: Use explicit dependency identifiers between issues/subissues
- **Temporal Ambiguity**: Don't reference time periods or relative timelines
- **Taxonomy**: Linear platform content structure includes {`Workspace` > `Team` > `Project` > `Issue` > `Sub-issue` > `Milestone`}

### HITL Approvals

- Risk-based workflow: low (auto-approved) → medium (dev/tech_lead) → high/critical (devops_engineer)
- Orchestrator creates sub-issues in DEV-68 via `linear_workspace_client.py`
- LangGraph checkpoint interrupts workflow, resumes on approval
- Template: `HITL_ORCHESTRATOR_TEMPLATE_UUID=aa632a46-ea22-4dd0-9403-90b0d1f05aa0`

## Deployment workflows

### Quick Reference

**Automated Deployment (Recommended):**

```powershell
# Auto-detect changes and deploy
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType auto

# Config-only (30s - for .env changes)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config

# Full rebuild (10min - for code changes)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType full

# Rollback to previous commit
.\support\scripts\deploy\deploy-to-droplet.ps1 -Rollback
```

**Health Checks:**

```bash
curl http://45.55.173.72:8001/health  # Orchestrator
curl http://45.55.173.72:8000/health  # Gateway
curl http://45.55.173.72:8007/health  # RAG
curl http://45.55.173.72:8008/health  # State
```

### ⚠️ Configuration Changes (CRITICAL)

**The droplet is connected to the main repo branch.** Configuration changes in `config/env/.env` require a specific workflow:

1. **Update Local `.env`**: Edit `config/env/.env` with new configuration
2. **Update Template** (if applicable): Sync changes to `config/env/.env.template` if adding new variables
3. **Commit Template**: `git add config/env/.env.template && git commit && git push` (`.env` is gitignored)
4. **Deploy to Droplet**:

   ```powershell
   .\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config
   ```

5. **Verify**: Check health endpoints and verify environment variables loaded correctly

**Why This Matters**: Docker Compose reads `.env` at startup. Simple `docker compose restart` does NOT reload environment variables from disk. You must use `down && up` to pick up `.env` changes.

### Deployment Strategies

| Change Type             | Strategy | Duration | Command                                        |
| ----------------------- | -------- | -------- | ---------------------------------------------- |
| `.env` or config YAML   | `config` | 30s      | `...\deploy-to-droplet.ps1 -DeployType config` |
| Python code, Dockerfile | `full`   | 10min    | `...\deploy-to-droplet.ps1 -DeployType full`   |
| Documentation, README   | `quick`  | 15s      | `...\deploy-to-droplet.ps1 -DeployType quick`  |
| Not sure                | `auto`   | varies   | `...\deploy-to-droplet.ps1 -DeployType auto`   |

**GitHub Actions:**

- **Deployment**: `.github/workflows/deploy-intelligent.yml`
  - Automatic on push to `main` branch
  - Detects file changes and selects optimal strategy (config/full/quick)
  - Manual trigger with strategy override via workflow_dispatch
  - Health validation and automatic cleanup on failure
  - Triggers cleanup workflow after successful deploys
- **Cleanup**: `.github/workflows/cleanup-docker-resources.yml`
  - Runs after successful deployments (standard cleanup)
  - Weekly schedule: Sundays at 3 AM UTC (aggressive cleanup)
  - Manual trigger with 3 modes: standard/aggressive/full
  - Includes pre/post metrics and health validation

**Complete Documentation:** See `support/docs/DEPLOYMENT.md` for detailed procedures, troubleshooting, and HITL workflow

### Local Development

- Use `make up|down|rebuild|logs` (wraps `support/scripts/dev/*.sh`) or direct `docker-compose` commands; scripts assume bash and run from repo root.
- `./support/scripts/dev/up.sh` brings stack online, waits 10s, prints health; `make logs-agent AGENT=<service>` for troubleshooting.
- Rebuild when Python deps change: `support/scripts/dev/rebuild.sh` or `docker-compose build <service>`.
- Backups: `support/scripts/docker/backup_volumes.sh` creates tarballs of `orchestrator-data`, `mcp-config`, `qdrant-data`, `postgres-data` under `./backups/<timestamp>`.
- Local overrides: `deploy/docker-compose.override.yml` (gitignored sample sets DEBUG/LOG_LEVEL).

### Remote Deployment (DigitalOcean)

- Target droplet: `45.55.173.72` (alex@appsmithery.co)
- Deploy path: `/opt/Dev-Tools`
- Method 1: `./support/scripts/deploy.ps1 -Target remote` (copies .env, builds, deploys)
- Method 2: SSH + git pull + docker-compose commands (see `support/docs/DEPLOY.md`)
- Verify: Check health endpoints, LangSmith traces, Prometheus metrics
- API key from `GRADIENT_API_KEY` env var (uses DigitalOcean PAT); base URL `https://api.digitalocean.com/v2/ai`.
- Orchestrator model: llama3.3-70b-instruct. Agent node models configured in respective agent files (supervisor/code-review: 70b, feature-dev: codellama-13b, infrastructure/cicd: 8b, documentation: mistral-7b).
- Cost: $0.20-0.60/1M tokens (150x cheaper than GPT-4); <50ms latency within DO network.

### SSH Access from VS Code

**VS Code Remote SSH Extension:**

1. Install "Remote - SSH" extension (`ms-vscode-remote.remote-ssh`)
2. Press `F1` → "Remote-SSH: Connect to Host"
3. Enter: `root@45.55.173.72` or use alias `do-mcp-gateway`
4. Opens new VS Code window connected to droplet
5. Access terminal, files, and run commands directly on remote
6. Edit files in place, debug services, and monitor logs in real-time

**SSH Config Setup** (`C:\Users\<USER>\.ssh\config` on Windows, `~/.ssh/config` on Linux/Mac):

```
Host do-mcp-gateway
    HostName 45.55.173.72
    User root
    IdentityFile ~/.ssh/github-actions-deploy
    StrictHostKeyChecking no
    ServerAliveInterval 60
```

**Quick Remote Commands:**

```powershell
# SSH directly from terminal
ssh root@45.55.173.72

# Execute single command
ssh root@45.55.173.72 "cd /opt/Dev-Tools && git pull && docker compose ps"

# SCP files to droplet
scp local-file.txt root@45.55.173.72:/opt/Dev-Tools/

# Tail logs remotely
ssh root@45.55.173.72 "docker compose -f /opt/Dev-Tools/deploy/docker-compose.yml logs -f orchestrator"

# Check service health
ssh root@45.55.173.72 "curl -s http://localhost:8001/health | jq ."

# Restart specific service
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose restart orchestrator"
```

**Firewall Configuration (UFW):**

```bash
ssh root@45.55.173.72
ufw allow 22/tcp              # SSH (CRITICAL)
ufw allow 8000:8008/tcp       # Agent services
ufw allow 80/tcp              # HTTP (Caddy)
ufw allow 443/tcp             # HTTPS (Caddy with Let's Encrypt)
ufw status                    # Verify rules
```

### Container Hygiene & Cleanup (Automated)

**Automated Cleanup System** (DEV-169, completed):

- **Post-deployment**: Automatic cleanup after every deploy via `deploy-to-droplet.ps1` (dangling images, build cache, 1h old containers)
- **Weekly maintenance**: Cron job runs Sundays at 3 AM UTC via `weekly-cleanup.sh` (7-day retention policy)
- **GitHub Actions**: `cleanup-docker-resources.yml` workflow with 3 modes (standard/aggressive/full)
- **Expected savings**: 500MB-1GB per deploy, 1-2GB weekly, prevents 100% memory saturation
- **Monitoring**: Logs at `/var/log/docker-cleanup.log` on droplet

**Manual Cleanup** (when needed):

- **Never leave failed containers running.** After experiments or interrupted builds, run `docker compose down --remove-orphans` before handing control back to the user.
- **Quick cleanup**: `ssh root@45.55.173.72 "docker image prune -f && docker builder prune -f"`
- **Emergency cleanup**: Use GitHub Actions workflow with "full" mode (stops services, cleans all, restarts)
- **Verify health after cleanup.** Re-run `support/scripts/validation/validate-tracing.sh` or curl `/health` endpoints to confirm the stack is stable before moving on.
- **Document what you removed.** Mention the cleanup commands you executed in your summary so the operator understands the current state.

**Documentation**: `support/docs/operations/CLEANUP_QUICK_REFERENCE.md`, `support/docs/operations/droplet-memory-optimization.md`

### LangSmith (LLM Tracing)

- **Automatic tracing** via LangChain's native integration in `gradient_client`; no explicit tracing code needed in agents.
- **Dashboard**: https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects/p/f967bb5e-2e61-434f-8ee1-0df8c22bc046
- **Configuration** (in `config/env/.env`):
  ```bash
  LANGSMITH_TRACING=true                                              # Enable LangSmith SDK tracing
  LANGCHAIN_TRACING_V2=true                                           # Enable LangChain tracing
  LANGCHAIN_ENDPOINT=https://api.smith.langchain.com                  # LangSmith API endpoint
  LANGCHAIN_PROJECT=agents                                            # Project name (auto-created if missing)
  LANGCHAIN_API_KEY=lsv2_sk_***                                       # Service key (full org access)
  LANGSMITH_API_KEY=lsv2_sk_***                                       # Same key (both vars supported)
  LANGSMITH_WORKSPACE_ID=5029c640-3f73-480c-82f3-58e402ed4207        # Workspace/Org ID from URL
  ```
- **Key Requirements**:
  - Use **service key** (`lsv2_sk_*`) not personal token (`lsv2_pt_*`) for production
  - **Workspace ID** is REQUIRED for org-scoped service keys (extract from URL: `/o/{workspace-id}/`)
  - Both `LANGCHAIN_API_KEY` and `LANGSMITH_API_KEY` must be set (SDK compatibility)
- **Deployment**: After changing tracing config, must run `docker compose down && docker compose up -d` (restart alone won't reload `.env`)
- **Deprecation Note**: Langfuse has been completely removed. All tracing now uses LangSmith only. No `LANGFUSE_*` environment variables should be present. Gateway instrumentation.js contains only OpenTelemetry, no Langfuse imports.

### Grafana Cloud (Prometheus Metrics)

- **Metrics Collection**: Grafana Alloy v1.11.3 installed on droplet (45.55.173.72), scrapes 4 services every 15s
- **Dashboard**: https://appsmithery.grafana.net (Stack 1376474-hm, Org ID 1534681, User ID 2677183)
- **Remote Write**: https://prometheus-prod-56-prod-us-east-2.grafana.net/api/prom/push
- **Configuration** (on droplet at `/etc/alloy/config.alloy`):
  - **Instrumented Services**: orchestrator:8001, gateway-mcp:8000, state-persistence:8008, prometheus:9090
  - **Scrape Interval**: 15s
  - **Metrics Exposed**: `/metrics` endpoints on all 4 services
  - **Gateway (Node.js)**: prom-client with default metrics (CPU, memory, event loop, GC)
  - **State/Orchestrator (Python)**: prometheus-fastapi-instrumentator with HTTP request metrics
- **Alloy Service Management**:

  ```bash
  # Check status
  ssh root@45.55.173.72 "sudo systemctl status alloy"

  # Restart after config changes
  ssh root@45.55.173.72 "sudo systemctl restart alloy"

  # View logs
  ssh root@45.55.173.72 "sudo journalctl -u alloy -f"
  ```

- **Dashboard Access**: Navigate to https://appsmithery.grafana.net/explore, select datasource "grafanacloud-appsmithery-prom", query `up{cluster="dev-tools"}` to verify all services reporting

## Extension points

### Adding a New Agent Node (Agent-Centric Structure)

**Directory Structure** (12-Factor Agents):

```
agent_orchestrator/agents/<agent_name>/
├── __init__.py              # Agent implementation (inherits from BaseAgent)
├── system.prompt.md         # System prompt with token budget
├── tools.yaml               # Tool access configuration
└── workflows/               # Agent-specific workflows
```

**Steps:**

1. **Create agent directory**: `agent_orchestrator/agents/<agent_name>/`
2. **Create `__init__.py`**: Define agent class inheriting from `_shared.base_agent.BaseAgent`

   ```python
   from pathlib import Path
   from .._shared.base_agent import BaseAgent

   class NewAgent(BaseAgent):
       def __init__(self, config_path: str = None):
           if config_path is None:
               config_path = str(Path(__file__).parent / "tools.yaml")
           super().__init__(str(config_path), agent_name="<agent_name>")
   ```

3. **Create `system.prompt.md`**: Define role, context window budget (8K max), output format, compression rules
4. **Create `tools.yaml`**: Specify model, temperature, max_tokens, allowed MCP servers
5. **Add node to LangGraph StateGraph** in `agent_orchestrator/graph.py`
6. **Update conditional edges** for supervisor routing
7. **Update `config/mcp-agent-tool-mapping.yaml`** with tool access
8. **Add LangSmith tracing** with project: `agents-<agent>`
9. **(Optional) Create agent-specific workflows** in `workflows/` subdirectory

**Key Principles**:

- **Locality of Behavior**: Everything for an agent in one directory
- **Version-Controlled Prompts**: `system.prompt.md` tracked in git
- **Tool Configuration**: `tools.yaml` specifies MCP server access
- **Shared Base**: All agents inherit from `_shared.base_agent.BaseAgent`
- **Cross-Cutting Tools**: Tool usage guides in `_shared/tool_guides/`

Note: Agent nodes are workflow steps, not separate containers. All nodes run within orchestrator service.

### MCP Servers

- Add new servers in `shared/mcp/servers/<server-name>/`; gateway auto-discovers tools via stdio communication.
- Update gateway routing if custom logic needed; maintain tool manifest in `shared/lib/agents-manifest.json`.

### Templates

- Pipeline generators: `support/templates/pipelines/`
- Documentation generators: `support/templates/docs/`
- Keep generated artifacts out of version control unless curated.

### Tool Binding Pattern (LangChain Integration)

To enable LLM function calling with MCP tools:

```python
# Step 1: Discover relevant tools (progressive disclosure)
from lib.progressive_mcp_loader import ToolLoadingStrategy
relevant_toolsets = progressive_loader.get_tools_for_task(
    task_description=user_request,
    strategy=ToolLoadingStrategy.MINIMAL
)

# Step 2: Convert MCP tools to LangChain BaseTool instances
langchain_tools = mcp_client.to_langchain_tools(relevant_toolsets)

# Step 3: Bind tools to LLM for function calling
llm_with_tools = gradient_client.get_llm_with_tools(
    tools=langchain_tools,
    temperature=0.7,
    max_tokens=2000
)

# Step 4: LLM can now INVOKE tools
from langchain_core.messages import HumanMessage, SystemMessage
messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
response = await llm_with_tools.ainvoke(messages)

# Check for tool calls
if hasattr(response, 'tool_calls') and response.tool_calls:
    # LLM requested tool invocations
    for tool_call in response.tool_calls:
        # Tool execution happens automatically in full agent loop
        pass
```

This pattern provides:

- 80-90% token reduction via progressive disclosure
- Actual tool execution via LangChain function calling
- Seamless MCP gateway integration
- Production-ready error handling

### Progressive MCP Tool Disclosure with LangChain Integration

- **Architecture**: LangChain-native tool binding inspired by `LLMToolSelectorMiddleware` pattern
- **Implementation**: 3-layer approach:
  1. **Discovery** (`shared/lib/progressive_mcp_loader.py`): Filter 150+ tools → 10-30 relevant tools
  2. **Conversion** (`shared/lib/mcp_client.py:to_langchain_tools()`): MCP schemas → LangChain `BaseTool` instances
  3. **Binding** (`shared/lib/gradient_client.py:get_llm_with_tools()`): Tools bound to LLM via `bind_tools()`
- **Key Innovation**: LLM can now **INVOKE** tools via function calling, not just see documentation
- **Orchestrator Integration**: Automatic in `decompose_with_llm()` during task decomposition
- **Token Savings**: 80-90% reduction (150+ tools → 10-30 tools per task)
- **Strategies**:
  - `MINIMAL`: Keyword-based (80-95% savings, recommended for simple tasks)
  - `AGENT_PROFILE`: Agent manifest-based (60-80% savings)
  - `PROGRESSIVE`: Minimal + high-priority agent tools (70-85% savings, default)
  - `FULL`: All 150+ tools (0% savings, debugging only)
- **Keyword Mappings**: 60+ keywords mapped to MCP servers in `keyword_to_servers` dict
- **Benefits**:
  - Reduced token costs (80-90% savings on tool context)
  - Actual tool execution via LangChain function calling
  - Seamless MCP gateway integration
  - Production-ready LangChain patterns

### Zen Pattern Integration (DEV-175, Completed November 2025)

**Overview:** Ported battle-tested patterns from Zen MCP Server (1000+ production conversations) to enhance event sourcing and workflow management.

**Completed Implementations:**

1. **Parent Workflow Chains** (`shared/lib/workflow_reducer.py` + `config/state/workflow_events.sql`):

   - Added `parent_workflow_id` field to `WorkflowEvent` dataclass
   - Implemented `get_workflow_chain(workflow_id, event_loader)` with circular detection
   - Recursive CTE view: `workflow_chains` for SQL-based traversal
   - Use case: PR deployment → hotfix workflow composition with complete audit trail
   - Migration: `SELECT migrate_parent_workflow_id();` (idempotent)

2. **Resource Deduplication** (`agent_orchestrator/workflows/workflow_engine.py`):

   - Newest-first priority: `_deduplicate_workflow_resources()` walks events backwards
   - **80-90% token savings** when files modified multiple times (Zen production proven)
   - Example: `docker-compose.yml` modified 5x → 1 file in context (5000 → 1000 tokens)
   - Metrics logged: "Deduplication saved X tokens (Y% reduction)"

3. **Workflow TTL Management** (`agent_orchestrator/workflows/workflow_engine.py` + `config/state/workflow_events.sql`):
   - Configuration: `WORKFLOW_TTL_HOURS=24` in `.env` (dev: 3h, staging: 12h, prod: 24h)
   - TTL refresh on every event: `_refresh_workflow_ttl()` called in `_persist_event()`
   - PostgreSQL table: `workflow_ttl` with `expires_at`, `refreshed_at`, `refresh_count`
   - Cleanup function: `SELECT * FROM cleanup_expired_workflows();` (cron hourly)
   - View: `active_workflows_with_ttl` shows TTL status for monitoring

**Implementation Stats:**

- Code: 300+ lines production code, 160+ lines SQL (migrations, views, functions)
- Tests: 55 unit tests across 3 test files (24 + 18 + 13)
- Linear Issues: DEV-175 (parent), DEV-176 (parent chains), DEV-177 (resource dedup), DEV-178 (TTL management)

**Key Files:**

- `shared/lib/workflow_reducer.py`: Parent chain traversal logic
- `agent_orchestrator/workflows/workflow_engine.py`: Deduplication + TTL management
- `config/state/workflow_events.sql`: Schema migrations and database functions
- `config/env/.env.template`: `WORKFLOW_TTL_HOURS` configuration
- `support/tests/unit/test_workflow_chains.py`: 24 test cases
- `support/tests/unit/test_resource_deduplication.py`: 18 test cases
- `support/tests/unit/test_workflow_ttl.py`: 13 test cases

**Deployment:**

1. Update `.env`: Set `WORKFLOW_TTL_HOURS` (24 for production)
2. Run SQL migrations: `psql $DATABASE_URL -f config/state/workflow_events.sql`
3. Deploy: `./support/scripts/deploy/deploy-to-droplet.ps1 -DeployType full`
4. Setup cron: `0 * * * * psql $DATABASE_URL -c "SELECT * FROM cleanup_expired_workflows();"`
5. Monitor: LangSmith traces show token savings, Grafana metrics track workflow lifecycle

**Future Enhancements (See Linear Backlog):**

- Dual prioritization strategy (DEV-167 dependency)
- Model context management improvements
- Provider registry for multi-LLM workflows
- Workflow conversation memory (planned Q2 2026)
- Continuation API for resumed workflows

## Quality bar

- **Typing**: Use Pydantic models, FastAPI dependency injection, type hints on all functions.
- **Health Endpoints**: Every agent must expose `GET /health` returning `{"status": "healthy", "mcp_gateway": "connected"/"disconnected"}`.
- **Observability**: All agents must initialize MCP client, Gradient client (if using LLM), LangSmith tracing (via LangChain), Prometheus metrics.
- **Error Handling**: Graceful fallback when API keys missing (use `gradient_client.is_enabled()` check before LLM calls).
- **Tool Integration**: Use LangChain tool binding (`bind_tools()`) for function calling, not text-only documentation. Convert MCP tools via `mcp_client.to_langchain_tools()`.
- **Shell Scripts**: POSIX-compliant bash, executable permissions, consistent logging format (echo + status lines).
- **Container Hygiene**: Treat Docker resources as disposable—tear down stray containers, prune layers after failures, and leave compose stacks either fully running or fully stopped.
- **Documentation Hygiene**:
  - **DO NOT create summary/completion markdown files** unless explicitly requested by user
  - Update existing docs in `support/docs/` when architecture changes
  - Use inline responses for status updates, not new files
  - Archive temporary/working files to `_archive/docs-temp/` after completion
  - Keep `support/docs/_temp/` clean - only active work-in-progress files
- **Linear Integration**:
  - When user says "update linear roadmap", update the **Linear project** via GraphQL API, NOT the markdown file
  - Use scripts: `update-linear-graphql.py` (update descriptions), `create-hitl-subtasks.py` (create issues), `mark-hitl-complete.py` (mark complete)
  - Set `$env:LINEAR_API_KEY="lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571"` before running
  - Update `LINEAR_PROGRESS_ASSESSMENT.md` only for internal tracking, Linear project for external visibility
- Pipeline or documentation generators should draw from `templates/pipelines` or `templates/docs`; keep generated artifacts out of version control unless curated.
- Update MCP behavior alongside any new model integrations by wiring config files into `mcp/gateway` and the `compose` service volume mounts.
