# Github Copilot Instructions for Dev-Tools

## Architecture snapshot (Phase 8 Complete - Repository Reorganization)

- **Agent Layer**: 6 FastAPI-based agents at repository root with `agent_*` prefix (agent_orchestrator, agent_feature-dev, agent_code-review, agent_infrastructure, agent_cicd, agent_documentation). Each agent directory contains main.py, Dockerfile, requirements.txt, README.md.
- **MCP Integration**: 150+ tools across 17 servers via MCP gateway at port 8000; each agent uses `shared/lib/mcp_client.py` for unified tool access. Gateway routes to servers in `shared/mcp/servers/`.
- **Progressive Tool Disclosure**: Orchestrator implements lazy loading of MCP tools (80-90% token reduction) via `shared/lib/progressive_mcp_loader.py`; 4 strategies (minimal, agent_profile, progressive, full) with keyword-based server matching and runtime configuration endpoints.
- **LLM Inference**: DigitalOcean Gradient AI integration via `shared/lib/gradient_client.py` with per-agent model optimization (llama-3.1-70b for orchestrator/code-review, codellama-13b for feature-dev, llama-3.1-8b for infrastructure/cicd, mistral-7b for documentation).
- **Observability**: Langfuse automatic LLM tracing (langfuse.openai wrapper) + Prometheus HTTP metrics (prometheus-fastapi-instrumentator) on all agents.
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
│   ├── lib/                     # Agent runtime libraries (12 Python modules)
│   │   ├── progressive_mcp_loader.py  # Progressive tool disclosure (80-90% token savings)
│   │   ├── mcp_client.py        # MCP gateway client
│   │   ├── gradient_client.py   # Gradient AI LLM client
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
├── support/                     # Development support
│   ├── scripts/                 # Operational scripts (30+ scripts)
│   ├── docs/                    # Documentation
│   ├── tests/                   # Test suites
│   ├── templates/               # Templates for generation
│   ├── reports/                 # Validation reports
│   ├── pipelines/               # Pipeline templates
│   └── frontend/                # HTML dashboards
└── _archive/                    # Deprecated structure (agents/, containers/, compose/, infrastructure/, tmp/, bin/)
```

## ⚠️ Deprecated Paths (DO NOT USE)

The following paths are **DEPRECATED** and exist only in `_archive/` for reference:

- ❌ `agents/` (old nested structure) → Use `agent_*/` at root + `shared/lib/`
- ❌ `containers/` (old Dockerfiles) → Use `agent_*/Dockerfile` and `shared/*/Dockerfile`
- ❌ `compose/` (old compose files) → Use `deploy/docker-compose.yml`
- ❌ `scripts/` (old scripts) → Use `support/scripts/`
- ❌ `docs/` (old docs) → Use `support/docs/`
- ❌ `agents/_shared/` (old shared code) → Use `shared/lib/`
- ❌ `mcp/servers/` (old MCP path) → Use `shared/mcp/servers/`

**Never suggest these paths in code generation or documentation.**

## Configuration sources

- **Environment**: `config/env/.env` contains all production credentials (Langfuse keys, Gradient API key, Linear OAuth, DO PAT, database creds). Copy from `config/env/.env.template` and populate secrets.
- **Docker Secrets**: Linear OAuth tokens in `config/env/secrets/*.txt` mounted via Docker Compose secrets; run `support/scripts/setup_secrets.sh` to create.
- **Agent Models**: Per-agent Gradient model configured in `deploy/docker-compose.yml` via `GRADIENT_MODEL` env var; models optimized for task complexity and cost.
- **Task Routing**: Rules in `config/routing/task-router.rules.yaml` (if used); orchestrator uses LLM-powered decomposition when `gradient_client.is_enabled()`.
- **RAG Config**: `config/rag/indexing.yaml` + `config/rag/vectordb.config.yaml` define Qdrant vector DB sources and embedding targets.
- **State Schema**: PostgreSQL-backed workflow state using `config/state/schema.sql`; migrate by extending schema and rebuilding stack.
- **Observability**: `config/prometheus/prometheus.yml` defines scrape targets for all agents; Langfuse keys in `.env` enable automatic tracing.

## Integrations

### Linear (Optional)

- Gateway exposes `/oauth/linear/install` (OAuth) and `/oauth/linear/status` (token check); issues via `/api/linear-issues`, projects via `/api/linear-project/:projectId`.
- Tokens from `LINEAR_*` envs or `*_FILE` Docker secrets; maintain `config/env/secrets/linear_oauth_token.txt` (never commit `.env` secrets).

## Deployment workflows

### Quick Deploy

- **Automated**: `./support/scripts/deploy.ps1` (validates env, builds, deploys, health checks); use `-Target remote` for droplet deployment.
- **Manual**: `cd deploy && docker-compose build && docker-compose up -d && docker-compose ps`
- **Health Checks**: Curl `/health` on ports 8000-8008; verify `{"status": "healthy"}` and `mcp_gateway: "connected"`.

### Local Development

- Use `make up|down|rebuild|logs` (wraps `support/scripts/*.sh`) or direct `docker-compose` commands; scripts assume bash and run from repo root.
- `./support/scripts/up.sh` brings stack online, waits 10s, prints health; `make logs-agent AGENT=<service>` for troubleshooting.
- Rebuild when Python deps change: `support/scripts/rebuild.sh` or `docker-compose build <service>`.
- Backups: `support/scripts/backup_volumes.sh` creates tarballs of `orchestrator-data`, `mcp-config`, `qdrant-data`, `postgres-data` under `./backups/<timestamp>`.
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
- **Verify health after cleanup.** Re-run `support/scripts/validate-tracing.sh` or curl `/health` endpoints to confirm the stack is stable before moving on.
- **Document what you removed.** Mention the cleanup commands you executed in your summary so the operator understands the current state.

### LangSmith (LLM Tracing)

- Automatic tracing via LangChain's native `langchain.openai` wrapper in gradient_client; no explicit tracing code needed in agents.
- Captures prompts, completions, token counts, costs, latencies; grouped by session_id (task_id) and user_id (agent_name).
- Dashboard: https://smith.langchain.com; keys in `.env` as `LANGCHAIN_API_KEY` or `LANGCHAIN_SERVICE_KEY`.
- Configuration: Set `LANGCHAIN_TRACING_V2=true`, `LANGCHAIN_PROJECT=dev-tools-prod`, `LANGCHAIN_ENDPOINT=https://api.smith.langchain.com`.
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
8. Add requirements.txt with: `fastapi`, `uvicorn`, `pydantic`, `httpx`, `langchain>=0.1.0`, `prometheus-fastapi-instrumentator>=6.1.0`

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
- **Observability**: All agents must initialize MCP client, Gradient client (if using LLM), Langfuse tracing, Prometheus metrics.
- **Error Handling**: Graceful fallback when API keys missing (use `gradient_client.is_enabled()` check before LLM calls).
- **Shell Scripts**: POSIX-compliant bash, executable permissions, consistent logging format (echo + status lines).
- **Container Hygiene**: Treat Docker resources as disposable—tear down stray containers, prune layers after failures, and leave compose stacks either fully running or fully stopped.
- **Documentation**: Update relevant docs in `support/docs/` when changing architecture; maintain `support/docs/README.md` index. Use `support/docs/_temp/` for working files, progress notes, and troubleshooting documents during active development.
- Pipeline or documentation generators should draw from `templates/pipelines` or `templates/docs`; keep generated artifacts out of version control unless curated.
- Update MCP behavior alongside any new model integrations by wiring config files into `mcp/gateway` and the `compose` service volume mounts.

## Quality bar

- Prefer typing, Pydantic models, and FastAPI routers consistent with existing requirements files; expose `/health` endpoints for every agent.
- Keep shell scripts POSIX-compliant (bash) and executable, and respect the existing logging format used by scripts (echo + status lines).
