# code/chef - AI DevOps Team

[![VS Code](https://img.shields.io/badge/VS%20Code-Extension-blue?logo=visualstudiocode)](https://marketplace.visualstudio.com/items?itemName=appsmithery.vscode-codechef)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestrator-purple?logo=langchain)](https://www.langchain.com/langgraph)
[![MCP Tools](https://img.shields.io/badge/MCP_Tools-150+-green)](https://github.com/Appsmithery/code-chef)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

The code/chef VS Code extension brings LangGraph-powered, multi-agent workflows directly into Copilot Chat with 150+ MCP tools and intelligent workflow routing.

## Architecture

**Flow:** User → `@chef` → Orchestrator → Specialized Agents → RAG / Context / MCP Tools → Artifacts → User

| Component             | Description                                                   |
| --------------------- | ------------------------------------------------------------- |
| **Chat Participant**  | `@chef` chat participant in Copilot Chat                      |
| **Orchestrator API**  | Supervisor (Head Chef) + Workflow Router                      |
| **Agent Nodes**       | feature-dev, code-review, infrastructure, cicd, documentation |
| **MCP Tools**         | 150+ tools (Linear, GitHub, Docker, Pylance...)               |
| **RAG Context**       | Semantic search via Qdrant for code patterns & library docs   |
| **State Persistence** | PostgreSQL for workflow state, checkpoints, HITL approvals    |
| **StateGraph**        | LangGraph orchestration with interrupt/resume for HITL        |

## Features

- **`@chef` Chat Participant** - Natural language task submission via Copilot Chat
- **Smart Workflow Router** - Heuristic + LLM-based workflow selection with confidence scoring
- **LangGraph StateGraph** - Multi-agent orchestration with PostgreSQL checkpointing
- **150+ MCP Tools** - Progressive disclosure reduces tokens by 80-90%
- **HITL Approvals** - Linear integration for high-risk operations

## Installation

### Option 1: VSIX from GitHub Releases (Recommended)

1. Go to [Releases](https://github.com/Appsmithery/code-chef/releases)
2. Download the latest `vscode-codechef-*.vsix` file
3. In VS Code: `Ctrl+Shift+P` → "Extensions: Install from VSIX..."
4. Select the downloaded file and reload

### Option 2: Build from Source

```bash
cd extensions/vscode-codechef
npm install && npm run compile
npx vsce package
code --install-extension vscode-codechef-*.vsix
```

## Quick Start

### 1. Configure

Press `Ctrl+Shift+P` → "code/chef: Configure"

**Required Settings:**

| Setting                    | Description                                                            |
| -------------------------- | ---------------------------------------------------------------------- |
| `codechef.orchestratorUrl` | Orchestrator endpoint (default: `https://codechef.appsmithery.co/api`) |
| `codechef.apiKey`          | API key for authentication (get from administrator)                    |

### 2. Start Using

Open Copilot Chat and type:

```
@chef Add JWT authentication to my Express API
```

Or use a workflow command:

```
@chef /workflow Deploy PR #123 to production
```

## Slash Commands

| Command                            | Description              | Example                          |
| ---------------------------------- | ------------------------ | -------------------------------- |
| `@chef <task>`                     | Submit development task  | `@chef Add authentication`       |
| `@chef /status [id]`               | Check task status        | `@chef /status abc123`           |
| `@chef /approve <task> <approval>` | Approve pending task     | `@chef /approve abc123 xyz`      |
| `@chef /workflow [name] <task>`    | Execute workflow         | `@chef /workflow Deploy PR #123` |
| `@chef /workflows`                 | List available workflows | `@chef /workflows`               |
| `@chef /tools`                     | List available MCP tools | `@chef /tools`                   |

## Command Palette

Press `Ctrl+Shift+P` and search for:

| Command                             | Description                  |
| ----------------------------------- | ---------------------------- |
| `code/chef: Submit Task`            | Submit via input box         |
| `code/chef: Check Task Status`      | Check task status            |
| `code/chef: Show Pending Approvals` | Open Linear approval hub     |
| `code/chef: Health Check`           | Test orchestrator connection |
| `code/chef: Open LangSmith Traces`  | View LLM traces              |
| `code/chef: Open Grafana Metrics`   | View dashboards              |
| `code/chef: Open Settings`          | Configure extension          |
| `code/chef: Clear Cache`            | Clear session cache          |

## Configuration

### Connection & Authentication

| Setting                    | Default                               | Description                |
| -------------------------- | ------------------------------------- | -------------------------- |
| `codechef.orchestratorUrl` | `https://codechef.appsmithery.co/api` | Orchestrator endpoint      |
| `codechef.apiKey`          | `""`                                  | API key for authentication |

### Workflow Settings

| Setting                             | Default | Description                                                                     |
| ----------------------------------- | ------- | ------------------------------------------------------------------------------- |
| `codechef.defaultWorkflow`          | `auto`  | Default workflow (auto/feature/pr-deployment/hotfix/infrastructure/docs-update) |
| `codechef.workflowAutoExecute`      | `true`  | Auto-execute without confirmation                                               |
| `codechef.workflowConfirmThreshold` | `0.7`   | Confidence threshold for confirmation (0.0-1.0)                                 |
| `codechef.showWorkflowPreview`      | `true`  | Show preview before execution                                                   |

### Token Optimization

| Setting                        | Default       | Description                                                    |
| ------------------------------ | ------------- | -------------------------------------------------------------- |
| `codechef.environment`         | `production`  | Model selection (production/development)                       |
| `codechef.toolLoadingStrategy` | `progressive` | Tool loading strategy (minimal/progressive/agent_profile/full) |
| `codechef.maxToolsPerRequest`  | `30`          | Max tools exposed per request                                  |
| `codechef.enableContext7Cache` | `true`        | Cache library IDs (90% savings)                                |

### Context & RAG

| Setting                     | Default         | Description                    |
| --------------------------- | --------------- | ------------------------------ |
| `codechef.maxContextTokens` | `8000`          | Token budget for agent context |
| `codechef.ragEnabled`       | `true`          | Include RAG context in prompts |
| `codechef.ragMaxResults`    | `5`             | Max semantic search results    |
| `codechef.ragCollection`    | `code_patterns` | Primary RAG collection         |

### Cost Controls

| Setting                       | Default | Description                       |
| ----------------------------- | ------- | --------------------------------- |
| `codechef.dailyTokenBudget`   | `0`     | Daily limit (0 = unlimited)       |
| `codechef.showTokenUsage`     | `true`  | Show token count after requests   |
| `codechef.costAlertThreshold` | `0.10`  | Warning threshold per request ($) |

### Linear Integration

| Setting                         | Default        | Description                         |
| ------------------------------- | -------------- | ----------------------------------- |
| `codechef.linearHubIssue`       | `DEV-68`       | Approval hub issue ID               |
| `codechef.linearWorkspaceSlug`  | `dev-ops`      | Linear workspace slug               |
| `codechef.linearTeamId`         | `f5b610be-...` | Linear team ID for project creation |
| `codechef.autoApproveThreshold` | `low`          | Auto-approve risk level             |

### Observability

| Setting                 | Default                           | Description          |
| ----------------------- | --------------------------------- | -------------------- |
| `codechef.langsmithUrl` | LangSmith project URL             | LangSmith traces URL |
| `codechef.grafanaUrl`   | `https://appsmithery.grafana.net` | Grafana metrics URL  |

## Troubleshooting

### Cannot connect to orchestrator

1. Check URL: `Ctrl+Shift+P` → "code/chef: Configure"
2. Verify API key is set in settings
3. Test health: `curl https://codechef.appsmithery.co/api/health`

### 401 Unauthorized

1. Get API key from administrator
2. Set in VS Code settings: `codechef.apiKey`

### No tools appearing

1. Clear cache: `Ctrl+Shift+P` → "code/chef: Clear Cache"
2. Restart VS Code

## Development

```bash
# Build
npm run compile

# Watch mode
npm run watch

# Package VSIX
npx vsce package

# Lint
npm run lint
```

## License

MIT License - see [LICENSE](LICENSE)

## Links

- [GitHub Repository](https://github.com/Appsmithery/code-chef)
- [Linear Project](https://linear.app/dev-ops/project/codechef-78b3b839d36b)
- [LangSmith Traces](https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects/p/f967bb5e-2e61-434f-8ee1-0df8c22bc046)
- [Grafana Metrics](https://appsmithery.grafana.net)
