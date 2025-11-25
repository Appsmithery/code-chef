# Dev-Tools Deployment Guide

**Version:** v0.3  
**Status:**  Production Ready  
**Last Updated:** November 25, 2025

See [QUICKSTART.md](QUICKSTART.md) for local setup | [ARCHITECTURE.md](ARCHITECTURE.md) for system design

---

## Quick Reference

### Deploy Commands

```powershell
# Auto-detect changes and deploy (recommended)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType auto

# Config-only (30s - for .env changes)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config

# Full rebuild (10min - for code changes)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType full

# Rollback to previous commit
.\support\scripts\deploy\deploy-to-droplet.ps1 -Rollback
```

### Health Checks

```bash
# Production (45.55.173.72)
curl http://45.55.173.72:8001/health  # Orchestrator
curl http://45.55.173.72:8000/health  # Gateway
curl http://45.55.173.72:8007/health  # RAG
curl http://45.55.173.72:8008/health  # State
```

Expected: `{"status": "healthy", "mcp_gateway": "connected"}`

---

## Deployment Strategies

| Change Type            | Strategy | Duration | Command                                        |
| ---------------------- | -------- | -------- | ---------------------------------------------- |
| .env or config YAML    | `config` | 30s      | `deploy-to-droplet.ps1 -DeployType config`     |
| Python code/Dockerfile | `full`   | 10min    | `deploy-to-droplet.ps1 -DeployType full`       |
| Documentation only     | `quick`  | 15s      | `deploy-to-droplet.ps1 -DeployType quick`      |
| Not sure               | `auto`   | varies   | `deploy-to-droplet.ps1 -DeployType auto`       |

---

## Config Strategy (Environment Changes)

**When:** Only `config/env/.env` or YAML config files changed

**What it does:**

1. Uploads `.env` to droplet via SCP
2. Runs `git pull origin main`
3. Runs `docker compose down && docker compose up -d` (CRITICAL)
4. Validates health endpoints

 **Why down+up?** Docker Compose only reads `.env` at startup. Simple `restart` does NOT reload environment variables.

**Example:**

```powershell
# Edit config/env/.env locally
# Update LANGSMITH_API_KEY or LINEAR_OAUTH_TOKEN

# Deploy
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config
```

---

## Full Strategy (Code Changes)

**When:** Python code, Dockerfiles, or requirements.txt changed

**What it does:**

1. Ensures local changes committed and pushed
2. Uploads `.env` to droplet
3. Runs `git pull origin main` on droplet
4. Runs `docker compose down --remove-orphans`
5. Runs `docker compose build --no-cache`
6. Runs `docker compose up -d`
7. Validates health endpoints

**Example:**

```powershell
# Make code changes
git add .
git commit -m "feat: Add new HITL workflow"
git push origin main

# Deploy
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType full
```

---

## Auto Strategy (Recommended)

**When:** Not sure what changed

**What it does:**

- Detects file changes via git diff
- Chooses optimal strategy automatically
- Falls back to `full` if uncertain

**Example:**

```powershell
# Make any changes, commit, push
git add .
git commit -m "chore: Update agent models"
git push origin main

# Auto-deploy
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType auto
```

---

## Production Environment

### Target Droplet

- **IP:** 45.55.173.72
- **User:** root
- **Deploy Path:** /opt/Dev-Tools
- **Resources:** 4GB RAM, 2 vCPUs, 80GB SSD

### Services

| Service      | Port | Container Name         |
| ------------ | ---- | ---------------------- |
| orchestrator | 8001 | deploy-orchestrator-1  |
| gateway-mcp  | 8000 | deploy-gateway-mcp-1   |
| rag-context  | 8007 | deploy-rag-context-1   |
| state        | 8008 | deploy-state-1         |
| postgres     | 5432 | deploy-postgres-1      |

### Networking

- **Bridge Network:** `devtools-network`
- **Internal DNS:** Services resolve by name (e.g., `postgres:5432`)
- **External Access:** Ports exposed to 0.0.0.0

---

## Configuration Management

### Environment Variables

**Critical variables in `config/env/.env`:**

```bash
# LangSmith Tracing
LANGSMITH_API_KEY=lsv2_sk_***
LANGSMITH_WORKSPACE_ID=5029c640-3f73-480c-82f3-58e402ed4207

# DigitalOcean Gradient AI
GRADIENT_API_KEY=<do-pat>

# Linear Integration
LINEAR_API_KEY=lin_oauth_***
LINEAR_TEAM_ID=f5b610be-ac34-4983-918b-2c9d00aa9b7a

# Database
DB_PASSWORD=<secure-password>
POSTGRES_PASSWORD=<secure-password>
```

### Docker Secrets

**Mounted as files in `/run/secrets/`:**

```yaml
secrets:
  linear_oauth_token:
    file: ../config/env/secrets/linear_oauth_token.txt
  github_pat:
    file: ../config/env/secrets/github_pat.txt
```

**Create secrets:**

```bash
# Run setup script
./support/scripts/setup_secrets.sh

# Or manually
echo "lin_oauth_***" > config/env/secrets/linear_oauth_token.txt
echo "ghp_***" > config/env/secrets/github_pat.txt
```

---

## Deployment Workflow

### Pre-Deployment Checklist

- [ ] All changes committed and pushed to `origin/main`
- [ ] `config/env/.env` populated with production secrets
- [ ] Docker secrets created (`setup_secrets.sh`)
- [ ] SSH access to droplet verified (`ssh root@45.55.173.72`)
- [ ] Backup tag created (`git tag pre-deploy-$(date +%Y%m%d)`)

### Deploy Process

```powershell
# 1. Create backup tag
git tag -a pre-deploy-$(Get-Date -Format yyyyMMdd) -m "Backup before deploy"
git push origin --tags

# 2. Choose deployment strategy
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType auto

# 3. Monitor deployment
# - Script shows real-time progress
# - Health checks validate services
# - Automatic rollback on failure

# 4. Verify in production
curl http://45.55.173.72:8001/health
curl http://45.55.173.72:8000/health
```

### Post-Deployment Verification

```bash
# Check service status
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose ps"

# View logs
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose logs orchestrator --tail=50"

# Test workflow
curl -X POST http://45.55.173.72:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"task": "Generate unit tests for authentication module"}'

# Check LangSmith traces
# https://smith.langchain.com/o/<workspace-id>/projects

# Check Grafana metrics
# https://appsmithery.grafana.net
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
ssh root@45.55.173.72 "docker compose logs orchestrator --tail=100"

# Common issues:
# 1. Missing env vars - Check .env uploaded correctly
# 2. Port conflicts - Verify no other services on 8000-8010
# 3. Database connection - Check postgres service health
```

### Environment Variables Not Loading

```bash
# Docker Compose only reads .env at startup
# Must use down+up, not restart

ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose down && docker compose up -d"
```

### Health Check Failing

```bash
# Check service is running
ssh root@45.55.173.72 "docker compose ps"

# Check internal connectivity
ssh root@45.55.173.72 "docker exec deploy-orchestrator-1 curl http://gateway-mcp:8000/health"

# Check logs for errors
ssh root@45.55.173.72 "docker compose logs orchestrator | grep ERROR"
```

### Out of Memory

```bash
# Check memory usage
ssh root@45.55.173.72 "free -h"

# Clean up Docker resources
ssh root@45.55.173.72 "docker system prune -af && docker builder prune -af"

# Or use automated cleanup
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType cleanup
```

---

## Rollback

### Automatic Rollback

If deployment fails validation, script automatically rolls back:

```powershell
# Failed deployment triggers automatic rollback
# - Reverts to previous commit
# - Rebuilds from last known good state
# - Validates health checks
```

### Manual Rollback

```powershell
# Rollback to previous commit
.\support\scripts\deploy\deploy-to-droplet.ps1 -Rollback

# Or rollback to specific tag
ssh root@45.55.173.72 "cd /opt/Dev-Tools && git checkout pre-deploy-20251125"
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose down && docker compose up -d --build"
```

---

## Monitoring

### LangSmith (LLM Tracing)

- **Dashboard:** https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects
- **Traces:** All LLM calls, tool invocations, agent reasoning
- **Alerts:** Token usage spikes, high latency, errors

### Grafana Cloud (Prometheus)

- **Dashboard:** https://appsmithery.grafana.net
- **Metrics:** HTTP requests, response times, error rates
- **Alerts:** Service health, memory usage, disk space

### Docker Logs

```bash
# View all services
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose logs -f"

# View specific service
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose logs -f orchestrator"

# Filter errors
ssh root@45.55.173.72 "docker compose logs orchestrator | grep ERROR"
```

---

## Automated Deployment (GitHub Actions)

### Workflow: deploy-intelligent.yml

- **Trigger:** Push to `main` branch or manual workflow_dispatch
- **Strategy:** Auto-detects changes (config/full/quick)
- **Validation:** Health checks after deployment
- **Cleanup:** Automatic Docker resource cleanup after deploy

### Manual Trigger

```bash
# GitHub Actions  Actions tab  deploy-intelligent.yml  Run workflow
# - Choose branch: main
# - Choose strategy: auto/config/full/quick
```

---

## Disaster Recovery

### Backup

```bash
# Create backup of volumes
./support/scripts/docker/backup_volumes.sh

# Backups saved to: ./backups/<timestamp>/
# - orchestrator-data.tar.gz
# - postgres-data.tar.gz
# - qdrant-data.tar.gz
```

### Restore

```bash
# Restore from backup
./support/scripts/docker/restore_volumes.sh ./backups/20251125_120000/

# Restart services
docker compose restart
```

### Emergency Rebuild

```bash
# Complete rebuild from scratch
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose down --volumes"
ssh root@45.55.173.72 "cd /opt/Dev-Tools && git pull origin main"
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose up -d --build"
```

---

## Related Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Local setup
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design
- **[operations/SECRETS_MANAGEMENT.md](operations/SECRETS_MANAGEMENT.md)** - Security
- **[operations/CLEANUP_QUICK_REFERENCE.md](operations/CLEANUP_QUICK_REFERENCE.md)** - Docker hygiene
- **[operations/DISASTER_RECOVERY.md](operations/DISASTER_RECOVERY.md)** - Complete DR guide
