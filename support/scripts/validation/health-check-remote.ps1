#!/usr/bin/env pwsh
# Health check for remote droplet services
param(
    [string]$DropletIP = "45.55.173.72"
)

Write-Host "[HEALTH] Checking droplet service health..."

$services = @(
    @{Port=8000; Name="gateway-mcp"},
    @{Port=8001; Name="orchestrator"},
    @{Port=8007; Name="rag-context"},
    @{Port=8008; Name="state-persistence"},
    @{Port=8009; Name="agent-registry"},
    @{Port=8010; Name="langgraph"}
)

foreach ($svc in $services) {
    try {
        $response = Invoke-WebRequest -Uri "http://${DropletIP}:$($svc.Port)/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "  [OK] $($svc.Name) (port $($svc.Port))"
        } else {
            Write-Host "  [ERROR] $($svc.Name) (port $($svc.Port)) - HTTP $($response.StatusCode)"
        }
    } catch {
        Write-Host "  [ERROR] $($svc.Name) (port $($svc.Port)) - Unreachable"
    }
}
