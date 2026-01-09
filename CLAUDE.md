# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

code/chef is a multi-agent orchestrator system built on LangGraph that provides AI-powered development capabilities through VS Code. The system uses specialized agents for different DevOps functions (feature development, code review, infrastructure, CI/CD, documentation) coordinated through a supervisor agent.

## Key Technologies

- **LangGraph**: Multi-agent workflow orchestration with PostgreSQL checkpointing
- **FastAPI**: Service APIs for orchestrator and infrastructure services
- **MCP (Model Context Protocol)**: 150+ specialized tools across 17 servers
- **LangSmith**: Distributed tracing and observability
- **Docker Compose**: Service orchestration and deployment
- **OpenRouter/DigitalOcean Gradient**: Multi-model LLM access

## Development Commands

### Environment Setup

```bash
# Create/activate virtual environment (Python 3.11)
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r agent_orchestrator/requirements.txt

# Load environment variables (Windows)
.\load_env.ps1

# Copy environment template
cp config/env/.env.template config/env/.env
# Edit config/env/.env with your API keys
```

### Running Services

```bash
# Start all services
cd deploy && docker-compose up -d

# Check service health
curl http://localhost:8001/health  # Orchestrator
curl http://localhost:8007/health  # RAG Context
curl http://localhost:8008/health  # State Persistence

# View logs
docker-compose logs -f orchestrator
docker-compose logs -f [service-name]

# Stop services
docker-compose down

# Rebuild specific service
docker-compose up -d --build orchestrator
```

### Testing

```bash
# Run LangSmith integration tests
python test_langsmith_basic.py

# Run evaluation scripts
python support/scripts/evaluation/evaluate_workflow.py
```

### Deployment

```powershell
# Auto-detect changes and deploy to production
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType auto

# Config-only deployment (30s - for .env changes)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config

# Full rebuild (10min - for code changes)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType full
```

## Architecture

### Core Structure

```
agent_orchestrator/          # Main orchestrator service
├── graph.py                 # LangGraph workflow definition (StateGraph)
├── main.py                  # FastAPI entrypoint
├── agents/                  # Specialized agent implementations
│   ├── _shared/base_agent.py  # Base agent class with tool loading
│   ├── supervisor/          # Task routing agent
│   ├── feature_dev/         # Code implementation agent
│   ├── code_review/         # Security/quality review agent
│   ├── infrastructure/      # IaC + ModelOps agent
│   ├── cicd/               # Pipeline automation agent
│   └── documentation/       # Docs generation agent
├── workflows/               # Workflow engine and templates
│   ├── workflow_engine.py   # Template-driven execution
│   └── workflow_router.py   # Workflow selection logic
└── tools/                   # Custom MCP tool implementations

shared/                      # Shared libraries and services
├── lib/                     # Core library modules
│   ├── llm_client.py       # LLM provider abstraction
│   ├── mcp_client.py       # MCP Gateway client
│   ├── progressive_mcp_loader.py  # Token-efficient tool loading
│   ├── error_recovery_engine.py   # Error recovery with retries
│   ├── agent_memory.py     # Cross-agent knowledge sharing
│   ├── linear_client.py    # Linear issue tracking integration
│   └── event_bus.py        # Inter-agent communication
├── services/                # Infrastructure services
│   └── rag/                # RAG context manager
└── mcp/                     # MCP Gateway and servers
    ├── gateway/gateway.py   # HTTP-to-stdio bridge (Node.js)
    └── servers/             # MCP server implementations

config/                      # Configuration files
├── agents/models.yaml       # Agent-to-model mappings
├── mcp-agent-tool-mapping.yaml  # Tool-to-agent mappings
├── error-handling.yaml      # Error recovery policies
├── hitl/                    # Human-in-the-loop approval policies
├── modelops/                # ModelOps training defaults
└── env/.env                 # Environment variables

extensions/vscode-codechef/  # VS Code extension
support/docs/                # Documentation
deploy/                      # Docker Compose and deployment scripts
```

### Agent Architecture

All agents inherit from `BaseAgent` (agent_orchestrator/agents/_shared/base_agent.py) which provides:

- **Progressive Tool Loading**: Tools bound at invoke-time based on token strategy (MINIMAL/PROGRESSIVE/FULL)
- **LangSmith Tracing**: `@traceable` decorators for observability
- **Error Recovery**: Integration with error recovery engine for resilience
- **Cross-Agent Memory**: Knowledge sharing via AgentMemoryManager
- **Inter-Agent Communication**: EventBus pub/sub pattern for agent coordination

### Workflow State

The `WorkflowState` TypedDict (graph.py:78-100) is the core state object passed between agents:

- `messages`: Conversation history
- `current_agent`, `next_agent`: Routing information
- `task_result`: Agent execution results
- `workflow_id`, `thread_id`: Checkpointing identifiers
- `requires_approval`, `pending_operation`: HITL approval state
- `captured_insights`, `memory_context`: Cross-agent memory
- `workflow_template`, `use_template_engine`: Template-driven execution

### Service Ports

| Service       | Port | Health Endpoint | Purpose              |
|---------------|------|----------------|----------------------|
| orchestrator  | 8001 | /health        | Main API             |
| rag-context   | 8007 | /health        | Semantic search      |
| state-persist | 8008 | /health        | Workflow persistence |
| agent-registry| 8009 | /health        | Agent discovery      |
| redis         | 6379 | N/A            | Event bus            |
| postgres      | 5432 | N/A            | Database             |

## Important Configuration Files

### Agent Model Selection

Edit `config/agents/models.yaml` to configure which LLM each agent uses. Default models:

- Supervisor: Claude 3.5 Sonnet (routing)
- Feature Dev: Qwen 2.5 Coder 32B (code generation)
- Code Review: DeepSeek V3 (analysis)
- Infrastructure: Gemini 2.0 Flash (IaC)
- CI/CD: Gemini 2.0 Flash (YAML)
- Documentation: DeepSeek V3 (technical writing)

### MCP Tool Mapping

Edit `config/mcp-agent-tool-mapping.yaml` to control which tools each agent can access. The progressive loader uses this to prioritize tools by agent specialty.

### Error Recovery Policies

Edit `config/error-handling.yaml` to configure retry strategies, circuit breakers, and fallback behaviors for different error types.

## LangGraph Workflow Execution

The system supports two execution modes:

1. **Supervisor-driven** (default): Supervisor agent dynamically routes tasks to specialized agents based on LLM decisions
2. **Template-driven**: Declarative YAML workflows executed by WorkflowEngine for deterministic multi-step processes

Key workflow functions in `graph.py`:

- `supervisor_node()`: Routes tasks to appropriate agents
- `agent_node()`: Executes agent with tool binding and error recovery
- `create_workflow_graph()`: Builds the StateGraph with conditional edges
- PostgreSQL checkpointing enables interrupt/resume for HITL approval flows

## ModelOps (Model Fine-tuning)

The Infrastructure agent includes ModelOps capabilities for fine-tuning agent models:

**Architecture**: ModelOpsCoordinator → ModelOpsTrainer + ModelEvaluator + ModelOpsDeployment + ModelRegistry

**VS Code Commands**:
- `codechef.modelops.train` - Start training wizard
- `codechef.modelops.evaluate` - Evaluate model performance
- `codechef.modelops.deploy` - Deploy model to agent
- `codechef.modelops.rollback` - Rollback to previous version
- `codechef.modelops.modelVersions` - View deployment history

**Files**:
- `agent_orchestrator/agents/infrastructure/modelops/` - Core modules
- `config/models/registry.json` - Model version registry
- `config/modelops/training_defaults.yaml` - Training presets

See `support/docs/operations/LLM_OPERATIONS.md` for complete guide.

## MCP Integration

The MCP Gateway (shared/mcp/gateway/gateway.py) provides HTTP-to-stdio bridge for 150+ tools across 17 servers.

**Tool Categories**:
- Filesystem (24 tools): File I/O, directory management
- Git (5 tools): Repository operations
- Docker (13 tools): Container management
- Playwright (21 tools): Browser automation, E2E testing
- Notion (19 tools): Documentation and task management

Agents access tools via `MCPClient` (shared/lib/mcp_client.py). The `ProgressiveMCPLoader` implements token-efficient tool loading strategies.

## Environment Variables

Required variables in `config/env/.env`:

```bash
# LLM Provider (at least one required)
OPENROUTER_API_KEY=sk-or-v1-...      # Recommended
GRADIENT_API_KEY=dop_v1_...          # Alternative

# Issue Tracking
LINEAR_API_KEY=lin_api_...           # Required

# Observability (optional)
LANGSMITH_API_KEY=lsv2_sk_...        # LLM tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=code-chef-production

# Semantic Search (optional)
QDRANT_API_KEY=...
QDRANT_URL=https://...

# Database (auto-configured in Docker)
POSTGRES_PASSWORD=...
```

## VS Code Extension Development

The extension (extensions/vscode-codechef/) provides Copilot Chat integration with `@chef` participant.

**Key Files**:
- `src/extension.ts` - Extension activation and participant registration
- `src/commands/modelops.ts` - ModelOps command handlers
- `src/api/orchestrator.ts` - API client for orchestrator service

**Development**:
```bash
cd extensions/vscode-codechef
npm install
npm run compile
code --extensionDevelopmentPath=.
```

## LangSmith Integration

All agent invocations are traced in LangSmith with per-agent projects:

- `code-chef-orchestrator`
- `code-chef-feature-dev`
- `code-chef-code-review`
- `code-chef-infrastructure`
- `code-chef-cicd`
- `code-chef-documentation`

View traces at https://smith.langchain.com

Evaluation scripts in `support/scripts/evaluation/` compare model performance using 5 metrics: accuracy, completeness, efficiency, latency, integration.

## Common Development Patterns

### Adding a New Agent

1. Create directory: `agent_orchestrator/agents/new_agent/`
2. Implement `__init__.py` inheriting from `BaseAgent`
3. Add configuration: `config/agents/new_agent/config.yaml`
4. Update model mapping: `config/agents/models.yaml`
5. Add MCP tool mappings: `config/mcp-agent-tool-mapping.yaml`
6. Register in graph: `agent_orchestrator/graph.py`

### Adding a New MCP Tool

1. Implement tool in `agent_orchestrator/tools/`
2. Register in MCP Gateway: `shared/mcp/gateway/gateway.py`
3. Update tool mappings: `config/mcp-agent-tool-mapping.yaml`

### Adding a Workflow Template

1. Create YAML: `agent_orchestrator/workflows/templates/my-workflow.yaml`
2. Define steps with agent assignments and conditions
3. Register in WorkflowRouter: `agent_orchestrator/workflows/workflow_router.py`

## Debugging

### Enable Debug Logging

Add to agent main.py:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Inspect LangGraph Checkpoints

Query PostgreSQL database for workflow state:
```sql
SELECT thread_id, checkpoint_id, channel_values
FROM checkpoints
WHERE thread_id = 'your-thread-id';
```

### View LangSmith Traces

Navigate to project URL in logs or check https://smith.langchain.com

### Test Agent in Isolation

```python
from agents.feature_dev import FeatureDevAgent
agent = FeatureDevAgent("feature-dev")
result = agent.invoke({"messages": [HumanMessage(content="task")]})
```

## Production Considerations

- Production URL: `codechef.appsmithery.co` (45.55.173.72)
- All services log to JSON with max 10MB per file, 3 file rotation
- Resource limits: Orchestrator has 2 CPU cores, 2GB RAM limits
- Health checks run every 30s with 60s startup grace period
- Use config-only deployment for environment variable changes (30s vs 10min full rebuild)
- PostgreSQL checkpoints enable workflow resume across deployments

## Documentation

Key documentation in `support/docs/`:

- `architecture-and-platform/ARCHITECTURE.md` - System design
- `getting-started/QUICK_START.md` - Installation and setup
- `operations/LLM_OPERATIONS.md` - ModelOps complete guide
- `reference/MCP_INTEGRATION.md` - MCP tool reference
- `integrations/LINEAR_INTEGRATION.md` - Linear issue tracking
- `integrations/LANGSMITH_TRACING.md` - Observability setup
