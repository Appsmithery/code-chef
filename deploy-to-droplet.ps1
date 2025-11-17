#!/usr/bin/env pwsh
# Clean Rebuild & Deployment Script for DigitalOcean Droplet
# Scrubs old containers and rebuilds from scratch to avoid configuration drift

param(
    [switch]$SkipClean,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$DROPLET = "do-mcp-gateway"
$DEPLOY_PATH = "/opt/Dev-Tools"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Clean Rebuild & Deploy to Droplet" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test SSH connection
Write-Host "Testing SSH connection..." -ForegroundColor Yellow
ssh -o ConnectTimeout=5 $DROPLET "echo 'Connected successfully'" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "SSH connection failed" -ForegroundColor Red
    exit 1
}
Write-Host "SSH connection working" -ForegroundColor Green

# Pull latest code
Write-Host ""
Write-Host "Pulling latest code..." -ForegroundColor Yellow
ssh $DROPLET "cd $DEPLOY_PATH ; git pull origin main"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Git pull failed" -ForegroundColor Red
    exit 1
}
Write-Host "Code updated" -ForegroundColor Green

if (-not $SkipClean) {
    # Stop all containers
    Write-Host ""
    Write-Host "Stopping all containers..." -ForegroundColor Yellow
    ssh $DROPLET "cd $DEPLOY_PATH/compose ; docker-compose down"
    Write-Host "Containers stopped" -ForegroundColor Green

    # Clean up old containers and images
    Write-Host ""
    Write-Host "Cleaning up old containers and images..." -ForegroundColor Yellow
    ssh $DROPLET "docker container prune -f"
    ssh $DROPLET "docker image prune -f"
    Write-Host "Cleanup complete" -ForegroundColor Green

    # Rebuild all containers
    Write-Host ""
    Write-Host "Rebuilding all containers from scratch..." -ForegroundColor Yellow
    ssh $DROPLET "cd $DEPLOY_PATH/compose ; docker-compose build --no-cache"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Build failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "Containers rebuilt" -ForegroundColor Green
}

# Start all services
Write-Host ""
Write-Host "Starting all services..." -ForegroundColor Yellow
ssh $DROPLET "cd $DEPLOY_PATH/compose ; docker-compose up -d"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Service start failed" -ForegroundColor Red
    exit 1
}
Write-Host "Services started" -ForegroundColor Green

# Wait for services to be ready
Write-Host ""
Write-Host "Waiting 15 seconds for services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Health checks
Write-Host ""
Write-Host "Running health checks..." -ForegroundColor Yellow
$services = @(
    @{Name="Gateway"; Port=8000},
    @{Name="Orchestrator"; Port=8001},
    @{Name="Feature-Dev"; Port=8002},
    @{Name="Code-Review"; Port=8003},
    @{Name="Infrastructure"; Port=8004},
    @{Name="CI/CD"; Port=8005},
    @{Name="Documentation"; Port=8006}
)

$healthyCount = 0
foreach ($service in $services) {
    $result = ssh $DROPLET "curl -s -o /dev/null -w '%{http_code}' http://localhost:$($service.Port)/health" 2>$null
    if ($result -eq "200") {
        Write-Host "  $($service.Name) (port $($service.Port))" -ForegroundColor Green
        $healthyCount++
    } else {
        Write-Host "  $($service.Name) (port $($service.Port)) - HTTP $result" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "$healthyCount/$($services.Count) services healthy" -ForegroundColor $(if ($healthyCount -eq $services.Count) { "Green" } else { "Yellow" })

if (-not $SkipTests) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Running Validation Tests" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    # Test 1: Orchestrator with Langfuse tracing
    Write-Host "Test 1: Orchestrator Task Decomposition (creates Langfuse trace)..." -ForegroundColor Yellow
    $orchCmd = "curl -X POST http://localhost:8001/orchestrate -H 'Content-Type: application/json' -d '{`"description`":`"Build a REST API with authentication`",`"priority`":`"high`"}' -s -o /dev/null -w '%{http_code}'"
    $statusCode = ssh $DROPLET $orchCmd
    if ($statusCode -eq "200") {
        Write-Host "  Orchestrator responding (HTTP $statusCode)" -ForegroundColor Green
    } else {
        Write-Host "  Orchestrator failed (HTTP $statusCode)" -ForegroundColor Red
    }

    # Test 2: Feature-Dev agent
    Write-Host ""
    Write-Host "Test 2: Feature-Dev Code Generation..." -ForegroundColor Yellow
    $featureCmd = "curl -X POST http://localhost:8002/generate -H 'Content-Type: application/json' -d '{`"feature`":`"user authentication`",`"framework`":`"FastAPI`"}' -s -o /dev/null -w '%{http_code}'"
    $statusCode = ssh $DROPLET $featureCmd
    if ($statusCode -eq "200") {
        Write-Host "  Feature-Dev responding (HTTP $statusCode)" -ForegroundColor Green
    } else {
        Write-Host "  Feature-Dev failed (HTTP $statusCode)" -ForegroundColor Red
    }

    # Test 3: MCP Gateway
    Write-Host ""
    Write-Host "Test 3: MCP Gateway Tool Discovery..." -ForegroundColor Yellow
    $mcpCmd = "curl -s http://localhost:8000/api/tools -o /dev/null -w '%{http_code}'"
    $statusCode = ssh $DROPLET $mcpCmd
    if ($statusCode -eq "200") {
        Write-Host "  MCP Gateway responding (HTTP $statusCode)" -ForegroundColor Green
    } else {
        Write-Host "  MCP Gateway failed (HTTP $statusCode)" -ForegroundColor Red
    }

    # Copy and run validation script
    Write-Host ""
    Write-Host "Running comprehensive validation script on droplet..." -ForegroundColor Yellow
    scp -q scripts/validate-tracing.sh ${DROPLET}:/tmp/validate-tracing.sh
    ssh $DROPLET "chmod +x /tmp/validate-tracing.sh ; /tmp/validate-tracing.sh"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Verification Steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Check Langfuse Traces:" -ForegroundColor White
Write-Host "   https://us.cloud.langfuse.com" -ForegroundColor Cyan
Write-Host "   Filter by: metadata.agent_name = 'orchestrator'" -ForegroundColor Gray
Write-Host "   Expected: Task decomposition trace with LLM calls" -ForegroundColor Gray
Write-Host ""
Write-Host "2. View Frontend:" -ForegroundColor White
Write-Host "   http://45.55.173.72/production-landing.html" -ForegroundColor Cyan
Write-Host "   http://45.55.173.72/agents.html" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Manual curl tests:" -ForegroundColor White
Write-Host "   ssh $DROPLET 'curl -X POST http://localhost:8001/orchestrate -H Content-Type:application/json -d {description:test,priority:high}'" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Check logs:" -ForegroundColor White
Write-Host "   ssh $DROPLET 'cd $DEPLOY_PATH/compose ; docker-compose logs -f orchestrator'" -ForegroundColor Gray
Write-Host ""
