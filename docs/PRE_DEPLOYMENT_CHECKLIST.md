# Pre-Deployment Checklist

**Version:** 1.0.0  
**Last Updated:** November 13, 2025  
**Target Environment:** DigitalOcean Droplet (45.55.173.72)

---

## 🎯 Overview

This checklist ensures all components are properly configured before deploying the Dev-Tools agent stack to production.

---

## ✅ Environment Configuration

### 1. Environment Variables (.env)

All required environment variables must be set in `config/env/.env`:

- [ ] **Runtime Environment**

  - [ ] `NODE_ENV=production`
  - [ ] `PORT=8000`
  - [ ] `SERVICE_NAME=gateway-mcp`

- [ ] **Agent Service URLs** (default values OK for Docker Compose)

  - [ ] `ORCHESTRATOR_URL=http://orchestrator:8001`
  - [ ] `FEATURE_DEV_URL=http://feature-dev:8002`
  - [ ] `CODE_REVIEW_URL=http://code-review:8003`
  - [ ] `INFRASTRUCTURE_URL=http://infrastructure:8004`
  - [ ] `CICD_URL=http://cicd:8005`
  - [ ] `DOCUMENTATION_URL=http://documentation:8006`
  - [ ] `MCP_GATEWAY_URL=http://gateway-mcp:8000`

- [ ] **Langfuse Observability** (REQUIRED)

  - [ ] `LANGFUSE_SECRET_KEY=sk-lf-...` (from https://us.cloud.langfuse.com)
  - [ ] `LANGFUSE_PUBLIC_KEY=pk-lf-...` (from https://us.cloud.langfuse.com)
  - [ ] `LANGFUSE_BASE_URL=https://us.cloud.langfuse.com`

- [ ] **DigitalOcean Gradient AI** (REQUIRED for LLM inference)

  - [ ] `GRADIENT_API_KEY=do-api-...` (from https://cloud.digitalocean.com/ai)
  - [ ] `GRADIENT_BASE_URL=https://api.digitalocean.com/v2/ai`
  - [ ] `GRADIENT_MODEL=llama-3.1-8b-instruct` (default, per-agent overrides in docker-compose.yml)
  - [ ] `GRADIENT_EMBEDDING_MODEL=all-MiniLM-L6-v2`

- [ ] **Qdrant Cloud + KB Sync**

  - [ ] `QDRANT_URL=https://<cluster>.cloud.qdrant.io`
  - [ ] `QDRANT_API_KEY=...` (cluster API key)
  - [ ] `QDRANT_COLLECTION=the-shop`
  - [ ] `QDRANT_VECTOR_SIZE=1536`
  - [ ] `QDRANT_DISTANCE=cosine`
  - [ ] `DIGITALOCEAN_KB_UUID=...` (from `config/env/workspaces/*.json`)
  - [ ] `DIGITALOCEAN_KB_MANIFEST=config/env/workspaces/the-shop.json`
  - [ ] `DIGITALOCEAN_KB_DOWNLOAD_DIR=./tmp/kb-sync`

- [ ] **Linear Integration** (Optional)

  - [ ] `LINEAR_OAUTH_CLIENT_ID=...` (if using Linear OAuth)
  - [ ] `LINEAR_OAUTH_CLIENT_SECRET=...` (if using Linear OAuth)
  - [ ] `LINEAR_OAUTH_DEV_TOKEN=...` (if using dev token auth)
  - [ ] `LINEAR_OAUTH_REDIRECT_URI=http://localhost:8000/oauth/linear/callback`
  - [ ] `LINEAR_OAUTH_SCOPES=read,write,app:mentionable,app:assignable`
  - [ ] `LINEAR_TOKEN_STORE_DIR=./config`

- [ ] **DigitalOcean** (Optional)

  - [ ] `DIGITAL_OCEAN_PAT=...` (if using DO API)
  - [ ] `DIGITAL_OCEAN_OAUTH_CLIENT_ID=...` (if using DO OAuth)
  - [ ] `DIGITAL_OCEAN_OAUTH_CLIENT_SECRET=...` (if using DO OAuth)

- [ ] **Database**

  - [ ] `DB_HOST=postgres`
  - [ ] `DB_PORT=5432`
  - [ ] `DB_NAME=devtools`
  - [ ] `DB_USER=devtools`
  - [ ] `DB_PASSWORD=changeme` (⚠️ CHANGE IN PRODUCTION!)

- [ ] **Logging**
  - [ ] `LOG_LEVEL=info` (or `debug` for troubleshooting)

### 2. Secrets Files

Secrets are mounted via Docker Compose from `config/env/secrets/`:

- [ ] **Linear OAuth Token** (if using Linear)

  - [ ] `config/env/secrets/linear_oauth_token.txt` exists
  - [ ] Contains valid Linear OAuth token (no whitespace/newlines)

- [ ] **Linear Webhook Secret** (if using Linear)
  - [ ] `config/env/secrets/linear_webhook_secret.txt` exists
  - [ ] Contains valid webhook signing secret

**Setup Command:**

```bash
./scripts/setup_secrets.sh
```

---

## ✅ Code Validation

### 3. Agent Initialization

All agents should have proper initialization:

- [ ] **Orchestrator** (`agents/orchestrator/main.py`)

  - [ ] `mcp_client = MCPClient(agent_name="orchestrator")`
  - [ ] `gradient_client = get_gradient_client("orchestrator")`
  - [ ] Prometheus instrumentation enabled

- [ ] **Feature-Dev** (`agents/feature-dev/main.py`)

  - [ ] `mcp_client = MCPClient(agent_name="feature-dev")`
  - [ ] `gradient_client = get_gradient_client("feature-dev")`
  - [ ] Prometheus instrumentation enabled

- [ ] **Code-Review** (`agents/code-review/main.py`)

  - [ ] `mcp_client = MCPClient(agent_name="code-review")`
  - [ ] `gradient_client = get_gradient_client("code-review")`
  - [ ] Prometheus instrumentation enabled

- [ ] **Infrastructure** (`agents/infrastructure/main.py`)

  - [ ] `mcp_client = MCPClient(agent_name="infrastructure")`
  - [ ] `gradient_client = get_gradient_client("infrastructure")`
  - [ ] Prometheus instrumentation enabled

- [ ] **CI/CD** (`agents/cicd/main.py`)

  - [ ] `mcp_client = MCPClient(agent_name="cicd")`
  - [ ] `gradient_client = get_gradient_client("cicd")`
  - [ ] Prometheus instrumentation enabled

- [ ] **Documentation** (`agents/documentation/main.py`)
  - [ ] `mcp_client = MCPClient(agent_name="documentation")`
  - [ ] `gradient_client = get_gradient_client("documentation")`
  - [ ] Prometheus instrumentation enabled

### 4. Shared Libraries

- [ ] **MCP Client** (`agents/_shared/mcp_client.py`)

  - [ ] Reads `MCP_GATEWAY_URL` from environment
  - [ ] Tool discovery on initialization
  - [ ] Proper error handling

- [ ] **Gradient Client** (`agents/_shared/gradient_client.py`)

  - [ ] Reads `GRADIENT_API_KEY`, `GRADIENT_BASE_URL`, `GRADIENT_MODEL` from environment
  - [ ] Uses `langfuse.openai` wrapper for automatic tracing
  - [ ] Graceful fallback when API key not set (`is_enabled()` check)

- [ ] **Gradient Warmup** (`agents/_shared/gradient_warmup.py`)
  - [ ] Optional background task to prevent cold starts
  - [ ] Pings models every 5 minutes

---

## ✅ Docker Configuration

### 5. Docker Compose

Verify `compose/docker-compose.yml` configuration:

- [ ] **Networks**

  - [ ] `devtools-network` defined and used by all services

- [ ] **Volumes**

  - [ ] `orchestrator-data` for task state
  - [ ] `mcp-config` for MCP gateway config
  - [ ] `qdrant-data` for vector database
  - [ ] `postgres-data` for state persistence
  - [ ] `prometheus-data` for metrics storage

- [ ] **Secrets**

  - [ ] `linear_oauth_token` mapped to `config/env/secrets/linear_oauth_token.txt`
  - [ ] `linear_webhook_secret` mapped to `config/env/secrets/linear_webhook_secret.txt`

- [ ] **Environment Variables per Agent**

  - [ ] Orchestrator: `GRADIENT_MODEL=llama-3.1-70b-instruct` (complex reasoning)
  - [ ] Feature-Dev: `GRADIENT_MODEL=codellama-13b-instruct` (code generation)
  - [ ] Code-Review: `GRADIENT_MODEL=llama-3.1-70b-instruct` (deep analysis)
  - [ ] Infrastructure: `GRADIENT_MODEL=llama-3.1-8b-instruct` (fast IaC)
  - [ ] CI/CD: `GRADIENT_MODEL=llama-3.1-8b-instruct` (pipeline configs)
  - [ ] Documentation: `GRADIENT_MODEL=mistral-7b-instruct` (fast docs)

- [ ] **Port Mappings**
  - [ ] Gateway (MCP): 8000
  - [ ] Orchestrator: 8001
  - [ ] Feature-Dev: 8002
  - [ ] Code-Review: 8003
  - [ ] Infrastructure: 8004
  - [ ] CI/CD: 8005
  - [ ] Documentation: 8006
  - [ ] RAG: 8007
  - [ ] State: 8008
  - [ ] Prometheus: 9090
  - [ ] Qdrant: 6333 (HTTP), 6334 (gRPC)
  - [ ] PostgreSQL: 5432

### 6. Dockerfiles

Verify all Dockerfiles exist and are correct:

- [ ] `containers/orchestrator/Dockerfile`
- [ ] `containers/feature-dev/Dockerfile`
- [ ] `containers/code-review/Dockerfile`
- [ ] `containers/infrastructure/Dockerfile`
- [ ] `containers/cicd/Dockerfile`
- [ ] `containers/documentation/Dockerfile`
- [ ] `containers/gateway-mcp/Dockerfile`
- [ ] `containers/rag/Dockerfile`
- [ ] `containers/state/Dockerfile`

---

## ✅ Dependencies

### 7. Python Requirements

All agents must have correct dependencies in `requirements.txt`:

- [ ] **Orchestrator** (`agents/orchestrator/requirements.txt`)

  - [ ] `fastapi>=0.104.0`
  - [ ] `uvicorn>=0.24.0`
  - [ ] `pydantic>=2.5.0`
  - [ ] `httpx>=0.25.0`
  - [ ] `langfuse>=2.0.0`
  - [ ] `prometheus-fastapi-instrumentator>=6.1.0`

- [ ] **Feature-Dev** (`agents/feature-dev/requirements.txt`)

  - [ ] Same as orchestrator

- [ ] **All Other Agents**
  - [ ] Same dependencies verified

### 8. Node.js Dependencies

Gateway MCP requires Node.js packages:

- [ ] `mcp/gateway/package.json` has all dependencies
- [ ] Run `npm install` in `mcp/gateway/` before building

---

## ✅ Infrastructure Services

### 9. PostgreSQL

- [ ] Database name: `devtools`
- [ ] User: `admin` (or from `DB_USER` env var)
- [ ] Password: Set to secure value (not `changeme` in production!)
- [ ] Health check enabled
- [ ] Volume mounted for persistence

### 10. Qdrant

- [ ] HTTP API on port 6333 _(local dev container)_ or `QDRANT_URL` _(cloud)_
- [ ] gRPC API on port 6334 _(local dev container)_
- [ ] Volume mounted for persistence _(local dev only)_
- [ ] `QDRANT_URL`/`QDRANT_API_KEY` configured for managed cluster _(production)_
- [ ] Docker DNS or cloud hostname referenced by `rag-context`

### 11. Prometheus

- [ ] Config file: `config/prometheus/prometheus.yml`
- [ ] Scrape targets configured for all 8+ services
- [ ] Scrape interval: 15 seconds
- [ ] Volume mounted for data persistence
- [ ] Web UI accessible on port 9090

---

## ✅ Observability

### 12. Langfuse Setup

- [ ] Account created at https://us.cloud.langfuse.com
- [ ] Project created
- [ ] API keys copied to `.env`
- [ ] All agents have `langfuse>=2.0.0` in requirements.txt
- [ ] Gradient client uses `langfuse.openai` wrapper

### 13. Prometheus Setup

- [ ] Scrape config includes all agent `/metrics` endpoints
- [ ] All agents have `prometheus-fastapi-instrumentator` installed
- [ ] Instrumentator initialized in each agent's `main.py`
- [ ] Test queries work (see `docs/PROMETHEUS_METRICS.md`)

---

## ✅ MCP Integration

### 14. MCP Gateway

- [ ] Gateway accessible at `http://gateway-mcp:8000`
- [ ] 150+ tools discovered from 17 servers
- [ ] Tool mapping config: `config/mcp-agent-tool-mapping.yaml`
- [ ] Agent manifest: `agents/agents-manifest.json`
- [ ] Health check: `GET /health` returns `{"status": "healthy"}`

### 15. MCP Servers

All MCP servers configured in `mcp/servers/`:

- [ ] `filesystem` - File operations
- [ ] `memory` - Persistent state (KV store)
- [ ] `time` - Temporal operations
- [ ] `gitmcp` - Git operations
- [ ] `sequential-thinking` - Multi-step reasoning
- [ ] And 12 more servers...

---

## ✅ Testing

### 16. Pre-Deployment Tests

Run these tests before deploying:

- [ ] **Health Checks**

  ```bash
  # Gateway
  curl http://localhost:8000/health | jq .

  # Orchestrator
  curl http://localhost:8001/health | jq .

  # All other agents (8002-8006)
  ```

- [ ] **MCP Tool Discovery**

  ```bash
  curl http://localhost:8000/tools | jq '. | length'
  # Should return 150+
  ```

- [ ] **Gradient Client Test**

  ```bash
  # In Python shell
  from agents._shared.gradient_client import get_gradient_client
  client = get_gradient_client("test")
  print(client.is_enabled())  # Should return True if API key set
  ```

- [ ] **E2E Workflow Test**

  ```bash
  curl -X POST http://localhost:8001/orchestrate \
    -H "Content-Type: application/json" \
    -d '{"description": "Build REST API for user management", "priority": "high"}' | jq .
  ```

- [ ] **Langfuse Traces**

  - [ ] Visit https://us.cloud.langfuse.com
  - [ ] Verify traces appear from test workflow
  - [ ] Check token counts and costs

- [ ] **Prometheus Metrics**
  ```bash
  curl http://localhost:9090/api/v1/query?query=up | jq .
  # Should show all services with value=1
  ```

---

## ✅ Documentation

### 17. Documentation Review

- [ ] `README.md` in root is current
- [ ] `docs/README.md` index is updated
- [ ] All integration guides are accurate:
  - [ ] `docs/MCP_INTEGRATION.md`
  - [ ] `docs/GRADIENT_QUICK_START.md`
  - [ ] `docs/LANGFUSE_TRACING.md`
  - [ ] `docs/PROMETHEUS_METRICS.md`
- [ ] Obsolete docs moved to `docs/archive/`
- [ ] API endpoints documented in `docs/AGENT_ENDPOINTS.md`

---

## ✅ Deployment

### 18. Deployment Steps

Once all checks pass:

1. **SSH to Droplet**

   ```bash
   ssh root@45.55.173.72
   ```

2. **Update Code**

   ```bash
   cd /opt/Dev-Tools
   git pull origin main
   ```

3. **Set Environment Variables**

   ```bash
   export GRADIENT_API_KEY='do-api-XXX'
   echo "GRADIENT_API_KEY=$GRADIENT_API_KEY" >> config/env/.env
   ```

4. **Setup Secrets** (if needed)

   ```bash
   ./scripts/setup_secrets.sh
   ```

5. **Build Containers**

   ```bash
   docker-compose -f compose/docker-compose.yml build
   ```

6. **Deploy Stack**

   ```bash
   docker-compose -f compose/docker-compose.yml up -d
   ```

7. **Verify Health**

   ```bash
   docker-compose -f compose/docker-compose.yml ps
   curl http://localhost:8001/health | jq .
   ```

8. **Monitor Logs**
   ```bash
   docker-compose -f compose/docker-compose.yml logs -f
   ```

---

## ✅ Post-Deployment

### 19. Validation

- [ ] All services show `Up` status in `docker-compose ps`
- [ ] All health endpoints return `{"status": "healthy"}`
- [ ] Langfuse dashboard shows live traces
- [ ] Prometheus dashboard shows metrics from all services
- [ ] Test E2E workflow completes successfully
- [ ] No errors in `docker-compose logs`

### 20. Monitoring Setup

- [ ] Langfuse alerts configured (optional)
- [ ] Prometheus alerts configured (optional)
- [ ] Log aggregation setup (optional)
- [ ] Uptime monitoring (optional)

---

## 🚨 Troubleshooting

### Common Issues

**1. "GRADIENT_API_KEY not set" warnings**

- Verify `.env` file has the key
- Verify docker-compose.yml mounts the `.env` file
- Restart containers after adding key

**2. MCP Gateway not connecting**

- Check `docker-compose logs gateway-mcp`
- Verify network connectivity: `docker network inspect devtools-network`
- Ensure secrets files exist

**3. Langfuse traces not appearing**

- Verify API keys are correct
- Check `LANGFUSE_BASE_URL` matches your region
- Ensure `langfuse>=2.0.0` is installed in all agents

**4. Prometheus not scraping**

- Verify `config/prometheus/prometheus.yml` has all targets
- Check service names match docker-compose service names
- Verify agents expose `/metrics` endpoint

**5. Database connection errors**

- Wait for PostgreSQL health check to pass
- Verify `DB_*` environment variables
- Check `docker-compose logs postgres`

---

## 📋 Summary

Before deploying, ensure:

✅ All environment variables configured  
✅ All secrets files created  
✅ All agents have MCP + Gradient + Prometheus initialization  
✅ Docker Compose configuration validated  
✅ Dependencies installed  
✅ Infrastructure services configured  
✅ Observability platforms setup  
✅ MCP integration validated  
✅ Pre-deployment tests pass  
✅ Documentation current

**Ready to deploy!** 🚀

See `docs/GRADIENT_QUICK_START.md` for detailed deployment instructions.
