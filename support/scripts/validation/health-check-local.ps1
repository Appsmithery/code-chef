#!/usr/bin/env pwsh
# Health check for local services

Write-Host "[HEALTH] Checking local service health..."

# NOTE: Post-DEV-123 LangGraph migration
# Agent nodes (feature-dev, code-review, infrastructure, cicd, documentation) are NOT separate services
# They are LangGraph workflow nodes within orchestrator (port 8001)
# Gateway-MCP deprecated Dec 2025 - see _archive/gateway-deprecated-2025-12-03/
$services = @(
    @{Port=8001; Name="orchestrator (includes all agent nodes)"},
    @{Port=8007; Name="rag-context"},
    @{Port=8008; Name="state-persistence"},
    @{Port=8009; Name="agent-registry"},
    @{Port=8010; Name="langgraph"}
)

foreach ($svc in $services) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$($svc.Port)/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "  [OK] $($svc.Name) (port $($svc.Port))"
        } else {
            Write-Host "  [ERROR] $($svc.Name) (port $($svc.Port)) - HTTP $($response.StatusCode)"
        }
    } catch {
        Write-Host "  [ERROR] $($svc.Name) (port $($svc.Port)) - Unreachable"
    }
}
