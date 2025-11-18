#!/usr/bin/env pwsh
<#
.SYNOPSIS
    MCP Configuration Validation Script
    
.DESCRIPTION
    Validates MCP Gateway, agent configurations, tool mappings, and integration points.
    Runs 7 comprehensive tests to ensure the MCP integration is properly configured.
    
.PARAMETER GatewayUrl
    MCP Gateway URL (default: http://localhost:8000)
    
.PARAMETER VerboseOutput
    Enable verbose output
    
.EXAMPLE
    .\scripts\validate-mcp-config.ps1
    
.EXAMPLE
    .\scripts\validate-mcp-config.ps1 -GatewayUrl "http://gateway-mcp:8000" -VerboseOutput
#>

[CmdletBinding()]
param(
    [Parameter()]
    [string]$GatewayUrl = "http://localhost:8000",
    
    [Parameter()]
    [switch]$VerboseOutput
)

$ErrorActionPreference = "Continue"
$script:TestsPassed = 0
$script:TestsFailed = 0
$script:TestsSkipped = 0

# Color output helpers
function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Failure {
    param([string]$Message)
    Write-Host "[FAILURE] $Message" -ForegroundColor Red
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Message)
    if ($VerboseOutput) {
        Write-Host "[INFO] $Message" -ForegroundColor Cyan
    }
}

function Write-TestHeader {
    param([string]$TestName, [int]$TestNumber)
    Write-Host ""
    Write-Host "================================" -ForegroundColor Blue
    Write-Host "Test $TestNumber/7: $TestName" -ForegroundColor Blue
    Write-Host "================================" -ForegroundColor Blue
}

# Test 1: Gateway Health Check
function Test-GatewayHealth {
    Write-TestHeader -TestName "MCP Gateway Health Check" -TestNumber 1
    
    try {
        Write-Info "Checking gateway at: $GatewayUrl/health"
        $response = Invoke-RestMethod -Uri "$GatewayUrl/health" -Method Get -TimeoutSec 10 -ErrorAction Stop
        
        if ($response.status -eq "ok") {
            Write-Success "Gateway is healthy"
            Write-Info "  Service: $($response.service)"
            Write-Info "  Timestamp: $($response.timestamp)"
            if ($response.servers_running) {
                Write-Info "  Servers Running: $($response.servers_running)"
            }
            if ($response.total_tools) {
                Write-Info "  Total Tools: $($response.total_tools)"
            }
            $script:TestsPassed++
            return $true
        } else {
            Write-Failure "Gateway returned non-ok status: $($response.status)"
            $script:TestsFailed++
            return $false
        }
    }
    catch {
        Write-Failure "Gateway health check failed: $_"
        Write-Warning-Custom "Make sure the MCP Gateway is running on $GatewayUrl"
        $script:TestsFailed++
        return $false
    }
}

# Test 2: Tool Enumeration
function Test-ToolEnumeration {
    Write-TestHeader -TestName "Tool Enumeration" -TestNumber 2
    
    try {
        Write-Info "Fetching tool list from: $GatewayUrl/tools"
        $response = Invoke-RestMethod -Uri "$GatewayUrl/tools" -Method Get -TimeoutSec 15 -ErrorAction Stop
        
        if ($response.servers) {
            $serverCount = $response.servers.Count
            $totalTools = ($response.servers | ForEach-Object { $_.tools.Count } | Measure-Object -Sum).Sum
            
            Write-Success "Successfully enumerated tools"
            Write-Info "  Total Servers: $serverCount"
            Write-Info "  Total Tools: $totalTools"
            
            if ($VerboseOutput) {
                Write-Info ""
                Write-Info "  Server Breakdown:"
                foreach ($server in $response.servers) {
                    Write-Info "    - $($server.name): $($server.tools.Count) tools"
                }
            }
            
            $script:TestsPassed++
            return $response
        } else {
            Write-Failure "No servers found in tools response"
            $script:TestsFailed++
            return $null
        }
    }
    catch {
        Write-Failure "Tool enumeration failed: $_"
        $script:TestsFailed++
        return $null
    }
}

# Test 3: Agent Manifest Validation
function Test-ManifestValidation {
    Write-TestHeader -TestName "Agent Manifest Validation" -TestNumber 3
    
    $manifestPath = "agents/agents-manifest.json"
    
    if (-not (Test-Path $manifestPath)) {
        Write-Failure "Agent manifest not found at: $manifestPath"
        $script:TestsFailed++
        return $false
    }
    
    try {
        $manifest = Get-Content $manifestPath -Raw | ConvertFrom-Json
        
        if (-not $manifest.profiles) {
            Write-Failure "Manifest missing 'profiles' array"
            $script:TestsFailed++
            return $false
        }
        
        $expectedAgents = @("orchestrator", "feature-dev", "code-review", "infrastructure", "cicd", "documentation")
        $foundAgents = $manifest.profiles | ForEach-Object { $_.name }
        
        $allFound = $true
        foreach ($expected in $expectedAgents) {
            if ($expected -notin $foundAgents) {
                Write-Failure "Missing agent profile: $expected"
                $allFound = $false
            }
        }
        
        if ($allFound) {
            Write-Success "All 6 agent profiles found in manifest"
            
            if ($VerboseOutput) {
                Write-Info ""
                Write-Info "  Agent Details:"
                foreach ($profile in $manifest.profiles) {
                    $recTools = $profile.mcp_tools.recommended.Count
                    $sharedTools = $profile.mcp_tools.shared.Count
                    $caps = $profile.capabilities.Count
                    Write-Info "    - $($profile.name): $recTools recommended, $sharedTools shared, $caps capabilities"
                }
            }
            
            $script:TestsPassed++
            return $manifest
        } else {
            $script:TestsFailed++
            return $null
        }
    }
    catch {
        Write-Failure "Manifest validation failed: $_"
        $script:TestsFailed++
        return $null
    }
}

# Test 4: Docker Compose Configuration
function Test-DockerComposeConfig {
    Write-TestHeader -TestName "Docker Compose Configuration" -TestNumber 4
    
    $composePath = "deploy/docker-compose.yml"
    
    if (-not (Test-Path $composePath)) {
        Write-Failure "Docker Compose file not found at: $composePath"
        $script:TestsFailed++
        return $false
    }
    
    try {
        $composeContent = Get-Content $composePath -Raw
        
        # Check for MCP_GATEWAY_URL in all agent services
        $expectedServices = @("orchestrator", "feature-dev", "code-review", "infrastructure", "cicd", "documentation", "rag-context")
        $foundCount = 0
        
        foreach ($service in $expectedServices) {
            $pattern = "(?s)${service}:.*?MCP_GATEWAY_URL"
            if ($composeContent -match $pattern) {
                $foundCount++
                Write-Info "  MCP_GATEWAY_URL found in $service"
            } else {
                Write-Failure "  MCP_GATEWAY_URL missing in $service"
            }
        }
        
        if ($foundCount -eq $expectedServices.Count) {
            Write-Success "All $foundCount services have MCP_GATEWAY_URL configured"
            $script:TestsPassed++
            return $true
        } else {
            Write-Failure "Only $foundCount/$($expectedServices.Count) services have MCP_GATEWAY_URL"
            $script:TestsFailed++
            return $false
        }
    }
    catch {
        Write-Failure "Docker Compose validation failed: $_"
        $script:TestsFailed++
        return $false
    }
}

# Test 5: Agent Health Checks
function Test-AgentHealthChecks {
    Write-TestHeader -TestName "Agent Health Checks" -TestNumber 5
    
    $agents = @(
        @{Name="orchestrator"; Port=8001},
        @{Name="feature-dev"; Port=8002},
        @{Name="code-review"; Port=8003},
        @{Name="infrastructure"; Port=8004},
        @{Name="cicd"; Port=8005},
        @{Name="documentation"; Port=8006}
    )
    
    $healthyCount = 0
    $unhealthyCount = 0
    
    foreach ($agent in $agents) {
        $url = "http://localhost:$($agent.Port)/health"
        Write-Info "Checking $($agent.Name) at $url"
        
        try {
            $response = Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 5 -ErrorAction Stop
            
            if ($response.status -eq "ok") {
                Write-Success "  $($agent.Name) is healthy"
                
                # Check for MCP integration
                if ($response.mcp) {
                    Write-Info "    MCP Gateway Status: $($response.mcp.gateway.status)"
                } else {
                    Write-Warning-Custom "    MCP section missing in health response"
                }
                
                $healthyCount++
            } else {
                Write-Warning-Custom "  $($agent.Name) returned non-ok status"
                $unhealthyCount++
            }
        }
        catch {
            Write-Warning-Custom "  $($agent.Name) is not accessible: $_"
            $unhealthyCount++
        }
    }
    
    Write-Info ""
    Write-Info "Summary: $healthyCount healthy, $unhealthyCount not accessible"
    
    if ($healthyCount -gt 0) {
        Write-Success "At least $healthyCount agent(s) are healthy"
        $script:TestsPassed++
        return $true
    } else {
        Write-Failure "No agents are healthy - services may not be running"
        Write-Warning-Custom "Run 'docker-compose up -d' or 'make up' to start services"
        $script:TestsFailed++
        return $false
    }
}

# Test 6: Sample Tool Invocation
function Test-SampleToolInvocation {
    Write-TestHeader -TestName "Sample Tool Invocation" -TestNumber 6
    
    try {
        Write-Info "Testing time server tool invocation..."
        $payload = @{
            params = @{}
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri "$GatewayUrl/tools/time/get_current_time" `
            -Method Post `
            -Body $payload `
            -ContentType "application/json" `
            -TimeoutSec 10 `
            -ErrorAction Stop
        
        if ($response.success -or $response.result) {
            Write-Success "Tool invocation successful"
            Write-Info "  Tool: time/get_current_time"
            if ($response.result) {
                Write-Info "  Result: $($response.result)"
            }
            $script:TestsPassed++
            return $true
        } else {
            Write-Failure "Tool invocation returned error: $($response.error)"
            $script:TestsFailed++
            return $false
        }
    }
    catch {
        Write-Failure "Tool invocation failed: $_"
        Write-Warning-Custom "The time server may not be running or the gateway is not configured"
        $script:TestsFailed++
        return $false
    }
}

# Test 7: Memory Server Integration
function Test-MemoryServerIntegration {
    Write-TestHeader -TestName "Memory Server Integration" -TestNumber 7
    
    try {
        Write-Info "Testing memory server with entity creation..."
        
        $testEntity = @{
            params = @{
                entities = @(
                    @{
                        name = "mcp-validation-test-$(Get-Random)"
                        type = "validation_test"
                        metadata = @{
                            timestamp = (Get-Date).ToUniversalTime().ToString("o")
                            test = "Phase 6 Validation"
                        }
                    }
                )
            }
        } | ConvertTo-Json -Depth 10
        
        $response = Invoke-RestMethod -Uri "$GatewayUrl/tools/memory/create_entities" `
            -Method Post `
            -Body $testEntity `
            -ContentType "application/json" `
            -TimeoutSec 10 `
            -ErrorAction Stop
        
        if ($response.success -or $response.result) {
            Write-Success "Memory server integration working"
            Write-Info "  Tool: memory/create_entities"
            Write-Info "  Test entity created successfully"
            $script:TestsPassed++
            return $true
        } else {
            Write-Failure "Memory server returned error: $($response.error)"
            $script:TestsFailed++
            return $false
        }
    }
    catch {
        Write-Failure "Memory server test failed: $_"
        Write-Warning-Custom "The memory server may not be running or configured"
        $script:TestsFailed++
        return $false
    }
}

# Main execution
function Main {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Magenta
    Write-Host "  MCP Configuration Validation Suite" -ForegroundColor Magenta
    Write-Host "========================================" -ForegroundColor Magenta
    Write-Host ""
    Write-Host "Gateway URL: $GatewayUrl" -ForegroundColor Cyan
    Write-Host "Started: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
    Write-Host ""
    
    # Run all tests
    Test-GatewayHealth
    $toolsResponse = Test-ToolEnumeration
    $manifest = Test-ManifestValidation
    Test-DockerComposeConfig
    Test-AgentHealthChecks
    Test-SampleToolInvocation
    Test-MemoryServerIntegration
    
    # Final summary
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Magenta
    Write-Host "  Validation Summary" -ForegroundColor Magenta
    Write-Host "========================================" -ForegroundColor Magenta
    Write-Host ""
    Write-Host "Tests Passed:  $script:TestsPassed" -ForegroundColor Green
    Write-Host "Tests Failed:  $script:TestsFailed" -ForegroundColor Red
    Write-Host "Tests Skipped: $script:TestsSkipped" -ForegroundColor Yellow
    Write-Host ""
    
    $totalTests = $script:TestsPassed + $script:TestsFailed + $script:TestsSkipped
    $successRate = [math]::Round(($script:TestsPassed / $totalTests) * 100, 1)
    
    Write-Host "Success Rate: $successRate%" -ForegroundColor $(if ($successRate -ge 80) { "Green" } elseif ($successRate -ge 50) { "Yellow" } else { "Red" })
    Write-Host ""
    
    if ($script:TestsFailed -eq 0) {
        Write-Host "ALL TESTS PASSED - MCP Configuration is valid!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next Steps:" -ForegroundColor Cyan
        Write-Host "  1. Review validation results above" -ForegroundColor White
        Write-Host "  2. Proceed to Phase 7: Deploy and E2E Testing" -ForegroundColor White
        Write-Host "  3. Run: .\scripts\rebuild.sh or make rebuild" -ForegroundColor White
        exit 0
    } else {
        Write-Host "VALIDATION FAILED - Please fix the issues above" -ForegroundColor Red
        Write-Host ""
        Write-Host "Common Issues:" -ForegroundColor Cyan
        Write-Host "  - Services not running: Run 'docker-compose up -d'" -ForegroundColor White
        Write-Host "  - Gateway not accessible: Check network and port 8000" -ForegroundColor White
        Write-Host "  - Missing manifest: Run .\scripts\generate-agent-manifest.ps1" -ForegroundColor White
        exit 1
    }
}

# Execute main function
Main
