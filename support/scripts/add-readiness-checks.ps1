#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Adds /ready endpoint to all agent main.py files
.DESCRIPTION
    Injects readiness check endpoint after /health endpoint in each agent
#>

$Agents = @("feature-dev", "code-review", "infrastructure", "cicd", "documentation")
$RepoRoot = "D:\INFRA\Dev-Tools\Dev-Tools"

foreach ($Agent in $Agents) {
    $AgentPath = Join-Path $RepoRoot "agent_$Agent"
    $MainFile = Join-Path $AgentPath "main.py"
    
    if (-not (Test-Path $MainFile)) {
        Write-Host "Skipping $Agent - main.py not found" -ForegroundColor Yellow
        continue
    }
    
    Write-Host "Processing $Agent..." -ForegroundColor Cyan
    
    $Content = Get-Content $MainFile -Raw
    
    # Check if /ready already exists
    if ($Content -match '@app.get\("/ready"\)') {
        Write-Host "  /ready endpoint already exists, skipping" -ForegroundColor Yellow
        continue
    }
    
    # Find the health check endpoint and add readiness check after it
    $HealthPattern = '@app\.get\("/health"\)\s+async def health_check\(\):[\s\S]*?return \{[^}]*"status"[^}]*\}'
    
    if ($Content -match $HealthPattern) {
        $HealthEndpoint = $Matches[0]
        
        $ReadinessCode = @"

@app.get("/ready")
async def readiness_check():
    ""Readiness check endpoint - indicates if service is ready to handle traffic""
    # Check critical dependencies
    mcp_ready = hasattr(mcp_client, 'list_tools')
    gradient_ready = gradient_client.is_enabled() if 'gradient_client' in dir() else True
    
    # Service is ready if core dependencies are available
    is_ready = mcp_ready
    
    return {
        "ready": is_ready,
        "service": "$($Agent.Replace('-', '_'))",
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": {
            "mcp_gateway": mcp_ready,
            "gradient_ai": gradient_ready
        }
    }
"@
        
        $NewContent = $Content -replace [regex]::Escape($HealthEndpoint), "$HealthEndpoint$ReadinessCode"
        $NewContent | Set-Content $MainFile -NoNewline
        Write-Host "  Added /ready endpoint" -ForegroundColor Green
    } else {
        Write-Host "  Could not find /health endpoint pattern" -ForegroundColor Red
    }
}

Write-Host "`nDone! Added /ready endpoints to all agents." -ForegroundColor Green
