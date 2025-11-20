#!/usr/bin/env pwsh
# Phase 6 Completion Validation Script
# Validates all Phase 6 implementations: tests, metrics, Prometheus config

Write-Host "`n=== Phase 6 Completion Validation ===" -ForegroundColor Cyan
Write-Host "This script validates:" -ForegroundColor Cyan
Write-Host "  1. Integration tests pass" -ForegroundColor Cyan
Write-Host "  2. Prometheus metrics are exported" -ForegroundColor Cyan
Write-Host "  3. Agent-registry is in Prometheus targets" -ForegroundColor Cyan
Write-Host "  4. Documentation is updated`n" -ForegroundColor Cyan

$ErrorActionPreference = "Continue"
$validationErrors = @()
$validationWarnings = @()

# ==========================================
# STEP 1: Run Integration Tests
# ==========================================
Write-Host "`n[1/6] Running integration tests..." -ForegroundColor Yellow

try {
    Write-Host "  - Checking pytest installation..." -ForegroundColor Gray
    $pytestVersion = python -m pytest --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "pytest not installed"
    }
    Write-Host "    ✅ pytest installed: $($pytestVersion -split "`n" | Select-Object -First 1)" -ForegroundColor Green
    
    Write-Host "  - Running test_multi_agent_workflows.py..." -ForegroundColor Gray
    $testOutput = python -m pytest support/tests/workflows/test_multi_agent_workflows.py -v --tb=short 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    ✅ All integration tests passed" -ForegroundColor Green
        $testOutput | Select-String "PASSED" | ForEach-Object { Write-Host "      $_" -ForegroundColor Green }
    } else {
        $validationErrors += "Integration tests failed"
        Write-Host "    ❌ Some tests failed:" -ForegroundColor Red
        $testOutput | Select-String "FAILED" | ForEach-Object { Write-Host "      $_" -ForegroundColor Red }
    }
} catch {
    $validationErrors += "Failed to run integration tests: $_"
    Write-Host "    ❌ Failed to run tests: $_" -ForegroundColor Red
}

# ==========================================
# STEP 2: Verify EventBus Metrics
# ==========================================
Write-Host "`n[2/6] Checking EventBus Prometheus metrics..." -ForegroundColor Yellow

$expectedEventBusMetrics = @(
    "event_bus_events_emitted_total",
    "event_bus_events_delivered_total",
    "event_bus_subscriber_errors_total",
    "agent_request_latency_seconds",
    "agent_requests_active",
    "agent_requests_total",
    "agent_responses_total",
    "agent_request_timeouts_total"
)

Write-Host "  - Searching for EventBus metric definitions in shared/lib/event_bus.py..." -ForegroundColor Gray
$eventBusContent = Get-Content shared/lib/event_bus.py -Raw

$foundMetrics = @()
foreach ($metric in $expectedEventBusMetrics) {
    if ($eventBusContent -match $metric) {
        $foundMetrics += $metric
        Write-Host "    ✅ $metric" -ForegroundColor Green
    } else {
        $validationErrors += "EventBus metric missing: $metric"
        Write-Host "    ❌ $metric (NOT FOUND)" -ForegroundColor Red
    }
}

Write-Host "  - EventBus metrics: $($foundMetrics.Count)/$($expectedEventBusMetrics.Count) found" -ForegroundColor $(if ($foundMetrics.Count -eq $expectedEventBusMetrics.Count) { "Green" } else { "Red" })

# ==========================================
# STEP 3: Verify ResourceLockManager Metrics
# ==========================================
Write-Host "`n[3/6] Checking ResourceLockManager Prometheus metrics..." -ForegroundColor Yellow

$expectedLockMetrics = @(
    "resource_lock_acquisitions_total",
    "resource_lock_wait_time_seconds",
    "resource_locks_active",
    "resource_lock_contentions_total",
    "resource_lock_releases_total",
    "resource_lock_timeouts_total"
)

Write-Host "  - Searching for ResourceLock metric definitions in shared/lib/resource_lock.py..." -ForegroundColor Gray
$lockContent = Get-Content shared/lib/resource_lock.py -Raw

$foundLockMetrics = @()
foreach ($metric in $expectedLockMetrics) {
    if ($lockContent -match $metric) {
        $foundLockMetrics += $metric
        Write-Host "    ✅ $metric" -ForegroundColor Green
    } else {
        $validationErrors += "ResourceLock metric missing: $metric"
        Write-Host "    ❌ $metric (NOT FOUND)" -ForegroundColor Red
    }
}

Write-Host "  - ResourceLock metrics: $($foundLockMetrics.Count)/$($expectedLockMetrics.Count) found" -ForegroundColor $(if ($foundLockMetrics.Count -eq $expectedLockMetrics.Count) { "Green" } else { "Red" })

# ==========================================
# STEP 4: Verify Prometheus Configuration
# ==========================================
Write-Host "`n[4/6] Checking Prometheus scraping configuration..." -ForegroundColor Yellow

Write-Host "  - Checking if agent-registry is in prometheus.yml..." -ForegroundColor Gray
$prometheusConfig = Get-Content config/prometheus/prometheus.yml -Raw

if ($prometheusConfig -match "agent-registry") {
    Write-Host "    ✅ agent-registry scrape target found" -ForegroundColor Green
    
    # Extract the agent-registry section
    $registrySection = $prometheusConfig | Select-String -Pattern "- job_name.*agent-registry" -Context 0,5
    if ($registrySection) {
        Write-Host "      Configuration:" -ForegroundColor Gray
        $registrySection.Context.PostContext | ForEach-Object { Write-Host "        $_" -ForegroundColor Gray }
    }
} else {
    $validationErrors += "agent-registry not found in Prometheus config"
    Write-Host "    ❌ agent-registry scrape target NOT FOUND" -ForegroundColor Red
}

# Check all expected scrape targets
$expectedTargets = @("orchestrator", "feature-dev", "code-review", "infrastructure", "cicd", "documentation", "gateway-mcp", "rag-context", "state-persistence", "agent-registry")
$foundTargets = @()

foreach ($target in $expectedTargets) {
    if ($prometheusConfig -match "job_name.*[`"']$target[`"']") {
        $foundTargets += $target
    }
}

Write-Host "  - Prometheus scrape targets: $($foundTargets.Count)/$($expectedTargets.Count) configured" -ForegroundColor $(if ($foundTargets.Count -eq $expectedTargets.Count) { "Green" } else { "Yellow" })

# ==========================================
# STEP 5: Verify Documentation Updates
# ==========================================
Write-Host "`n[5/6] Checking documentation updates..." -ForegroundColor Yellow

$docFiles = @(
    @{Path="support/docs/EVENT_PROTOCOL.md"; ExpectedSections=@("Complete Usage Examples", "Error Handling Patterns", "Best Practices", "Prometheus Metrics")},
    @{Path="support/docs/AGENT_REGISTRY.md"; ExpectedSections=@("Complete Integration Examples", "Discovery Workflow", "Error Handling Best Practices", "Prometheus Metrics")},
    @{Path="support/docs/RESOURCE_LOCKING.md"; ExpectedSections=@("Complete Usage Examples", "Common Patterns", "Error Handling Best Practices", "Prometheus Metrics")}
)

foreach ($doc in $docFiles) {
    Write-Host "  - Checking $($doc.Path)..." -ForegroundColor Gray
    
    if (-not (Test-Path $doc.Path)) {
        $validationErrors += "Documentation file not found: $($doc.Path)"
        Write-Host "    ❌ File not found" -ForegroundColor Red
        continue
    }
    
    $content = Get-Content $doc.Path -Raw
    $foundSections = @()
    
    foreach ($section in $doc.ExpectedSections) {
        if ($content -match $section) {
            $foundSections += $section
        } else {
            $validationWarnings += "Section missing in $($doc.Path): $section"
        }
    }
    
    $sectionCount = $foundSections.Count
    $totalSections = $doc.ExpectedSections.Count
    
    if ($sectionCount -eq $totalSections) {
        Write-Host "    ✅ All $totalSections sections present" -ForegroundColor Green
    } else {
        Write-Host "    ⚠️  $sectionCount/$totalSections sections found" -ForegroundColor Yellow
        $doc.ExpectedSections | Where-Object { $_ -notin $foundSections } | ForEach-Object {
            Write-Host "      - Missing: $_" -ForegroundColor Yellow
        }
    }
}

# ==========================================
# STEP 6: Check for Dependencies
# ==========================================
Write-Host "`n[6/6] Checking Python dependencies..." -ForegroundColor Yellow

$requiredPackages = @("pytest", "pytest-asyncio", "prometheus-client", "asyncpg")

foreach ($package in $requiredPackages) {
    Write-Host "  - Checking $package..." -ForegroundColor Gray
    $installed = python -m pip show $package 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        $version = ($installed | Select-String "Version:").ToString().Split(":")[1].Trim()
        Write-Host "    ✅ $package ($version) installed" -ForegroundColor Green
    } else {
        $validationWarnings += "Python package not installed: $package"
        Write-Host "    ⚠️  $package not installed" -ForegroundColor Yellow
    }
}

# ==========================================
# Summary
# ==========================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "VALIDATION SUMMARY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($validationErrors.Count -eq 0) {
    Write-Host "`n✅ ALL CRITICAL CHECKS PASSED" -ForegroundColor Green
    Write-Host "`nPhase 6 implementation is COMPLETE and validated!" -ForegroundColor Green
} else {
    Write-Host "`n❌ CRITICAL ISSUES FOUND: $($validationErrors.Count)" -ForegroundColor Red
    foreach ($error in $validationErrors) {
        Write-Host "  - $error" -ForegroundColor Red
    }
}

if ($validationWarnings.Count -gt 0) {
    Write-Host "`n⚠️  WARNINGS: $($validationWarnings.Count)" -ForegroundColor Yellow
    foreach ($warning in $validationWarnings) {
        Write-Host "  - $warning" -ForegroundColor Yellow
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "NEXT STEPS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "`n1. Run tests locally:" -ForegroundColor White
Write-Host "   cd support/tests/workflows" -ForegroundColor Gray
Write-Host "   pytest test_multi_agent_workflows.py -v -s" -ForegroundColor Gray

Write-Host "`n2. Deploy to droplet and verify metrics:" -ForegroundColor White
Write-Host "   ./support/scripts/deploy.ps1 -Target remote" -ForegroundColor Gray
Write-Host "   ssh root@45.55.173.72 `"docker compose -f /opt/Dev-Tools/deploy/docker-compose.yml restart orchestrator`"" -ForegroundColor Gray
Write-Host "   curl http://localhost:8001/metrics | grep event_bus" -ForegroundColor Gray

Write-Host "`n3. Check Prometheus UI:" -ForegroundColor White
Write-Host "   http://localhost:9090/targets" -ForegroundColor Gray
Write-Host "   Query: event_bus_events_emitted_total" -ForegroundColor Gray

Write-Host "`n4. Validate LangSmith traces:" -ForegroundColor White
Write-Host "   https://smith.langchain.com" -ForegroundColor Gray
Write-Host "   Filter by: tags=['orchestrator', 'multi-agent']" -ForegroundColor Gray

Write-Host "`n5. Mark Phase 6 complete in Linear:" -ForegroundColor White
Write-Host "   Update PR-68 with completion status" -ForegroundColor Gray

Write-Host ""

# Exit with appropriate code
if ($validationErrors.Count -gt 0) {
    exit 1
} else {
    exit 0
}
