#!/usr/bin/env pwsh
# Health check for remote droplet services
param(
    [string]$DropletIP = "45.55.173.72"
)

Write-Host "[HEALTH] Checking droplet service health..."

$services = @(
    @{Port=8000; Name="gateway-mcp"},
    @{Port=8001; Name="orchestrator"},
    @{Port=8002; Name="feature-dev"},
    @{Port=8003; Name="code-review"},
    @{Port=8004; Name="infrastructure"},
    @{Port=8005; Name="cicd"},
    @{Port=8006; Name="documentation"},
    @{Port=8007; Name="rag-context"},
    @{Port=8008; Name="state-persistence"}
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
