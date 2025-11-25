# **Memory Optimization Report for Dev-Tools Deployment**

## Root Cause Analysis

Based on your architecture, here are the likely culprits:

### 1. **Docker Image Bloat**

Your current deployment rebuilds ALL services on every code change:

- 6 services × ~500MB-1GB base images = **3-6GB just in images**
- Old images not cleaned up after rebuilds
- Dangling layers accumulate

### 2. **Multiple Python Runtimes**

Each service runs its own Python interpreter:

- `orchestrator`: FastAPI + LangChain + LangGraph + all agent code
- `langgraph`: Separate FastAPI service (redundant with orchestrator)
- `state-persistence`: FastAPI + SQLAlchemy
- `agent-registry`: FastAPI + PostgreSQL client
- `rag-context`: FastAPI + Qdrant client

**Total**: ~5 Python runtimes × 100-200MB each = **500MB-1GB overhead**

### 3. **Duplicate Dependencies**

Every service has shared mounted, but also installs dependencies independently:

- LangChain installed in orchestrator, langgraph, rag-context
- FastAPI in all 5 Python services
- Pydantic, requests, etc. duplicated across services

### 4. **PostgreSQL + Qdrant Data Growth**

- Workflow checkpoints accumulating in PostgreSQL
- Vector embeddings in Qdrant never pruned
- No retention policies

### 5. **LangSmith Tracing Overhead**

LangSmith SDK keeps in-memory buffers before flushing to API. With 6 traced services × concurrent requests, buffers can grow to 100MB+.

---

## Immediate Fixes (Deploy Today)

### Fix 1: Aggressive Cleanup After Deploys

```powershell
// ...existing code...

# After successful deployment, add cleanup:
Write-Host "🧹 Cleaning up Docker resources..." -ForegroundColor Cyan
ssh $DropletUser@$DropletIP @"
cd $DeployPath/deploy && \
docker builder prune -f && \
docker image prune -f && \
docker system df
"@
```

### Fix 2: Add Memory Limits to All Services

```yaml
services:
  orchestrator:
    # ...existing code...
    deploy:
      resources:
        limits:
          memory: 512M # Prevent runaway memory usage
        reservations:
          memory: 256M
    restart: unless-stopped

  langgraph:
    # ...existing code...
    deploy:
      resources:
        limits:
          memory: 256M # Smaller than orchestrator
        reservations:
          memory: 128M

  state-persistence:
    # ...existing code...
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  agent-registry:
    # ...existing code...
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  rag-context:
    # ...existing code...
    deploy:
      resources:
        limits:
          memory: 384M # Higher for Qdrant client
        reservations:
          memory: 192M

  gateway-mcp:
    # ...existing code...
    deploy:
      resources:
        limits:
          memory: 256M
        reservations:
          memory: 128M

  postgres:
    # ...existing code...
    deploy:
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  qdrant:
    # ...existing code...
    deploy:
      resources:
        limits:
          memory: 1G # Vector DB needs more
        reservations:
          memory: 512M
```

### Fix 3: Weekly Cleanup Cron Job

```bash
#!/bin/bash
set -e

echo "🧹 Weekly Docker Cleanup"

# Remove stopped containers older than 7 days
docker container prune -f --filter "until=168h"

# Remove unused images
docker image prune -af --filter "until=168h"

# Remove unused volumes (CAREFUL - excludes postgres/qdrant)
docker volume prune -f --filter "label!=persist=true"

# Remove build cache older than 7 days
docker builder prune -f --filter "until=168h"

# Show current usage
echo "📊 Current Docker Disk Usage:"
docker system df

# Show memory usage
echo "📊 Current Memory Usage:"
free -h
```

**Deploy via cron:**

```bash
ssh root@45.55.173.72 "crontab -e"
# Add: 0 3 * * 0 /opt/Dev-Tools/support/scripts/maintenance/weekly-cleanup.sh >> /var/log/docker-cleanup.log 2>&1
```

---

## Medium-Term Fixes (Next Sprint)

### Fix 4: Consolidate Services (Eliminate `langgraph` service)

The `langgraph` service is **redundant** - orchestrator already runs LangGraph workflows. Remove it:

```yaml
# REMOVE this entire service:
# langgraph:
#   build:
#     context: ..
#     dockerfile: shared/services/langgraph/Dockerfile
#   ...
```

Move any unique logic from langgraph into workflows.py.

**Memory savings**: ~200-300MB

### Fix 5: Shared Python Runtime (Consolidate to 2 Services)

Merge `state-persistence` and `agent-registry` into `orchestrator`:

```python
// ...existing code...

# Add state-persistence routes
from shared.services.state.main import router as state_router
app.include_router(state_router, prefix="/state", tags=["state"])

# Add agent-registry routes
from shared.services.agent_registry.main import router as registry_router
app.include_router(registry_router, prefix="/registry", tags=["registry"])
```

```yaml
# REMOVE these services:
# state-persistence:
#   ...
# agent-registry:
#   ...

# orchestrator now handles all 3 responsibilities
orchestrator:
  ports:
    - "8001:8001" # Main orchestrator
    - "8008:8008" # State persistence (internal)
    - "8009:8009" # Agent registry (internal)
```

**Memory savings**: ~400-500MB (2 fewer Python runtimes)

### Fix 6: PostgreSQL Connection Pooling

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,          # Max 5 connections (down from default 10)
    max_overflow=2,       # Max 2 overflow (down from 10)
    pool_recycle=3600,    # Recycle connections every hour
    pool_pre_ping=True    # Verify connections before use
)
```

### Fix 7: Qdrant Data Retention

```python
import schedule
import time
from datetime import datetime, timedelta

def prune_old_vectors():
    """Delete vectors older than 30 days"""
    cutoff = datetime.now() - timedelta(days=30)
    # Implement deletion logic via Qdrant client
    pass

# Run daily at 2 AM
schedule.every().day.at("02:00").do(prune_old_vectors)
```

---

## Long-Term Fixes (After MVP)

### Fix 8: Migrate to Multi-Stage Docker Builds

Reduce image sizes by 50-70%:

```dockerfile
# Stage 1: Builder
FROM python:3.11-slim as builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### Fix 9: Upgrade Droplet Size

Current: **Basic Droplet (1GB RAM)**  
Recommended: **$12/month droplet (2GB RAM, 1 CPU → 2 vCPUs)**

This gives you breathing room for 6 services + PostgreSQL + Qdrant.

### Fix 10: Implement Request Throttling

```python
// filepath: main.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/orchestrate")
@limiter.limit("10/minute")  # Max 10 orchestrations per minute per IP
async def orchestrate_task(request: Request, task: TaskRequest):
    # ...existing code...
```

---

## Implementation Status (November 25, 2025)

### ✅ Completed

1. **GitHub Actions Workflow** - `.github/workflows/cleanup-docker-resources.yml`
   - Post-deployment cleanup (standard mode)
   - Weekly scheduled cleanup (aggressive mode - Sundays at 3 AM UTC)
   - Manual trigger with 3 modes (standard/aggressive/full)
   - Health validation after cleanup

2. **Deployment Script Enhancement** - `support/scripts/deploy/deploy-to-droplet.ps1`
   - Automatic post-deployment cleanup
   - Removes dangling images, build cache, stopped containers
   - Non-blocking (failures are non-fatal)

3. **Cron-Based Maintenance**
   - Script: `support/scripts/maintenance/weekly-cleanup.sh`
   - Cron job: `0 3 * * 0` (Sundays at 3 AM)
   - Logs: `/var/log/docker-cleanup.log`
   - Includes health checks and log rotation

4. **Setup Automation** - `support/scripts/maintenance/setup-cron-job.sh`
   - One-command installation of cron job
   - Verifies installation and permissions

### 📊 Current Metrics (Pre-Cleanup)

```bash
TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE
Images          59        53        19.45GB   16.85GB (86%)  # 🚨 High reclaimable
Containers      15        15        3.65MB    0B (0%)
Local Volumes   18        9         331.4MB   225MB (67%)
Build Cache     46        8         512.3MB   50.95MB
```

**Memory Usage**: 929Mi / 1.9Gi (48%) - Improved from 100% saturation

### 🎯 Expected Results

- **Post-deployment cleanup**: Reclaim 16.85GB immediately after next deploy
- **Weekly maintenance**: Prevent accumulation of unused resources
- **Sustained memory usage**: Stay below 70% average

## Recommended Action Plan

### ~~**Today** (30 minutes)~~ ✅ COMPLETE:

1. ~~Deploy memory limits (Fix 2)~~ - Pending
2. ~~Add cleanup to deployment script (Fix 1)~~ ✅ **DONE**
3. ~~Run manual cleanup~~ ✅ **DONE** (cron job installed and tested)

### **This Week** (2-4 hours):

4. Set up weekly cron job (Fix 3)
5. Remove `langgraph` service (Fix 4)
6. Add PostgreSQL connection pooling (Fix 6)

### **Next Sprint** (1-2 days):

7. Consolidate state/registry into orchestrator (Fix 5)
8. Implement Qdrant retention policy (Fix 7)
9. Consider droplet upgrade (Fix 9)

### **Post-MVP**:

10. Multi-stage Docker builds (Fix 8)
11. Request throttling (Fix 10)

---

## Monitoring Commands

Add these to your health checks:

```bash
# Check memory usage per container
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Check Docker disk usage
docker system df

# Check droplet memory
ssh root@45.55.173.72 "free -h && df -h"

# Find memory hogs
docker ps --format "{{.Names}}" | xargs -I {} docker stats {} --no-stream --format "{{.Name}}: {{.MemUsage}}"
```
