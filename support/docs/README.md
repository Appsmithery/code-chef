# Dev-Tools Documentation

**Complete documentation for the LangGraph-powered AI agent orchestration platform.**

---

## Quick Start

| Document                                 | Description                        |
| ---------------------------------------- | ---------------------------------- |
| **[QUICKSTART.md](QUICKSTART.md)**       | 15-minute setup guide              |
| **[ARCHITECTURE.md](ARCHITECTURE.md)**   | System design + LangGraph workflow |
| **[DEPLOYMENT.md](DEPLOYMENT.md)**       | Production deployment              |
| **[OBSERVABILITY.md](OBSERVABILITY.md)** | Monitoring + tracing               |

---

## Structure

```
support/docs/
 QUICKSTART.md
 ARCHITECTURE.md
 DEPLOYMENT.md
 OBSERVABILITY.md
 LINEAR_HITL_WORKFLOW.md
 architecture/          # Architecture deep-dives
 guides/                # Integration guides
 operations/            # Operational procedures
```

---

## Find What You Need

### Setup & Deployment

- Local setup [QUICKSTART.md](QUICKSTART.md)
- Production deploy [DEPLOYMENT.md](DEPLOYMENT.md)
- Manage secrets [operations/SECRETS_MANAGEMENT.md](operations/SECRETS_MANAGEMENT.md)

### Architecture & Design

- System overview [ARCHITECTURE.md](ARCHITECTURE.md)
- LangGraph workflow [architecture/LANGGRAPH_INTEGRATION.md](architecture/LANGGRAPH_INTEGRATION.md)
- MCP tools (150+) [architecture/MCP_INTEGRATION.md](architecture/MCP_INTEGRATION.md)

### Integrations

- Linear + HITL [guides/LINEAR_INTEGRATION.md](guides/LINEAR_INTEGRATION.md)
- LangSmith tracing [guides/LANGSMITH_TRACING.md](guides/LANGSMITH_TRACING.md)
- Gradient AI [guides/GRADIENT_AI_SETUP.md](guides/GRADIENT_AI_SETUP.md)

### Operations

- Monitor services [OBSERVABILITY.md](OBSERVABILITY.md)
- Clean Docker [operations/CLEANUP_QUICK_REFERENCE.md](operations/CLEANUP_QUICK_REFERENCE.md)
- Disaster recovery [operations/DISASTER_RECOVERY.md](operations/DISASTER_RECOVERY.md)

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

## Recent Changes (November 25, 2025)

**Documentation Consolidation:**

- Created QUICKSTART.md (all-in-one setup guide)
- Rewrote ARCHITECTURE.md (v0.3 LangGraph focus)
- Unified DEPLOYMENT.md (all strategies in one doc)
- Consolidated LINEAR_INTEGRATION.md (combined 5 Linear docs)
- Removed 40+ redundant/outdated files
- **Net reduction**: 60+ files 15 essential docs (~75%)

**Deprecated Paths** (update bookmarks):

- ~~WORKSPACE_AWARE_ARCHITECTURE.md~~ [ARCHITECTURE.md](ARCHITECTURE.md)
- ~~DEPLOYMENT_GUIDE.md~~ [DEPLOYMENT.md](DEPLOYMENT.md)
- ~~SETUP_GUIDE.md~~ [QUICKSTART.md](QUICKSTART.md)
- ~~api/AGENT_ENDPOINTS.md~~ [ARCHITECTURE.md](ARCHITECTURE.md)
- ~~guides/integration/LINEAR_SETUP.md~~ [guides/LINEAR_INTEGRATION.md](guides/LINEAR_INTEGRATION.md)

---

_For documentation issues, open an issue on GitHub._
