# Dev-Tools Multi-Agent Orchestrator

[![Agents](https://img.shields.io/badge/agents-6-blue)](https://github.com/Appsmithery/Dev-Tools)
[![MCP Tools](https://img.shields.io/badge/tools-150%2B-green)](https://github.com/Appsmithery/Dev-Tools/tree/main/shared/mcp/servers)
[![LangChain](https://img.shields.io/badge/LangChain-enabled-purple)](https://www.langchain.com/)

VS Code extension that integrates Dev-Tools orchestrator into Copilot Chat, enabling you to submit development tasks to specialized AI agents with LangChain-powered function calling and progressive tool disclosure from any workspace.

## Features

- **@devtools Chat Participant**: Submit tasks directly from Copilot Chat with natural language
- **LangChain Function Calling**: Agents can INVOKE 150+ MCP tools via LangChain's native tool binding
- **Progressive Tool Disclosure**: 80-90% token reduction through intelligent tool filtering (minimal/agent_profile/progressive/full strategies)
- **Multi-Agent Orchestration**: Routes tasks to 6 specialized agents (feature-dev, code-review, infrastructure, cicd, documentation)
- **Workspace Context Extraction**: Automatically gathers git branch, open files, project type
- **Real-Time Approvals**: Linear integration for HITL approval workflow (<1s notification latency)
- **Observability**: LangSmith LLM tracing + Prometheus HTTP metrics across all agents
- **Session Management**: PostgreSQL-backed multi-turn conversations with context retention

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
- `devtools.linearHubIssue` - Linear approval hub issue (default: `DEV-68`)
- `devtools.linearWorkspaceSlug` - Linear workspace slug for approval links (default: `dev-ops`)
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

Response shows 150+ tools across 17 MCP servers:

- **Development**: filesystem, github, gitlab, sequential-thinking
- **Infrastructure**: docker (containaier), terraform, kubernetes, prometheus
- **Documentation**: notion, context7, docs-langchain
- **Memory**: mcp-memory, everything
- **Database**: postgres, sqlite
- **Productivity**: linear, slack, gmail
- **AI**: fetch (web scraping)

**Progressive Disclosure**: Only relevant tools (10-30) are loaded per task for 80-90% token savings while maintaining full tool invocation capability via LangChain function calling.

## Approval Workflow

High-risk tasks require human approval:

1. **Task Submitted** → Risk assessed by guardrail system
2. **Sub-Issue Created** → Linear creates sub-issue under DEV-68 (HITL Approvals Hub) using agent-specific template
3. **User Notified** → Toast notification (if enabled) or status bar indicator with Linear link
4. **Approve/Reject** → Change Linear sub-issue status to "Done" (approved) or "Canceled" (rejected)
5. **Agents Proceed** → Execution continues after approval

**Linear Integration:**

- Parent Hub: [DEV-68](https://linear.app/dev-ops/issue/DEV-68)
- Sub-issues include: Risk level emoji, task description, metadata, timestamp
- Templates: `HITL_ORCHESTRATOR_TEMPLATE_UUID` (and per-agent variants)

## Observability

All tasks are traced and monitored:

- **LangSmith Traces**: [View Project](https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects/p/f967bb5e-2e61-434f-8ee1-0df8c22bc046)
- **Prometheus Metrics**: http://45.55.173.72:9090
- **Linear Approvals**: https://linear.app/dev-ops/issue/DEV-68 (HITL Approvals Hub with sub-issues)

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

1. Verify Linear OAuth token configured: `LINEAR_API_KEY` in `.env`
2. Check HITL templates configured: `HITL_ORCHESTRATOR_TEMPLATE_UUID`, etc.
3. Subscribe to DEV-68 issue in Linear for sub-issue notifications
4. Verify approval hub setting: `LINEAR_APPROVAL_HUB_ISSUE_ID=DEV-68` (note: PR-68 is internal reference, DEV-68 is public identifier)

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
┌─────────────────────────────────────────────────────────┐
│ Dev-Tools Droplet (45.55.173.72)                        │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Orchestrator (:8001)                               │ │
│  │ ┌────────────────────────────────────────────────┐ │ │
│  │ │ LangChain Tool Binding (3-Layer Architecture)  │ │ │
│  │ │ 1. Discovery: progressive_mcp_loader.py        │ │ │
│  │ │    (150+ tools → 10-30 relevant, 80-90% saved) │ │ │
│  │ │ 2. Conversion: mcp_client.to_langchain_tools() │ │ │
│  │ │    (MCP schemas → LangChain BaseTool instances)│ │ │
│  │ │ 3. Binding: llm.bind_tools(tools)              │ │ │
│  │ │    (LLM can INVOKE tools via function calling) │ │ │
│  │ └────────────────────────────────────────────────┘ │ │
│  │ - Task decomposition                               │ │
│  │ - Agent routing                                    │ │
│  │ - Approval workflow                                │ │
│  └──────────┬─────────────────────────────────────────┘ │
│             │                                            │
│  ┌──────────▼───────────────────────────────────────┐   │
│  │ MCP Gateway (:8000)                              │   │
│  │ - 17 MCP servers, 150+ tools                     │   │
│  │ - Stdio communication                            │   │
│  └──────────┬───────────────────────────────────────┘   │
│             │                                            │
│  ┌──────────▼───────────────────────────────────────┐   │
│  │ 6 Specialized Agents (:8002-:8006)               │   │
│  │ - feature-dev (codellama-13b)                    │   │
│  │ - code-review (llama-3.1-70b)                    │   │
│  │ - infrastructure (llama-3.1-8b)                  │   │
│  │ - cicd (llama-3.1-8b)                            │   │
│  │ - documentation (mistral-7b)                     │   │
│  │ Each with MCP client + LangChain tool binding    │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
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
- Linear Project: https://linear.app/project-roadmaps/project/ai-devops-agent-platform-78b3b839d36b
- Discord: https://discord.gg/appsmithery

## Related

### Documentation

- [Dev-Tools Repository](https://github.com/Appsmithery/Dev-Tools)
- [Progressive Tool Disclosure Architecture](https://github.com/Appsmithery/Dev-Tools/blob/main/support/docs/PROGRESSIVE_TOOL_DISCLOSURE.md)
- [Integration Implementation Plan](https://github.com/Appsmithery/Dev-Tools/blob/main/support/docs/INTEGRATION_IMPLEMENTATION_PLAN.md)
- [Setup Guide](https://github.com/Appsmithery/Dev-Tools/blob/main/support/docs/SETUP_GUIDE.md)

### Integrations

- [LangChain LLM Framework](https://www.langchain.com/)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [DigitalOcean Gradient AI](https://docs.digitalocean.com/products/ai/)
- [LangSmith LLM Observability](https://smith.langchain.com/)

### Packages

- [MCP Bridge Client](https://www.npmjs.com/package/@appsmithery/mcp-bridge-client)
