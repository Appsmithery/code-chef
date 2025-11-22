# Deployment Quick Reference

## Quick Commands

### Local Deployment (PowerShell)

```powershell
# Auto-detect changes and deploy
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType auto

# Config-only (fast - 30s)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config

# Full rebuild (slow - 10min)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType full

# Quick restart (fastest - 15s)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType quick

# Rollback to previous commit
.\support\scripts\deploy\deploy-to-droplet.ps1 -Rollback
```

### Manual SSH Commands

```bash
# Config deployment (manual)
scp config/env/.env root@45.55.173.72:/opt/Dev-Tools/config/env/.env
ssh root@45.55.173.72 "cd /opt/Dev-Tools && git pull origin main && cd deploy && docker compose down && docker compose up -d"

# Full rebuild (manual)
ssh root@45.55.173.72 "cd /opt/Dev-Tools && git pull origin main && cd deploy && docker compose down --remove-orphans && docker compose build --no-cache && docker compose up -d"

# Quick restart (manual)
ssh root@45.55.173.72 "cd /opt/Dev-Tools && git pull origin main && cd deploy && docker compose restart"

# Check health
ssh root@45.55.173.72 "curl -s http://localhost:8001/health | jq"

# View logs
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose logs -f orchestrator"
```

## When to Use Each Strategy

| Change Type             | Strategy | Duration | Command                                        |
| ----------------------- | -------- | -------- | ---------------------------------------------- |
| `.env` or config YAML   | `config` | 30s      | `...\deploy-to-droplet.ps1 -DeployType config` |
| Python code, Dockerfile | `full`   | 10min    | `...\deploy-to-droplet.ps1 -DeployType full`   |
| Documentation, README   | `quick`  | 15s      | `...\deploy-to-droplet.ps1 -DeployType quick`  |
| Not sure                | `auto`   | varies   | `...\deploy-to-droplet.ps1 -DeployType auto`   |

## GitHub Actions

**Automatic deployment:**

- Push to `main` branch → GitHub Action runs automatically
- Detects changes and selects optimal strategy
- View: https://github.com/Appsmithery/Dev-Tools/actions

**Manual trigger:**

1. Go to: https://github.com/Appsmithery/Dev-Tools/actions/workflows/deploy-intelligent.yml
2. Click "Run workflow"
3. Select strategy (auto/config/full/quick)
4. Click "Run workflow"

## Health Checks

All deployments validate these endpoints:

```bash
# Check all services
for port in 8001 8002 8003 8004 8005 8006; do
    echo "Port $port:"
    ssh root@45.55.173.72 "curl -s http://localhost:${port}/health | jq -r '.status'"
done
```

Expected: `ok` for all ports

## Troubleshooting

### Deployment failed

```powershell
# View logs
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose logs --tail=100"

# Rollback
.\support\scripts\deploy\deploy-to-droplet.ps1 -Rollback
```

### Environment variables not loading

```bash
# Check current value
ssh root@45.55.173.72 "docker exec deploy-orchestrator-1 env | grep LANGSMITH_WORKSPACE_ID"

# If old value shown, must use down+up (not restart)
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose down && docker compose up -d"
```

### Services unhealthy after deployment

```bash
# Check specific service
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose logs orchestrator --tail=50"

# Restart specific service
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose restart orchestrator"
```

## Configuration Changes Workflow

1. Edit `config/env/.env` locally
2. Update `config/env/.env.template` if adding new variables
3. Commit template (`.env` is gitignored):
   ```powershell
   git add config/env/.env.template
   git commit -m "config: Add new environment variable"
   git push origin main
   ```
4. Deploy config:
   ```powershell
   .\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config
   ```

## Verification

### LangSmith Traces

https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects/p/f967bb5e-2e61-434f-8ee1-0df8c22bc046

### Test Orchestrator

```bash
ssh root@45.55.173.72 'curl -X POST http://localhost:8001/orchestrate -H "Content-Type: application/json" -d "{\"description\":\"test task\",\"priority\":\"high\"}"'
```

### View All Services

```bash
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose ps"
```

## Important Notes

⚠️ **Config changes require `down && up` cycle** - `restart` does NOT reload `.env`

⚠️ **Commit before full deployment** - Script will fail if you have uncommitted changes

⚠️ **GitHub Action requires secrets** - Ensure all secrets are set in repo settings

✅ **Auto-detect is smart** - Use `-DeployType auto` when unsure

✅ **Rollback is safe** - Reverts to previous git commit and restarts services

## Documentation

- **Complete Guide:** `support/docs/DEPLOYMENT_AUTOMATION.md`
- **Copilot Instructions:** `.github/copilot-instructions.md` → "Deployment workflows"
- **Script:** `support/scripts/deploy/deploy-to-droplet.ps1`
- **GitHub Action:** `.github/workflows/deploy-intelligent.yml`
