#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Updates GitHub Actions workflows for new structure
#>

param([switch]$DryRun)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$workflowsPath = Join-Path $RepoRoot ".github\workflows"
$newWorkflowsPath = Join-Path $RepoRoot "infrastructure\.github\workflows"

if (!(Test-Path $workflowsPath)) {
    Write-Error "Workflows directory not found"
    exit 1
}

Write-Host "Updating GitHub Actions workflows..." -ForegroundColor Cyan

$workflows = Get-ChildItem -Path $workflowsPath -Filter "*.yml"

foreach ($workflow in $workflows) {
    $content = Get-Content -Path $workflow.FullName -Raw
    
    # Update paths
    $newContent = $content `
        -replace "containers/([^/]+)/Dockerfile", 'agents/$1/Dockerfile' `
        -replace "agents/([^/]+)/\*\*", 'agents/$1/src/**' `
        -replace "agents/_shared/\*\*", 'agents/_shared/**' `
        -replace "compose/docker-compose\.yml", 'infrastructure/compose/docker-compose.yml' `
        -replace "config/", 'infrastructure/config/'
    
    if ($newContent -ne $content) {
        $destPath = Join-Path $newWorkflowsPath $workflow.Name
        if ($DryRun) {
            Write-Host "  [DRY] Would update: $($workflow.Name)" -ForegroundColor DarkGray
            Write-Host "    - Updated file paths" -ForegroundColor DarkGray
        } else {
            $destDir = Split-Path -Parent $destPath
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
            Set-Content -Path $destPath -Value $newContent -Encoding UTF8 -NoNewline
            Write-Host "  ✓ Updated: $($workflow.Name)" -ForegroundColor Green
        }
    }
}

Write-Host "`n✓ Workflows updated successfully`n" -ForegroundColor Green
exit 0
