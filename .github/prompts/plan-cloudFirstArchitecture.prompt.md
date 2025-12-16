# Plan: Cloud-First Architecture Optimization for 2GB Droplet

Migrate storage and observability to cloud services, eliminate redundant infrastructure, optimize for traceability and LLM fine-tuning during beta.

## Current State Analysis

### Droplet Resource Usage (45.55.173.72)

**Disk**: 20GB used / 49GB total (40% utilization) - **30GB free, plenty of space**

- Docker images: 6.7GB (4.6GB reclaimable)
- Docker volumes: 58MB (PostgreSQL + Redis data)
- Build cache: 735MB (100% reclaimable)

**Memory**: 1.1GB used / 1.9GB total (58% utilization) - **Operating near capacity**

- System overhead: ~800MB
- Docker containers: ~741MB actual usage (see breakdown below)
- Swap: 192MB used (⚠️ swapping indicates memory pressure)

**Current Docker Container Memory Usage:**
| Container | Actual Usage | Limit | % of Limit | Status |
|-----------|--------------|-------|------------|--------|
| orchestrator | 195 MB | 2 GB | 10% | ✅ Healthy, plenty of headroom |
| rag-context | 139 MB | 512 MB | 27% | ✅ Healthy |
| agent-registry | 47 MB | 512 MB | 9% | ✅ Under-utilized |
| state-persistence | 43 MB | 512 MB | 8% | ✅ Under-utilized |
| langgraph | 55 MB | 256 MB | 21% | ✅ Healthy |
| grafana | 68 MB | 256 MB | 26% | ⚠️ Observability (redundant) |
| prometheus | 47 MB | 256 MB | 18% | ⚠️ Observability (redundant) |
| loki | 38 MB | 256 MB | 15% | ⚠️ Observability (redundant) |
| promtail | 22 MB | 256 MB | 8% | ⚠️ Observability (redundant) |
| postgres | 35 MB | 256 MB | 14% | ✅ Healthy |
| redis | 7 MB | 128 MB | 5% | ✅ Healthy |
| caddy | 44 MB | 256 MB | 17% | ✅ Healthy |
| oauth2-proxy | 4 MB | 256 MB | 2% | ⚠️ Observability (redundant) |

**Key Findings:**

1. **Disk is NOT an issue** - 30GB free, only 20GB/49GB used
2. **Memory is the constraint** - 1.1GB/1.9GB used, system is swapping (192MB in swap)
3. **Observability stack uses 180MB** (grafana 68 + prometheus 47 + loki 38 + promtail 22 + oauth2-proxy 4)
4. **Storage services use 85MB** (postgres 35 + redis 7 + state-persistence 43)
5. **Compute services are healthy** - orchestrator, rag-context, langgraph all stable

### Current Observability Stack Functions

**What Local Stack Provides:**

1. **Prometheus (47 MB actual, 256 MB limit)**

   - Scrapes metrics from all services every 15 seconds
   - Stores 15 days of metrics on disk
   - Provides `/metrics` endpoint for queries
   - Powers Grafana dashboards
   - **Exports to Grafana Cloud** via Alloy agent

2. **Grafana (68 MB actual, 256 MB limit)**

   - Visualizes Prometheus metrics in dashboards
   - Provides web UI at https://codechef.appsmithery.co/grafana
   - Stores dashboard configurations locally
   - **Redundant** - dashboards already exist in Grafana Cloud (https://appsmithery.grafana.net)

3. **Loki (38 MB actual, 256 MB limit)**

   - Aggregates logs from all Docker containers
   - Stores logs on disk for 7 days
   - Provides log search and filtering
   - Integrates with Grafana for log visualization

4. **Promtail (22 MB actual, 256 MB limit)**

   - Collects logs from Docker containers (via /var/log/docker)
   - Ships logs to Loki
   - Labels logs with container names, service names

5. **oauth2-proxy (4 MB actual, 256 MB limit)**
   - Provides authentication for Prometheus UI
   - Protects internal metrics endpoints
   - **Not critical** - metrics endpoints should be internal-only anyway

**Cloud Alternatives Already Configured:**

- ✅ **Grafana Cloud** (https://appsmithery.grafana.net) - Receiving metrics from Alloy agent
- ✅ **LangSmith** (https://smith.langchain.com) - LLM tracing and evaluation
- ✅ **Qdrant Cloud** (us-east4-0.gcp.cloud.qdrant.io) - Vector database

**What's Redundant:**

- Local Prometheus → **Grafana Cloud receives same metrics**
- Local Grafana → **Grafana Cloud has same dashboards**
- Local Loki/Promtail → **Could use Grafana Cloud Logs (free tier: 50GB/mo)**

### PostgreSQL Current Setup

- **Location**: Docker container on droplet (`postgres:16-alpine`)
- **Actual memory usage**: 35 MB (13% of 256 MB limit)
- **Data size**: ~58 MB in volumes
- **Purpose**: LangGraph checkpointing, workflow state, agent registry
- **Backup strategy**: ❌ None currently
- **Migration target**: Managed PostgreSQL (Neon, Supabase, or DigitalOcean Managed DB)

### Redis Current Setup

- **Location**: Docker container on droplet (`redis:7-alpine`)
- **Actual memory usage**: 7 MB (5% of 128 MB limit)
- **Persistence**: AOF + RDB to disk
- **Purpose**: Event bus, agent heartbeats, caching
- **Migration target**: Upstash (serverless Redis, 256MB free tier)

## Steps

### 1. Eliminate Redundant Observability Stack (First Priority)

**Rationale**: Already using Grafana Cloud, local stack is redundant
**Risk**: Low - metrics already flowing to cloud
**Time**: 1-2 hours

**Changes to docker-compose.yml:**

- Remove `prometheus`, `grafana`, `loki`, `promtail`, `oauth2-proxy` services
- Add log rotation to all remaining services:
  ```yaml
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "3"
  ```
- Update restart policies to `always` (auto-restart even after manual stops)
- Verify Grafana Cloud is receiving metrics: Check https://appsmithery.grafana.net
- Verify LangSmith traces working: Check https://smith.langchain.com
- Update deployment scripts to remove health checks for removed services
- Restart services: `docker compose down && docker compose up -d`
- **Frees ~180MB actual RAM** (180MB current usage → 0MB)
- **Eliminates 1.28GB memory limits** (reduces pressure on system)

**Post-migration verification:**

- Grafana Cloud dashboards still updating
- LangSmith traces still recording
- No gaps in metrics collection
- Log files rotating properly (check `/var/lib/docker/containers/*/`)

### 2. Evaluate Storage Migration Need (Optional)

**Current state**: PostgreSQL (35MB actual) and Redis (7MB actual) running stable
**Total memory used**: 85MB (postgres 35 + redis 7 + state-persistence 43)
**Question**: Is migration worth the complexity?

**Option A: Keep Local (Recommended for Beta)**

- ✅ Currently stable and performant
- ✅ Low latency (1ms vs 20-100ms for cloud)
- ✅ Zero additional cost
- ✅ Simple architecture
- ❌ No automated backups
- ❌ Single point of failure

**Option B: Migrate to Managed Services (+$25-30/mo)**

- PostgreSQL → Neon Free Tier or Supabase Pro ($25/mo)
- Redis → Upstash Free (256MB free tier)
- ✅ Automated backups
- ✅ Better disaster recovery
- ❌ Added latency (+20-100ms per operation)
- ❌ Monthly cost increase
- ❌ Migration complexity

**Recommendation**: **DEFER migration until post-beta** unless backup/DR is critical

**If keeping local (recommended), add optimizations:**

**PostgreSQL Tuning** (add to docker-compose.yml):

```yaml
postgres:
  image: postgres:16-alpine
  environment:
    # Disk-based caching optimizations for 2GB droplet
    - POSTGRES_SHARED_BUFFERS=64MB
    - POSTGRES_EFFECTIVE_CACHE_SIZE=128MB
    - POSTGRES_WORK_MEM=2MB
    - POSTGRES_MAINTENANCE_WORK_MEM=32MB
    - POSTGRES_MAX_CONNECTIONS=50
  command: >
    postgres
    -c shared_buffers=64MB
    -c effective_cache_size=128MB
    -c work_mem=2MB
    -c maintenance_work_mem=32MB
    -c max_connections=50
    -c checkpoint_completion_target=0.9
    -c wal_buffers=2MB
  restart: always
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U devtools -d devtools"]
    interval: 10s
    timeout: 5s
    retries: 5
```

**Redis Tuning** (add to docker-compose.yml):

```yaml
redis:
  image: redis:7-alpine
  command: >
    redis-server
    --appendonly yes
    --appendfsync everysec
    --maxmemory 64mb
    --maxmemory-policy allkeys-lru
    --save 900 1
    --save 300 10
    --save 60 10000
  restart: always
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
```

**Volume Optimization** (use host paths for better performance):

```yaml
volumes:
  postgres-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/code-chef/data/postgres
  redis-data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /opt/code-chef/data/redis
```

**Setup commands:**

```bash
ssh root@45.55.173.72 "mkdir -p /opt/code-chef/data/{postgres,redis,orchestrator}"
```

**If proceeding with cloud migration:**

- Export PostgreSQL: `ssh root@45.55.173.72 "docker exec deploy-postgres-1 pg_dump -U devtools devtools > /tmp/backup.sql"`
- Set up managed database (Neon/Supabase)
- Update environment variables in config/env/.env
- Remove postgres, redis, state-persistence from docker-compose.yml
- Frees 85MB actual RAM (512MB+ in limits)

### 3. Consolidate agent-registry (Optional)

**Current usage**: 47MB actual, 512MB limit
**Risk**: Medium - requires refactoring
**Time**: 3-6 hours
**Benefit**: Frees 47MB actual (512MB limit)

**Question**: Is this worth the refactoring effort?

- Agent registry provides service discovery for agents
- Could merge into orchestrator as in-process registry
- Alternative: Keep as separate service, it's only using 47MB

**Recommendation**: **SKIP for beta** - not worth complexity for 47MB savings

### 4. Reclaim Docker Disk Space (Immediate Win)

**Current state**: 4.6GB reclaimable images + 735MB build cache = **5.3GB reclaimable**
**Risk**: None
**Time**: 5 minutes

```bash
ssh root@45.55.173.72 "docker system prune -a --volumes -f"
```

This removes:

- Unused images (4.6GB)
- Build cache (735MB)
- Unused volumes (minimal)

### 5. Apply Container Optimizations

**Rationale**: Improve reliability and performance
**Risk**: Low - standard Docker best practices
**Time**: 30 minutes

**Update all service configurations in docker-compose.yml:**

1. **Restart policies** - Change to `always` for all services:

   ```yaml
   restart: always # Auto-restart even after manual stops
   ```

2. **Health check dependencies** - Ensure proper startup order:

   ```yaml
   orchestrator:
     depends_on:
       rag-context:
         condition: service_healthy
       state-persistence:
         condition: service_healthy
       postgres:
         condition: service_healthy
       redis:
         condition: service_healthy
   ```

3. **Health check timeouts** - Adjust for 2GB droplet:

   ```yaml
   healthcheck:
     interval: 30s # Check every 30s (was 15s)
     timeout: 10s # Wait up to 10s for response
     retries: 5 # Retry 5 times before marking unhealthy
     start_period: 60s # Grace period for startup
   ```

4. **Log rotation** - Already added in Step 1 for all services

5. **Memory optimizations** - Keep current limits, already well-configured

### 6. Deploy and Validate

- SSH to droplet: `ssh root@45.55.173.72`
- Create data directories: `mkdir -p /opt/code-chef/data/{postgres,redis,orchestrator}`
- Pull updated docker-compose: `cd /opt/Dev-Tools && git pull`
- Restart services: `docker compose down && docker compose up -d`
- Wait for health checks: `watch -n 2 'docker compose ps'` (wait for all "healthy")
- Verify health endpoints:
  - `curl http://localhost:8001/health` (orchestrator)
  - `curl http://localhost:8007/health` (rag-context)
  - `curl http://localhost:8010/health` (langgraph)
- Test extension via VS Code @chef chat
- Confirm LangSmith traces: https://smith.langchain.com
- Monitor memory for 24 hours: `watch -n 5 'free -h && docker stats --no-stream'`

## Expected Results

### Memory Allocation (After Phase 1 Only - Remove Observability)

| Service                     | Current Actual          | Current Limit           | After Migration                     |
| --------------------------- | ----------------------- | ----------------------- | ----------------------------------- |
| orchestrator                | 195 MB                  | 2 GB                    | 195 MB (no change)                  |
| rag-context                 | 139 MB                  | 512 MB                  | 139 MB (no change)                  |
| langgraph                   | 55 MB                   | 256 MB                  | 55 MB (no change)                   |
| agent-registry              | 47 MB                   | 512 MB                  | 47 MB (keep)                        |
| state-persistence           | 43 MB                   | 512 MB                  | 43 MB (keep)                        |
| postgres                    | 35 MB                   | 256 MB                  | 35 MB (keep)                        |
| caddy                       | 44 MB                   | 256 MB                  | 44 MB (no change)                   |
| redis                       | 7 MB                    | 128 MB                  | 7 MB (keep)                         |
| **Observability (removed)** | **180 MB**              | **1.28 GB**             | **0 MB** ✅                         |
| **TOTAL**                   | **745 MB** → **565 MB** | **5.5 GB** → **4.2 GB** | **-180 MB actual, -1.28 GB limits** |

**Droplet Status After Migration:**

- **Memory used**: 565MB containers + ~800MB system = **1.36GB / 1.9GB (72%)**
- **Memory free**: ~540MB (vs 87MB currently)
- **Swap usage**: Should drop to 0 (vs 192MB currently)
- **Result**: ✅ **System no longer under memory pressure**

### Cost Comparison

| Item                     | Current        | After Phase 1 Only | Change    |
| ------------------------ | -------------- | ------------------ | --------- |
| DigitalOcean Droplet 2GB | $18/mo         | $18/mo             | -         |
| Qdrant Cloud             | $25/mo         | $25/mo             | -         |
| LangSmith                | $99/mo         | $99/mo             | -         |
| OpenRouter               | ~$50/mo        | ~$50/mo            | -         |
| Grafana Cloud            | $0 (free tier) | $0 (free tier)     | -         |
| Linear                   | $8/mo          | $8/mo              | -         |
| **TOTAL**                | **$200/mo**    | **$200/mo**        | **$0** ✅ |

**If also doing Phase 2 (storage migration):**
| Item | Cost/mo |
|------|---------|
| Supabase Pro or Neon | +$0-25 |
| Upstash Redis | +$0 (free) |
| **TOTAL** | **$200-225/mo** |

## Further Considerations

### 1. Observability Trade-offs

**Question**: Can we live without local Prometheus/Grafana during beta?

- ✅ **Yes** - Grafana Cloud already receiving metrics
- ✅ **Yes** - LangSmith provides LLM tracing (more important for beta)
- ⚠️ **Maybe** - Lose ability to query historical metrics if Grafana Cloud has issues
- **Recommendation**: Proceed with removal, Grafana Cloud is reliable

### 2. Storage Migration Priority

**Question**: Migrate PostgreSQL/Redis now or later?

- **Current state**: Only using 85MB total, stable performance
- **Backup risk**: No automated backups currently
- **Cost**: +$0-25/mo for managed services
- **Latency impact**: +20-100ms per operation
- **Recommendation**: **DEFER to post-beta** unless backups are critical

### 3. Disk Space Management

**Question**: 5.3GB reclaimable via docker prune - safe to remove?

- **Yes** - These are unused images and build cache
- **Impact**: Faster rebuilds after prune (one-time cost)
- **Recommendation**: Run `docker system prune -a -f` immediately

### 4. Swap Usage Concern

**Current**: 192MB in swap indicates memory pressure
**After Phase 1**: Should drop to 0MB swap (540MB free RAM)
**Question**: If swap persists after observability removal, need to investigate why

### 5. Orchestrator Headroom

**Current**: 195MB used / 2GB limit (10% utilization)
**Question**: Does orchestrator need 2GB limit or can we reduce?

- **Keep 2GB**: Allows for LLM model caching, tool loading spikes
- **Reduce to 1GB**: Risk of OOM during heavy workflows
- **Recommendation**: Keep 2GB, orchestrator is the core service

### 6. Future Scaling Path

**When to upgrade droplet?**

- If swap usage returns after observability removal
- If orchestrator consistently uses >1.5GB
- If adding new services (e.g., separate training service)
- **Upgrade path**: 2GB ($18) → 4GB ($24) = +$6/mo

## Success Criteria

**Configuration Changes:**

- [ ] Observability stack removed from docker-compose.yml
- [ ] Log rotation added to all remaining services (10MB max, 3 files)
- [ ] Restart policies changed to `always` for all services
- [ ] Health check dependencies properly configured
- [ ] PostgreSQL tuning applied (64MB shared_buffers, 50 max_connections)
- [ ] Redis LRU eviction configured (64MB maxmemory, allkeys-lru)
- [ ] Volume paths updated to /opt/code-chef/data/\* structure

**Deployment Validation:**

- [ ] Data directories created on droplet: /opt/code-chef/data/{postgres,redis,orchestrator}
- [ ] All services restart successfully after changes
- [ ] orchestrator health check returns 200 OK (within 60s start_period)
- [ ] rag-context health check returns 200 OK
- [ ] langgraph health check returns 200 OK
- [ ] postgres health check returns healthy (pg_isready)
- [ ] redis health check returns healthy (redis-cli ping)
- [ ] Grafana Cloud still receiving metrics (verify in https://appsmithery.grafana.net)
- [ ] LangSmith traces still recording (verify in https://smith.langchain.com)
- [ ] VS Code extension connects and responds to @chef messages

**Performance Validation:**

- [ ] Memory usage drops to ~565MB containers + 800MB system = <1.4GB total
- [ ] Swap usage drops to 0MB (from 192MB)
- [ ] Free RAM increases to ~540MB (from 87MB)
- [ ] No OOM kills in first 48 hours of operation
- [ ] Workflow execution latency unchanged (<5 seconds per step)
- [ ] PostgreSQL query performance stable (check with \timing in psql)
- [ ] Redis hit rate >80% (check with INFO stats)
- [ ] Log files rotating properly (check file sizes in /var/lib/docker/containers/)
- [ ] Docker disk cleanup completes successfully

## Rollback Plan

**If observability removal causes issues:**

1. **Revert docker-compose.yml**: `cd /opt/Dev-Tools && git checkout HEAD~1 deploy/docker-compose.yml`
2. **Restart services**: `docker compose up -d prometheus grafana loki promtail oauth2-proxy`
3. **Verify health**: `curl http://localhost:9090/-/healthy` (Prometheus)
4. **Time estimate**: 5-10 minutes to rollback

**Note**: Rollback is low-risk because Grafana Cloud already has all metrics/dashboards

## Implementation Timeline

**Phase 1 (Observability Removal) - IMMEDIATE PRIORITY**

- Remove services from docker-compose.yml: 15 minutes
- Git commit and push: 5 minutes
- SSH to droplet and pull changes: 5 minutes
- Restart services: 5 minutes
- Verify health and metrics: 15 minutes
- **Total: 45 minutes to 1 hour**

**Phase 2 (Storage Migration) - DEFER TO POST-BETA**

- Only if backup/DR becomes critical
- Estimated: 4-6 hours (export, setup managed services, import, test)

**Phase 3 (Optional) - NOT RECOMMENDED FOR BETA**

- agent-registry consolidation: 3-6 hours
- Docker disk cleanup: 5 minutes (run anytime)

## Next Actions

### Immediate (This Week)

1. ✅ **Verify Grafana Cloud working**: Check https://appsmithery.grafana.net shows live metrics
2. ✅ **Verify LangSmith working**: Check https://smith.langchain.com shows recent traces
3. ✅ **Backup current state**: `ssh root@45.55.173.72 "docker compose config > /tmp/docker-compose-backup.yml"`
4. 🔲 **Update docker-compose.yml**:
   - Remove observability stack (5 services)
   - Add log rotation to all services
   - Change restart policies to `always`
   - Add health check dependencies
   - Apply PostgreSQL tuning parameters
   - Apply Redis LRU configuration
   - Update volume paths to /opt/code-chef/data/\*
5. 🔲 **Prepare droplet**: `ssh root@45.55.173.72 "mkdir -p /opt/code-chef/data/{postgres,redis,orchestrator}"`
6. 🔲 **Deploy to droplet**: Git push, SSH, pull, restart
7. 🔲 **Monitor for 48 hours**: Watch memory, swap, service health, log rotation
8. 🔲 **Run disk cleanup**: `docker system prune -a -f`

### Post-Beta (Future)

1. Evaluate storage migration (PostgreSQL/Redis) if backups become critical
2. Consider 4GB droplet upgrade if memory pressure returns
3. Set up automated backup validation for PostgreSQL
4. Document disaster recovery procedures
