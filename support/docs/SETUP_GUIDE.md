# Dev-Tools Setup Guide

Complete guide for setting up and using the Dev-Tools diagnostics and automation platform.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Configuration](#environment-configuration)
- [Diagnostics Workflow](#diagnostics-workflow)
- [MCP Server Management](#mcp-server-management)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### Required

- **Node.js**: >= 20.0.0
- **npm**: >= 10.0.0
- **Git**: >= 2.30.0
- **Python**: >= 3.11 (for agent stack with LangChain integration)

### Optional

- **jq**: For JSON processing in shell scripts
- **PowerShell**: >= 7.0 (for Windows users)
- **DigitalOcean doctl**: Required for pushing images to DOCR (Windows shortcut: `pwsh ./scripts/install-doctl.ps1`; macOS: `brew install doctl`)

````bash

### Filetree & Codebase Index

Generate and view the canonical filetree and codebase index:

```bash
# Filetree (outputs to context/_repo-GPS/repo-folder-tree.txt)
brew install node jq

# Codebase index (outputs to docs/CODEBASE_INDEX.md)
````

# Or use the task runner for a full scan

task folder-mapper:scan

````

**Canonical filetree location:**
`context/_repo-GPS/repo-folder-tree.txt`

**Codebase index location:**
`docs/CODEBASE_INDEX.md`

**Ubuntu/Debian**:

```bash
sudo apt-get update
sudo apt-get install nodejs npm jq
````

**Windows** (via Chocolatey):

```powershell
choco install nodejs jq
```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Alextorelli/Dev-Tools.git
cd Dev-Tools
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Build MCP Servers (Optional)

If you plan to use MCP servers:

## Environment Configuration

### 1. Create Environment File

Copy the example environment file:

```bash
cp .env.example .env
```

Or for agent-specific configuration:

```bash
cp .env.example agents/.env.agent.local
```

For the Dockerized agent stack, also copy the runtime template:

```bash
cp config/env/.env.template config/env/.env
```

### 2. Configure Required Variables

Edit `.env` or `agents/.env.agent.local`:

```bash
# Required
NODE_ENV=development

# Recommended - Supabase Configuration
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key

# Recommended - GitHub Configuration
GITHUB_TOKEN=your-github-token

# Recommended - Highlight.io Configuration
HIGHLIGHT_PROJECT_ID=your-highlight-project-id
```

### Environment File Priority

The system loads environment variables in this order (first found wins):

1. `agents/.env.agent.local`
2. `.env.agent.local`
3. `.env`
4. System environment variables

### DigitalOcean Gradient Onboarding

1. **Fill control-plane credentials**
   - Copy `config/env/.env.template` → `config/env/.env`.
   - Populate `DIGITALOCEAN_TOKEN` (or `DIGITAL_OCEAN_PAT`), `GRADIENT_API_KEY`, `GRADIENT_MODEL_ACCESS_KEY`, Langfuse, and Supabase keys.
   - Optional: override `GRADIENT_GENAI_BASE_URL` if you are targeting a non-default endpoint.
2. **Store partner LLM keys**
   - Populate `config/env/secrets/openai_api_key.txt` and/or `config/env/secrets/anthropic_api_key.txt` with the raw vendor keys referenced in the Gradient UI.
   - Add any extra partner secrets to `secrets.template.json` so teammates know which files to create.
3. **Track workspace metadata**
   - Edit `config/env/workspaces/the-shop.json` (or add another manifest) with the actual DigitalOcean Project UUID, model UUIDs, knowledge base IDs, and agent API key targets.
4. **Run the workspace sync script**
   - `python scripts/gradient_workspace_sync.py --dry-run` to preview actions.
   - `python scripts/gradient_workspace_sync.py` to create/update the workspace, attach knowledge bases, mint agent API keys, and write them to `config/env/secrets/agent-access/<workspace>/`.
5. **Distribute agent keys**
   - Share the generated JSON files with whichever service calls the Gradient agent endpoints (or re-run the script to rotate them later).

### DigitalOcean Registry Workflow

1. **Install `doctl`**
   - Windows: `pwsh ./scripts/install-doctl.ps1`
   - macOS: `brew install doctl`
   - Linux: `sudo snap install doctl` or grab the GitHub release tarball.
2. **Validate your token scopes**
   - Run `doctl auth init --context devtools` followed by `doctl account get`. The repo’s shared token already includes the `account:read` scope, so this should succeed unless you deliberately supply a more restrictive PAT.
3. **Build and push images**
   - Execute `pwsh ./scripts/push-docr.ps1` to mint a short-lived Docker credential, build (unless `-SkipBuild`), and push every service with `IMAGE_TAG=<current git sha>`.
   - Use `-Services orchestrator,gateway-mcp` to limit the push set or `-Registry registry.digitalocean.com/<yours>` when testing against another namespace.
4. **Fallback**
   - If PowerShell 7 isn’t available, run the manual commands in `docs/DEPLOYMENT.md` (doctl registry login → docker compose build → docker compose push) and remember to export `IMAGE_TAG`/`DOCR_REGISTRY` yourself.

## Diagnostics Workflow

### Environment Baseline

Run a complete environment diagnostic:

```bash
npm run diagnostics:baseline
```

This executes:

- **Environment validation**: Checks `.env` files and required variables
- **Repository structure scan**: Generates file tree and statistics
- **Package inventory**: Analyzes dependencies and version mismatches
- **Language detection**: Reports code coverage by programming language

**Output Location**: `reports/context/latest/`

### Individual Diagnostic Commands

Run specific diagnostics:

```bash
# Environment only
npm run diagnostics:env

# Repository structure only
npm run diagnostics:structure

# Package inventory only
npm run diagnostics:packages

# Language detection only
npm run diagnostics:languages
```

### Dry Run Mode

Test diagnostics without saving reports:

```bash
node --loader ts-node/esm diagnostics/collect-env.ts --dry-run
```

### Reading Diagnostic Reports

Reports are saved as JSON in `reports/context/latest/`:

```bash
# View environment diagnostics
cat reports/context/latest/env-diagnostics.json | jq

# View repo structure (Markdown)
cat reports/context/latest/repo-structure.md

# View language report
cat reports/context/latest/language-report.json | jq '.languages'
```

## MCP Server Management

### Initialize MCP Servers

Start MCP servers with full diagnostics and health checks:

**Linux/macOS**:

```bash
./scripts/automation/init-mcp.sh
```

**Windows PowerShell**:

```powershell
./scripts/automation/init-mcp.ps1
```

**With Diagnostics**:

```bash
npm run diagnostics:mcp
```

### Check MCP Server Status

```bash
# View status file
cat workspace/runtime/mcp-status.json | jq

# Check server processes
ps aux | grep node | grep mcp
```

### View MCP Server Logs

```bash
# View all logs
ls -la workspace/runtime/logs/

# Tail utility server log
tail -f workspace/runtime/logs/utility.log
```

### Stop MCP Servers

**Linux/macOS**:

```bash
./scripts/automation/reset-mcp.sh
```

**Windows PowerShell**:

```powershell
./scripts/automation/reset-mcp.ps1
```

Options:

- `--no-backup` or `-NoBackup`: Skip log archiving

### Archived Logs

Logs are automatically archived to:

```
workspace/archive/mcp-logs-<timestamp>/
```

## LangChain Tool Binding

The orchestrator implements **progressive tool disclosure with LangChain function calling** to efficiently manage 150+ MCP tools.

### How It Works

**3-Layer Architecture:**

1. **Discovery**: Filter 150+ tools → 10-30 relevant tools (80-90% token reduction)
2. **Conversion**: MCP schemas → LangChain `BaseTool` instances
3. **Binding**: Tools bound to LLM via `bind_tools()` for function calling

**Result:** LLM can **INVOKE** tools via function calling, not just read documentation.

### Verification

Check orchestrator logs for progressive disclosure:

```bash
# View tool loading stats
docker compose logs orchestrator | grep "Progressive"

# Expected output:
# INFO:lib.progressive_mcp_loader:[ProgressiveMCP] Progressive strategy: loaded 4 servers
# INFO:lib.progressive_mcp_loader:[ProgressiveMCP] Minimal strategy: loaded 0 servers
```

### Configuration

Tool loading strategy can be configured per request:

```python
from lib.progressive_mcp_loader import ToolLoadingStrategy

# Options:
# - MINIMAL: Keyword-based (80-95% savings, default)
# - AGENT_PROFILE: Agent manifest-based (60-80% savings)
# - PROGRESSIVE: Minimal + high-priority (70-85% savings)
# - FULL: All 150+ tools (0% savings, debugging)
```

**Documentation:** See `.github/copilot-instructions.md` for tool binding pattern examples.

---

## Context Operations

Dev-Tools provides robust multi-agent context management. You can validate agent context files for schema correctness and compact scratchpads to keep working memory efficient.

### Validate Agent Context Files

Validate all agent context files against the schema:

```bash
npm run context:validate
```

This checks all agent context files in `context/` against the canonical schema (`context/schemas/agent-context.schema.json`). Errors and warnings will be reported in the console.

### Compact Agent Scratchpads

Compact all agent scratchpads (auto-compress old notes, promote summary):

```bash
npm run context:compact
```

This will keep only the most recent notes (default: 80) and promote a summary for older entries.

### Reference

- [ContextManager Quick Reference](../../context/agents/CONTEXTMANAGER_QUICKREF.md)

---

## Troubleshooting

### Diagnostics Issues

**Problem**: `npm run diagnostics:baseline` fails

**Solutions**:

1. Check Node.js version: `node --version` (must be >= 20.0.0)
2. Reinstall dependencies: `rm -rf node_modules && npm install`
3. Run with verbose logging: `npm run diagnostics:env 2>&1 | tee diagnostic.log`

**Problem**: Missing environment variables warning

**Solutions**:

1. Create `.env` file from `.env.example`
2. Configure required variables (see [Environment Configuration](#environment-configuration))
3. Warnings for recommended variables can be safely ignored if not using those features

### MCP Server Issues

**Problem**: MCP servers won't start

**Solutions**:

1. Build MCP servers: `npm run build`
2. Check if servers are already running: `./scripts/automation/reset-mcp.sh`
3. Verify environment variables are set
4. Check logs: `cat workspace/runtime/logs/*.log`

**Problem**: Health check fails

**Solutions**:

1. Wait a few seconds and check again
2. Verify Node.js version compatibility
3. Check system resources (memory, CPU)
4. Review server logs for errors

### Permission Issues

**Problem**: Cannot execute shell scripts

**Solution**:

```bash
chmod +x scripts/automation/*.sh
```

### TypeScript Errors

**Problem**: TypeScript compilation errors

**Solutions**:

1. Install TypeScript: `npm install -D typescript`
2. Verify tsconfig.json is present
3. Check Node.js version compatibility

## Next Steps

After setup:

1. **Run diagnostics** to establish baseline: `npm run diagnostics:baseline`
2. **Review reports** in `reports/context/latest/`
3. **Initialize MCP servers** (if needed): `./scripts/automation/init-mcp.sh`
4. **Integrate with your project** (see docs/standalone/GETTING_STARTED.md)

## Additional Resources

- [DOCUMENTATION_INDEX.md](./DOCUMENTATION_INDEX.md) - Complete documentation index
- [docs/standalone/GETTING_STARTED.md](./docs/standalone/GETTING_STARTED.md) - Integration guide
- [README.md](../README.md) - Project overview
- [CHANGELOG.md](../CHANGELOG.md) - Version history

## Support

For issues or questions:

1. Check existing issues: https://github.com/Alextorelli/Dev-Tools/issues
2. Review troubleshooting guide above
3. Create a new issue with diagnostic output

---

**Version**: 1.1.0
**Last Updated**: 2025-11-02
