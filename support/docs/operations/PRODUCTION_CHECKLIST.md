# Production Deployment Checklist - v0.2

## Pre-Deployment Validation ✅

### Environment & Configuration

- [ ] Run `.\support\scripts\validation\validate-env.ps1` - all checks pass
- [ ] Verify `.env` has no placeholder values
- [ ] Confirm all secrets files exist in `config/env/secrets/`
- [ ] Test Linear OAuth token: `curl http://localhost:8000/oauth/linear/status`
- [ ] Test Gradient API key: `curl -H "Authorization: Bearer $GRADIENT_API_KEY" https://api.digitalocean.com/v2/ai/models`

### Docker & Containerization

- [ ] Validate docker-compose.yml: `docker compose -f deploy/docker-compose.yml config --quiet`
- [ ] Resource limits defined for all services (15+ services)
- [ ] Redis persistence configured (AOF + RDB)
- [ ] All hardcoded passwords replaced with Docker secrets
- [ ] Restart policies set to `unless-stopped` for all services

### Monitoring & Observability

- [ ] Prometheus scrape configs updated for all agents
- [ ] Alert rules loaded (`config/prometheus/alerts.yml` mounted)
- [ ] Grafana dashboards prepared (`config/grafana/dashboards/`)
- [ ] LangSmith project exists and API key valid
- [ ] Test Prometheus: `curl http://localhost:9090/-/healthy`

### API Health Checks

- [ ] Orchestrator: `curl http://localhost:8001/health && curl http://localhost:8001/ready`
- [ ] Feature-Dev: `curl http://localhost:8002/health && curl http://localhost:8002/ready`
- [ ] Code-Review: `curl http://localhost:8003/health`
- [ ] Infrastructure: `curl http://localhost:8004/health`
- [ ] CI/CD: `curl http://localhost:8005/health`
- [ ] Documentation: `curl http://localhost:8006/health`
- [ ] Gateway: `curl http://localhost:8000/health`

---

## Deployment Steps 🚀

### 1. Backup Current State

```powershell
# Backup volumes
.\support\scripts\docker\backup_volumes.sh

# Backup .env and secrets
Copy-Item config/env/.env config/env/.env.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')
tar -czf config/env/secrets-backup-$(Get-Date -Format 'yyyyMMdd-HHmmss').tar.gz config/env/secrets/
```

### 2. Deploy to Droplet (45.55.173.72)

```powershell
# Option A: Automated deployment
.\support\scripts\deploy.ps1 -Target remote

# Option B: Manual SSH deployment
ssh root@45.55.173.72
cd /opt/Dev-Tools
git pull origin main
docker compose -f deploy/docker-compose.yml pull
docker compose -f deploy/docker-compose.yml up -d --remove-orphans
docker compose -f deploy/docker-compose.yml ps
```

### 3. Post-Deployment Validation

```powershell
# Wait for services to start (60s)
Start-Sleep -Seconds 60

# Check all health endpoints
$Services = @(
    @{Name="Gateway"; Port=8000},
    @{Name="Orchestrator"; Port=8001},
    @{Name="Feature-Dev"; Port=8002},
    @{Name="Code-Review"; Port=8003},
    @{Name="Infrastructure"; Port=8004},
    @{Name="CI/CD"; Port=8005},
    @{Name="Documentation"; Port=8006}
)

foreach ($Service in $Services) {
    $Response = curl -s "http://45.55.173.72:$($Service.Port)/health"
    if ($Response -match '"status"\s*:\s*"ok"') {
        Write-Host "✅ $($Service.Name) healthy" -ForegroundColor Green
    } else {
        Write-Host "❌ $($Service.Name) unhealthy" -ForegroundColor Red
    }
}
```

### 4. Functional Testing

- [ ] Test chat endpoint: `POST http://45.55.173.72:8001/chat`
- [ ] Verify LangSmith traces appear: https://smith.langchain.com
- [ ] Test Linear integration: Create test issue
- [ ] Verify Prometheus metrics: http://45.55.173.72:9090/targets
- [ ] Check agent registry: `curl http://45.55.173.72:8009/agents`
- [ ] Test event bus: Trigger approval notification

---

## Monitoring Setup 📊

### Prometheus

```powershell
# Access Prometheus (via OAuth2 proxy)
# URL: http://theshop.appsmithery.co/prometheus
# GitHub OAuth required

# Verify all targets up
curl http://45.55.173.72:9090/api/v1/targets | jq '.data.activeTargets[] | select(.health != "up")'
```

### Grafana (Manual Setup Required)

1. Deploy Grafana container:

```yaml
grafana:
  image: grafana/grafana:latest
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
  volumes:
    - ../config/grafana/dashboards:/var/lib/grafana/dashboards:ro
    - grafana-data:/var/lib/grafana
  networks:
    - devtools-network
```

2. Import dashboard: `config/grafana/dashboards/agent-performance.json`
3. Configure Prometheus datasource: `http://prometheus:9090`

### LangSmith

- Project: `dev-tools-prod`
- Dashboard: https://smith.langchain.com/projects/dev-tools-prod
- Verify traces appear within 30s of agent LLM calls

---

## Rollback Procedures 🔙

### Quick Rollback (Suspected Issues)

```powershell
ssh root@45.55.173.72
cd /opt/Dev-Tools
git log --oneline -5  # Find previous commit
git checkout <previous-commit-hash>
docker compose -f deploy/docker-compose.yml up -d --force-recreate
```

### Full Rollback (Critical Failure)

```powershell
# Restore from backup
scp backups/latest-backup.tar.gz root@45.55.173.72:/opt/Dev-Tools/
ssh root@45.55.173.72
cd /opt/Dev-Tools
docker compose -f deploy/docker-compose.yml down
tar -xzf latest-backup.tar.gz
docker compose -f deploy/docker-compose.yml up -d
```

### Restore Secrets

```powershell
# Restore .env
ssh root@45.55.173.72
cd /opt/Dev-Tools
cp config/env/.env.backup-YYYYMMDD-HHmmss config/env/.env

# Restore secrets
tar -xzf config/env/secrets-backup-YYYYMMDD-HHmmss.tar.gz
docker compose -f deploy/docker-compose.yml restart
```

---

## Post-Deployment Tasks ✨

### Day 1

- [ ] Monitor Prometheus alerts for 24 hours
- [ ] Check LangSmith token usage (should be < 100K tokens/day)
- [ ] Verify no memory/CPU limit breaches
- [ ] Test end-to-end workflow: Task submission → Agent execution → Linear update

### Week 1

- [ ] Review error rates (should be < 1%)
- [ ] Check response times (p95 < 5s)
- [ ] Validate backup automation
- [ ] Document any operational issues

### Month 1

- [ ] Capacity planning review (CPU/memory headroom)
- [ ] Secrets rotation reminder (quarterly schedule)
- [ ] Update runbook with learnings
- [ ] Plan next phase improvements

---

## Emergency Contacts 📞

- **System Owner**: alex@appsmithery.co
- **Droplet IP**: 45.55.173.72
- **SSH Key**: `~/.ssh/github-actions-deploy`
- **Linear Workspace**: https://linear.app/project-roadmaps
- **LangSmith Dashboard**: https://smith.langchain.com

## Related Documentation

- [Secrets Rotation Guide](./SECRETS_ROTATION.md)
- [Prometheus Metrics](./PROMETHEUS_METRICS.md)
- [Deployment Guide](../DEPLOY.md)
- [Architecture Overview](../../README.md)
