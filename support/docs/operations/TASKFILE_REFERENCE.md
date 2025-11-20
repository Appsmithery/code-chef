# Taskfile Command Reference

Complete reference for all `task` commands available in the Dev-Tools project.

## Quick Start

```bash
# List all available commands
task

# Get detailed help for a command
task --summary <command-name>
```

---

## 📦 Build & Registry Commands

### `task build:all`

Build all agent images locally using Docker Compose definitions.

**Usage**: Development and testing local builds  
**Time**: ~5-10 minutes (first build), ~1-2 minutes (incremental)  
**Output**: Docker images tagged as `alextorelli28/appsmithery:<service>-latest`

```bash
task build:all
```

### `task build:push-dockerhub`

Push all images to Docker Hub registry under `alextorelli28/appsmithery`.

**Prerequisites**:

- `docker login` authenticated
- Images built locally via `task build:all`

**Usage**: Share images with team or deploy to external servers

```bash
task build:push-dockerhub
```

### `task build:push-docr`

Push images to DigitalOcean Container Registry.

**Prerequisites**:

- `doctl auth init` completed
- DOCR repository created
- Images built locally

**Usage**: Deploy to DigitalOcean droplets with faster pull times

```bash
task build:push-docr
```

---

## 🖥️ Local Stack Lifecycle

### `task local:up`

Start full local development stack with automatic health checks.

**What it does**:

1. Starts all 15+ services in detached mode
2. Waits 15 seconds for initialization
3. Runs health checks on all endpoints

**Ports opened**: 8000-8008 (agents), 9090 (Prometheus), 5432 (Postgres), 6379 (Redis), 3100 (Loki)

```bash
task local:up

# Check logs after startup
task local:logs
```

### `task local:down`

Stop all services and clean up orphaned containers.

**Safe operation**: Preserves volumes and data  
**Time**: ~10 seconds

```bash
task local:down
```

### `task local:rebuild`

Nuclear rebuild - stops services, rebuilds images without cache, restarts.

**Use when**:

- Python dependencies changed (`requirements.txt`)
- Dockerfile modifications
- Persistent issues with cached layers

**Time**: ~10-15 minutes

```bash
task local:rebuild
```

### `task local:logs`

Stream logs from all running services (press Ctrl+C to exit).

**Options**:

```bash
# Default: 50 lines from each service
task local:logs

# Follow specific service (in deploy/ directory)
cd deploy
docker compose logs -f orchestrator
```

### `task local:ps`

Show running services, their status, and port mappings.

```bash
task local:ps

# Example output:
# NAME                STATUS       PORTS
# orchestrator        Up 2 hours   0.0.0.0:8001->8001/tcp
# gateway-mcp         Up 2 hours   0.0.0.0:8000->8000/tcp
```

### `task local:clean`

⚠️ **DESTRUCTIVE**: Remove all containers, volumes, images, and build cache.

**⚠️ WARNING**: This deletes ALL local data including:

- PostgreSQL database
- Redis event bus data
- Prometheus metrics
- Loki logs
- All Docker images

**Use when**: Complete reset needed or disk space critical

```bash
# Confirm before running
task local:clean
```

---

## 🏥 Health & Validation

### `task health:local`

Check health of all local services (ports 8000-8008).

**Checks**:

- `/health` endpoint for all 9 services
- Gateway → Orchestrator → Feature-Dev → Code-Review → Infrastructure → CI/CD → Documentation → RAG → State

**Output**: ✅ Healthy / ❌ Unhealthy for each service

```bash
task health:local

# Example output:
# ✅ gateway-mcp (8000) - healthy
# ✅ orchestrator (8001) - healthy
# ❌ feature-dev (8002) - connection refused
```

### `task health:remote`

Check health of all droplet services at `45.55.173.72`.

**Use after**: Remote deployment to verify successful startup

```bash
task health:remote
```

---

## 🚀 Remote Deployment (Droplet)

### `task deploy:droplet`

Full deployment to DigitalOcean droplet (git pull + rebuild + health checks).

**What it does**:

1. SSH to droplet (`root@45.55.173.72`)
2. Pull latest code from `main` branch
3. Stop running services
4. Rebuild all images
5. Start services
6. Wait 20 seconds
7. Run health checks

**Time**: ~15-20 minutes  
**Downtime**: ~2-3 minutes

```bash
task deploy:droplet
```

### `task deploy:docr`

Fast deployment using pre-built DOCR images (no rebuild).

**Prerequisites**: Images pushed via `task build:push-docr`

**What it does**:

1. SSH to droplet
2. Pull images from DOCR
3. Restart services
4. Health check

**Time**: ~2-3 minutes  
**Downtime**: ~30 seconds

```bash
# First, push images
task build:push-docr

# Then deploy
task deploy:docr
```

### `task deploy:restart`

Quick restart of droplet services without rebuild.

**Use when**:

- Environment variables changed
- Configuration files updated
- Need to clear stuck state

**Time**: ~1 minute  
**Downtime**: ~10 seconds

```bash
task deploy:restart
```

---

## 🔧 Droplet Administration

### `task droplet:ssh`

Open interactive SSH session to production droplet.

```bash
task droplet:ssh

# Equivalent to:
# ssh root@45.55.173.72
```

### `task droplet:status`

Comprehensive droplet status report.

**Shows**:

- Running Docker services
- Disk usage (`/opt`)
- Current git branch and latest commit
- Service health summary

```bash
task droplet:status

# Example output:
# === Docker Services ===
# orchestrator   Up 5 hours
# gateway-mcp    Up 5 hours
#
# === Disk Usage ===
# /opt   45G/160G (28% used)
#
# === Git Branch ===
# main
# abc1234 Phase 7 production readiness
```

---

## 🛠️ Utilities

### `task utilities:env`

Validate `.env` file and show required variable status.

**Checks**:

- `GRADIENT_API_KEY`
- `LANGCHAIN_API_KEY`
- `LINEAR_API_KEY`
- All secrets files exist

**Output**: ✅ Configured / ❌ Missing for each variable

```bash
task utilities:env

# Run full validation
.\support\scripts\validation\validate-env.ps1
```

### `task utilities:ports`

Display service port mappings reference.

**Shows**: Port → Service → Purpose for all exposed services

```bash
task utilities:ports

# Output:
# 8000 → gateway-mcp (MCP tool routing)
# 8001 → orchestrator (task delegation)
# 8002 → feature-dev (code generation)
# ...
```

---

## 🔄 Workflow Management (HITL)

### `task workflow:init-db`

Initialize `approval_requests` table in PostgreSQL.

**Idempotent**: Safe to run multiple times  
**Prerequisites**: PostgreSQL service running

```bash
task workflow:init-db
```

### `task workflow:list-pending`

List all pending approval requests.

**Shows**:

- Request ID (UUID)
- Workflow ID
- Risk level (low/medium/high/critical)
- Created timestamp
- Timeout (seconds remaining)
- Description

```bash
task workflow:list-pending

# Example output:
# REQUEST_ID                            RISK     TIMEOUT   DESCRIPTION
# abc-123-def-456                       high     3600s     Deploy auth service
# xyz-789-ghi-012                       medium   7200s     Update database schema
```

### `task workflow:approve REQUEST_ID=<uuid>`

Approve a pending approval request.

**Parameters**:

- `REQUEST_ID`: UUID of the approval request

**Effect**: Workflow resumes execution immediately

```bash
task workflow:approve REQUEST_ID=abc-123-def-456
```

### `task workflow:reject REQUEST_ID=<uuid> REASON="..."`

Reject an approval request with reason.

**Parameters**:

- `REQUEST_ID`: UUID of the approval request
- `REASON`: Explanation for rejection (logged)

**Effect**: Workflow terminates, agent notified

```bash
task workflow:reject REQUEST_ID=abc-123-def-456 REASON="Security review required"
```

### `task workflow:status WORKFLOW_ID=<id>`

Display detailed workflow status.

**Shows**:

- All subtasks and their status
- Approval requests (pending/approved/rejected)
- Execution history with timestamps
- Current state

```bash
task workflow:status WORKFLOW_ID=deploy-auth-123
```

### `task workflow:clean-expired`

Mark expired approval requests as 'expired'.

**Runs as**: Maintenance task (can be scheduled via cron)  
**Effect**: Cleanup old requests, free up resources

```bash
task workflow:clean-expired
```

---

## 🔍 Common Workflows

### First-Time Setup

```bash
# 1. Validate environment
task utilities:env

# 2. Initialize workflow database
task workflow:init-db

# 3. Start local stack
task local:up

# 4. Check health
task health:local
```

### Local Development Cycle

```bash
# Start working
task local:up

# Make code changes...

# Rebuild specific service
cd deploy
docker compose build orchestrator
docker compose restart orchestrator

# Check logs
docker compose logs -f orchestrator

# When done
task local:down
```

### Production Deployment

```bash
# Option A: Full rebuild (safer, slower)
task deploy:droplet

# Option B: Pre-built images (faster)
task build:all
task build:push-docr
task deploy:docr

# Verify deployment
task health:remote
task droplet:status
```

### Troubleshooting Failed Service

```bash
# Check status
task droplet:status

# SSH to droplet
task droplet:ssh

# Once on droplet
cd /opt/Dev-Tools/deploy
docker compose logs <service-name>
docker compose restart <service-name>

# Check health from local machine
task health:remote
```

### Handling Approval Workflow

```bash
# Check pending approvals
task workflow:list-pending

# Approve a request
task workflow:approve REQUEST_ID=abc-123-def-456

# Check workflow status
task workflow:status WORKFLOW_ID=deploy-auth-123

# Reject a request
task workflow:reject REQUEST_ID=xyz-789 REASON="Requires additional testing"
```

---

## 📚 Related Documentation

- [Production Checklist](./operations/PRODUCTION_CHECKLIST.md)
- [Disaster Recovery Plan](./operations/DISASTER_RECOVERY.md)
- [Secrets Rotation Guide](./operations/SECRETS_ROTATION.md)
- [Prometheus Metrics](./operations/PROMETHEUS_METRICS.md)

---

## 🆘 Getting Help

```bash
# List all commands
task

# Get command summary
task --summary <command>

# View Taskfile source
cat Taskfile.yml
```

**Questions?** Contact: alex@appsmithery.co
