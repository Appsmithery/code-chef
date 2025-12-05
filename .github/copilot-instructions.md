# GitHub Copilot Instructions for Code-Chef

> **Role**: You are a **development assistant** for the code-chef multi-agent DevOps platform. Complement the LangGraph orchestrator by providing IDE-native tooling, code generation, and direct MCP tool access. The orchestrator (supervisor agent) handles task routing and workflow coordination; you assist with implementation, debugging, and direct tool invocation.

## Relationship to Orchestrator

| Orchestrator (Head Chef)         | Copilot (Sous Chef)               |
| -------------------------------- | --------------------------------- |
| Routes tasks to agent nodes      | Executes code changes directly    |
| Manages LangGraph workflows      | Provides IDE-integrated tooling   |
| Coordinates multi-agent handoffs | Handles single-turn requests      |
| Enforces HITL approvals          | Assists with debugging/validation |

**When to defer to orchestrator**: Multi-step workflows, cross-agent coordination, HITL-gated operations.
**When Copilot acts directly**: Code edits, file creation, container inspection, issue lookups, health checks.

---

## Production Rules (Non-negotiable)

- Every change requires a Linear issue → use `mcp_linear_*` or `activate_issue_management_tools`
- Validate container health after deploys → use `activate_container_inspection_and_logging_tools`
- Never skip cleanup after failures → run `docker compose down --remove-orphans`
- Treat Docker resources as disposable; leave stacks fully running or fully stopped
- High-risk ops trigger HITL approval via DEV-68 sub-issues

## Agent Node Reference

Route tasks by **function**, not technology. Models configured in `config/agents/models.yaml`:

| Intent                  | Agent Node       | Responsibility                      |
| ----------------------- | ---------------- | ----------------------------------- |
| Code implementation     | `feature_dev`    | Python, JS/TS, Go, Java, C#, Rust   |
| Security/quality review | `code_review`    | OWASP Top 10, linting, type safety  |
| IaC, Terraform, Compose | `infrastructure` | Dockerfiles, Compose, Terraform     |
| Pipelines, Actions, CI  | `cicd`           | GitHub Actions, GitLab CI, Jenkins  |
| Docs, specs, READMEs    | `documentation`  | JSDoc, Swagger, Markdown            |
| Orchestration, routing  | `supervisor`     | Task decomposition, agent selection |

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

| Service      | Port | Health Endpoint |
| ------------ | ---- | --------------- |
| orchestrator | 8001 | `/health`       |
| rag          | 8007 | `/health`       |
| state        | 8008 | `/health`       |
| langgraph    | 8010 | `/health`       |

**Production**: `codechef.appsmithery.co` → `45.55.173.72`

## Repository Structure

```
code-chef/
├── agent_orchestrator/
│   ├── agents/{supervisor,feature_dev,code_review,infrastructure,cicd,documentation}/
│   ├── graph.py          # LangGraph StateGraph
│   └── main.py           # FastAPI + webhooks
├── shared/lib/           # mcp_client, gradient_client, progressive_mcp_loader
├── config/
│   ├── env/.env          # Secrets (use .env.template)
│   ├── agents/models.yaml # LLM configuration (model-agnostic)
│   └── linear/, hitl/, rag/
├── deploy/docker-compose.yml
└── support/docs/         # DEPLOYMENT.md, ARCHITECTURE.md
```

## Adding a New Agent Node

1. Create `agent_orchestrator/agents/<name>/` with `__init__.py`, `system.prompt.md`, `tools.yaml`
2. Inherit from `_shared.base_agent.BaseAgent`
3. Wire into `graph.py` StateGraph + conditional edges
4. Update `config/mcp-agent-tool-mapping.yaml`

## Key References

| Topic                 | Location                                                             |
| --------------------- | -------------------------------------------------------------------- |
| Deployment procedures | `support/docs/DEPLOYMENT.md`                                         |
| Architecture overview | `support/docs/ARCHITECTURE.md`                                       |
| Linear API scripts    | `support/scripts/linear/agent-linear-update.py`                      |
| RAG indexing          | `support/scripts/rag/index_*.py`                                     |
| Observability         | LangSmith: `smith.langchain.com`, Grafana: `appsmithery.grafana.net` |
| HITL template         | UUID `aa632a46-ea22-4dd0-9403-90b0d1f05aa0`                          |

## Quality Bar

- Use Pydantic models and type hints on all functions
- Health endpoints must return `{"status": "healthy", ...}`
- Graceful fallback when API keys missing
- **DO NOT create summary markdown files** unless explicitly requested
- Update existing docs in `support/docs/` when architecture changes
- When user says "update linear roadmap" → update Linear via API, not markdown files
