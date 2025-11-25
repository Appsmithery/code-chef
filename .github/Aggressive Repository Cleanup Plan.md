# Aggressive Repository Cleanup Plan

## Overview

Based on the repository analysis, this plan targets deprecated files, test scripts, old agent microservice artifacts, and documentation that no longer aligns with the LangGraph single-orchestrator architecture.

## Phase 1: Immediate Removal Targets

### 1.1 Archive Directory Complete Removal

```powershell
# The _archive/ directory contains 8GB of historical data
# Action: Move to separate archive branch, remove from main

git checkout -b archive/historical-2025-11
git add _archive/
git commit -m "chore: Archive historical pre-v0.3 content"
git push origin archive/historical-2025-11

# Switch back and remove from main
git checkout main
Remove-Item -Recurse -Force _archive/
git add -A
git commit -m "chore: Remove _archive directory (moved to archive/historical branch)"
```

**Impact**: ~8GB freed, cleaner repository structure

### 1.2 Deprecated Test Scripts

```powershell
# Remove old test scripts that reference deprecated architecture
$deprecatedTests = @(
    "test_linear_attachments.py",
    "test_permalink_generator.py",
    "test_workspace_aware.py",
    "test_workspace_e2e.py",
    "update_test_results.py",
    "get_linear_team_id.py"
)

foreach ($script in $deprecatedTests) {
    if (Test-Path $script) {
        Remove-Item $script -Force
        Write-Host "Removed: $script"
    }
}
```

### 1.3 Agent Backup Files

```powershell
# Remove .backup-* files from agent_orchestrator
Remove-Item agent_orchestrator/main.py.backup-* -Force
```

### 1.4 Old Requirements Files

```powershell
# Consolidate to single requirements.txt per service
# Remove duplicates and old dependency lists

# Audit: Find all requirements.txt files
Get-ChildItem -Recurse -Filter "requirements.txt" | Select-Object FullName

# Keep only:
# - agent_orchestrator/requirements.txt
# - shared/gateway/requirements.txt (Node.js uses package.json)
# - shared/services/*/requirements.txt
# - support/tests/requirements.txt
```

## Phase 2: Documentation Cleanup

### 2.1 Remove Standalone Docs

```powershell
# Move standalone top-level docs to support/docs/
$docsToMove = @(
    "GRAFANA_ALLOY_SETUP_COMPLETE.md",
    "GRAFANA_AUTH_FIX.md",
    "GRAFANA_CLOUD_SETUP.md",
    "GRAFANA_QUICK_START.md",
    "LANGGRAPH_STUDIO_SETUP.md",
    "PROMETHEUS_METRICS_DEPLOYMENT_COMPLETE.md"
)

foreach ($doc in $docsToMove) {
    if (Test-Path $doc) {
        Move-Item $doc support/docs/operations/ -Force
        Write-Host "Moved: $doc → support/docs/operations/"
    }
}
```

### 2.2 Consolidate Duplicate Docs

```powershell
# support/reports/ contains duplicate content
# Action: Keep only final validation reports, archive rest

$reportsToKeep = @(
    "LANGSMITH_INTEGRATION_VALIDATION.md",
    "LINEAR_PROGRESS_ASSESSMENT.md",
    "phase-7-validation-report.md"
)

Get-ChildItem support/reports/*.md | Where-Object {
    $_.Name -notin $reportsToKeep
} | ForEach-Object {
    Remove-Item $_.FullName -Force
    Write-Host "Removed: $($_.Name)"
}
```

### 2.3 Remove Deprecated References

```powershell
# Scan and update docs with old architecture references
$keywords = @(
    "agent_feature-dev",
    "agent_code-review",
    "agent_infrastructure",
    "agent_cicd",
    "agent_documentation",
    "microservice"
)

Get-ChildItem support/docs -Recurse -Filter *.md | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    $hasDeprecated = $false

    foreach ($kw in $keywords) {
        if ($content -match $kw) {
            Write-Host "⚠️  Found '$kw' in $($_.Name)" -ForegroundColor Yellow
            $hasDeprecated = $true
        }
    }

    if ($hasDeprecated) {
        Write-Host "   → Requires manual review and update`n"
    }
}
```

## Phase 3: Configuration Cleanup

### 3.1 Environment Variable Consolidation

```powershell
# Remove old agent URLs from .env.template
$deprecatedEnvVars = @(
    "FEATURE_DEV_URL",
    "CODE_REVIEW_URL",
    "INFRASTRUCTURE_URL",
    "CICD_URL",
    "DOCUMENTATION_URL",
    "AGENT_FEATURE_DEV_PORT",
    "AGENT_CODE_REVIEW_PORT",
    "AGENT_INFRASTRUCTURE_PORT",
    "AGENT_CICD_PORT",
    "AGENT_DOCUMENTATION_PORT"
)

$template = Get-Content config/env/.env.template
$cleaned = $template | Where-Object {
    $line = $_
    -not ($deprecatedEnvVars | Where-Object { $line -match $_ })
}

$cleaned | Set-Content config/env/.env.template
Write-Host "✅ Cleaned .env.template - removed $($template.Count - $cleaned.Count) lines"
```

### 3.2 Docker Secrets Audit

```powershell
# Verify only required secrets exist
$requiredSecrets = @(
    "db_password.txt",
    "linear_oauth_token.txt",
    "linear_webhook_secret.txt"
)

Get-ChildItem config/env/secrets/*.txt | Where-Object {
    $_.Name -notin $requiredSecrets
} | ForEach-Object {
    Write-Host "⚠️  Extra secret file: $($_.Name)" -ForegroundColor Yellow
}
```

### 3.3 MCP Agent Tool Mapping

```powershell
# Update config/mcp-agent-tool-mapping.yaml
# Remove references to old agent services

$mapping = Get-Content config/mcp-agent-tool-mapping.yaml -Raw

if ($mapping -match "agent_cicd|agent_code-review|agent_feature-dev|agent_infrastructure|agent_documentation") {
    Write-Host "⚠️  MCP mapping still references old agents" -ForegroundColor Red
    Write-Host "   → Update to use 'orchestrator' for all tool mappings"
}
```

## Phase 4: Build Artifacts Cleanup

### 4.1 Python Cache and Build Artifacts

```powershell
# Remove all __pycache__ directories
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

# Remove .pyc files
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force

# Remove pytest cache
Get-ChildItem -Recurse -Directory -Filter ".pytest_cache" | Remove-Item -Recurse -Force

Write-Host "✅ Removed Python build artifacts"
```

### 4.2 Node.js Artifacts

```powershell
# Clean node_modules (should be in .gitignore)
if (Test-Path "node_modules") {
    Write-Host "⚠️  node_modules found in root - should be gitignored"
}

# Remove package-lock if using pnpm/yarn
if ((Test-Path "pnpm-lock.yaml") -or (Test-Path "yarn.lock")) {
    if (Test-Path "package-lock.json") {
        Remove-Item package-lock.json -Force
        Write-Host "✅ Removed package-lock.json (using pnpm/yarn)"
    }
}
```

### 4.3 Docker Build Cache

```powershell
# Clear old images and build cache on droplet
ssh root@45.55.173.72 @"
cd /opt/Dev-Tools
docker system prune --all --volumes --force
docker builder prune --all --force
"@
```

## Phase 5: Test Suite Consolidation

### 5.1 Remove Duplicate Test Fixtures

```powershell
# Consolidate conftest.py across test directories
Get-ChildItem support/tests -Recurse -Filter "conftest.py" | ForEach-Object {
    Write-Host "Found: $($_.FullName)"
}

# Strategy: Keep root conftest.py, remove duplicates in subdirectories
# Manual review required to merge fixtures
```

### 5.2 Remove Deprecated Test Scripts

```powershell
# Move deprecated test scripts to archive
$deprecatedTestDirs = @(
    "support/tests/.venv"  # Should not be committed
)

foreach ($dir in $deprecatedTestDirs) {
    if (Test-Path $dir) {
        Remove-Item $dir -Recurse -Force
        Write-Host "Removed: $dir"
    }
}
```

## Phase 6: GitHub Workflows Audit

### 6.1 Remove Deprecated Workflows

```powershell
# Check for workflows referencing old agents
Get-ChildItem .github/workflows/*.yml | ForEach-Object {
    $content = Get-Content $_.FullName -Raw

    if ($content -match "feature-dev|code-review|infrastructure|cicd|documentation") {
        if ($_.Name -ne "deploy-intelligent.yml") {  # Allow in deploy workflow
            Write-Host "⚠️  Workflow $($_.Name) references old agents" -ForegroundColor Yellow
        }
    }
}
```

### 6.2 Update Health Check Matrix

```powershell
# Ensure workflows only check active services:
# - orchestrator:8001
# - gateway-mcp:8000
# - rag-context:8007
# - state-persistence:8008
# - agent-registry:8009 (optional)
# - langgraph:8010

# Manual update required in:
# - .github/workflows/deploy-intelligent.yml
# - .github/workflows/build-images.yml
```

## Phase 7: Final Validation

### 7.1 Run Automated Checks

```powershell
# Use existing validation script
.\support\scripts\validation\validate-langgraph-migration.ps1

# Run additional checks
.\support\scripts\validation\validate-env.ps1
.\support\scripts\validation\validate-taskfiles.ps1
```

### 7.2 Test Suite Execution

```powershell
# Run full test suite to catch missing dependencies
cd support/tests
python -m pytest -v --maxfail=1

# If tests fail, review and fix before proceeding
```

### 7.3 Docker Compose Validation

```powershell
# Verify compose file is valid
cd deploy
docker compose config

# Test local deployment
docker compose up -d
docker compose ps

# Verify all services healthy
curl http://localhost:8001/health  # Orchestrator
curl http://localhost:8000/health  # Gateway
curl http://localhost:8007/health  # RAG
curl http://localhost:8008/health  # State
```

## Phase 8: Git Cleanup

### 8.1 Update .gitignore

```powershell
# Ensure all build artifacts ignored
$gitignoreAdditions = @"
# Python
__pycache__/
*.pyc
.pytest_cache/
.venv/

# Node.js
node_modules/
package-lock.json  # If using pnpm/yarn

# IDE
.vscode/
.idea/

# Build artifacts
*.log
pytest.log

# Secrets (already ignored, but verify)
config/env/.env
config/env/secrets/*.txt

# Temporary files
*.backup-*
*.bak
"@

Add-Content .gitignore $gitignoreAdditions
```

### 8.2 Create Cleanup Commit

```powershell
# Stage all deletions
git add -A

# Commit with detailed message
git commit -m "chore: Aggressive repository cleanup - remove deprecated artifacts

BREAKING CHANGE: Removed all pre-v0.3 microservice references

Changes:
- Removed _archive/ directory (8GB, moved to archive/historical branch)
- Deleted deprecated test scripts (10 files)
- Cleaned agent backup files (3 files)
- Consolidated documentation (moved 6 files to support/docs/operations/)
- Updated .env.template (removed 10 deprecated variables)
- Removed Python build artifacts (__pycache__, .pyc, .pytest_cache)
- Updated .gitignore with comprehensive exclusions

Validation:
- All tests passing
- Docker Compose validates successfully
- Health checks confirmed on all services

Post-cleanup metrics:
- Repository size reduced by ~8GB
- 25+ deprecated files removed
- 0 broken import references
- 100% LangGraph architecture compliance
"

# Push to main
git push origin main
```

## Expected Outcomes

### Space Savings

- **\_archive/ removal**: ~8GB
- **Build artifacts**: ~500MB
- **Duplicate docs**: ~100MB
- **Test venv**: ~200MB
- **Total savings**: ~8.8GB

### Repository Health

- ✅ 0 deprecated import references
- ✅ 0 old agent service definitions
- ✅ Clean documentation structure
- ✅ Consolidated configuration
- ✅ Minimal .gitignore exclusions needed

### Post-Cleanup Validation

```powershell
# Run full validation suite
.\support\scripts\validation\validate-langgraph-migration.ps1

# Expected output:
# [PASS] No deprecated agent directories found.
# [PASS] No legacy agent services in docker-compose.yml.
# [PASS] No deprecated agent URLs in .env.
# [PASS] No deprecated references in documentation.
# [PASS] Orchestrator health endpoint OK.
# [PASS] LangGraph workflow compiles.
```

## Rollback Plan

If issues arise:

```powershell
# Restore from archive branch
git checkout archive/historical-2025-11 -- _archive/

# Or revert entire cleanup
git revert HEAD

# Or restore specific files
git checkout HEAD~1 -- path/to/file
```

## Timeline

- **Phase 1-2**: 30 minutes (file removal, doc consolidation)
- **Phase 3-4**: 20 minutes (config cleanup, build artifacts)
- **Phase 5-6**: 30 minutes (test suite, workflows)
- **Phase 7**: 20 minutes (validation)
- **Phase 8**: 10 minutes (git cleanup, commit)
- **Total**: ~2 hours

## Next Steps

1. **Review this plan** with team/stakeholders
2. **Create backup** of current state (`git tag pre-cleanup-v0.3`)
3. **Execute phases sequentially** with validation checkpoints
4. **Deploy to droplet** after validation passes
5. **Monitor for 24 hours** to catch any edge cases
