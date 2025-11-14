# Quick Deploy Commands

## ⚡ Fastest Path to Deployment

### Option 1: Automated Deployment Script (Recommended)

```powershell
# Local deployment with health checks
./scripts/deploy.ps1

# Remote deployment to droplet
./scripts/deploy.ps1 -Target remote

# Quick redeploy (skip build if code unchanged)
./scripts/deploy.ps1 -SkipBuild
```

### Option 2: Manual Docker Compose

```powershell
# Navigate to compose directory
cd compose

# Build all containers (5-10 minutes first time)
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

---

## 🔍 Health Checks

```powershell
# Test all agents
$ports = 8000,8001,8002,8003,8004,8005,8006,8007,8008
foreach ($port in $ports) {
  curl "http://localhost:$port/health" | jq .
}

# Quick status
docker-compose ps

# View logs
docker-compose logs --tail=50 orchestrator
```

---

## 🚀 Remote Deployment (to 45.55.173.72)

```powershell
# Using deploy script (easiest)
./scripts/deploy.ps1 -Target remote

# Or manual SSH
ssh root@45.55.173.72
cd /opt/Dev-Tools
git pull origin main
cd compose
docker-compose build
docker-compose up -d
docker-compose ps
```

---

## 📊 Access Dashboards

- **Langfuse Traces**: https://us.cloud.langfuse.com
- **Prometheus Metrics**: http://localhost:9090 (or http://45.55.173.72:9090)
- **MCP Gateway**: http://localhost:8000/health
- **Orchestrator**: http://localhost:8001/health

---

## 🔧 Troubleshooting

```powershell
# View logs
docker-compose logs <service-name>

# Restart a service
docker-compose restart <service-name>

# Rebuild a specific service
docker-compose build <service-name>
docker-compose up -d <service-name>

# Full reset
docker-compose down
docker-compose build
docker-compose up -d
```

---

## ✅ Verification Commands

```powershell
# All services running?
docker-compose ps | Select-String "Up"

# MCP Gateway connected?
curl http://localhost:8001/health | jq .mcp_gateway

# Langfuse traces?
# Visit https://us.cloud.langfuse.com and check for recent traces

# Prometheus metrics?
curl http://localhost:9090/api/v1/query?query=up | jq .
```

---

## 📋 Configuration Files

- **Environment**: `config/env/.env` (all credentials configured ✓)
- **Secrets**: `config/env/secrets/*` (Linear tokens ✓)
- **Compose**: `compose/docker-compose.yml` (all services defined ✓)

---

## 💡 Quick Tips

1. **First deployment**: Allow 10-15 minutes for container builds
2. **Subsequent deployments**: Use `-SkipBuild` if only config changed
3. **Check logs**: Most issues are visible in `docker-compose logs`
4. **Health checks**: Wait 15-20 seconds after `docker-compose up` for services to initialize
5. **Langfuse traces**: May take 30-60 seconds to appear in dashboard

---

## 🎯 Success Criteria

✅ All services show "Up" in `docker-compose ps`  
✅ All `/health` endpoints return `{"status": "healthy"}`  
✅ MCP gateway shows "connected" status  
✅ Langfuse dashboard shows traces  
✅ Prometheus shows all agents with `up=1`

**Ready to deploy!** 🚀
