# Dev-Tools

> Single-root development environment for AI-assisted software development workflows

Dev-Tools is a unified AI DevOps automation platform built on a single orchestrator container using LangGraph multi-agent workflows. It eliminates legacy microservice agents in favor of a scalable, memory-efficient architecture (900MB → 154MB RAM, 100% → 0.2% CPU).

## Key Features

- **LangGraph Multi-Agent Orchestration**: All agent logic (feature-dev, code-review, infrastructure, cicd, documentation, orchestrator) is now implemented as nodes in a single orchestrator container using LangGraph.
- **MCP Direct Access**: 150+ tools across 17 servers via stdio transport (memory, filesystem, git, playwright, notion, etc.)
- **Linear Integration**: Direct SDK access for issue management with OAuth support
- **LLM Inference**: DigitalOcean Gradient AI with per-agent model optimization
- **Observability**: LangSmith LLM tracing + Prometheus HTTP metrics
- **State Management**: PostgreSQL-backed workflow state
- **RAG Configuration**: Qdrant vector database and indexing for context-aware agents
- **Backup & Restore**: Volume management scripts for data persistence

## Resource Metrics

- **Memory**: 154MB RAM (down from 900MB)
- **CPU**: 0.2% (down from 100%)

## Deployment Status

**Production-ready with full observability**

- **LangSmith Integration**: All agent nodes + workflows traced (prompts, completions, tokens, latencies)
- **LangGraph Workflows**: Multi-agent orchestration with PostgreSQL state persistence
- **MCP Toolkit**: 150+ tools via direct stdio transport (50-100ms latency)
- **Gradient AI**: Per-agent model optimization (70b → 8b based on complexity)
- **HITL Approvals**: Risk assessment + Linear sub-issues (DEV-68) + template-based approval workflows
- **Copilot Integration**: Natural language chat interface with session management
- **Event Bus**: Redis-based inter-agent communication with <1s latency
- **Prometheus Metrics**: HTTP monitoring on all services
- **Agent Registry**: Phase 6 discovery infrastructure ready

**Observability Stack:**

- LLM Traces → LangSmith (https://smith.langchain.com)
- HTTP Metrics → Prometheus → Grafana
- Workflow State → PostgreSQL
- Vector Operations → Qdrant Cloud
- Notifications → Linear + Email

**Deploy Now:** `./support/scripts/deploy.ps1 -Target remote` (see validation report: `support/reports/LANGSMITH_INTEGRATION_VALIDATION.md`)

## Quick Start

### Prerequisites

- Docker 24.0+
- Docker Compose 2.20+
- VS Code with extensions:
  - Remote - SSH
  - Dev Containers
  - Docker

### Installation

```bash
# Clone repository
git clone https://github.com/Appsmithery/Dev-Tools.git
cd Dev-Tools

# Configure environment
cp config/env/.env.template config/env/.env
# Edit .env with your settings

# Make scripts executable (Linux/Mac)
chmod +x support/scripts/*.sh

# Start services
cd deploy
docker-compose up -d

# Verify services
docker-compose ps
```

**Windows PowerShell:**

```powershell
# Navigate to deploy directory
cd deploy

# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### Remote Development Setup

1. **Connect to droplet**:

   - VS Code → Remote-SSH → Connect to Host
   - Open `/path/to/Dev-Tools`

2. **Attach to container**:

   - Click "Reopen in Container" when prompted
   - Wait for devcontainer build

3. **Verify services**:

   ```bash
   cd deploy
   docker-compose ps
   ```

# Test health endpoints (only 3 core services remain)

curl http://localhost:8000/health # MCP Gateway
curl http://localhost:8001/health # Orchestrator (LangGraph)
curl http://localhost:8007/health # RAG Context
curl http://localhost:8008/health # State Persistence

````

**Windows PowerShell:**

```powershell
# Test health endpoints
Invoke-RestMethod http://localhost:8000/health  # MCP Gateway
Invoke-RestMethod http://localhost:8001/health  # Orchestrator (LangGraph)
Invoke-RestMethod http://localhost:8007/health  # RAG Context
Invoke-RestMethod http://localhost:8008/health  # State Persistence
````

## Architecture

```
Dev-Tools (LangGraph Multi-Agent Orchestrator)
├── Orchestrator (8001) - LangGraph agent nodes (feature-dev, code-review, infrastructure, cicd, documentation, orchestrator)
├── MCP Gateway (8000) - Linear OAuth, tool routing
├── RAG Context (8007) - Qdrant vector search
├── State Persistence (8008) - PostgreSQL workflow state
├── Shared Modules (shared/lib/)
│   ├── mcp_client.py - Direct MCP tool invocation
│   ├── progressive_mcp_loader.py - Progressive tool disclosure
│   ├── linear_workspace_client.py - Linear GraphQL API
│   └── gradient_client.py - DigitalOcean Gradient AI
└── Configuration
  ├── Routing rules (config/routing/)
  ├── MCP tool mappings (config/mcp-agent-tool-mapping.yaml)
  ├── RAG indexing (config/rag/)
  └── Environment (config/env/.env)
```

**Architecture Highlights:**

- **Direct Stdio Transport**: Agents invoke MCP tools via subprocess (no HTTP overhead)
- **Linear Hybrid**: OAuth via Node.js gateway, programmatic access via Python SDK
- **Per-Agent Models**: Optimized LLM selection (70b for orchestrator, codellama-13b for feature-dev, etc.)
- **Observability**: Automatic Langfuse tracing + Prometheus metrics on all agents

For detailed architecture, see [support/docs/ARCHITECTURE.md](support/docs/ARCHITECTURE.md) and [support/docs/archive/IMPLEMENTATION_SUMMARY_MCP_LINEAR.md](support/docs/archive/IMPLEMENTATION_SUMMARY_MCP_LINEAR.md).

## 🚀 Deployment

### Production Deployment

Follow our [45-minute DigitalOcean deployment guide](support/docs/DIGITALOCEAN_QUICK_DEPLOY.md) for production setup:

- 2GB RAM minimum (4GB recommended)
- Ubuntu 22.04 LTS
- Pre-configured Docker Compose
- Health checks and monitoring included

### Local Development

See [Quick Start](#quick-start) above for local Docker Compose setup.

For AWS, Azure, or GCP deployments, adapt the DigitalOcean guide or see [support/docs/DEPLOYMENT.md](support/docs/DEPLOYMENT.md).

### Service Ports

| Service             | Port       | Purpose                  |
| ------------------- | ---------- | ------------------------ |
| MCP Gateway         | 8000       | Linear OAuth + API proxy |
| Orchestrator        | 8001       | LangGraph agent nodes    |
| RAG Context Manager | 8007       | Semantic code search     |
| State Persistence   | 8008       | Task/workflow state      |
| Qdrant              | 6333, 6334 | Vector database          |
| PostgreSQL          | 5432       | Relational database      |
| Prometheus          | 9090       | Metrics collection       |

**Note:** MCP tool invocation now happens directly via stdio (no HTTP gateway for tools). The gateway at port 8000 handles Linear OAuth only.

## LangGraph Agent Nodes

All agent logic is now implemented as nodes in the LangGraph workflow within the orchestrator container:

- **feature-dev**: Feature implementation, code generation, testing
- **code-review**: Quality analysis, security scanning, review comments
- **infrastructure**: IaC (Terraform, Docker Compose), deployment
- **cicd**: Pipeline automation, workflow orchestration
- **documentation**: README, API docs, architecture diagrams
- **orchestrator**: Task routing, agent selection, workflow orchestration

## Model Configuration

**Single Source of Truth:** `config/agents/models.yaml`

All LLM configuration (models, costs, context windows, parameters) is managed via YAML with Pydantic validation. No hardcoded models in Python code.

**Quick Model Switch:**
```bash
# Edit YAML
nano config/agents/models.yaml

# Restart orchestrator (30s)
docker compose restart orchestrator
```

**Features:**
- ✅ **Hot-reload** - No rebuild required for model changes
- ✅ **Environment overrides** - Use cheaper models in dev, production models in prod
- ✅ **Automatic cost tracking** - Token costs calculated from YAML config
- ✅ **Validation** - PowerShell script ensures all agents have valid config

**Example Config:**
```yaml
agents:
  orchestrator:
    model: llama3.3-70b-instruct
    cost_per_1m_tokens: 0.60
    context_window: 128000
    max_tokens: 2000
    temperature: 0.7

environments:
  development:
    orchestrator:
      model: llama3-8b-instruct  # 3x cheaper for testing
      cost_per_1m_tokens: 0.20
```

**Documentation:** See [LLM Configuration Refactoring Plan](support/docs/guides/implementation/LLM_CONFIG_REFACTORING_PLAN.md) for architecture details and [Observability Guide](support/docs/OBSERVABILITY_GUIDE.md) for token tracking.

## LangGraph Workflows

All agent workflows are now orchestrated via LangGraph in the orchestrator container. See [support/docs/LANGGRAPH_ARCHITECTURE.md](support/docs/LANGGRAPH_ARCHITECTURE.md) for details.

### Submit a Task

```bash
curl -X POST http://localhost:8001/orchestrate/langgraph \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Add user authentication with JWT",
    "priority": "high"
  }'
```

**Windows PowerShell:**

```powershell
$body = @{
    description = "Add user authentication with JWT"
    priority = "high"
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8001/orchestrate/langgraph `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
```

### Human-in-the-Loop (HITL) Approvals

High-risk operations (production deploys, destructive database work, secrets handling) trigger a human approval gate before orchestration proceeds. The orchestrator:

1. **Creates Linear sub-issue** under DEV-68 (HITL Approvals Hub) using agent-specific templates
2. **Responds** with `routing_plan.status = "approval_pending"` and `approval_request_id`
3. **Includes metadata**: Task description, risk level, agent name, timestamp, environment
4. **Waits** for approval via Linear issue status change (e.g., "Done" = approved, "Canceled" = rejected)

**Linear Integration:**

- Approval Hub: [DEV-68](https://linear.app/dev-ops/issue/DEV-68)
- Sub-issues use HITL templates: `HITL_ORCHESTRATOR_TEMPLATE_UUID`, `HITL_FEATURE_DEV_TEMPLATE_UUID`, etc.
- Each sub-issue includes risk emoji (🔴 critical, 🟠 high, 🟡 medium, 🟢 low)

See [support/docs/architecture/NOTIFICATION_SYSTEM.md](support/docs/architecture/NOTIFICATION_SYSTEM.md) for complete HITL workflow details.

### Backup & Restore

```bash
./scripts/backup_volumes.sh
./scripts/restore_volumes.sh ./backups/20250112_140000
```

## Configuration

### Environment Variables

Edit `config/env/.env` as needed for orchestrator, gateway, and supporting services. See `.env.template` for all options.

### Task Routing Rules

Edit `config/routing/task-router.rules.yaml` to control LangGraph agent node routing.

### RAG Configuration

Edit `config/rag/vectordb.config.yaml` for Qdrant and embedding model settings.

## Documentation

- **[📚 Documentation Index](support/docs/README.md)** - Complete documentation hub with navigation
- **[🚀 DigitalOcean Deployment](support/docs/DIGITALOCEAN_QUICK_DEPLOY.md)** - 45-minute production deployment guide
- **[🏠 Architecture Overview](support/docs/ARCHITECTURE.md)** - System design and components
- **[🛰️ LangGraph Architecture](support/docs/LANGGRAPH_ARCHITECTURE.md)** - Multi-agent workflow and node details
- **[🛰️ Agent Endpoints](support/docs/AGENT_ENDPOINTS.md)** - Complete API reference
- **[🔐 Secrets Management](support/docs/SECRETS_MANAGEMENT.md)** - Security and configuration
- **[📖 Operational Handbook](support/docs/HANDBOOK.md)** - Development practices and troubleshooting

## Development

### Local Development

```bash
# Start stack
make up

# View logs
make logs

# Rebuild services
make rebuild

# Stop stack
make down
```

### Adding New Agents

1. Create agent directory: `agent_<name>/` at repository root
2. Add main.py, Dockerfile, requirements.txt, README.md
3. Update `deploy/docker-compose.yml` with service definition
4. Add routing rules: `config/routing/task-router.rules.yaml`
5. Document endpoints: `support/docs/AGENT_ENDPOINTS.md`
6. Update tool access: `config/mcp-agent-tool-mapping.yaml`

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or contributions:

- **Issues**: [GitHub Issues](https://github.com/Appsmithery/Dev-Tools/issues)
- **Documentation**: [docs/](docs/)
- **Discussions**: [GitHub Discussions](https://github.com/Appsmithery/Dev-Tools/discussions)

---

**Built with** ❤️ **for remote AI-assisted development workflows**
