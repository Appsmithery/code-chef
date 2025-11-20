# Quick Start Guide - VS Code Extension

## ✅ Completed Setup

Your VS Code extension is **ready to test**!

### What's Been Built

1. **Extension Core** (6 TypeScript files → compiled to JavaScript)

   - `extension.ts` - Activation/deactivation lifecycle
   - `chatParticipant.ts` - @devtools chat participant handler
   - `orchestratorClient.ts` - HTTP API client
   - `contextExtractor.ts` - Workspace context gathering
   - `sessionManager.ts` - Multi-turn conversation persistence
   - `linearWatcher.ts` - Approval notification polling

2. **Supporting Files**

   - `package.json` - Extension manifest with chat participant registration
   - `README.md` - Full documentation with examples
   - `prompts/system.md` - Participant behavior instructions
   - `Taskfile.yml` - Build automation (15 tasks)
   - `.vscode/launch.json` - Debug configuration
   - `.vscode/tasks.json` - Build tasks

3. **Dependencies Installed** (315 packages)

   - axios (HTTP client)
   - eventsource (SSE for notifications)
   - TypeScript + ESLint + types

4. **Compilation Status**: ✅ Success

   - All 6 TypeScript files compiled to `out/` directory
   - Source maps generated for debugging

5. **Connectivity**: ✅ Healthy
   - Orchestrator: http://45.55.173.72:8001 (responding)
   - MCP Gateway: http://45.55.173.72:8000 (available)

## 🚀 Testing Steps

### 1. Open Extension in VS Code

```powershell
code D:\INFRA\Dev-Tools\Dev-Tools\extensions\vscode-devtools-copilot
```

### 2. Launch Extension Development Host

Press **F5** in VS Code (or Run → Start Debugging)

This opens a new VS Code window with your extension loaded.

### 3. Open Copilot Chat

In the Extension Development Host window:

- Press **Ctrl+I** (or click Copilot icon in sidebar)
- Copilot Chat panel opens

### 4. Test @devtools Participant

Type in Copilot Chat:

```
@devtools Add JWT authentication to my Express API
```

**Expected Response:**

```
✅ Task Submitted

Task ID: abc123-...

Subtasks (4):
💻 feature-dev: Implement JWT middleware
💻 feature-dev: Add login/logout endpoints
🔍 code-review: Security audit
📚 documentation: Generate API docs

Estimated Duration: 30 minutes
```

### 5. Check Task Status

```
@devtools /status abc123
```

**Expected Response:**

```
Task Status: abc123

Status: in_progress
Progress: 2/4 subtasks

✅ feature-dev: Implement JWT middleware (completed)
🔄 feature-dev: Add login/logout endpoints (in progress)
⏳ code-review: Security audit (pending)
⏳ documentation: Generate API docs (pending)
```

### 6. List Available Tools

```
@devtools /tools
```

**Expected Response:**

```
## Available MCP Tools (150+)

### memory (10 tools)
- **memory/read**: Read from persistent memory
- **memory/write**: Write to persistent memory
...

### context7 (15 tools)
- **context7/add_context**: Add context to knowledge base
...
```

### 7. Test Approval Workflow

Submit high-risk task requiring approval:

```
@devtools Drop all tables in production database
```

**Expected Response:**

```
⚠️ Approval Required

Task ID: xyz789-...
Risk Level: HIGH

This task requires manual approval before execution.

Approval request posted to Linear (PR-68).

Use /approve xyz789 to proceed after review.
```

### 8. Verify LangSmith Traces

1. Open [LangSmith Project](https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects/p/f967bb5e-2e61-434f-8ee1-0df8c22bc046)
2. Find trace with your task ID
3. Verify:
   - Task decomposition prompts captured
   - Agent routing decisions logged
   - Token counts tracked
   - Latency measured

## 🐛 Troubleshooting

### Extension Not Showing in Chat

1. Check Output panel → "Extension Host"
2. Look for activation errors
3. Verify `package.json` → `contributes.chatParticipants` registered

### Cannot Connect to Orchestrator

1. Check orchestrator health:
   ```powershell
   Invoke-WebRequest http://45.55.173.72:8001/health
   ```
2. Verify firewall allows outbound connections
3. Update URL in settings: F1 → "Dev-Tools: Configure"

### Context Not Being Extracted

1. Open a workspace with files (not empty folder)
2. Check git is initialized: `git status`
3. Verify extension has filesystem access

### Approvals Not Showing

1. Install Linear Connect extension: `linear.linear-vscode`
2. Configure Linear API token in extension settings
3. Subscribe to PR-68 in Linear workspace
4. Check polling is enabled: `devtools.enableNotifications = true`

## 📦 Packaging (Optional)

### Create VSIX Package

```powershell
cd D:\INFRA\Dev-Tools\Dev-Tools\extensions\vscode-devtools-copilot
npm run package
```

Creates `vscode-devtools-copilot-0.1.0.vsix`

### Install Locally

```powershell
code --install-extension vscode-devtools-copilot-0.1.0.vsix
```

### Publish to Marketplace (Future)

```powershell
# Requires VS Code publisher account
npm run publish
```

## 🔄 Next Steps

1. **Test Extension** (F5 → Copilot Chat → @devtools)
2. **Submit Real Task** (verify end-to-end workflow)
3. **Check LangSmith Traces** (confirm observability)
4. **Build MCP Bridge** (PR-114 - NPM/PyPI packages)
5. **Setup GitHub Packages** (PR-115 - automated publishing)
6. **Create Template Repo** (PR-115 - devtools-project-template)
7. **Write Integration Docs** (PR-116 - quick start guides)
8. **Integration Testing** (PR-117 - sample project validation)

## 📚 Resources

- **Extension Source**: `D:\INFRA\Dev-Tools\Dev-Tools\extensions\vscode-devtools-copilot`
- **Implementation Plan**: `support/docs/INTEGRATION_IMPLEMENTATION_PLAN.md`
- **Linear Roadmap**: [PR-112](https://linear.app/appsmithery/issue/PR-112)
- **LangSmith Project**: [agents](https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects/p/f967bb5e-2e61-434f-8ee1-0df8c22bc046)
- **Orchestrator API**: http://45.55.173.72:8001
- **MCP Gateway**: http://45.55.173.72:8000

## 💡 Tips

- Use `/status [task-id]` frequently to monitor progress
- Check Linear PR-68 for approval notifications
- Use `/tools` to discover available capabilities
- Submit complex tasks - orchestrator will decompose automatically
- LangSmith traces show exact prompts/tokens for debugging
