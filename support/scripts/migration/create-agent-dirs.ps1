#!/usr/bin/env pwsh
param([switch]$DryRun)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$Agents = @(
    'orchestrator', 'feature-dev', 'code-review', 
    'infrastructure', 'cicd', 'documentation',
    'rag', 'state', 'langgraph'
)

$NewStructure = @{
    'agents' = @{
        '_shared' = @('', 'tests')
        'orchestrator' = @('src', 'config', 'tests')
        'feature-dev' = @('src', 'config', 'tests')
        'code-review' = @('src', 'config', 'tests')
        'infrastructure' = @('src', 'config', 'tests')
        'cicd' = @('src', 'config', 'tests')
        'documentation' = @('src', 'config', 'tests')
        'rag' = @('src', 'config', 'tests')
        'state' = @('src', 'config', 'tests')
        'langgraph' = @('src', 'config', 'tests')
    }
    'gateway' = @('src', 'config', 'tests')
    'infrastructure' = @('compose', 'config', 'scripts', '.github')
    'docs' = @('architecture', 'deployment', 'agents', '_temp')
}

function New-DirectoryTree {
    param([string]$BasePath, [hashtable]$Tree)
    
    foreach ($key in $Tree.Keys) {
        $currentPath = Join-Path $BasePath $key
        
        if ($DryRun) {
            Write-Host "  [DRY] mkdir -p $currentPath" -ForegroundColor DarkGray
        } else {
            New-Item -ItemType Directory -Path $currentPath -Force | Out-Null
            Write-Host "  ✓ Created: $currentPath" -ForegroundColor Green
        }
        
        $value = $Tree[$key]
        if ($value -is [hashtable]) {
            New-DirectoryTree -BasePath $currentPath -Tree $value
        } elseif ($value -is [array]) {
            foreach ($subdir in $value) {
                if ($subdir) {
                    $subdirPath = Join-Path $currentPath $subdir
                    if ($DryRun) {
                        Write-Host "  [DRY] mkdir -p $subdirPath" -ForegroundColor DarkGray
                    } else {
                        New-Item -ItemType Directory -Path $subdirPath -Force | Out-Null
                        Write-Host "  ✓ Created: $subdirPath" -ForegroundColor Green
                    }
                }
            }
        }
    }
}

Write-Host "Creating agent-centric directory structure..." -ForegroundColor Cyan
New-DirectoryTree -BasePath $RepoRoot -Tree $NewStructure

# Create README templates
foreach ($agent in $Agents) {
    $readmePath = Join-Path $RepoRoot "agents/$agent/README.md"
    if (!(Test-Path $readmePath)) {
        $readmeContent = "# $agent Agent`n`n"
        $readmeContent += "## Overview`n[Brief description of agent responsibilities]`n`n"
        $readmeContent += "## API Endpoints`n- GET /health - Health check`n`n"
        $readmeContent += "## Configuration`nSee config/ for agent-specific settings`n`n"
        $readmeContent += "## Development`npytest agents/$agent/tests/`n"
        
        if ($DryRun) {
            Write-Host "  [DRY] Would create $readmePath" -ForegroundColor DarkGray
        } else {
            Set-Content -Path $readmePath -Value $readmeContent -Encoding UTF8
            Write-Host "  ✓ Created README: $readmePath" -ForegroundColor Green
        }
    }
}

Write-Host "`n✓ Directory structure created successfully`n" -ForegroundColor Green
exit 0
