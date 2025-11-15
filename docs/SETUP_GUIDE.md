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

### Optional

- **jq**: For JSON processing in shell scripts
- **PowerShell**: >= 7.0 (for Windows users)

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
