#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Updates Dockerfile COPY paths for new agent structure
#>

param([switch]$DryRun)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$Agents = @(
    'orchestrator', 'feature-dev', 'code-review', 
    'infrastructure', 'cicd', 'documentation',
    'rag', 'state', 'langgraph'
)

Write-Host "Updating Dockerfiles..." -ForegroundColor Cyan

foreach ($agent in $Agents) {
    $dockerfilePath = Join-Path $RepoRoot "agents\$agent\Dockerfile"
    
    if (!(Test-Path $dockerfilePath)) {
        Write-Host "  ! Skipping $agent (no Dockerfile)" -ForegroundColor Yellow
        continue
    }
    
    $content = Get-Content -Path $dockerfilePath -Raw
    
    # Update COPY paths
    $newContent = $content `
        -replace 'COPY agents/_shared/', 'COPY _shared/' `
        -replace 'COPY agents/\w+/', 'COPY src/' `
        -replace 'COPY requirements\.txt \.', 'COPY requirements.txt .' `
        -replace 'WORKDIR /app', 'WORKDIR /app'
    
    if ($newContent -ne $content) {
        if ($DryRun) {
            Write-Host "  [DRY] Would update: $dockerfilePath" -ForegroundColor DarkGray
            Write-Host "    - Updated COPY paths" -ForegroundColor DarkGray
        } else {
            Set-Content -Path $dockerfilePath -Value $newContent -Encoding UTF8 -NoNewline
            Write-Host "  ✓ Updated: agents/$agent/Dockerfile" -ForegroundColor Green
        }
    } else {
        Write-Host "  • No changes: agents/$agent/Dockerfile" -ForegroundColor Gray
    }
}

Write-Host "`n✓ Dockerfiles updated successfully`n" -ForegroundColor Green
exit 0
