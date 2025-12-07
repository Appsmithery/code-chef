# Dev-Tools Architecture

**Version:** v0.5  
**Status:** Production  
**Last Updated:** December 7, 2025  
**Product:** code/chef (https://theshop.appsmithery.co)

See [QUICKSTART.md](QUICKSTART.md) for setup | [DEPLOYMENT.md](DEPLOYMENT.md) for deployment

---

## Overview

Dev-Tools is a **LangGraph-powered AI agent orchestration platform** with 6 specialized agent nodes, 150+ MCP tools via Docker MCP Toolkit, and RAG-based context management.

### Core Architecture

```
Orchestrator (8001) - Single FastAPI service
 ├─ LangGraph StateGraph Workflow
 │   ├─ Supervisor Node (llama-3.3-70b)
 │   ├─ Feature-Dev Node (codellama-13b)
 │   ├─ Code-Review Node (llama-3.3-70b)
 │   ├─ Infrastructure Node (llama-3.1-8b)
 │   ├─ CI/CD Node (llama-3.1-8b)
 │   └─ Documentation Node (mistral-7b)
 ├─ Linear Integration (GraphQL via LinearWorkspaceClient)
 └─ HITL Webhook Handler (/webhooks/linear)
```

**Key Point:** All 6 agents are **nodes** within one LangGraph workflow, not separate microservices.

---

## Services

| Service      | Port | Purpose                                    |
| ------------ | ---- | ------------------------------------------ |
| orchestrator | 8001 | LangGraph workflow + 6 agents + Linear API |
| rag-context  | 8007 | Vector search (Qdrant Cloud)               |
| state        | 8008 | Workflow persistence (PostgreSQL)          |
| langgraph    | 8010 | LangGraph checkpointing service            |
| postgres     | 5432 | Checkpointing + HITL approvals             |

**Note:** MCP tools are accessed via Docker MCP Toolkit (local gateway), not a Docker service.

---

## Agent Nodes

### Supervisor (LangGraph Routing Node)

- **Purpose:** Task decomposition and agent routing
- **Model:** llama-3.3-70b-instruct
- **Tools:** sequential-thinking, time

### Feature-Dev (Code Generation Node)

- **Purpose:** Code generation, scaffolding, test creation
- **Model:** codellama-13b-instruct
- **Tools:** rust-mcp-filesystem, github-official, playwright, hugging-face

### Code-Review (Quality Analysis Node)

- **Purpose:** Security analysis, quality checks, standards
- **Model:** llama-3.3-70b-instruct
- **Tools:** github-official, rust-mcp-filesystem, hugging-face

### Infrastructure (IaC Node)

- **Purpose:** IaC authoring, deployment automation
- **Model:** llama-3.1-8b-instruct
- **Tools:** dockerhub, rust-mcp-filesystem, github-official

### CI/CD (Pipeline Node)

- **Purpose:** Pipeline generation, workflow execution
- **Model:** llama-3.1-8b-instruct
- **Tools:** github-official, dockerhub, playwright

### Documentation (Docs Node)

- **Purpose:** Technical documentation, API docs
- **Model:** mistral-7b-instruct
- **Tools:** rust-mcp-filesystem, github-official, notion, hugging-face

---

## MCP Integration

### Docker MCP Toolkit (20 servers, 178+ tools)

MCP tools are managed via **Docker MCP Toolkit** in Docker Desktop. The orchestrator accesses tools via the local MCP gateway (not a Docker service).

```bash
# List configured servers
docker mcp server list

# View server tools
docker mcp catalog
```

### Progressive Tool Disclosure (80-90% Token Savings)

```python
from shared.lib.progressive_mcp_loader import ToolLoadingStrategy

# Filter 178+ tools → 10-30 relevant tools
relevant_tools = progressive_loader.get_tools_for_task(
    task_description="Review auth code for vulnerabilities",
    strategy=ToolLoadingStrategy.PROGRESSIVE
)

# Convert to LangChain BaseTool instances
langchain_tools = mcp_client.to_langchain_tools(relevant_tools)

# Bind to LLM for function calling
llm_with_tools = gradient_client.get_llm_with_tools(tools=langchain_tools)
```

### Available Tool Servers

| Server           | Tools | Key Capabilities               |
| ---------------- | ----- | ------------------------------ |
| github-official  | 40    | Full GitHub API with OAuth     |
| rust-filesystem  | 24    | File I/O, directory navigation |
| playwright       | 21    | Browser automation, testing    |
| stripe           | 22    | Payment operations, testing    |
| notion           | 19    | Documentation management       |
| dockerhub        | 13    | Container operations           |
| sequential-think | 6     | Step-by-step reasoning         |
| hugging-face     | 9     | ML model analysis              |
| context7         | 3     | Library documentation lookup   |
| grafana          | 4     | Dashboard/metrics queries      |
| prometheus       | 3     | Metrics queries                |
| gmail-mcp        | 5     | Email operations               |
| google-maps      | 8     | Location services              |
| youtube-trans    | 2     | Video transcript extraction    |

See `config/mcp-agent-tool-mapping.yaml` for complete agent-to-tool mapping.

---

## LangGraph Workflow

### StateGraph Definition

```python
workflow = StateGraph(WorkflowState)

# Add agent nodes
workflow.add_node("supervisor", supervisor_agent)
workflow.add_node("feature_dev", feature_dev_agent)
workflow.add_node("code_review", code_review_agent)
# ... other agent nodes

# Supervisor routes to specialized agents
workflow.add_conditional_edges("supervisor", route_to_agent, {
    "feature_dev": "feature_dev",
    "code_review": "code_review",
    "end": END
})

# Compile with PostgreSQL checkpointer
compiled = workflow.compile(checkpointer=PostgresSaver(conn))
```

### Workflow State

```python
class WorkflowState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    current_agent: str
    next_agent: str
    task_result: Dict[str, Any]
    approvals: List[str]
    requires_approval: bool
    workflow_id: Optional[str]
    thread_id: Optional[str]
    pending_operation: Optional[Dict[str, Any]]
    captured_insights: List[Dict[str, Any]]  # Cross-agent memory (CHEF-206)
    memory_context: Optional[str]  # Retrieved context on resume (CHEF-207)
```

### Cross-Agent Memory Integration

Agents share knowledge via `AgentMemoryManager` → RAG service → Qdrant Cloud:

```python
# Insights captured during agent execution
from shared.lib.agent_memory import AgentMemoryManager

memory = AgentMemoryManager(rag_base_url="http://rag-context:8007")
await memory.store_insight(
    agent_id="feature-dev",
    insight_type=InsightType.CODE_PATTERN,
    content="Use async context managers for DB connections",
    confidence=0.9
)

# Retrieved on workflow resume via /resume endpoint
# Last 10 insights injected as memory_context
```

### HITL Approval Flow

```
1. Agent Node  Risk Assessment (high-risk operation detected)
2. Create Approval Request  PostgreSQL
3. LangGraph Interrupt  approval_gate node
4. Linear Sub-Issue Created  DEV-68
5. User Approves in Linear
6. Webhook  Update PostgreSQL
7. Workflow Resumes from Checkpoint
```

---

## Data Flow

### Task Submission Execution

```
POST /orchestrate

LangGraph Workflow Starts

Supervisor Decomposes Task

Routes to Agent Node (conditional_edges)

Agent Node Executes:
  - Progressive Tool Loading (filter 150  10-30 tools)
  - LangChain Tool Binding (MCP  BaseTool)
  - LLM Function Calling (Gradient AI)
  - Tool Execution (MCP stdio)
  - State Update (PostgreSQL checkpoint)

Return to Supervisor or END
```

---

## Configuration

### Agent Models (`config/agents/models.yaml`)

```yaml
orchestrator:
  model: llama3.3-70b-instruct
  temperature: 0.7
  max_tokens: 4000
  cost_per_1m_tokens: 0.60

feature_dev:
  model: codellama-13b-instruct
  temperature: 0.5
  max_tokens: 3000
  cost_per_1m_tokens: 0.30
```

**Hot-reload:** Edit YAML Restart orchestrator (no rebuild required)

### Environment Variables (`config/env/.env`)

```bash
# LangSmith Tracing
LANGSMITH_API_KEY=lsv2_sk_***
LANGSMITH_WORKSPACE_ID=<org-id>

# DigitalOcean Gradient AI
GRADIENT_API_KEY=<do-pat>

# Linear Integration
LINEAR_API_KEY=lin_oauth_***
LINEAR_TEAM_ID=<team-uuid>
```

---

## Observability

### LangSmith (LLM Tracing)

- **Dashboard:** https://smith.langchain.com
- **Auto-Trace:** All LLM calls, tool invocations, agent reasoning
- **Metrics:** Token usage, latency, success rate per agent node

### Grafana Cloud (Prometheus)

- **Dashboard:** https://appsmithery.grafana.net
- **Metrics:** HTTP requests, response times, error rates
- **Scrape:** orchestrator:8001, state:8008, langgraph:8010

### PostgreSQL (Audit Trail)

- **Workflow Checkpoints:** LangGraph state snapshots
- **HITL Approvals:** Decision history with timestamps
- **Task Registry:** Orchestrator task lifecycle

---

## Performance

- **LLM Cost:** $0.20-0.60/1M tokens (150x cheaper than GPT-4)
- **LLM Latency:** <50ms (DigitalOcean network)
- **Token Savings:** 80-90% via progressive tool disclosure
- **Workflow Resume:** <1s from PostgreSQL checkpoint

---

## Security

### Secrets Management

- **Environment:** API keys in `.env` (gitignored)
- **Docker Secrets:** Sensitive config as mounted files (optional)
- **Validation:** `support/scripts/automation/validate-secrets.ts`

### HITL Approval

- **Risk Levels:** Low (auto-approve) Critical (manual approve)
- **Linear Integration:** Approval requests as sub-issues in DEV-68
- **Audit:** All approvals logged in PostgreSQL

---

## Related Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Setup and first workflow
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment
- **[MCP_INTEGRATION.md](architecture/MCP_INTEGRATION.md)** - Complete tool catalog
- **[LANGGRAPH_INTEGRATION.md](architecture/LANGGRAPH_INTEGRATION.md)** - Workflow patterns
- **[OBSERVABILITY.md](OBSERVABILITY.md)** - Monitoring setup
