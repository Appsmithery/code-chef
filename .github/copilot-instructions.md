# Github Copilot Instructions for Dev-Tools

## Architecture snapshot (Phase 7 Complete)

- **Agent Layer**: 6 FastAPI-based agents under `agents/*` (orchestrator, feature-dev, code-review, infrastructure, cicd, documentation) with container builds in `containers/*` and Docker orchestration in `compose/docker-compose.yml`.
- **MCP Integration**: 150+ tools across 17 servers via MCP gateway at port 8000; each agent uses `agents/_shared/mcp_client.py` for unified tool access. Gateway routes to servers in `mcp/servers/`.
- **LLM Inference**: DigitalOcean Gradient AI integration via `agents/_shared/gradient_client.py` with per-agent model optimization (llama-3.1-70b for orchestrator/code-review, codellama-13b for feature-dev, llama-3.1-8b for infrastructure/cicd, mistral-7b for documentation).
- **Observability**: Langfuse automatic LLM tracing (langfuse.openai wrapper) + Prometheus HTTP metrics (prometheus-fastapi-instrumentator) on all agents.
- **Service Ports**: gateway-mcp:8000, orchestrator:8001, feature-dev:8002, code-review:8003, infrastructure:8004, cicd:8005, documentation:8006, rag:8007, state:8008, prometheus:9090.

## Configuration sources

- **Environment**: `config/env/.env` contains all production credentials (Langfuse keys, Gradient API key, Linear OAuth, DO PAT, database creds). Copy from `.env.example` and populate secrets.
- **Docker Secrets**: Linear OAuth tokens in `config/env/secrets/*.txt` mounted via Docker Compose secrets; run `./scripts/setup_secrets.sh` to create.
- **Agent Models**: Per-agent Gradient model configured in `compose/docker-compose.yml` via `GRADIENT_MODEL` env var; models optimized for task complexity and cost.
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

- **Automated**: `./scripts/deploy.ps1` (validates env, builds, deploys, health checks); use `-Target remote` for droplet deployment.
- **Manual**: `cd compose && docker-compose build && docker-compose up -d && docker-compose ps`
- **Health Checks**: Curl `/health` on ports 8000-8008; verify `{"status": "healthy"}` and `mcp_gateway: "connected"`.

### Local Development

- Use `make up|down|rebuild|logs` (wraps `scripts/*.sh`) or direct `docker-compose` commands; scripts assume bash and run from repo root.
- `./scripts/up.sh` brings stack online, waits 10s, prints health; `make logs-agent AGENT=<service>` for troubleshooting.
- Rebuild when Python deps change: `scripts/rebuild.sh` or `docker-compose build <service>`.
- Backups: `scripts/backup_volumes.sh` creates tarballs of `orchestrator-data`, `mcp-config`, `qdrant-data`, `postgres-data` under `./backups/<timestamp>`.
- Local overrides: `compose/docker-compose.override.yml` (gitignored sample sets DEBUG/LOG_LEVEL).

### Remote Deployment (DigitalOcean)

- Target droplet: `45.55.173.72` (alex@appsmithery.co)
- Deploy path: `/opt/Dev-Tools`
- Method 1: `./scripts/deploy.ps1 -Target remote` (copies .env, builds, deploys)
- Method 2: SSH + git pull + docker-compose commands (see `DEPLOY.md`)
- Verify: Check health endpoints, Langfuse traces, Prometheus metricsent with langfuse.openai wrapper.
- API key from `GRADIENT_API_KEY` env var (uses DigitalOcean PAT); base URL `https://api.digitalocean.com/v2/ai`.
- Per-agent models: orchestrator/code-review (70b), feature-dev (codellama-13b), infrastructure/cicd (8b), documentation (mistral-7b).
- Cost: $0.20-0.60/1M tokens (150x cheaper than GPT-4); <50ms latency within DO network.

### Langfuse (LLM Tracing)

- Automatic tracing via `langfuse.openai` wrapper in gradient_client; no explicit tracing code needed in agents.
- Captures prompts, completions, token counts, costs; grouped by `langfuse_session_id` (task_id), `langfuse_user_id` (agent_name).
- Dashboard: https://us.cloud.langfuse.com; keys in `.env` as `LANGFUSE_SECRET_KEY` and `LANGFUSE_PUBLIC_KEY`.

## Extension points

### Adding a New Agent

1. Create `agents/<agent>/main.py` (FastAPI app with Pydantic models)
2. Initialize shared clients: `mcp_client = MCPClient(agent_name="...")` and `gradient_client = get_gradient_client("...")`
3. Add Prometheus: `Instrumentator().instrument(app).expose(app)`
4. Create `containers/<agent>/Dockerfile` (copy pattern from existing agents)
5. Add service to `compose/docker-compose.yml` with env vars (GRADIENT*MODEL, LANGFUSE*\*, MCP_GATEWAY_URL)
6. Update `config/mcp-agent-tool-mapping.yaml` with tool access
7. Document endpoints in `docs/AGENT_ENDPOINTS.md`
8. Add requirements.txt with: `fastapi`, `uvicorn`, `pydantic`, `httpx`, `langfuse>=2.0.0`, `prometheus-fastapi-instrumentator>=6.1.0`

### MCP Servers

- Add new servers in `mcp/servers/<server-name>/`; gateway auto-discovers tools via stdio communication.
- Update gateway routing if custom logic needed; maintain tool manifest in `agents/agents-manifest.json`.

### Templates

- Pipeline generators: `templates/pipelines/`
- Documentation generators: `templates/docs/`
- Keep generated artifacts out of version control unless curated.

## Quality bar

- **Typing**: Use Pydantic models, FastAPI dependency injection, type hints on all functions.
- **Health Endpoints**: Every agent must expose `GET /health` returning `{"status": "healthy", "mcp_gateway": "connected"/"disconnected"}`.
- **Observability**: All agents must initialize MCP client, Gradient client (if using LLM), Langfuse tracing, Prometheus metrics.
- **Error Handling**: Graceful fallback when API keys missing (use `gradient_client.is_enabled()` check before LLM calls).
- **Shell Scripts**: POSIX-compliant bash, executable permissions, consistent logging format (echo + status lines).
- **Documentation**: Update relevant docs in `docs/` when changing architecture; maintain `docs/README.md` index.ps change.
- Backups are volume-level tarballs written by `scripts/backup_volumes.sh`, storing `orchestrator-data` and `mcp-config` snapshots under `./backups/<timestamp>`.
- Place local-only adjustments in `compose/docker-compose.override.yml`; the sample sets DEBUG/LOG_LEVEL for the orchestrator.

## Extension points

- When adding a new agent, mirror the pattern in `README.md`: create `agents/<agent>/` (FastAPI app), `containers/<agent>/Dockerfile`, add a service block to `compose/docker-compose.yml`, update routing rules, and document endpoints in `docs/AGENT_ENDPOINTS.md`.
- Pipeline or documentation generators should draw from `templates/pipelines` or `templates/docs`; keep generated artifacts out of version control unless curated.
- Update MCP behavior alongside any new model integrations by wiring config files into `mcp/gateway` and the `compose` service volume mounts.

## Quality bar

- Prefer typing, Pydantic models, and FastAPI routers consistent with existing requirements files; expose `/health` endpoints for every agent.
- Keep shell scripts POSIX-compliant (bash) and executable, and respect the existing logging format used by scripts (echo + status lines).
