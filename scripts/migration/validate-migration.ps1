#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Validates the new directory structure and Docker configuration
#>

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$ValidationPassed = $true

function Test-Requirement {
    param($Name, $Condition, $Message)
    
    if ($Condition) {
        Write-Host "  ✓ $Name" -ForegroundColor Green
        return $true
    } else {
        Write-Host "  ✗ $Name" -ForegroundColor Red
        Write-Host "    $Message" -ForegroundColor Yellow
        return $false
    }
}

Write-Host "`nValidating migration..." -ForegroundColor Cyan

# Check directory structure
Write-Host "`n[1] Directory Structure" -ForegroundColor Yellow
$agents = @('orchestrator', 'feature-dev', 'code-review', 'infrastructure', 'cicd', 'documentation', 'rag', 'state', 'langgraph')

foreach ($agent in $agents) {
    $agentPath = Join-Path $RepoRoot "agents\$agent"
    $hasSrc = Test-Path (Join-Path $agentPath "src")
    $hasDockerfile = Test-Path (Join-Path $agentPath "Dockerfile")
    $hasRequirements = Test-Path (Join-Path $agentPath "requirements.txt")
    
    $valid = $hasSrc -and $hasDockerfile -and $hasRequirements
    $ValidationPassed = $ValidationPassed -and (Test-Requirement `
        -Name "$agent structure" `
        -Condition $valid `
        -Message "Missing: src/=$(−$hasSrc), Dockerfile=$(!$hasDockerfile), requirements.txt=$(!$hasRequirements)")
}

# Check shared code
Write-Host "`n[2] Shared Components" -ForegroundColor Yellow
$sharedPath = Join-Path $RepoRoot "agents\_shared"
$ValidationPassed = $ValidationPassed -and (Test-Requirement `
    -Name "agents/_shared exists" `
    -Condition (Test-Path $sharedPath) `
    -Message "Shared code directory missing")

# Check infrastructure
Write-Host "`n[3] Infrastructure" -ForegroundColor Yellow
$infrastructurePath = Join-Path $RepoRoot "infrastructure"
$ValidationPassed = $ValidationPassed -and (Test-Requirement `
    -Name "infrastructure/compose exists" `
    -Condition (Test-Path (Join-Path $infrastructurePath "compose\docker-compose.yml")) `
    -Message "Compose file not in infrastructure/")

$ValidationPassed = $ValidationPassed -and (Test-Requirement `
    -Name "infrastructure/config exists" `
    -Condition (Test-Path (Join-Path $infrastructurePath "config")) `
    -Message "Config directory not in infrastructure/")

# Check gateway
Write-Host "`n[4] Gateway" -ForegroundColor Yellow
$gatewayPath = Join-Path $RepoRoot "gateway"
$ValidationPassed = $ValidationPassed -and (Test-Requirement `
    -Name "gateway/ exists" `
    -Condition (Test-Path $gatewayPath) `
    -Message "Gateway directory missing at root level")

# Validate docker-compose.yml
Write-Host "`n[5] Docker Compose Configuration" -ForegroundColor Yellow
$composePath = Join-Path $RepoRoot "infrastructure\compose\docker-compose.yml"
if (Test-Path $composePath) {
    $composeContent = Get-Content -Path $composePath -Raw
    
    $hasNewPaths = $composeContent -match "context: \.\./agents/"
    $ValidationPassed = $ValidationPassed -and (Test-Requirement `
        -Name "Compose uses new build contexts" `
        -Condition $hasNewPaths `
        -Message "docker-compose.yml still references old paths")
    
    $hasOldPaths = $composeContent -match "context: \.\./containers/"
    $ValidationPassed = $ValidationPassed -and (Test-Requirement `
        -Name "No old container paths remain" `
        -Condition (!$hasOldPaths) `
        -Message "docker-compose.yml contains old container/ paths")
}

# Summary
Write-Host "`n" + ("=" * 50) -ForegroundColor Cyan
if ($ValidationPassed) {
    Write-Host "✓ Validation PASSED - Migration successful!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "✗ Validation FAILED - Please review errors above" -ForegroundColor Red
    exit 1
}
