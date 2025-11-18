# Dev-Tools

> Single-root development environment for AI-assisted software development workflows

Dev-Tools consolidates AI agents, MCP gateway, Docker orchestration, and development configurations into a unified repository designed for remote development on DigitalOcean droplets with VS Code Dev Containers.

## Features

- **AI Agent Suite**: Six specialized agents (Orchestrator, Feature-Dev, Code-Review, Infrastructure, CI/CD, Documentation)
- **MCP Direct Access**: 150+ tools across 17 servers via stdio transport (memory, filesystem, git, playwright, notion, etc.)
- **Linear Integration**: Direct SDK access for issue management with OAuth support
- **LLM Inference**: DigitalOcean Gradient AI with per-agent model optimization
- **Observability**: Langfuse LLM tracing + Prometheus HTTP metrics
- **LangGraph Workflows**: Multi-agent orchestration with PostgreSQL state persistence and streaming
- **Inter-Agent Communication**: HTTP-based workflow orchestration with automated task routing
- **Docker Compose Stack**: Complete containerized development environment
- **Docker MCP Toolkit**: Direct stdio communication with MCP servers (no HTTP gateway)
- **VS Code Integration**: Dev Container support with Remote-SSH
- **RAG Configuration**: Qdrant vector database and indexing for context-aware agents
- **State Management**: PostgreSQL-backed task tracking and workflow state
- **Backup & Restore**: Volume management scripts for data persistence

## Deployment Status

**LangGraph Integration Complete** ✅ - Multi-agent workflow orchestration ready

- ✅ LangGraph workflow service on port 8009
- ✅ PostgreSQL checkpointer for state persistence
- ✅ Streaming support via SSE (Server-Sent Events)
- ✅ LangChain-compatible Gradient AI wrapper
- ✅ FastAPI server with /invoke, /stream, /stream-events endpoints
- ✅ Docker container with full agent service dependencies
- ✅ All integration tests passing (5/5)

**MCP Toolkit Integration Complete** ✅ - Production-ready with direct stdio transport

- ✅ All 6 agents operational with direct MCP tool access
- ✅ Phase 1-4 complete: Discovery system, Linear SDK, stdio transport, documentation
- ✅ Gradient AI client integrated (OpenAI-compatible with Langfuse tracing)
- ✅ Prometheus metrics collection active on all services
- ✅ 50% faster tool invocation (50-100ms vs HTTP)
- ✅ Zero 404 errors from eliminated HTTP gateway routing
- ✅ Comprehensive documentation and pre-deployment checklist

**Next:** Deploy to DigitalOcean droplet (see `support/docs/PRE_DEPLOYMENT_CHECKLIST.md`)

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
   cd compose
   docker-compose ps

   # Test health endpoints
   curl http://localhost:8000/health  # MCP Gateway
   curl http://localhost:8001/health  # Orchestrator
   curl http://localhost:8002/health  # Feature-Dev
   curl http://localhost:8003/health  # Code-Review
   curl http://localhost:8004/health  # Infrastructure
   curl http://localhost:8005/health  # CI/CD
   curl http://localhost:8006/health  # Documentation
   curl http://localhost:8007/health  # RAG Context
   curl http://localhost:8008/health  # State Persistence
   ```

   **Windows PowerShell:**

   ```powershell
   # Test health endpoints
   Invoke-RestMethod http://localhost:8000/health  # MCP Gateway
   Invoke-RestMethod http://localhost:8001/health  # Orchestrator
   Invoke-RestMethod http://localhost:8002/health  # Feature-Dev
   Invoke-RestMethod http://localhost:8003/health  # Code-Review
   Invoke-RestMethod http://localhost:8004/health  # Infrastructure
   Invoke-RestMethod http://localhost:8005/health  # CI/CD
   Invoke-RestMethod http://localhost:8006/health  # Documentation
   Invoke-RestMethod http://localhost:8007/health  # RAG Context
   Invoke-RestMethod http://localhost:8008/health  # State Persistence
   ```

## Architecture

```
Dev-Tools (MCP Toolkit Integration - Direct Stdio Transport)
├── Agents (6 specialized FastAPI services)
│   ├── Orchestrator (8001) - Task routing & coordination
│   ├── Feature-Dev (8002) - Code generation
│   ├── Code-Review (8003) - Quality & security
│   ├── Infrastructure (8004) - IaC authoring
│   ├── CI/CD (8005) - Pipeline automation
│   └── Documentation (8006) - Doc generation
├── MCP Integration
│   ├── Direct Stdio Access (shared/lib/mcp_tool_client.py)
│   ├── Docker MCP Toolkit (150+ tools, 17 servers)
│   └── Linear Gateway (8000) - OAuth only (Node.js)
├── Supporting Services
│   ├── RAG Context (8007) - Qdrant vector search
│   └── State Persistence (8008) - PostgreSQL workflow state
├── Shared Modules (shared/lib/)
│   ├── mcp_tool_client.py - Direct MCP tool invocation
│   ├── mcp_discovery.py - Real-time server discovery
│   ├── linear_client.py - Direct Linear SDK access
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
| Linear Gateway      | 8000       | Linear OAuth + API proxy |
| Orchestrator        | 8001       | Task coordination        |
| Feature-Dev         | 8002       | Code generation          |
| Code-Review         | 8003       | Quality checks           |
| Infrastructure      | 8004       | IaC generation           |
| CI/CD               | 8005       | Pipeline automation      |
| Documentation       | 8006       | Doc generation           |
| RAG Context Manager | 8007       | Semantic code search     |
| State Persistence   | 8008       | Task/workflow state      |
| Qdrant              | 6333, 6334 | Vector database          |
| PostgreSQL          | 5432       | Relational database      |
| Prometheus          | 9090       | Metrics collection       |

**Note:** MCP tool invocation now happens directly via stdio (no HTTP gateway for tools). The gateway at port 8000 handles Linear OAuth only.

## Agent Responsibilities

### Orchestrator

Coordinates task routing, agent selection, and workflow orchestration.

### Feature-Dev

Implements features, generates code, sets up testing.

### Code-Review

Performs quality analysis, security scanning, generates review comments.

### Infrastructure

Generates IaC (Terraform, Docker Compose), manages deployments.

### CI/CD

Creates pipelines, automates workflows, orchestrates builds.

### Documentation

Generates READMEs, API docs, architecture diagrams.

## Usage

### Task-Based Workflows

Dev-Tools uses [Task](https://taskfile.dev) for agent workflow automation. Each agent has its own Taskfile with standardized commands.

**Quick Commands:**

```bash
# Check agent health
task health

# Build all agent containers
task build:all

# Start services
task compose:up

# Stop services
task compose:down
```

**Per-Agent Commands:**

```bash
# Run agent locally
task <agent>:dev:run

# Build agent container
task <agent>:build

# Check agent health
task <agent>:health

# View agent logs
task <agent>:logs
```

For complete workflow documentation, see [support/docs/TASKFILE_WORKFLOWS.md](support/docs/TASKFILE_WORKFLOWS.md).

### Submit a Task

```bash
curl -X POST http://localhost:8001/orchestrate \
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

Invoke-RestMethod -Uri http://localhost:8001/orchestrate `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
```

**Response:**

```json
{
  "task_id": "uuid",
  "subtasks": [
    {
      "id": "uuid",
      "agent_type": "feature-dev",
      "description": "Implement JWT authentication",
      "status": "pending"
    }
  ],
  "routing_plan": {
    "execution_order": ["uuid"],
    "estimated_duration_minutes": 15
  },
  "estimated_tokens": 25
}
```

### Human-in-the-Loop (HITL) Approvals

High-risk operations (production deploys, destructive database work, secrets handling) trigger a human approval gate before orchestration proceeds.

1. **First-time setup:**


    ```powershell
    task workflow:init-db
    ```
    Initializes the `approval_requests` table in PostgreSQL.

2. **Submit task:** `/orchestrate` responds with `routing_plan.status = "approval_pending"` and an `approval_request_id`.
3. **Review queue:**


    ```powershell
    task workflow:list-pending
    ```

4. **Approve or reject:**


    ```powershell
    task workflow:approve REQUEST_ID=<uuid>
    task workflow:reject REQUEST_ID=<uuid> REASON="Needs runbook"
    ```

5. **Resume orchestration:**


    ```powershell
    Invoke-RestMethod -Uri http://localhost:8001/resume/<task_id> -Method Post
    ```

Rejected or expired approvals return HTTP errors with explanatory messages so the operator can re-submit safely.

### Backup Volumes

```bash
./scripts/backup_volumes.sh
```

### Restore from Backup

```bash
./scripts/restore_volumes.sh ./backups/20250112_140000
```

## Configuration

### Environment Variables

Edit `config/env/.env`:

```bash
ORCHESTRATOR_URL=http://orchestrator:8001
MCP_GATEWAY_URL=http://gateway-mcp:8000
LOG_LEVEL=info
```

### Task Routing Rules

Edit `config/routing/task-router.rules.yaml`:

```yaml
routes:
  - pattern: "feature|implement"
    agent: "feature-dev"
    priority: 1
```

### RAG Configuration

Edit `config/rag/vectordb.config.yaml`:

```yaml
vectordb:
  type: "qdrant"
  mode: "cloud"
  url_env: "QDRANT_URL"
  api_key_env: "QDRANT_API_KEY"
  default_collection: "the-shop"

embeddings:
  provider: "digitalocean-gradient"
  model_env: "GRADIENT_EMBEDDING_MODEL"
```

## Documentation

- **[📚 Documentation Index](support/docs/README.md)** - Complete documentation hub with navigation
- **[🚀 DigitalOcean Deployment](support/docs/DIGITALOCEAN_QUICK_DEPLOY.md)** - 45-minute production deployment guide
- **[🏭️ Architecture Overview](support/docs/ARCHITECTURE.md)** - System design and components
- **[📡 Agent Endpoints](support/docs/AGENT_ENDPOINTS.md)** - Complete API reference
- **[🔒 Secrets Management](support/docs/SECRETS_MANAGEMENT.md)** - Security and configuration
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
