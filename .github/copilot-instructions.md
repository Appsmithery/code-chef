# GitHub Copilot Instructions for Code-Chef

> **Role**: You are a **development assistant** for the code-chef multi-agent DevOps platform. Complement the LangGraph orchestrator by providing IDE-native tooling, code generation, and direct MCP tool access. The orchestrator (supervisor agent) handles task routing and workflow coordination; you assist with implementation, debugging, and direct tool invocation.

## Relationship to Orchestrator

| Orchestrator (Head Chef)         | Copilot (Sous Chef)               |
| -------------------------------- | --------------------------------- |
| Routes tasks to agent nodes      | Executes code changes directly    |
| Manages LangGraph StateGraph     | Provides IDE-integrated tooling   |
| Coordinates multi-agent handoffs | Handles single-turn requests      |
| Enforces HITL via interrupt()    | Assists with debugging/validation |

**When to defer to orchestrator**: Multi-step workflows, cross-agent coordination, HITL-gated operations.
**When Copilot acts directly**: Code edits, file creation, container inspection, issue lookups, health checks.

---

## Core Architecture Patterns

### LangGraph StateGraph

- **State**: `WorkflowState` TypedDict with `messages`, `current_agent`, `next_agent`, `task_result`, `approvals`, `requires_approval`, `workflow_id`, `thread_id`, `pending_operation`
- **Checkpointing**: PostgresSaver with async pool for interrupt/resume
- **Agent Caching**: `get_agent()` with `_agent_cache` dict prevents redundant instantiation
- **HITL Pattern**: `interrupt({"pending_operation": {...}})` → webhook/poll resume → `graph.invoke(None, config)`

### Workflow Routing (workflow_router.py)

- **Heuristic First** (<10ms): Pattern matching via `task-router.rules.yaml`
- **LLM Fallback**: Semantic routing when heuristics uncertain (confidence < 0.7)
- **Selection Model**: `WorkflowSelection(workflow_id, confidence, method, reasoning, matched_rules, alternatives)`
- **Methods**: `HEURISTIC`, `LLM`, `EXPLICIT`, `DEFAULT`

### Progressive Tool Loading (base_agent.py)

- **Invoke-Time Binding**: Tools bound per request, not at init
- **Strategy Enum**: `MINIMAL` (10-30), `PROGRESSIVE` (30-60), `FULL` (150+)
- **Cache**: `_bound_llm_cache` keyed by tool config hash
- **Loader**: `ProgressiveMCPLoader` with keyword→server mapping

### Observability

- **@traceable Decorators**: 33+ across graph.py, workflow_engine.py, base_agent.py, ModelOps modules
- **LangSmith Projects** (Purpose-Based, Effective Dec 10, 2025):
  - `code-chef-production` - Live extension usage (`environment:"production"`)
  - `code-chef-experiments` - A/B testing (`experiment_id IS NOT NULL`)
  - `code-chef-training` - Model training ops (`module:"training"`)
  - `code-chef-evaluation` - Model evaluations (`module:"evaluation"`)
- **Trace Metadata Schema**: `config/observability/tracing-schema.yaml`
  - `experiment_group`: code-chef | baseline (A/B testing)
  - `environment`: production | training | evaluation | test
  - `module`: training | evaluation | deployment | registry | coordinator | {agent}
  - `extension_version`: Semver (e.g., "1.2.3")
  - `model_version`: Model identifier (e.g., "codellama-13b-v2")
  - `experiment_id`: Correlate A/B runs (e.g., "exp-2025-01-001")
  - `task_id`: Correlate tasks across groups
  - `config_hash`: Config fingerprint
- **Prometheus**: `/metrics` endpoint via `Instrumentator`
- **Grafana**: `appsmithery.grafana.net`

**Note**: Old per-agent projects (code-chef-feature-dev, etc.) deprecated Dec 10, 2025. See `support/docs/procedures/langsmith-project-restructure.md` for migration details.

---

## Production Rules (Non-negotiable)

- Every change requires a Linear issue → use `mcp_linear_*` or `activate_issue_management_tools`
- Validate container health after deploys → use `activate_container_inspection_and_logging_tools`
- Never skip cleanup after failures → run `docker compose down --remove-orphans`
- Treat Docker resources as disposable; leave stacks fully running or fully stopped
- High-risk ops trigger HITL approval via interrupt() + Linear webhook

## Linear Issue Standards

When creating or updating Linear issues:

- **Use GitHub permalinks** for all file references (not relative paths)
- Format: `https://github.com/Appsmithery/Dev-Tools/blob/<commit-sha>/<path>`
- Get commit SHA via: `git log -1 --format="%H" -- "<file-path>"`
- For stable references, use `main` branch: `https://github.com/Appsmithery/Dev-Tools/blob/main/<path>`
- Always link plan documents, specs, and implementation files in issue descriptions

## Agent Node Reference

Route tasks by **function**, not technology. Models in `config/agents/models.yaml`:

| Intent                  | Agent Node       | Model         | Provider |
| ----------------------- | ---------------- | ------------- | -------- |
| Code implementation     | `feature_dev`    | codellama-13b | gradient |
| Security/quality review | `code_review`    | llama3.3-70b  | gradient |
| IaC, Terraform, Compose | `infrastructure` | llama3-8b     | gradient |
| Pipelines, Actions, CI  | `cicd`           | llama3.3-70b  | gradient |
| Docs, specs, READMEs    | `documentation`  | llama3.3-70b  | gradient |
| Orchestration, routing  | `supervisor`     | llama3.3-70b  | gradient |

## MCP Tool Strategy

Use **progressive disclosure** for token efficiency:

| Strategy        | When to Use                      | Tool Count  |
| --------------- | -------------------------------- | ----------- |
| **MINIMAL**     | Simple tasks, keyword-matched    | 10-30 tools |
| **PROGRESSIVE** | Multi-step, agent-priority tools | 30-60 tools |
| **FULL**        | Debugging tool discovery issues  | 150+ tools  |

**Key tool activators:**

- `activate_container_*` → Docker management
- `mcp_linear_*` → Issue tracking (mandatory for production)
- `activate_python_*` → Pylance, validation, imports
- `mcp_docs_by_langc_*` → LangChain documentation

## Services & Health

| Service        | Port | Health Endpoint |
| -------------- | ---- | --------------- |
| orchestrator   | 8001 | `/health`       |
| rag-context    | 8007 | `/health`       |
| state-persist  | 8008 | `/health`       |
| agent-registry | 8009 | `/health`       |
| langgraph      | 8010 | `/health`       |

**Production**: `codechef.appsmithery.co` → `45.55.173.72`

## Repository Structure

```
code-chef/
├── agent_orchestrator/
│   ├── agents/{supervisor,feature_dev,code_review,infrastructure,cicd,documentation}/
│   │   └── _shared/base_agent.py  # BaseAgent with invoke-time tool binding
│   ├── workflows/
│   │   ├── workflow_engine.py     # Event-sourced workflow execution
│   │   ├── workflow_router.py     # Heuristic + LLM routing
│   │   └── templates/*.yaml       # Declarative workflow definitions
│   ├── graph.py                   # LangGraph StateGraph + PostgresSaver
│   └── main.py                    # FastAPI + webhooks + /resume endpoint
├── shared/lib/
│   ├── hitl_manager.py            # HITLManager with Linear webhooks
│   ├── progressive_mcp_loader.py  # Token-efficient tool loading
│   ├── mcp_client.py, gradient_client.py
│   └── workflow_reducer.py        # Event sourcing reducer
├── config/
│   ├── agents/models.yaml         # Model configs (single source of truth)
│   ├── routing/task-router.rules.yaml
│   └── hitl/, linear/, rag/
├── deploy/docker-compose.yml
└── support/docs/                  # DEPLOYMENT.md, ARCHITECTURE.md
```

## Adding a New Agent Node

1. Create `agent_orchestrator/agents/<name>/` with `__init__.py`, `system.prompt.md`, `tools.yaml`
2. Inherit from `_shared.base_agent.BaseAgent` (invoke-time tool binding inherited)
3. Wire into `graph.py` StateGraph + conditional edges + add to `get_agent()` cache
4. Update `config/mcp-agent-tool-mapping.yaml`
5. Add `@traceable` decorators for LangSmith visibility

## HITL Approval Flow

```
Task → RiskAssessor → HIGH/CRITICAL?
  ├─ NO  → Execute directly
  └─ YES → interrupt({"pending_operation": {...}})
           → Create Linear issue with approval request
           → Webhook callback OR 30s polling fallback
           → graph.invoke(None, config) to resume
```

## Key References

| Topic                 | Location                                                             |
| --------------------- | -------------------------------------------------------------------- |
| Deployment procedures | `support/docs/DEPLOYMENT.md`                                         |
| Architecture overview | `support/docs/ARCHITECTURE.md`                                       |
| Workflow templates    | `agent_orchestrator/workflows/templates/*.yaml`                      |
| Linear API scripts    | `support/scripts/linear/agent-linear-update.py`                      |
| RAG indexing          | `support/scripts/rag/index_*.py`                                     |
| Observability         | LangSmith: `smith.langchain.com`, Grafana: `appsmithery.grafana.net` |

## ModelOps Extension

> **📘 Complete Documentation**: See [LLM Operations Guide](../support/docs/operations/llm-operations.md) for comprehensive procedures covering model selection, training, evaluation, deployment, A/B testing, cost management, and troubleshooting.

The Infrastructure agent supports full model training, evaluation, and deployment lifecycle:

**Training**: HuggingFace Space API (`alextorelli/code-chef-modelops-trainer`)

- Demo mode: $0.50, 5 minutes (100 examples)
- Production mode: $3.50-$15, 90 minutes (full dataset)
- AutoTrain handles GPU selection, LoRA config, monitoring

**Evaluation**: LangSmith-based comparison using existing evaluators

- Weighted scoring: 30% accuracy, 25% completeness, 20% efficiency, 15% latency, 10% integration
- Automatic recommendations: deploy, needs_review, reject

**Deployment**: Immediate deployment (100%) with rollback support

- Updates `config/agents/models.yaml` automatically
- Creates backups before changes, rollback in <60 seconds

**Registry**: Version tracking in `config/models/registry.json` with Pydantic validation

**VS Code Integration**: 5 commands in `codechef.modelops.*` namespace

- Training wizard with cost estimation and live progress monitoring
- Evaluation results visualization with recommendations
- Model version history and GGUF conversion

**Key Files**:

- `agent_orchestrator/agents/infrastructure/modelops/coordinator.py` - Main orchestration
- `agent_orchestrator/agents/infrastructure/modelops/training.py` - AutoTrain integration
- `agent_orchestrator/agents/infrastructure/modelops/evaluation.py` - LangSmith comparison
- `agent_orchestrator/agents/infrastructure/modelops/deployment.py` - Config management
- `extensions/vscode-codechef/src/commands/modelops.ts` - VS Code commands

## Quality Bar

- Use Pydantic models and type hints on all functions
- Add `@traceable` decorator for any new LangGraph node or workflow step
- Health endpoints must return `{"status": "healthy", ...}`
- Graceful fallback when API keys missing
- **DO NOT create summary markdown files** unless explicitly requested
- Update existing docs in `support/docs/` when architecture changes
- When user says "update linear roadmap" → update Linear via API, not markdown files
