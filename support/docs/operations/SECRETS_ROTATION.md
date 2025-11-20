# Secrets Rotation Guide

## Overview

This guide provides procedures for rotating secrets in a running Dev-Tools stack with minimal downtime.

## Secrets Inventory

| Secret                       | Location            | Usage                          | Rotation Frequency |
| ---------------------------- | ------------------- | ------------------------------ | ------------------ |
| `db_password.txt`            | config/env/secrets/ | PostgreSQL authentication      | Quarterly          |
| `linear_oauth_token.txt`     | config/env/secrets/ | Linear API access              | On revocation      |
| `linear_webhook_secret.txt`  | config/env/secrets/ | Webhook signature verification | Annually           |
| `GRADIENT_API_KEY`           | config/env/.env     | DigitalOcean AI API            | On revocation      |
| `LANGCHAIN_API_KEY`          | config/env/.env     | LangSmith tracing              | On revocation      |
| `OAUTH2_PROXY_CLIENT_SECRET` | config/env/.env     | GitHub OAuth                   | On revocation      |

## Rotation Procedures

### 1. Database Password (`db_password.txt`)

**Downtime**: ~30 seconds per service

```powershell
# Step 1: Generate new password
$NewPassword = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
$NewPassword | Out-File -NoNewline config/env/secrets/db_password.txt

# Step 2: Update PostgreSQL password
docker exec -it postgres psql -U devtools -c "ALTER USER devtools WITH PASSWORD '$NewPassword';"

# Step 3: Rolling restart of dependent services
$Services = @("state-persistence", "agent-registry", "langgraph")
foreach ($Service in $Services) {
    docker compose -f deploy/docker-compose.yml restart $Service
    Start-Sleep -Seconds 5
    docker compose -f deploy/docker-compose.yml ps $Service
}

# Step 4: Verify all services healthy
.\support\scripts\validation\validate-health.ps1
```

**Rollback**: Revert `db_password.txt` to previous value and restart services.

### 2. Linear OAuth Token (`linear_oauth_token.txt`)

**Downtime**: ~5 seconds (gateway only)

```powershell
# Step 1: Generate new token at https://linear.app/settings/api
# Copy token to clipboard

# Step 2: Update secret file
Read-Host "Paste new Linear OAuth token" -AsSecureString |
    ConvertFrom-SecureString |
    Out-File -NoNewline config/env/secrets/linear_oauth_token.txt

# Step 3: Update .env
$env:LINEAR_API_KEY = "lin_oauth_<new-token>"

# Step 4: Restart gateway
docker compose -f deploy/docker-compose.yml restart gateway-mcp

# Step 5: Test Linear integration
curl http://localhost:8000/oauth/linear/status
```

**Rollback**: Revert `linear_oauth_token.txt` and restart gateway.

### 3. Gradient API Key (`.env`)

**Downtime**: None (rolling restart)

```powershell
# Step 1: Generate new key at DigitalOcean dashboard
# https://cloud.digitalocean.com/account/api/tokens

# Step 2: Update .env
(Get-Content config/env/.env) -replace 'GRADIENT_API_KEY=.*', "GRADIENT_API_KEY=<new-key>" |
    Set-Content config/env/.env

# Step 3: Rolling restart of agents
$Agents = @("orchestrator", "feature-dev", "code-review", "infrastructure", "cicd", "documentation")
foreach ($Agent in $Agents) {
    docker compose -f deploy/docker-compose.yml restart $Agent
    Start-Sleep -Seconds 10  # Wait for agent to become ready
    curl http://localhost:800$($Agents.IndexOf($Agent) + 1)/health
}
```

**Rollback**: Revert `.env` change and restart agents.

### 4. LangSmith API Key (`.env`)

**Downtime**: None (graceful degradation)

```powershell
# Step 1: Generate new key at https://smith.langchain.com/settings

# Step 2: Update .env
(Get-Content config/env/.env) -replace 'LANGCHAIN_API_KEY=.*', "LANGCHAIN_API_KEY=<new-key>" |
    Set-Content config/env/.env

# Step 3: Rolling restart
$Services = @("orchestrator", "feature-dev", "code-review", "infrastructure", "cicd", "documentation")
foreach ($Service in $Services) {
    docker compose -f deploy/docker-compose.yml restart $Service
    Start-Sleep -Seconds 5
}

# Step 4: Verify tracing works
# Check https://smith.langchain.com for new traces
```

**Impact**: Tracing may be temporarily unavailable during restart, but agents continue to function.

## Zero-Downtime Rotation (Production)

For production deployments, use blue-green deployment:

```powershell
# Step 1: Update secrets in new compose file
cp deploy/docker-compose.yml deploy/docker-compose.green.yml

# Step 2: Update secrets in green environment
# ... modify secrets in config/env/secrets/ and .env

# Step 3: Start green stack on different ports
# Modify port mappings in docker-compose.green.yml (e.g., 9001-9006)
docker compose -f deploy/docker-compose.green.yml up -d

# Step 4: Health check green stack
foreach ($Port in 9001..9006) {
    curl "http://localhost:$Port/health"
}

# Step 5: Update Caddy to route to green stack
# Modify config/caddy/Caddyfile

# Step 6: Reload Caddy (no downtime)
docker exec caddy caddy reload --config /etc/caddy/Caddyfile

# Step 7: Shutdown blue stack
docker compose -f deploy/docker-compose.yml down

# Step 8: Rename green to production
mv deploy/docker-compose.green.yml deploy/docker-compose.yml
# Update port mappings back to 8000-8006
```

## Verification Checklist

After any rotation:

- [ ] All health endpoints return `{"status": "healthy"}`
- [ ] Check Prometheus for no alerts
- [ ] Test Linear integration (create test issue)
- [ ] Test LLM inference (send test request to orchestrator)
- [ ] Check LangSmith traces appear
- [ ] Verify database connectivity
- [ ] Check event bus (Redis) connections

## Emergency Revocation

If a secret is compromised:

```powershell
# Immediate shutdown of affected services
docker compose -f deploy/docker-compose.yml stop <service>

# Rotate secret using procedures above

# Update firewall rules if external breach
# ssh root@45.55.173.72 "ufw deny from <ip-address>"

# Audit access logs
docker logs <service> --since 24h | grep -i "error\|unauthorized\|forbidden"

# Notify team via Linear
python support/scripts/linear/agent-linear-update.py create-issue \
    --title "Security Incident: <secret> Rotation" \
    --description "Emergency rotation performed" \
    --status "done"
```

## Automation (Future Enhancement)

Planned automation via orchestrator:

- Quarterly password rotation reminders (Linear notifications)
- Automated health checks post-rotation
- Secrets expiry tracking (PostgreSQL triggers)
- Vault integration for dynamic secrets

## References

- [Docker Secrets Documentation](https://docs.docker.com/engine/swarm/secrets/)
- [Linear API Tokens](https://developers.linear.app/docs/graphql/working-with-the-graphql-api#personal-api-keys)
- [DigitalOcean API Tokens](https://docs.digitalocean.com/reference/api/create-personal-access-token/)
- [LangSmith API Keys](https://docs.smith.langchain.com/)
