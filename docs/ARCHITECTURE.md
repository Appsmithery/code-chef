# Dev-Tools Architecture

**Version:** 2.0.0
**Last Updated:** 2025-11-13
**Status:** Production (MCP-Integrated)

---

## Overview

Dev-Tools is a **containerized AI agent orchestration platform** providing specialized development automation via FastAPI agents, MCP tool integration, and vector-based context management. The system operates as a distributed microservices architecture with MECE-aligned agent responsibilities.

### Key Principles

1. **Agent Specialization** - Each agent handles a distinct domain (feature-dev, code-review, infrastructure, ci/cd, documentation)
2. **MCP Tool Integration** - Central gateway provides 150+ tools across 17 servers for agent capabilities
3. **Configuration-Driven** - Behavior controlled via YAML routing rules and tool mappings
4. **Stateful Workflows** - PostgreSQL + Qdrant provide persistent state and RAG context
5. **Container-First** - Docker Compose orchestration with health checks and volume persistence

---

## Repository Structure

### High-Level Layout

```
Dev-Tools/
 agents/           # FastAPI agent implementations (orchestrator, feature-dev, code-review, etc.)
 compose/          # Docker Compose orchestration
 config/           # Configuration files (routing rules, MCP mappings, RAG config, secrets)
 containers/       # Dockerfiles for each service
 context/          # Temporary context files and repo metadata
 docs/             # Documentation
 frontend/         # Web UI for MCP servers and agent monitoring
 mcp/              # MCP Gateway and server implementations
    gateway/      # Central MCP HTTP gateway (Node.js/Express)
    servers/      # MCP server implementations (17+ servers)
 pipelines/        # CI/CD pipeline templates
 reports/          # Generated reports and validation results
 scripts/          # Automation scripts (setup, backup, deployment)
 services/         # Supporting services (RAG, state persistence)
 templates/        # Reusable templates (docs, infrastructure, pipelines)
```

---

## Component Breakdown

### 1. Agents (`/agents/`)

**Purpose:** FastAPI-based agent implementations with specialized development capabilities.

```
agents/
 agents-manifest.json       # Agent registry with tool allocations
 orchestrator/              # Task routing and coordination
    main.py                # FastAPI app (port 8001)
    README.md              # API documentation
    requirements.txt       # Python dependencies
    Taskfile.yml           # Agent-specific workflows
 feature-dev/               # Code generation and implementation
    main.py                # FastAPI app (port 8002)
    ...
 code-review/               # Quality, security, standards enforcement
    main.py                # FastAPI app (port 8003)
    ...
 infrastructure/            # IaC authoring and deployment
    main.py                # FastAPI app (port 8004)
    ...
 cicd/                      # Pipeline generation and automation
    main.py                # FastAPI app (port 8005)
    ...
 documentation/             # Documentation synthesis
     main.py                # FastAPI app (port 8006)
     ...
```

**Key Components:**

- **Orchestrator Agent:** Task decomposition, agent routing, workflow coordination
- **Feature-Dev Agent:** Code generation, scaffolding, test creation
- **Code-Review Agent:** Automated quality, security, and standards enforcement
- **Infrastructure Agent:** IaC authoring, deployment automation, drift detection
- **CI/CD Agent:** Pipeline synthesis, workflow execution, policy enforcement
- **Documentation Agent:** Technical documentation generation and maintenance

**Configuration:**

- `agents-manifest.json` - Agent profiles with MCP tool allocations
- `config/routing/task-router.rules.yaml` - Task routing rules
- `config/mcp-agent-tool-mapping.yaml` - Tool-to-agent mappings

**Integration Points:**

- MCP Gateway (`gateway-mcp:8000`) for tool invocation
- RAG Context Manager (`rag-context:8007`) for semantic search
- State Persistence (`state-persistence:8008`) for workflow state

---

### 2. MCP Gateway (`/mcp/gateway/`)

**Purpose:** Central Model Context Protocol gateway exposing 150+ tools from 17 MCP servers.

**Available Servers (17):**

- context7 (2 tools), dockerhub (13), fetch (1), gitmcp (5), gmail-mcp (3)
- google-maps (8), hugging-face (9), memory (9), next-devtools (5)
- notion (19), perplexity-ask (3), playwright (21), rust-filesystem (24)
- sequentialthinking (1), stripe (22), time (2), youtube_transcript (3)

**Endpoints:**

- `GET /tools` - List all available tools
- `POST /tools/{server}/{tool}` - Invoke specific tool
- `GET /servers` - List server status
- `GET /health` - Gateway health check

---

### 3. Services (`/services/`)

#### RAG Context Manager (`/services/rag/main.py` - port 8007)

- **Vector Search:** Qdrant integration for semantic code search
- **Collections:** `code-knowledge`, `documentation`, `workflows`
- **Endpoints:** `/query`, `/index`, `/collections`

#### State Persistence (`/services/state/main.py` - port 8008)

- **Task Registry:** Track orchestrator task states
- **PostgreSQL Integration:** Tables for tasks, workflows, agent_state
- **Endpoints:** `/tasks`, `/workflows`

---

### 4. Configuration (`/config/`)

**Key Files:**

- **mcp-agent-tool-mapping.yaml:** 150 MCP tools mapped to 6 agents with rationale, priority, use cases
- **routing/task-router.rules.yaml:** Pattern-based routing rules
- **rag/vectordb.config.yaml:** Qdrant connection and collection definitions
- **rag/indexing.yaml:** RAG indexing strategy

---

### 5. Docker Compose (`/compose/`)

**Services:**

1. **gateway-mcp** (8000) - MCP HTTP Gateway
2. **orchestrator** (8001) - Task coordination
3. **feature-dev** (8002) - Code generation
4. **code-review** (8003) - Quality enforcement
5. **infrastructure** (8004) - IaC management
6. **cicd** (8005) - Pipeline automation
7. **documentation** (8006) - Documentation generation
8. **rag-context** (8007) - Vector search
9. **state-persistence** (8008) - Workflow state
10. **qdrant** (6333, 6334) - Vector database
11. **postgres** (5432) - Relational database

**Volumes:** `orchestrator-data`, `mcp-config`, `qdrant-data`, `postgres-data`

---

### 6. Scripts (`/scripts/`)

**Lifecycle:** `up.sh`, `down.sh`, `rebuild.sh`
**Backup:** `backup_volumes.sh`, `restore_volumes.sh`
**Setup:** `setup_secrets.sh`
**Utilities:** CORS configuration, UI generation, validation

---

## Integration Points

### Agent MCP Gateway

```
Agent (FastAPI)  HTTP  MCP Gateway  stdio  MCP Server  Tool Execution
```

**Tool Allocation:**

- **Orchestrator:** memory, notion, time, sequentialthinking, prometheus
- **Feature-Dev:** rust-filesystem, gitmcp, playwright, hugging-face, next-devtools
- **Code-Review:** gitmcp, rust-filesystem, hugging-face, playwright
- **Infrastructure:** dockerhub, rust-filesystem, gitmcp, notion, prometheus
- **CI/CD:** gitmcp, rust-filesystem, dockerhub, playwright, notion
- **Documentation:** rust-filesystem, gitmcp, notion, hugging-face, playwright

### Orchestrator Agent Routing

**Configuration:** `config/routing/task-router.rules.yaml`

**Rules:**

- `feature|implement|build|create` feature-dev
- `review|lint|check|quality` code-review
- `deploy|infrastructure|terraform|docker` infrastructure
- `pipeline|ci|cd|workflow` cicd
- `document|readme|api-docs` documentation
- `.*` (fallback) orchestrator

---

## Deployment Architecture

### Production Stack (DigitalOcean)

**Production URL:** https://theshop.appsmithery.co
**Server:** 45.55.173.72

```
Internet  Caddy (443)  Docker Compose Stack
   gateway-mcp (8000)
   orchestrator (8001)
   6 specialized agents (8002-8006)
   rag-context (8007)
   state-persistence (8008)
   qdrant (6333, 6334)
   postgres (5432)
```

### Local Development

```bash
# Start entire stack
./scripts/up.sh

# Access agents
http://localhost:8001/health  # Orchestrator
http://localhost:8002/health  # Feature-Dev
# ... etc

# Access MCP Gateway
http://localhost:8000/tools

# Access RAG
http://localhost:8007/query
```

---

## Data Flow

### Task Execution Flow

```
User Request  Orchestrator (/orchestrate)
   Task Router
   Task Decomposition
   State Persistence (create task)
   Agent Selection
   Agent Invocation (HTTP POST)
   MCP Tool Invocation
   RAG Context Query
   Result Generation
   State Update
   User Response
```

---

## Configuration System

### Configuration Hierarchy

1. **Environment Variables** (.env, Docker Compose) - Highest priority
2. **YAML Files** (config/) - MCP mappings, routing, RAG
3. **Secret Files** (config/env/secrets/) - OAuth tokens, API keys
4. **Agent Config** (agents/\*/) - requirements.txt, Taskfile.yml

---

## Security

- **Secrets:** Never commit; use `*_FILE` env vars and Docker secrets
- **Network:** Internal `devtools-network` isolates services
- **Database:** PostgreSQL/Qdrant only accessible within Docker network
- **TLS:** Caddy reverse proxy with automatic HTTPS in production

---

## Extension Points

### Adding New Agents

1. Create `agents/<agent-name>/main.py` (FastAPI)
2. Create `containers/<agent-name>/Dockerfile`
3. Add service to `compose/docker-compose.yml`
4. Update `config/routing/task-router.rules.yaml`
5. Map MCP tools in `config/mcp-agent-tool-mapping.yaml`
6. Document in `docs/AGENT_ENDPOINTS.md`

### Adding New MCP Servers

1. Install via Docker MCP toolkit
2. Verify with `docker mcp gateway run`
3. Update `config/mcp-agent-tool-mapping.yaml`
4. Assign tools to agent profiles
5. Document capabilities

---

## Performance Targets

- **Orchestrator routing:** < 2 seconds
- **Code generation:** < 30 seconds
- **Code review:** < 10 seconds
- **MCP tool invocation:** < 100ms overhead
- **Vector search:** < 500ms
- **State persistence:** < 50ms

---

## Additional Resources

- **[AGENT_ENDPOINTS.md](AGENT_ENDPOINTS.md)** - Complete API reference
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Deployment procedures
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Getting started
- **[SECRETS_MANAGEMENT.md](SECRETS_MANAGEMENT.md)** - Secret handling
- **[HANDBOOK.md](HANDBOOK.md)** - Operational procedures
- **[chatmodes/](chatmodes/)** - Agent-specific documentation

---

**Maintained by:** Dev-Tools Team
**Production:** https://theshop.appsmithery.co
**Repository:** https://github.com/Appsmithery/Dev-Tools
