#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test progressive MCP tool disclosure implementation

.DESCRIPTION
    Validates the progressive loader implementation by testing:
    - Tool loading strategies
    - Token savings calculations
    - Configuration endpoints
    - Integration with orchestrator

.EXAMPLE
    .\test-progressive-disclosure.ps1
#>

$ErrorActionPreference = "Stop"

Write-Host "`n=== Progressive MCP Tool Disclosure Tests ===" -ForegroundColor Cyan

# Configuration
$ORCHESTRATOR_URL = "http://localhost:8001"

function Test-HealthCheck {
    Write-Host "`n[TEST 1] Health Check" -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "$ORCHESTRATOR_URL/health" -Method Get
        Write-Host "✓ Orchestrator healthy" -ForegroundColor Green
        Write-Host "  - MCP Toolkit: $($response.mcp.toolkit_available)" -ForegroundColor Gray
        Write-Host "  - Server Count: $($response.mcp.server_count)" -ForegroundColor Gray
        return $true
    }
    catch {
        Write-Host "✗ Health check failed: $_" -ForegroundColor Red
        return $false
    }
}

function Test-ToolLoadingStats {
    Write-Host "`n[TEST 2] Tool Loading Statistics" -ForegroundColor Yellow
    try {
        $response = Invoke-RestMethod -Uri "$ORCHESTRATOR_URL/config/tool-loading/stats" -Method Get
        Write-Host "✓ Retrieved tool loading stats" -ForegroundColor Green
        Write-Host "  - Current Strategy: $($response.current_strategy)" -ForegroundColor Gray
        Write-Host "  - Loaded Tools: $($response.stats.loaded_tools) / $($response.stats.total_tools)" -ForegroundColor Gray
        Write-Host "  - Token Savings: $($response.stats.savings_percent)%" -ForegroundColor Gray
        Write-Host "  - Tokens Saved: $($response.stats.estimated_tokens_saved)" -ForegroundColor Gray
        Write-Host "  - Recommendation: $($response.recommendation)" -ForegroundColor Gray
        return $true
    }
    catch {
        Write-Host "✗ Stats retrieval failed: $_" -ForegroundColor Red
        return $false
    }
}

function Test-StrategyChange {
    param([string]$Strategy)
    
    Write-Host "`n[TEST 3.$Strategy] Change Strategy to $Strategy" -ForegroundColor Yellow
    try {
        $body = @{
            strategy = $Strategy
            reason = "automated_testing"
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri "$ORCHESTRATOR_URL/config/tool-loading" -Method Post `
            -ContentType "application/json" -Body $body
        
        Write-Host "✓ Strategy changed to $($response.current_strategy)" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "✗ Strategy change failed: $_" -ForegroundColor Red
        return $false
    }
}

function Test-Orchestration {
    param([string]$Description, [string]$ExpectedStrategy)
    
    Write-Host "`n[TEST 4] Orchestrate Task with $ExpectedStrategy" -ForegroundColor Yellow
    try {
        $body = @{
            description = $Description
            priority = "high"
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri "$ORCHESTRATOR_URL/orchestrate" -Method Post `
            -ContentType "application/json" -Body $body -TimeoutSec 30
        
        Write-Host "✓ Task orchestrated successfully" -ForegroundColor Green
        Write-Host "  - Task ID: $($response.task_id)" -ForegroundColor Gray
        Write-Host "  - Subtasks: $($response.subtasks.Count)" -ForegroundColor Gray
        Write-Host "  - Estimated Tokens: $($response.estimated_tokens)" -ForegroundColor Gray
        
        # Check validation results for tool loading info
        foreach ($key in $response.routing_plan.tool_validation.PSObject.Properties.Name) {
            $validation = $response.routing_plan.tool_validation.$key
            if ($validation.loaded_toolsets) {
                Write-Host "  - Loaded Toolsets: $($validation.loaded_toolsets)" -ForegroundColor Gray
                break
            }
        }
        
        return $true
    }
    catch {
        Write-Host "✗ Orchestration failed: $_" -ForegroundColor Red
        Write-Host "  Error details: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Test-InvalidStrategy {
    Write-Host "`n[TEST 5] Invalid Strategy Handling" -ForegroundColor Yellow
    try {
        $body = @{
            strategy = "invalid_strategy"
            reason = "testing"
        } | ConvertTo-Json
        
        $response = Invoke-RestMethod -Uri "$ORCHESTRATOR_URL/config/tool-loading" -Method Post `
            -ContentType "application/json" -Body $body
        
        Write-Host "✗ Should have failed with invalid strategy" -ForegroundColor Red
        return $false
    }
    catch {
        if ($_.Exception.Response.StatusCode -eq 400) {
            Write-Host "✓ Correctly rejected invalid strategy" -ForegroundColor Green
            return $true
        }
        else {
            Write-Host "✗ Unexpected error: $_" -ForegroundColor Red
            return $false
        }
    }
}

# Run tests
Write-Host "`nStarting test suite..." -ForegroundColor Cyan
Write-Host "Target: $ORCHESTRATOR_URL" -ForegroundColor Gray

$results = @()

# Test 1: Health check
$results += Test-HealthCheck

# Test 2: Get initial stats
$results += Test-ToolLoadingStats

# Test 3: Strategy changes
$results += Test-StrategyChange -Strategy "minimal"
$results += Test-StrategyChange -Strategy "progressive"
$results += Test-StrategyChange -Strategy "agent_profile"
$results += Test-StrategyChange -Strategy "full"
$results += Test-StrategyChange -Strategy "progressive"  # Reset to default

# Test 4: Orchestration with progressive strategy
$results += Test-Orchestration -Description "implement user authentication with email and password" `
    -ExpectedStrategy "progressive"

# Test 5: Invalid strategy handling
$results += Test-InvalidStrategy

# Summary
Write-Host "`n=== Test Summary ===" -ForegroundColor Cyan
$passed = ($results | Where-Object { $_ -eq $true }).Count
$total = $results.Count
$percentage = [math]::Round(($passed / $total) * 100, 1)

Write-Host "Passed: $passed / $total ($percentage%)" -ForegroundColor $(if ($passed -eq $total) { "Green" } else { "Yellow" })

if ($passed -eq $total) {
    Write-Host "`n✓ All tests passed! Progressive disclosure is working correctly." -ForegroundColor Green
    exit 0
}
else {
    Write-Host "`n⚠ Some tests failed. Review output above." -ForegroundColor Yellow
    exit 1
}
