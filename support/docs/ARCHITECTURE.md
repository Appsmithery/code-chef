# Architecture Overview

## System Design

code-chef is a multi-agent orchestrator system built on LangGraph with specialized agents for different DevOps functions.

## Core Architecture

### LangGraph StateGraph

- **State**: `WorkflowState` TypedDict with `messages`, `current_agent`, `next_agent`, `task_result`
- **Checkpointing**: PostgresSaver with async pool for interrupt/resume
- **Agent Caching**: `get_agent()` with `_agent_cache` dict prevents redundant instantiation
- **HITL Pattern**: `interrupt({"pending_operation": {...}})` → webhook/poll resume

### Agent Architecture

#### Base Agent Pattern

All agents inherit from `BaseAgent` class which provides:

- **Progressive Tool Loading**: Tools bound at invoke-time based on token strategy
- **LangSmith Tracing**: `@traceable` decorators for observability
- **Error Recovery**: Graceful fallback when tools unavailable
- **Configuration**: YAML-based tool and model configuration

#### Agent Specialization

| Agent            | Model         | Function                    | Tools                       |
| ---------------- | ------------- | --------------------------- | --------------------------- |
| `feature_dev`    | codellama-13b | Code implementation         | Python, Node.js, Git        |
| `code_review`    | llama3.3-70b  | Security/quality review     | SAST, linting, security     |
| `infrastructure` | llama3-8b     | IaC + ModelOps              | Terraform, Docker, ModelOps |
| `cicd`           | llama3.3-70b  | Pipelines, automation       | GitHub Actions, CI/CD       |
| `documentation`  | llama3.3-70b  | Docs, specs, READMEs        | Markdown, API docs          |
| `supervisor`     | llama3.3-70b  | Task routing, orchestration | Graph coordination          |

### ModelOps Extension

The Infrastructure agent includes a comprehensive ModelOps extension for fine-tuning agent models:

**Architecture**:

```
InfrastructureAgent
└─> ModelOpsCoordinator
    ├─> ModelOpsTrainer (HuggingFace AutoTrain integration)
    ├─> ModelEvaluator (LangSmith comparison)
    ├─> ModelOpsDeployment (config management)
    └─> ModelRegistry (version tracking)
```

**Workflow**: Training → Evaluation → Deployment → Registry

**Features**:

- **Training**: AutoTrain Advanced via HuggingFace Space API
- **Evaluation**: Weighted comparison using existing LangSmith evaluators
- **Deployment**: Immediate deployment with automatic config updates
- **Registry**: Thread-safe version tracking with rollback support
- **VS Code Integration**: 5 commands for IDE-native model operations

**Files**:

- `agents/infrastructure/modelops/` - Core ModelOps modules
- `config/models/registry.json` - Model version registry
- `config/modelops/training_defaults.yaml` - Training presets
- `extensions/vscode-codechef/src/commands/modelops.ts` - VS Code UI

## Tool Loading Strategy

Uses **progressive disclosure** for token efficiency:

| Strategy        | When to Use                      | Tool Count  |
| --------------- | -------------------------------- | ----------- |
| **MINIMAL**     | Simple tasks, keyword-matched    | 10-30 tools |
| **PROGRESSIVE** | Multi-step, agent-priority tools | 30-60 tools |
| **FULL**        | Debugging tool discovery issues  | 150+ tools  |

## Observability

- **LangSmith Projects**: Per-agent tracing (`code-chef-feature-dev`, etc.)
- **Prometheus**: `/metrics` endpoint via `Instrumentator`
- **Grafana**: `appsmithery.grafana.net`

## Services & Health

| Service        | Port | Health Endpoint |
| -------------- | ---- | --------------- |
| orchestrator   | 8001 | `/health`       |
| rag-context    | 8007 | `/health`       |
| state-persist  | 8008 | `/health`       |
| agent-registry | 8009 | `/health`       |
| langgraph      | 8010 | `/health`       |

**Production**: `codechef.appsmithery.co` → `45.55.173.72`
