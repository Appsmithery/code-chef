# Docker Deployment Guide

Complete guide for deploying the Dev-Tools MCP agent stack using Docker Compose.

## Prerequisites

- **Docker Engine:** 24.0 or higher
- **Docker Compose:** 2.20 or higher (V2 syntax)
- **System Requirements:**
  - 4GB RAM minimum (8GB recommended)
  - 10GB disk space for images and volumes
  - Network access for pulling base images

### Verify Installation

```bash
docker --version
docker-compose --version
```

**Windows PowerShell:**

```powershell
docker --version
docker compose version
```

---

## Quick Start

### 1. Navigate to Compose Directory

```bash
cd compose
```

### 2. Start All Services

```bash
docker-compose up -d
```

**Expected Output:**

```
[+] Running 9/9
 ✔ Network devtools-network      Created
 ✔ Volume mcp-config             Created
 ✔ Volume orchestrator-data      Created
 ✔ Container compose-gateway-mcp-1      Started
 ✔ Container compose-orchestrator-1     Started
 ✔ Container compose-feature-dev-1      Started
 ✔ Container compose-code-review-1      Started
 ✔ Container compose-infrastructure-1   Started
 ✔ Container compose-cicd-1             Started
 ✔ Container compose-documentation-1    Started
```

### 3. Verify Services

```bash
docker-compose ps
```

**Expected Output:**

```
NAME                         STATUS    PORTS
compose-gateway-mcp-1        Up        0.0.0.0:8000->8000/tcp
compose-orchestrator-1       Up        0.0.0.0:8001->8001/tcp
compose-feature-dev-1        Up        0.0.0.0:8002->8002/tcp
compose-code-review-1        Up        0.0.0.0:8003->8003/tcp
compose-infrastructure-1     Up        0.0.0.0:8004->8004/tcp
compose-cicd-1               Up        0.0.0.0:8005->8005/tcp
compose-documentation-1      Up        0.0.0.0:8006->8006/tcp
```

### 4. Health Check

**Linux/Mac:**

```bash
for port in 8000 8001 8002 8003 8004 8005 8006; do
  echo "Testing port $port..."
  curl -s http://localhost:$port/health | jq
done
```

**Windows PowerShell:**

```powershell
8000..8006 | ForEach-Object {
    Write-Host "Testing port $_..."
    Invoke-RestMethod "http://localhost:$_/health"
}
```

**Expected Response (per service):**

```json
{
  "status": "ok",
  "service": "orchestrator",
  "version": "1.0.0"
}
```

---

## DigitalOcean Container Registry (DOCR) Integration

| Item              | Value                                |
| ----------------- | ------------------------------------ |
| Default registry  | `registry.digitalocean.com/the-shop` |
| Compose variables | `DOCR_REGISTRY`, `IMAGE_TAG`         |
| CI workflow       | `.github/workflows/docr-build.yml`   |

### Why it matters

- **Single source of truth** – `compose/docker-compose.yml` now tags every build as `${DOCR_REGISTRY}/<service>:${IMAGE_TAG}` so local, staging, and prod environments all pull the same artifact.
- **Short‑lived auth** – `digitalocean/action-doctl@v2` plus `doctl registry login --expiry-seconds 1200` keeps CI pushes secure while matching [DigitalOcean’s documented flow](https://docs.digitalocean.com/products/container-registry/how-to/use-registry-docker-kubernetes/#docker-integration).
- **Kubernetes ready** – After [adding the secret to your DOKS cluster](https://docs.digitalocean.com/products/container-registry/how-to/use-registry-docker-kubernetes/#add-secret-control-panel) (or piping `doctl registry kubernetes-manifest | kubectl apply -f -`), workloads can reference DOCR images with no extra YAML changes.

### Local developer steps

```powershell
doctl registry login
docker compose build orchestrator
IMAGE_TAG=$(git rev-parse --short HEAD) DOCR_REGISTRY=registry.digitalocean.com/the-shop docker compose push orchestrator
```

> Replace the last line with the services you need to publish. Compose uses the `image:` field you set earlier, so both `build` and `push` reuse the same tag.

### GitHub Actions workflow

`.github/workflows/docr-build.yml` builds every service Dockerfile, tags it as:

```
registry.digitalocean.com/<REGISTRY_NAME>/<service>:<git-sha>
registry.digitalocean.com/<REGISTRY_NAME>/<service>:latest
```

It expects two repository secrets:

- `DIGITALOCEAN_ACCESS_TOKEN` – read/write DO API token.
- `REGISTRY_NAME` – DOCR namespace (`the-shop`, etc.).

Triggering a push to `main` (or running the workflow manually) will push fresh images; downstream deployment jobs can simply `docker compose pull && docker compose up -d` or roll out via Kubernetes.

---

## Service Architecture

### Ports & Services

| Port | Service        | Technology | Description               |
| ---- | -------------- | ---------- | ------------------------- |
| 8000 | MCP Gateway    | Node.js 18 | Linear OAuth, MCP routing |
| 8001 | Orchestrator   | FastAPI    | Task coordination         |
| 8002 | Feature-Dev    | FastAPI    | Code generation           |
| 8003 | Code-Review    | FastAPI    | Quality analysis          |
| 8004 | Infrastructure | FastAPI    | IaC generation            |
| 8005 | CI/CD          | FastAPI    | Pipeline automation       |
| 8006 | Documentation  | FastAPI    | Doc generation            |

### Docker Network

**Name:** `devtools-network`  
**Type:** Bridge  
**Purpose:** Enables service-to-service communication via DNS

**Service Hostnames (internal):**

- `gateway-mcp:8000`
- `orchestrator:8001`
- `feature-dev:8002`
- `code-review:8003`
- `infrastructure:8004`
- `cicd:8005`
- `documentation:8006`

### Persistent Volumes

| Volume              | Mount Point   | Service      | Purpose                      |
| ------------------- | ------------- | ------------ | ---------------------------- |
| `mcp-config`        | `/app/config` | gateway-mcp  | OAuth tokens, MCP config     |
| `orchestrator-data` | `/app/data`   | orchestrator | Task state, routing metadata |

---

## Common Operations

### View Logs

**All services:**

```bash
docker-compose logs -f
```

**Specific service:**

```bash
docker-compose logs -f orchestrator
docker-compose logs -f feature-dev
```

**Last 50 lines:**

```bash
docker-compose logs --tail=50 orchestrator
```

**Windows PowerShell:**

```powershell
# All services
docker-compose logs -f

# Specific service with last 50 lines
docker logs --tail 50 compose-orchestrator-1
```

### Stop Services

**Graceful shutdown:**

```bash
docker-compose down
```

**With volume cleanup (WARNING: deletes data):**

```bash
docker-compose down -v
```

### Restart Services

**All services:**

```bash
docker-compose restart
```

**Specific service:**

```bash
docker-compose restart orchestrator
```

### Rebuild After Code Changes

**Rebuild all images:**

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

**Rebuild specific service:**

```bash
docker-compose build --no-cache orchestrator
docker-compose up -d orchestrator
```

### Scale Services (if needed)

```bash
docker-compose up -d --scale feature-dev=3
```

---

## Testing & Validation

### 1. Health Check Script

**Linux/Mac:**

```bash
#!/bin/bash
# health-check.sh

SERVICES=("gateway-mcp:8000" "orchestrator:8001" "feature-dev:8002"
          "code-review:8003" "infrastructure:8004" "cicd:8005" "documentation:8006")

for service in "${SERVICES[@]}"; do
    port="${service##*:}"
    name="${service%%:*}"

    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health)

    if [ "$response" = "200" ]; then
        echo "✅ $name (port $port): Healthy"
    else
        echo "❌ $name (port $port): Unhealthy (HTTP $response)"
    fi
done
```

**Windows PowerShell:**

```powershell
# health-check.ps1

$services = @(
    @{Name="gateway-mcp"; Port=8000},
    @{Name="orchestrator"; Port=8001},
    @{Name="feature-dev"; Port=8002},
    @{Name="code-review"; Port=8003},
    @{Name="infrastructure"; Port=8004},
    @{Name="cicd"; Port=8005},
    @{Name="documentation"; Port=8006}
)

foreach ($svc in $services) {
    try {
        $response = Invoke-RestMethod "http://localhost:$($svc.Port)/health" -ErrorAction Stop
        Write-Host "✅ $($svc.Name) (port $($svc.Port)): Healthy" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ $($svc.Name) (port $($svc.Port)): Unhealthy" -ForegroundColor Red
    }
}
```

### 2. Orchestrator Integration Test

```bash
curl -X POST http://localhost:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Deploy new API endpoint with authentication",
    "priority": "high"
  }'
```

**Expected Response:**

```json
{
  "task_id": "uuid",
  "subtasks": [
    {
      "id": "uuid",
      "agent_type": "infrastructure",
      "description": "Infrastructure changes: Deploy new API endpoint...",
      "status": "pending"
    }
  ],
  "routing_plan": {
    "execution_order": ["uuid"],
    "estimated_duration_minutes": 5
  },
  "estimated_tokens": 12
}
```

### 3. Gateway OAuth Status

```bash
curl http://localhost:8000/oauth/linear/status
```

**Expected Response:**

```json
{
  "success": true,
  "status": {
    "stored": null,
    "developerFallback": true
  }
}
```

---

## Troubleshooting

### Issue: Services Won't Start

**Symptom:** `docker-compose up` fails with errors

**Solutions:**

1. **Check port conflicts:**

   ```bash
   # Linux/Mac
   netstat -tuln | grep '800[0-6]'

   # Windows
   netstat -an | findstr "800"
   ```

2. **Free up ports:**

   ```bash
   # Stop conflicting services
   docker ps -a
   docker stop <conflicting-container>
   ```

3. **Check Docker daemon:**
   ```bash
   docker info
   systemctl status docker  # Linux
   ```

### Issue: Build Failures

**Symptom:** `docker-compose build` errors

**Solutions:**

1. **Clean build cache:**

   ```bash
   docker system prune -a
   docker-compose build --no-cache
   ```

2. **Check Dockerfile paths:**

   - Ensure `context: ..` in docker-compose.yml
   - Verify `COPY agents/X/ /app/` paths in Dockerfiles

3. **Verify requirements.txt:**
   ```bash
   cat agents/orchestrator/requirements.txt
   # Should contain: fastapi, uvicorn, pydantic
   ```

### Issue: Service Unhealthy

**Symptom:** Health check returns 500 or connection refused

**Solutions:**

1. **Check service logs:**

   ```bash
   docker-compose logs orchestrator
   ```

2. **Inspect container:**

   ```bash
   docker exec -it compose-orchestrator-1 /bin/bash
   ps aux
   cat /app/main.py
   ```

3. **Verify Python dependencies:**
   ```bash
   docker exec compose-orchestrator-1 pip list
   ```

### Issue: Inter-Service Communication Fails

**Symptom:** Orchestrator can't reach other agents

**Solutions:**

1. **Verify network:**

   ```bash
   docker network inspect devtools-network
   ```

2. **Test internal DNS:**

   ```bash
   docker exec compose-orchestrator-1 ping feature-dev
   docker exec compose-orchestrator-1 curl http://feature-dev:8002/health
   ```

3. **Check firewall rules:**
   ```bash
   # Linux
   iptables -L
   ufw status
   ```

---

## Environment Configuration

### .env File Structure

Create `compose/.env` or edit `config/env/.env`:

```bash
# Service URLs (internal Docker network)
ORCHESTRATOR_URL=http://orchestrator:8001
FEATURE_DEV_URL=http://feature-dev:8002
CODE_REVIEW_URL=http://code-review:8003
INFRASTRUCTURE_URL=http://infrastructure:8004
CICD_URL=http://cicd:8005
DOCUMENTATION_URL=http://documentation:8006
MCP_GATEWAY_URL=http://gateway-mcp:8000

# Logging
LOG_LEVEL=info
DEBUG=false

# Linear OAuth (optional)
LINEAR_CLIENT_ID=your_client_id
LINEAR_CLIENT_SECRET=your_secret
LINEAR_REDIRECT_URI=http://localhost:8000/oauth/linear/callback

# PostgreSQL (future - Phase 4)
# POSTGRES_HOST=postgres
# POSTGRES_PORT=5432
# POSTGRES_DB=devtools
# POSTGRES_USER=admin
# POSTGRES_PASSWORD=changeme

# RAG Vector DB (future - Phase 4)
# VECTOR_DB_URL=http://qdrant:6333
# EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### Override Configuration

Create `compose/docker-compose.override.yml` for local customizations:

```yaml
version: "3.8"

services:
  orchestrator:
    environment:
      - DEBUG=true
      - LOG_LEVEL=debug
    volumes:
      - ../agents/orchestrator:/app:ro # Mount source for hot-reload

  feature-dev:
    environment:
      - DEBUG=true
      - LOG_LEVEL=debug
```

**Note:** Override file is gitignored, safe for local settings.

---

## Performance Tuning

### Resource Limits

Add to `docker-compose.yml`:

```yaml
services:
  orchestrator:
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 512M
        reservations:
          memory: 256M
```

### Build Optimization

**Multi-stage builds (example):**

```dockerfile
# Build stage
FROM python:3.11-slim AS builder
WORKDIR /build
COPY agents/orchestrator/requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
COPY agents/orchestrator/ /app/
WORKDIR /app
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Health Check Tuning

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 10s
```

---

## Backup & Restore

### Backup Volumes

```bash
cd scripts
./backup_volumes.sh
```

**Output:** `backups/YYYYMMDD_HHMMSS/`

**Windows PowerShell:**

```powershell
# Manual backup
docker run --rm -v mcp-config:/data -v ${PWD}/backups:/backup `
  ubuntu tar czf /backup/mcp-config-$(Get-Date -Format 'yyyyMMdd-HHmmss').tar.gz /data

docker run --rm -v orchestrator-data:/data -v ${PWD}/backups:/backup `
  ubuntu tar czf /backup/orchestrator-data-$(Get-Date -Format 'yyyyMMdd-HHmmss').tar.gz /data
```

### Restore from Backup

```bash
cd scripts
./restore_volumes.sh ./backups/20250113_040000
```

**Windows PowerShell:**

```powershell
# Stop services first
docker-compose down

# Restore volumes
docker run --rm -v mcp-config:/data -v ${PWD}/backups:/backup `
  ubuntu tar xzf /backup/mcp-config-20250113-040000.tar.gz -C /

docker run --rm -v orchestrator-data:/data -v ${PWD}/backups:/backup `
  ubuntu tar xzf /backup/orchestrator-data-20250113-040000.tar.gz -C /

# Restart services
docker-compose up -d
```

---

## Security Considerations

### 1. Network Isolation

- Services communicate via internal Docker network
- Only gateway port (8000) should be exposed externally in production
- Use reverse proxy (nginx/traefik) for TLS termination

### 2. Secrets Management

**DO NOT commit secrets to git**

Use Docker secrets or environment files:

```bash
echo "my_secret_value" | docker secret create linear_token -
```

Mount in compose:

```yaml
services:
  gateway-mcp:
    secrets:
      - linear_token

secrets:
  linear_token:
    external: true
```

### 3. Image Scanning

```bash
docker scan compose-orchestrator
trivy image compose-orchestrator
```

### 4. Container Hardening

- Run as non-root user in Dockerfiles
- Use read-only root filesystems where possible
- Minimize installed packages (slim base images)

---

## Production Deployment

### 1. Use Production-Ready Compose File

Create `docker-compose.prod.yml`:

```yaml
version: "3.8"

services:
  orchestrator:
    image: ghcr.io/yourorg/orchestrator:v1.0.0
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
```

### 2. Enable Monitoring

Add Prometheus/Grafana stack:

```yaml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=changeme
```

### 3. Deploy Command

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Next Steps

- **Phase 4:** Integrate RAG Context Manager and State Persistence Layer
- **Monitoring:** Add metrics collection and alerting
- **CI/CD:** Automate image builds and deployments
- **Testing:** Implement end-to-end workflow tests

---

## Support

- **Documentation:** `docs/`
- **Architecture:** `docs/ARCHITECTURE.md`
- **API Reference:** `docs/AGENT_ENDPOINTS.md`
- **Secrets Guide:** `docs/SECRETS_MANAGEMENT.md`

**Questions?** Open an issue in the repository.
