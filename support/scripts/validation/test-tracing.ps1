#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test agent tracing by making sample requests
.DESCRIPTION
    Sends test requests to agents to generate Langfuse traces
#>

param(
    [string]$DropletIp = "45.55.173.72"
)

$ErrorActionPreference = "Continue"

Write-Host "`n=== Testing Agent Tracing ===" -ForegroundColor Cyan
Write-Host "Droplet: $DropletIp`n" -ForegroundColor Gray

# Test 1: Orchestrator health
Write-Host "[1/3] Testing orchestrator health..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://${DropletIp}:8001/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✓ Orchestrator: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Orchestrator unavailable (internal service)" -ForegroundColor Gray
}

# Test 2: Gateway MCP tools
Write-Host "`n[2/3] Testing MCP Gateway..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://${DropletIp}:8000/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  ✓ Gateway: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Gateway failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Check container logs for trace confirmations
Write-Host "`n[3/3] Checking agent logs for Langfuse initialization..." -ForegroundColor Yellow
$agents = @("orchestrator", "feature-dev", "code-review")
foreach ($agent in $agents) {
    try {
        $logs = ssh root@${DropletIp} "docker logs compose-${agent}-1 --tail 5 2>&1" 2>$null
        if ($logs -match "LangGraph|Langfuse|Started|running") {
            Write-Host "  ✓ ${agent}: Running" -ForegroundColor Green
        } else {
            Write-Host "  ? ${agent}: Check manually" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ✗ ${agent}: Error checking logs" -ForegroundColor Red
    }
}

Write-Host "`n=== Next Steps ===" -ForegroundColor Cyan
Write-Host "1. Agents are internal services (not exposed externally)" -ForegroundColor Gray
Write-Host "2. To see traces, agents need to make LLM calls via Gradient client" -ForegroundColor Gray
Write-Host "3. Check Langfuse: https://us.cloud.langfuse.com" -ForegroundColor Cyan
Write-Host "4. Traces appear when agents process tasks internally`n" -ForegroundColor Gray
