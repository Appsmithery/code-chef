# Phase 6 Integration Validation Script
# Validates that all agents have required Phase 6 features

$ErrorActionPreference = "Continue"

Write-Host "[*] Validating Phase 6 Integration..." -ForegroundColor Cyan
Write-Host "====================================`n" -ForegroundColor Cyan

$agents = @("orchestrator", "feature-dev", "code-review", "infrastructure", "cicd", "documentation")
$results = @{}
$overallPass = $true

foreach ($agent in $agents) {
    Write-Host "Checking $agent..." -ForegroundColor Yellow

    $mainPath = "agent_$agent/main.py"

    if (-not (Test-Path $mainPath)) {
        Write-Host "  ❌ $mainPath not found`n" -ForegroundColor Red
        $overallPass = $false
        continue
    }

    $content = Get-Content $mainPath -Raw

    $checks = @{
        "RegistryClient import" = $content -match "from lib.registry_client import"
        "Event Bus import" = $content -match "from lib.event_bus import get_event_bus"
        "Agent events import" = $content -match "from lib.agent_events import"
        "LangGraph checkpointer" = $content -match "checkpointer = get_postgres_checkpointer"
        "Qdrant client" = $content -match "qdrant_client = get_qdrant_client"
        "Hybrid memory" = ($content -match "hybrid_memory = create_hybrid_memory") -or ($content -match "from lib.langchain_memory import")
        "Lifespan manager" = $content -match "@asynccontextmanager"
        "Registry client global" = ($content -match "registry_client:.*RegistryClient") -or ($content -match "registry_client = None")
        "Agent request endpoint" = $content -match '/agent-request'
        "Registry registration" = $content -match "await registry_client.register"
        "Event bus connection" = $content -match "await event_bus.connect"
        "Heartbeat start" = $content -match "await registry_client.start_heartbeat"
        "Heartbeat stop" = $content -match "await registry_client.stop_heartbeat"
        "Lifespan in FastAPI" = $content -match 'lifespan=lifespan'
    }

    $results[$agent] = $checks

    $agentPassed = $true
    foreach ($check in $checks.Keys) {
        $passed = $checks[$check]
        $status = if ($passed) { "[OK]" } else { "[FAIL]"; $agentPassed = $false; $overallPass = $false }
        $color = if ($passed) { "Green" } else { "Red" }
        Write-Host "  $status $check" -ForegroundColor $color
    }

    Write-Host ""
}

# Summary
Write-Host "[*] Summary" -ForegroundColor Cyan
Write-Host "==========" -ForegroundColor Cyan

$totalChecks = 0
$passedChecks = 0

foreach ($agent in $results.Keys) {
    $agentChecks = $results[$agent]
    $agentTotal = $agentChecks.Count
    $agentPassed = ($agentChecks.Values | Where-Object { $_ }).Count

    $totalChecks += $agentTotal
    $passedChecks += $agentPassed

    $percentage = if ($agentTotal -gt 0) { [math]::Round(($agentPassed / $agentTotal) * 100, 1) } else { 0 }
    $status = if ($agentPassed -eq $agentTotal) { "[OK]" } else { "[WARN]" }
    $color = if ($agentPassed -eq $agentTotal) { "Green" } else { "Yellow" }

    Write-Host "$status $agent : $agentPassed/$agentTotal ($percentage%)" -ForegroundColor $color
}

Write-Host ""
$overallPercentage = if ($totalChecks -gt 0) { [math]::Round(($passedChecks / $totalChecks) * 100, 1) } else { 0 }
Write-Host "Overall: $passedChecks / $totalChecks checks ($overallPercentage%)" -ForegroundColor $(if ($overallPass) { "Green" } else { "Yellow" })

if ($overallPass) {
    Write-Host "`n[SUCCESS] All agents ready for Phase 6!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n[WARN] Some agents need manual fixes" -ForegroundColor Yellow
    Write-Host "Run: .\support\scripts\maintenance\inject-phase6-features.ps1" -ForegroundColor Cyan
    exit 1
}
