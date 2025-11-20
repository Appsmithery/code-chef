# Github Copilot Instructions for Dev-Tools

## Architecture snapshot

**Production Status**: Multi-agent DevOps automation platform running on DigitalOcean (droplet: 45.55.173.72)

- **Agent Layer**: 6 FastAPI-based agents at repository root with `agent_*` prefix (agent_orchestrator, agent_feature-dev, agent_code-review, agent_infrastructure, agent_cicd, agent_documentation). Each agent directory contains main.py, Dockerfile, requirements.txt, README.md.
- **MCP Integration**: 150+ tools across 17 servers via MCP gateway at port 8000; each agent uses `shared/lib/mcp_client.py` for unified tool access. Gateway routes to servers in `shared/mcp/servers/`.
- **Progressive Tool Disclosure**: Orchestrator implements lazy loading of MCP tools (80-90% token reduction) via `shared/lib/progressive_mcp_loader.py`; 4 strategies (minimal, agent_profile, progressive, full) with keyword-based server matching and runtime configuration endpoints.
- **LLM Inference**: DigitalOcean Gradient AI integration via LangChain wrappers (`shared/lib/gradient_client.py`, `shared/lib/langchain_gradient.py`) with per-agent model optimization (llama-3.1-70b for orchestrator/code-review, codellama-13b for feature-dev, llama-3.1-8b for infrastructure/cicd, mistral-7b for documentation).
- **Observability**: LangSmith automatic LLM tracing (all 6 agents + workflows) + Prometheus HTTP metrics (prometheus-fastapi-instrumentator) on all agents. Complete observability: LLM traces → LangSmith, HTTP metrics → Prometheus, state → PostgreSQL, vectors → Qdrant.
- **Notification System**: Event-driven approval notifications via `shared/lib/event_bus.py` (async pub/sub); Linear workspace client posts to PR-68 hub with @mentions; <1s latency; optional email fallback via SMTP.
- **Copilot Integration**: Natural language task submission via `/chat` endpoint; multi-turn conversations with PostgreSQL session management; real-time approval notifications (<1s latency); OAuth integration with Linear GraphQL API.
- **Service Ports**: gateway-mcp:8000, orchestrator:8001, feature-dev:8002, code-review:8003, infrastructure:8004, cicd:8005, documentation:8006, rag:8007, state:8008, prometheus:9090.

## Repository structure

```
Dev-Tools/
├── agent_orchestrator/          # Orchestrator agent (root-level, no nesting)
├── agent_feature-dev/           # Feature development agent
├── agent_code-review/           # Code review agent
├── agent_infrastructure/        # Infrastructure agent
├── agent_cicd/                  # CI/CD agent
├── agent_documentation/         # Documentation agent
├── shared/                      # Shared runtime components
│   ├── lib/                     # Agent runtime libraries (15+ Python modules)
│   │   ├── progressive_mcp_loader.py  # Progressive tool disclosure (80-90% token savings)
│   │   ├── mcp_client.py        # MCP gateway client
│   │   ├── gradient_client.py   # Gradient AI LLM client
│   │   ├── event_bus.py         # Async pub/sub event routing (notification system)
│   │   ├── linear_workspace_client.py  # Linear GraphQL API client (OAuth)
│   │   ├── notifiers/           # Event subscribers (Linear, Email)
│   │   └── ...                  # Other shared modules
│   ├── services/                # Backend microservices (rag, state, langgraph)
│   ├── gateway/                 # MCP gateway for tool routing
│   ├── mcp/                     # MCP servers (17 servers)
│   └── context/                 # MCP server context data
├── deploy/                      # Deployment orchestration
│   ├── docker-compose.yml       # Service definitions
│   ├── workflows/               # CI/CD workflows
│   └── .env.template            # Environment template
├── config/                      # Runtime configuration
│   ├── env/                     # Environment variables
│   ├── caddy/                   # Reverse proxy config
│   ├── prometheus/              # Metrics config
│   ├── rag/                     # RAG config
│   ├── state/                   # State schema
│   └── routing/                 # Task routing rules
└── support/                     # Development support
    ├── scripts/                 # Operational scripts (30+ scripts)
    ├── docs/                    # Documentation
    ├── tests/                   # Test suites
    ├── templates/               # Templates for generation
    ├── reports/                 # Validation reports
    ├── pipelines/               # Pipeline templates
    └── frontend/                # HTML dashboards
```

## ⚠️ Deprecated Paths (REMOVED - November 20, 2025)

The `_archive/` directory has been **PERMANENTLY REMOVED** from the main branch as of November 20, 2025.

**All imports have been updated to current structure:**

- ✅ `agents._shared.*` → `shared.lib.*`
- ✅ `agents.<agent>.*` → `agent_<agent>.*` (with sys.path for hyphenated names)
- ✅ All deprecated paths cleaned up (0 violations)
- ✅ Docker environment pruned (8GB freed)
- ✅ Repository optimized (~8.1GB reduction)

**Historical Reference**: Archive contents moved to `archive/historical` branch for reference.

**Never suggest `_archive/`, `agents/`, `containers/`, or `compose/` paths in code generation or documentation.**

## Configuration sources

- **Environment**: `config/env/.env` contains all production credentials (LangSmith API key, Gradient model access key, Linear OAuth, DO PAT, database creds). Copy from `config/env/.env.template` and populate secrets.
- **Docker Secrets**: Linear OAuth tokens in `config/env/secrets/*.txt` mounted via Docker Compose secrets; run `support/scripts/setup_secrets.sh` to create.
- **Agent Models**: Per-agent Gradient model configured in `deploy/docker-compose.yml` via `GRADIENT_MODEL` env var; models optimized for task complexity and cost.
- **Task Routing**: Rules in `config/routing/task-router.rules.yaml` (if used); orchestrator uses LLM-powered decomposition when `gradient_client.is_enabled()`.
- **RAG Config**: `config/rag/indexing.yaml` + `config/rag/vectordb.config.yaml` define Qdrant vector DB sources and embedding targets.
- **State Schema**: PostgreSQL-backed workflow state using `config/state/schema.sql`; migrate by extending schema and rebuilding stack.
- **Observability**: `config/prometheus/prometheus.yml` defines scrape targets for all agents; LangSmith keys in `.env` enable automatic tracing.

## Integrations

### Linear (OAuth + Notifications)

- Gateway exposes `/oauth/linear/install` (OAuth) and `/oauth/linear/status` (token check); issues via `/api/linear-issues`, projects via `/api/linear-project/:projectId`.
- Tokens from `LINEAR_*` envs or `*_FILE` Docker secrets; maintain `config/env/secrets/linear_oauth_token.txt` (never commit `.env` secrets).
- **Linear Integration - Two Separate Workflows**:
  1. **Roadmap Management (Project-Specific)**: Use `support/scripts/linear/agent-linear-update.py` with `--project-id` parameter. Sub-agents update their assigned project only; Orchestrator can update any project.
  2. **HITL Approvals (Workspace-Wide)**: Use orchestrator event bus → PR-68. All agents can request approvals via events.
- **Update Linear Roadmap**: When user says "update linear roadmap", they mean update the **Linear project issues** (not the markdown file). Use `agent-linear-update.py` with `--project-id` and `LINEAR_API_KEY` env var (OAuth token: `lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571`).
- **Sub-Issue Requirements**: Break down complex features into 3-5 sub-tasks using `agent-linear-update.py create-phase --project-id "UUID"`. Always set appropriate status (todo/in_progress/done) when creating/updating issues.
- **Status Management**: Retrospective updates should be marked "done". Use `agent-linear-update.py update-status --issue-id "PR-XX" --status "done"` for completed work.
- **Access Control**: Sub-agents MUST pass `--project-id` for their assigned project. Orchestrator can omit for default (AI DevOps Agent Platform) or specify any project UUID.
- **Approval Notifications**: Orchestrator posts approval requests to Linear workspace hub (PR-68) via `linear_workspace_client.py`; events emitted via `event_bus.py`; <1s latency; native Linear notifications (email/mobile/desktop). Configure: `LINEAR_APPROVAL_HUB_ISSUE_ID=PR-68` in `.env`.
- **Project UUID**: AI DevOps Agent Platform = `b21cbaa1-9f09-40f4-b62a-73e0f86dd501` (slug: `78b3b839d36b`)
- **Team ID**: Project Roadmaps (PR) = `f5b610be-ac34-4983-918b-2c9d00aa9b7a`
- **Approval Hub Issue**: PR-68 (workspace-level approval notification hub - for HITL only)
- **Phase 6 Issue**: PR-85 (Multi-Agent Collaboration completion)

## Deployment workflows

### ⚠️ Configuration Changes Deployment (CRITICAL)

**The droplet is connected to the main repo branch.** Configuration changes in `config/env/.env` require a specific workflow:

1. **Update Local `.env`**: Edit `config/env/.env` with new configuration
2. **Update Template** (if applicable): Sync changes to `config/env/.env.template` if adding new variables
3. **Commit Template**: `git add config/env/.env.template && git commit && git push` (`.env` is gitignored)
4. **Deploy to Droplet**:
   ```bash
   scp config/env/.env root@45.55.173.72:/opt/Dev-Tools/config/env/.env
   ssh root@45.55.173.72 "cd /opt/Dev-Tools && git pull origin main && cd deploy && docker compose down && docker compose up -d"
   ```
5. **Verify**: Check health endpoints and verify environment variables loaded correctly

**Why This Matters**: Docker Compose reads `.env` at startup. Simple `docker compose restart` does NOT reload environment variables from disk. You must use `down && up` to pick up `.env` changes.

### Quick Deploy

- **Automated**: `./support/scripts/deploy.ps1` (validates env, builds, deploys, health checks); use `-Target remote` for droplet deployment.
- **Manual**: `cd deploy && docker-compose build && docker-compose up -d && docker-compose ps`
- **Health Checks**: Curl `/health` on ports 8000-8008; verify `{"status": "healthy"}` and `mcp_gateway: "connected"`.

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
- Per-agent models: orchestrator/code-review (70b), feature-dev (codellama-13b), infrastructure/cicd (8b), documentation (mistral-7b).
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

### Container Hygiene & Cleanup (Required)

- **Never leave failed containers running.** After experiments or interrupted builds, run `docker compose down --remove-orphans` before handing control back to the user.
- **Prune on errors.** If a compose build/push/deploy fails, follow up with `docker builder prune -f`, `docker image prune -f`, and (when on the droplet) `docker system prune --volumes --force` unless the user explicitly says otherwise.
- **Verify health after cleanup.** Re-run `support/scripts/validation/validate-tracing.sh` or curl `/health` endpoints to confirm the stack is stable before moving on.
- **Document what you removed.** Mention the cleanup commands you executed in your summary so the operator understands the current state.

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
- **Deprecation Note**: Langfuse has been replaced by LangSmith for all tracing functionality. Remove any `LANGFUSE_*` environment variables.

## Extension points

### Adding a New Agent

1. Create `agent_<agent>/main.py` (FastAPI app with Pydantic models)
2. Initialize shared clients: `mcp_client = MCPClient(agent_name="...")` and `gradient_client = get_gradient_client("...")`
3. Add Prometheus: `Instrumentator().instrument(app).expose(app)`
4. Create `agent_<agent>/Dockerfile` (copy pattern from existing agents)
5. Add service to `deploy/docker-compose.yml` with env vars (`GRADIENT_MODEL`, `PORT`, `MCP_GATEWAY_URL`)
6. Update `config/mcp-agent-tool-mapping.yaml` with tool access
7. Document endpoints in `support/docs/AGENT_ENDPOINTS.md`

- Add requirements.txt with: `fastapi`, `uvicorn`, `pydantic`, `httpx`, `langchain>=0.1.0`, `langchain-openai>=0.1.0`, `langsmith>=0.1.0`, `prometheus-fastapi-instrumentator>=6.1.0`

### MCP Servers

- Add new servers in `shared/mcp/servers/<server-name>/`; gateway auto-discovers tools via stdio communication.
- Update gateway routing if custom logic needed; maintain tool manifest in `shared/lib/agents-manifest.json`.

### Templates

- Pipeline generators: `support/templates/pipelines/`
- Documentation generators: `support/templates/docs/`
- Keep generated artifacts out of version control unless curated.

### Progressive MCP Tool Disclosure

- **Implementation**: `shared/lib/progressive_mcp_loader.py` with 4 loading strategies
- **Orchestrator Integration**: Automatic lazy loading in `/orchestrate` endpoint
- **Token Savings**: 80-90% reduction (150+ tools → 10-30 tools per task)
- **Configuration**: Runtime strategy changes via `POST /config/tool-loading`
- **Monitoring**: Token usage stats via `GET /config/tool-loading/stats`
- **Strategies**:
  - `MINIMAL`: Keyword-based (80-95% savings, recommended for simple tasks)
  - `AGENT_PROFILE`: Agent manifest-based (60-80% savings)
  - `PROGRESSIVE`: Minimal + high-priority agent tools (70-85% savings, default)
  - `FULL`: All 150+ tools (0% savings, debugging only)
- **Keyword Mappings**: 60+ keywords mapped to MCP servers in `keyword_to_servers` dict
- **Extension**: Apply pattern to other agents by importing `get_progressive_loader()` and calling `get_tools_for_task()`
- **Documentation**: `support/docs/_temp/progressive-mcp-disclosure-implementation.md`

## Quality bar

- **Typing**: Use Pydantic models, FastAPI dependency injection, type hints on all functions.
- **Health Endpoints**: Every agent must expose `GET /health` returning `{"status": "healthy", "mcp_gateway": "connected"/"disconnected"}`.
- **Observability**: All agents must initialize MCP client, Gradient client (if using LLM), LangSmith tracing (via LangChain), Prometheus metrics.
- **Error Handling**: Graceful fallback when API keys missing (use `gradient_client.is_enabled()` check before LLM calls).
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
