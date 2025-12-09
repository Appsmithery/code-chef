# code/chef Architecture

**Version:** v1.0  
**Last Updated:** December 9, 2025

See [QUICKSTART.md](QUICKSTART.md) for setup | [DEPLOYMENT.md](DEPLOYMENT.md) for deployment

---

## How code/chef Works

When you type `@chef Add authentication to my app`, here's what happens:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Your VS Code                                      │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  Copilot Chat: @chef Add JWT authentication to my Express API         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         code/chef Orchestrator                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  🧑‍🍳 Supervisor (Head Chef)                                          │   │
│  │  • Understands your request                                          │   │
│  │  • Routes to the right specialist                                    │   │
│  │  • Coordinates multi-step workflows                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│         ┌──────────────────────────┼──────────────────────────┐            │
│         ▼                          ▼                          ▼            │
│  ┌─────────────┐          ┌─────────────┐          ┌─────────────┐        │
│  │ Feature Dev │          │ Code Review │          │   CI/CD     │        │
│  │ Claude 3.5  │          │   GPT-4o    │          │ Llama 3.1   │        │
│  └─────────────┘          └─────────────┘          └─────────────┘        │
│         │                          │                          │            │
│  ┌─────────────┐          ┌─────────────┐          ┌─────────────┐        │
│  │Infrastructure│          │Documentation│          │  150+ MCP   │        │
│  │ Llama 3.1   │          │ Claude 3.5  │          │   Tools     │        │
│  └─────────────┘          └─────────────┘          └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  📁 Your Codebase  │  🐙 GitHub  │  📋 Linear  │  🐳 Docker  │  📊 Metrics │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## The AI Team

code/chef uses specialized AI agents, each optimized for specific tasks:

### 🧑‍🍳 Supervisor (Head Chef)

**Model:** Claude 3.5 Sonnet via OpenRouter

The head chef who receives your request, breaks it down into subtasks, and coordinates the specialist agents. Handles complex multi-step workflows.

### 🚀 Feature Dev

**Model:** Claude 3.5 Sonnet via OpenRouter

Writes production-ready code. Understands your codebase context and generates code that matches your existing patterns, with tests.

### 🔍 Code Review

**Model:** GPT-4o via OpenRouter

Analyzes code for security vulnerabilities, performance issues, and best practices. Provides actionable feedback with specific line numbers.

### 🏗️ Infrastructure

**Model:** Llama 3.1 70B via OpenRouter

Creates Docker configurations, Terraform files, Kubernetes manifests, and other infrastructure-as-code. Cost-effective for configuration generation.

### ⚡ CI/CD

**Model:** Llama 3.1 70B via OpenRouter

Builds pipelines for GitHub Actions, GitLab CI, Jenkins, and more. Understands testing, deployment, and release workflows.

### 📚 Documentation

**Model:** Claude 3.5 Sonnet via OpenRouter

Writes README files, API documentation, architecture diagrams, and inline code comments. Excellent technical writing.

---

## Multi-Model Architecture

code/chef uses **OpenRouter** to access the best AI models for each task:

```
┌───────────────────────────────────────────────────────────────┐
│                        OpenRouter                              │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  200+ Models • Single API • Automatic Fallback          │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│   │Claude 3.5    │  │   GPT-4o     │  │ Llama 3.1    │       │
│   │Sonnet        │  │              │  │   70B        │       │
│   │              │  │              │  │              │       │
│   │• Code Gen    │  │• Reasoning   │  │• Config Gen  │       │
│   │• Docs        │  │• Analysis    │  │• Pipelines   │       │
│   │• Planning    │  │• Review      │  │• IaC         │       │
│   └──────────────┘  └──────────────┘  └──────────────┘       │
└───────────────────────────────────────────────────────────────┘
```

### Why Multi-Model?

| Benefit                   | How it Helps                                                    |
| ------------------------- | --------------------------------------------------------------- |
| **Best tool for the job** | Claude for code, GPT-4o for analysis, Llama for cost efficiency |
| **Automatic failover**    | If one model is slow, another takes over                        |
| **Cost optimization**     | Use expensive models only when needed                           |
| **Real-time streaming**   | See responses as they're generated                              |

---

## Workflow Engine

code/chef uses pre-built workflows for common development patterns:

### Feature Development Workflow

```
Analyze Requirements → Implement Feature → Code Review → Write Tests → Create PR
```

### PR Deployment Workflow

```
Validate PR → Run Tests → Security Scan → Deploy to Staging → Notify Team
```

### Hotfix Workflow

```
Assess Impact → Apply Fix → Expedited Review → Deploy → Post-mortem
```

### Documentation Update Workflow

```
Scan Codebase → Generate Docs → Review for Accuracy → Commit
```

---

## Integrations

code/chef connects to 150+ tools through the **Model Context Protocol (MCP)**:

### Code & Files

- **Filesystem** — Read, write, search files
- **GitHub** — PRs, issues, actions, repos
- **Git** — Commits, branches, diffs

### Project Management

- **Linear** — Issues, projects, approvals
- **Notion** — Documentation, wikis

### Infrastructure

- **Docker** — Containers, images, compose
- **Kubernetes** — Coming soon

### Monitoring

- **Grafana** — Dashboards, alerts
- **Prometheus** — Metrics queries

---

## Human-in-the-Loop (HITL)

For high-risk operations, code/chef asks for approval:

```
┌────────────────────────────────────────────────────────┐
│  ⚠️ Approval Required                                  │
│                                                        │
│  Action: Deploy to production                          │
│  Risk Level: High                                      │
│                                                        │
│  Details:                                              │
│  - Affects 3 services                                  │
│  - Requires database migration                         │
│  - Estimated downtime: 2 minutes                       │
│                                                        │
│  [Approve in Linear] or reply "approve" in chat       │
└────────────────────────────────────────────────────────┘
```

### Risk Assessment

| Risk Level   | Examples                    | Action                    |
| ------------ | --------------------------- | ------------------------- |
| **Low**      | Read files, generate docs   | Auto-execute              |
| **Medium**   | Create branches, open PRs   | Execute with notification |
| **High**     | Deploy, delete resources    | Require approval          |
| **Critical** | Production database changes | Multi-person approval     |

---

## Services Overview

When self-hosting, code/chef runs these services:

| Service          | Purpose                 | Port |
| ---------------- | ----------------------- | ---- |
| **Orchestrator** | Main API, all AI agents | 8001 |
| **RAG Context**  | Semantic code search    | 8007 |
| **State**        | Workflow persistence    | 8008 |
| **PostgreSQL**   | Database                | 5432 |

All services run in Docker containers via `docker-compose`.

---

## Security

### Data Handling

- Your code stays in your environment (self-hosted) or is encrypted in transit (hosted)
- API keys are never logged or stored in plain text
- HITL approvals provide human oversight for sensitive operations

### Access Control

- API key authentication for all requests
- Role-based access coming soon

---

## Related Documentation

- **[QUICKSTART.md](QUICKSTART.md)** — Installation and first steps
- **[DEPLOYMENT.md](DEPLOYMENT.md)** — Production deployment guide
- **[README](../../README.md)** — Feature overview
