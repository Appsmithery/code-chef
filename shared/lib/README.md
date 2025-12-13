# Shared Library Components

Core utilities and clients for code-chef orchestrator and agents.

**Version**: 2.0  
**Updated**: December 2025

---

## Overview

This directory contains shared infrastructure used across all code-chef agents and services:

- **MCP Integration** - Tool access via Docker MCP Toolkit
- **State Management** - PostgreSQL checkpointing and session handling
- **Linear Integration** - Issue tracking and HITL workflows
- **Observability** - Token tracking, tracing, and metrics
- **Type System** - Shared Pydantic models and enums

---

## MCP Integration

Direct MCP server access via Docker MCP Toolkit.

| File                                                     | Purpose                                                 | Status    |
| -------------------------------------------------------- | ------------------------------------------------------- | --------- |
| [`mcp_tool_client.py`](mcp_tool_client.py)               | **Direct stdio tool invocation**                        | ✅ Active |
| [`mcp_discovery.py`](mcp_discovery.py)                   | **Server/tool enumeration**                             | ✅ Active |
| [`progressive_mcp_loader.py`](progressive_mcp_loader.py) | **Context-optimized tool loading** (10-30 tools vs 178) | ✅ Active |
| [`mcp_client.py`](mcp_client.py)                         | Agent manifest and profile loading                      | ✅ Active |

### Quick Examples

```python
# Discovery
from shared.lib.mcp_discovery import get_mcp_discovery
discovery = get_mcp_discovery()
servers = discovery.discover_servers()  # 178 tools from 15+ servers

# Tool invocation
from shared.lib.mcp_tool_client import get_mcp_tool_client
client = get_mcp_tool_client("feature_dev")
result = await client.invoke_tool_simple(
    server="rust-mcp-filesystem",
    tool="read_file",
    params={"path": "/workspace/main.py"}
)

# Progressive loading (token-efficient)
from shared.lib.progressive_mcp_loader import ProgressiveMCPLoader, ToolLoadingStrategy
loader = ProgressiveMCPLoader(
    mcp_client=client,
    mcp_discovery=discovery,
    default_strategy=ToolLoadingStrategy.PROGRESSIVE
)
tools = await loader.get_tools_for_task("Implement JWT auth", "feature_dev")
# Returns ~15 relevant tools instead of all 178
```

**See**: [`../mcp/README.md`](../mcp/README.md) for full MCP architecture documentation.

---

## State Management

PostgreSQL-backed state persistence with LangGraph checkpointing.

| File                                                   | Purpose                                  |
| ------------------------------------------------------ | ---------------------------------------- |
| [`checkpoint_connection.py`](checkpoint_connection.py) | PostgreSQL checkpointing with async pool |
| [`state_client.py`](state_client.py)                   | State persistence HTTP client            |
| [`session_manager.py`](session_manager.py)             | Agent session lifecycle                  |
| [`workflow_events.py`](workflow_events.py)             | Event sourcing for workflows             |
| [`workflow_reducer.py`](workflow_reducer.py)           | Event reduction to workflow state        |

### Example: Checkpointing

```python
from shared.lib.checkpoint_connection import get_checkpoint_saver

# Get async checkpointer
saver = get_checkpoint_saver()

# Use with LangGraph
from langgraph.graph import StateGraph
graph = StateGraph(WorkflowState)
# ... build graph ...
compiled = graph.compile(checkpointer=saver)

# Resume from checkpoint
config = {"configurable": {"thread_id": "workflow-123"}}
result = await compiled.ainvoke(None, config)
```

---

## Linear Integration

Issue tracking, project management, and human-in-the-loop (HITL) workflows.

| File                                                     | Purpose                              |
| -------------------------------------------------------- | ------------------------------------ |
| [`linear_client.py`](linear_client.py)                   | Linear GraphQL API client            |
| [`linear_project_manager.py`](linear_project_manager.py) | Project CRUD operations              |
| [`hitl_manager.py`](hitl_manager.py)                     | Human-in-the-loop approval workflows |
| [`risk_assessor.py`](risk_assessor.py)                   | Risk scoring for operations          |

### Example: HITL Workflow

```python
from shared.lib.hitl_manager import HITLManager

hitl = HITLManager()

# Assess risk
risk_level = await hitl.assess_risk("delete production database")
# Returns: RiskLevel.CRITICAL

# Request approval (creates Linear issue + webhook)
approval_id = await hitl.request_approval(
    operation="deploy to production",
    context={"service": "orchestrator", "version": "v2.1.0"},
    risk_level=RiskLevel.HIGH
)

# Check approval status (polls Linear API)
status = await hitl.check_approval_status(approval_id)
# Returns: ApprovalStatus.APPROVED | PENDING | REJECTED
```

**Configuration**: [`../../config/hitl/`](../../config/hitl/) contains approval policies and risk rules.

---

## Observability

Token tracking, cost monitoring, and LangSmith tracing integration.

| File                                                 | Purpose                                     |
| ---------------------------------------------------- | ------------------------------------------- |
| [`token_tracker.py`](token_tracker.py)               | LLM token usage and cost tracking           |
| [`longitudinal_tracker.py`](longitudinal_tracker.py) | A/B testing metrics (baseline vs code-chef) |
| [`tracing.py`](tracing.py)                           | LangSmith tracer initialization             |

### Example: Token Tracking

```python
from shared.lib.token_tracker import TokenTracker

tracker = TokenTracker()

# Record LLM call
tracker.track_tokens(
    agent="feature_dev",
    prompt_tokens=850,
    completion_tokens=420,
    model="qwen/qwen-2.5-coder-32b-instruct",
    cost_per_1m=0.07
)

# Get usage summary
summary = tracker.get_usage_summary("feature_dev")
# Returns: {"total_tokens": 1270, "total_cost_usd": 0.00009, "calls": 1}

# Export to Prometheus
metrics = tracker.export_prometheus()
```

### Example: A/B Testing

```python
from shared.lib.longitudinal_tracker import LongitudinalTracker

tracker = LongitudinalTracker()

# Record baseline result
await tracker.record_result(
    agent="feature_dev",
    experiment_group="baseline",
    experiment_id="exp-2025-01-001",
    task_id="task-jwt-auth",
    scores={"accuracy": 0.72, "latency": 2.1},
    metadata={"model": "codellama-13b"}
)

# Record code-chef result
await tracker.record_result(
    agent="feature_dev",
    experiment_group="code-chef",
    experiment_id="exp-2025-01-001",
    task_id="task-jwt-auth",
    scores={"accuracy": 0.89, "latency": 1.6},
    metadata={"model": "codellama-13b-v2-lora"}
)

# Compare results
comparison = await tracker.compare_experiments("exp-2025-01-001")
# Returns: {"accuracy_improvement": 23.6%, "latency_improvement": 23.8%}
```

**See**: [`../../support/docs/operations/LLM_OPERATIONS.md`](../../support/docs/operations/LLM_OPERATIONS.md) for full ModelOps guide.

---

## Type System

Shared Pydantic models and enums for type safety across services.

| File                             | Purpose                                   |
| -------------------------------- | ----------------------------------------- |
| [`core_types.py`](core_types.py) | Core types (InsightType, RiskLevel, etc.) |
| [`validation.py`](validation.py) | Pydantic validators and constraints       |

### Example: InsightType

```python
from shared.lib.core_types import InsightType

# Used across services for consistent categorization
insight = InsightType.CODE_PATTERN  # Enum value
# Available types: CODE_PATTERN, WORKFLOW_EVENT, AGENT_MEMORY,
#                  ISSUE_TRACKER, DOCUMENTATION, LIBRARY_REGISTRY
```

---

## LLM Clients

OpenRouter and Gradient AI integration with retry logic.

| File                                           | Purpose                            |
| ---------------------------------------------- | ---------------------------------- |
| [`openrouter_client.py`](openrouter_client.py) | OpenRouter API client (production) |
| [`gradient_client.py`](gradient_client.py)     | Gradient AI client (fine-tuning)   |

### Example: OpenRouter

```python
from shared.lib.openrouter_client import OpenRouterClient

client = OpenRouterClient(
    model="qwen/qwen-2.5-coder-32b-instruct",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

response = await client.chat_completion(
    messages=[
        {"role": "system", "content": "You are a coding assistant"},
        {"role": "user", "content": "Implement JWT middleware"}
    ],
    temperature=0.3,
    max_tokens=2048
)
```

**Configuration**: Model settings in [`../../config/agents/models.yaml`](../../config/agents/models.yaml).

---

## Utility Functions

Common helpers used across agents.

| File                                   | Purpose                             |
| -------------------------------------- | ----------------------------------- |
| [`config_loader.py`](config_loader.py) | YAML config loading with validation |
| [`logger.py`](logger.py)               | Structured logging setup            |
| [`retry.py`](retry.py)                 | Exponential backoff retry decorator |
| [`env_utils.py`](env_utils.py)         | Environment variable helpers        |

---

## Related Documentation

- [MCP Architecture](../mcp/README.md) - Docker MCP Toolkit integration
- [System Architecture](../../support/docs/architecture-and-platform/ARCHITECTURE.md) - Overall system design
- [LLM Operations](../../support/docs/operations/LLM_OPERATIONS.md) - Model training, evaluation, deployment
- [Agent Configuration](../../config/agents/models.yaml) - Model settings per agent
- [Tool Mapping](../../config/mcp-agent-tool-mapping.yaml) - Agent-specific tool priorities

---

## Testing

```bash
# Run unit tests
pytest support/tests/unit/shared/lib/ -v

# Run integration tests (requires Docker)
pytest support/tests/integration/shared/lib/ -v

# Test MCP tool invocation
pytest support/tests/integration/test_mcp_tool_client.py -v
```

---

**Questions?** File an issue in [Linear](https://linear.app/dev-ops/project/codechef-78b3b839d36b) with label `shared-lib`.
