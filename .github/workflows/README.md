# GitHub Actions Workflows

Automated CI/CD pipelines for code-chef multi-agent DevOps platform.

## Quick Reference

| Workflow                                                       | Trigger              | Purpose                  | Duration | Status       |
| -------------------------------------------------------------- | -------------------- | ------------------------ | -------- | ------------ |
| [deploy-intelligent.yml](#1-intelligent-deploy-to-droplet)     | Push to `main`       | Production deployment    | ~3 min   | ✅ Optimized |
| [weekly-evaluation.yml](#2-weekly-health-check)                | Weekly (Sun 6AM UTC) | Agent health monitoring  | ~5 min   | ✅ New       |
| [e2e-langsmith-eval.yml](#3-e2e-langsmith-evaluation)          | Manual               | Full trace evaluation    | ~15 min  | ✅ Optimized |
| [evaluation-regression.yml](#4-evaluation--regression-testing) | Weekly (Sun 2AM UTC) | A/B testing & regression | ~12 min  | ✅ Optimized |
| [cleanup-docker-resources.yml](#5-cleanup-docker-resources)    | Weekly + post-deploy | Docker pruning           | ~2 min   | ✅ Active    |
| [lint.yml](#6-lint)                                            | Push/PR              | Code quality checks      | ~30 sec  | ✅ Optimized |
| [publish-extension.yml](#7-publish-vs-code-extension)          | Manual               | Extension release        | ~4 min   | ✅ Active    |
| [deploy-frontend.yml](#8-deploy-frontend-to-production)        | Manual               | Frontend deployment      | ~2 min   | ✅ Active    |
| [frontend-preview.yml](#9-frontend-build-preview)              | PR                   | Bundle size analysis     | ~1 min   | ✅ Active    |

---

## Recent Optimizations (December 2025)

### Phase 3 Complete - Linear Issue: [CHEF-255](https://linear.app/dev-ops/issue/CHEF-255)

**E2E Evaluation Optimization (Dec 13):**

- ✅ **e2e-langsmith-eval.yml**: Converted to manual-only (removed daily schedule + push triggers)
- ✅ **weekly-evaluation.yml**: New lightweight weekly health check (core evaluators only)
- ✅ **evaluators.py**: Added `streaming_response_quality` evaluator for SSE validation
- ✅ **OpenRouter validation**: Pre-flight checks before evaluation runs
- ✅ **Phase selection**: Run specific phases (phase1/phase2/modelops) instead of full suite

**Impact**: 90% reduction in evaluation runs (1 weekly vs 7+ daily), no CI/CD blocking

**Phase 2 (Dec 9-11):**

- ✅ **deploy-intelligent.yml**: Docker BuildKit + layer caching (70% faster: 10min → 3min)
- ✅ **publish-extension.yml**: Changed to manual-only trigger
- ✅ **evaluation-regression.yml**: Added pip caching to 3 jobs (30-50% faster deps)
- ✅ **lint.yml**: Streamlined caching (75% faster: 2min → 30sec)

**Overall Impact**: 67% reduction in CI time for typical PR workflow (~30min → ~10min)

---

## Workflow Documentation

### 1. Intelligent Deploy to Droplet

**File**: `deploy-intelligent.yml`  
**Triggers**:

- Push to `main` with changes to:
  - `agent_*/**`
  - `shared/**`
  - `config/**`
  - `deploy/docker-compose.yml`
- Manual dispatch with deployment type selection

**Parameters** (Manual Dispatch):
| Parameter | Type | Default | Options | Description |
|-----------|------|---------|---------|-------------|
| `deploy_type` | choice | `auto` | `auto`, `config`, `full`, `quick` | Deployment strategy |

**Jobs**:

1. **prepare-env** - Creates `.env` file with secrets
2. **analyze** - Detects changed services via git diff
3. **deploy** - Executes deployment strategy (auto-detection or manual)
4. **health-check** - Validates all services healthy (90s timeout)

**Deployment Types**:

- **auto**: Smart detection based on changed files (default)
- **config**: Config-only reload (no container restart)
- **full**: Complete rebuild and restart
- **quick**: Fast restart without rebuild

**Secrets Required**:

- `DROPLET_SSH_KEY` - SSH private key for root@45.55.173.72
- `ORCHESTRATOR_API_KEY` - API key for orchestrator service
- `GRADIENT_API_KEY` - Gradient AI API key
- `LANGSMITH_API_KEY` - LangSmith tracing API key
- `LANGSMITH_WORKSPACE_ID` - LangSmith workspace identifier
- `OPENROUTER_API_KEY` - OpenRouter LLM API key
- `QDRANT_API_KEY` - Qdrant vector DB API key
- `QDRANT_URL` - Qdrant cluster URL
- `LINEAR_API_KEY` - Linear project management API key
- `LINEAR_WEBHOOK_SECRET` - Linear webhook verification secret
- `HUGGINGFACE_TOKEN` - HuggingFace API token

**Optimizations**:

- Docker BuildKit with layer caching
- Parallel service rebuilds
- Intelligent change detection
- Health check parallelization

---

### 2. Weekly Health Check

**File**: `weekly-evaluation.yml` ⭐ **NEW**  
**Triggers**:

- Schedule: Weekly on Sunday at 6 AM UTC
- Manual dispatch

**Parameters** (Manual Dispatch):
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project` | string | `code-chef-production` | LangSmith project to evaluate |

**Jobs**:

1. **health-check** - Runs core evaluators on production traces

**Evaluators Run**:

- `agent_routing_accuracy`
- `token_efficiency`
- `latency_threshold`

**Regression Detection**:

- **Threshold**: <70% overall score or >5 failures
- **Action**: Creates GitHub summary, fails workflow, triggers Linear issue (ready)

**Secrets Required**:

- `LANGCHAIN_API_KEY`
- `OPENROUTER_API_KEY`

**Purpose**: Lightweight weekly monitoring to detect performance regressions without blocking CI/CD.

---

### 3. E2E LangSmith Evaluation

**File**: `e2e-langsmith-eval.yml` ⭐ **OPTIMIZED**  
**Triggers**:

- Manual dispatch only (removed automatic triggers)

**Parameters** (Manual Dispatch):
| Parameter | Type | Default | Options | Description |
|-----------|------|---------|---------|-------------|
| `phase` | choice | `all` | `phase1`, `phase2`, `modelops`, `all` | Which phase to evaluate |
| `dataset` | string | `ib-agent-scenarios-v1` | - | LangSmith dataset name |
| `evaluators` | string | `all` | comma-separated or `all` | Specific evaluators to run |
| `project` | string | `code-chef-testing` | - | LangSmith project |

**Jobs**:

1. **phase1-data-layer** - MCP servers, Docker, Qdrant (evaluators: `mcp_integration_quality`, `latency_threshold`, `workflow_completeness`)
2. **phase2-core-agents** - LangGraph workflows, RAG, routing (evaluators: `agent_routing_accuracy`, `token_efficiency`, `latency_threshold`, `workflow_completeness`, `streaming_response_quality`)
3. **modelops-evaluation** - Training, deployment workflows (evaluators: `modelops_training_quality`, `modelops_deployment_success`, `latency_threshold`, `workflow_completeness`)
4. **full-evaluation** - Aggregates results, creates Linear issues for failures
5. **custom-evaluation** - Runs specific evaluators when not `all`

**New Features**:

- ✅ **OpenRouter validation** - Pre-flight checks before evaluation
- ✅ **Phase selection** - Run specific phases independently
- ✅ **Streaming evaluator** - Validates SSE format, chunk timing, error handling
- ✅ **Manual-only** - No automatic triggers to prevent CI/CD blocking

**Secrets Required**:

- `LANGCHAIN_API_KEY`

---

### 4. Evaluation & Regression Testing

**File**: `evaluation-regression.yml` ⭐ **OPTIMIZED**  
**Triggers**:

- Schedule: Weekly on Sunday at 2 AM UTC
- Manual dispatch

**Parameters** (Manual Dispatch):
| Parameter | Type | Default | Options | Description |
|-----------|------|---------|---------|-------------|
| `hypothesis_profile` | string | `dev` | `ci`, `dev`, `thorough` | Property-based test profile |
| `skip_regression` | string | `false` | `true`, `false` | Skip regression detection |
| `experiment_id` | string | `` | - | Custom experiment ID |

**Jobs**:

1. **database-persistence** - Validates evaluation storage (PostgreSQL)
2. **baseline-comparison** - A/B testing (baseline vs code-chef models)
3. **property-based** - Hypothesis-driven robustness tests (1500+ test cases)
4. **regression-detection** - Detects performance degradation across versions

**Hypothesis Profiles**:

- **ci**: Fast (20 examples per property) - ~3 min
- **dev**: Default (100 examples) - ~8 min
- **thorough**: Comprehensive (500 examples) - ~25 min

**Optimizations**:

- Pip caching on all 3 jobs
- PostgreSQL service for database tests
- Parallel job execution

**Secrets Required**:

- `LANGCHAIN_API_KEY`

---

### 5. Cleanup Docker Resources

**File**: `cleanup-docker-resources.yml`  
**Triggers**:

- Schedule: Weekly on Sunday at 3 AM UTC
- After successful deploy (workflow_run)
- Manual dispatch

**Parameters** (Manual Dispatch):
| Parameter | Type | Default | Options | Description |
|-----------|------|---------|---------|-------------|
| `cleanup_type` | choice | `standard` | `standard`, `aggressive`, `full` | Cleanup strategy |

**Cleanup Types**:

- **standard**: Remove stopped containers, dangling images
- **aggressive**: + unused networks, orphaned volumes
- **full**: + prune build cache, force volume removal

**Jobs**:

1. **cleanup** - Executes cleanup strategy on droplet

**Secrets Required**:

- `DROPLET_SSH_KEY`

**Purpose**: Prevents disk space exhaustion from orphaned Docker resources (~500MB-2GB saved per run).

---

### 6. Lint

**File**: `lint.yml` ⭐ **OPTIMIZED**  
**Triggers**:

- Push to `main` with changes to:
  - `agent_orchestrator/**/*.py`
  - `shared/**/*.py`
  - `config/**/*.yaml`
  - `config/**/*.yml`
- Pull requests (same paths)

**Jobs**:

1. **lint-python** - Black, Pylint (non-blocking)
2. **lint-yaml** - yamllint (non-blocking)

**Optimizations**:

- Pip caching for Python linters
- Parallel job execution
- Path filters to skip unnecessary runs

**Purpose**: Enforces code style and catches YAML syntax errors early.

---

### 7. Publish VS Code Extension

**File**: `publish-extension.yml` ⭐ **MANUAL ONLY**  
**Triggers**:

- Manual dispatch only

**Parameters** (Manual Dispatch):
| Parameter | Type | Required | Options | Description |
|-----------|------|----------|---------|-------------|
| `version` | string | **Yes** | - | Version to publish (e.g., `1.0.1`) |
| `version_bump` | choice | No | `patch`, `minor`, `major`, `none` | Auto-bump alternative |

**Jobs**:

1. **build-and-publish** - Builds VSIX, publishes to VS Code Marketplace

**Steps**:

1. Updates `package.json` version
2. Compiles TypeScript
3. Packages `.vsix` file
4. Publishes to marketplace
5. Creates Git tag
6. Uploads artifact to GitHub

**Secrets Required**:

- `VSCE_PAT` - Visual Studio Marketplace Personal Access Token
- `GITHUB_TOKEN` (automatic)

**Purpose**: Controlled release process for VS Code extension.

---

### 8. Deploy Frontend to Production

**File**: `deploy-frontend.yml`  
**Triggers**:

- Manual dispatch only

**Jobs**:

1. **deploy** - Builds React bundle, syncs to droplet, restarts Caddy

**Steps**:

1. `npm ci` (with cache)
2. `npm run build`
3. `rsync` dist/ to `/opt/Dev-Tools/support/frontend/dist/`
4. `docker compose restart caddy`

**Secrets Required**:

- `DROPLET_SSH_KEY`
- `DROPLET_USER` (default: `root`)
- `DROPLET_HOST` (default: `45.55.173.72`)

**Purpose**: Deploy React frontend to https://codechef.appsmithery.co

---

### 9. Frontend Build Preview

**File**: `frontend-preview.yml`  
**Triggers**:

- Pull requests with changes to:
  - `frontend/src/**`
  - `frontend/public/**`
  - `frontend/package.json`

**Jobs**:

1. **build-preview** - Type checks, builds bundle, comments size on PR

**Purpose**: Prevents bundle size regressions, catches TypeScript errors early.

---

## 🚀 Production Deployment Guide

### Full Production Update Sequence

For a complete production update (backend + frontend + extension), follow this order:

#### Step 1: Deploy Backend Services (~3 min)

```bash
Actions → Intelligent Deploy to Droplet → Run workflow
  branch: main
  deploy_type: full  # Complete rebuild
```

**Validates**:

- ✅ All 5 services healthy (orchestrator, rag-context, state-persist, agent-registry, langgraph)
- ✅ PostgreSQL connection established
- ✅ Qdrant vector DB accessible
- ✅ Health endpoints responding

**Wait for**: Green checkmark in Actions tab

---

#### Step 2: Deploy Frontend (~2 min)

```bash
Actions → Deploy Frontend to Production → Run workflow
```

**Validates**:

- ✅ Production bundle built
- ✅ Files synced to droplet
- ✅ Caddy serving at https://codechef.appsmithery.co

**Verify**: Open https://codechef.appsmithery.co in browser

---

#### Step 3: Publish Extension (~4 min)

```bash
Actions → Publish VS Code Extension → Run workflow
  version: 1.0.0  # Or next version
  version_bump: none
```

**Validates**:

- ✅ Package version updated
- ✅ TypeScript compiled
- ✅ VSIX published to marketplace
- ✅ Git tag created
- ✅ GitHub Release created (automated)

**Wait for**: Extension available in VS Code Marketplace (~10 min propagation)

**Test Installation**:

```bash
code --install-extension appsmithery.vscode-codechef
```

---

#### Step 4: Cleanup (Optional, ~2 min)

```bash
Actions → Cleanup Docker Resources → Run workflow
  cleanup_type: standard
```

**Frees**: ~500MB-2GB disk space

---

### Total Deployment Time

**~11 minutes** for complete production update (all 4 steps)

### Quick Reference

| What Changed        | Required Workflows          | Time    |
| ------------------- | --------------------------- | ------- |
| Backend code only   | deploy-intelligent (auto)   | ~3 min  |
| Frontend code only  | deploy-frontend             | ~2 min  |
| Extension code only | publish-extension           | ~4 min  |
| Config files only   | deploy-intelligent (config) | ~1 min  |
| Everything          | All 4 workflows             | ~11 min |

---

## 📦 Distribution Strategy

### GitHub Releases

Every extension publish automatically creates a GitHub Release with:

- ✅ Versioned VSIX file
- ✅ Release notes (auto-generated)
- ✅ Git tag (immutable)
- ✅ Installation instructions
- ✅ API key requirements

**Access**: [Releases Page](https://github.com/Appsmithery/code-chef/releases)

### GitHub Packages (npm Registry)

For shared libraries across projects:

**Package Structure**:

```
@appsmithery/code-chef-core       # Shared MCP client, auth validation
@appsmithery/code-chef-agents     # Agent base classes
@appsmithery/code-chef-workflows  # Workflow templates
```

**Installation** (in other projects):

```bash
# Configure registry
echo "@appsmithery:registry=https://npm.pkg.github.com" >> .npmrc

# Install package
npm install @appsmithery/code-chef-core@^1.0.0
```

**Usage**:

```typescript
import { AuthValidator } from "@appsmithery/code-chef-core/auth";

const validator = new AuthValidator();
await validator.validate(process.env.CHEF_API_KEY);
```

### VS Code Marketplace

**Primary distribution** for extension:

- Search "code-chef" in VS Code Extensions
- Or: `code --install-extension appsmithery.vscode-codechef`

**Updates**: Auto-update enabled by default in VS Code

---

## 🔐 Security & Access Control

### API Key Gating (Private Alpha)

code-chef is currently in **Private Alpha** with multi-layer API key authentication:

#### Layer 1: Extension Activation

- Validates API key on VS Code extension activation
- Shows error if missing/invalid
- Caches validation for 5 minutes

#### Layer 2: Orchestrator API

- FastAPI middleware validates Bearer token
- Database-backed key storage (hashed)
- Per-tier rate limiting (60-1000 req/min)

#### Layer 3: Usage Tracking

- PostgreSQL logging of all requests
- Token usage, cost tracking
- Billing-ready metrics

### Getting an API Key

**For UAT participants only**:

1. Create issue: [API Access Request](https://github.com/Appsmithery/code-chef/issues/new?template=api-access-request.md)
2. Receive key format: `chef_<uuid>`
3. Configure in VS Code: Settings → "codechef.orchestratorApiKey"

**Tiers**:

- **free**: 60 requests/min
- **pro**: 300 requests/min
- **admin**: 1000 requests/min (maintainers only)

### Why API Keys?

Repository is **public for presentation**, but platform is **private for UAT**:

- ✅ Prevents unauthorized usage
- ✅ Tracks usage per user
- ✅ Enables billing later
- ✅ Controls access during testing

---

## Environment Variables

### Common Across Workflows

```yaml
PYTHON_VERSION: "3.11"
NODE_VERSION: "20"
LANGCHAIN_TRACING_V2: "true"
LANGCHAIN_PROJECT: "code-chef-testing" # or "code-chef-production"
TRACE_ENVIRONMENT: "evaluation" # for evaluation workflows
EXTENSION_VERSION: "1.2.3" # should match package.json
```

### Droplet Deployment

```yaml
DROPLET_HOST: "root@45.55.173.72"
DROPLET_IP: "45.55.173.72"
DEPLOY_PATH: "/opt/Dev-Tools"
HEALTH_CHECK_TIMEOUT: 90
HEALTH_CHECK_INTERVAL: 5
```

---

## Secrets Management

### Required Secrets (Repository Level)

Navigate to: **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name              | Example Value                            | Purpose                     | Used By                         |
| ------------------------ | ---------------------------------------- | --------------------------- | ------------------------------- |
| `DROPLET_SSH_KEY`        | `-----BEGIN OPENSSH PRIVATE KEY-----...` | SSH authentication          | Deploy workflows                |
| `DROPLET_USER`           | `root`                                   | SSH username                | Deploy workflows                |
| `DROPLET_HOST`           | `45.55.173.72`                           | Droplet IP address          | Deploy workflows                |
| `ORCHESTRATOR_API_KEY`   | `sk_live_...`                            | Orchestrator authentication | deploy-intelligent              |
| `GRADIENT_API_KEY`       | `grad_...`                               | Gradient AI LLM API         | deploy-intelligent              |
| `LANGSMITH_API_KEY`      | `lsv2_sk_...`                            | LangSmith tracing           | All evaluation workflows        |
| `LANGSMITH_WORKSPACE_ID` | `5029c640-3f73-480c-82f3-58e402ed4207`   | LangSmith workspace         | deploy-intelligent              |
| `OPENROUTER_API_KEY`     | `sk-or-v1-...`                           | OpenRouter LLM API          | deploy-intelligent, evaluations |
| `QDRANT_API_KEY`         | `...`                                    | Qdrant vector DB            | deploy-intelligent              |
| `QDRANT_URL`             | `https://...qdrant.io:6333`              | Qdrant cluster URL          | deploy-intelligent              |
| `LINEAR_API_KEY`         | `lin_api_...`                            | Linear project management   | deploy-intelligent              |
| `LINEAR_WEBHOOK_SECRET`  | `...`                                    | Linear webhook verification | deploy-intelligent              |
| `HUGGINGFACE_TOKEN`      | `hf_...`                                 | HuggingFace model access    | deploy-intelligent              |
| `VSCE_PAT`               | `...`                                    | VS Code Marketplace token   | publish-extension               |

### Generating SSH Keys

```bash
# Generate deploy key
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/github_deploy

# Copy private key to DROPLET_SSH_KEY secret
cat ~/.ssh/github_deploy

# Add public key to droplet
ssh root@45.55.173.72
echo "ssh-ed25519 AAAA..." >> ~/.ssh/authorized_keys
```

---

## Usage Examples

### Manual Deployment

```bash
# Via GitHub UI
Actions → Intelligent Deploy to Droplet → Run workflow
  branch: main
  deploy_type: auto

# Via GitHub CLI
gh workflow run deploy-intelligent.yml -f deploy_type=full
```

### Run Specific Evaluation Phase

```bash
# Test ModelOps only
Actions → E2E LangSmith Evaluation → Run workflow
  phase: modelops
  dataset: ib-agent-scenarios-v1
  evaluators: all
  project: code-chef-testing
```

### Publish Extension

```bash
# Bump patch version (1.0.0 → 1.0.1)
Actions → Publish VS Code Extension → Run workflow
  version: 1.0.1
  version_bump: none

# Or auto-bump
Actions → Publish VS Code Extension → Run workflow
  version: ""
  version_bump: patch
```

### Emergency Cleanup

```bash
# Aggressive cleanup (frees ~2GB)
Actions → Cleanup Docker Resources → Run workflow
  cleanup_type: aggressive
```

---

## Monitoring & Debugging

### GitHub Actions Dashboard

- **Actions tab**: Real-time build status
- **Email notifications**: On workflow failure
- **Status checks**: Required for PR merges

### Workflow Logs

```bash
# View specific job logs
gh run view <run-id> --log

# Download logs
gh run download <run-id>

# Watch live
gh run watch
```

### Droplet Health Checks

```bash
# SSH to droplet
ssh root@45.55.173.72

# Check all services
cd /opt/Dev-Tools
docker compose ps

# View logs
docker compose logs orchestrator -f --tail=100

# Check health endpoints
curl http://localhost:8001/health  # orchestrator
curl http://localhost:8007/health  # rag-context
curl http://localhost:8008/health  # state-persist
```

---

## Troubleshooting

### Common Issues

#### 1. Deployment Fails - Health Check Timeout

**Error**: `Health check failed after 90s`  
**Causes**:

- Service taking too long to start
- Database migration blocking
- Network connectivity issues

**Fix**:

```bash
# SSH to droplet
ssh root@45.55.173.72
cd /opt/Dev-Tools

# Check failing service
docker compose logs orchestrator --tail=50

# Manual restart
docker compose restart orchestrator

# Check health
curl http://localhost:8001/health
```

#### 2. Evaluation Workflow Fails - No Recent Runs

**Error**: `No recent runs to evaluate`  
**Cause**: LangSmith project has no traces in last 24 hours

**Fix**:

- Generate traces by using the platform
- Or adjust time window in `list_recent_runs()` function
- Or use a different project with active traces

#### 3. SSH Connection Refused

**Error**: `Connection refused` or `Permission denied`  
**Causes**:

- `DROPLET_SSH_KEY` secret incorrect
- Public key not in `~/.ssh/authorized_keys`
- SSH service down on droplet

**Fix**:

```bash
# Test SSH locally
ssh -i ~/.ssh/deploy_key root@45.55.173.72

# Regenerate and update secret
ssh-keygen -t ed25519 -C "github-deploy" -f ~/.ssh/new_deploy
# Copy ~/.ssh/new_deploy to DROPLET_SSH_KEY secret
# Add ~/.ssh/new_deploy.pub to droplet authorized_keys
```

#### 4. Docker Build Fails - Out of Space

**Error**: `no space left on device`  
**Cause**: Docker images/volumes consuming disk space

**Fix**:

```bash
# Manual cleanup on droplet
ssh root@45.55.173.72
docker system prune -af --volumes  # CAUTION: Removes all unused data
docker volume prune -f

# Or trigger cleanup workflow
Actions → Cleanup Docker Resources → Run workflow (cleanup_type: full)
```

---

## Performance Benchmarks

### Before Optimization (Dec 9, 2025)

| Workflow              | Duration | Frequency        | Monthly Cost |
| --------------------- | -------- | ---------------- | ------------ |
| deploy-intelligent    | ~10 min  | 30/month         | 300 min      |
| e2e-langsmith-eval    | ~12 min  | Daily (30/month) | 360 min      |
| evaluation-regression | ~20 min  | Weekly (4/month) | 80 min       |
| lint                  | ~2 min   | 100/month        | 200 min      |
| **Total**             | -        | -                | **940 min**  |

### After Optimization (Dec 13, 2025)

| Workflow              | Duration | Frequency        | Monthly Cost |
| --------------------- | -------- | ---------------- | ------------ |
| deploy-intelligent    | ~3 min   | 30/month         | 90 min       |
| weekly-evaluation     | ~5 min   | Weekly (4/month) | 20 min       |
| e2e-langsmith-eval    | ~15 min  | Manual (2/month) | 30 min       |
| evaluation-regression | ~12 min  | Weekly (4/month) | 48 min       |
| lint                  | ~30 sec  | 100/month        | 50 min       |
| **Total**             | -        | -                | **238 min**  |

**Savings**: **74% reduction** (940 → 238 min/month), **~$7/month saved** at GitHub Actions pricing

---

## Future Enhancements

### Planned (Q1 2025)

- [ ] **Staging environment** - Deploy to staging.codechef.appsmithery.co before production
- [ ] **Blue-green deployment** - Zero-downtime deployments with instant rollback
- [ ] **Canary releases** - Gradual rollout of new versions (10% → 50% → 100%)
- [ ] **Automated rollback** - Auto-rollback on health check failure or error rate spike
- [ ] **Slack notifications** - Post deployment status to #code-chef-deployments
- [ ] **Linear auto-linking** - Automatically link deployed commits to Linear issues

### Under Consideration

- [ ] **Deploy previews** - Ephemeral environments for PRs (Vercel/Netlify style)
- [ ] **Visual regression testing** - Percy or Chromatic for UI changes
- [ ] **Lighthouse CI** - Performance monitoring on every deployment
- [ ] **Load testing** - k6 or Locust integration for performance validation
- [ ] **Security scanning** - Snyk or Trivy for dependency vulnerabilities
- [ ] **DORA metrics** - Track deployment frequency, lead time, MTTR, change failure rate

---

## Resources

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Docker BuildKit](https://docs.docker.com/build/buildkit/)
- [LangSmith Tracing](https://docs.smith.langchain.com/)
- [Hypothesis Testing](https://hypothesis.readthedocs.io/)
- [OpenRouter API](https://openrouter.ai/docs)

---

**Last Updated**: December 13, 2025  
**Maintained by**: Alex Torelli (@alextorelli28)  
**Linear Project**: [CHEF](https://linear.app/dev-ops/project/codechef-78b3b839d36b)
