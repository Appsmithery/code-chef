# Dev-Tools Quick Start

**Get up and running with Dev-Tools in 15 minutes.**

---

## Prerequisites

- **Docker** 24.0+ with Docker Compose
- **Git** 2.30+
- **PowerShell** 7.0+ (Windows) or Bash (Linux/Mac)
- **Python** 3.11+ (for local agent development)

---

## Local Development Setup

### 1. Clone and Configure

```bash
git clone https://github.com/Appsmithery/Dev-Tools.git
cd Dev-Tools

# Copy environment template
cp config/env/.env.template config/env/.env
```

### 2. Configure Secrets

Edit `config/env/.env` and fill in required values:

```bash
# REQUIRED: LangSmith (LLM tracing)
LANGSMITH_API_KEY=lsv2_sk_***
LANGSMITH_WORKSPACE_ID=<your-workspace-id>

# REQUIRED: DigitalOcean Gradient AI
GRADIENT_API_KEY=<digitalocean-pat>

# REQUIRED: Linear (project management)
LINEAR_API_KEY=lin_oauth_***
LINEAR_TEAM_ID=<team-uuid>

# REQUIRED: Database
DB_PASSWORD=<secure-password>
```

See [Secrets Management](operations/SECRETS_MANAGEMENT.md) for complete setup.

### 3. Start Services

```bash
cd deploy
docker compose up -d

# Wait for services to be healthy (~30s)
docker compose ps
```

### 4. Verify Health

```bash
# Check all services
curl http://localhost:8001/health  # Orchestrator
curl http://localhost:8000/health  # Gateway
curl http://localhost:8007/health  # RAG
curl http://localhost:8008/health  # State
```

Expected response: `{"status": "healthy", "mcp_gateway": "connected"}`

---

## Your First Workflow

### Submit a Task via API

```bash
curl -X POST http://localhost:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Review the authentication module for security vulnerabilities",
    "context": {
      "repository": "https://github.com/your-org/your-repo",
      "files": ["src/auth/login.py"]
    }
  }'
```

### Monitor Progress

- **LangSmith Dashboard**: https://smith.langchain.com
- **Grafana Metrics**: https://appsmithery.grafana.net
- **Docker Logs**: `docker compose logs -f orchestrator`

---

## Production Deployment

### Deploy to DigitalOcean Droplet

```powershell
# Auto-detect changes and deploy
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType auto

# Config-only (30s - for .env changes)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config

# Full rebuild (10min - for code changes)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType full
```

**Production URL**: https://codechef.appsmithery.co

**API Endpoints**:

- Orchestrator: https://codechef.appsmithery.co/api
- RAG: https://codechef.appsmithery.co/rag
- State: https://codechef.appsmithery.co/state
- LangGraph: https://codechef.appsmithery.co/langgraph

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment guide.

---

## Architecture Overview

### Services

| Service      | Port | Purpose                          |
| ------------ | ---- | -------------------------------- |
| orchestrator | 8001 | LangGraph workflow with 6 agents |
| rag-context  | 8007 | Vector search (Qdrant)           |
| state        | 8008 | Workflow persistence (Postgres)  |
| langgraph    | 8010 | LangGraph checkpoint service     |
| caddy        | 443  | Reverse proxy + SSL              |
| postgres     | 5432 | Database                         |

### Agent Nodes (within Orchestrator)

All 6 agents run as **LangGraph nodes** within the orchestrator service:

1. **Supervisor**: Task decomposition and routing
2. **Feature-Dev**: Code generation and scaffolding
3. **Code-Review**: Quality and security analysis
4. **Infrastructure**: IaC and deployment automation
5. **CI/CD**: Pipeline generation and execution
6. **Documentation**: Technical documentation

See [ARCHITECTURE.md](ARCHITECTURE.md) for details.

---

## Key Integrations

### MCP Tools (150+ Available)

Access filesystem, git, memory, sequential-thinking, and more via MCP gateway:

```python
from shared.lib.mcp_client import get_mcp_client

mcp = get_mcp_client()
tools = await mcp.discover_tools()
result = await mcp.call_tool("rust-mcp-filesystem", "read_file", {"path": "README.md"})
```

See [architecture/MCP_INTEGRATION.md](architecture/MCP_INTEGRATION.md) for tool catalog.

### Linear Project Management

Tasks, issues, and approval workflows integrate with Linear workspace:

- **Issue Creation**: Auto-create Linear issues from agent workflows
- **HITL Approvals**: High-risk operations require human approval in Linear
- **Progress Tracking**: Real-time status updates in Linear project board

See [guides/LINEAR_INTEGRATION.md](guides/LINEAR_INTEGRATION.md) for setup.

### LangSmith Tracing

All LLM calls automatically traced to LangSmith:

- **Dashboard**: https://smith.langchain.com/o/<workspace-id>/projects
- **Traces**: View token usage, latency, and agent reasoning
- **Debugging**: Replay failed workflows with full context

See [guides/LANGSMITH_TRACING.md](guides/LANGSMITH_TRACING.md) for examples.

---

## Common Tasks

### Update Environment Variables

```powershell
# Edit config/env/.env locally
# Deploy changes (30s restart)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config
```

### View Logs

```bash
# Local
docker compose logs -f orchestrator

# Remote (use SSH alias)
ssh do-codechef-droplet "cd /opt/Dev-Tools/deploy && docker compose logs -f orchestrator"
```

### Restart Services

```bash
# Local
docker compose restart orchestrator

# Remote (config changes require down+up)
ssh do-codechef-droplet "cd /opt/Dev-Tools/deploy && docker compose down && docker compose up -d"
```

### Clean Up Docker Resources

```powershell
# Local
docker system prune -af
docker builder prune -af

# Remote
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType cleanup
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker compose logs orchestrator

# Common issues:
# 1. Missing environment variables - Check config/env/.env
# 2. Port conflicts - Ensure ports 8000-8010 are free
# 3. Database connection - Verify DB_PASSWORD and postgres service health
```

### Environment Variables Not Loading

```bash
# Docker Compose only reads .env at startup
# Must use down+up, not restart
docker compose down
docker compose up -d
```

### MCP Gateway Disconnected

```bash
# Check gateway health
curl http://localhost:8000/health

# Restart gateway
docker compose restart gateway-mcp

# Verify orchestrator can connect
docker compose logs orchestrator | grep "MCP"
```

---

## Next Steps

- **[Architecture Guide](ARCHITECTURE.md)** - Understand system design
- **[Deployment Guide](DEPLOYMENT.md)** - Production deployment strategies
- **[Observability](OBSERVABILITY.md)** - Monitoring and tracing setup
- **[Linear Integration](guides/LINEAR_INTEGRATION.md)** - Project management setup
- **[Secrets Management](operations/SECRETS_MANAGEMENT.md)** - Security best practices

---

## Getting Help

- **Documentation Issues**: Open issue on GitHub
- **Deployment Problems**: Check [DEPLOYMENT.md](DEPLOYMENT.md) troubleshooting section
- **Architecture Questions**: See [ARCHITECTURE.md](ARCHITECTURE.md)
- **Integration Support**: See respective integration guides in `guides/`
