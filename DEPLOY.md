# Quick Deployment Guide

**Target:** DigitalOcean Droplet at `45.55.173.72`  
**Estimated Time:** 20-30 minutes  
**Prerequisites:** Git, Docker, Docker Compose

---

## 📋 Before You Deploy

**Required API Keys:**

1. **Gradient AI** (LLM inference): https://cloud.digitalocean.com/ai
2. **Langfuse** (observability): https://us.cloud.langfuse.com

**Optional Keys:**

- Linear OAuth (for Linear integration)
- DigitalOcean PAT (for DO API access)

---

## 🚀 Deployment Steps

### 1. SSH to Droplet

```bash
ssh root@45.55.173.72
```

### 2. Clone or Update Repository

```bash
# If first deployment
cd /opt
git clone https://github.com/Appsmithery/Dev-Tools.git
cd Dev-Tools

# If updating
cd /opt/Dev-Tools
git pull origin main
```

### 3. Configure Environment

```bash
# Copy template
cp config/env/.env.example config/env/.env

# Edit with your keys
nano config/env/.env
```

**Required Environment Variables:**

```bash
# Langfuse (get from https://us.cloud.langfuse.com)
LANGFUSE_SECRET_KEY=sk-lf-XXXXX
LANGFUSE_PUBLIC_KEY=pk-lf-XXXXX
LANGFUSE_BASE_URL=https://us.cloud.langfuse.com

# Gradient AI (get from https://cloud.digitalocean.com/ai)
GRADIENT_API_KEY=do-api-XXXXX
GRADIENT_BASE_URL=https://api.digitalocean.com/v2/ai
GRADIENT_MODEL=llama-3.1-8b-instruct

# Database (CHANGE PASSWORD!)
DB_PASSWORD=YOUR_SECURE_PASSWORD_HERE

# Runtime
NODE_ENV=production
LOG_LEVEL=info
```

### 4. Setup Secrets (if using Linear)

```bash
# Create Linear OAuth token file
mkdir -p config/env/secrets
echo "your-linear-token" > config/env/secrets/linear_oauth_token.txt
echo "your-webhook-secret" > config/env/secrets/linear_webhook_secret.txt
chmod 600 config/env/secrets/*
```

### 5. Build Containers

```bash
cd compose
docker-compose build
```

This will build all 9 services (may take 5-10 minutes first time):

- gateway-mcp
- orchestrator
- feature-dev
- code-review
- infrastructure
- cicd
- documentation
- rag-context
- state-persistence

### 6. Deploy Stack

```bash
docker-compose up -d
```

### 7. Verify Deployment

```bash
# Check all services are running
docker-compose ps

# Should see 13 services with status "Up":
# - 6 agents (8001-8006)
# - MCP gateway (8000)
# - RAG service (8007)
# - State service (8008)
# - Prometheus (9090)
# - Qdrant (6333, 6334)
# - PostgreSQL (5432)

# Test health endpoints
curl http://localhost:8001/health | jq .
# Should return: {"status": "healthy", "mcp_gateway": "connected", ...}

# Check Gradient client initialization
docker-compose logs orchestrator | grep GRADIENT
# Should see: [GRADIENT] orchestrator: Initialized with model llama-3.1-70b-instruct
```

### 8. Monitor Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f orchestrator

# Last 50 lines
docker-compose logs --tail=50
```

---

## ✅ Validation Checklist

After deployment, verify:

- [ ] All services show "Up" in `docker-compose ps`
- [ ] Health endpoints return `{"status": "healthy"}`
- [ ] MCP gateway shows "connected" status in agent health checks
- [ ] Gradient client initialized (check logs for "[GRADIENT]" messages)
- [ ] No errors in logs (ignore warnings about default env vars)

**Test E2E Workflow:**

```bash
curl -X POST http://localhost:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a REST API for user management with JWT authentication",
    "priority": "high",
    "project_context": {
      "framework": "FastAPI",
      "language": "Python"
    }
  }' | jq .
```

Should return task ID and status. Check response includes LLM-generated subtasks.

**Check Langfuse Traces:**

1. Visit https://us.cloud.langfuse.com
2. Select your project
3. Look for traces from "orchestrator" or "feature-dev"
4. Verify token counts and model info appear

**Check Prometheus Metrics:**

1. Visit http://45.55.173.72:9090
2. Query: `up{job=~".*agent.*"}`
3. Should see all agents with value=1

---

## 🔧 Troubleshooting

### Service Won't Start

```bash
# View logs
docker-compose logs <service-name>

# Common issues:
# - Missing env vars → Check .env file
# - Port conflicts → Check other processes
# - Volume permissions → Check /var/lib/docker/volumes/
```

### MCP Gateway Not Connecting

```bash
# Check gateway logs
docker-compose logs gateway-mcp

# Verify network
docker network inspect devtools-network

# Ensure secrets exist
ls -la config/env/secrets/
```

### Gradient API Errors

```bash
# Verify API key
echo $GRADIENT_API_KEY

# Test API directly
curl -H "Authorization: Bearer $GRADIENT_API_KEY" \
  https://api.digitalocean.com/v2/ai/models

# Should list available models
```

### Database Connection Errors

```bash
# Check PostgreSQL health
docker-compose exec postgres pg_isready -U admin -d devtools

# Verify credentials in .env match docker-compose.yml
grep DB_ config/env/.env
```

### No Langfuse Traces

```bash
# Verify keys in .env
grep LANGFUSE_ config/env/.env

# Check agent logs for Langfuse errors
docker-compose logs orchestrator | grep -i langfuse

# Test API connection
curl -X POST https://us.cloud.langfuse.com/api/public/ingestion \
  -H "Authorization: Bearer $LANGFUSE_PUBLIC_KEY:$LANGFUSE_SECRET_KEY" \
  -H "Content-Type: application/json" \
  -d '{"batch": []}'
```

---

## 🔄 Updates

To deploy code updates:

```bash
# SSH to droplet
ssh root@45.55.173.72
cd /opt/Dev-Tools

# Pull latest
git pull origin main

# Rebuild containers (if code changed)
cd compose
docker-compose build

# Restart services
docker-compose restart

# Or full redeploy
docker-compose down
docker-compose up -d
```

---

## 📊 Monitoring

### Service Endpoints

- **MCP Gateway**: http://45.55.173.72:8000
- **Orchestrator**: http://45.55.173.72:8001
- **Feature-Dev**: http://45.55.173.72:8002
- **Code-Review**: http://45.55.173.72:8003
- **Infrastructure**: http://45.55.173.72:8004
- **CI/CD**: http://45.55.173.72:8005
- **Documentation**: http://45.55.173.72:8006
- **RAG**: http://45.55.173.72:8007
- **State**: http://45.55.173.72:8008
- **Prometheus**: http://45.55.173.72:9090

### Health Checks

```bash
# Quick health check script
for port in 8000 8001 8002 8003 8004 8005 8006 8007 8008; do
  echo -n "Port $port: "
  curl -s http://localhost:$port/health | jq -r .status 2>/dev/null || echo "DOWN"
done
```

### Log Monitoring

```bash
# Real-time logs
docker-compose logs -f --tail=100

# Filter by service
docker-compose logs -f orchestrator feature-dev

# Search logs
docker-compose logs | grep ERROR
docker-compose logs | grep -i "gradient"
docker-compose logs | grep -i "langfuse"
```

---

## 📚 Documentation

For detailed information:

- **Pre-Deployment Checklist**: `docs/PRE_DEPLOYMENT_CHECKLIST.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Gradient Setup**: `docs/GRADIENT_QUICK_START.md`
- **Langfuse Tracing**: `docs/LANGFUSE_TRACING.md`
- **Prometheus Metrics**: `docs/PROMETHEUS_METRICS.md`
- **MCP Integration**: `docs/MCP_INTEGRATION.md`
- **API Reference**: `docs/AGENT_ENDPOINTS.md`

---

## 🎯 Success Criteria

Deployment is successful when:

✅ All 13 services running (docker-compose ps)  
✅ All health endpoints return "healthy"  
✅ E2E workflow test completes successfully  
✅ Langfuse dashboard shows live traces  
✅ Prometheus dashboard shows metrics from all agents  
✅ No errors in logs (warnings OK)

**You're ready for production!** 🚀

---

## 💡 Quick Tips

1. **Logs are your friend** - Most issues are visible in logs
2. **Environment variables** - Double-check spelling and values
3. **Network issues** - Ensure Docker network is healthy
4. **Secrets** - Keep them secure, never commit to git
5. **Backups** - Run `./scripts/backup_volumes.sh` regularly
6. **Monitoring** - Check Langfuse and Prometheus daily

---

## 🆘 Need Help?

- Review: `docs/PRE_DEPLOYMENT_CHECKLIST.md` (comprehensive troubleshooting)
- Check: Service-specific README files in `agents/*/README.md`
- Search: GitHub issues for similar problems
- Contact: Open an issue with logs attached

**Happy Deploying!** 🎉
