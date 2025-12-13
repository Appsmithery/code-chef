---
status: active
category: getting-started
last_updated: 2025-12-09
---

# code/chef Quick Start Guide

Get up and running with code/chef in 5 minutes.

---

## Option A: VS Code Extension Only (Recommended)

Use the hosted code/chef service—no server setup required.

### Step 1: Install the Extension

**Quick Install (Recommended)**:

Download and install the latest version in one command:

**Bash/Linux/macOS:**

```bash
curl -L https://github.com/Appsmithery/code-chef/releases/latest/download/vscode-codechef-1.0.0.vsix -o codechef.vsix && code --install-extension codechef.vsix
```

**PowerShell/Windows:**

```powershell
curl -L https://github.com/Appsmithery/code-chef/releases/latest/download/vscode-codechef-1.0.0.vsix -o codechef.vsix; code --install-extension codechef.vsix
```

**Manual Install from GitHub Releases**:

1. Go to [Releases](https://github.com/Appsmithery/code-chef/releases)
2. Download the latest `vscode-codechef-*.vsix` file
3. In VS Code: `Ctrl+Shift+P` → **Extensions: Install from VSIX...**
4. Select the downloaded file and reload VS Code

**Update Existing Installation**:

**Bash/Linux/macOS:**

```bash
code --uninstall-extension appsmithery.vscode-codechef && curl -L https://github.com/Appsmithery/code-chef/releases/latest/download/vscode-codechef-1.0.0.vsix -o codechef.vsix && code --install-extension codechef.vsix
```

**PowerShell/Windows:**

```powershell
code --uninstall-extension appsmithery.vscode-codechef; curl -L https://github.com/Appsmithery/code-chef/releases/latest/download/vscode-codechef-1.0.0.vsix -o codechef.vsix; code --install-extension codechef.vsix
```

**From VS Code Marketplace** (Coming Soon):

1. Open Extensions (`Ctrl+Shift+X`)
2. Search "code/chef"
3. Click Install

### Step 2: Configure

1. Press `Ctrl+Shift+P` → "code/chef: Configure"
2. Enter your API key (get from your administrator)
3. Leave the default URL unless self-hosting

### Step 3: Start Cooking

Open Copilot Chat and try:

```
@chef Build a REST API for user management with JWT auth
```

That's it! The AI team handles the rest.

---

## Option B: Self-Hosted (Full Control)

Run your own code/chef orchestrator for complete customization.

### Prerequisites

- Docker Desktop with [MCP Toolkit](https://docs.docker.com/desktop/features/mcp-toolkit/)
- Git

### Step 1: Clone & Configure

```bash
git clone https://github.com/Appsmithery/code-chef.git
cd code-chef

# Copy environment template
cp config/env/.env.template config/env/.env
```

### Step 2: Add Your API Keys

Edit `config/env/.env`:

```bash
# Required - Choose your LLM provider
OPENROUTER_API_KEY=sk-or-v1-your-key    # Get from openrouter.ai (recommended)
# OR
GRADIENT_API_KEY=dop_v1_your-key        # Get from DigitalOcean

# Required for issue tracking
LINEAR_API_KEY=lin_api_your-key         # Get from linear.app/settings/api

# Optional - Enhanced observability
LANGSMITH_API_KEY=lsv2_sk_your-key      # Get from smith.langchain.com
```

### Step 3: Start Services

```bash
cd deploy
docker-compose up -d
```

### Step 4: Verify Health

```bash
curl http://localhost:8001/health
```

Expected response:

```json
{ "status": "healthy", "version": "0.5.0" }
```

### Step 5: Connect VS Code

1. Install the extension (see Option A, Step 1)
2. Configure: `Ctrl+Shift+P` → "code/chef: Configure"
3. Set URL to `http://localhost:8001/api`
4. Start using `@chef` in Copilot Chat

---

## Environment Variables Reference

| Variable               | Required | Description                             |
| ---------------------- | -------- | --------------------------------------- |
| `OPENROUTER_API_KEY`   | Yes\*    | OpenRouter API key (recommended)        |
| `GRADIENT_API_KEY`     | Yes\*    | DigitalOcean Gradient key (alternative) |
| `LINEAR_API_KEY`       | Yes      | Linear.app API key for issue tracking   |
| `LANGSMITH_API_KEY`    | No       | LangSmith for LLM tracing               |
| `QDRANT_API_KEY`       | No       | Qdrant Cloud for semantic search        |
| `ORCHESTRATOR_API_KEY` | No       | API key for authenticated access        |

\*At least one LLM provider key is required.

---

## Service Ports

| Service       | Port | Purpose              |
| ------------- | ---- | -------------------- |
| Orchestrator  | 8001 | Main API             |
| RAG Context   | 8007 | Semantic search      |
| State Service | 8008 | Workflow persistence |
| PostgreSQL    | 5432 | Database             |

---

## First Commands to Try

| Command                                            | What it does           |
| -------------------------------------------------- | ---------------------- |
| `@chef Add dark mode to my app`                    | Feature implementation |
| `@chef Review this code for security issues`       | Code review            |
| `@chef Write tests for the UserService class`      | Test generation        |
| `@chef Create a GitHub Actions workflow for CI/CD` | Pipeline setup         |
| `@chef Document the API endpoints`                 | Documentation          |

---

## Production Deployment

For production setup on DigitalOcean or other cloud providers:

```powershell
# Auto-detect changes and deploy
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType auto

# Config-only (30s - for .env changes)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config

# Full rebuild (10min - for code changes)
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType full
```

See [deployment.md](deployment.md) for complete production setup.

---

## Troubleshooting

### "Cannot connect to orchestrator"

1. Check the URL in settings: `Ctrl+Shift+P` → "code/chef: Configure"
2. For self-hosted: ensure services are running (`docker-compose ps`)
3. Test connection: `curl http://your-url/health`

### "401 Unauthorized"

1. Check your API key is set correctly
2. For hosted service, contact your administrator

### "No response from @chef"

1. Clear cache: `Ctrl+Shift+P` → "code/chef: Clear Cache"
2. Restart VS Code
3. Check the Output panel for errors

### Environment Variables Not Loading

```bash
# Docker Compose only reads .env at startup
# Must use down+up, not restart
docker-compose down
docker-compose up -d
```

---

## Next Steps

- **[README](../../README.md)** — Feature overview
- **[architecture.md](../architecture-and-platform/architecture.md)** — How it works under the hood
- **[deployment.md](deployment.md)** — Production deployment
