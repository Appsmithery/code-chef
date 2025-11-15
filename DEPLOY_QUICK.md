# Hybrid Architecture Deployment Guide

## Emergency: If Everything is Hanging

Run these from **local PowerShell** (doesn't require SSH to work):

### 1. Reboot Droplet via DigitalOcean API

```powershell
$env:DIGITALOCEAN_TOKEN = "dop_v1_386655ab63501ca37c093c03e768c4c67fcc49bac5facd3505b316e91f924857"

# Get droplet ID
$droplets = Invoke-RestMethod -Uri "https://api.digitalocean.com/v2/droplets" -Headers @{Authorization="Bearer $env:DIGITALOCEAN_TOKEN"}
$droplet = $droplets.droplets | Where-Object { $_.networks.v4.ip_address -contains "45.55.173.72" }

# Power cycle (soft reboot)
Invoke-RestMethod -Uri "https://api.digitalocean.com/v2/droplets/$($droplet.id)/actions" `
  -Method Post `
  -Headers @{Authorization="Bearer $env:DIGITALOCEAN_TOKEN"; "Content-Type"="application/json"} `
  -Body '{"type":"reboot"}'

Write-Host "Droplet rebooting... wait 2-3 minutes then test: curl http://45.55.173.72:8000/health"
```

### 2. Check Droplet Status

```powershell
$env:DIGITALOCEAN_TOKEN = "dop_v1_386655ab63501ca37c093c03e768c4c67fcc49bac5facd3505b316e91f924857"
$droplets = Invoke-RestMethod -Uri "https://api.digitalocean.com/v2/droplets" -Headers @{Authorization="Bearer $env:DIGITALOCEAN_TOKEN"}
$droplet = $droplets.droplets | Where-Object { $_.networks.v4.ip_address -contains "45.55.173.72" }
Write-Host "Status: $($droplet.status)" -ForegroundColor Cyan
Write-Host "Memory: $($droplet.memory)MB" -ForegroundColor Gray
Write-Host "Disk: $($droplet.disk)GB" -ForegroundColor Gray
```

### 3. Use DigitalOcean Web Console (Most Reliable)

1. Go to: https://cloud.digitalocean.com/droplets
2. Click on droplet with IP `45.55.173.72`
3. Click "Access" tab → "Launch Droplet Console"
4. Login with root credentials
5. Run deployment commands directly in browser terminal

---

## Quick Deploy via VS Code Remote SSH

Since SSH commands from PowerShell are freezing, use VS Code's built-in Remote SSH feature:

### Step 1: Connect to Droplet

1. Press `F1` in VS Code
2. Type: `Remote-SSH: Connect to Host`
3. Enter: `root@45.55.173.72`
4. Wait for connection to establish

### Step 2: Open Terminal on Droplet

Once connected, open a new terminal (Ctrl+` or Terminal → New Terminal)

### Step 3: Deploy Infrastructure Services

```bash
cd /opt/Dev-Tools

# Pull latest code
git pull origin main

# Copy .env file if needed (first time only)
# scp from local machine or edit directly

# Start only infrastructure services (not agents)
docker compose -f compose/docker-compose.yml up -d \
  gateway-mcp \
  rag-context \
  state-persistence \
  qdrant \
  postgres \
  prometheus

# Wait for services to start
sleep 15

# Verify gateway health
curl http://localhost:8000/health | jq

# Check all containers
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### Step 4: Verify from Local Machine

```powershell
# Test gateway from your local machine
Invoke-RestMethod http://45.55.173.72:8000/health

# Test Gradient AI agents
Invoke-RestMethod https://zqavbvjov22wijsmbqtkqy4r.agents.do-ai.run/health
```

## Architecture Overview

**Gradient AI Agents (Managed - Already Running):**

- DevTools Orchestrator: `https://zqavbvjov22wijsmbqtkqy4r.agents.do-ai.run`
- Feature Development: `https://mdu2tzvveslhs6spm36znwul.agents.do-ai.run`
- Code Review: `https://miml4tgrdvjufzudn5udh2sp.agents.do-ai.run`
- Infrastructure: `https://r2eqzfrjao62mdzdbtolmq3sa.agents.do-ai.run`
- CI/CD: `https://dxoc7qrjjgbvj7ybct7nogbp.agents.do-ai.run`
- Documentation: `https://tzyvehgqf3pgl4z46rrzbbs.agents.do-ai.run`

**Docker Infrastructure (Droplet 45.55.173.72):**

- Gateway MCP: Port 8000
- RAG Context: Port 8007
- State Persistence: Port 8008
- Qdrant: Port 6333
- PostgreSQL: Port 5432
- Prometheus: Port 9090

## Troubleshooting

### VS Code Remote SSH Connection Hanging

If VS Code Remote SSH is hanging on "Initializing VS Code Server":

**Option 1: Restart SSH Service on Droplet (from local PowerShell)**

```powershell
# Force close SSH connection
ssh root@45.55.173.72 "systemctl restart sshd" &
Start-Sleep 2
# Kill local SSH processes
Get-Process ssh -ErrorAction SilentlyContinue | Stop-Process -Force
```

**Option 2: Restart Droplet (DigitalOcean Dashboard)**

1. Go to https://cloud.digitalocean.com/droplets
2. Click on `mcp-gateway` droplet
3. Click "Power" → "Power Cycle" (NOT destroy!)
4. Wait 2-3 minutes for restart
5. Retry SSH connection

**Option 3: Restart Docker Desktop on Droplet (via DigitalOcean Console)**

1. Go to droplet in DigitalOcean dashboard
2. Click "Access" → "Launch Droplet Console"
3. Login as root
4. Run:

```bash
systemctl --user restart docker-desktop
systemctl --user status docker-desktop
docker ps
```

**Option 4: Clean Docker State**

```bash
# Via DigitalOcean Console
systemctl --user stop docker-desktop
rm -rf ~/.docker/desktop
systemctl --user start docker-desktop

# Wait for Docker to start (30-60 seconds)
docker version
```

**Option 5: Nuclear - Clean Start**

```bash
# Via DigitalOcean Console
cd /opt/Dev-Tools

# Stop all containers
docker compose -f compose/docker-compose.yml down -v

# Remove Docker Desktop (if corrupted)
apt-get remove --purge docker-desktop -y

# Reinstall Docker Compose standalone (lightweight)
curl -SL https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
docker-compose version

# Restart services
docker-compose -f compose/docker-compose.yml up -d gateway-mcp rag-context state-persistence qdrant postgres
```

### Check Droplet Resource Usage

SSH hanging often means resource exhaustion:

```bash
# Via DigitalOcean Console
# Check memory
free -h

# Check disk space
df -h

# Check running processes
top -bn1 | head -20

# Check Docker resource usage
docker stats --no-stream

# If memory is full, restart hungry containers
docker restart $(docker ps -q)
```

### If containers won't start:

```bash
# Check logs
docker compose -f compose/docker-compose.yml logs gateway-mcp

# Restart specific service
docker compose -f compose/docker-compose.yml restart gateway-mcp

# Full restart
docker compose -f compose/docker-compose.yml down
docker compose -f compose/docker-compose.yml up -d gateway-mcp rag-context state-persistence qdrant postgres
```

### If gateway can't find MCP servers:

```bash
# Verify Docker MCP plugin
docker mcp --version

# Check MCP server list
docker mcp list
```

### Clean deployment:

```bash
# Stop all services
docker compose -f compose/docker-compose.yml down

# Remove volumes (CAUTION: deletes data)
docker volume prune

# Rebuild and start
docker compose -f compose/docker-compose.yml build gateway-mcp rag-context state-persistence
docker compose -f compose/docker-compose.yml up -d gateway-mcp rag-context state-persistence qdrant postgres
```

## Update .env on Droplet

If you need to add LINEAR_API_KEY or other variables:

```bash
# Via VS Code Remote SSH
cd /opt/Dev-Tools
nano config/env/.env

# Or via command line
echo "LINEAR_API_KEY=lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571" >> config/env/.env

# Restart affected services
docker compose -f compose/docker-compose.yml restart gateway-mcp
```

## Next Steps

1. **Configure Gradient AI Agents** - Update each agent in DigitalOcean dashboard with:
   - `MCP_GATEWAY_URL=http://45.55.173.72:8000`
2. **Test End-to-End** - Call an agent endpoint and verify it can access MCP tools

3. **Monitor** - Check Langfuse for traces, Prometheus for metrics

## Why This Works Better

- **No SSH hanging** - Using VS Code's persistent SSH connection instead of one-off commands
- **Direct access** - Interactive terminal on the droplet for debugging
- **File editing** - Edit files directly on droplet with VS Code
- **Clear separation** - Agents run in Gradient AI (managed), infrastructure runs in Docker (self-hosted)
