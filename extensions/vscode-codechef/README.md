# code/chef - AI Agent Orchestrator

[![VS Code](https://img.shields.io/badge/VS%20Code-Extension-blue)](https://marketplace.visualstudio.com/)
[![MCP Tools](https://img.shields.io/badge/tools-150%2B-green)](https://github.com/Appsmithery/Dev-Tools)
[![LangGraph](https://img.shields.io/badge/LangGraph-enabled-purple)](https://www.langchain.com/)

VS Code extension that integrates the code/chef orchestrator into Copilot Chat, enabling AI-powered task automation with 150+ MCP tools.

## Features

- **@codechef Chat Participant** - Submit tasks directly from Copilot Chat
- **LangGraph Workflow Engine** - Single orchestrator with agent nodes and PostgreSQL checkpointing
- **150+ MCP Tools** - LangChain function calling with progressive disclosure (80-90% token savings)
- **Agent Routing** - Routes to specialized agents (feature-dev, code-review, infrastructure, cicd, documentation)
- **Workspace Context** - Automatically extracts git branch, open files, project type
- **HITL Approvals** - Linear integration for human-in-the-loop workflow
- **Observability** - LangSmith tracing + Prometheus metrics

## Quick Start

### 1. Install Extension

From VS Code Marketplace or build locally:

```bash
cd extensions/vscode-codechef
npm install && npm run compile
npx vsce package
code --install-extension vscode-codechef-0.5.0.vsix
```

### 2. Configure

Press `F1` → "code/chef: Configure"

**Required Settings:**

- `codechef.orchestratorUrl` - Orchestrator endpoint (default: `https://codechef.appsmithery.co/api`)
- `codechef.apiKey` - API key for authentication (get from administrator)

### 3. Use in Copilot Chat

Open Copilot Chat (`Ctrl+I`) and type:

```
@codechef Add JWT authentication to my Express API
```

## Commands

### Chat Commands

| Command                                | Description              | Example                         |
| -------------------------------------- | ------------------------ | ------------------------------- |
| `@codechef <task>`                     | Submit development task  | `@codechef Add authentication`  |
| `@codechef /status <id>`               | Check task status        | `@codechef /status abc123`      |
| `@codechef /approve <task> <approval>` | Approve pending task     | `@codechef /approve abc123 xyz` |
| `@codechef /tools`                     | List available MCP tools | `@codechef /tools`              |

### Command Palette (`F1`)

- **code/chef: Submit Task** - Submit via input box
- **code/chef: Check Status** - Check task status
- **code/chef: Configure** - Update settings
- **code/chef: Show Approvals** - Open Linear approval hub
- **code/chef: Clear Cache** - Clear session cache

## Configuration

| Setting                         | Description                | Default                               |
| ------------------------------- | -------------------------- | ------------------------------------- |
| `codechef.orchestratorUrl`      | Orchestrator endpoint      | `https://codechef.appsmithery.co/api` |
| `codechef.apiKey`               | API key for authentication | (required)                            |
| `codechef.linearHubIssue`       | Linear approval hub        | `DEV-68`                              |
| `codechef.linearWorkspaceSlug`  | Linear workspace slug      | `dev-ops`                             |
| `codechef.autoApproveThreshold` | Auto-approve risk level    | `low`                                 |
| `codechef.enableNotifications`  | Toast notifications        | `true`                                |
| `codechef.langsmithUrl`         | LangSmith project URL      | (set)                                 |

### Workspace Settings

Create `.vscode/settings.json`:

```json
{
  "codechef.orchestratorUrl": "https://codechef.appsmithery.co/api",
  "codechef.apiKey": "your-api-key-here",
  "codechef.autoApproveThreshold": "low"
}
```

## Example Workflow

```
@codechef Add user authentication with JWT tokens
```

Response:

```
✅ Task Submitted (abc123)

Subtasks (4):
💻 feature-dev: Implement JWT middleware
💻 feature-dev: Add login/logout endpoints
🔍 code-review: Security audit
📚 documentation: Generate API docs

Estimated Duration: 30 minutes
```

## Approval Workflow

High-risk tasks require human approval via Linear:

1. Task submitted → Risk assessment
2. Sub-issue created under DEV-68
3. User notified via toast/Linear
4. Approve by marking "Done" in Linear
5. Workflow continues

## Troubleshooting

### Cannot connect to orchestrator

1. Check URL: `F1` → "code/chef: Configure"
2. Verify API key is set in settings
3. Test health: `curl https://codechef.appsmithery.co/api/health`

### 401 Unauthorized

API key is missing or invalid:

1. Get API key from administrator
2. Set in VS Code settings: `codechef.apiKey`

### No tools appearing

1. Clear cache: `F1` → "code/chef: Clear Cache"
2. Restart VS Code

## Development

```bash
# Build
npm run compile

# Package
npx vsce package

# Publish to npm
npm publish --ignore-scripts
```

## License

MIT License - see [LICENSE](LICENSE)

## Links

- [GitHub Repository](https://github.com/Appsmithery/Dev-Tools)
- [Linear Project](https://linear.app/project-roadmaps/project/ai-devops-agent-platform-78b3b839d36b)
- [LangSmith Traces](https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects/p/f967bb5e-2e61-434f-8ee1-0df8c22bc046)
