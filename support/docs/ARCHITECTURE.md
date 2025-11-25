# Dev-Tools Architecture

**Version:** v0.3  
**Status:**  Production  
**Last Updated:** November 25, 2025

See [QUICKSTART.md](QUICKSTART.md) for setup | [DEPLOYMENT.md](DEPLOYMENT.md) for deployment

---

## Overview

Dev-Tools is a **LangGraph-powered AI agent orchestration platform** with 6 specialized agent nodes, 150+ MCP tools, and RAG-based context management.

### Core Architecture

```
Orchestrator (8001) - Single FastAPI service
 LangGraph StateGraph Workflow
     Supervisor Node (llama-3.1-70b)
     Feature-Dev Node (codellama-13b)
     Code-Review Node (llama-3.1-70b)
     Infrastructure Node (llama-3.1-8b)
     CI/CD Node (llama-3.1-8b)
     Documentation Node (mistral-7b)
```

**Key Point:** All 6 agents are **nodes** within one LangGraph workflow, not separate microservices.

---

## Services

| Service      | Port | Purpose                          |
|--------------|------|----------------------------------|
| orchestrator | 8001 | LangGraph workflow + 6 agents    |
| gateway-mcp  | 8000 | Linear OAuth + MCP coordination  |
| rag-context  | 8007 | Vector search (Qdrant)           |
| state        | 8008 | Workflow persistence (Postgres)  |
| postgres     | 5432 | Checkpointing + HITL approvals   |

---

## Agent Nodes

### Supervisor (LangGraph Routing Node)

- **Purpose:** Task decomposition and agent routing
- **Model:** llama-3.1-70b-instruct
- **Tools:** memory, sequential-thinking, time

### Feature-Dev (Code Generation Node)

- **Purpose:** Code generation, scaffolding, test creation
- **Model:** codellama-13b-instruct
- **Tools:** rust-mcp-filesystem, gitmcp, playwright, hugging-face

### Code-Review (Quality Analysis Node)

- **Purpose:** Security analysis, quality checks, standards
- **Model:** llama-3.1-70b-instruct
- **Tools:** gitmcp, rust-mcp-filesystem, hugging-face

### Infrastructure (IaC Node)

- **Purpose:** IaC authoring, deployment automation
- **Model:** llama-3.1-8b-instruct
- **Tools:** dockerhub, rust-mcp-filesystem, gitmcp

### CI/CD (Pipeline Node)

- **Purpose:** Pipeline generation, workflow execution
- **Model:** llama-3.1-8b-instruct
- **Tools:** gitmcp, dockerhub, playwright

### Documentation (Docs Node)

- **Purpose:** Technical documentation, API docs
- **Model:** mistral-7b-instruct
- **Tools:** rust-mcp-filesystem, gitmcp, notion, hugging-face

---

## MCP Integration

### Progressive Tool Disclosure (80-90% Token Savings)

```python
from shared.lib.progressive_mcp_loader import ToolLoadingStrategy

# Filter 150+ tools  10-30 relevant tools
relevant_tools = progressive_loader.get_tools_for_task(
    task_description="Review auth code for vulnerabilities",
    strategy=ToolLoadingStrategy.PROGRESSIVE
)

# Convert to LangChain BaseTool instances
langchain_tools = mcp_client.to_langchain_tools(relevant_tools)

# Bind to LLM for function calling
llm_with_tools = gradient_client.get_llm_with_tools(tools=langchain_tools)
```

### Available Tool Servers (17 servers, 150+ tools)

| Server           | Tools | Key Capabilities            |
|------------------|-------|-----------------------------|
| rust-filesystem  | 24    | File I/O, directory nav     |
| playwright       | 21    | Browser automation          |
| stripe           | 22    | Payment testing             |
| notion           | 19    | Documentation mgmt          |
| dockerhub        | 13    | Container operations        |
| memory           | 9     | Knowledge graph             |
| hugging-face     | 9     | Code analysis               |
| gitmcp           | 5     | Git operations              |

See `config/mcp-agent-tool-mapping.yaml` for complete catalog.

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
    task: str
    context: dict
    agent_outputs: dict[str, Any]
    approval_request_id: str | None
    current_agent: str
    next_action: str
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

### Task Submission  Execution

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

**Hot-reload:** Edit YAML  Restart orchestrator (no rebuild required)

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
- **Scrape:** orchestrator:8001, gateway:8000, state:8008

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

- **Docker Secrets:** Linear OAuth, GitHub PAT as mounted files
- **Environment:** API keys in `.env` (gitignored)
- **Validation:** `support/scripts/automation/validate-secrets.ts`

### HITL Approval

- **Risk Levels:** Low (auto-approve)  Critical (manual approve)
- **Linear Integration:** Approval requests as sub-issues in DEV-68
- **Audit:** All approvals logged in PostgreSQL

---

## Related Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Setup and first workflow
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment
- **[MCP_INTEGRATION.md](architecture/MCP_INTEGRATION.md)** - Complete tool catalog
- **[LANGGRAPH_INTEGRATION.md](architecture/LANGGRAPH_INTEGRATION.md)** - Workflow patterns
- **[OBSERVABILITY.md](OBSERVABILITY.md)** - Monitoring setup
