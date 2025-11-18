#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Moves agent files from old structure to new agent-centric layout
#>

param([switch]$DryRun)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$AgentMappings = @(
    @{
        Name = 'orchestrator'
        OldSrc = 'agents/orchestrator'
        OldContainer = 'containers/orchestrator'
        NewBase = 'agents/orchestrator'
    },
    @{
        Name = 'feature-dev'
        OldSrc = 'agents/feature_dev'
        OldContainer = 'containers/feature-dev'
        NewBase = 'agents/feature-dev'
    },
    @{
        Name = 'code-review'
        OldSrc = 'agents/code_review'
        OldContainer = 'containers/code-review'
        NewBase = 'agents/code-review'
    },
    @{
        Name = 'infrastructure'
        OldSrc = 'agents/infrastructure'
        OldContainer = 'containers/infrastructure'
        NewBase = 'agents/infrastructure'
    },
    @{
        Name = 'cicd'
        OldSrc = 'agents/cicd'
        OldContainer = 'containers/cicd'
        NewBase = 'agents/cicd'
    },
    @{
        Name = 'documentation'
        OldSrc = 'agents/documentation'
        OldContainer = 'containers/documentation'
        NewBase = 'agents/documentation'
    },
    @{
        Name = 'rag'
        OldSrc = 'agents/rag'
        OldContainer = 'containers/rag'
        NewBase = 'agents/rag'
    },
    @{
        Name = 'state'
        OldSrc = 'agents/state'
        OldContainer = 'containers/state'
        NewBase = 'agents/state'
    },
    @{
        Name = 'langgraph'
        OldSrc = 'agents/langgraph'
        OldContainer = 'containers/langgraph'
        NewBase = 'agents/langgraph'
    }
)

function Move-AgentFiles {
    param($Mapping)
    
    $oldSrcPath = Join-Path $RepoRoot $Mapping.OldSrc
    $oldContainerPath = Join-Path $RepoRoot $Mapping.OldContainer
    $newBase = Join-Path $RepoRoot $Mapping.NewBase
    
    Write-Host "`nMigrating: $($Mapping.Name)" -ForegroundColor Yellow
    
    # Move Python source files
    if (Test-Path $oldSrcPath) {
        $pyFiles = Get-ChildItem -Path $oldSrcPath -Filter "*.py" -File
        foreach ($file in $pyFiles) {
            $dest = Join-Path "$newBase/src" $file.Name
            if ($DryRun) {
                Write-Host "  [DRY] mv $($file.FullName) -> $dest" -ForegroundColor DarkGray
            } else {
                Copy-Item -Path $file.FullName -Destination $dest -Force
                Write-Host "  ✓ Moved: $($file.Name) -> src/" -ForegroundColor Green
            }
        }
        
        # Move requirements.txt
        $reqFile = Join-Path $oldSrcPath "requirements.txt"
        if (Test-Path $reqFile) {
            $dest = Join-Path $newBase "requirements.txt"
            if ($DryRun) {
                Write-Host "  [DRY] mv $reqFile -> $dest" -ForegroundColor DarkGray
            } else {
                Copy-Item -Path $reqFile -Destination $dest -Force
                Write-Host "  ✓ Moved: requirements.txt" -ForegroundColor Green
            }
        }
    }
    
    # Move Dockerfile
    if (Test-Path $oldContainerPath) {
        $dockerfile = Join-Path $oldContainerPath "Dockerfile"
        if (Test-Path $dockerfile) {
            $dest = Join-Path $newBase "Dockerfile"
            if ($DryRun) {
                Write-Host "  [DRY] mv $dockerfile -> $dest" -ForegroundColor DarkGray
            } else {
                Copy-Item -Path $dockerfile -Destination $dest -Force
                Write-Host "  ✓ Moved: Dockerfile" -ForegroundColor Green
            }
        }
    }
}

Write-Host "Moving agent files to new structure..." -ForegroundColor Cyan

foreach ($mapping in $AgentMappings) {
    Move-AgentFiles -Mapping $mapping
}

# Move MCP gateway
Write-Host "`nMigrating: gateway-mcp" -ForegroundColor Yellow
$oldGateway = Join-Path $RepoRoot "mcp/gateway"
$newGateway = Join-Path $RepoRoot "gateway"

if (Test-Path $oldGateway) {
    $files = Get-ChildItem -Path $oldGateway -File -Recurse
    foreach ($file in $files) {
        $relativePath = $file.FullName.Substring($oldGateway.Length + 1)
        $dest = Join-Path "$newGateway/src" $relativePath
        if ($DryRun) {
            Write-Host "  [DRY] mv $($file.FullName) -> $dest" -ForegroundColor DarkGray
        } else {
            $destDir = Split-Path -Parent $dest
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
            Copy-Item -Path $file.FullName -Destination $dest -Force
            Write-Host "  ✓ Moved: $relativePath" -ForegroundColor Green
        }
    }
}

# Move MCP servers
$oldServers = Join-Path $RepoRoot "mcp/servers"
$newServers = Join-Path $RepoRoot "gateway/servers"
if (Test-Path $oldServers) {
    if ($DryRun) {
        Write-Host "  [DRY] mv $oldServers -> $newServers" -ForegroundColor DarkGray
    } else {
        Copy-Item -Path $oldServers -Destination $newServers -Recurse -Force
        Write-Host "  ✓ Moved: mcp/servers -> gateway/servers" -ForegroundColor Green
    }
}

Write-Host "`n✓ Agent files moved successfully`n" -ForegroundColor Green
exit 0
