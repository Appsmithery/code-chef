#!/usr/bin/env pwsh
# Quick deployment script for DigitalOcean droplet
# Run this locally to deploy frontend and test tracing

$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "🚀 Deploying to Droplet via SSH" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Test SSH connection first
Write-Host "Testing SSH connection..." -ForegroundColor Yellow
try {
    $testResult = ssh -o ConnectTimeout=5 do-mcp-gateway "echo 'Connected successfully'"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ SSH connection working" -ForegroundColor Green
    } else {
        Write-Host "✗ SSH connection failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "✗ SSH error: $_" -ForegroundColor Red
    exit 1
}

# Pull latest code
Write-Host "`nPulling latest code..." -ForegroundColor Yellow
ssh do-mcp-gateway "cd /opt/Dev-Tools && git pull origin main"
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Git pull failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Code updated" -ForegroundColor Green

# Restart gateway to serve new frontend
Write-Host "`nRestarting gateway..." -ForegroundColor Yellow
ssh do-mcp-gateway "cd /opt/Dev-Tools/compose && docker-compose restart gateway-mcp"
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Gateway restart failed" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Gateway restarted" -ForegroundColor Green

# Wait for services
Write-Host "`nWaiting 10 seconds for services..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check agent health
Write-Host "`nChecking agent health..." -ForegroundColor Yellow
$ports = @(8001, 8002, 8003, 8004, 8005, 8006)
foreach ($port in $ports) {
    Write-Host "  Testing port $port..." -ForegroundColor Gray
    $result = ssh do-mcp-gateway "curl -s http://localhost:$port/health"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Port $port healthy" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Port $port unhealthy" -ForegroundColor Red
    }
}

# Trigger orchestration to create Langfuse trace
Write-Host "`nTriggering orchestration (creates Langfuse trace)..." -ForegroundColor Yellow
$orchResult = ssh do-mcp-gateway @"
curl -X POST http://localhost:8001/orchestrate \
  -H 'Content-Type: application/json' \
  -d '{\"description\":\"Build REST API with authentication\",\"priority\":\"high\"}'
"@

Write-Host "Orchestration response:" -ForegroundColor Gray
Write-Host $orchResult -ForegroundColor White

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "✅ Deployment Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "📊 Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Check Langfuse: https://us.cloud.langfuse.com" -ForegroundColor White
Write-Host "     Filter: metadata.agent_name = `"orchestrator`"" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. View Frontend:" -ForegroundColor White
Write-Host "     http://45.55.173.72/production-landing.html" -ForegroundColor Gray
Write-Host "     http://45.55.173.72/agents.html" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Check Logs:" -ForegroundColor White
Write-Host "     ssh do-mcp-gateway `"cd /opt/Dev-Tools/compose && docker-compose logs -f orchestrator`"" -ForegroundColor Gray
Write-Host ""
