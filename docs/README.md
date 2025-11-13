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

### Development

- **[Codebase Index](CODEBASE_INDEX.md)** - Code structure and organization
- **[Task Orchestration](TASK_ORCHESTRATION.md)** - Workflow engine details
- **[Taskfile Workflows](TASKFILE_WORKFLOWS.md)** - Per-agent task automation
- **[Handbook](HANDBOOK.md)** - Development practices and patterns

### Governance

- **[Refactor Checklist](REFACTOR_CHECKLIST.md)** - Pre-deployment checklist
- **[Documentation Strategy](DOCUMENTATION_STRATEGY.md)** - How we document

---

## 🎯 By Use Case

### I want to...

- **Deploy to production** → [DigitalOcean Quick Deploy](DIGITALOCEAN_QUICK_DEPLOY.md)
- **Set up locally** → [Setup Guide](SETUP_GUIDE.md)
- **Understand the system** → [Architecture Overview](ARCHITECTURE.md)
- **Call an agent API** → [Agent Endpoints](AGENT_ENDPOINTS.md)
- **Configure secrets** → [Secrets Management](SECRETS_MANAGEMENT.md)
- **Run agent tasks** → [Taskfile Workflows](TASKFILE_WORKFLOWS.md)

---

## 📊 System Status

**Current Phase:** Phase 5 Complete ✅

- ✅ All 6 agents operational (orchestrator, feature-dev, code-review, documentation, cicd, infrastructure)
- ✅ RAG service with Qdrant vector database
- ✅ State persistence with PostgreSQL
- ✅ Inter-agent HTTP communication
- ✅ End-to-end workflows validated
- ✅ Per-agent Taskfile automation

**Services:**

- Gateway (MCP): Port 8000
- Orchestrator: Port 8001
- Feature Dev: Port 8002
- Code Review: Port 8003
- Documentation: Port 8006
- CI/CD: Port 8005
- Infrastructure: Port 8004
- RAG: Port 8007
- State: Port 8008
- Qdrant: Ports 6333 (HTTP), 6334 (gRPC)
- PostgreSQL: Port 5432

---

## 📝 Documentation Guidelines

This documentation follows a **layered approach**:

1. **Quick Start** - Get running in <15 minutes
2. **Deep Dive** - Understand architecture and design
3. **Reference** - API specs, schemas, configurations
4. **Operations** - Day-to-day management and troubleshooting

For contributing to documentation, see [Documentation Strategy](DOCUMENTATION_STRATEGY.md).
