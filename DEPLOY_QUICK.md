# Hybrid Architecture Deployment Guide

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
