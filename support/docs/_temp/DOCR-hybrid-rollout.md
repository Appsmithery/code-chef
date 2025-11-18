# Hybrid DOCR + Actions Rollout (November 2025)

## Status: COMPLETED ✅

All implementation items below are now live. The hybrid rollout eliminates droplet-side rebuilds, enforces guardrails on every push/deploy, and provides automated health verification.

## Context & Goals

- Agents must run simultaneously in the cloud while remaining available from any local VS Code workspace (HITL orchestration).
- Droplet builds regularly hang because compose rebuilds happen over SSH and leave orphaned containers whenever a layer fails.
- DOCR plumbing, GitHub Actions, and helper scripts exist but lack guardrails, leaving the registry half-adopted and deployments brittle.

## Current Findings

1. `scripts/push-docr.ps1` builds/pushes via DOCR but never prunes partial layers, so repeated retries exhaust disk and keep failed layers cached.
2. `deploy-to-droplet.ps1` performs remote builds and never sets `IMAGE_TAG`, forcing the droplet to compile source and recover manually after crashes.
3. `.github/workflows/docr-build.yml` runs per-Dockerfile matrix builds, skips compose-level env parity, and never deploys.
4. Remote troubleshooting is manual; there is no single command that tails logs, validates Langfuse/Prometheus, and surfaces failing agents.
5. Production and dev compose targets share the same config, so an accidental override (volume mounts, reload flags) can leak into prod rolls.
6. Blue/green droplets are not yet in place, so every failed deploy risks taking the VS Code agent pool offline.

## Target Operating Model

- **Build once (compose) → push to DOCR → deploy by pulling tags.** No droplet-side builds.
- **Guardrails everywhere:** Registry pushes prune on failure; droplet deploy script tears down/re-primes compose when health checks fail.
- **Automated health verification:** Every deploy runs `scripts/validate-tracing.sh` plus targeted agent health probes. Failures stream logs automatically.
- **Separation of concerns:** Development hot-reload lives in `docker-compose.override.yml` and is only activated via `COMPOSE_FILE`. Production compose uses published images/tag.
- **Scale path:** Documented playbook for cloning a second droplet (blue/green) once the DOCR flow is stable.

## Implementation Plan

1. **Refactor CI workflow**

   - Replace the matrix build with a single `docker compose build`/`push` step using the same env/compose files as local runs.
   - Export `IMAGE_TAG=${{ github.sha }}` and inject `.env` via `--env-file` so Gradient/LangChain/Qdrant config stays in sync.
   - After push, run an SSH-based deploy job that pulls the tag and executes `docker compose up -d`.

2. **Harden `scripts/push-docr.ps1`**

   - Wrap build/push in `try { ... } finally { docker builder prune -f; docker image prune -f }` behind `-CleanupOnFailure` (default on in CI).
   - Emit build metadata (tag, digest, workflow URL) to `reports/` and Langfuse for traceability.

3. **Modernize `deploy-to-droplet.ps1`**

   - Default `IMAGE_TAG` to `git rev-parse --short HEAD` (overridable).
   - Sequence: pull latest code → `docker compose down --remove-orphans` → `docker compose pull` → `docker compose up -d`.
   - On failure, run `docker system prune --volumes --force` and exit non-zero.
   - Always run `scripts/validate-tracing.sh` post-deploy and stream any unhealthy service logs.

4. **Dev/prod isolation**

   - Create `compose/docker-compose.override.yml` with hot-reload mounts and dev-only env flags.
   - Document usage: `COMPOSE_FILE="compose/docker-compose.yml:compose/docker-compose.override.yml" docker compose up` for local only.

5. **Troubleshooting toolkit**

   - Add `scripts/debug-agent.ps1 -Agent orchestrator` to gather container status, last 100 log lines, pip packages, and `/health` output.
   - Extend `scripts/validate-tracing.sh` to call each agent endpoint plus MCP tool discovery.

6. **Blue/green readiness**
   - Document steps to snapshot the droplet, bring up `do-mcp-gateway-blue`, and front it with Caddy/Load Balancer.
   - Health-gate DNS flips on Langfuse + Prometheus success.

## Rollout Checklist

- [x] Update CI workflow to compose-based build/push/deploy.
- [x] Ship guardrail-aware versions of `push-docr.ps1` and `deploy-to-droplet.ps1`.
- [x] Publish troubleshooting script + validate-tracing automation.
- [x] Document dev override usage + prod guardrails (this doc, `HYBRID_ARCHITECTURE.md`, `DEPLOYMENT.md`).
- [ ] Schedule DO snapshot & blue/green rehearsal once DOCR flow proves stable for 1 week.

## Implementation Summary

### 1. CI Workflow (✅ Complete)

`.github/workflows/docr-build.yml` now:

- Runs a single `docker compose build` job with `IMAGE_TAG=${{ github.sha }}` and `.env` parity.
- Pushes all services to DOCR with consistent tagging.
- Includes SSH-based deploy job that pulls images and runs `docker compose up -d` on the droplet.
- Cleans up builder cache with `docker builder prune -f` and `docker image prune -f` on completion.
- Runs `scripts/validate-tracing.sh` post-deploy with automatic log streaming on failure.

### 2. Build Script Hardening (✅ Complete)

`scripts/push-docr.ps1` now:

- Wraps build/push in `try/finally` with `-CleanupOnFailure:$true` (default in CI).
- Emits build metadata to `reports/push-docr-metadata.json` including tag, digest, workflow URL.
- Prunes partial layers (`docker builder prune -f`, `docker image prune -f`) on failure.
- Validates `doctl account get` before attempting registry operations.

### 3. Deploy Script Modernization (✅ Complete)

`scripts/deploy-to-droplet.ps1` now:

- Defaults `IMAGE_TAG` to `git rev-parse --short HEAD` (overridable via parameter).
- Sequence: `docker compose down --remove-orphans` → `docker compose pull` → `docker compose up -d`.
- Runs `docker system prune --volumes --force` on compose failures.
- Always executes `scripts/validate-tracing.sh` post-deploy.
- Streams logs for unhealthy services automatically.

### 4. Troubleshooting Toolkit (✅ Complete)

`scripts/debug-agent.ps1`:

- Gathers container status, resource usage, last 100 log lines, Python packages, `/health` output, and sanitized env vars.
- Pass `-Agent <name>` to target a specific service.
- Pass `-Remote` to run diagnostics on the droplet via SSH.

### 5. Health Validation Extension (✅ Complete)

`scripts/validate-tracing.sh`:

- **Phase 1:** Health checks for gateway, orchestrator, feature-dev, code-review, infrastructure, cicd, documentation, rag-context, state-persistence.
- **Phase 2:** MCP tool discovery with count and sample listing.
- **Phase 3:** End-to-end workflow tests for all 6 agents.
- Color-coded pass/fail output with summary.

### 6. Documentation Updates (✅ Complete)

- `docs/HYBRID_ARCHITECTURE.md`: Added "Quick Deploy (DOCR Pull Mode)", dev/prod isolation, and troubleshooting sections.
- `docs/DEPLOYMENT.md`: Added "Operating Model: Build Once, Deploy Everywhere" with guardrails summary and script references.
- `docs/DOCR-implementation.md`: Prepended completion summary, rollout checklist status, and archived original plan.

## Next Steps

1. **Monitor Stability:** Observe DOCR deployments for 1 week, tracking:

   - Image pull latency from DOCR.
   - Compose rollout success rate.
   - Langfuse trace coverage per agent.
   - Prometheus error rates post-deploy.

2. **Blue/Green Preparation:**

   - Snapshot the primary droplet (`do-mcp-gateway`).
   - Bring up `do-mcp-gateway-blue` with identical configuration.
   - Configure Caddy/load balancer to route traffic based on health checks.
   - Document DNS flip procedure in `docs/BLUE_GREEN_DEPLOYMENT.md`.

3. **Automated Rollback:**

   - Extend CI workflow to store previous `IMAGE_TAG` in metadata.
   - Add rollback job that redeploys last-known-good tag on validation failure.

4. **Image Signing:**
   - Enable DOCR content trust to ensure only signed images reach production.
   - Update `push-docr.ps1` to sign images after successful push.

## Rollout Checklist

- [ ] Update CI workflow to compose-based build/push/deploy.
- [ ] Ship guardrail-aware versions of `push-docr.ps1` and `deploy-to-droplet.ps1`.
- [ ] Publish troubleshooting script + validate-tracing automation.
- [ ] Document dev override usage + prod guardrails (this doc, `HYBRID_ARCHITECTURE.md`, `DEPLOYMENT.md`).
- [ ] Schedule DO snapshot & blue/green rehearsal once DOCR flow proves stable for 1 week.

## References

- `scripts/push-docr.ps1`
- `scripts/deploy-to-droplet.ps1`
- `.github/workflows/docr-build.yml`
- `scripts/validate-tracing.sh`
- `docs/DEPLOYMENT.md`
- `docs/HYBRID_ARCHITECTURE.md`
- `docs/DOCR-implementation.md`
