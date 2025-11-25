# Validate LangGraph Migration - Automated Checks
# This script validates that the repository is fully migrated to LangGraph architecture.

Write-Host "[Validation] Starting LangGraph migration validation..."

# 1. Check no old agent directories exist (consolidated into agent_orchestrator/agents/)
# Note: Agents are now LangGraph workflow nodes, not separate services
$oldAgents = @(
    "agent_feature-dev",
    "agent_code-review",
    "agent_infrastructure",
    "agent_cicd",
    "agent_documentation"
)
$missing = $true
foreach ($dir in $oldAgents) {
    if (Test-Path "../../$dir") {
        Write-Host "[FAIL] Deprecated agent directory still exists: $dir" -ForegroundColor Red
        $missing = $false
    }
}
if ($missing) { Write-Host "[PASS] No deprecated agent directories found." -ForegroundColor Green }

# 2. Verify docker-compose.yml has only orchestrator, gateway, rag, state, registry, postgres, redis, prometheus, caddy, loki, promtail
$compose = Get-Content "../../deploy/docker-compose.yml" -Raw
$legacyAgents = @("feature-dev", "code-review", "infrastructure", "cicd", "documentation")
$foundLegacy = $false
foreach ($agent in $legacyAgents) {
    if ($compose -match $agent) {
        Write-Host "[FAIL] Found legacy agent service in docker-compose.yml: $agent" -ForegroundColor Red
        $foundLegacy = $true
    }
}
if (-not $foundLegacy) { Write-Host "[PASS] No legacy agent services in docker-compose.yml." -ForegroundColor Green }

# 3. Confirm .env has no old agent URLs
$envFile = Get-Content "../../config/env/.env" -Raw
$envVars = @(
    "FEATURE_DEV_URL",
    "CODE_REVIEW_URL",
    "INFRASTRUCTURE_URL",
    "CICD_URL",
    "DOCUMENTATION_URL"
)
$foundEnv = $false
foreach ($var in $envVars) {
    if ($envFile -match $var) {
        Write-Host "[FAIL] Found deprecated env var in .env: $var" -ForegroundColor Red
        $foundEnv = $true
    }
}
if (-not $foundEnv) { Write-Host "[PASS] No deprecated agent URLs in .env." -ForegroundColor Green }

# 4. Validate all docs updated (keyword scan - excluding historical archives)
$docs = Get-ChildItem -Path "../../support/docs" -Filter "*.md" -Recurse | Where-Object { $_.FullName -notmatch "_archive" }
$keywords = @(
    "microservice",
    "agent_feature-dev",
    "agent_code-review",
    "agent_infrastructure",
    "agent_cicd",
    "agent_documentation"
)
$foundDoc = $false
foreach ($doc in $docs) {
    $content = Get-Content $doc.FullName -Raw
    foreach ($kw in $keywords) {
        if ($content -match $kw) {
            Write-Host "[FAIL] Found deprecated reference in $($doc.FullName): $kw" -ForegroundColor Red
            $foundDoc = $true
        }
    }
}
if (-not $foundDoc) { Write-Host "[PASS] No deprecated references in documentation." -ForegroundColor Green }

# 5. Test orchestrator health endpoint
try {
    $resp = Invoke-RestMethod -Uri "http://localhost:8001/health" -TimeoutSec 5
    if ($resp.status -eq "healthy") {
        Write-Host "[PASS] Orchestrator health endpoint OK." -ForegroundColor Green
    } else {
        Write-Host "[FAIL] Orchestrator health endpoint returned: $($resp | ConvertTo-Json)" -ForegroundColor Red
    }
} catch {
    Write-Host "[FAIL] Orchestrator health endpoint not reachable." -ForegroundColor Red
}

# 6. Verify LangGraph workflow compiles (basic import test)
try {
    python "../../agent_orchestrator/graph.py"
    Write-Host "[PASS] LangGraph workflow compiles." -ForegroundColor Green
} catch {
    Write-Host "[FAIL] LangGraph workflow import failed." -ForegroundColor Red
}

Write-Host "[Validation] LangGraph migration validation complete."
