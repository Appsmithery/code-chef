#!/usr/bin/env pwsh
<#
.SYNOPSIS
    End-to-end functional test for code-chef deployment

.DESCRIPTION
    Validates all services are operational and can handle requests.
    Tests:
    1. Health endpoints for all services
    2. Orchestrator API functionality
    3. RAG context search
    4. State persistence
    5. Agent registry
    6. Metrics scraping

.PARAMETER Host
    The droplet host or IP address (default: 45.55.173.72)

.EXAMPLE
    .\test-deployment.ps1
    Run full functional test suite
#>

param(
    [string]$HostAddress = "45.55.173.72"
)

$ErrorActionPreference = "Stop"

# Test results tracking
$results = @{
    passed = 0
    failed = 0
    tests  = @()
}

function Write-TestHeader {
    param([string]$Text)
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host " $Text" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

function Write-TestResult {
    param(
        [string]$TestName,
        [bool]$Passed,
        [string]$Message = ""
    )
    
    $results.tests += @{
        name    = $TestName
        passed  = $Passed
        message = $Message
    }
    
    if ($Passed) {
        $results.passed++
        Write-Host "âœ“ $TestName" -ForegroundColor Green
        if ($Message) {
            Write-Host "  $Message" -ForegroundColor Gray
        }
    }
    else {
        $results.failed++
        Write-Host "âœ— $TestName" -ForegroundColor Red
        if ($Message) {
            Write-Host "  Error: $Message" -ForegroundColor Yellow
        }
    }
}

function Test-ServiceHealth {
    param(
        [string]$ServiceName,
        [int]$Port,
        [string]$ExpectedKey = "status"
    )
    
    try {
        $response = ssh root@$HostAddress "curl -s http://localhost:$Port/health"
        $json = $response | ConvertFrom-Json
        
        if ($json.$ExpectedKey) {
            Write-TestResult -TestName "$ServiceName health check" -Passed $true -Message "$($json.$ExpectedKey)"
            return $true
        }
        else {
            Write-TestResult -TestName "$ServiceName health check" -Passed $false -Message "Missing $ExpectedKey in response"
            return $false
        }
    }
    catch {
        Write-TestResult -TestName "$ServiceName health check" -Passed $false -Message $_.Exception.Message
        return $false
    }
}

function Test-MetricsEndpoint {
    param(
        [string]$ServiceName,
        [int]$Port
    )
    
    try {
        $response = ssh root@$HostAddress "curl -s http://localhost:$Port/metrics | head -5"
        
        if ($response -match "# HELP | # TYPE") {
        Write-TestResult -TestName "$ServiceName metrics" -Passed $true -Message "Prometheus metrics available"
        return $true
    }
    else {
        Write-TestResult -TestName "$ServiceName metrics" -Passed $false -Message "Invalid metrics format"
        return $false
    }
}
catch {
    Write-TestResult -TestName "$ServiceName metrics" -Passed $false -Message $_.Exception.Message
    return $false
}
}

# ============================================================================
# Main Test Suite
# ============================================================================

Write-TestHeader "Code-Chef Functional Test Suite"
Write-Host "Testing droplet: $HostAddress`n" -ForegroundColor Blue

# Test 1: Core Service Health Checks
Write-TestHeader "1. Service Health Checks"

Test-ServiceHealth -ServiceName "Orchestrator" -Port 8001 -ExpectedKey "status"
Test-ServiceHealth -ServiceName "RAG Context" -Port 8007 -ExpectedKey "status"
Test-ServiceHealth -ServiceName "State Persistence" -Port 8008 -ExpectedKey "status"
Test-ServiceHealth -ServiceName "Agent Registry" -Port 8009 -ExpectedKey "status"
Test-ServiceHealth -ServiceName "LangGraph" -Port 8010 -ExpectedKey "status"

# Test 2: Metrics Endpoints
Write-TestHeader "2. Prometheus Metrics"

Test-MetricsEndpoint -ServiceName "RAG Context" -Port 8007
Test-MetricsEndpoint -ServiceName "State Persistence" -Port 8008

# Test 3: Frontend Access
Write-TestHeader "3. Frontend & Caddy"

try {
    $statusCode = ssh root@$HostAddress "curl -s -o /dev/null -w '%{http_code}' http://localhost:80/"
    
    if ($statusCode -eq "200") {
        Write-TestResult -TestName "Frontend serving" -Passed $true -Message "HTTP $statusCode"
    }
    else {
        Write-TestResult -TestName "Frontend serving" -Passed $false -Message "HTTP $statusCode (expected 200)"
    }
}
catch {
    Write-TestResult -TestName "Frontend serving" -Passed $false -Message $_.Exception.Message
}

# Test 4: Database Connectivity
Write-TestHeader "4. Database Connectivity"

try {
    $pgTest = ssh root@$HostAddress "docker exec deploy-postgres-1 psql -U devtools -d devtools -c 'SELECT 1;' 2>&1"
    
    if ($pgTest -match "1 row") {
        Write-TestResult -TestName "PostgreSQL connection" -Passed $true -Message "Database responsive"
    }
    else {
        Write-TestResult -TestName "PostgreSQL connection" -Passed $false -Message "Query failed"
    }
}
catch {
    Write-TestResult -TestName "PostgreSQL connection" -Passed $false -Message $_.Exception.Message
}

# Test 5: Redis Connectivity
try {
    $redisTest = ssh root@$HostAddress "docker exec deploy-redis-1 redis-cli ping"
    
    if ($redisTest -match "PONG") {
        Write-TestResult -TestName "Redis connection" -Passed $true -Message "Cache responsive"
    }
    else {
        Write-TestResult -TestName "Redis connection" -Passed $false -Message "Ping failed"
    }
}
catch {
    Write-TestResult -TestName "Redis connection" -Passed $false -Message $_.Exception.Message
}

# Test 6: Container Status
Write-TestHeader "5. Container Health Status"

try {
    $containers = ssh root@$HostAddress "cd /opt/code-chef/deploy && docker compose ps --format json" | ConvertFrom-Json
    
    foreach ($container in $containers) {
        $isHealthy = $container.Health -match "healthy" -or $container.Status -match "Up" -and $container.Health -eq ""
        
        if ($isHealthy) {
            Write-TestResult -TestName "Container: $($container.Service)" -Passed $true -Message $container.Status
        }
        else {
            Write-TestResult -TestName "Container: $($container.Service)" -Passed $false -Message $container.Status
        }
    }
}
catch {
    Write-TestResult -TestName "Container status check" -Passed $false -Message $_.Exception.Message
}

# Test 7: Basic API Request
Write-TestHeader "6. API Functionality"

try {
    # Test orchestrator config endpoint
    $configResponse = ssh root@$HostAddress "curl -s http://localhost:8001/config/agents"
    $config = $configResponse | ConvertFrom-Json
    
    if ($config.feature_dev -or $config.PSObject.Properties.Count -gt 0) {
        Write-TestResult -TestName "Orchestrator API" -Passed $true -Message "Agent config accessible"
    }
    else {
        Write-TestResult -TestName "Orchestrator API" -Passed $false -Message "No agent config returned"
    }
}
catch {
    Write-TestResult -TestName "Orchestrator API" -Passed $false -Message $_.Exception.Message
}

# ============================================================================
# Test Summary
# ============================================================================

Write-TestHeader "Test Summary"

$total = $results.passed + $results.failed
$passRate = if ($total -gt 0) { [math]::Round(($results.passed / $total) * 100, 1) } else { 0 }

Write-Host ""
Write-Host "Total Tests: $total" -ForegroundColor Cyan
Write-Host "Passed:      $($results.passed)" -ForegroundColor Green
Write-Host "Failed:      $($results.failed)" -ForegroundColor $(if ($results.failed -gt 0) { "Red" } else { "Gray" })
Write-Host "Pass Rate:   $passRate%" -ForegroundColor $(if ($passRate -ge 80) { "Green" } elseif ($passRate -ge 60) { "Yellow" } else { "Red" })
Write-Host ""

if ($results.failed -gt 0) {
    Write-Host "Failed Tests:" -ForegroundColor Red
    foreach ($test in $results.tests | Where-Object { -not $_.passed }) {
        Write-Host "  â€¢ $($test.name): $($test.message)" -ForegroundColor Yellow
    }
    Write-Host ""
}

# Exit with appropriate code
if ($results.failed -gt 0) {
    Write-Host "âŒ Some tests failed. Review issues above." -ForegroundColor Red
    exit 1
}
else {
    Write-Host "âœ… All tests passed! Deployment is healthy." -ForegroundColor Green
    exit 0
}

