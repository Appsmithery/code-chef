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

---

## 🚀 Get Started in 2 Minutes

### Step 1: Install

**From GitHub Releases** (recommended):

1. Go to [Releases](https://github.com/Appsmithery/code-chef/releases)
2. Download `vscode-codechef-*.vsix`
3. In VS Code: `Ctrl+Shift+P` → "Extensions: Install from VSIX..."
4. Select the file and reload

**From VS Code Marketplace**:

1. Open Extensions (`Ctrl+Shift+X`)
2. Search "code/chef"
3. Click Install

### Step 2: Configure

Press `Ctrl+Shift+P` → "code/chef: Configure"

Enter your API key (get from your administrator).

### Step 3: Start Cooking

Open Copilot Chat and type:

```
@chef Build a REST API for user management with JWT auth
```

That's it! The AI team handles the rest.

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

---

## 🔧 Commands

### Chat Commands

| Command                  | What it does                 |
| ------------------------ | ---------------------------- |
| `@chef <task>`           | Execute any development task |
| `@chef /status`          | Check current task progress  |
| `@chef /workflow <name>` | Run a specific workflow      |
| `@chef /tools`           | See available integrations   |

### Command Palette

Press `Ctrl+Shift+P` and search for:

| Command                   | Description          |
| ------------------------- | -------------------- |
| `code/chef: Submit Task`  | Submit via input box |
| `code/chef: Health Check` | Test connection      |
| `code/chef: Configure`    | Open settings        |
| `code/chef: Clear Cache`  | Reset session        |

---

## ⚙️ Settings

### Essential Settings

| Setting                    | Description                          |
| -------------------------- | ------------------------------------ |
| `codechef.orchestratorUrl` | Server URL (default: hosted service) |
| `codechef.apiKey`          | Your API key                         |

### Workflow Settings

| Setting                        | Default | Description                  |
| ------------------------------ | ------- | ---------------------------- |
| `codechef.defaultWorkflow`     | `auto`  | Automatic workflow selection |
| `codechef.showWorkflowPreview` | `true`  | Preview before execution     |

### Streaming (Real-time Responses)

| Setting                 | Default | Description                      |
| ----------------------- | ------- | -------------------------------- |
| `codechef.useStreaming` | `true`  | Enable real-time token streaming |

---

## 🔌 Integrations

code/chef connects to your existing tools:

- **GitHub** — PRs, issues, actions
- **Linear** — Project management, approvals
- **Docker** — Container management
- **Databases** — PostgreSQL, Redis

---

## ❓ Troubleshooting

### Cannot connect to orchestrator

1. Check URL: `Ctrl+Shift+P` → "code/chef: Configure"
2. Verify API key is set
3. Run health check: `Ctrl+Shift+P` → "code/chef: Health Check"

### No response from @chef

1. Clear cache: `Ctrl+Shift+P` → "code/chef: Clear Cache"
2. Restart VS Code
3. Check Output panel (`Ctrl+Shift+U`) for errors

---

## 🏢 Self-Hosting

Want full control? Run your own code/chef instance. See the [main repository](https://github.com/Appsmithery/code-chef) for setup instructions.

---

## 📄 License

MIT License — see [LICENSE](LICENSE)

---

## 🔗 Links

- [GitHub Repository](https://github.com/Appsmithery/code-chef)
- [Quick Start Guide](https://github.com/Appsmithery/code-chef/blob/main/support/docs/QUICKSTART.md)
- [Linear Project](https://linear.app/dev-ops/project/codechef-78b3b839d36b)

## Links

- [GitHub Repository](https://github.com/Appsmithery/code-chef)
- [Linear Project](https://linear.app/dev-ops/project/codechef-78b3b839d36b)
- [LangSmith Traces](https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects/p/f967bb5e-2e61-434f-8ee1-0df8c22bc046)
- [Grafana Metrics](https://appsmithery.grafana.net)
