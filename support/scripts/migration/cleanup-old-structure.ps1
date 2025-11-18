#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Removes old directory structure after successful migration
#>

param([switch]$DryRun)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$OldDirectories = @(
    'containers',
    'mcp',
    'compose'
)

$OldFiles = @(
    '.github/workflows'  # Will be moved to infrastructure/
)

Write-Host "Cleaning up old structure..." -ForegroundColor Cyan
Write-Host "  ! This will DELETE the following:" -ForegroundColor Yellow

foreach ($dir in $OldDirectories) {
    $path = Join-Path $RepoRoot $dir
    if (Test-Path $path) {
        Write-Host "    - $dir/" -ForegroundColor Yellow
    }
}

if (!$DryRun) {
    $response = Read-Host "`nProceed with deletion? (yes/NO)"
    if ($response -ne 'yes') {
        Write-Host "Cleanup cancelled by user" -ForegroundColor Yellow
        exit 0
    }
}

foreach ($dir in $OldDirectories) {
    $path = Join-Path $RepoRoot $dir
    if (Test-Path $path) {
        if ($DryRun) {
            Write-Host "  [DRY] Would remove: $dir/" -ForegroundColor DarkGray
        } else {
            Remove-Item -Path $path -Recurse -Force
            Write-Host "  ✓ Removed: $dir/" -ForegroundColor Green
        }
    }
}

# Clean up old agent source directories (keep _shared)
$oldAgentsPath = Join-Path $RepoRoot "agents"
if (Test-Path $oldAgentsPath) {
    $oldAgentDirs = Get-ChildItem -Path $oldAgentsPath -Directory | Where-Object { 
        $_.Name -notmatch '^(_shared|orchestrator|feature-dev|code-review|infrastructure|cicd|documentation|rag|state|langgraph)$' 
    }
    
    foreach ($dir in $oldAgentDirs) {
        if ($DryRun) {
            Write-Host "  [DRY] Would remove: agents/$($dir.Name)/" -ForegroundColor DarkGray
        } else {
            Remove-Item -Path $dir.FullName -Recurse -Force
            Write-Host "  ✓ Removed: agents/$($dir.Name)/" -ForegroundColor Green
        }
    }
}

Write-Host "`n✓ Cleanup complete`n" -ForegroundColor Green
exit 0
