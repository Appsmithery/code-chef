# code/chef Multi-Agent DevOps Team

[![Orchestrator](https://img.shields.io/badge/orchestrator-LangGraph-blue)](https://github.com/Appsmithery/code/chef)
[![MCP Tools](https://img.shields.io/badge/tools-150%2B-green)](https://github.com/Appsmithery/code/chef/tree/main/shared/mcp/servers)
[![LangChain](https://img.shields.io/badge/LangChain-enabled-purple)](https://www.langchain.com/)

VS Code extension that integrates the head codechef orchestrator into Copilot Chat, enabling you to submit development tasks with LangChain-powered subagents, function calling and progressive tool disclosure from any workspace.

## Features

- **@codechef Chat Participant**: Submit tasks directly from Copilot Chat with natural language
- **LangGraph Workflow Engine**: Single orchestrator with internal agent nodes and PostgreSQL checkpointing
- **LangChain Function Calling**: Orchestrator can INVOKE 150+ MCP tools via LangChain's native tool binding
- **Progressive Tool Disclosure**: 80-90% token reduction through intelligent tool filtering (minimal/agent_profile/progressive/full strategies)
- **Agent Node Routing**: Routes tasks to internal agent nodes (feature-dev, code-review, infrastructure, cicd, documentation)
- **Workspace Context Extraction**: Automatically gathers git branch, open files, project type
- **Real-Time Approvals**: Linear integration for HITL approval workflow (<1s notification latency)
- **Observability**: LangSmith LLM tracing + Prometheus HTTP metrics
- **Session Management**: PostgreSQL-backed multi-turn conversations with workflow state retention

## Quick Start

### 1. Install Extension

```bash
code --install-extension appsmithery.vscode-devtools-copilot
```

### 2. Configure Orchestrator

Press `F1` → "code/chef: Configure" → Enter `https://codechef.appsmithery.co/api`

### 3. Use in Copilot Chat

Open Copilot Chat (Ctrl+I) and type:

```
@codechef Add JWT authentication to my Express API
```

The orchestrator will decompose your task into subtasks and route them to appropriate agents.

## Commands

### Chat Participant Commands

- `@codechef <task>` - Submit development task
- `@codechef /status [task-id]` - Check task status
- `@codechef /approve <task-id> <approval-id>` - Approve pending task
- `@codechef /tools` - List available MCP tools

### Command Palette

- **code/chef: Submit Task** - Submit task via input box
- **code/chef: Check Status** - Check task status via input box
- **code/chef: Configure** - Update orchestrator URL
- **code/chef: Show Approvals** - Open Linear approval hub
- **code/chef: Clear Cache** - Clear session cache

## Configuration

### Settings

- `codechef.orchestratorUrl` - Orchestrator endpoint (default: `https://codechef.appsmithery.co/api`)
- `codechef.mcpGatewayUrl` - MCP gateway endpoint (default: `https://codechef.appsmithery.co/api`)
- `codechef.linearHubIssue` - Linear approval hub issue (default: `DEV-68`)
- `codechef.linearWorkspaceSlug` - Linear workspace slug for approval links (default: `dev-ops`)
- `codechef.autoApproveThreshold` - Auto-approve risk level (default: `low`)
- `codechef.enableNotifications` - Show toast notifications (default: `true`)
- `codechef.langsmithUrl` - LangSmith project URL for traces

### Workspace Configuration

Create `.vscode/settings.json`:

```json
{
  "codechef.orchestratorUrl": "https://codechef.appsmithery.co/api",
  "codechef.enableNotifications": true,
  "codechef.autoApproveThreshold": "low"
}
```

## Examples

### Basic Task Submission

```
@codechef Add authentication to my API
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
@codechef /status abc123
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
@codechef /tools
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
- **Prometheus Metrics**: https://codechef.appsmithery.co
- **Linear Approvals**: https://linear.app/dev-ops/issue/DEV-68 (HITL Approvals Hub with sub-issues)

## Troubleshooting

### Cannot connect to orchestrator

1. Check URL in settings: `code/chef: Configure`
2. Verify service health: `curl https://codechef.appsmithery.co/api/health`
3. Check firewall allows outbound connections

### No tools appearing

1. Clear cache: `code/chef: Clear Cache`
2. Restart VS Code
3. Check MCP gateway: `curl https://codechef.appsmithery.co/api/health`

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
│  │  @codechef "Add auth to API"  │ │
│  └──────────┬─────────────────────┘ │
│             │                        │
│  ┌──────────▼─────────────────────┐ │
│  │ code/chef Chat Participant     │ │
│  │ - Context extraction           │ │
│  │ - Session management           │ │
│  │ - Linear notifications         │ │
│  └──────────┬─────────────────────┘ │
└─────────────┼───────────────────────┘
              │ HTTP POST
              ▼
┌──────────────────────────────────────────────────────────────┐
│ code/chef Droplet (codechef.appsmithery.co)                             │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ LangGraph Orchestrator (:8001)                          │ │
│  │ ┌─────────────────────────────────────────────────────┐ │ │
│  │ │ LangChain Tool Binding (3-Layer Architecture)       │ │ │
│  │ │ 1. Discovery: progressive_mcp_loader.py             │ │ │
│  │ │    (150+ tools → 10-30 relevant, 80-90% saved)      │ │ │
│  │ │ 2. Conversion: mcp_client.to_langchain_tools()      │ │ │
│  │ │    (MCP schemas → LangChain BaseTool instances)     │ │ │
│  │ │ 3. Binding: llm.bind_tools(tools)                   │ │ │
│  │ │    (LLM can INVOKE tools via function calling)      │ │ │
│  │ └─────────────────────────────────────────────────────┘ │ │
│  │ ┌─────────────────────────────────────────────────────┐ │ │
│  │ │ LangGraph StateGraph (Workflow Engine)              │ │ │
│  │ │ - Task decomposition node                           │ │ │
│  │ │ - Supervisor node (routing logic)                   │ │ │
│  │ │ - 5 Agent nodes (internal workflow steps):          │ │ │
│  │ │   • feature-dev (codellama-13b)                     │ │ │
│  │ │   • code-review (llama-3.1-70b)                     │ │ │
│  │ │   • infrastructure (llama-3.1-8b)                   │ │ │
│  │ │   • cicd (llama-3.1-8b)                             │ │ │
│  │ │   • documentation (mistral-7b)                      │ │ │
│  │ │ - Approval gate node (HITL workflow interrupts)     │ │ │
│  │ │ - PostgreSQL checkpointing (workflow state)         │ │ │
│  │ └─────────────────────────────────────────────────────┘ │ │
│  └───────────┬─────────────────────────────────────────────┘ │
│              │                                                │
│  ┌───────────▼──────────────────────────────────────────┐    │
│  │ MCP Gateway (:8000)                                  │    │
│  │ - 17 MCP servers, 150+ tools                         │    │
│  │ - Stdio communication with orchestrator              │    │
│  └──────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────┘
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

- GitHub Issues: https://github.com/Appsmithery/code/chef/issues
- Linear Project: https://linear.app/project-roadmaps/project/ai-devops-agent-platform-78b3b839d36b
- Discord: https://discord.gg/appsmithery

## Related

### Documentation

- [code/chef Repository](https://github.com/Appsmithery/code/chef)
- [Progressive Tool Disclosure Architecture](https://github.com/Appsmithery/code/chef/blob/main/support/docs/PROGRESSIVE_TOOL_DISCLOSURE.md)
- [Linear Integration Guide](https://github.com/Appsmithery/code/chef/blob/main/support/docs/LINEAR_INTEGRATION_GUIDE.md)
- [Linear HITL Workflow](https://github.com/Appsmithery/code/chef/blob/main/support/docs/LINEAR_HITL_WORKFLOW.md)
- [Deployment Guide](https://github.com/Appsmithery/code/chef/blob/main/support/docs/DEPLOYMENT_GUIDE.md)

### Integrations

- [LangChain LLM Framework](https://www.langchain.com/)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [DigitalOcean Gradient AI](https://docs.digitalocean.com/products/ai/)
- [LangSmith LLM Observability](https://smith.langchain.com/)

### Packages

- [MCP Bridge Client](https://www.npmjs.com/package/@appsmithery/mcp-bridge-client)
