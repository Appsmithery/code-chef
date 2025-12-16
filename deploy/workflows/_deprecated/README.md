# Deprecated Workflows

**Date Deprecated**: December 16, 2025  
**Reason**: Migration to unified intelligent deployment workflow

---

## ⚠️ DO NOT USE THESE WORKFLOWS

These workflows have been deprecated and archived. They are kept for historical reference only.

---

## Deprecated Files

### 1. `deploy.yml`

- **Status**: DISABLED (already marked as "Legacy - DISABLED")
- **Reason**: Replaced by `.github/workflows/deploy-intelligent.yml`
- **Issues**:
  - Used old compose directory structure
  - No .env syncing mechanism
  - Manual secret file management

### 2. `build-images.yml`

- **Status**: OBSOLETE
- **Reason**: Uses old `containers/` directory structure
- **Issues**:
  - Points to non-existent `containers/` directory
  - Replaced by unified `agent_orchestrator/` architecture
  - GitHub Container Registry (ghcr.io) not actively used

### 3. `docker-hub-deploy.yml`

- **Status**: PARTIAL - Contains legacy references
- **Reason**: Still references deprecated Gradient AI provider
- **Issues**:
  - Line 42: `GRADIENT_API_KEY=${{ secrets.GRADIENT_API_KEY }}` (no longer used)
  - Pushes to Docker Hub which is not the primary deployment target
  - Replaced by direct droplet deployment via SSH

### 4. `docr-build.yml`

- **Status**: UNUSED
- **Reason**: DigitalOcean Container Registry not used in production
- **Issues**:
  - Project uses direct Docker Compose builds on droplet
  - No active DOCR registry configured
  - Unnecessary complexity for single-droplet deployment

### 5. `lint.yml`

- **Status**: DUPLICATE (stale copy)
- **Reason**: Active version is in `.github/workflows/lint.yml`
- **Issues**:
  - References old directory structure (`agents/`, `mcp/`)
  - Active version uses correct paths (`agent_orchestrator/`, `shared/`)
  - Caused confusion with duplicate workflow names

---

## ✅ Current Production Workflow

**Use this instead**: `.github/workflows/deploy-intelligent.yml`

### Features

- ✅ Automated .env syncing to production droplet
- ✅ Intelligent deployment strategy selection (config/full/quick)
- ✅ Health check validation after deployment
- ✅ Proper secret management via GitHub Secrets
- ✅ Fail-fast error handling
- ✅ Rollback capability on failure

### Usage

**Automatic Deployment** (on push to main):

```bash
git push origin main
# Triggers deploy-intelligent.yml automatically
```

**Manual Deployment** (via GitHub Actions UI):

1. Go to: https://github.com/Appsmithery/code-chef/actions/workflows/deploy-intelligent.yml
2. Click "Run workflow"
3. Select deployment type: auto/config/full/quick
4. Click "Run workflow"

**Local Deployment** (manual via SSH):

```bash
# Sync .env first
bash support/scripts/deployment/sync-env-to-droplet.sh

# Deploy
ssh root@45.55.173.72 "cd /opt/code-chef && git pull origin main"
ssh root@45.55.173.72 "cd /opt/code-chef/deploy && docker compose down && docker compose up -d --build"

# Verify
curl https://codechef.appsmithery.co/health
```

---

## 🔍 Migration History

| Date         | Action                           | Details                                                       |
| ------------ | -------------------------------- | ------------------------------------------------------------- |
| Dec 16, 2025 | Archived workflows               | Moved to `_deprecated/` after Gradient → OpenRouter migration |
| Dec 16, 2025 | Created `deploy-intelligent.yml` | Unified deployment with .env sync and health checks           |
| Dec 16, 2025 | Removed hardcoded fallbacks      | Fail-fast error handling in `shared/lib/llm_providers.py`     |

---

## 📚 Documentation

- **Main Deployment Guide**: `support/docs/deployment/PRODUCTION_HARDENING_PLAN.md`
- **Deployment Scripts**: `support/scripts/deployment/`
- **Current Workflow**: `.github/workflows/deploy-intelligent.yml`

---

**If you need to reference these old workflows**, they remain here for historical context. However, **DO NOT attempt to run them** as they reference deprecated infrastructure and secrets.
