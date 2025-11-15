# Dev-Tools Documentation Index

## 📚 Quick Navigation

### Getting Started

- **[Setup Guide](SETUP_GUIDE.md)** - First-time setup instructions
- **[Architecture Overview](ARCHITECTURE.md)** - System design and components
- **[Agent Endpoints](AGENT_ENDPOINTS.md)** - API reference for all agents

### Deployment

- **[DigitalOcean Quick Deploy](DIGITALOCEAN_QUICK_DEPLOY.md)** - 45-minute production deployment guide
- **[Deployment Overview](DEPLOYMENT.md)** - General deployment concepts
- **[Secrets Management](SECRETS_MANAGEMENT.md)** - Security and configuration

### Integrations

- **[MCP Integration](MCP_INTEGRATION.md)** - Model Context Protocol (150+ tools)
- **[Gradient Quick Start](GRADIENT_QUICK_START.md)** - DigitalOcean AI inference setup
- **[Gradient Troubleshooting](GRADIENT_TROUBLESHOOTING.md)** - LLM integration debugging guide
- **[Langfuse Tracing](LANGFUSE_TRACING.md)** - LLM observability setup
- **[Langfuse Examples](LANGFUSE_EXAMPLES.md)** - Tracing patterns and queries
- **[Prometheus Metrics](PROMETHEUS_METRICS.md)** - HTTP metrics and monitoring

### Development

- **[Task Orchestration](TASK_ORCHESTRATION.md)** - Workflow engine details
- **[Frontend Integration](FRONTEND_INTEGRATION.md)** - UI/API integration guide
- **[Handbook](HANDBOOK.md)** - Development practices and patterns

---

## 🎯 By Use Case

### I want to...

- **Deploy to production** → [DigitalOcean Quick Deploy](DIGITALOCEAN_QUICK_DEPLOY.md)
- **Set up locally** → [Setup Guide](SETUP_GUIDE.md)
- **Understand the system** → [Architecture Overview](ARCHITECTURE.md)
- **Call an agent API** → [Agent Endpoints](AGENT_ENDPOINTS.md)
- **Configure secrets** → [Secrets Management](SECRETS_MANAGEMENT.md)
- **Add LLM inference** → [Gradient Quick Start](GRADIENT_QUICK_START.md)
- **Debug LLM issues** → [Gradient Troubleshooting](GRADIENT_TROUBLESHOOTING.md)
- **Monitor LLM calls** → [Langfuse Tracing](LANGFUSE_TRACING.md)
- **Track HTTP metrics** → [Prometheus Metrics](PROMETHEUS_METRICS.md)
- **Access 150+ tools** → [MCP Integration](MCP_INTEGRATION.md)

---

## 📊 System Status

**Current Phase:** Phase 7 Complete ✅

- ✅ All 6 agents operational with MCP integration
- ✅ 150+ MCP tools available (filesystem, memory, git, sequential-thinking, etc.)
- ✅ Langfuse LLM tracing infrastructure configured
- ✅ Prometheus HTTP metrics collection active
- ✅ DigitalOcean Gradient AI integration complete (llama3-8b-instruct operational)
- ✅ LLM-powered task decomposition in production (150x cheaper than GPT-4)
- ✅ RAG service streaming DigitalOcean KB exports into Qdrant Cloud
- ✅ State persistence with PostgreSQL
- ✅ E2E workflows validated

**Services:**

- Gateway (MCP): Port 8000 - 150+ tools, Linear integration, secrets management
- Orchestrator: Port 8001 - Task delegation, llama-3.1-70b inference
- Feature Dev: Port 8002 - Code generation, codellama-13b inference, RAG context
- Code Review: Port 8003 - Quality assurance, llama-3.1-70b inference
- Infrastructure: Port 8004 - IaC generation, llama-3.1-8b inference
- CI/CD: Port 8005 - Pipeline automation, llama-3.1-8b inference
- Documentation: Port 8006 - Docs generation, mistral-7b inference
- RAG: Port 8007 - Vector search
- State: Port 8008 - Workflow persistence
- Prometheus: Port 9090 - Metrics dashboard
- Qdrant: Ports 6333 (HTTP), 6334 (gRPC)
- PostgreSQL: Port 5432

---

## 📝 Documentation Guidelines

This documentation follows a **layered approach**:

1. **Quick Start** - Get running in <15 minutes
2. **Deep Dive** - Understand architecture and design
3. **Reference** - API specs, schemas, configurations
4. **Operations** - Day-to-day management and troubleshooting

### Archived Documentation

Obsolete or superseded documents are moved to `archive/` to maintain clarity.
