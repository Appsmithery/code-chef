# code/chef — Your AI Development Team

[![VS Code](https://img.shields.io/badge/VS%20Code-Extension-blue?logo=visualstudiocode)](https://marketplace.visualstudio.com/items?itemName=appsmithery.vscode-codechef)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestrator-purple?logo=langchain)](https://www.langchain.com/langgraph)
[![OpenRouter](https://img.shields.io/badge/OpenRouter-Multi--Model-orange)](https://openrouter.ai)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

> **Talk to your code. Ship faster.**

code/chef is an AI-powered development team that lives in VS Code. Just type `@chef` in Copilot Chat and describe what you want—feature implementation, code reviews, infrastructure setup, CI/CD pipelines, or documentation. The AI team handles the rest.

---

## ✨ What Can code/chef Do?

### 🚀 Build Features

```
@chef Add user authentication with JWT tokens and password reset
```

The Feature Dev agent writes production-ready code with tests.

### 🔍 Review Code

```
@chef Review this PR for security vulnerabilities
```

The Code Review agent analyzes for security issues, performance, and best practices.

### 🏗️ Set Up Infrastructure

```
@chef Create a Docker Compose setup for my Node.js app with PostgreSQL
```

The Infrastructure agent generates Dockerfiles, compose files, and Terraform configs.

### ⚡ Automate Pipelines

```
@chef Create a GitHub Actions workflow for testing and deployment
```

The CI/CD agent builds your pipelines across GitHub Actions, GitLab CI, Jenkins, and more.

### 📚 Write Documentation

```
@chef Document the API endpoints in this codebase
```

The Documentation agent creates README files, API docs, and architecture diagrams.

---

## 🎯 Why code/chef?

| Traditional Workflow          | With code/chef               |
| ----------------------------- | ---------------------------- |
| Switch between 5+ tools       | One chat interface           |
| Copy-paste context everywhere | AI understands your codebase |
| Wait for code reviews         | Instant AI analysis          |
| Manual documentation          | Auto-generated docs          |
| Complex CI/CD setup           | Plain English commands       |

### 🧠 Smart Model Selection

code/chef automatically picks the right AI model for each task:

| Task            | Model             | Why                        |
| --------------- | ----------------- | -------------------------- |
| Code Generation | Claude 3.5 Sonnet | Best-in-class coding       |
| Code Review     | GPT-4o            | Strong reasoning           |
| Infrastructure  | Llama 3.1 70B     | Cost-effective for configs |
| Documentation   | Claude 3.5 Sonnet | Excellent writing          |

### 🏗️ Architecture Overview

```mermaid
flowchart TB
    subgraph VSCode["🖥️ VS Code"]
        Chat["@chef Add JWT auth to my Express API"]
    end

    subgraph Orchestrator["🧑‍🍳 code/chef Orchestrator"]
        Supervisor["Supervisor\n(Head Chef)"]

        subgraph Agents["Specialized Agents"]
            FeatureDev["🚀 Feature Dev\nClaude 3.5"]
            CodeReview["🔍 Code Review\nGPT-4o"]
            CICD["⚡ CI/CD\nLlama 3.1"]
            Infra["🏗️ Infrastructure\nLlama 3.1"]
            Docs["📚 Documentation\nClaude 3.5"]
        end

        Tools["🔧 150+ MCP Tools"]
    end

    subgraph Integrations["External Services"]
        GitHub["🐙 GitHub"]
        Linear["📋 Linear"]
        Docker["🐳 Docker"]
        Metrics["📊 Metrics"]
    end

    Chat --> Supervisor
    Supervisor --> FeatureDev
    Supervisor --> CodeReview
    Supervisor --> CICD
    Supervisor --> Infra
    Supervisor --> Docs

    FeatureDev --> Tools
    CodeReview --> Tools
    CICD --> Tools
    Infra --> Tools
    Docs --> Tools

    Tools --> GitHub
    Tools --> Linear
    Tools --> Docker
    Tools --> Metrics
```

---

## 🚀 Get Started in 2 Minutes

### Install the VS Code Extension

1. **Download** from [GitHub Releases](https://github.com/Appsmithery/code-chef/releases)
2. **Install**: `Ctrl+Shift+P` → "Extensions: Install from VSIX..."
3. **Configure**: `Ctrl+Shift+P` → "code/chef: Configure"
4. **Use**: Open Copilot Chat and type `@chef <your request>`

That's it! See [QUICKSTART.md](support/docs/QUICKSTART.md) for self-hosting options.

---

## 💬 Example Conversations

### Feature Development

```
You: @chef Build a REST API for managing blog posts with CRUD operations

Chef: I'll create a complete blog API with:
- Express routes for posts (GET, POST, PUT, DELETE)
- PostgreSQL database schema
- Input validation
- Error handling
- Unit tests

[Creates files, runs tests, opens PR]
```

### Code Review

```
You: @chef Check my authentication code for security issues

Chef: I found 3 issues:
🔴 Critical: Password stored in plain text (line 45)
🟡 Warning: Missing rate limiting on login endpoint
🟢 Suggestion: Consider adding CSRF protection

[Links to specific lines with fix suggestions]
```

### Infrastructure Setup

```
You: @chef Set up Kubernetes deployment for my microservices

Chef: I'll create:
- Deployment manifests for each service
- ConfigMaps and Secrets
- Horizontal Pod Autoscaler
- Ingress configuration

[Generates YAML files with best practices]
```

---

## 🔧 Slash Commands

| Command                  | What it does                 |
| ------------------------ | ---------------------------- |
| `@chef <task>`           | Execute any development task |
| `@chef /status`          | Check current task progress  |
| `@chef /workflow <name>` | Run a specific workflow      |
| `@chef /tools`           | See available integrations   |

---

## 🔌 Integrations

code/chef connects to your existing tools:

- **GitHub** — PRs, issues, actions
- **Linear** — Project management, approvals
- **Docker** — Container management
- **Databases** — PostgreSQL, Redis
- **Cloud** — DigitalOcean, AWS (coming)

---

## 🏢 Self-Hosting

Want full control? Run your own code/chef instance.

```bash
git clone https://github.com/Appsmithery/code-chef.git
cd code-chef && cp config/env/.env.template config/env/.env
# Add your API keys to .env
cd deploy && docker-compose up -d
```

See [QUICKSTART.md](support/docs/QUICKSTART.md) for detailed setup.

---

## 📖 Documentation

| Guide                                        | Description                 |
| -------------------------------------------- | --------------------------- |
| [Quick Start](support/docs/QUICKSTART.md)    | Installation & first steps  |
| [Architecture](support/docs/ARCHITECTURE.md) | How it works under the hood |
| [Deployment](support/docs/DEPLOYMENT.md)     | Production setup            |

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Open Pull Request

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

## 🔗 Links

- [VS Code Extension](https://marketplace.visualstudio.com/items?itemName=appsmithery.vscode-codechef)
- [GitHub Repository](https://github.com/Appsmithery/code-chef)
- [Linear Project](https://linear.app/dev-ops/project/codechef-78b3b839d36b)

- [LangSmith Traces](https://smith.langchain.com)
- [Grafana Metrics](https://appsmithery.grafana.net)

---

**Built with** ❤️ **using LangGraph, MCP, and VS Code**
