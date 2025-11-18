#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Updates docker-compose.yml build context paths
#>

param([switch]$DryRun)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$composePath = Join-Path $RepoRoot "compose\docker-compose.yml"
$newComposePath = Join-Path $RepoRoot "infrastructure\compose\docker-compose.yml"

if (!(Test-Path $composePath)) {
    Write-Error "docker-compose.yml not found at $composePath"
    exit 1
}

Write-Host "Updating docker-compose.yml..." -ForegroundColor Cyan

$content = Get-Content -Path $composePath -Raw

# Update build contexts from containers/<agent> to agents/<agent>
$agentPattern = '(orchestrator|feature-dev|code-review|infrastructure|cicd|documentation|rag|state|langgraph)'

$newContent = $content `
    -replace "context: \.\./containers/$agentPattern", 'context: ../agents/$1' `
    -replace "dockerfile: Dockerfile", "dockerfile: Dockerfile" `
    -replace "context: \.\./mcp/gateway", "context: ../gateway"

# Update volume mounts
$newContent = $newContent `
    -replace "\.\./config/", "../infrastructure/config/" `
    -replace "\.\./agents/_shared/", "../agents/_shared/"

if ($DryRun) {
    Write-Host "  [DRY] Would update: $composePath" -ForegroundColor DarkGray
    Write-Host "    - Build contexts: containers/* -> agents/*" -ForegroundColor DarkGray
    Write-Host "    - Volume paths: config/* -> infrastructure/config/*" -ForegroundColor DarkGray
    Write-Host "  [DRY] Would copy to: $newComposePath" -ForegroundColor DarkGray
} else {
    # Copy to new location
    $newDir = Split-Path -Parent $newComposePath
    New-Item -ItemType Directory -Path $newDir -Force | Out-Null
    Set-Content -Path $newComposePath -Value $newContent -Encoding UTF8 -NoNewline
    Write-Host "  ✓ Updated and moved: infrastructure/compose/docker-compose.yml" -ForegroundColor Green
}

Write-Host "`n✓ Compose file updated successfully`n" -ForegroundColor Green
exit 0
