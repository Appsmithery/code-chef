# Dev-Tools Documentation Index

## 📚 Quick Navigation

### Getting Started

- **[Setup Guide](onboarding/SETUP_GUIDE.md)** - First-time setup instructions
- **[Architecture Overview](overview/ARCHITECTURE.md)** - System design and components
- **[Agent Endpoints](AGENT_ENDPOINTS.md)** - API reference for all agents

### Deployment

- **[DigitalOcean Quick Deploy](DIGITALOCEAN_QUICK_DEPLOY.md)** - 45-minute production deployment guide
- **[Deployment Overview](DEPLOYMENT.md)** - General deployment concepts
- **[Secrets Management](SECRETS_MANAGEMENT.md)** - Security and configuration

### Development

- **[Codebase Index](CODEBASE_INDEX.md)** - Code structure and organization
- **[Task Orchestration](overview/TASK_ORCHESTRATION.md)** - Workflow engine details
- **[Handbook](HANDBOOK.md)** - Development practices and patterns

### Operations

- **[Operations Guide](OPERATIONS.md)** - Day-to-day operational procedures _(coming soon)_
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues and solutions _(coming soon)_
- **[API Reference](API_REFERENCE.md)** - Comprehensive endpoint documentation _(coming soon)_

### Governance

- **[Refactor Checklist](governance/REFACTOR_CHECKLIST.md)** - Pre-deployment checklist
- **[Secrets Management Policy](governance/SECRETS_MANAGEMENT.md)** - Security guidelines
- **[Documentation Strategy](overview/DOCUMENTATION_STRATEGY.md)** - How we document

### Archive

- **[Completed Phases](archive/phases/)** - Historical phase completion summaries
- **[Planning Documents](archive/planning/)** - Archived planning artifacts

---

## 🎯 By Use Case

### I want to...

- **Deploy to production** → [DigitalOcean Quick Deploy](DIGITALOCEAN_QUICK_DEPLOY.md)
- **Set up locally** → [Setup Guide](onboarding/SETUP_GUIDE.md)
- **Understand the system** → [Architecture Overview](overview/ARCHITECTURE.md)
- **Call an agent API** → [Agent Endpoints](AGENT_ENDPOINTS.md)
- **Fix an issue** → [Troubleshooting](TROUBLESHOOTING.md) _(coming soon)_
- **Configure secrets** → [Secrets Management](SECRETS_MANAGEMENT.md)

---

## 📊 System Status

**Current Phase:** Phase 5 Complete ✅

- ✅ All 6 agents operational (orchestrator, feature-dev, code-review, documentation, cicd, infrastructure)
- ✅ RAG service with Qdrant vector database
- ✅ State persistence with PostgreSQL
- ✅ Inter-agent HTTP communication
- ✅ End-to-end workflows validated

**Services:**

- Gateway (MCP): Port 8000
- Orchestrator: Port 8001
- Feature Dev: Port 8002
- Code Review: Port 8003
- Documentation: Port 8004
- CI/CD: Port 8005
- Infrastructure: Port 8006
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

For contributing to documentation, see [Documentation Strategy](overview/DOCUMENTATION_STRATEGY.md).
