# Droplet Reboot Procedure

**Droplet**: 45.55.173.72 (alex@appsmithery.co)  
**Current Issue**: OOM crashes, Node processes killed  
**Goal**: Clean reboot + infrastructure migration prep

## Pre-Reboot Status

**Current State**:
- 11 Docker containers consuming ~2.5GB RAM on 2GB droplet
- Multiple OOM kills (Node processes at 4493MB VM)
- SSH timeout, console UI hanging
- Services down: orchestrator, feature-dev, code-review, infrastructure, cicd, documentation, rag, state, gateway, postgres, qdrant

**Migration Plan**:
- Target: 3 containers (~850MB total)
- Architecture decision deferred (sync vs async sub-agents)
- Infrastructure scaffolding complete (LangGraph, Qdrant Cloud, PostgreSQL checkpointing)

## Reboot Procedure

### 1. Power Cycle Droplet

**Via DigitalOcean Console**:
1. Navigate to: https://cloud.digitalocean.com/droplets
2. Select droplet: `do-mcp-gateway` (45.55.173.72)
3. Click "Power" → "Power Cycle"
4. Wait for droplet to restart (~2-3 minutes)

**Verify Reboot**:
```powershell
# Test SSH connection
ssh alex@45.55.173.72

# Check uptime (should be recent)
uptime

# Check memory status
free -h
```

### 2. Post-Reboot Health Check

**System Resources**:
```bash
# Memory usage
free -h
# Expected: ~200MB used (OS only, no containers)

# Disk usage
df -h
# Expected: /dev/vda1 with ~20% usage

# Docker status
sudo systemctl status docker
# Expected: active (running)
```

**Container Status**:
```bash
cd /opt/Dev-Tools

# Check containers (should be down)
docker-compose ps
# Expected: No containers running

# Check volumes
docker volume ls
# Expected: orchestrator-data, mcp-config, qdrant-data, postgres-data
```

### 3. Apply Infrastructure Changes

**Update Docker Compose (Qdrant Cloud Migration)**:
```bash
cd /opt/Dev-Tools/compose

# Backup current compose file
cp docker-compose.yml docker-compose.yml.backup

# Edit to remove local Qdrant
# (This will be done via file edit from local machine)
```

**Apply PostgreSQL Checkpointing Schema**:
```bash
# Start postgres only
docker-compose up -d postgres

# Wait for postgres to initialize
sleep 10

# Apply LangGraph checkpointing schema
docker exec -i postgres psql -U devtools -d devtools < /opt/Dev-Tools/config/state/langgraph_checkpointing.sql

# Verify schema
docker exec -i postgres psql -U devtools -d devtools -c "\dt checkpoints.*"
# Expected: checkpoints, checkpoint_writes, checkpoint_metadata tables
```

**Update Environment Variables**:
```bash
cd /opt/Dev-Tools/config/env

# Verify Qdrant Cloud credentials
grep QDRANT .env
# Expected: QDRANT_URL and QDRANT_API_KEY

# Verify Gradient AI key
grep GRADIENT_API_KEY .env
# Expected: Gradient API key present

# Verify Langfuse keys
grep LANGFUSE .env
# Expected: LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY
```

### 4. Selective Service Startup

**Phase 1: Core Infrastructure Only**
```bash
cd /opt/Dev-Tools/compose

# Start only essential services
docker-compose up -d postgres gateway-mcp

# Wait for services to stabilize
sleep 15

# Check health
curl http://localhost:8000/health
# Expected: {"status": "healthy", "mcp_gateway": "connected"}

# Check memory usage
docker stats --no-stream
# Expected: postgres ~150MB, gateway ~120MB, total ~270MB
```

**Phase 2: Add Orchestrator**
```bash
# Start orchestrator only
docker-compose up -d orchestrator

# Wait for startup
sleep 10

# Check health
curl http://localhost:8001/health
# Expected: {"status": "healthy", "mcp_gateway": "connected"}

# Check memory usage
docker stats --no-stream
# Expected: Total ~450MB with orchestrator
```

**Phase 3: Monitor Before Adding More**
```bash
# Watch memory for 5 minutes
watch -n 30 'docker stats --no-stream'

# Check for OOM events
dmesg | grep -i "out of memory"
# Expected: No new OOM kills

# If stable, proceed to add other agents
# If unstable, stop and troubleshoot
```

### 5. Full Stack Startup (If Memory Allows)

**Only if Phase 1-3 are stable**:
```bash
# Start remaining agents one at a time
docker-compose up -d feature-dev
sleep 30
docker stats --no-stream

docker-compose up -d code-review
sleep 30
docker stats --no-stream

# Continue for infrastructure, cicd, documentation
# Monitor memory after each addition
```

**Add RAG (Optional - high memory usage)**:
```bash
# Only if memory allows (not recommended on 2GB droplet)
docker-compose up -d rag-context
```

**Add State Persistence (Optional - will be replaced by LangGraph)**:
```bash
# Skip this if using LangGraph checkpointing
# docker-compose up -d state-persistence
```

### 6. Validate Deployment

**Health Checks**:
```bash
# Gateway
curl http://localhost:8000/health

# Orchestrator
curl http://localhost:8001/health

# Feature Dev
curl http://localhost:8002/health

# Code Review
curl http://localhost:8003/health

# Infrastructure
curl http://localhost:8004/health

# CICD
curl http://localhost:8005/health

# Documentation
curl http://localhost:8006/health
```

**Frontend Access**:
```bash
# Test production landing page
curl http://45.55.173.72/production-landing.html

# Test agent cards
curl http://45.55.173.72/agents.html

# Test MCP servers page
curl http://45.55.173.72/servers.html
```

**Langfuse Traces**:
```bash
# Send test task to orchestrator
curl -X POST http://localhost:8001/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-trace-001",
    "description": "Test trace after reboot",
    "context": {"test": true}
  }'

# Check Langfuse dashboard
# URL: https://us.cloud.langfuse.com
# Expected: New trace with task_id "test-trace-001"
```

**Prometheus Metrics**:
```bash
# Check Prometheus
curl http://localhost:9090/-/healthy
# Expected: Prometheus is Healthy.

# Check agent metrics
curl http://localhost:8001/metrics
# Expected: HTTP metrics from orchestrator
```

## Monitoring Strategy

**Continuous Memory Watch**:
```bash
# Run in separate terminal
watch -n 10 'free -h && echo "---" && docker stats --no-stream'
```

**OOM Detection**:
```bash
# Watch for new OOM kills
dmesg -w | grep -i "out of memory"
```

**Service Logs**:
```bash
# Orchestrator logs
docker-compose logs -f orchestrator

# Gateway logs
docker-compose logs -f gateway-mcp

# All agent logs
docker-compose logs -f
```

## Rollback Plan

**If OOM Persists**:
1. Stop all containers: `docker-compose down`
2. Start only gateway + postgres: `docker-compose up -d postgres gateway-mcp`
3. Do NOT start agent services
4. Proceed with consolidation migration (unified workflow)

**If Services Fail**:
1. Check logs: `docker-compose logs <service>`
2. Verify environment variables: `docker exec <service> env | grep GRADIENT`
3. Test service health endpoints
4. Restart individual service: `docker-compose restart <service>`

## Success Criteria

**Minimum Viable State**:
- ✅ Droplet responds to SSH
- ✅ Docker daemon running
- ✅ Gateway + Postgres healthy
- ✅ Orchestrator healthy
- ✅ No OOM kills in dmesg
- ✅ Memory usage < 1.5GB total

**Optimal State**:
- ✅ All 6 agents running
- ✅ All health checks passing
- ✅ Frontend pages accessible
- ✅ Langfuse traces recording
- ✅ Prometheus metrics collecting
- ✅ Memory usage stable < 2GB

**Migration Ready State**:
- ✅ PostgreSQL checkpointing schema applied
- ✅ Qdrant Cloud client configured
- ✅ LangGraph base infrastructure available
- ✅ Environment variables verified
- ✅ Architecture decision documented (pending)

## Next Steps After Reboot

1. **Verify Infrastructure**: Complete post-reboot health check
2. **Test Selective Startup**: Phase 1-3 from procedure above
3. **Monitor Stability**: Watch for 30 minutes before adding more services
4. **Decide Architecture**: Sync unified workflow vs async multi-agent
5. **Implement Migration**: Based on architecture decision
6. **Deploy Consolidated Stack**: Target 3 containers, ~850MB RAM

## Contact Info

- **SSH**: `ssh alex@45.55.173.72` or `ssh do-mcp-gateway`
- **Deployment Path**: `/opt/Dev-Tools`
- **Logs**: `/opt/Dev-Tools/compose` + `docker-compose logs`
- **Console**: https://cloud.digitalocean.com/droplets
