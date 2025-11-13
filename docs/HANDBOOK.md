# Dev-Tools Operational Handbook

## Daily Operations

### Starting the Stack

```bash
./scripts/up.sh
```

### Stopping the Stack

```bash
./scripts/down.sh
```

### Rebuilding Services

```bash
./scripts/rebuild.sh
```

## Backup & Restore

### Creating Backups

```bash
./scripts/backup_volumes.sh
```

Backups are stored in `./backups/YYYYMMDD_HHMMSS/`

### Restoring from Backup

```bash
./scripts/restore_volumes.sh ./backups/20250112_140000
```

## Troubleshooting

### Services Won't Start

1. Check Docker daemon: `systemctl status docker`
2. View logs: `cd compose && docker-compose logs`
3. Check port conflicts: `netstat -tulpn | grep :8000`

### Agent Not Responding

1. Check service status: `cd compose && docker-compose ps`
2. View agent logs: `docker-compose logs <agent-name>`
3. Restart specific service: `docker-compose restart <agent-name>`

### Dev Container Won't Attach

1. Ensure Remote-SSH connection is active
2. Check .devcontainer/devcontainer.json syntax
3. Rebuild container: VS Code → Dev Containers: Rebuild Container

### Volume Data Lost

1. Check volume exists: `docker volume ls`
2. Restore from backup: `./scripts/restore_volumes.sh <backup-dir>`

## Monitoring

### View All Logs

```bash
cd compose
docker-compose logs -f
```

### View Specific Agent Logs

```bash
docker-compose logs -f orchestrator
```

### Check Resource Usage

```bash
docker stats
```

## Maintenance

### Update Agent Code

1. Make changes to agent code
2. Rebuild: `./scripts/rebuild.sh`
3. Verify: Check agent logs

### Update Configuration

1. Edit files in `config/`
2. Restart affected services
3. Verify configuration load in logs

### Prune Old Images

```bash
docker image prune -a
```

## Security

### Secrets Management

- Never commit `secrets.json` or `.env` with real values
- Use template files: `.env.example`, `secrets.template.json`
- Store production secrets in secure vault
- Rotate API keys regularly

### SSH Keys

- Use SSH agent forwarding for Git operations
- Configure in devcontainer.json: `"forwardAgent": true`

## Performance Tuning

### Resource Limits

Edit `compose/docker-compose.yml` to add limits:

```yaml
services:
  orchestrator:
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G
```

### Scaling Services

```bash
cd compose
docker-compose up -d --scale feature-dev=3
```
