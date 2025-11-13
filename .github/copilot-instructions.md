# Github Copilot Instructions for Dev-Tools

## Architecture snapshot

- Single repo bundling FastAPI-based agents under `agents/*`, container builds under `containers/*`, and Docker orchestration in `compose/docker-compose.yml`.
- Each agent has a matching service in compose exposing ports 8001-8006 and reads FastAPI deps from its `requirements.txt`; implement REST handlers in `agents/<name>/main.py`.
- `mcp/gateway/gateway.py` should expose the MCP HTTP bridge that routes to downstream servers listed in `mcp/servers/`; keep routing logic parallel with agent endpoints in `docs/AGENT_ENDPOINTS.md`.

## Configuration sources

- Copy `configs/env/.env.example` to `.env` for service URLs and DB credentials; secrets live in `configs/env/secrets.template.json`.
- Task routing rules belong in `configs/routing/task-router.rules.yaml`; prioritize explicit patterns before the catch-all orchestrator rule.
- `configs/rag/indexing.yaml` + `configs/rag/vectordb.config.yaml` define RAG sources and embedding targets; update both when adding new corpora or providers.
- Persistent workflow state is PostgreSQL-backed using `configs/state/schema.sql`; migrate schema by extending this file and rebuilding the stack.
- Secrets are surfaced to containers via Docker Compose secrets in `configs/env/secrets/*.txt`; run `./scripts/setup_secrets.sh` locally (gitignored) and set matching GitHub Actions repo secrets for CI/CD.

## Linear roadmap access

- Gateway service exposes `/oauth/linear/install` (initiate OAuth) and `/oauth/linear/status` (check token). Issues live under `/api/linear-issues`; project snapshots via `/api/linear-project/:projectId`.
- Tokens resolve from `LINEAR_*` envs or their `*_FILE` counterparts; keep `configs/env/secrets/linear_oauth_token.txt` up to date and never commit raw `.env` secrets.
- To track progress, authorize once per workspace, then poll the above endpoints or integrate against `services/linear.js` helpers for programmatic access.

## Local workflows

- Preferred entrypoint is `make up|down|rebuild|logs` which wrap the scripts in `scripts/`; scripts assume GNU tools and run from repo root.
- `./scripts/up.sh` brings the entire compose stack online, waits 10s, then prints health info; use `make health` or curl the `/health` probes listed in `README.md`.
- Use `make logs-agent AGENT=<service>` or `docker-compose logs -f <service>` for troubleshooting, and `scripts/rebuild.sh` when Python deps change.
- Backups are volume-level tarballs written by `scripts/backup_volumes.sh`, storing `orchestrator-data` and `mcp-config` snapshots under `./backups/<timestamp>`.
- Place local-only adjustments in `compose/docker-compose.override.yml`; the sample sets DEBUG/LOG_LEVEL for the orchestrator.

## Extension points

- When adding a new agent, mirror the pattern in `README.md`: create `agents/<agent>/` (FastAPI app), `containers/<agent>/Dockerfile`, add a service block to `compose/docker-compose.yml`, update routing rules, and document endpoints in `docs/AGENT_ENDPOINTS.md`.
- Pipeline or documentation generators should draw from `templates/pipelines` or `templates/docs`; keep generated artifacts out of version control unless curated.
- Update MCP behavior alongside any new model integrations by wiring config files into `mcp/gateway` and the `compose` service volume mounts.

## Quality bar

- Prefer typing, Pydantic models, and FastAPI routers consistent with existing requirements files; expose `/health` endpoints for every agent.
- Keep shell scripts POSIX-compliant (bash) and executable, and respect the existing logging format used by scripts (echo + status lines).
