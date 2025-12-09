# code/chef - AI DevOps Team

[![VS Code](https://img.shields.io/badge/VS%20Code-Extension-blue?logo=visualstudiocode)](https://marketplace.visualstudio.com/items?itemName=appsmithery.vscode-codechef)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestrator-purple?logo=langchain)](https://www.langchain.com/langgraph)
[![MCP Tools](https://img.shields.io/badge/MCP_Tools-150+-green)](https://github.com/Appsmithery/code-chef)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

> LangGraph-powered multi-agent DevOps automation with 150+ MCP tools

code/chef is a unified AI DevOps automation platform built on a single orchestrator container using LangGraph multi-agent workflows. The VS Code extension brings this directly into Copilot Chat via the `@chef` participant.

## Architecture

**Flow:** User → `@chef` → Orchestrator → Specialized Agents → RAG / Context / MCP Tools → Artifacts → User

| Component             | Description                                                   |
| --------------------- | ------------------------------------------------------------- |
| **Chat Participant**  | `@chef` chat participant in Copilot Chat                      |
| **Orchestrator API**  | Supervisor (Head Chef) + Workflow Router                      |
| **Agent Nodes**       | feature-dev, code-review, infrastructure, cicd, documentation |
| **MCP Tools**         | 150+ tools (Linear, GitHub, Docker, Pylance...)               |
| **RAG Context**       | Semantic search via Qdrant for code patterns & library docs   |
| **State Persistence** | PostgreSQL for workflow state, checkpoints, HITL approvals    |
| **StateGraph**        | LangGraph orchestration with interrupt/resume for HITL        |

```
code-chef/
├── agent_orchestrator/       # LangGraph StateGraph with all agent nodes
│   ├── agents/               # Specialized agent implementations
│   │   ├── supervisor/       # Task routing & orchestration
│   │   ├── feature_dev/      # Feature implementation
│   │   ├── code_review/      # Quality analysis & security
│   │   ├── infrastructure/   # IaC (Terraform, Docker)
│   │   ├── cicd/             # Pipeline automation
│   │   └── documentation/    # Docs & architecture diagrams
│   ├── workflows/            # Declarative workflow templates
│   └── graph.py              # LangGraph StateGraph definition
├── shared/lib/               # Shared utilities
│   ├── mcp_client.py         # Direct MCP tool invocation
│   ├── progressive_mcp_loader.py  # Token-efficient tool loading
│   └── gradient_client.py    # DigitalOcean Gradient AI
├── extensions/vscode-codechef/  # VS Code extension
├── config/                   # All configuration
│   ├── agents/models.yaml    # LLM model configuration
│   ├── routing/              # Task routing rules
│   └── env/                  # Environment templates
└── deploy/                   # Docker Compose stack
```

## Key Features

- **`@chef` Chat Participant** - Natural language task submission via Copilot Chat
- **Smart Workflow Router** - Heuristic + LLM-based workflow selection with confidence scoring
- **LangGraph StateGraph** - Multi-agent orchestration with PostgreSQL checkpointing
- **150+ MCP Tools** - Progressive disclosure reduces tokens by 80-90%
- **HITL Approvals** - Linear integration for high-risk operations

## Resource Metrics

Consolidated architecture delivers significant efficiency gains:

| Metric | Before (Microservices) | After (LangGraph) |
|--------|------------------------|-------------------|
| Memory | 900MB RAM | 154MB RAM |
| CPU | 100% idle | 0.2% idle |
| Containers | 6+ agents | 1 orchestrator |

## Quick Start

### VS Code Extension

1. Install from [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=appsmithery.vscode-codechef) or [GitHub Releases](https://github.com/Appsmithery/code-chef/releases)
2. Configure: `Ctrl+Shift+P` → "code/chef: Configure"
3. Use: `@chef Add JWT authentication to my Express API`

### Self-Hosted Orchestrator

```bash
# Clone and configure
git clone https://github.com/Appsmithery/code-chef.git
cd code-chef
cp config/env/.env.template config/env/.env
# Edit .env with your API keys (or configure via GitHub Secrets for CI/CD)

# Start services
cd deploy && docker-compose up -d

# Verify health
curl http://localhost:8001/health
```

### Service Ports

| Service             | Port | Purpose                  |
| ------------------- | ---- | ------------------------ |
| Orchestrator        | 8001 | LangGraph agent nodes    |
| RAG Context         | 8007 | Semantic code search     |
| State Persistence   | 8008 | Workflow state           |
| PostgreSQL          | 5432 | Relational database      |
| Redis               | 6379 | Event bus & caching      |

## Usage

### Chat Participant Commands

| Command                            | Description              | Example                          |
| ---------------------------------- | ------------------------ | -------------------------------- |
| `@chef <task>`                     | Submit development task  | `@chef Add authentication`       |
| `@chef /status [id]`               | Check task status        | `@chef /status abc123`           |
| `@chef /workflow [name] <task>`    | Execute workflow         | `@chef /workflow Deploy PR #123` |
| `@chef /tools`                     | List available MCP tools | `@chef /tools`                   |

### API Usage

```bash
# Submit a task
curl -X POST http://localhost:8001/orchestrate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $ORCHESTRATOR_API_KEY" \
  -d '{"description": "Add user authentication with JWT", "priority": "high"}'
```

## LLM Configuration

**Single Source of Truth:** `config/agents/models.yaml`

```yaml
agents:
  orchestrator:
    model: llama3.3-70b-instruct
    cost_per_1m_tokens: 0.60
  feature_dev:
    model: codellama-13b-instruct
    cost_per_1m_tokens: 0.20
```

Hot-reload model changes without rebuild:
```bash
nano config/agents/models.yaml
docker compose restart orchestrator
```

## Observability

- **LLM Traces**: [LangSmith](https://smith.langchain.com) - prompts, completions, tokens, latencies
- **HTTP Metrics**: [Grafana Cloud](https://appsmithery.grafana.net) via Alloy
- **Workflow State**: PostgreSQL with LangGraph checkpointing
- **Vector Operations**: Qdrant Cloud

## Documentation

| Topic | Location |
|-------|----------|
| Architecture | [support/docs/ARCHITECTURE.md](support/docs/ARCHITECTURE.md) |
| Deployment | [support/docs/DEPLOYMENT.md](support/docs/DEPLOYMENT.md) |
| LangGraph Design | [support/docs/LANGGRAPH_ARCHITECTURE.md](support/docs/LANGGRAPH_ARCHITECTURE.md) |
| API Reference | [support/docs/AGENT_ENDPOINTS.md](support/docs/AGENT_ENDPOINTS.md) |
| VS Code Extension | [extensions/vscode-codechef/README.md](extensions/vscode-codechef/README.md) |

## Development

```bash
# Start stack
cd deploy && docker-compose up -d

# View logs
docker-compose logs -f orchestrator

# Rebuild after code changes
docker-compose up -d --build orchestrator

# Run tests
pytest support/tests -v
```

### Adding a New Agent Node

1. Create `agent_orchestrator/agents/<name>/` with `__init__.py`, `system.prompt.md`
2. Inherit from `_shared.base_agent.BaseAgent`
3. Wire into `graph.py` StateGraph with conditional edges
4. Add model config to `config/agents/models.yaml`
5. Update tool mapping in `config/mcp-agent-tool-mapping.yaml`

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## License

MIT License - see [LICENSE](LICENSE)

## Links

- [VS Code Extension](https://marketplace.visualstudio.com/items?itemName=appsmithery.vscode-codechef)
- [GitHub Repository](https://github.com/Appsmithery/code-chef)
- [Linear Project](https://linear.app/dev-ops/project/codechef-78b3b839d36b)
- [LangSmith Traces](https://smith.langchain.com)
- [Grafana Metrics](https://appsmithery.grafana.net)

---

**Built with** ❤️ **using LangGraph, MCP, and VS Code**
