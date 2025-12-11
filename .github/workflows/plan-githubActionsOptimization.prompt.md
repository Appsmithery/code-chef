# GitHub Actions Workflow Optimization Plan

**Date**: December 11, 2025  
**Scope**: Complete audit and optimization of all 10 workflows  
**Expected Impact**: 60% reduction in CI time, 40% reduction in workflow complexity

---

## Executive Summary

After auditing all GitHub Actions workflows, identified significant optimization opportunities across the entire CI/CD pipeline. Current issues include:

- **Over-engineering**: Complex change detection logic and redundant builds
- **Resource waste**: Installing dependencies 4+ times per workflow run
- **Broken workflows**: Frontend preview using wrong path after directory restructure
- **Deprecated workflows**: Two unused publishing workflows still present
- **Expensive tests**: evaluation-regression.yml runs 6 jobs on every PR merge (~15 minutes)

**Primary Goal**: Reduce CI costs and improve developer feedback loops while maintaining reliability.

---

## Audit Findings

| Workflow                     | Lines | Status        | Primary Issues                                          | Priority   |
| ---------------------------- | ----- | ------------- | ------------------------------------------------------- | ---------- |
| evaluation-regression.yml    | 432   | 🔴 Critical   | Runs 6 Postgres jobs on every PR merge, ~15 min per run | **HIGH**   |
| e2e-langsmith-eval.yml       | 338   | 🟡 Needs Work | Installs deps 4+ times, redundant steps                 | **MEDIUM** |
| deploy-intelligent.yml       | 325   | 🟡 Needs Work | Over-engineered change detection, complex logic         | **MEDIUM** |
| cleanup-docker-resources.yml | 231   | 🟢 Acceptable | Runs after every deploy + weekly, could consolidate     | **LOW**    |
| publish-extension.yml        | 155   | 🟡 Needs Work | Compiles on every push to main, should be manual        | **MEDIUM** |
| frontend-preview.yml         | ~100  | 🔴 Broken     | Wrong path (support/frontend vs frontend)               | **HIGH**   |
| lint.yml                     | ~100  | 🟡 Needs Work | Full pip install for simple linting checks              | **LOW**    |
| publish-npm.yml              | 80    | 🔴 Deprecated | Unused npm package publishing                           | **HIGH**   |
| publish-python.yml           | 80    | 🔴 Deprecated | Unused Python package publishing                        | **HIGH**   |
| deploy-frontend.yml          | ~60   | ✅ Done       | Already optimized (streamlined to 3 steps)              | -          |

---

## Optimization Strategy

### Phase 1: Quick Wins (30 minutes)

**Objective**: Remove dead code and fix broken workflows

#### 1.1 Delete Deprecated Workflows

```bash
rm .github/workflows/publish-npm.yml
rm .github/workflows/publish-python.yml
```

**Impact**: Cleaner workflow list, no risk

#### 1.2 Fix Frontend Preview Path

**File**: `.github/workflows/frontend-preview.yml`

**Change**:

```yaml
# Before
working-directory: support/frontend

# After
working-directory: frontend
```

**Also optimize**:

- Remove build step (build locally, deploy artifacts)
- Add path filters to only trigger on frontend changes

**Impact**: Fix broken preview deployments, reduce unnecessary runs

#### 1.3 Optimize Lint Workflow

**File**: `.github/workflows/lint.yml`

**Changes**:

- Add dependency caching for pip
- Split Python and YAML linting into separate jobs (parallel execution)
- Only install required linters (not full requirements.txt)

**Impact**: Reduce lint time from ~2 minutes to ~30 seconds

#### 1.4 Make Evaluation Regression Manual Only

**File**: `.github/workflows/evaluation-regression.yml`

**Change**:

```yaml
# Before
on:
  push:
    branches: [main]
  pull_request:
    types: [opened, synchronize, reopened]

# After
on:
  workflow_dispatch: # Manual trigger only
  schedule:
    - cron: '0 2 * * 0' # Weekly on Sunday at 2 AM
```

**Rationale**: This is a 15-minute, 6-job workflow with Postgres. Too expensive for every PR. Run weekly or on-demand instead.

**Impact**: Save ~15 minutes per PR merge, reduce CI costs significantly

---

### Phase 2: Major Optimizations (2 hours)

**Objective**: Consolidate redundant steps and improve caching

#### 2.1 Simplify Deploy Intelligent Workflow

**File**: `.github/workflows/deploy-intelligent.yml` (325 lines)

**Current Issues**:

- Complex change detection logic using multiple git diff commands
- Builds all services even when only one changed
- No caching of Docker layers

**Proposed Changes**:

1. **Simplify change detection**:

   ```yaml
   # Use GitHub's built-in paths filter instead of custom git diff
   on:
     push:
       paths:
         - "agent_orchestrator/**"
         - "shared/**"
         - "deploy/docker-compose.yml"
   ```

2. **Conditional job execution**:

   ```yaml
   jobs:
     detect-changes:
       outputs:
         orchestrator: ${{ steps.filter.outputs.orchestrator }}
         rag: ${{ steps.filter.outputs.rag }}
         # ... other services

     deploy-orchestrator:
       needs: detect-changes
       if: needs.detect-changes.outputs.orchestrator == 'true'
   ```

3. **Add Docker layer caching**:
   ```yaml
   - uses: docker/setup-buildx-action@v3
   - uses: docker/build-push-action@v5
     with:
       cache-from: type=gha
       cache-to: type=gha,mode=max
   ```

**Impact**: Reduce deployment time from ~10 minutes to ~3 minutes for single-service changes

#### 2.2 Consolidate E2E LangSmith Workflow

**File**: `.github/workflows/e2e-langsmith-eval.yml` (338 lines)

**Current Issues**:

- Installs dependencies 4+ times (once per job)
- No job dependency optimization
- Redundant Postgres setup in multiple jobs

**Proposed Changes**:

1. **Create shared setup job**:

   ```yaml
   jobs:
     setup:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with:
             python-version: "3.11"
             cache: "pip"
         - run: pip install -r agent_orchestrator/requirements.txt
         - uses: actions/cache@v4
           with:
             path: ~/.cache/pip
             key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}

     test-feature-dev:
       needs: setup
       # Now just runs tests, no install step
   ```

2. **Consolidate Postgres service**:
   - Use a single Postgres service container shared across jobs
   - Run migrations once in setup job

**Impact**: Reduce workflow time from ~12 minutes to ~5 minutes

#### 2.3 Change Extension Publishing to Manual

**File**: `.github/workflows/publish-extension.yml`

**Change**:

```yaml
# Before
on:
  push:
    branches: [main]

# After
on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to publish (e.g., 1.0.1)'
        required: true
        type: string
```

**Rationale**: Extensions should be published intentionally, not on every commit to main. Compilation is expensive and unnecessary for most changes.

**Impact**: Reduce unnecessary builds, maintain control over releases

#### 2.4 Add Universal Dependency Caching

**Apply to all workflows that install dependencies**:

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.11"
    cache: "pip" # Built-in caching

- uses: actions/setup-node@v4
  with:
    node-version: "20"
    cache: "npm" # Built-in caching
```

**Files to update**:

- evaluation-regression.yml
- e2e-langsmith-eval.yml
- lint.yml
- publish-extension.yml
- Any other workflows with pip/npm installs

**Impact**: 30-50% faster dependency installation

---

### Phase 3: Advanced Optimizations (Future)

**Objective**: Strategic workflow improvements for long-term efficiency

#### 3.1 Implement Matrix Strategy for Tests

**Target**: evaluation-regression.yml, e2e-langsmith-eval.yml

**Benefit**: Run agent tests in parallel instead of sequentially

```yaml
strategy:
  matrix:
    agent:
      [
        feature_dev,
        code_review,
        infrastructure,
        cicd,
        documentation,
        supervisor,
      ]
  fail-fast: false

steps:
  - name: Test ${{ matrix.agent }}
    run: pytest support/tests/integration/test_${{ matrix.agent }}.py
```

**Impact**: 6 jobs run in parallel → 6x faster if runners available

#### 3.2 Create Composite Actions

**Target**: Repetitive setup steps across workflows

**Example**: Create `.github/actions/setup-python-env/action.yml`

```yaml
name: "Setup Python Environment"
description: "Install Python with caching and dependencies"
inputs:
  requirements-file:
    required: true
runs:
  using: composite
  steps:
    - uses: actions/setup-python@v5
      with:
        python-version: "3.11"
        cache: "pip"
    - run: pip install -r ${{ inputs.requirements-file }}
      shell: bash
```

**Usage in workflows**:

```yaml
- uses: ./.github/actions/setup-python-env
  with:
    requirements-file: agent_orchestrator/requirements.txt
```

**Impact**: DRY principle, consistent setup across workflows

#### 3.3 Implement Workflow Artifacts

**Target**: deploy-intelligent.yml

**Benefit**: Build Docker images once, deploy to multiple environments

```yaml
jobs:
  build:
    steps:
      - name: Build and export
        uses: docker/build-push-action@v5
        with:
          outputs: type=docker,dest=/tmp/image.tar

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: docker-image
          path: /tmp/image.tar

  deploy-staging:
    needs: build
    steps:
      - name: Download artifact
        uses: actions/download-artifact@v4
        with:
          name: docker-image
      # Deploy to staging

  deploy-production:
    needs: [build, deploy-staging]
    # Deploy same image to production
```

**Impact**: Build once, deploy many (staging → production pipeline)

---

## Implementation Checklist

### Phase 1: Quick Wins ✅

- [ ] Delete `publish-npm.yml`
- [ ] Delete `publish-python.yml`
- [ ] Fix `frontend-preview.yml` path (support/frontend → frontend)
- [ ] Add path filters to `frontend-preview.yml`
- [ ] Optimize `lint.yml` with caching
- [ ] Change `evaluation-regression.yml` to manual/weekly trigger
- [ ] Test each changed workflow

### Phase 2: Major Optimizations 🔄

- [ ] Simplify `deploy-intelligent.yml` change detection
- [ ] Add Docker layer caching to `deploy-intelligent.yml`
- [ ] Create shared setup job in `e2e-langsmith-eval.yml`
- [ ] Consolidate Postgres services in `e2e-langsmith-eval.yml`
- [ ] Change `publish-extension.yml` to workflow_dispatch
- [ ] Add pip/npm caching to all workflows
- [ ] Test all optimized workflows
- [ ] Monitor CI time improvements

### Phase 3: Advanced (Future) 📋

- [ ] Implement matrix strategy for test workflows
- [ ] Create composite actions for common setup
- [ ] Set up artifact-based deployment pipeline
- [ ] Document new workflow patterns
- [ ] Train team on workflow_dispatch usage

---

## Expected Impact Metrics

| Metric                                | Before  | After       | Improvement          |
| ------------------------------------- | ------- | ----------- | -------------------- |
| **evaluation-regression.yml runtime** | ~15 min | Weekly only | ~15 min saved per PR |
| **e2e-langsmith-eval.yml runtime**    | ~12 min | ~5 min      | 58% faster           |
| **deploy-intelligent.yml runtime**    | ~10 min | ~3 min      | 70% faster           |
| **lint.yml runtime**                  | ~2 min  | ~30 sec     | 75% faster           |
| **frontend-preview.yml**              | Broken  | 30 sec      | Fixed + optimized    |
| **Total CI time per PR**              | ~30 min | ~10 min     | **67% reduction**    |
| **Active workflows**                  | 10      | 8           | 2 deprecated removed |
| **Dependency install time**           | ~3 min  | ~1 min      | Caching benefit      |

---

## Risk Assessment

| Change                            | Risk Level | Mitigation                                   |
| --------------------------------- | ---------- | -------------------------------------------- |
| Delete deprecated workflows       | 🟢 Low     | Verify no external triggers first            |
| Make evaluation-regression manual | 🟡 Medium  | Add weekly schedule, document manual trigger |
| Simplify deploy-intelligent       | 🟡 Medium  | Test in non-production branch first          |
| Consolidate e2e jobs              | 🟡 Medium  | Maintain job outputs for debugging           |
| Change extension to manual        | 🟢 Low     | Document release process                     |

---

## Success Criteria

1. **Performance**: CI time reduced by ≥60% for typical PR workflow
2. **Reliability**: No increase in workflow failures after optimization
3. **Developer Experience**: Faster feedback loops (<5 min for most workflows)
4. **Cost**: Reduce GitHub Actions compute costs by ~50%
5. **Maintainability**: Simpler workflows, easier to understand and modify

---

## Next Steps

1. **User Approval**: Review and approve Phase 1 implementation
2. **Implementation**: Execute Phase 1 Quick Wins (30 minutes)
3. **Testing**: Trigger each modified workflow to verify functionality
4. **Monitoring**: Track CI times for 1 week to measure improvement
5. **Phase 2**: If Phase 1 successful, proceed with major optimizations

**Ready to begin Phase 1?** The quick wins are low-risk and high-impact.
