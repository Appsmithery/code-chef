# Dev-Tools Documentation

**Complete documentation for the LangGraph-powered AI agent orchestration platform.**

---

## Quick Start

| Document                                                          | Description                        |
| ----------------------------------------------------------------- | ---------------------------------- |
| **[quickstart.md](getting-started/quickstart.md)**                | 15-minute setup guide              |
| **[architecture.md](architecture-and-platform/architecture.md)**  | System design + LangGraph workflow |
| **[deployment.md](getting-started/deployment.md)**                | Production deployment              |
| **[observability-guide.md](integrations/observability-guide.md)** | Monitoring + tracing               |

---

## Documentation Structure

```
support/docs/
├── getting-started/              # Essential setup and deployment
│   ├── quickstart.md
│   ├── deployment.md
│   └── frontend-v3-deployment.md
├── architecture-and-platform/    # Core system design
│   ├── architecture.md
│   ├── langgraph-integration.md
│   ├── multi-agent-workflows.md
│   ├── task-orchestration.md
│   └── rag-documentation-aggregation.md
├── integrations/                 # External service integrations
│   ├── linear-integration-guide.md
│   ├── linear-hitl-workflow.md
│   ├── langsmith-tracing.md
│   ├── gradient-ai-setup.md
│   └── observability-guide.md
├── operations/                   # Operational procedures
│   ├── cleanup-quick-reference.md
│   ├── disaster-recovery.md
│   ├── docker-cleanup.md
│   ├── grafana-dashboard-guide.md
│   ├── import-grafana-dashboards.md
│   ├── rag-qdrant-alignment.md
│   ├── rag-semantic-search.md
│   ├── secrets-management.md
│   └── secrets-rotation.md
└── reference/                    # Technical references
    ├── mcp-integration.md
    ├── langgraph-quick-ref.md
    ├── event-protocol.md
    ├── notification-system.md
    └── shared-lib-notifications.md
```

---

## Find What You Need

### 🚀 Getting Started

- [Local setup](getting-started/quickstart.md)
- [Production deployment](getting-started/deployment.md)
- [Frontend V3 deployment](getting-started/frontend-v3-deployment.md)

### 🏗️ Architecture & Platform

- [System overview](architecture-and-platform/architecture.md)
- [LangGraph integration](architecture-and-platform/langgraph-integration.md)
- [Multi-agent workflows](architecture-and-platform/multi-agent-workflows.md)
- [Task orchestration](architecture-and-platform/task-orchestration.md)
- [RAG documentation aggregation](architecture-and-platform/rag-documentation-aggregation.md)

### 🔌 Integrations

- [Linear + HITL workflow](integrations/linear-integration-guide.md)
- [Linear HITL workflow details](integrations/linear-hitl-workflow.md)
- [LangSmith tracing](integrations/langsmith-tracing.md)
- [Gradient AI setup](integrations/gradient-ai-setup.md)
- [Observability guide](integrations/observability-guide.md)

### ⚙️ Operations

- [Cleanup quick reference](operations/cleanup-quick-reference.md)
- [Docker cleanup](operations/docker-cleanup.md)
- [Disaster recovery](operations/disaster-recovery.md)
- [Secrets management](operations/secrets-management.md)
- [Secrets rotation](operations/secrets-rotation.md)
- [Grafana dashboards](operations/grafana-dashboard-guide.md)
- [Import Grafana dashboards](operations/import-grafana-dashboards.md)
- [RAG Qdrant alignment](operations/rag-qdrant-alignment.md)
- [RAG semantic search](operations/rag-semantic-search.md)

### 📚 Reference

- [MCP integration (150+ tools)](reference/mcp-integration.md)
- [LangGraph quick reference](reference/langgraph-quick-ref.md)
- [Event protocol](reference/event-protocol.md)
- [Notification system](reference/notification-system.md)
- [Shared lib notifications](reference/shared-lib-notifications.md)

---

## System Overview

**v0.3 Architecture:**

- **1 Orchestrator Service** (FastAPI + LangGraph, port 8001)
  - 6 Internal Agent Nodes (supervisor, feature-dev, code-review, infrastructure, cicd, documentation)
- **MCP Gateway** (port 8000): 150+ tools via stdio transport
- **RAG Context** (port 8007): Vector search with Qdrant
- **State Persistence** (port 8008): PostgreSQL checkpointing

**Key Features:**

LangGraph workflows with PostgreSQL checkpointing  
 Progressive tool disclosure (80-90% token savings)  
 LangChain function calling (LLM invokes tools directly)  
 HITL approvals via Linear integration  
 LangSmith automatic tracing  
 Gradient AI inference ($0.20-0.60/1M tokens)

---

## Production Status

**Domain:** https://codechef.appsmithery.co  
**Droplet:** mcp-gateway (codechef.appsmithery.co, 45.55.173.72)  
**Version:** v0.4  
**Updated:** December 2025

### Services

- **orchestrator** (/api): LangGraph + 6 agents
- **rag-context** (/rag): Vector search (Qdrant Cloud)
- **state** (/state): Workflow persistence
- **langgraph** (/langgraph): Checkpoint service

### Monitoring

- **LangSmith**: https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207
- **Grafana**: https://appsmithery.grafana.net
- **Linear**: https://linear.app/dev-ops

---

## Document Status

| Status        | Folder                     | Description                           |
| ------------- | -------------------------- | ------------------------------------- |
| ✅ **Active** | getting-started/           | Essential setup and deployment guides |
| ✅ **Active** | architecture-and-platform/ | Core system architecture and design   |
| ✅ **Active** | integrations/              | Third-party service integrations      |
| ✅ **Active** | operations/                | Operational runbooks and procedures   |
| ✅ **Active** | reference/                 | Technical references and API docs     |

---

## Recent Changes (December 9, 2025)

**Documentation Reorganization:**

- Restructured into taxonomy-based folders (getting-started, architecture-and-platform, integrations, operations, reference)
- Renamed all docs to kebab-case for consistency
- Consolidated redundant guides into focused documents
- Removed legacy-archive/ folder (deprecated content cleaned up)
- Updated README with clear navigation paths for #codebase compatibility
- **Net result**: Improved discoverability and maintainability

**Path Updates** (update bookmarks):

- ~~QUICKSTART.md~~ → [getting-started/quickstart.md](getting-started/quickstart.md)
- ~~ARCHITECTURE.md~~ → [architecture-and-platform/architecture.md](architecture-and-platform/architecture.md)
- ~~DEPLOYMENT.md~~ → [getting-started/deployment.md](getting-started/deployment.md)
- ~~LINEAR_INTEGRATION_GUIDE.md~~ → [integrations/linear-integration-guide.md](integrations/linear-integration-guide.md)
- ~~OBSERVABILITY_GUIDE.md~~ → [integrations/observability-guide.md](integrations/observability-guide.md)
- ~~architecture/LANGGRAPH_INTEGRATION.md~~ → [architecture-and-platform/langgraph-integration.md](architecture-and-platform/langgraph-integration.md)
- ~~guides/LANGSMITH_TRACING.md~~ → [integrations/langsmith-tracing.md](integrations/langsmith-tracing.md)

---

_For documentation issues, open an issue on GitHub._
