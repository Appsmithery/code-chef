# Dev-Tools Copilot Extension - Deployment Guide

## ✅ Package Built Successfully

**VSIX**: `vscode-devtools-copilot-0.1.0.vsix` (28.6 KB, 19 files)

## Installation Options

### Option 1: Local Install (Immediate Use)

```bash
# Install from VSIX
code --install-extension vscode-devtools-copilot-0.1.0.vsix

# Verify installation
code --list-extensions | grep devtools
```

**Windows PowerShell:**

```powershell
cd D:\INFRA\Dev-Tools\Dev-Tools\extensions\vscode-devtools-copilot
code --install-extension .\vscode-devtools-copilot-0.1.0.vsix
```

After installation:

1. Reload VS Code (`Ctrl+Shift+P` → "Reload Window")
2. Open Copilot Chat (`Ctrl+I`)
3. Type `@devtools Add JWT authentication to my API`

### Option 2: Workspace Recommendation

Add to `.vscode/extensions.json` in your project:

```json
{
  "recommendations": ["appsmithery.vscode-devtools-copilot"]
}
```

Share the VSIX file with teammates via:

- Internal file share
- GitHub release (private repository)
- Azure DevOps artifacts

### Option 3: VS Code Marketplace (Future)

**Prerequisites:**

1. Create Azure DevOps organization: https://aka.ms/SignupAzureDevOps
2. Generate Personal Access Token (scope: Marketplace → Manage)
3. Create publisher: `vsce create-publisher appsmithery`

**Publish:**

```bash
vsce login appsmithery
vsce publish
```

**Note**: Publishing to public marketplace requires:

- Real icon (128x128 PNG)
- Screenshot/video of extension in action
- Detailed description (minimum 50 words)
- Publisher verification

For now, distribute via VSIX for internal testing.

## Configuration

### First-Time Setup

Press `F1` → "Dev-Tools: Configure Orchestrator URL"

Default configuration:

```json
{
  "devtools.orchestratorUrl": "http://45.55.173.72:8001",
  "devtools.mcpGatewayUrl": "http://45.55.173.72:8000",
  "devtools.linearHubIssue": "PR-68",
  "devtools.enableNotifications": true,
  "devtools.autoApproveThreshold": "low"
}
```

### Network Requirements

Ensure firewall allows outbound connections:

- `45.55.173.72:8001` - Orchestrator API
- `45.55.173.72:8000` - MCP Gateway (for `/tools` command)
- `linear.app` - Approval notifications

Test connectivity:

```bash
curl http://45.55.173.72:8001/health
# Expected: {"status": "ok", "mcp_gateway": "connected"}
```

## Usage Examples

### Submit Development Task

```
@devtools Add authentication middleware to my Express API
```

### Check Task Status

```
@devtools /status abc123-def456-...
```

### List Available Tools

```
@devtools /tools
```

### Approve Pending Task

```
@devtools /approve abc123 approval-456
```

## Troubleshooting

### Extension Not Appearing

1. Check installation: `code --list-extensions`
2. Reload VS Code: `Ctrl+Shift+P` → "Reload Window"
3. Check extension host logs: `Ctrl+Shift+P` → "Developer: Show Logs" → "Extension Host"

### Cannot Connect to Orchestrator

1. Verify URL: `F1` → "Dev-Tools: Configure"
2. Test endpoint: `curl http://45.55.173.72:8001/health`
3. Check firewall/VPN settings
4. View status bar (bottom right): Should show "✓ Dev-Tools"

### No Approval Notifications

1. Subscribe to Linear issue: https://linear.app/appsmithery/issue/PR-68
2. Enable notifications: `F1` → "Preferences: Open Settings (JSON)"
   ```json
   {
     "devtools.enableNotifications": true
   }
   ```
3. Check Linear Watcher connection in Output panel

### /tools Command Returns 404

**Known Issue (PR-118)**: MCP Gateway missing `/tools` endpoint.

**Workaround**: Use orchestrator directly - it has access to all MCP tools during task execution.

**Fix in Progress**: PR-118 - Implement MCP Tool Discovery Endpoints

## Architecture

```
VS Code Workspace
    ↓ (Ctrl+I)
Copilot Chat → @devtools
    ↓ (HTTP POST)
Orchestrator :8001
    ↓ (Routes tasks)
6 Specialized Agents
    ↓ (Observability)
LangSmith + Prometheus
    ↓ (Approvals)
Linear PR-68
```

## Observability

### LangSmith Traces

https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects/p/f967bb5e-2e61-434f-8ee1-0df8c22bc046

All tasks automatically traced:

- Prompts sent to agents
- Tool invocations
- Token usage
- Latency metrics

### Prometheus Metrics

http://45.55.173.72:9090

Query examples:

```promql
# Request rate per agent
rate(http_requests_total[5m])

# Task processing time
histogram_quantile(0.95, http_request_duration_seconds_bucket)

# Active tasks
orchestrator_active_tasks
```

### Linear Approvals

https://linear.app/appsmithery/issue/PR-68

All high-risk tasks post approval requests here with:

- Task description
- Risk assessment
- Estimated impact
- Required actions

## Development

### Build from Source

```bash
cd extensions/vscode-devtools-copilot
npm install
npm run compile
npm run package
```

### Run in Development Mode

```bash
# Open extension development host
code --extensionDevelopmentPath=$(pwd)

# Or use VS Code "Run Extension" (F5)
```

### Update Extension

```bash
# Increment version in package.json
# Rebuild and repackage
npm run compile
npx @vscode/vsce package --allow-missing-repository

# Reinstall
code --install-extension vscode-devtools-copilot-0.1.1.vsix
```

## Related Issues

- ✅ **PR-113**: VS Code Extension (COMPLETE)
- ✅ **PR-114**: MCP Bridge Client Libraries (COMPLETE)
- ✅ **PR-115**: GitHub Packages Publishing (COMPLETE)
- 🔄 **PR-118**: Implement MCP Gateway `/tools` Endpoints (TODO)

## Support

- GitHub Issues: https://github.com/Appsmithery/Dev-Tools/issues
- Linear Project: https://linear.app/appsmithery/project/ai-devops-agent-platform-b21cbaa1-9f09
- Extension README: [README.md](./README.md)

## Next Steps

1. **Install locally** and test with Copilot Chat
2. **Collect feedback** on agent routing and task decomposition
3. **Share VSIX** with team members for beta testing
4. **Complete PR-118** to enable `/tools` command functionality
5. **Add icon** (128x128 PNG) for marketplace publishing
6. **Record demo video** showing end-to-end workflow
7. **Publish to marketplace** once stable

---

**Status**: ✅ Ready for installation  
**Next Task**: Install extension and test `@devtools` in Copilot Chat  
**Blocker**: None (PR-118 optional - doesn't affect core functionality)
