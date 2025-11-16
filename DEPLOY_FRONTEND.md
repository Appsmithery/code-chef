# Frontend Deployment - Agent Cards & Landing Page

**Date:** November 16, 2025  
**Changes:** Updated agent cards page and landing page with compact tiles

---

## 📦 What's New

- **`frontend/agents.html`**: New comprehensive agent cards page with metadata and endpoints
- **`frontend/production-landing.html`**: Updated with compact tile layout for agents/MCP/overview

---

## 🚀 Deploy to DigitalOcean Droplet

### Quick Deploy (From Droplet)

```bash
# SSH to droplet (use your configured SSH key)
ssh alex@45.55.173.72

# Navigate to deployment directory
cd /opt/Dev-Tools

# Pull latest changes
git pull origin main

# Restart gateway to serve updated frontend
docker-compose -f compose/docker-compose.yml restart gateway-mcp

# Verify deployment
curl -I http://localhost:80/agents.html
curl -I http://localhost:80/production-landing.html
```

### Verify Frontend Pages

```bash
# Check agent cards page
curl http://localhost/agents.html

# Check updated landing page
curl http://localhost/production-landing.html

# Check from browser
open http://45.55.173.72/agents.html
open http://45.55.173.72/production-landing.html
```

---

## 🧪 Test Agent Tracing

### 1. Verify All Agents Are Running

```bash
# Check health endpoints
curl http://localhost:8001/health  # Orchestrator
curl http://localhost:8002/health  # Feature-Dev
curl http://localhost:8003/health  # Code-Review
curl http://localhost:8004/health  # Infrastructure
curl http://localhost:8005/health  # CI/CD
curl http://localhost:8006/health  # Documentation
```

### 2. Trigger Sample Workflow

```bash
# Orchestrate a sample task (triggers Langfuse tracing)
curl -X POST http://localhost:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Build REST API with authentication",
    "priority": "high"
  }'
```

### 3. Check Langfuse Dashboard

Visit: https://us.cloud.langfuse.com

**What to Look For:**
- New traces appearing with `agent_name` metadata
- Task decomposition showing routing decisions
- Token usage per agent/model
- Execution timing and performance data

**Filter by Agent:**
```
metadata.agent_name = "orchestrator"
metadata.agent_name = "feature-dev"
metadata.agent_name = "code-review"
```

---

## 🔍 Troubleshooting

### Frontend Not Loading

```bash
# Check gateway logs
docker-compose -f compose/docker-compose.yml logs gateway-mcp

# Check if files exist
ls -la /opt/Dev-Tools/frontend/
```

### Agents Not Responding

```bash
# Check agent logs
docker-compose -f compose/docker-compose.yml logs orchestrator
docker-compose -f compose/docker-compose.yml logs feature-dev
docker-compose -f compose/docker-compose.yml logs code-review

# Restart all agents
docker-compose -f compose/docker-compose.yml restart orchestrator feature-dev code-review infrastructure cicd documentation
```

### Traces Not Appearing

```bash
# Check Langfuse environment variables
docker-compose -f compose/docker-compose.yml exec orchestrator env | grep LANGFUSE

# Expected output:
# LANGFUSE_SECRET_KEY=sk-lf-...
# LANGFUSE_PUBLIC_KEY=pk-lf-...
# LANGFUSE_HOST=https://us.cloud.langfuse.com
```

---

## 📊 Expected Results

Once deployed:

1. **Frontend Pages Accessible:**
   - http://45.55.173.72/agents.html - Agent cards with metadata
   - http://45.55.173.72/production-landing.html - Updated landing page
   - http://45.55.173.72/servers.html - MCP servers page

2. **All Agents Online:**
   - Orchestrator (8001): ✓ Online
   - Feature-Dev (8002): ✓ Online
   - Code-Review (8003): ✓ Online
   - Infrastructure (8004): ✓ Online
   - CI/CD (8005): ✓ Online
   - Documentation (8006): ✓ Online

3. **Langfuse Traces:**
   - Task orchestration traces with metadata
   - Agent-specific traces with task_id grouping
   - Token usage and cost tracking per model
   - Execution timing and performance metrics

---

## 🎯 Next Steps

1. **Access Frontend**: Visit http://45.55.173.72/production-landing.html
2. **Test Agents**: Navigate to agent cards page, try sample API calls
3. **Monitor Traces**: Check Langfuse dashboard for incoming traces
4. **Review Metrics**: Check Prometheus at http://45.55.173.72:9090

---

## 📝 Manual Deployment Commands

If automated deployment doesn't work, run these commands manually on the droplet:

```bash
# 1. SSH to droplet
ssh alex@45.55.173.72

# 2. Navigate to project
cd /opt/Dev-Tools

# 3. Pull changes
git pull origin main

# 4. Restart gateway (serves frontend)
docker-compose -f compose/docker-compose.yml restart gateway-mcp

# 5. Verify agents running
docker-compose -f compose/docker-compose.yml ps

# 6. Check agent health
for port in 8001 8002 8003 8004 8005 8006; do
  echo "Checking port $port..."
  curl -s http://localhost:$port/health | jq .
done

# 7. Test orchestration
curl -X POST http://localhost:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create user authentication API",
    "priority": "medium"
  }' | jq .

# 8. Check Langfuse
echo "Visit: https://us.cloud.langfuse.com"
echo "Look for traces with metadata: agent_name, task_id, thread_id, model"
```

---

**Status:** Ready for deployment  
**SSH Access Required:** Yes (key-based authentication)  
**Estimated Deployment Time:** 2-5 minutes
