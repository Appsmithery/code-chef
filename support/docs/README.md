# Dev-Tools Documentation Index

## 📁 Directory Structure

Documentation is organized into logical categories:

- **architecture/** - System design, agent architecture, event protocols
- **api/** - API endpoints and reference documentation
- **guides/** - Implementation and integration guides
  - **integration/** - External service setup (Linear, LangSmith, etc.)
  - **implementation/** - Feature implementation guides (HITL, etc.)
- **operations/** - Deployment, monitoring, maintenance
- **testing/** - Testing strategies and chaos engineering
- **\_temp/** - Temporary working files (excluded from Git)

## 📚 Quick Navigation

### Getting Started

- **[Setup Guide](SETUP_GUIDE.md)** - First-time setup instructions
- **[Architecture Overview](ARCHITECTURE.md)** - System design and components
- **[Agent Endpoints](api/AGENT_ENDPOINTS.md)** - API reference for all agents

### Deployment & Operations

- **[Docker Hub Deployment](operations/DOCKER_HUB_DEPLOYMENT.md)** - v2.0 architecture with Docker Hub registry
- **[DigitalOcean Quick Deploy](operations/DIGITALOCEAN_QUICK_DEPLOY.md)** - 45-minute production deployment guide
- **[Deployment Overview](operations/DEPLOYMENT.md)** - General deployment concepts
- **[Secrets Management](operations/SECRETS_MANAGEMENT.md)** - Security and configuration
- **[Prometheus Metrics](operations/PROMETHEUS_METRICS.md)** - HTTP metrics and monitoring

### Architecture & Design

- **[MCP Integration](architecture/MCP_INTEGRATION.md)** - Model Context Protocol (150+ tools)
- **[Progressive Tool Disclosure](architecture/PROGRESSIVE_TOOL_DISCLOSURE.md)** - LangChain tool binding (80-90% token savings)
- **[LangGraph Integration](architecture/LANGGRAPH_INTEGRATION.md)** - Workflow orchestration
- **[Multi-Agent Workflows](architecture/MULTI_AGENT_WORKFLOWS.md)** - Collaboration patterns
- **[Task Orchestration](architecture/TASK_ORCHESTRATION.md)** - Workflow engine details

### Integration Guides

- **[Gradient Quick Start](guides/integration/GRADIENT_AI_QUICK_START.md)** - DigitalOcean AI inference setup
- **[LangSmith Tracing](guides/integration/LANGSMITH_TRACING.md)** - LLM observability setup
- **[LangSmith Examples](guides/integration/LANGSMITH_EXAMPLES.md)** - Tracing patterns and queries
- **[Linear Setup](guides/integration/LINEAR_SETUP.md)** - Linear project management

### Development Guides

- **[Frontend Integration](guides/FRONTEND_INTEGRATION.md)** - UI/API integration guide
- **[Handbook](guides/HANDBOOK.md)** - Development practices and patterns
- **[Configure Agents UI](guides/CONFIGURE_AGENTS_UI.md)** - Agent UI configuration

---

## 🎯 By Use Case

### I want to...

- **Deploy to production** → [Docker Hub Deployment](operations/DOCKER_HUB_DEPLOYMENT.md) (v2.0 recommended)
- **Set up locally** → [Setup Guide](SETUP_GUIDE.md)
- **Understand the system** → [Architecture Overview](ARCHITECTURE.md)
- **Call an agent API** → [Agent Endpoints](api/AGENT_ENDPOINTS.md)
- **Configure secrets** → [Secrets Management](operations/SECRETS_MANAGEMENT.md)
- **Add LLM inference** → [Gradient Quick Start](guides/integration/GRADIENT_AI_QUICK_START.md)
- **Monitor LLM calls** → [LangSmith Tracing](guides/integration/LANGSMITH_TRACING.md)
- **Track HTTP metrics** → [Prometheus Metrics](operations/PROMETHEUS_METRICS.md)
- **Access 150+ tools** → [MCP Integration](architecture/MCP_INTEGRATION.md)

---

## 📊 System Status

**Current Phase:** Phase 7 Complete ✅

- ✅ LangGraph orchestrator with 6 internal agent nodes
- ✅ 150+ MCP tools available (filesystem, memory, git, sequential-thinking, etc.)
- ✅ **LangChain tool binding** - Progressive disclosure with function calling (80-90% token savings)
- ✅ LangSmith LLM tracing infrastructure configured
- ✅ Prometheus HTTP metrics collection active
- ✅ DigitalOcean Gradient AI integration complete (llama3-8b-instruct operational)
- ✅ LLM-powered task decomposition in production (150x cheaper than GPT-4)
- ✅ RAG service streaming DigitalOcean KB exports into Qdrant Cloud
- ✅ State persistence with PostgreSQL
- ✅ E2E workflows validated

**Core Services:**

- MCP Gateway: Port 8000 - 150+ tools, Linear integration, secrets management
- Orchestrator: Port 8001 - LangGraph workflow engine with agent nodes (feature-dev, code-review, infrastructure, cicd, documentation)
- RAG: Port 8007 - Vector search
- State: Port 8008 - Workflow persistence
- Prometheus: Port 9090 - Metrics dashboard
- Qdrant: Ports 6333 (HTTP), 6334 (gRPC)
- PostgreSQL: Port 5432

**Architecture:** Single orchestrator container with LangGraph supervisor routing. All 6 agents are internal nodes within the workflow graph, not separate microservices.

---

## 📝 Documentation Guidelines

This documentation follows a **layered approach**:

1. **Quick Start** - Get running in <15 minutes
2. **Deep Dive** - Understand architecture and design
3. **Reference** - API specs, schemas, configurations
4. **Operations** - Day-to-day management and troubleshooting

### Archived Documentation

Obsolete or superseded documents are moved to `archive/` to maintain clarity.
