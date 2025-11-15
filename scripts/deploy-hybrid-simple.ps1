#!/usr/bin/env pwsh
# Simple Hybrid Deployment Script

$ErrorActionPreference = "Stop"
$DROPLET_IP = "45.55.173.72"
$DROPLET_USER = "root"
$DEPLOY_PATH = "/opt/Dev-Tools"

Write-Host "`n🚀 Dev-Tools Hybrid Deployment`n" -ForegroundColor Cyan

# Deploy to droplet
Write-Host "📦 Deploying to droplet..." -ForegroundColor Green
ssh $DROPLET_USER@$DROPLET_IP @"
cd $DEPLOY_PATH
git pull origin main
docker compose -f compose/docker-compose.yml up -d gateway-mcp rag-context state-persistence qdrant postgres prometheus
"@

Write-Host "`n⏳ Waiting for services (15s)..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Verify
Write-Host "`n🏥 Checking gateway health..." -ForegroundColor Green
try {
    $health = Invoke-RestMethod -Uri "http://${DROPLET_IP}:8000/health" -TimeoutSec 10
    Write-Host "✅ Gateway: $($health.status)" -ForegroundColor Green
    Write-Host "   MCP Servers: $($health.mcp_servers_count)" -ForegroundColor Gray
} catch {
    Write-Warning "⚠️  Gateway health check failed"
}

Write-Host "`n✅ Deployment complete!`n" -ForegroundColor Green
