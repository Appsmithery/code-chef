# Automated Deployment Workflows

This document describes the automated CI/CD deployment system for Dev-Tools with intelligent change detection.

## Overview

The deployment system automatically detects whether changes require:

- **Config deployment** (30s): Environment variable changes only → fast `down+up` cycle
- **Full rebuild** (10min): Code/dependency changes → complete rebuild
- **Quick restart** (15s): Documentation/non-critical changes → simple restart

## Deployment Methods

### 1. Local PowerShell Script

**Location:** `support/scripts/deploy/deploy-to-droplet.ps1`

**Auto-detect changes:**

```powershell
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType auto
```

**Config-only deployment (fast):**

```powershell
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config
```

**Full rebuild:**

```powershell
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType full
```

**Quick restart:**

```powershell
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType quick
```

**Rollback to previous commit:**

```powershell
.\support\scripts\deploy\deploy-to-droplet.ps1 -Rollback
```

**Skip health checks:**

```powershell
.\support\scripts\deploy\deploy-to-droplet.ps1 -SkipHealthCheck
```

### 2. GitHub Actions (Automatic)

**Location:** `.github/workflows/deploy-intelligent.yml`

**Triggers:**

- Automatic on push to `main` branch
- Manual via workflow dispatch (with strategy override)

**Change Detection:**
The workflow automatically detects file changes:

```yaml
code_changes:
  - "agent_*/**/*.py"
  - "shared/**/*.py"
  - "**/Dockerfile"
  - "**/requirements.txt"
  - "deploy/docker-compose.yml"

config_changes:
  - "config/env/*.env"
  - "config/**/*.yaml"
  - "config/**/*.yml"
```

**Strategy Selection:**

1. Code/dependency changes → **full** rebuild
2. Config-only changes → **config** fast deployment
3. Other changes → **quick** restart

**Manual Trigger:**
Go to GitHub Actions → "Intelligent Deploy to Droplet" → Run workflow → Select strategy

## Deployment Strategies Explained

### Config Strategy (Fastest - ~30s)

**When:** Only `config/env/.env` or YAML config files changed

**What it does:**

1. Uploads `config/env/.env` to droplet via SCP
2. Runs `git pull origin main` (for template updates)
3. Runs `docker compose down && docker compose up -d` (CRITICAL for env reload)
4. Validates health endpoints

**Why down+up:** Docker Compose only reads `.env` at startup. Simple `restart` does NOT reload environment variables.

**Example use case:**

- Updated LangSmith API key
- Changed Linear OAuth token
- Modified Prometheus scrape intervals

### Full Strategy (Slowest - ~10min)

**When:** Python code, Dockerfiles, or requirements.txt changed

**What it does:**

1. Ensures local changes are committed and pushed to main
2. Uploads `.env` to droplet
3. Runs `git pull origin main` on droplet
4. Runs `docker compose down --remove-orphans`
5. Runs `docker compose build --no-cache` (rebuild all images)
6. Runs `docker compose up -d`
7. Validates health endpoints

**Example use case:**

- Modified agent logic (`agent_orchestrator/main.py`)
- Added Python dependencies
- Changed Dockerfile instructions
- Updated shared libraries

### Quick Strategy (Fast - ~15s)

**When:** Documentation, markdown files, or non-critical changes

**What it does:**

1. Runs `git pull origin main` on droplet
2. Runs `docker compose restart`
3. Validates health endpoints

**Example use case:**

- Updated README.md
- Modified documentation
- Changed Linear markdown roadmap

## Configuration Requirements

### Local Script Requirements

1. **SSH Access:** Must have SSH key configured for `do-mcp-gateway` alias

   ```bash
   # ~/.ssh/config (Windows: C:\Users\<USER>\.ssh\config)
   Host do-mcp-gateway
       HostName 45.55.173.72
       User root
       IdentityFile ~/.ssh/github-actions-deploy
       StrictHostKeyChecking no
   ```

2. **Local .env file:** Must have `config/env/.env` with production secrets
   - Copy from `config/env/.env.template`
   - Populate: `GRADIENT_API_KEY`, `LANGSMITH_API_KEY`, `LINEAR_OAUTH_DEV_TOKEN`, etc.

### GitHub Actions Requirements

**Required Secrets** (Settings → Secrets → Actions):

| Secret Name              | Description                        | Example                                  |
| ------------------------ | ---------------------------------- | ---------------------------------------- |
| `DROPLET_SSH_KEY`        | Private SSH key for droplet access | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `GRADIENT_API_KEY`       | DigitalOcean Gradient AI API key   | `dop_v1_...`                             |
| `LANGSMITH_API_KEY`      | LangSmith service key              | `lsv2_sk_...`                            |
| `LANGSMITH_WORKSPACE_ID` | LangSmith workspace ID             | `5029c640-3f73-480c-82f3-58e402ed4207`   |
| `LINEAR_OAUTH_DEV_TOKEN` | Linear OAuth token                 | `lin_oauth_...`                          |

**How to extract workspace ID:**
From LangSmith URL: `https://smith.langchain.com/o/{workspace-id}/projects/p/{project-id}`

## Health Validation

Both deployment methods validate these endpoints after deployment:

| Port | Service        | Endpoint                       |
| ---- | -------------- | ------------------------------ |
| 8001 | Orchestrator   | `http://localhost:8001/health` |
| 8002 | Feature-Dev    | `http://localhost:8002/health` |
| 8003 | Code-Review    | `http://localhost:8003/health` |
| 8004 | Infrastructure | `http://localhost:8004/health` |
| 8005 | CI/CD          | `http://localhost:8005/health` |
| 8006 | Documentation  | `http://localhost:8006/health` |

**Expected response:**

```json
{
  "status": "ok",
  "service": "orchestrator",
  "timestamp": "2025-11-20T22:00:00.000000",
  "version": "1.0.0"
}
```

**Failure behavior:**

- PowerShell script: Exits with error code 1, suggests rollback command
- GitHub Action: Fails workflow, runs emergency cleanup (`docker system prune --volumes --force`)

## Rollback Procedure

### Automatic Rollback (PowerShell)

```powershell
.\support\scripts\deploy\deploy-to-droplet.ps1 -Rollback
```

**What it does:**

1. Runs `git reset --hard HEAD~1` on droplet (revert to previous commit)
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

## Troubleshooting

### Deployment fails with "uncommitted changes"

```powershell
git status  # Check what's uncommitted
git add .
git commit -m "fix: Your commit message"
git push origin main
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType full
```

### Health checks fail after config deployment

1. Check if environment variables loaded:
   ```bash
   ssh root@45.55.173.72 "docker exec deploy-orchestrator-1 env | grep LANGSMITH_WORKSPACE_ID"
   ```
2. If old value shown, ensure you used `down+up` not `restart`

### GitHub Action fails with SSH error

1. Verify `DROPLET_SSH_KEY` secret is set correctly
2. Ensure key has no passphrase
3. Check key format: OpenSSH format (`-----BEGIN OPENSSH PRIVATE KEY-----`)

### Services start but are unhealthy

```bash
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose logs orchestrator --tail=100"
```

Common issues:

- Missing environment variables (check `.env` uploaded correctly)
- LangSmith 403 errors (check `LANGSMITH_WORKSPACE_ID` matches URL)
- Import errors (check Python dependencies in `requirements.txt`)

## Best Practices

### When to use each method

**Local PowerShell Script:**

- Development/testing deployments
- One-off config changes
- When you need immediate feedback
- When troubleshooting issues

**GitHub Actions:**

- Production deployments from main branch
- Automated deployments after PR merge
- When you want deployment history
- Team deployments (no local SSH key needed)

### Workflow recommendations

1. **Config changes only:**

   ```powershell
   # Edit config/env/.env locally
   git add config/env/.env.template  # If you added new variables
   git commit -m "config: Update LangSmith workspace ID"
   git push origin main

   # Fast local deployment (30s)
   .\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config
   ```

2. **Code changes:**

   ```powershell
   # Make code changes
   git add .
   git commit -m "feat: Add new orchestrator workflow"
   git push origin main

   # Let GitHub Action handle deployment (automatic)
   # OR manual local deployment:
   .\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType full
   ```

3. **Emergency rollback:**
   ```powershell
   .\support\scripts\deploy\deploy-to-droplet.ps1 -Rollback
   ```

## Integration with Existing Tools

These deployment workflows integrate with existing scripts:

- **Validation:** Uses `support/scripts/validation/validate-tracing.sh` for post-deployment tests
- **Monitoring:** Validates LangSmith traces at dashboard after deployment
- **Linear:** Compatible with `support/scripts/linear/agent-linear-update.py` for roadmap updates

## Future Enhancements

Potential improvements for deployment automation:

1. **Blue-green deployments:** Zero-downtime deployments with traffic switching
2. **Canary deployments:** Gradual rollout to subset of traffic
3. **Automatic rollback:** Detect unhealthy deployments and auto-rollback
4. **Deployment notifications:** Post to Linear workspace hub (PR-68) or Slack
5. **Performance metrics:** Track deployment duration, success rate, rollback frequency
6. **Multi-environment:** Support for staging/production environments

## References

- **Copilot Instructions:** `.github/copilot-instructions.md` → "Configuration Changes Deployment" section
- **Docker Compose:** `deploy/docker-compose.yml` → Service definitions
- **Environment Template:** `config/env/.env.template` → All configuration variables
- **Health Endpoints:** `support/docs/AGENT_ENDPOINTS.md` → API documentation
