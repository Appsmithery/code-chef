# Dev-Tools

> Single-root development environment for AI-assisted software development workflows

Dev-Tools consolidates AI agents, MCP gateway, Docker orchestration, and development configurations into a unified repository designed for remote development on DigitalOcean droplets with VS Code Dev Containers.

## Features

- **AI Agent Suite**: Six specialized agents (Orchestrator, Feature-Dev, Code-Review, Infrastructure, CI/CD, Documentation)
- **MCP Gateway**: Centralized Model Context Protocol routing
- **Docker Compose Stack**: Complete containerized development environment
- **VS Code Integration**: Dev Container support with Remote-SSH
- **RAG Configuration**: Vector database and indexing for context-aware agents
- **State Management**: PostgreSQL-backed task tracking and workflow state
- **Backup & Restore**: Volume management scripts for data persistence

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
cp configs/env/.env.example configs/env/.env
# Edit .env with your settings

# Make scripts executable (Linux/Mac)
chmod +x scripts/*.sh

# Start services
cd compose
docker-compose up -d

# Verify services
docker-compose ps
```

**Windows PowerShell:**

```powershell
# Navigate to compose directory
cd compose

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
   ```

## Architecture

```
Dev-Tools (single-root)
├── Agents (orchestrator, feature-dev, code-review, infrastructure, cicd, documentation)
├── MCP Gateway (routes to MCP servers)
├── Compose Stack (Docker orchestration)
├── Configs (routing, RAG, state, environment)
├── Templates (pipelines, infra, docs)
└── Scripts (up, down, rebuild, backup, restore)
```

### Service Ports

| Service        | Port | Purpose             |
| -------------- | ---- | ------------------- |
| MCP Gateway    | 8000 | MCP routing         |
| Orchestrator   | 8001 | Task coordination   |
| Feature-Dev    | 8002 | Code generation     |
| Code-Review    | 8003 | Quality checks      |
| Infrastructure | 8004 | IaC generation      |
| CI/CD          | 8005 | Pipeline automation |
| Documentation  | 8006 | Doc generation      |

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

Edit `configs/env/.env`:

```bash
ORCHESTRATOR_URL=http://orchestrator:8001
MCP_GATEWAY_URL=http://gateway-mcp:8000
LOG_LEVEL=info
```

### Task Routing Rules

Edit `configs/routing/task-router.rules.yaml`:

```yaml
routes:
  - pattern: "feature|implement"
    agent: "feature-dev"
    priority: 1
```

### RAG Configuration

Edit `configs/rag/vectordb.config.yaml`:

```yaml
vectordb:
  type: "chromadb"
  host: "localhost"
  port: 8001
```

## Documentation

- **[Complete Documentation](docs/README.md)** - Full setup and usage guide
- **[Agent Endpoints](docs/AGENT_ENDPOINTS.md)** - API reference
- **[Operational Handbook](docs/HANDBOOK.md)** - Troubleshooting and maintenance

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

1. Create agent directory: `agents/new-agent/`
2. Add Dockerfile: `containers/new-agent/Dockerfile`
3. Update `compose/docker-compose.yml`
4. Add routing rules: `configs/routing/task-router.rules.yaml`
5. Document endpoints: `docs/AGENT_ENDPOINTS.md`

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
