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
 agent_*/          # Agent services at repository root
 shared/           # Shared libraries and services
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
agent_orchestrator/        # LangGraph orchestrator with all agent nodes
    main.py                # FastAPI app (port 8001)
    graph.py               # LangGraph workflow definition
    workflows.py           # Workflow state and routing
    agents/                # Agent node implementations
        supervisor.py      # Supervisor routing agent
        feature_dev.py     # Code generation agent node
        code_review.py     # Quality/security agent node
        infrastructure.py  # IaC/deployment agent node
        cicd.py            # Pipeline automation agent node
        documentation.py   # Documentation agent node
    tools/                 # Agent-specific tool definitions
    README.md              # API documentation
    requirements.txt       # Python dependencies
```

**Key Components:**

- **Orchestrator Service:** LangGraph workflow with supervisor routing and agent nodes
- **Supervisor Agent:** Task decomposition, agent routing, workflow coordination (LangGraph node)
- **Feature-Dev Agent:** Code generation, scaffolding, test creation (LangGraph node)
- **Code-Review Agent:** Automated quality, security, and standards enforcement (LangGraph node)
- **Infrastructure Agent:** IaC authoring, deployment automation, drift detection (LangGraph node)
- **CI/CD Agent:** Pipeline synthesis, workflow execution, policy enforcement (LangGraph node)
- **Documentation Agent:** Technical documentation generation and maintenance (LangGraph node)

**Shared Modules (`shared/lib/`):**

- `mcp_client.py` - Legacy MCP HTTP gateway client (deprecated)
- `mcp_discovery.py` - Real-time MCP server discovery via Docker MCP Toolkit
- `mcp_tool_client.py` - Direct MCP tool invocation via stdio transport (replaces HTTP calls)
- `linear_client.py` - Direct Linear API access using Linear SDK
- `gradient_client.py` - DigitalOcean Gradient AI LLM integration
- `guardrail.py` - Shared validation and safety checks

**Configuration:**

- `agents-manifest.json` - Agent profiles with MCP tool allocations
- `config/routing/task-router.rules.yaml` - Task routing rules
- `config/mcp-agent-tool-mapping.yaml` - Tool-to-agent mappings

**Integration Points:**

- **MCP Tools:** Direct stdio invocation via `mcp_tool_client.py` and Docker MCP Toolkit
- **Linear API:** Direct SDK access via `linear_client.py` (OAuth tokens from gateway)
- **RAG Context:** Semantic search via `rag-context:8007`
- **State Persistence:** Workflow state via `state-persistence:8008`
- **LLM Inference:** DigitalOcean Gradient AI via `gradient_client.py`
- **LangGraph:** PostgreSQL checkpointer for workflow state, conditional edges for agent routing

---

### 2. MCP Integration (`/mcp/`)

**Purpose:** Model Context Protocol integration providing 150+ tools from 17 MCP servers via direct stdio transport and Linear OAuth gateway.

#### MCP Servers (17 available via Docker MCP Toolkit)

- context7 (2 tools), dockerhub (13), fetch (1), gitmcp (5), gmail-mcp (3)
- google-maps (8), hugging-face (9), memory (9), next-devtools (5)
- notion (19), perplexity-ask (3), playwright (21), rust-filesystem (24)
- sequentialthinking (1), stripe (22), time (2), youtube_transcript (3)

#### Gateway (`/mcp/gateway/`) - Linear OAuth Only

**Purpose:** Node.js Express service providing Linear OAuth integration and API access.

**Endpoints:**

- `GET /oauth/linear/install` - Initiate Linear OAuth flow
- `GET /oauth/linear/callback` - Handle OAuth callback
- `GET /oauth/linear/status` - Check token status
- `POST /api/linear-issues` - Fetch Linear issues
- `GET /api/linear-project/:projectId` - Get project roadmap
- `GET /health` - Gateway health check

**Note:** MCP tool invocation now happens directly via Python SDK (`shared/lib/mcp_tool_client.py`) using stdio transport, not through HTTP gateway.

---

### 3. Services (`/services/`)

#### RAG Context Manager (`/services/rag/main.py` - port 8007)

- **Vector Search:** Qdrant Cloud integration for semantic code search
- **Collections:** `the-shop` (primary production KB), `documentation`
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

### MCP Tool Access Architecture

**New Pattern (Direct Stdio):**

```
Python Agent  mcp_tool_client.py  Docker MCP Toolkit  stdio  MCP Server Container  Tool Execution
```

**Legacy Pattern (Deprecated):**

```
Agent (FastAPI)  HTTP  MCP Gateway  [NOT IMPLEMENTED]
```

**Implementation:**

Agents now use `shared/lib/mcp_tool_client.py` for direct MCP tool invocation:

```python
from agents._shared.mcp_tool_client import MCPToolClient

# Initialize with server name (e.g., "memory", "rust-filesystem")
mcp_client = MCPToolClient(server_name="memory")

# Invoke tool directly via stdio
result = await mcp_client.invoke_tool_simple(
    tool_name="create_entities",
    arguments={"entities": [{"name": "user123", "entityType": "person"}]}
)
```

**Server Discovery:**

Agents can discover available MCP servers dynamically:

```python
from agents._shared.mcp_discovery import MCPToolkitDiscovery

discovery = MCPToolkitDiscovery()
servers = await discovery.discover_servers()
# Returns: [{"name": "memory", "tools": [...]}, {"name": "rust-filesystem", ...}, ...]
```

### Linear Integration

**OAuth Flow (Node.js Gateway):**

```
User  Browser  gateway-mcp:8000/oauth/linear/install  Linear OAuth  Token Storage
```

**Direct API Access (Python SDK):**

```
Python Agent  linear_client.py  Linear SDK  Linear GraphQL API
```

**Implementation:**

```python
from agents._shared.linear_client import LinearIntegration

linear = LinearIntegration()  # Uses LINEAR_API_KEY from environment

# Fetch issues
issues = await linear.fetch_issues(team_id="TEAM123", limit=50)

# Create issue
issue = await linear.create_issue(
    team_id="TEAM123",
    title="Feature Request",
    description="Add support for..."
)
```

**Tool Allocation:**

- **Orchestrator:** memory, notion, time, sequentialthinking, linear
- **Feature-Dev:** rust-filesystem, gitmcp, playwright, hugging-face, next-devtools
- **Code-Review:** gitmcp, rust-filesystem, hugging-face, playwright
- **Infrastructure:** dockerhub, rust-filesystem, gitmcp, notion
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
   gateway-mcp (8000) - Linear OAuth only
   orchestrator (8001) - Direct MCP + Linear SDK
   6 specialized agents (8002-8006) - Direct MCP + Linear SDK
   rag-context (8007)
   state-persistence (8008)
   qdrant (6333, 6334)
   postgres (5432)
   Docker MCP Toolkit (stdio communication with agents)
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

### Task Execution Flow (Updated)

```
User Request  Orchestrator (/orchestrate)
   Task Router
   Task Decomposition
   State Persistence (create task)
   Agent Selection
   Agent Invocation (HTTP POST)
   MCP Tool Invocation (direct stdio via mcp_tool_client.py)
   Linear API Access (direct SDK via linear_client.py)
   RAG Context Query
   Result Generation
   State Update
   User Response
```

### MCP Tool Invocation Flow

```
Agent Code
   MCPToolClient.invoke_tool_simple()
      subprocess.Popen(['docker', 'mcp', 'run', 'server_name'])
         Docker MCP Toolkit
            MCP Server Container (stdio)
               Tool Execution
            JSON-RPC Response
         Parse Response
      Return Result
   Agent Process Result
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
2. Create `agent_<agent-name>/Dockerfile`
3. Add service to `deploy/docker-compose.yml`
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
