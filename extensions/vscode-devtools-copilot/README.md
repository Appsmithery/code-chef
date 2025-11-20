# Dev-Tools Copilot Extension

VS Code extension that integrates Dev-Tools orchestrator into Copilot Chat, enabling you to submit development tasks to specialized AI agents from any workspace.

## Features

- **@devtools Chat Participant**: Submit tasks directly from Copilot Chat
- **Workspace Context Extraction**: Automatically gathers git branch, open files, project type
- **Multi-Agent Orchestration**: Routes tasks to 6 specialized agents (feature-dev, code-review, infrastructure, cicd, documentation)
- **Real-Time Approvals**: Linear integration for HITL approval workflow
- **Observability**: LangSmith traces and Prometheus metrics integration
- **Session Management**: Multi-turn conversations with context retention

## Quick Start

### 1. Install Extension

```bash
code --install-extension appsmithery.vscode-devtools-copilot
```

### 2. Configure Orchestrator

Press `F1` → "Dev-Tools: Configure" → Enter `http://45.55.173.72:8001`

### 3. Use in Copilot Chat

Open Copilot Chat (Ctrl+I) and type:

```
@devtools Add JWT authentication to my Express API
```

The orchestrator will decompose your task into subtasks and route them to appropriate agents.

## Commands

### Chat Participant Commands

- `@devtools <task>` - Submit development task
- `@devtools /status [task-id]` - Check task status
- `@devtools /approve <task-id> <approval-id>` - Approve pending task
- `@devtools /tools` - List available MCP tools

### Command Palette

- **Dev-Tools: Submit Task** - Submit task via input box
- **Dev-Tools: Check Status** - Check task status via input box
- **Dev-Tools: Configure** - Update orchestrator URL
- **Dev-Tools: Show Approvals** - Open Linear approval hub
- **Dev-Tools: Clear Cache** - Clear session cache

## Configuration

### Settings

- `devtools.orchestratorUrl` - Orchestrator endpoint (default: `http://45.55.173.72:8001`)
- `devtools.mcpGatewayUrl` - MCP gateway endpoint (default: `http://45.55.173.72:8000`)
- `devtools.linearHubIssue` - Linear approval hub issue (default: `PR-68`)
- `devtools.autoApproveThreshold` - Auto-approve risk level (default: `low`)
- `devtools.enableNotifications` - Show toast notifications (default: `true`)
- `devtools.langsmithUrl` - LangSmith project URL for traces

### Workspace Configuration

Create `.vscode/settings.json`:

```json
{
  "devtools.orchestratorUrl": "http://45.55.173.72:8001",
  "devtools.enableNotifications": true,
  "devtools.autoApproveThreshold": "low"
}
```

## Examples

### Basic Task Submission

```
@devtools Add authentication to my API
```

Response:

```
✅ Task Submitted

Task ID: abc123...

Subtasks (4):
💻 feature-dev: Implement JWT middleware
💻 feature-dev: Add login/logout endpoints
🔍 code-review: Security audit
📚 documentation: Generate API docs

Estimated Duration: 30 minutes
```

### Check Task Status

```
@devtools /status abc123
```

Response:

```
Task Status: abc123

Status: in_progress
Progress: 2/4 subtasks

✅ feature-dev: Implement JWT middleware (completed)
🔄 feature-dev: Add login/logout endpoints (in progress)
⏳ code-review: Security audit (pending)
⏳ documentation: Generate API docs (pending)
```

### List MCP Tools

```
@devtools /tools
```

Response shows 150+ tools across 18 MCP servers (memory, context7, notion, linear, terraform, etc.)

## Approval Workflow

High-risk tasks require human approval:

1. **Task Submitted** → Risk assessed by guardrail system
2. **Approval Posted** → Linear issue PR-68 receives notification
3. **User Notified** → Toast notification (if enabled) or status bar indicator
4. **Approve/Reject** → Use `/approve` command or Linear interface
5. **Agents Proceed** → Execution continues after approval

## Observability

All tasks are traced and monitored:

- **LangSmith Traces**: [View Project](https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects/p/f967bb5e-2e61-434f-8ee1-0df8c22bc046)
- **Prometheus Metrics**: http://45.55.173.72:9090
- **Linear Approvals**: https://linear.app/appsmithery/issue/PR-68

## Troubleshooting

### Cannot connect to orchestrator

1. Check URL in settings: `Dev-Tools: Configure`
2. Verify service health: `curl http://45.55.173.72:8001/health`
3. Check firewall allows outbound connections

### No tools appearing

1. Clear cache: `Dev-Tools: Clear Cache`
2. Restart VS Code
3. Check MCP gateway: `curl http://45.55.173.72:8000/health`

### Approval notifications not working

1. Install Linear Connect extension: `linear.linear-vscode`
2. Configure Linear API token in extension settings
3. Subscribe to PR-68 issue in Linear

## Development

### Build from Source

```bash
cd extensions/vscode-devtools-copilot
npm install
npm run compile
```

### Run Extension Development Host

```bash
task dev
# or
code --extensionDevelopmentPath=$(pwd)
```

### Package Extension

```bash
task package
# Creates vscode-devtools-copilot-0.1.0.vsix
```

### Install Locally

```bash
task install-local
```

## Architecture

```
┌─────────────────────────────────────┐
│ VS Code Workspace                    │
│                                      │
│  ┌────────────────────────────────┐ │
│  │ Copilot Chat                   │ │
│  │  @devtools "Add auth to API"  │ │
│  └──────────┬─────────────────────┘ │
│             │                        │
│  ┌──────────▼─────────────────────┐ │
│  │ Dev-Tools Chat Participant     │ │
│  │ - Context extraction           │ │
│  │ - Session management           │ │
│  │ - Linear notifications         │ │
│  └──────────┬─────────────────────┘ │
└─────────────┼───────────────────────┘
              │ HTTP POST
              ▼
┌─────────────────────────────────────┐
│ Dev-Tools Droplet (45.55.173.72)   │
│                                      │
│  ┌────────────────────────────────┐ │
│  │ Orchestrator (:8001)           │ │
│  │ - Task decomposition           │ │
│  │ - Agent routing                │ │
│  │ - Approval workflow            │ │
│  └──────────┬─────────────────────┘ │
│             │                        │
│  ┌──────────▼─────────────────────┐ │
│  │ 6 Specialized Agents           │ │
│  │ feature-dev, code-review, ...  │ │
│  └────────────────────────────────┘ │
└─────────────────────────────────────┘
```

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-capability`
3. Commit changes: `git commit -am 'Add capability'`
4. Push to branch: `git push origin feature/new-capability`
5. Create Pull Request

## License

MIT License - see LICENSE file

## Support

- GitHub Issues: https://github.com/Appsmithery/Dev-Tools/issues
- Linear Project: https://linear.app/appsmithery/project/ai-devops-agent-platform-b21cbaa1-9f09
- Discord: https://discord.gg/appsmithery

## Related

- [Dev-Tools Repository](https://github.com/Appsmithery/Dev-Tools)
- [MCP Bridge Client](https://www.npmjs.com/package/@appsmithery/mcp-bridge-client)
- [Integration Implementation Plan](https://github.com/Appsmithery/Dev-Tools/blob/main/support/docs/INTEGRATION_IMPLEMENTATION_PLAN.md)
