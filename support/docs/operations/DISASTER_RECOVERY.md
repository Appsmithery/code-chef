# Disaster Recovery Plan - Dev-Tools v0.2

## Executive Summary

**RTO (Recovery Time Objective)**: 30 minutes  
**RPO (Recovery Point Objective)**: 4 hours  
**Last Updated**: November 19, 2025  
**Owner**: alex@appsmithery.co

## Critical Assets

| Asset               | Priority | Backup Frequency   | Storage Location |
| ------------------- | -------- | ------------------ | ---------------- |
| PostgreSQL Database | P0       | Every 6 hours      | Local + Droplet  |
| Redis Event Bus     | P1       | Daily              | Droplet          |
| Orchestrator State  | P1       | Daily              | Droplet volume   |
| MCP Config          | P2       | Weekly             | Git repository   |
| Secrets             | P0       | Manual (on change) | Encrypted backup |
| Docker Images       | P2       | On build           | Docker Hub       |

## Backup Strategy

### Automated Backups

**Database (PostgreSQL)**

```bash
# Runs every 6 hours via cron on droplet
0 */6 * * * /opt/Dev-Tools/support/scripts/backup/postgres-backup.sh

# Backup script creates:
# - /opt/backups/postgres/devtools-YYYY-MM-DD-HHMMSS.sql.gz
# - Retention: 7 days local, 30 days in DO Spaces
```

**Docker Volumes**

```bash
# Runs daily at 2 AM via cron
0 2 * * * /opt/Dev-Tools/support/scripts/backup/volume-backup.sh

# Backs up:
# - orchestrator-data
# - postgres-data
# - redis-data
# - prometheus-data
# - loki-data
```

**Configuration Files**

```bash
# Git-tracked, backed up on every commit
cd /opt/Dev-Tools
git push origin main  # Pushes to GitHub
```

### Manual Backup (Pre-Deployment)

```powershell
# Run before any major deployment
ssh do-mcp-gateway
cd /opt/Dev-Tools

# Full system snapshot
./support/scripts/backup/full-backup.sh

# Creates:
# - /opt/backups/full/devtools-snapshot-YYYY-MM-DD.tar.gz
# - Includes: volumes, configs, .env, secrets (encrypted)
```

## Disaster Scenarios

### Scenario 1: Database Corruption

**Detection**: Health checks fail, agents unable to persist state  
**Impact**: High - No task tracking, no workflow state  
**RTO**: 15 minutes  
**RPO**: 6 hours

**Recovery Steps**:

```bash
# 1. Stop services
docker compose -f deploy/docker-compose.yml stop state-persistence agent-registry langgraph

# 2. Identify latest backup
ls -lh /opt/backups/postgres/ | tail -5

# 3. Restore database
docker exec -i postgres psql -U devtools -d devtools < /opt/backups/postgres/devtools-YYYY-MM-DD-HHMMSS.sql

# 4. Verify data integrity
docker exec postgres psql -U devtools -d devtools -c "SELECT COUNT(*) FROM agent_registry;"

# 5. Restart services
docker compose -f deploy/docker-compose.yml start state-persistence agent-registry langgraph

# 6. Validate
curl http://localhost:8008/health
curl http://localhost:8009/health
```

### Scenario 2: Complete Droplet Loss

**Detection**: Droplet unreachable, all services down  
**Impact**: Critical - Full service outage  
**RTO**: 30 minutes (with recent backup)  
**RPO**: 4 hours

**Recovery Steps**:

```powershell
# 1. Provision new droplet (DigitalOcean)
# - Ubuntu 22.04 LTS
# - 4 CPU / 8GB RAM minimum
# - 160GB SSD
# - Region: NYC3 (or closest to traffic)

# 2. Configure droplet
$DROPLET_IP = "<new-droplet-ip>"
ssh root@$DROPLET_IP

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 3. Clone repository
cd /opt
git clone https://github.com/Appsmithery/Dev-Tools.git
cd Dev-Tools

# 4. Restore secrets and .env
# From encrypted backup in DO Spaces or local workstation
scp config/env/.env root@$DROPLET_IP:/opt/Dev-Tools/config/env/
scp -r config/env/secrets/ root@$DROPLET_IP:/opt/Dev-Tools/config/env/

# 5. Restore database backup
scp /path/to/latest-backup.sql.gz root@$DROPLET_IP:/opt/backups/

# 6. Deploy stack
ssh root@$DROPLET_IP
cd /opt/Dev-Tools
docker compose -f deploy/docker-compose.yml up -d

# 7. Restore database
docker exec -i postgres psql -U devtools -d devtools < /opt/backups/latest-backup.sql

# 8. Update DNS (if using custom domain)
# Point theshop.appsmithery.co to $DROPLET_IP

# 9. Validate all services
./support/scripts/validation/validate-health.sh
```

### Scenario 3: Redis Data Loss

**Detection**: Event bus disconnected, agents can't communicate  
**Impact**: Medium - Agent coordination affected  
**RTO**: 5 minutes  
**RPO**: 24 hours

**Recovery Steps**:

```bash
# 1. Stop services that depend on Redis
docker compose -f deploy/docker-compose.yml stop orchestrator feature-dev code-review infrastructure cicd documentation agent-registry

# 2. Restore Redis from backup (if available)
docker compose -f deploy/docker-compose.yml stop redis
docker run --rm -v redis-data:/data -v /opt/backups/redis:/backup alpine sh -c "cd /data && tar -xzf /backup/redis-YYYY-MM-DD.tar.gz"

# 3. Start Redis
docker compose -f deploy/docker-compose.yml start redis

# 4. Restart agents
docker compose -f deploy/docker-compose.yml start orchestrator feature-dev code-review infrastructure cicd documentation agent-registry

# 5. Verify event bus
curl http://localhost:8009/health | jq '.event_bus'
```

### Scenario 4: Corrupted Docker Images

**Detection**: Containers crash on startup, invalid image errors  
**Impact**: Medium - Service restart required  
**RTO**: 10 minutes  
**RPO**: N/A (images in registry)

**Recovery Steps**:

```bash
# 1. Stop all services
docker compose -f deploy/docker-compose.yml down

# 2. Remove corrupted images
docker images | grep alextorelli28/appsmithery
docker rmi $(docker images -q alextorelli28/appsmithery:*)

# 3. Pull fresh images
docker compose -f deploy/docker-compose.yml pull

# 4. Restart stack
docker compose -f deploy/docker-compose.yml up -d

# 5. Validate
docker compose -f deploy/docker-compose.yml ps
```

### Scenario 5: Secrets Compromise

**Detection**: Unauthorized access detected, API key revoked  
**Impact**: Critical - Security breach  
**RTO**: Immediate (emergency mode)  
**RPO**: N/A

**Recovery Steps**:

```bash
# 1. IMMEDIATE: Shutdown affected services
docker compose -f deploy/docker-compose.yml stop <affected-service>

# 2. Rotate compromised secrets (see SECRETS_ROTATION.md)
# - Revoke old keys in provider dashboards
# - Generate new keys
# - Update config/env/secrets/

# 3. Update firewall rules
ufw deny from <malicious-ip>

# 4. Audit logs
docker logs <service> --since 24h | grep -i "unauthorized\|forbidden\|error"

# 5. Restart with new secrets
docker compose -f deploy/docker-compose.yml restart <affected-service>

# 6. Notify team
python support/scripts/linear/agent-linear-update.py create-issue \
  --title "Security Incident: Secrets Rotation" \
  --description "Emergency rotation performed due to compromise" \
  --status "done"
```

## DR Testing Schedule

| Test Type             | Frequency | Next Test Date |
| --------------------- | --------- | -------------- |
| Database Restore      | Monthly   | Dec 1, 2025    |
| Full Droplet Recovery | Quarterly | Feb 1, 2026    |
| Secrets Rotation      | Quarterly | Feb 1, 2026    |
| Backup Verification   | Weekly    | Nov 26, 2025   |

## DR Testing Procedure

### Monthly Database Restore Test

```bash
# 1. Create test environment
docker compose -f deploy/docker-compose.test.yml up -d postgres-test

# 2. Restore latest backup
docker exec -i postgres-test psql -U devtools -d devtools < /opt/backups/postgres/latest.sql

# 3. Verify row counts match production
docker exec postgres psql -U devtools -d devtools -c "SELECT COUNT(*) FROM agent_registry;"
docker exec postgres-test psql -U devtools -d devtools -c "SELECT COUNT(*) FROM agent_registry;"

# 4. Document results in Linear
# 5. Cleanup
docker compose -f deploy/docker-compose.test.yml down -v
```

### Quarterly Full Recovery Drill

```bash
# 1. Provision test droplet (smallest size)
# 2. Follow "Scenario 2: Complete Droplet Loss" procedure
# 3. Validate all services functional
# 4. Time the recovery process
# 5. Document lessons learned
# 6. Destroy test droplet
```

## Backup Verification

**Automated Daily Checks**:

```bash
# Runs at 3 AM daily
0 3 * * * /opt/Dev-Tools/support/scripts/backup/verify-backups.sh

# Checks:
# - Backup files exist
# - Files not corrupted (checksum)
# - Files within size ranges
# - Retention policy applied
```

**Manual Monthly Verification**:

- [ ] Restore database to test environment
- [ ] Verify data integrity
- [ ] Test secrets decryption
- [ ] Confirm DO Spaces backups accessible

## Contact Information

**Emergency Escalation**:

1. **Primary**: alex@appsmithery.co (SMS alerts enabled)
2. **Backup**: [Secondary contact if available]

**Service Providers**:

- **Hosting**: DigitalOcean (support@digitalocean.com)
- **Domain**: [DNS provider support]
- **Monitoring**: LangSmith (support@langchain.com)

## Recovery Tools Checklist

- [ ] SSH keys to droplet (`~/.ssh/github-actions-deploy`)
- [ ] DigitalOcean API token
- [ ] Encrypted secrets backup (offline storage)
- [ ] GitHub repository access
- [ ] Docker Hub credentials
- [ ] Linear API token (for incident tracking)

## Post-Incident Actions

After any disaster recovery:

1. Document timeline in Linear issue
2. Update runbooks with learnings
3. Test prevention measures
4. Schedule team post-mortem (within 48 hours)
5. Update RTO/RPO if needed
6. Verify all backups current

## Appendix: Backup Scripts

### A. PostgreSQL Backup Script

Location: `support/scripts/backup/postgres-backup.sh`

```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d-%H%M%S)
BACKUP_DIR="/opt/backups/postgres"
mkdir -p $BACKUP_DIR

docker exec postgres pg_dump -U devtools devtools | gzip > $BACKUP_DIR/devtools-$DATE.sql.gz

# Cleanup old backups (keep 7 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

# Upload to DO Spaces (if configured)
# s3cmd put $BACKUP_DIR/devtools-$DATE.sql.gz s3://dev-tools-backups/
```

### B. Volume Backup Script

Location: `support/scripts/backup/volume-backup.sh`

```bash
#!/bin/bash
DATE=$(date +%Y-%m-%d)
BACKUP_DIR="/opt/backups/volumes"
mkdir -p $BACKUP_DIR

VOLUMES="orchestrator-data postgres-data redis-data prometheus-data loki-data"

for VOL in $VOLUMES; do
    docker run --rm -v $VOL:/source -v $BACKUP_DIR:/backup alpine \
        tar czf /backup/$VOL-$DATE.tar.gz -C /source .
done

# Cleanup old backups (keep 7 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

## References

- [Secrets Rotation Guide](./SECRETS_ROTATION.md)
- [Production Checklist](./PRODUCTION_CHECKLIST.md)
- [DigitalOcean Droplet Backups](https://docs.digitalocean.com/products/images/backups/)
- [Docker Volume Backup Best Practices](https://docs.docker.com/storage/volumes/#backup-restore-or-migrate-data-volumes)
