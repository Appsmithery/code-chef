# Generate Agent Manifest from MCP Tool Mapping
# Reads config/mcp-agent-tool-mapping.yaml and generates agents/agents-manifest.json

param(
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

Write-Host "=================================="
Write-Host "Agent Manifest Generator"
Write-Host "=================================="
Write-Host ""

# File paths
$mappingFile = "config/mcp-agent-tool-mapping.yaml"
$outputFile = "agents/agents-manifest.json"

# Check if mapping file exists
if (-not (Test-Path $mappingFile)) {
    Write-Error "Mapping file not found: $mappingFile"
    exit 1
}

Write-Host "[1/4] Reading MCP tool mapping configuration..."
$yamlContent = Get-Content $mappingFile -Raw

# Parse YAML manually (since ConvertFrom-Yaml may not be available)
# Extract agent definitions using regex patterns

$manifest = @{
    version = "2.0.0"
    generatedAt = (Get-Date -Format "o")
    profiles = @()
    discovery_summary = @{
        total_servers = 18
        total_tools = 150
        discovery_method = "Docker MCP Toolkit CLI"
        discovery_timestamp = "2025-11-13T22:40:00Z"
    }
}

# Define agent profiles with endpoints
$agentConfigs = @(
    @{name = "orchestrator"; port = 8001; mission = "Coordinates task routing, agent hand-offs, workflow state, and global observability"},
    @{name = "feature-dev"; port = 8002; mission = "Implements features through code generation, scaffolding, and test creation"},
    @{name = "code-review"; port = 8003; mission = "Analyzes code quality, security, style, and maintainability"},
    @{name = "infrastructure"; port = 8004; mission = "Manages IaC, deployments, environment configuration, and resource provisioning"},
    @{name = "cicd"; port = 8005; mission = "Generates pipelines, orchestrates builds/tests, and manages deployment automation"},
    @{name = "documentation"; port = 8006; mission = "Generates, maintains, and audits technical documentation, diagrams, and knowledge bases"}
)

Write-Host "[2/4] Extracting agent tool mappings..."

foreach ($agentConfig in $agentConfigs) {
    $agentName = $agentConfig.name
    $agentNamePattern = $agentName -replace '-', '[-_]'  # Handle dash/underscore variations
    
    if ($Verbose) {
        Write-Host "  Processing: $agentName"
    }
    
    # Extract recommended tools section for this agent
    $pattern = "(?s)" + $agentNamePattern + ":.*?mission:.*?recommended_tools:(.*?)(?=\n  \w+:|shared_tools:|# ---|$)"
    $agentSection = [regex]::Match($yamlContent, $pattern)
    
    $recommendedTools = @()
    
    if ($agentSection.Success) {
        $toolsText = $agentSection.Groups[1].Value
        
        # Extract each tool server block - match from "- server:" to the next "- server:" or end markers
        $serverBlocks = [regex]::Matches($toolsText, '(?s)- server:\s*"([^"]+)"(.*?)(?=(- server:|shared_tools:|# ---|$))')
        
        foreach ($block in $serverBlocks) {
            $server = $block.Groups[1].Value
            $blockContent = $block.Groups[2].Value
            
            # Extract tools - handle both inline JSON array ["tool1", "tool2"] and YAML list format
            $tools = @()
            
            # Try inline JSON array format (can be single-line or multi-line): tools: ["tool1", "tool2"]
            if ($blockContent -match '(?s)tools:\s*\[([^\]]*)\]') {
                $toolsList = $matches[1]
                # Extract all quoted tool names
                $toolMatches = [regex]::Matches($toolsList, '"([^"]+)"')
                $tools = @($toolMatches | ForEach-Object { $_.Groups[1].Value })
            }
            # Try YAML list format: tools:\n  - tool1\n  - tool2
            elseif ($blockContent -match '(?s)tools:\s*\n((?:\s+-[^\n]+\n?)+)') {
                $toolsLines = $matches[1]
                $toolMatches = [regex]::Matches($toolsLines, '-\s*"?([^"\n]+?)"?\s*$', [System.Text.RegularExpressions.RegexOptions]::Multiline)
                $tools = @($toolMatches | ForEach-Object { $_.Groups[1].Value.Trim() })
            }
            # Try single tool (no array): tools: "tool_name" or tools: tool_name
            elseif ($blockContent -match 'tools:\s*"?([^"\n]+?)"?\s*$', [System.Text.RegularExpressions.RegexOptions]::Multiline) {
                $tools = @($matches[1].Trim())
            }
            
            # Ensure tools is always an array, even for single items
            if ($tools.Count -eq 0) {
                $tools = @()
            } elseif ($tools -is [string]) {
                $tools = @($tools)
            }
            
            # Extract priority
            $priority = "medium"
            if ($blockContent -match 'priority:\s*"([^"]+)"') {
                $priority = $matches[1]
            }
            
            # Extract rationale
            $rationale = "Primary tool for $agentName agent"
            if ($blockContent -match 'rationale:\s*"([^"]+)"') {
                $rationale = $matches[1]
            }
            
            $recommendedTools += @{
                server = $server
                tools = $tools
                priority = $priority
                rationale = $rationale
            }
        }
    }
    
    # Create agent profile
    $profile = @{
        name = $agentName
        display_name = ($agentName -replace '-', ' ' | ForEach-Object { (Get-Culture).TextInfo.ToTitleCase($_) })
        mission = $agentConfig.mission
        endpoint = "http://$($agentName):$($agentConfig.port)"
        health_check = "http://$($agentName):$($agentConfig.port)/health"
        mcp_tools = @{
            recommended = $recommendedTools
            shared = @("memory", "time", "rust-mcp-filesystem", "context7", "notion", "fetch")
        }
        capabilities = @()
        status = "active"
    }
    
    # Add agent-specific capabilities
    switch ($agentName) {
        "orchestrator" {
            $profile.capabilities = @(
                "task_decomposition",
                "agent_routing",
                "workflow_coordination",
                "sla_tracking",
                "stakeholder_notification"
            )
        }
        "feature-dev" {
            $profile.capabilities = @(
                "code_generation",
                "scaffolding",
                "test_creation",
                "git_operations",
                "branch_management"
            )
        }
        "code-review" {
            $profile.capabilities = @(
                "quality_analysis",
                "security_scanning",
                "standards_enforcement",
                "diff_analysis",
                "actionable_feedback"
            )
        }
        "infrastructure" {
            $profile.capabilities = @(
                "iac_authoring",
                "deployment_automation",
                "container_management",
                "drift_detection",
                "compliance_validation"
            )
        }
        "cicd" {
            $profile.capabilities = @(
                "pipeline_generation",
                "workflow_execution",
                "test_automation",
                "artifact_management",
                "deployment_orchestration"
            )
        }
        "documentation" {
            $profile.capabilities = @(
                "doc_generation",
                "api_documentation",
                "diagram_synthesis",
                "wiki_management",
                "changelog_generation"
            )
        }
    }
    
    $manifest.profiles += $profile
}

Write-Host "[3/4] Generating manifest JSON..."

# Convert to JSON with proper formatting
$jsonOutput = $manifest | ConvertTo-Json -Depth 10

# Write to file
$jsonOutput | Set-Content $outputFile -Encoding UTF8

Write-Host "[4/4] Validating generated manifest..."

# Validate JSON structure
try {
    $validation = Get-Content $outputFile | ConvertFrom-Json
    
    Write-Host ""
    Write-Host "=================================="
    Write-Host "Manifest Generated Successfully"
    Write-Host "=================================="
    Write-Host ""
    Write-Host "Output File:    $outputFile"
    Write-Host "Version:        $($validation.version)"
    Write-Host "Generated:      $($validation.generatedAt)"
    Write-Host "Total Agents:   $($validation.profiles.Count)"
    Write-Host ""
    
    if ($Verbose) {
        Write-Host "Agent Profiles:"
        foreach ($profile in $validation.profiles) {
            Write-Host "  - $($profile.display_name) ($($profile.name))"
            Write-Host "    Endpoint:  $($profile.endpoint)"
            Write-Host "    Tools:     $($profile.mcp_tools.recommended.Count) recommended, $($profile.mcp_tools.shared.Count) shared"
            Write-Host "    Capabilities: $($profile.capabilities.Count)"
            Write-Host ""
        }
    } else {
        foreach ($profile in $validation.profiles) {
            $toolCount = $profile.mcp_tools.recommended.Count
            Write-Host "  [OK] $($profile.display_name): $toolCount recommended tools, $($profile.capabilities.Count) capabilities"
        }
    }
    
    Write-Host ""
    Write-Host "[SUCCESS] Phase 1 Complete: Agent manifest ready for integration" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Steps:"
    Write-Host "  1. Review: $outputFile"
    Write-Host "  2. Execute Phase 2: .\scripts\update-docker-compose-mcp.ps1"
    Write-Host ""
    
} catch {
    Write-Error "Validation failed: $_"
    exit 1
}
