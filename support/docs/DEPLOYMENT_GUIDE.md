# Dev-Tools Deployment Guide

**Version:** v0.3  
**Status:** ✅ Production Ready  
**Last Updated:** November 22, 2025

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

# Quick restart (15s - for docs only)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType quick

# Rollback to previous commit
.\support\scripts\deploy\deploy-to-droplet.ps1 -Rollback
```

### Health Checks

```bash
# All services
curl http://45.55.173.72:8000/health  # Gateway
curl http://45.55.173.72:8001/health  # Orchestrator
curl http://45.55.173.72:8007/health  # RAG
curl http://45.55.173.72:8008/health  # State
```

Expected: `{"status": "healthy", "mcp_gateway": "connected"}`

### Troubleshooting

```powershell
# View logs
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose logs orchestrator --tail=50"

# Rollback
.\support\scripts\deploy\deploy-to-droplet.ps1 -Rollback

# Check env vars loaded
ssh root@45.55.173.72 "docker exec deploy-orchestrator-1 env | grep LANGSMITH_WORKSPACE_ID"
```

---

## Architecture Overview

### v0.3 LangGraph Architecture

**Services:**

| Service            | Port | Purpose                                      |
| ------------------ | ---- | -------------------------------------------- |
| **orchestrator**   | 8001 | LangGraph workflow engine with 6 agent nodes |
| **gateway-mcp**    | 8000 | MCP tool routing, 150+ tools                 |
| **rag-context**    | 8007 | Vector search, Qdrant integration            |
| **state**          | 8008 | Workflow state, PostgreSQL                   |
| **agent-registry** | 8009 | Agent capability discovery                   |
| **postgres**       | 5432 | Workflow checkpointing, HITL approval state  |
| **redis**          | 6379 | Event bus, pub/sub                           |

**Key Changes from v0.2:**

- 6 agent microservices → 1 orchestrator with LangGraph nodes
- Ports 8002-8006 deprecated (feature-dev, code-review, infrastructure, cicd, documentation)
- Simplified deployment (1 service vs 6 services)

---

## Deployment Strategies

### When to Use Each Strategy

| Change Type             | Strategy | Duration | Use Case                                 |
| ----------------------- | -------- | -------- | ---------------------------------------- |
| `.env` or config YAML   | `config` | 30s      | API keys, Linear tokens, DB passwords    |
| Python code, Dockerfile | `full`   | 10min    | Agent logic, dependencies, Docker images |
| Documentation, README   | `quick`  | 15s      | Markdown files, non-critical updates     |
| Not sure                | `auto`   | varies   | Script detects changes automatically     |

### Config Strategy (Fastest)

**When:** Only `config/env/.env` or YAML config files changed

**What it does:**

1. Uploads `config/env/.env` to droplet via SCP
2. Runs `git pull origin main` (for template updates)
3. Runs `docker compose down && docker compose up -d` (CRITICAL for env reload)
4. Validates health endpoints

⚠️ **Why down+up?** Docker Compose only reads `.env` at startup. Simple `restart` does NOT reload environment variables.

**Example:**

```powershell
# Edit config/env/.env locally
# Update LANGSMITH_API_KEY or LINEAR_OAUTH_TOKEN

# Deploy
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config
```

### Full Strategy (Complete Rebuild)

**When:** Python code, Dockerfiles, or requirements.txt changed

**What it does:**

1. Ensures local changes are committed and pushed to main
2. Uploads `.env` to droplet
3. Runs `git pull origin main` on droplet
4. Runs `docker compose down --remove-orphans`
5. Runs `docker compose build --no-cache` (rebuild all images)
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

### Quick Strategy (Fastest)

**When:** Documentation, markdown files, or non-critical changes

**What it does:**

1. Runs `git pull origin main` on droplet
2. Runs `docker compose restart`
3. Validates health endpoints

**Example:**

```powershell
# Update README.md
git commit -am "docs: Update README"
git push origin main

# Deploy
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType quick
   ```

---

## LLM Configuration Management

### Hot-Reload (No Deployment Required)

**Use Case:** Update model, cost, or context_window without restarting services

**Procedure:**

1. **Edit YAML config:**
   ```bash
   # Local machine
   nano config/agents/models.yaml
   ```

2. **Example change:**
   ```yaml
   agents:
     orchestrator:
       model: llama3-8b-instruct  # Changed from llama3.3-70b-instruct
       cost_per_1m_tokens: 0.20   # Changed from 0.60
   ```

3. **Commit and push:**
   ```bash
   git commit -am "config: Switch orchestrator to 8B model for cost savings"
   git push origin main
   ```

4. **Apply to droplet:**
   ```bash
   ssh root@45.55.173.72 "cd /opt/Dev-Tools && git pull origin main"
   ```

5. **Restart orchestrator service (30s):**
   ```bash
   ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose restart orchestrator"
   ```

**What gets reloaded:**

- ✅ Model name (LLM inference switches immediately)
- ✅ Cost per 1M tokens (token tracking updates)
- ✅ Context window (validation limits change)
- ✅ Max tokens, temperature (LLM parameters)
- ❌ New dependencies in requirements.txt (requires `full` deploy)
- ❌ Python code changes (requires `full` deploy)

**Verification:**

```bash
# Check health endpoint
curl http://45.55.173.72:8001/health | jq

# Check token tracking with new cost
curl http://45.55.173.72:8001/metrics/tokens | jq '.per_agent.orchestrator.total_cost'

# View logs for model switch confirmation
ssh root@45.55.173.72 "docker compose -f /opt/Dev-Tools/deploy/docker-compose.yml logs orchestrator --tail=20"
```

### Environment-Specific Overrides

**Use Case:** Use cheaper models in development, production models in prod

**Architecture:**

```yaml
# config/agents/models.yaml
agents:
  orchestrator:
    model: llama3.3-70b-instruct  # Default (production)
    cost_per_1m_tokens: 0.60

environments:
  development:
    orchestrator:
      model: llama3-8b-instruct  # Override for dev
      cost_per_1m_tokens: 0.20
  staging:
    orchestrator:
      model: llama3.1-8b-instruct  # Override for staging
      cost_per_1m_tokens: 0.20
```

**ConfigLoader Logic:**

```python
# shared/lib/config_loader.py
config = loader.get_agent_config("orchestrator")
# Returns development config if NODE_ENV=development
# Returns production config if NODE_ENV=production
```

**Deployment:**

```bash
# Development droplet
export NODE_ENV=development
docker compose up -d

# Production droplet
export NODE_ENV=production
docker compose up -d
```

**Cost Impact:**

| Environment | Model                   | Cost/1M Tokens | Monthly (100M tokens) |
| ----------- | ----------------------- | -------------- | --------------------- |
| Development | llama3-8b-instruct      | $0.20          | $20                   |
| Staging     | llama3.1-8b-instruct    | $0.20          | $20                   |
| Production  | llama3.3-70b-instruct   | $0.60          | $60                   |

---

## Configuration Requirements### Required Environment Variables

```bash
# LangSmith (LLM Tracing) - REQUIRED
LANGSMITH_API_KEY=lsv2_sk_***
LANGCHAIN_API_KEY=lsv2_sk_***
LANGSMITH_WORKSPACE_ID=5029c640-3f73-480c-82f3-58e402ed4207

# DigitalOcean Gradient AI - REQUIRED
GRADIENT_API_KEY=<gradient_api_key>
DIGITALOCEAN_TOKEN=<do_pat>
GRADIENT_MODEL_ACCESS_KEY=<model_key>

# Linear (HITL + Project Management) - REQUIRED
LINEAR_API_KEY=lin_oauth_***
LINEAR_OAUTH_DEV_TOKEN=lin_oauth_***
LINEAR_WEBHOOK_SIGNING_SECRET=<secret>
LINEAR_APPROVAL_HUB_ISSUE_ID=DEV-68
HITL_ORCHESTRATOR_TEMPLATE_UUID=aa632a46-ea22-4dd0-9403-90b0d1f05aa0

# Linear Custom Fields (HITL) - REQUIRED
LINEAR_FIELD_REQUEST_STATUS_ID=<field_uuid>
LINEAR_FIELD_REQUIRED_ACTION_ID=<field_uuid>
LINEAR_REQUEST_STATUS_APPROVED=<option_uuid>
LINEAR_REQUEST_STATUS_DENIED=<option_uuid>
LINEAR_REQUEST_STATUS_MORE_INFO=<option_uuid>

# Database - REQUIRED
DB_PASSWORD=<postgres_password>
POSTGRES_PASSWORD=<postgres_password>
```

### Setup Steps

1. **Copy template:**

   ```bash
   cp config/env/.env.template config/env/.env
   ```

2. **Populate secrets** (see above for required values)

3. **Validate secrets:**

   ```bash
   npm run secrets:validate:discover
   ```

4. **Create Docker secrets:**
   ```bash
   mkdir -p config/env/secrets
   echo "$LINEAR_OAUTH_TOKEN" > config/env/secrets/linear_oauth_token.txt
   echo "$LINEAR_WEBHOOK_SECRET" > config/env/secrets/linear_webhook_secret.txt
   echo "$DB_PASSWORD" > config/env/secrets/db_password.txt
   chmod 600 config/env/secrets/*.txt
   ```

### SSH Access Setup

**Windows:** `C:\Users\<USER>\.ssh\config`  
**Linux/Mac:** `~/.ssh/config`

```bash
Host do-mcp-gateway
    HostName 45.55.173.72
    User root
    IdentityFile ~/.ssh/github-actions-deploy
    StrictHostKeyChecking no
```

---

## Deployment Procedures

### First-Time Deployment

1. **Initialize database schema:**

   ```bash
   ssh root@45.55.173.72
   cd /opt/Dev-Tools
   task workflow:init-db
   task workflow:list-pending  # Verify empty
   ```

2. **Setup environment:**

   ```bash
   # Local machine
   cp config/env/.env.template config/env/.env
   # Edit .env with production secrets
   npm run secrets:validate:discover
   ```

3. **Create Docker secrets:**

   ```bash
   mkdir -p config/env/secrets
   # Create secret files (see Configuration Requirements)
   ```

4. **Deploy:**

   ```powershell
   .\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType full
   ```

5. **Verify deployment:**

   ```bash
   # Health checks
   curl http://45.55.173.72:8001/health

   # Test HITL workflow
   curl -X POST http://45.55.173.72:8001/orchestrate \
     -H "Content-Type: application/json" \
     -d '{"description": "Deploy auth service to production", "priority": "high"}'

   # Check Linear for approval request (DEV-68)
   ```

### Routine Deployments

#### Config Changes Only

```powershell
# 1. Edit config/env/.env locally
# 2. Update .env.template if adding new variables
git add config/env/.env.template
git commit -m "config: Update LangSmith workspace ID"
git push origin main

# 3. Deploy (30s)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config
```

#### Code Changes

```powershell
# 1. Make code changes
git add .
git commit -m "feat: Add new orchestrator workflow"
git push origin main

# 2. Deploy (10min)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType full

# OR let GitHub Action handle it automatically
```

#### Documentation Changes

```powershell
# 1. Update docs
git commit -am "docs: Update deployment guide"
git push origin main

# 2. Deploy (15s)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType quick
```

### GitHub Actions (Automatic)

**Triggers:**

- Automatic on push to `main` branch
- Manual: https://github.com/Appsmithery/Dev-Tools/actions/workflows/deploy-intelligent.yml

**Required Secrets** (Settings → Secrets → Actions):

- `DROPLET_SSH_KEY` - Private SSH key
- `GRADIENT_API_KEY` - DigitalOcean Gradient AI key
- `LANGSMITH_API_KEY` - LangSmith service key
- `LANGSMITH_WORKSPACE_ID` - `5029c640-3f73-480c-82f3-58e402ed4207`
- `LINEAR_OAUTH_DEV_TOKEN` - Linear OAuth token

---

## Validation & Testing

### Health Checks

```bash
# All services
for port in 8000 8001 8007 8008 8009; do
    echo "Port $port:"
    curl -s http://45.55.173.72:${port}/health | jq
done
```

### Functional Tests

**Low-Risk Task (Auto-Approve):**

```bash
curl -X POST http://45.55.173.72:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"description": "Read configuration from dev environment", "priority": "low"}'
# Expected: Immediate orchestration, no approval request
```

**High-Risk Task (HITL Approval):**

```bash
curl -X POST http://45.55.173.72:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"description": "Deploy to production", "priority": "high"}'
# Expected: approval_pending status, Linear sub-issue created in DEV-68
```

**Approval Workflow:**

```bash
task workflow:list-pending  # Find request ID
task workflow:approve REQUEST_ID=<uuid>
# Workflow resumes and executes
```

### Observability

**LangSmith Tracing:**  
https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects

**Prometheus Metrics:**  
http://45.55.173.72:9090/targets

**Linear Notifications:**  
Check DEV-68 for approval requests

---

## Troubleshooting

### Deployment Failed

```powershell
# View logs
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose logs --tail=100"

# Rollback
.\support\scripts\deploy\deploy-to-droplet.ps1 -Rollback
```

### Environment Variables Not Loading

**Problem:** Environment variables show old values after config deployment

**Solution:**

```bash
# Check current value
ssh root@45.55.173.72 "docker exec deploy-orchestrator-1 env | grep LANGSMITH_WORKSPACE_ID"

# If old value shown, must use down+up (not restart)
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose down && docker compose up -d"
```

### Services Unhealthy After Deployment

```bash
# Check specific service logs
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose logs orchestrator --tail=50"

# Restart specific service
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose restart orchestrator"

# Check all services
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose ps"
```

**Common Issues:**

- Missing environment variables → Check `.env` uploaded correctly
- LangSmith 403 errors → Verify `LANGSMITH_WORKSPACE_ID` matches URL
- Import errors → Check Python dependencies in `requirements.txt`

### Uncommitted Changes Error

```powershell
git status  # Check what's uncommitted
git add .
git commit -m "fix: Your commit message"
git push origin main
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType full
```

### GitHub Action SSH Errors

1. Verify `DROPLET_SSH_KEY` secret is set correctly
2. Ensure key has no passphrase
3. Check key format: OpenSSH format (`-----BEGIN OPENSSH PRIVATE KEY-----`)

---

## Rollback Procedures

### Automatic Rollback (Recommended)

```powershell
.\support\scripts\deploy\deploy-to-droplet.ps1 -Rollback
```

**What it does:**

1. Reverts to previous git commit (`HEAD~1`)
2. Runs `docker compose down && docker compose up -d`
3. Validates health endpoints

### Manual Rollback

```bash
ssh root@45.55.173.72
cd /opt/Dev-Tools
git log --oneline -10  # Find last known good commit
git reset --hard <commit-sha>
cd deploy
docker compose down && docker compose up -d
```

---

## HITL Approval System

### Risk-Based Workflow

**Risk Levels:**

| Risk Level   | Auto-Approve | Approver Role             | Timeout | Examples                     |
| ------------ | ------------ | ------------------------- | ------- | ---------------------------- |
| **Low**      | ✅ Yes       | N/A                       | N/A     | Dev reads, config queries    |
| **Medium**   | ❌ No        | developer/tech_lead       | 30 min  | Staging deploys, data import |
| **High**     | ❌ No        | tech_lead/devops_engineer | 60 min  | Production deploys, infra    |
| **Critical** | ❌ No        | devops_engineer           | 120 min | Production deletes, secrets  |

### Workflow Pattern

```
1. Risk Assessment → risk_assessor.assess_task(task_dict)
2. If requires_approval() → hitl_manager.create_approval_request()
3. LangGraph workflow interrupts at approval_gate node
4. Linear sub-issue created in DEV-68 (approval hub)
5. User sets Request Status (Approved/Denied/More info)
6. Linear webhook triggers status update in PostgreSQL
7. Workflow resumes from checkpoint if approved
```

### Taskfile Commands

```bash
task workflow:init-db              # Initialize approval_requests table
task workflow:list-pending         # List pending approvals
task workflow:approve REQUEST_ID=<uuid>   # Approve request
task workflow:reject REQUEST_ID=<uuid> REASON="..."  # Reject request
task workflow:status WORKFLOW_ID=<id>     # Show workflow status
task workflow:clean-expired        # Clean up expired requests
```

---

## Best Practices

### ✅ Do's

- **Use auto-detect:** `.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType auto` when unsure
- **Commit before deploying:** Full deployment requires clean git state
- **Update .env.template:** When adding new environment variables
- **Test locally first:** Run `npm run secrets:validate` before deploying
- **Check health after deploy:** Verify all endpoints return healthy status
- **Use config strategy for env changes:** Much faster than full rebuild

### ❌ Don'ts

- **Don't use `restart` for config changes:** Must use `down+up` to reload `.env`
- **Don't skip health checks:** Always validate deployment success
- **Don't commit `.env` file:** Only commit `.env.template`
- **Don't deploy with uncommitted changes:** Script will fail
- **Don't skip secrets validation:** Run `npm run secrets:validate:discover`

---

## Important Notes

⚠️ **Config changes require `down && up` cycle** - `restart` does NOT reload `.env`

⚠️ **Commit before full deployment** - Script will fail if you have uncommitted changes

⚠️ **GitHub Action requires secrets** - Ensure all secrets are set in repo settings

⚠️ **Droplet is connected to main branch** - Changes to main trigger automatic deployment

✅ **Auto-detect is smart** - Use `-DeployType auto` when unsure

✅ **Rollback is safe** - Reverts to previous git commit and restarts services

✅ **Health checks are comprehensive** - Validates all 5 core services

---

## Related Documentation

- **Copilot Instructions:** `.github/copilot-instructions.md`
- **Linear Integration:** `support/docs/LINEAR_INTEGRATION_GUIDE.md`
- **HITL Workflow:** `support/docs/LINEAR_HITL_WORKFLOW.md`
- **Secrets Management:** `support/docs/operations/SECRETS_MANAGEMENT.md`
- **LangSmith Tracing:** `support/docs/guides/integration/LANGSMITH_TRACING.md`
- **Docker Compose:** `deploy/docker-compose.yml`
- **Environment Template:** `config/env/.env.template`

---

**Document Version:** 1.0.0  
**Architecture:** LangGraph v0.3  
**Production Status:** ✅ Deployed  
**Last Deployment:** November 22, 2025
