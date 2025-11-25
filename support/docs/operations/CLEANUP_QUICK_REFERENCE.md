# Docker Cleanup Quick Reference

## Automated Cleanup (Hands-Free)

### 1. GitHub Actions Workflow

**Trigger automatically after deployments** or run manually:

```bash
# Manual trigger via GitHub UI:
# Actions → Cleanup Docker Resources → Run workflow → Select cleanup type
```

**Cleanup Types:**

- `standard`: Post-deployment (dangling images, 1h old containers)
- `aggressive`: Weekly maintenance (7-day retention)
- `full`: Emergency mode (stops services, cleans all, restarts)

**Schedule**: Runs automatically every Sunday at 3 AM UTC

---

### 2. Deployment Script (Automatic)

**Built into** `support/scripts/deploy/deploy-to-droplet.ps1`

Runs after every successful deployment:

```powershell
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType auto
# Cleanup happens automatically at the end
```

---

### 3. Cron Job (Weekly)

**Installed on droplet**, runs every Sunday at 3 AM:

```bash
# Check cron job status
ssh root@45.55.173.72 "crontab -l"

# View cleanup logs
ssh root@45.55.173.72 "tail -f /var/log/docker-cleanup.log"

# Manually trigger cleanup
ssh root@45.55.173.72 "/opt/Dev-Tools/support/scripts/maintenance/weekly-cleanup.sh"
```

---

## Manual Cleanup Commands

### Quick Cleanup (Safe)

```bash
ssh root@45.55.173.72 << 'EOF'
docker image prune -f
docker builder prune -f
docker container prune -f --filter "until=1h"
docker system df
EOF
```

### Aggressive Cleanup (Reclaim More Space)

```bash
ssh root@45.55.173.72 << 'EOF'
cd /opt/Dev-Tools/deploy
docker image prune -af --filter "until=168h"
docker builder prune -af --filter "until=168h"
docker container prune -f --filter "until=168h"
docker network prune -f
docker system df
EOF
```

### Emergency Full Cleanup (Last Resort)

```bash
ssh root@45.55.173.72 << 'EOF'
cd /opt/Dev-Tools/deploy
docker compose down
docker system prune -af
docker builder prune -af
docker compose up -d
sleep 15
docker compose ps
EOF
```

---

## Monitoring Commands

### Check Resource Usage

```bash
# Docker disk usage
ssh root@45.55.173.72 "docker system df"

# Container memory usage
ssh root@45.55.173.72 "docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}'"

# Droplet memory/disk
ssh root@45.55.173.72 "free -h && df -h /"

# Find reclaimable space
ssh root@45.55.173.72 "docker system df -v | grep -E '(SIZE|RECLAIMABLE)'"
```

### Health Checks After Cleanup

```bash
# Check all service health endpoints
for port in 8000 8001 8007 8008 8009 8010; do
    echo -n "Port $port: "
    curl -sf http://45.55.173.72:$port/health > /dev/null && echo "✓ OK" || echo "✗ FAIL"
done

# Check container status
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose ps"
```

---

## Troubleshooting

### Cron Job Not Running

```bash
# Check cron service
ssh root@45.55.173.72 "systemctl status cron"

# Verify cron job exists
ssh root@45.55.173.72 "crontab -l | grep weekly-cleanup"

# Check for execution (next Sunday)
ssh root@45.55.173.72 "grep 'Weekly Docker Cleanup' /var/log/docker-cleanup.log | tail -5"

# Reinstall cron job
bash support/scripts/maintenance/setup-cron-job.sh
```

### Memory Still High After Cleanup

```bash
# 1. Check what's using memory
ssh root@45.55.173.72 "docker stats --no-stream --format 'table {{.Name}}\t{{.MemUsage}}' | sort -k2 -h -r"

# 2. Check for stopped containers
ssh root@45.55.173.72 "docker ps -a --filter 'status=exited'"

# 3. Run emergency cleanup
# (Use GitHub Actions workflow with 'full' mode)
```

### Services Unhealthy After Cleanup

```bash
# Check logs for errors
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose logs --tail=50 | grep ERROR"

# Restart affected service
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose restart <service_name>"

# Full stack restart if needed
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose down && docker compose up -d"
```

---

## Expected Results

### Post-Deployment Cleanup

- **Reclaimed**: 500MB-1GB per deployment
- **Time**: ~30 seconds
- **Frequency**: After every deploy

### Weekly Maintenance

- **Reclaimed**: 1-2GB (7-day accumulation)
- **Time**: ~2 minutes
- **Frequency**: Every Sunday 3 AM UTC

### Emergency Full Cleanup

- **Reclaimed**: Up to 16GB+ (all unused resources)
- **Time**: ~5 minutes (includes service restart)
- **Downtime**: ~30 seconds

---

## Files Reference

| File                           | Purpose                        | Location                       |
| ------------------------------ | ------------------------------ | ------------------------------ |
| `cleanup-docker-resources.yml` | GitHub Actions workflow        | `.github/workflows/`           |
| `deploy-to-droplet.ps1`        | Deployment script with cleanup | `support/scripts/deploy/`      |
| `weekly-cleanup.sh`            | Cron job script                | `support/scripts/maintenance/` |
| `setup-cron-job.sh`            | Cron installation script       | `support/scripts/maintenance/` |
| `docker-cleanup.log`           | Cleanup execution logs         | `/var/log/` (on droplet)       |

---

## Related Documentation

- [Memory Optimization Guide](./droplet-memory-optimization.md) - Complete analysis and implementation plan
- [Deployment Guide](../DEPLOYMENT_GUIDE.md) - Deployment procedures
- Linear Issue: [DEV-169](https://linear.app/dev-ops/issue/DEV-169/automated-disk-cleanup-after-deployments)
