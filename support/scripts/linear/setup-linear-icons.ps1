#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Setup agent icons for Linear workspace labels
.DESCRIPTION
    This script provides instructions and helper commands to configure
    agent-specific icons in Linear workspace labels.
.PARAMETER GenerateDocs
    Generate markdown documentation showing icon mappings
.PARAMETER ListIcons
    List all available agent icons and their properties
.EXAMPLE
    .\setup-linear-icons.ps1 -ListIcons
    Shows all agent icons with their colors and descriptions
#>

param(
    [switch]$GenerateDocs,
    [switch]$ListIcons
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
$IconsDir = Join-Path $RepoRoot "extensions\vscode-devtools-copilot\src\icons"

# Agent configuration
$Agents = @{
    "orchestrator" = @{
        Icon = "orchestrator.png"
        Source = "minions_purple.png"
        Color = "#9333EA"
        ColorName = "Purple"
        Description = "Task coordination and routing"
        Symbol = "[O]"
        Label = "agent: orchestrator"
    }
    "feature-dev" = @{
        Icon = "feature-dev.png"
        Source = "minions_blue.png"
        Color = "#3B82F6"
        ColorName = "Blue"
        Description = "Feature development and implementation"
        Symbol = "[F]"
        Label = "agent: feature-dev"
    }
    "code-review" = @{
        Icon = "code-review.png"
        Source = "minions_green.png"
        Color = "#22C55E"
        ColorName = "Green"
        Description = "Code quality assurance and review"
        Symbol = "[C]"
        Label = "agent: code-review"
    }
    "infrastructure" = @{
        Icon = "infrastructure.png"
        Source = "minions_navy.png"
        Color = "#1E3A8A"
        ColorName = "Navy"
        Description = "Infrastructure and DevOps"
        Symbol = "[I]"
        Label = "agent: infrastructure"
    }
    "cicd" = @{
        Icon = "cicd.png"
        Source = "minions_orange.png"
        Color = "#F97316"
        ColorName = "Orange"
        Description = "Deployment and automation"
        Symbol = "[P]"
        Label = "agent: cicd"
    }
    "documentation" = @{
        Icon = "documentation.png"
        Source = "minions_teal.png"
        Color = "#14B8A6"
        ColorName = "Teal"
        Description = "Knowledge and documentation"
        Symbol = "[D]"
        Label = "agent: documentation"
    }
}

function Show-Icons {
    Write-Host "`n=== Dev-Tools Agent Icons ===" -ForegroundColor Cyan
    Write-Host ""
    
    foreach ($agent in $Agents.Keys | Sort-Object) {
        $config = $Agents[$agent]
        $iconPath = Join-Path $IconsDir $config.Icon
        $exists = Test-Path $iconPath
        $status = if ($exists) { "[OK]" } else { "[MISSING]" }
        
        Write-Host "$($config.Symbol) " -NoNewline
        Write-Host "$agent" -ForegroundColor White -NoNewline
        Write-Host " [$status]" -ForegroundColor $(if ($exists) { "Green" } else { "Red" })
        Write-Host "   Icon: $($config.Icon)" -ForegroundColor Gray
        Write-Host "   Color: $($config.ColorName) ($($config.Color))" -ForegroundColor Gray
        Write-Host "   Label: $($config.Label)" -ForegroundColor Gray
        Write-Host "   $($config.Description)" -ForegroundColor DarkGray
        Write-Host ""
    }
    
    Write-Host "Icon Directory: $IconsDir" -ForegroundColor DarkGray
}

function Show-LinearInstructions {
    Write-Host "`n=== Linear Icon Setup Instructions ===" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. Open Linear workspace:" -ForegroundColor Yellow
    Write-Host "   https://linear.app/project-roadmaps/settings/labels" -ForegroundColor Blue
    Write-Host ""
    Write-Host "2. For each agent label:" -ForegroundColor Yellow
    
    foreach ($agent in $Agents.Keys | Sort-Object) {
        $config = $Agents[$agent]
        $iconPath = Join-Path $IconsDir $config.Icon
        
        Write-Host ""
        Write-Host "   $($config.Symbol) $($config.Label)" -ForegroundColor White
        Write-Host "      - Find or create label: '$($config.Label)'" -ForegroundColor Gray
        Write-Host "      - Click label settings → Icon" -ForegroundColor Gray
        Write-Host "      - Upload: $iconPath" -ForegroundColor Gray
        Write-Host "      - Set color: $($config.Color)" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "3. Verify icons appear in:" -ForegroundColor Yellow
    Write-Host "   - Issue cards" -ForegroundColor Gray
    Write-Host "   - Label filters" -ForegroundColor Gray
    Write-Host "   - Roadmap views" -ForegroundColor Gray
    Write-Host ""
}

function Generate-Documentation {
    $output = @"
# Agent Icons Reference

This document provides a reference for all agent-specific icons used in the Dev-Tools platform.

## Icon Overview

| Agent | Icon | Color | Description |
|-------|------|-------|-------------|
"@
    
    foreach ($agent in $Agents.Keys | Sort-Object) {
        $config = $Agents[$agent]
        $iconPath = "../extensions/vscode-devtools-copilot/src/icons/$($config.Icon)"
        $output += "`n| **$agent** | ![$agent]($iconPath) | $($config.ColorName) ($($config.Color)) | $($config.Description) |"
    }
    
    $output += @"


## Usage

### In Linear

Each agent has a corresponding label in the Linear workspace:

"@
    
    foreach ($agent in $Agents.Keys | Sort-Object) {
        $config = $Agents[$agent]
        $output += "`n- ``$($config.Label)`` - $($config.Description)"
    }
    
    $output += @"


### In VS Code Extension

Icons are automatically loaded via the extension:

``````typescript
import { getAgentIcon, getAgentColor } from './extension';

// Get icon URI for status bar
const icon = getAgentIcon('feature-dev');

// Get color for styling
const color = getAgentColor('feature-dev'); // Returns: #3B82F6
``````

### In Documentation

Reference icons in markdown files:

``````markdown
![Orchestrator](./extensions/vscode-devtools-copilot/src/icons/orchestrator.png)
``````

## Color Palette

The agent icons use a coordinated color scheme:

"@
    
    foreach ($agent in $Agents.Keys | Sort-Object) {
        $config = $Agents[$agent]
        $output += "`n- **$($config.ColorName)** ($($config.Color)) - $agent"
    }
    
    $output += @"


## Icon Files

All icon files are located in:
``````
extensions/vscode-devtools-copilot/src/icons/
``````

| File | Agent | Source |
|------|-------|--------|
"@
    
    foreach ($agent in $Agents.Keys | Sort-Object) {
        $config = $Agents[$agent]
        $output += "`n| ``$($config.Icon)`` | $agent | $($config.Source) |"
    }
    
    $output += "`n"
    
    $docsPath = Join-Path $RepoRoot "support\docs\AGENT_ICONS.md"
    $output | Out-File -FilePath $docsPath -Encoding UTF8
    Write-Host "[OK] Generated documentation: $docsPath" -ForegroundColor Green
}

# Main execution
if ($ListIcons) {
    Show-Icons
} elseif ($GenerateDocs) {
    Generate-Documentation
} else {
    Show-Icons
    Show-LinearInstructions
}
