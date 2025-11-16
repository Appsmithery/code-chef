#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Simple deployment - minimal steps

.DESCRIPTION
    Deploys to droplet using minimal commands to avoid SSH hanging
#>

$ErrorActionPreference = "Continue"

$DROPLET = "root@45.55.173.72"
$PATH = "/opt/Dev-Tools"

Write-Host "`n=== Dev-Tools Simple Deployment ===" -ForegroundColor Cyan

# Step 1: Sync .env
Write-Host "`n[1] Syncing .env..." -ForegroundColor Yellow
scp config/env/.env "${DROPLET}:${PATH}/config/env/.env"

# Step 2: Pull code
Write-Host "`n[2] Pulling code..." -ForegroundColor Yellow
ssh $DROPLET "cd $PATH; git pull"

# Step 3: Check compose file
Write-Host "`n[3] Checking compose file..." -ForegroundColor Yellow
ssh $DROPLET "ls -la $PATH/compose/docker-compose.yml"

# Step 4: Build one service at a time
Write-Host "`n[4] Building services..." -ForegroundColor Yellow
Write-Host "    Building gateway-mcp..." -ForegroundColor Gray
ssh $DROPLET "cd $PATH/compose; docker compose build gateway-mcp 2>&1 | tail -10"

Write-Host "    Building orchestrator..." -ForegroundColor Gray
ssh $DROPLET "cd $PATH/compose; docker compose build orchestrator 2>&1 | tail -10"

# Step 5: Start infrastructure only
Write-Host "`n[5] Starting infrastructure services..." -ForegroundColor Yellow
ssh $DROPLET "cd $PATH/compose; docker compose up -d gateway-mcp rag-context state-persistence qdrant postgres prometheus"

# Step 6: Check status
Write-Host "`n[6] Checking status..." -ForegroundColor Yellow
ssh $DROPLET "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"

Write-Host "`n=== Deployment Steps Complete ===" -ForegroundColor Green
Write-Host "Next: Build and start agent services individually" -ForegroundColor Gray
