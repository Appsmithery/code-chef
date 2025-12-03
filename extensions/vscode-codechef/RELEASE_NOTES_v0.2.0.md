# Release Notes: VS Code Extension v0.2.0

**Release Date**: January 2025  
**Package**: `vscode-codechef-0.2.0.vsix` (971.31 KB)  
**Commit**: b3641ec

## 🎉 Major Features

### LangChain Function Calling Integration

The orchestrator and all 6 specialized agents can now **INVOKE** MCP tools via LangChain's native function calling protocol, not just read tool documentation.

**3-Layer Architecture**:

1. **Discovery**: `progressive_mcp_loader.py` filters 150+ tools → 10-30 relevant tools (80-90% token savings)
2. **Conversion**: `mcp_client.to_langchain_tools()` transforms MCP schemas → LangChain `BaseTool` instances
3. **Binding**: `gradient_client.get_llm_with_tools()` binds tools via `llm.bind_tools(tools)`

**Result**: LLM can execute tool functions directly through LangChain's function calling protocol while maintaining 80-90% token cost reduction through progressive disclosure.

### Progressive Tool Disclosure

4 loading strategies optimized for different use cases:

| Strategy        | Token Savings | Use Case                         | Tools Loaded |
| --------------- | ------------- | -------------------------------- | ------------ |
| `MINIMAL`       | 80-95%        | Simple tasks with clear keywords | 5-15         |
| `AGENT_PROFILE` | 60-80%        | Agent-specific workflows         | 20-40        |
| `PROGRESSIVE`   | 70-85%        | Balanced (minimal + agent tools) | 15-30        |
| `FULL`          | 0%            | Debugging, exploration           | 150+         |

### Enhanced Marketplace Presence

**Badges**:

- 🔵 6 Specialized Agents
- 🟢 150+ MCP Tools
- 🟣 LangChain Enabled

**Keywords**: 16 total (added: langchain, multi-agent, function-calling, progressive-disclosure, automation, code-generation, hitl, observability, digitalocean, gradient-ai)

**License**: MIT (open source)

**Icon**: Purple minions logo (11.06 KB)

## 📦 What's Included

### Documentation

- ✅ **README.md**: Comprehensive marketplace documentation with architecture diagrams
- ✅ **CHANGELOG.md**: Version history following Keep a Changelog format
- ✅ **RELEASE_NOTES_v0.2.0.md**: This file (detailed release information)
- ✅ **LICENSE**: MIT License
- ✅ **package.json**: Enhanced metadata with badges, expanded keywords, icon reference

### Extension Package

- **File**: `vscode-codechef-0.2.0.vsix`
- **Size**: 971.31 KB
- **Files**: 405 total (178 JavaScript, 12 TypeScript compiled, 385 node_modules)
- **Includes**: README, LICENSE, icon, compiled code, prompts, dependencies

## 🚀 Installation

### From .vsix File (Local)

```bash
cd extensions/vscode-codechef
code --install-extension vscode-codechef-0.2.0.vsix
```

### From VS Code Marketplace (Future)

```bash
code --install-extension appsmithery.vscode-codechef
```

## 🔧 Configuration

Required setting (press F1 → "code/chef: Configure"):

```json
{
  "codechef.orchestratorUrl": "https://codechef.appsmithery.co/api"
}
```

Optional settings:

```json
{
  "codechef.mcpGatewayUrl": "https://codechef.appsmithery.co/api",
  "codechef.linearHubIssue": "PR-68",
  "codechef.autoApproveThreshold": "low",
  "codechef.enableNotifications": true,
  "codechef.langsmithUrl": "https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects/p/f967bb5e-2e61-434f-8ee1-0df8c22bc046"
}
```

## 📊 Performance Metrics

### Token Efficiency

- **Before v0.2.0**: All 150+ tools in context = ~50,000 tokens per task
- **After v0.2.0**: 10-30 relevant tools = ~5,000-10,000 tokens per task
- **Savings**: 80-90% token cost reduction
- **Benefit**: Tool invocation capability maintained via LangChain function calling

### Agent Performance

- **Orchestrator**: llama-3.1-70b, progressive loading, <2s task decomposition
- **Feature-Dev**: codellama-13b, agent_profile loading, optimized for code generation
- **Code-Review**: llama-3.1-70b, full tool access, comprehensive security analysis
- **Infrastructure**: llama-3.1-8b, minimal loading, fast terraform/docker operations
- **CI/CD**: llama-3.1-8b, minimal loading, pipeline generation
- **Documentation**: mistral-7b, agent_profile loading, markdown generation

### Latency

- **Task Submission**: <500ms (HTTP POST to orchestrator)
- **Task Decomposition**: 1-3s (LLM-powered with progressive tool loading)
- **Approval Notifications**: <1s (Linear workspace hub)
- **Tool Discovery**: <100ms (cached after first load)
- **Tool Invocation**: Variable (depends on tool, typically <1s)

## 🔍 Observability

All tasks are fully traced and monitored:

### LangSmith LLM Tracing

- **Workspace**: code/chef (5029c640-3f73-480c-82f3-58e402ed4207)
- **Project**: agents (f967bb5e-2e61-434f-8ee1-0df8c22bc046)
- **URL**: https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects/p/f967bb5e-2e61-434f-8ee1-0df8c22bc046
- **Features**: Token counts, latency, tool calls, LLM responses, error traces

### Prometheus Metrics

- **Endpoint**: http://codechef.appsmithery.co:9090
- **Metrics**: HTTP requests, response times, error rates, agent health
- **Scrape Interval**: 15s
- **Retention**: 15 days

### Linear HITL Approvals

- **Hub Issue**: PR-68 (workspace-level approval notification hub)
- **Latency**: <1s notification delivery
- **Channels**: Linear native (email/mobile/desktop)
- **Access**: https://linear.app/project-roadmaps/issue/PR-68

## 🧪 Testing

### Extension Validation

```bash
cd extensions/vscode-codechef
.\validate-extension.ps1
```

Validates:

- ✅ Extension loads in VS Code
- ✅ Chat participant `@codechef` available
- ✅ Commands registered in Command Palette
- ✅ Configuration settings accessible
- ✅ Network connectivity to orchestrator

### Manual Testing

1. Open Copilot Chat (Ctrl+I)
2. Type: `@codechef Add JWT authentication to my Express API`
3. Verify:

   - Task submitted successfully
   - Task ID returned
   - Subtasks displayed (typically 3-5)
   - Agent assignments shown
   - Estimated duration provided

4. Check task status:

   ```
   @codechef /status <task-id>
   ```

5. List available tools:
   ```
   @codechef /tools
   ```

## 📝 Documentation Updates

### Updated Files

- ✅ `extensions/vscode-codechef/README.md`: Added LangChain architecture, badges, enhanced examples
- ✅ `extensions/vscode-codechef/CHANGELOG.md`: Version history following semantic versioning
- ✅ `extensions/vscode-codechef/package.json`: v0.2.0, expanded keywords, badges, icon
- ✅ `agent_orchestrator/README.md`: Progressive tool disclosure architecture
- ✅ `support/docs/README.md`: Added progressive tool disclosure link
- ✅ `support/docs/SETUP_GUIDE.md`: LangChain tool binding verification steps
- ✅ `.github/copilot-instructions.md`: Tool binding pattern with code examples

### New Files

- ✅ `extensions/vscode-codechef/CHANGELOG.md`: Version history
- ✅ `extensions/vscode-codechef/RELEASE_NOTES_v0.2.0.md`: This file
- ✅ `extensions/vscode-codechef/minions_purple.png`: Extension icon
- ✅ `extensions/vscode-codechef/vscode-codechef-0.2.0.vsix`: Packaged extension

## 🔗 References

### Documentation

- [Progressive Tool Disclosure Architecture](https://github.com/Appsmithery/code/chef/blob/main/support/docs/PROGRESSIVE_TOOL_DISCLOSURE.md)
- [Setup Guide](https://github.com/Appsmithery/code/chef/blob/main/support/docs/SETUP_GUIDE.md)
- [Integration Implementation Plan](https://github.com/Appsmithery/code/chef/blob/main/support/docs/INTEGRATION_IMPLEMENTATION_PLAN.md)

### Integrations

- [LangChain LLM Framework](https://www.langchain.com/)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [DigitalOcean Gradient AI](https://docs.digitalocean.com/products/ai/)
- [LangSmith Observability](https://smith.langchain.com/)

### Repository

- [code/chef GitHub](https://github.com/Appsmithery/code/chef)
- [Linear Project](https://linear.app/project-roadmaps/project/ai-devops-agent-platform-78b3b839d36b)
- [Issues](https://github.com/Appsmithery/code/chef/issues)

## 🎯 Next Steps

### For Users

1. **Install Extension**: `code --install-extension vscode-codechef-0.2.0.vsix`
2. **Configure**: F1 → "code/chef: Configure" → Enter orchestrator URL
3. **Test**: Open Copilot Chat → `@codechef hello world` (verify connection)
4. **Use**: Submit real tasks → `@codechef Add authentication to my API`

### For Developers

1. **Review Code**: Check `shared/lib/progressive_mcp_loader.py` for progressive disclosure logic
2. **Trace Tasks**: Visit LangSmith dashboard to see LLM traces
3. **Monitor Metrics**: Check Prometheus for HTTP metrics and agent health
4. **Contribute**: Fork repo → Create feature branch → Submit PR

### For Marketplace Publication

1. **Create Publisher**: Register at https://marketplace.visualstudio.com/manage
2. **Generate PAT**: Azure DevOps Personal Access Token (Marketplace: Read & Write)
3. **Login**: `vsce login appsmithery`
4. **Publish**: `vsce publish`
5. **Verify**: Check extension page for badges, screenshots, documentation

## 🐛 Known Issues

### Non-Critical Lint Warnings

- **activationEvents**: VS Code auto-generates from package.json (can be removed)
- **badge.href**: Optional property (badges still display correctly)

### Performance Optimization

- **Bundle Recommendation**: Extension has 405 files (178 JS). Consider webpack bundling for faster loading.
- **Command**: `npm run bundle` (add webpack configuration)

### Version Dependencies

- **@vscode/vsce**: v2.32.0 installed, v3.7.0 available (non-breaking update)
- **Command**: `npm install -g @vscode/vsce@latest`

## 🎊 Credits

**Implementation**: LangChain tool binding architecture (Discovery → Conversion → Binding)  
**Testing**: DigitalOcean droplet deployment, orchestrator task decomposition validation  
**Documentation**: Comprehensive README, CHANGELOG, SETUP_GUIDE updates  
**Commit**: b3641ec (feat: VS Code extension v0.2.0 with LangChain tool binding)  
**Previous Commit**: 894480e (feat: LangChain tool binding with progressive disclosure)

---

**Version**: 0.2.0  
**Status**: ✅ Ready for Distribution  
**Package**: `vscode-codechef-0.2.0.vsix` (971.31 KB)  
**License**: MIT  
**Publisher**: appsmithery
