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

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "🚀 Clean Rebuild & Deploy to Droplet" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Test SSH connection
Write-Host "Testing SSH connection..." -ForegroundColor Yellow
try {
    ssh -o ConnectTimeout=5 $DROPLET "echo 'Connected successfully'" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "SSH failed" }
    Write-Host "✓ SSH connection working" -ForegroundColor Green
} catch {
    Write-Host "✗ SSH connection failed: $_" -ForegroundColor Red
    exit 1
}

# Pull latest code
Write-Host "`nPulling latest code..." -ForegroundColor Yellow
ssh $DROPLET "cd $DEPLOY_PATH && git pull origin main"
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Git pull failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Code updated" -ForegroundColor Green

if (-not $SkipClean) {
    # Stop all containers
    Write-Host "`nStopping all containers..." -ForegroundColor Yellow
    ssh $DROPLET "cd $DEPLOY_PATH/compose && docker-compose down"
    Write-Host "✓ Containers stopped" -ForegroundColor Green

    # Clean up old containers and images
    Write-Host "`nCleaning up old containers and images..." -ForegroundColor Yellow
    ssh $DROPLET @"
# Remove all stopped containers
docker container prune -f

# Remove dangling images
docker image prune -f

# Remove old Dev-Tools images (keeping only latest)
docker images | grep 'compose-' | awk '{print `$3}' | tail -n +2 | xargs -r docker rmi -f 2>/dev/null || true

echo "Cleanup complete"
"@
    Write-Host "✓ Cleanup complete" -ForegroundColor Green

    # Rebuild all containers
    Write-Host "`nRebuilding all containers from scratch..." -ForegroundColor Yellow
    ssh $DROPLET "cd $DEPLOY_PATH/compose && docker-compose build --no-cache"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Build failed" -ForegroundColor Red
        exit 1
    }
    Write-Host "✓ Containers rebuilt" -ForegroundColor Green
}

# Start all services
Write-Host "`nStarting all services..." -ForegroundColor Yellow
ssh $DROPLET "cd $DEPLOY_PATH/compose && docker-compose up -d"
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Service start failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Services started" -ForegroundColor Green

# Wait for services to be ready
Write-Host "`nWaiting 15 seconds for services to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Health checks
Write-Host "`nRunning health checks..." -ForegroundColor Yellow
$services = @(
    @{Name="Gateway"; Port=8000; Path="/health"},
    @{Name="Orchestrator"; Port=8001; Path="/health"},
    @{Name="Feature-Dev"; Port=8002; Path="/health"},
    @{Name="Code-Review"; Port=8003; Path="/health"},
    @{Name="Infrastructure"; Port=8004; Path="/health"},
    @{Name="CI/CD"; Port=8005; Path="/health"},
    @{Name="Documentation"; Port=8006; Path="/health"}
)

$healthyCount = 0
foreach ($service in $services) {
    $result = ssh $DROPLET "curl -s -o /dev/null -w '%{http_code}' http://localhost:$($service.Port)$($service.Path)"
    if ($result -eq "200") {
        Write-Host "  ✓ $($service.Name) (port $($service.Port))" -ForegroundColor Green
        $healthyCount++
    } else {
        Write-Host "  ✗ $($service.Name) (port $($service.Port)) - HTTP $result" -ForegroundColor Red
    }
}

Write-Host "`n$healthyCount/$($services.Count) services healthy" -ForegroundColor $(if ($healthyCount -eq $services.Count) { "Green" } else { "Yellow" })

if (-not $SkipTests) {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "🧪 Running Validation Tests" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    # Test 1: Orchestrator with Langfuse tracing
    Write-Host "Test 1: Orchestrator Task Decomposition (creates Langfuse trace)..." -ForegroundColor Yellow
    $orchResponse = ssh $DROPLET @"
curl -X POST http://localhost:8001/orchestrate \
  -H 'Content-Type: application/json' \
  -d '{\"description\":\"Build a REST API with authentication and user management\",\"priority\":\"high\"}' \
  -w '\n%{http_code}' -s
"@
    
    $statusCode = ($orchResponse -split "`n")[-1]
    if ($statusCode -eq "200") {
        Write-Host "  ✓ Orchestrator responding (HTTP $statusCode)" -ForegroundColor Green
        Write-Host "  Response preview: $(($orchResponse -split "`n")[0..2] -join ' ')" -ForegroundColor Gray
    } else {
        Write-Host "  ✗ Orchestrator failed (HTTP $statusCode)" -ForegroundColor Red
    }

    # Test 2: Feature-Dev agent
    Write-Host "`nTest 2: Feature-Dev Code Generation..." -ForegroundColor Yellow
    $featureResponse = ssh $DROPLET @"
curl -X POST http://localhost:8002/generate \
  -H 'Content-Type: application/json' \
  -d '{\"feature\":\"user authentication endpoint\",\"framework\":\"FastAPI\"}' \
  -w '\n%{http_code}' -s
"@
    
    $statusCode = ($featureResponse -split "`n")[-1]
    if ($statusCode -eq "200") {
        Write-Host "  ✓ Feature-Dev responding (HTTP $statusCode)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Feature-Dev failed (HTTP $statusCode)" -ForegroundColor Red
    }

    # Test 3: Code-Review agent
    Write-Host "`nTest 3: Code-Review Analysis..." -ForegroundColor Yellow
    $reviewResponse = ssh $DROPLET @"
curl -X POST http://localhost:8003/review \
  -H 'Content-Type: application/json' \
  -d '{\"code\":\"def hello():\n    return '\''world'\''\",\"language\":\"python\"}' \
  -w '\n%{http_code}' -s
"@
    
    $statusCode = ($reviewResponse -split "`n")[-1]
    if ($statusCode -eq "200") {
        Write-Host "  ✓ Code-Review responding (HTTP $statusCode)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Code-Review failed (HTTP $statusCode)" -ForegroundColor Red
    }

    # Test 4: MCP Gateway tool discovery
    Write-Host "`nTest 4: MCP Gateway Tool Discovery..." -ForegroundColor Yellow
    $mcpResponse = ssh $DROPLET "curl -s http://localhost:8000/api/tools -w '\n%{http_code}'"
    $statusCode = ($mcpResponse -split "`n")[-1]
    if ($statusCode -eq "200") {
        Write-Host "  ✓ MCP Gateway responding (HTTP $statusCode)" -ForegroundColor Green
        $toolCount = (($mcpResponse -split "`n")[0] | ConvertFrom-Json).tools.Count
        Write-Host "  Found $toolCount MCP tools" -ForegroundColor Gray
    } else {
        Write-Host "  ✗ MCP Gateway failed (HTTP $statusCode)" -ForegroundColor Red
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "✅ Deployment Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "📊 Verification Steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Check Langfuse Traces:" -ForegroundColor White
Write-Host "   https://us.cloud.langfuse.com" -ForegroundColor Cyan
Write-Host "   Filter by: metadata.agent_name = `"orchestrator`"" -ForegroundColor Gray
Write-Host "   Expected: Task decomposition trace with LLM calls" -ForegroundColor Gray
Write-Host ""
Write-Host "2. View Frontend:" -ForegroundColor White
Write-Host "   http://45.55.173.72/production-landing.html" -ForegroundColor Cyan
Write-Host "   http://45.55.173.72/agents.html" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Manual Tests (run from your terminal):" -ForegroundColor White
Write-Host "   # Test orchestrator" -ForegroundColor Gray
Write-Host "   ssh $DROPLET `"curl -X POST http://localhost:8001/orchestrate -H 'Content-Type: application/json' -d '{\"description\":\"Create a web app\",\"priority\":\"high\"}'`"" -ForegroundColor Gray
Write-Host ""
Write-Host "   # Check logs" -ForegroundColor Gray
Write-Host "   ssh $DROPLET `"cd $DEPLOY_PATH/compose && docker-compose logs -f orchestrator`"" -ForegroundColor Gray
Write-Host ""
Write-Host "   # View all running containers" -ForegroundColor Gray
Write-Host "   ssh $DROPLET `"docker ps`"" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Curl Tests for Tracing Validation:" -ForegroundColor White
Write-Host "   # From droplet (already tested above)" -ForegroundColor Gray
Write-Host "   curl -X POST http://localhost:8001/orchestrate \\" -ForegroundColor Gray
Write-Host "     -H 'Content-Type: application/json' \\" -ForegroundColor Gray
Write-Host "     -d '{\"description\":\"Test task\",\"priority\":\"high\"}'" -ForegroundColor Gray
Write-Host ""
Write-Host "   # Check Langfuse for trace with:" -ForegroundColor Gray
Write-Host "   - Session ID (task_id from response)" -ForegroundColor Gray
Write-Host "   - User ID (agent_name: orchestrator)" -ForegroundColor Gray
Write-Host "   - LLM calls with token counts" -ForegroundColor Gray
Write-Host ""
