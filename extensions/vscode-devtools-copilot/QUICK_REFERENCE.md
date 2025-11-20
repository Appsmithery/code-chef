# @devtools Quick Reference

## Setup (One-Time)

1. **Install Extension**:

   ```bash
   code --install-extension vscode-devtools-copilot-0.1.0.vsix
   ```

2. **Reload VS Code**: `Ctrl+Shift+P` → "Reload Window"

3. **Configure** (optional): `F1` → "Dev-Tools: Configure"
   - Default: `http://45.55.173.72:8001` (already set)

## Usage

### Basic Commands

| Command                                | Description              | Example                                  |
| -------------------------------------- | ------------------------ | ---------------------------------------- |
| `@devtools <task>`                     | Submit development task  | `@devtools Add authentication to API`    |
| `@devtools /status <id>`               | Check task status        | `@devtools /status abc123`               |
| `@devtools /approve <task> <approval>` | Approve pending task     | `@devtools /approve abc123 approval-456` |
| `@devtools /tools`                     | List available MCP tools | `@devtools /tools`                       |

### Real-World Examples

**Feature Development**:

```
@devtools Implement JWT authentication middleware for Express
```

**Code Review**:

```
@devtools Review my authentication changes for security issues
```

**Infrastructure**:

```
@devtools Add Redis caching layer with Docker Compose
```

**CI/CD**:

```
@devtools Create GitHub Actions workflow for automated testing
```

**Documentation**:

```
@devtools Generate API docs from my Express routes
```

### Task Status

After submitting a task, you'll get:

- ✅ **Task ID**: `abc123-def456-...`
- 📋 **Subtasks**: List of agent assignments
- ⏱️ **Estimated Duration**: Time to completion
- ⚠️ **Approval Status**: If HITL required

Check status anytime:

```
@devtools /status abc123
```

### Approvals

High-risk tasks require approval:

1. **Notification**: Toast or status bar indicator
2. **Review**: Check Linear PR-68 for details
3. **Approve**:
   ```
   @devtools /approve abc123 approval-456
   ```
   Or use Linear interface directly

### Tool Discovery

List all 150+ MCP tools:

```
@devtools /tools
```

**Note**: This command currently returns 404 (PR-118 in progress). Tools are still accessible during task execution.

## Command Palette

| Command                   | Shortcut | Description                |
| ------------------------- | -------- | -------------------------- |
| Dev-Tools: Submit Task    | `F1`     | Submit via input box       |
| Dev-Tools: Check Status   | `F1`     | Check status via input box |
| Dev-Tools: Configure      | `F1`     | Update orchestrator URL    |
| Dev-Tools: Show Approvals | `F1`     | Open Linear PR-68          |
| Dev-Tools: Clear Cache    | `F1`     | Clear session cache        |

## Settings

Access via `F1` → "Preferences: Open Settings" → Search "devtools"

| Setting                | Default                    | Description               |
| ---------------------- | -------------------------- | ------------------------- |
| `orchestratorUrl`      | `http://45.55.173.72:8001` | Orchestrator endpoint     |
| `mcpGatewayUrl`        | `http://45.55.173.72:8000` | MCP gateway endpoint      |
| `linearHubIssue`       | `PR-68`                    | Approval notification hub |
| `autoApproveThreshold` | `low`                      | Auto-approve risk level   |
| `enableNotifications`  | `true`                     | Show toast notifications  |

## Status Bar

Bottom-right corner shows connection status:

- ✅ **Dev-Tools** - Connected
- ⚠️ **Dev-Tools** - Unhealthy
- ❌ **Dev-Tools** - Disconnected

Click to check status or configure.

## Troubleshooting

### Extension Not Working

1. Check installation: `code --list-extensions | grep devtools`
2. Reload window: `Ctrl+Shift+P` → "Reload Window"
3. Check logs: `F1` → "Developer: Show Logs" → "Extension Host"

### Cannot Connect

1. Test endpoint: `curl http://45.55.173.72:8001/health`
2. Check firewall/VPN settings
3. Reconfigure: `F1` → "Dev-Tools: Configure"

### No Approvals

1. Subscribe to Linear PR-68
2. Enable notifications in settings
3. Check Linear Watcher in Output panel

## Observability

### LangSmith Traces

Every task automatically traced:

- Prompts and completions
- Tool invocations
- Token usage and costs
- Latency metrics

**View Traces**: Click LangSmith link in task response or visit:
https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects/p/f967bb5e-2e61-434f-8ee1-0df8c22bc046

### Prometheus Metrics

Agent performance metrics:

- Request rates
- Error rates
- Processing times
- Active tasks

**View Metrics**: http://45.55.173.72:9090

### Linear Approvals

All approval requests posted to:
https://linear.app/project-roadmaps/issue/PR-68

## Tips & Tricks

### Multi-Turn Conversations

Continue refining tasks in same chat:

```
@devtools Add authentication
[response with task ID]

Can you also add password reset functionality?
[orchestrator continues with new subtask]
```

### Context Extraction

Extension automatically sends:

- Git branch and status
- Open files
- Project type (detected)
- Workspace structure

No need to describe your project - agents have full context.

### Progressive Tool Loading

Orchestrator uses keyword-based filtering to load only relevant tools:

- 150+ tools available
- 10-30 tools loaded per task
- 80-90% token savings
- <1s overhead

### Agent Routing

Tasks automatically routed to best agent:

- 💻 **feature-dev**: New features, bug fixes
- 🔍 **code-review**: Security, quality, best practices
- 🏗️ **infrastructure**: Docker, Terraform, cloud resources
- 🚀 **cicd**: GitHub Actions, pipelines, deployments
- 📚 **documentation**: API docs, README, guides

## Example Workflow

```bash
# 1. Open Copilot Chat
Ctrl+I

# 2. Submit complex task
@devtools Add authentication system with JWT, password reset, and email verification

# 3. Review routing plan
# Orchestrator shows:
# - 💻 feature-dev: JWT middleware (30 min)
# - 💻 feature-dev: Password reset flow (20 min)
# - 💻 feature-dev: Email verification (15 min)
# - 🔍 code-review: Security audit (10 min)
# - 📚 documentation: API documentation (10 min)
# Total: ~85 minutes

# 4. Approve if needed
@devtools /approve abc123 approval-456

# 5. Monitor progress
@devtools /status abc123
# Shows: 3/5 complete, 2 in progress

# 6. View traces in LangSmith
# Click link in response or visit dashboard
```

## What's Next?

- 🔄 **PR-118**: Fix `/tools` command (MCP Gateway endpoints)
- 🎨 **Icon**: Add 128x128 PNG for marketplace
- 📸 **Demo**: Record video showing workflow
- 🌐 **Marketplace**: Publish for wider distribution
- 📊 **Analytics**: Collect usage metrics via LangSmith

## Support

- **Docs**: [README.md](./README.md), [DEPLOYMENT.md](./DEPLOYMENT.md)
- **Issues**: https://github.com/Appsmithery/Dev-Tools/issues
- **Linear**: https://linear.app/project-roadmaps/project/ai-devops-agent-platform-78b3b839d36b

---

**Ready to use!** Open Copilot Chat (`Ctrl+I`) and type `@devtools <your task>`
