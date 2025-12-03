#!/usr/bin/env pwsh
# Health check for remote droplet services
param(
    [string]$DropletHost = "codechef.appsmithery.co",
    [string]$DropletIP = "45.55.173.72"  # Fallback for SSH
)

Write-Host "[HEALTH] Checking droplet service health at $DropletHost..."

# Services accessible via Caddy reverse proxy (HTTPS)
$httpsServices = @(
    @{Path="/api/health"; Name="orchestrator"},
    @{Path="/rag/health"; Name="rag-context"},
    @{Path="/state/health"; Name="state-persistence"},
    @{Path="/langgraph/health"; Name="langgraph"}
)

# Direct port access (for debugging)
$directServices = @(
    @{Port=8001; Name="orchestrator"},
    @{Port=8007; Name="rag-context"},
    @{Port=8008; Name="state-persistence"},
    @{Port=8010; Name="langgraph"}
)

Write-Host "`n[HTTPS via Caddy]"
foreach ($svc in $httpsServices) {
    try {
        $response = Invoke-WebRequest -Uri "https://${DropletHost}$($svc.Path)" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "  [OK] $($svc.Name) ($($svc.Path))"
        } else {
            Write-Host "  [ERROR] $($svc.Name) - HTTP $($response.StatusCode)"
        }
    } catch {
        Write-Host "  [ERROR] $($svc.Name) - Unreachable via HTTPS"
    }
}

Write-Host "`n[Direct Port Access (via SSH)]"
foreach ($svc in $directServices) {
    try {
        $result = ssh "root@${DropletIP}" "curl -s http://localhost:$($svc.Port)/health 2>/dev/null"
        if ($result -match '"status"\s*:\s*"(ok|healthy)"') {
            Write-Host "  [OK] $($svc.Name) (port $($svc.Port))"
        } else {
            Write-Host "  [ERROR] $($svc.Name) (port $($svc.Port)) - Unhealthy"
        }
    } catch {
        Write-Host "  [ERROR] $($svc.Name) (port $($svc.Port)) - SSH failed"
    }
}
