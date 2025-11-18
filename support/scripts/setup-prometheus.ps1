# Prometheus Monitoring Setup Script
# Automates Prometheus configuration, validation, and deployment

$ErrorActionPreference = "Stop"

Write-Host "`n[SETUP] Setting up Prometheus monitoring for Dev-Tools..." -ForegroundColor Cyan

# Step 1: Verify Configuration Files
Write-Host "`n[STEP 1] Verifying configuration files..." -ForegroundColor Yellow

$configDir = "config/prometheus"
$prometheusYml = "$configDir/prometheus.yml"
$dockerCompose = "deploy/docker-compose.yml"

if (Test-Path $prometheusYml) {
    Write-Host "  [OK] Found: $prometheusYml" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Missing: $prometheusYml" -ForegroundColor Red
    exit 1
}

if (Test-Path $dockerCompose) {
    Write-Host "  [OK] Found: $dockerCompose" -ForegroundColor Green
    
    $composeContent = Get-Content $dockerCompose -Raw
    if ($composeContent -match "prometheus:") {
        Write-Host "  [OK] Prometheus service defined in docker-compose.yml" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Prometheus service not found in docker-compose.yml" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "  [ERROR] Missing: $dockerCompose" -ForegroundColor Red
    exit 1
}

# Step 2: Verify Agent Instrumentation
Write-Host "`n[STEP 2] Checking Prometheus instrumentation..." -ForegroundColor Yellow

$agents = @("orchestrator", "feature-dev", "code-review", "infrastructure", "cicd", "documentation")
$allInstrumented = $true

foreach ($agent in $agents) {
    $reqFile = "agents/$agent/requirements.txt"
    $mainFile = "agents/$agent/main.py"
    
    if (Test-Path $reqFile) {
        $content = Get-Content $reqFile -Raw
        if ($content -match "prometheus-fastapi-instrumentator") {
            Write-Host "  [OK] $agent - prometheus-fastapi-instrumentator in requirements.txt" -ForegroundColor Green
        } else {
            Write-Host "  [ERROR] $agent - Missing prometheus-fastapi-instrumentator" -ForegroundColor Red
            $allInstrumented = $false
        }
    }
    
    if (Test-Path $mainFile) {
        $content = Get-Content $mainFile -Raw
        if ($content -match "from prometheus_fastapi_instrumentator import Instrumentator") {
            Write-Host "  [OK] $agent - Instrumentator imported in main.py" -ForegroundColor Green
        } else {
            Write-Host "  [ERROR] $agent - Missing Instrumentator import" -ForegroundColor Red
            $allInstrumented = $false
        }
        
        if ($content -match "Instrumentator\(\)\.instrument\(app\)\.expose\(app\)") {
            Write-Host "  [OK] $agent - Metrics endpoint exposed" -ForegroundColor Green
        } else {
            Write-Host "  [ERROR] $agent - Metrics endpoint not exposed" -ForegroundColor Red
            $allInstrumented = $false
        }
    }
}

if (-not $allInstrumented) {
    Write-Host "`n[WARNING] Some agents are not fully instrumented" -ForegroundColor Yellow
    exit 1
}

# Step 3: Validate Prometheus Configuration
Write-Host "`n[STEP 3] Validating prometheus.yml..." -ForegroundColor Yellow

$prometheusConfig = Get-Content $prometheusYml -Raw
$expectedJobs = @("orchestrator", "feature-dev", "code-review", "infrastructure", "cicd", "documentation", "gateway-mcp", "prometheus")

foreach ($job in $expectedJobs) {
    if ($prometheusConfig -match "job_name: '$job'") {
        Write-Host "  [OK] Job configured: $job" -ForegroundColor Green
    } else {
        Write-Host "  [WARNING] Job missing: $job" -ForegroundColor Yellow
    }
}

# Step 4: Docker Compose Validation
Write-Host "`n[STEP 4] Validating docker-compose.yml..." -ForegroundColor Yellow

try {
    Set-Location compose
    docker-compose config | Out-Null
    Write-Host "  [OK] docker-compose.yml is valid" -ForegroundColor Green
    Set-Location ..
} catch {
    Write-Host "  [ERROR] docker-compose.yml has syntax errors" -ForegroundColor Red
    Set-Location ..
    exit 1
}

# Summary
Write-Host "`n======================================" -ForegroundColor Cyan
Write-Host "  Prometheus Setup Summary" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

Write-Host "`n[CONFIGURATION]" -ForegroundColor Green
Write-Host "  * Prometheus config: $prometheusYml" -ForegroundColor White
Write-Host "  * Docker Compose: $dockerCompose" -ForegroundColor White
Write-Host "  * Agents instrumented: 6/6" -ForegroundColor White
Write-Host "  * Scrape targets: 8+" -ForegroundColor White

Write-Host "`n[ENDPOINTS]" -ForegroundColor Cyan
Write-Host "  * Prometheus UI: http://localhost:9090" -ForegroundColor White
Write-Host "  * Targets Status: http://localhost:9090/targets" -ForegroundColor White
Write-Host "  * Metrics Query: http://localhost:9090/graph" -ForegroundColor White

Write-Host "`n[AGENT METRICS]" -ForegroundColor Cyan
Write-Host "  * Orchestrator: http://localhost:8001/metrics" -ForegroundColor White
Write-Host "  * Feature Dev: http://localhost:8002/metrics" -ForegroundColor White
Write-Host "  * Code Review: http://localhost:8003/metrics" -ForegroundColor White
Write-Host "  * Infrastructure: http://localhost:8004/metrics" -ForegroundColor White
Write-Host "  * CI/CD: http://localhost:8005/metrics" -ForegroundColor White
Write-Host "  * Documentation: http://localhost:8006/metrics" -ForegroundColor White

Write-Host "`n[NEXT STEPS]" -ForegroundColor Yellow
Write-Host "  1. Build agents with Prometheus support:" -ForegroundColor White
Write-Host "     docker-compose -f deploy/docker-compose.yml build" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Start Prometheus:" -ForegroundColor White
Write-Host "     docker-compose -f deploy/docker-compose.yml up -d prometheus" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Restart agents to enable metrics:" -ForegroundColor White
Write-Host "     docker-compose -f deploy/docker-compose.yml restart orchestrator feature-dev code-review infrastructure cicd documentation" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. Verify targets are being scraped:" -ForegroundColor White
Write-Host "     Start-Process 'http://localhost:9090/targets'" -ForegroundColor Gray

Write-Host "`n[EXAMPLE QUERIES]" -ForegroundColor Cyan
Write-Host "  * Request rate: rate(http_requests_total[5m])" -ForegroundColor White
Write-Host "  * Response time: http_request_duration_seconds" -ForegroundColor White
Write-Host "  * Error rate: rate(http_requests_total)" -ForegroundColor White
Write-Host "  * Active requests: http_requests_inprogress" -ForegroundColor White

Write-Host "`n[OK] Prometheus setup validation complete!`n" -ForegroundColor Green
