# GitHub Actions Secret Sync

**Script**: [sync-secrets-to-github.ps1](sync-secrets-to-github.ps1)  
**Purpose**: Automate syncing of production credentials from local `.env` to GitHub Actions secrets

---

## Quick Start

```powershell
# Preview what will be synced
.\support\scripts\sync-secrets-to-github.ps1 -DryRun

# Sync all secrets (with confirmation)
.\support\scripts\sync-secrets-to-github.ps1

# Sync without confirmation
.\support\scripts\sync-secrets-to-github.ps1 -Force

# Sync only OAuth secrets
.\support\scripts\sync-secrets-to-github.ps1 -Force -Filter "OAUTH"
```

---

## Prerequisites

**Install GitHub CLI:**

```powershell
winget install GitHub.cli
```

**Authenticate:**

```powershell
gh auth login
```

**Verify access:**

```powershell
gh auth status
```

---

## What Gets Synced

The script syncs **32 secrets** from `config/env/.env` to GitHub Actions:

| Category           | Secrets                                                                                                  |
| ------------------ | -------------------------------------------------------------------------------------------------------- |
| **OAuth**          | OAUTH2_PROXY_CLIENT_SECRET, OAUTH2_PROXY_COOKIE_SECRET, GH_OAUTH_CLIENT_SECRET                           |
| **LLM Providers**  | CLAUDE_API_KEY, MISTRAL_API_KEY, PERPLEXITY_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY                  |
| **DigitalOcean**   | GRADIENT_API_KEY, GRADIENT_MODEL_ACCESS_KEY, DIGITAL_OCEAN_PAT, DIGITALOCEAN_TOKEN                       |
| **Observability**  | LANGCHAIN_API_KEY, LANGSMITH_API_KEY, LANGSMITH_WORKSPACE_ID, LANGGRAPH_API_KEY, GRAFANA_CLOUD_API_TOKEN |
| **Linear**         | LINEAR_API_KEY, LINEAR_OAUTH_DEV_TOKEN, LINEAR_WEBHOOK_SIGNING_SECRET, LINEAR_TEAM_ID                    |
| **RAG/Vector DB**  | QDRANT_URL, QDRANT_API_KEY                                                                               |
| **Database**       | DB_PASSWORD, POSTGRES_PASSWORD, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_TOKEN                                |
| **Infrastructure** | ORCHESTRATOR_API_KEY, DOCKER_PAT, DOCKER_USERNAME                                                        |

---

## How It Works

1. **Reads** `config/env/.env` and parses all `KEY=VALUE` pairs
2. **Filters** to only include secrets defined in the script
3. **Previews** what will be synced (with masked values)
4. **Uploads** to GitHub Actions via `gh secret set`
5. **Reports** success/failure for each secret

---

## GitHub Limitations

**Reserved Prefixes:**
GitHub Actions doesn't allow secrets starting with:

- `GITHUB_` (reserved for built-in variables)

**Workarounds:**

- `GITHUB_TOKEN` → Automatically provided by GitHub Actions
- `GITHUB_OAUTH_CLIENT_SECRET` → Renamed to `GH_OAUTH_CLIENT_SECRET` in workflow

---

## Deployment Integration

Once secrets are synced, the [deploy-intelligent.yml](../../.github/workflows/deploy-intelligent.yml) workflow:

1. **Builds `.env`** from GitHub secrets on every push to `main`
2. **Deploys to droplet** with credentials automatically populated
3. **No manual `.env` editing** required on droplet

```yaml
# Workflow automatically injects secrets
- name: Create .env file
  run: |
    echo "GRADIENT_API_KEY=${{ secrets.GRADIENT_API_KEY }}" >> config/env/.env
    echo "LANGCHAIN_API_KEY=${{ secrets.LANGSMITH_API_KEY }}" >> config/env/.env
    # ... all 30+ secrets
```

---

## Secret Rotation Workflow

**When rotating credentials:**

1. **Update local `.env`** with new values
2. **Re-run sync script:**
   ```powershell
   .\support\scripts\sync-secrets-to-github.ps1 -Force
   ```
3. **Deploy automatically:**
   ```powershell
   git commit --allow-empty -m "trigger deploy" && git push
   ```
4. **Old secrets invalidated** after deployment completes

---

## Security Best Practices

✅ **DO:**

- Keep `.env` in `.gitignore` (already configured)
- Use the sync script for all updates
- Rotate secrets regularly
- Review who has repo access

❌ **DON'T:**

- Commit `.env` to git
- Share `.env` via Slack/email
- Use production secrets in development
- Hardcode secrets in code

---

## Viewing Secrets in GitHub

**Web UI:**  
https://github.com/Appsmithery/code-chef/settings/secrets/actions

**CLI:**

```powershell
# List all secrets
gh secret list --repo Appsmithery/code-chef

# Delete a secret
gh secret delete SECRET_NAME --repo Appsmithery/code-chef
```

---

## Troubleshooting

**"GitHub CLI not found"**

```powershell
winget install GitHub.cli
# Restart terminal
```

**"Not authenticated with GitHub"**

```powershell
gh auth login
# Follow prompts
```

**"Secret not found in .env file"**

- Check spelling in local `.env`
- Ensure variable is not commented out
- Verify file path is correct

**"Failed to set secret"**

- Check repo permissions (need write access)
- Verify secret name doesn't start with `GITHUB_`
- Ensure value is not empty

---

## Current Status

**Synced:** 31 secrets ✅  
**Failed:** 1 (`GITHUB_TOKEN` - reserved by GitHub)  
**Last Sync:** December 12, 2025

**View:** https://github.com/Appsmithery/code-chef/settings/secrets/actions
