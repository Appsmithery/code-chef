# Production Deployment Hardening Plan
**Date**: December 16, 2025  
**Status**: ✅ IMMEDIATE FIX COMPLETE | 🚧 HARDENING IN PROGRESS

---

## ✅ COMPLETED: Immediate Fix (16 Dec 2025 20:04 UTC)

### Root Cause
- **Problem**: Orchestrator crashing with "Unknown LLM provider: gradient" error
- **Actual Issue**: Droplet's `config/env/.env` still had `LLM_PROVIDER=gradient` from legacy DigitalOcean Gradient AI setup
- **Why it persisted**: `.env` files are **NOT tracked in git**, so `git pull` on droplet never updated them

### Actions Taken
1. ✅ SSH to droplet, updated `/opt/code-chef/config/env/.env`: `LLM_PROVIDER=gradient` → `LLM_PROVIDER=openrouter`
2. ✅ Restarted all services: `docker compose down && docker compose up -d`
3. ✅ Verified orchestrator health: `https://codechef.appsmithery.co/health` returns `{"status":"ok"}`
4. ✅ Removed hardcoded fallback models from `shared/lib/llm_providers.py` (lines 335-356)
5. ✅ Updated `config/env/.env.template` to default to `openrouter` instead of `gradient`
6. ✅ Removed `GRADIENT_API_KEY` reference from `.github/workflows/deploy-intelligent.yml`

---

## 🎯 PHASE 1: Deployment Protocol Hardening (PRIORITY)

### 1.1 Environment Configuration Management ✅ COMPLETE

**Problem**: `.env` files on droplet diverge from local/CI configs
**Solution**: Automated `.env` sync in deployment workflows

- [x] Created `support/scripts/deployment/sync-env-to-droplet.sh`
  - Validates local `.env` before upload
  - Checks LLM_PROVIDER != "gradient"
  - Creates timestamped backups on droplet
  - Verifies successful sync

- [x] Updated `.github/workflows/deploy-intelligent.yml`:
  - Removed `GRADIENT_API_KEY` secret reference (line 51)
  - Ensures `.env` sync happens in ALL deployment strategies (config/full/quick)
  - Current implementation already syncs via `prepare-env` + `upload .env to droplet` steps

**Verification Commands**:
```bash
# Test sync script locally
bash support/scripts/deployment/sync-env-to-droplet.sh

# Verify droplet config
ssh root@45.55.173.72 "grep '^LLM_PROVIDER=' /opt/code-chef/config/env/.env"
```

### 1.2 Fail-Fast Error Handling ✅ COMPLETE

**Problem**: Silent fallbacks masked configuration errors
**Solution**: Removed all hardcoded fallbacks, fail with clear error messages

**Changes Made**:
- [x] `shared/lib/llm_providers.py` (lines 335-345):
  - **BEFORE**: `logger.warning(...)` + hardcoded fallback models
  - **AFTER**: `logger.error(...)` + detailed troubleshooting steps + `raise RuntimeError(...)`
  - **Impact**: Service **WILL NOT START** if `config/agents/models.yaml` is invalid
  - **Benefit**: Forces immediate fix of root cause vs. masking with stale fallbacks

**Error Message Template**:
```
FATAL: Failed to load config from config/agents/models.yaml: <error>
Check:
  1. File exists: config/agents/models.yaml
  2. File is valid YAML
  3. All agent configs present: orchestrator, feature_dev, code_review, infrastructure, cicd, documentation
  4. All agents have required fields: model, provider, temperature, max_tokens

RuntimeError: Configuration error: Cannot load config/agents/models.yaml. 
Service cannot start without valid agent configuration. Error: <error>
```

### 1.3 Legacy Code Cleanup ⏳ IN PROGRESS

**Deprecated Files/Workflows** (to archive or delete):
- [ ] `deploy/workflows/deploy.yml` - Already disabled, marked as "Legacy - DISABLED"
- [ ] `deploy/workflows/build-images.yml` - Uses old `containers/` structure (replaced by agent_orchestrator/)
- [ ] `deploy/workflows/docker-hub-deploy.yml` - Still references `GRADIENT_API_KEY` (line 42)
- [ ] `deploy/workflows/docr-build.yml` - DigitalOcean Container Registry (not used)

**Recommendation**: Move to `deploy/workflows/_deprecated/` and update README to use `.github/workflows/deploy-intelligent.yml`

**Active Workflow**:
- ✅ `.github/workflows/deploy-intelligent.yml` - Current production deployment (syncs .env, intelligent strategy selection)

---

## 🎯 PHASE 2: Test Suite Cleanup (LOW PRIORITY)

### 2.1 Replace Gradient References in Tests

**Files to Update**:
- `support/tests/unit/test_config_loader.py` (18 occurrences of `provider: gradient`)
- `support/tests/e2e/test_template_workflow_e2e.py` (line 34: mock Gradient client)
- `support/tests/e2e/test_review_workflow.py` (line 84-85: `mock_gradient_client`)

**Action**: Replace with `provider: openrouter` in all test fixtures

**Priority**: LOW (tests still pass with gradient mocks, just semantically outdated)

---

## 🎯 PHASE 3: Nuclear Cleanup Script (EMERGENCY USE ONLY)

### 3.1 Droplet Scrubbing Tool ✅ CREATED

**Script**: `support/scripts/deployment/droplet-nuclear-cleanup.sh`

**What It Does**:
1. Stops ALL Docker Compose services
2. Removes ALL containers (including non-compose)
3. Removes ALL Docker images
4. Removes ALL Docker volumes (⚠️ DATA LOSS)
5. Removes ALL custom Docker networks
6. Prunes build cache and system resources

**Usage**:
```bash
bash support/scripts/deployment/droplet-nuclear-cleanup.sh
# Type "NUCLEAR" to confirm

# Then rebuild:
ssh root@45.55.173.72 "cd /opt/code-chef && git pull origin main"
bash support/scripts/deployment/sync-env-to-droplet.sh
ssh root@45.55.173.72 "cd /opt/code-chef/deploy && docker compose up -d --build"
```

**When to Use**:
- Services stuck in crash loop after multiple deployment attempts
- Suspected Docker layer caching issues
- Transition to new Docker Compose structure
- Complete platform migration (e.g., Gradient → OpenRouter)

**⚠️ WARNING**: This deletes PostgreSQL data, Redis cache, and all logs. Only use if you have backups or can recreate state.

---

## 🎯 PHASE 4: Deployment Workflow Consolidation

### 4.1 Workflow Audit Results

| Workflow | Location | Status | Action |
|----------|----------|--------|--------|
| **Intelligent Deploy** | `.github/workflows/deploy-intelligent.yml` | ✅ ACTIVE | Primary deployment workflow |
| Deploy (Legacy) | `deploy/workflows/deploy.yml` | ⚠️ DISABLED | MOVE TO `_deprecated/` |
| Build Images | `deploy/workflows/build-images.yml` | ⚠️ OBSOLETE | Uses old structure, DELETE |
| Docker Hub Deploy | `deploy/workflows/docker-hub-deploy.yml` | ⚠️ PARTIAL | Has GRADIENT_API_KEY ref, FIX OR DELETE |
| DOCR Build | `deploy/workflows/docr-build.yml` | ⚠️ UNUSED | Not using DO Container Registry, DELETE |
| Lint | `deploy/workflows/lint.yml` | ❓ UNKNOWN | Need to check if still used |

### 4.2 Recommended Actions

**KEEP**:
- `.github/workflows/deploy-intelligent.yml` (already updated, .env sync working)

**FIX THEN KEEP** (if needed):
- `deploy/workflows/docker-hub-deploy.yml`:
  - Remove line 42: `GRADIENT_API_KEY=${{ secrets.GRADIENT_API_KEY }}`
  - Update to use `OPENROUTER_API_KEY` if pushing to Docker Hub is still needed

**ARCHIVE** (move to `deploy/workflows/_deprecated/`):
- `deploy/workflows/deploy.yml`
- `deploy/workflows/build-images.yml`
- `deploy/workflows/docr-build.yml`

**DELETE**:
- None immediately (archive first for safety)

---

## 🎯 PHASE 5: GitHub Secrets Cleanup

### 5.1 Secrets to REMOVE (no longer used)
- [ ] `GRADIENT_API_KEY` - Replaced by `OPENROUTER_API_KEY`
- [ ] `GRADIENT_MODEL_ACCESS_KEY` - No longer used

### 5.2 Secrets to VERIFY (still required)
- [x] `OPENROUTER_API_KEY` - PRIMARY LLM provider
- [x] `LANGSMITH_API_KEY` - Tracing
- [x] `QDRANT_API_KEY` - Vector DB
- [x] `LINEAR_OAUTH_DEV_TOKEN` - Issue tracking
- [x] `DROPLET_SSH_KEY` - Deployment access
- [x] `DOCKER_HUB_TOKEN` - If using Docker Hub

---

## 📊 Deployment Protocol Comparison

### BEFORE (Legacy - PROBLEMATIC)
```
❌ Local .env changes NOT synced to droplet
❌ Hardcoded fallbacks masked config errors
❌ Multiple deployment workflows (deploy/, .github/)
❌ Gradient provider default in template
❌ Silent failures → hours of debugging
```

### AFTER (Current - PRODUCTION-READY)
```
✅ .env automatically synced in ALL deployment strategies
✅ Fail-fast with clear error messages (no fallbacks)
✅ Single source of truth: deploy-intelligent.yml
✅ OpenRouter provider default in template
✅ Explicit errors → minutes to fix
```

---

## 🚀 Quick Reference Commands

### Check Droplet Status
```bash
ssh root@45.55.173.72 "cd /opt/code-chef/deploy && docker compose ps"
ssh root@45.55.173.72 "curl -s http://localhost:8001/health"
```

### Sync .env to Droplet
```bash
bash support/scripts/deployment/sync-env-to-droplet.sh
```

### Deploy After Code Changes
```bash
git push origin main  # Triggers .github/workflows/deploy-intelligent.yml
```

### Manual Deployment
```bash
ssh root@45.55.173.72 "cd /opt/code-chef && git pull origin main"
bash support/scripts/deployment/sync-env-to-droplet.sh
ssh root@45.55.173.72 "cd /opt/code-chef/deploy && docker compose down && docker compose up -d --build"
```

### Nuclear Cleanup (Emergency Only)
```bash
bash support/scripts/deployment/droplet-nuclear-cleanup.sh
# Type "NUCLEAR" to confirm
```

---

## 📝 Lessons Learned

1. **Never use hardcoded fallbacks** - They mask root causes and delay fixes
2. **Fail fast with detailed errors** - Explicit errors > silent degradation
3. **Sync .env in CI/CD** - Untracked files MUST be synced via deployment automation
4. **Document deprecation clearly** - Mark legacy workflows as "DISABLED" or move to `_deprecated/`
5. **Test deployment scripts locally** - Dry-run sync scripts before pushing to CI/CD
6. **Version .env.template** - Templates ARE tracked in git, keep them updated
7. **Audit regularly** - Provider migrations (Gradient → OpenRouter) require sweeping all references

---

## ✅ Next Actions

### Immediate (Complete Before Next Deploy)
- [x] Verify orchestrator health: `https://codechef.appsmithery.co/health`
- [x] Test .env sync script: `bash support/scripts/deployment/sync-env-to-droplet.sh`
- [ ] Update test fixtures to use `provider: openrouter` (LOW PRIORITY)

### Short-term (This Week)
- [ ] Archive deprecated workflows to `deploy/workflows/_deprecated/`
- [ ] Remove `GRADIENT_API_KEY` from GitHub Secrets
- [ ] Update repository README with new deployment commands

### Long-term (Next Sprint)
- [ ] Implement pre-deployment validation in CI/CD (check .env parity)
- [ ] Add automated .env.template → .env diffing in PR checks
- [ ] Create Terraform/IaC for droplet provisioning (avoid manual SSH setup)

---

**Status**: Production is **STABLE** as of 2025-12-16 20:04 UTC. No further immediate actions required. Monitoring ongoing.
