#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Complete deployment of Dev-Tools to DigitalOcean droplet

.DESCRIPTION
    Deploys all 6 agent services + infrastructure services to droplet 45.55.173.72
    - Syncs .env file
    - Builds all Docker images
    - Deploys via docker compose
    - Verifies all services health

.PARAMETER SkipBuild
    Skip Docker image building (use existing images)

.PARAMETER SkipEnvSync
    Skip syncing .env file (use existing)

.EXAMPLE
    .\scripts\deploy-complete.ps1
    Full deployment

.EXAMPLE
    .\scripts\deploy-complete.ps1 -SkipBuild
    Deploy without rebuilding images
#>

param(
    [switch]$SkipBuild,
    [switch]$SkipEnvSync
)

$ErrorActionPreference = "Stop"

$DROPLET_IP = "45.55.173.72"
$DROPLET_USER = "root"
$DEPLOY_PATH = "/opt/Dev-Tools"

Write-Host "`n╔═══════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║    Dev-Tools Complete Deployment                 ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════╝" -ForegroundColor Cyan

# ============================================================================
# STEP 1: Validate Local Environment
# ============================================================================
Write-Host "`n[1/7] Validating local environment..." -ForegroundColor Yellow

if (-not (Test-Path "config/env/.env")) {
    Write-Host "❌ config/env/.env not found" -ForegroundColor Red
    Write-Host "   Copy config/env/.env.template and populate with keys" -ForegroundColor Gray
    exit 1
}

# Check required environment variables
$required_vars = @(
    "GRADIENT_MODEL_ACCESS_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "LINEAR_API_KEY"
)

$env_content = Get-Content "config/env/.env" -Raw
$missing_vars = @()

foreach ($var in $required_vars) {
    if ($env_content -notmatch "$var=\w+") {
        $missing_vars += $var
    }
}

if ($missing_vars.Count -gt 0) {
    Write-Host "❌ Missing required environment variables:" -ForegroundColor Red
    foreach ($var in $missing_vars) {
        Write-Host "   - $var" -ForegroundColor Gray
    }
    exit 1
}

Write-Host "✅ Local environment validated" -ForegroundColor Green

# ============================================================================
# STEP 2: Sync .env to Droplet
# ============================================================================
if (-not $SkipEnvSync) {
    Write-Host "`n[2/7] Syncing .env file to droplet..." -ForegroundColor Yellow
    
    scp config/env/.env "${DROPLET_USER}@${DROPLET_IP}:${DEPLOY_PATH}/config/env/.env"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to sync .env file" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "✅ .env file synced" -ForegroundColor Green
} else {
    Write-Host "`n[2/7] Skipping .env sync (using existing)" -ForegroundColor Gray
}

# ============================================================================
# STEP 3: Git Pull Latest Changes
# ============================================================================
Write-Host "`n[3/7] Pulling latest code..." -ForegroundColor Yellow

ssh "${DROPLET_USER}@${DROPLET_IP}" "cd ${DEPLOY_PATH}; git pull origin main"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to pull latest code" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Code updated" -ForegroundColor Green

# ============================================================================
# STEP 4: Stop Existing Services
# ============================================================================
Write-Host "`n[4/7] Stopping existing services..." -ForegroundColor Yellow

ssh "${DROPLET_USER}@${DROPLET_IP}" "cd ${DEPLOY_PATH}/compose; docker compose down"

Write-Host "✅ Services stopped" -ForegroundColor Green

# ============================================================================
# STEP 5: Build Docker Images
# ============================================================================
if (-not $SkipBuild) {
    Write-Host "`n[5/7] Building Docker images..." -ForegroundColor Yellow
    Write-Host "   This may take 5-10 minutes..." -ForegroundColor Gray
    
    $build_start = Get-Date
    
    ssh "${DROPLET_USER}@${DROPLET_IP}" "cd ${DEPLOY_PATH}/compose; docker compose build"
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker build failed" -ForegroundColor Red
        exit 1
    }
    
    $build_duration = (Get-Date) - $build_start
    Write-Host "✅ Images built in $($build_duration.TotalMinutes.ToString('0.0')) minutes" -ForegroundColor Green
} else {
    Write-Host "`n[5/7] Skipping image build (using existing)" -ForegroundColor Gray
}

# ============================================================================
# STEP 6: Start Services
# ============================================================================
Write-Host "`n[6/7] Starting services..." -ForegroundColor Yellow

ssh "${DROPLET_USER}@${DROPLET_IP}" "cd ${DEPLOY_PATH}/compose; docker compose up -d"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start services" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Services started" -ForegroundColor Green
Write-Host "   Waiting 30s for services to stabilize..." -ForegroundColor Gray
Start-Sleep -Seconds 30

# ============================================================================
# STEP 7: Verify Health
# ============================================================================
Write-Host "`n[7/7] Verifying service health..." -ForegroundColor Yellow

$services = @(
    @{Name="MCP Gateway"; Port=8000; Path="/health"},
    @{Name="Orchestrator Agent"; Port=8001; Path="/health"},
    @{Name="Feature Dev Agent"; Port=8002; Path="/health"},
    @{Name="Code Review Agent"; Port=8003; Path="/health"},
    @{Name="Infrastructure Agent"; Port=8004; Path="/health"},
    @{Name="CI/CD Agent"; Port=8005; Path="/health"},
    @{Name="Documentation Agent"; Port=8006; Path="/health"},
    @{Name="RAG Context"; Port=8007; Path="/health"},
    @{Name="State Persistence"; Port=8008; Path="/health"}
)

$healthy = 0
$unhealthy = 0

Write-Host "`n  Service Health Status:" -ForegroundColor Cyan
Write-Host "  ┌────────────────────────┬─────────┬─────────────────┐" -ForegroundColor Gray
Write-Host "  │ Service                │ Status  │ Details         │" -ForegroundColor Gray
Write-Host "  ├────────────────────────┼─────────┼─────────────────┤" -ForegroundColor Gray

foreach ($svc in $services) {
    try {
        $response = Invoke-RestMethod -Uri "http://${DROPLET_IP}:$($svc.Port)$($svc.Path)" -TimeoutSec 10 -ErrorAction Stop
        
        $status_icon = if ($response.status -eq "healthy" -or $response.status -eq "ok") { "✅" } else { "⚠️" }
        $status_color = if ($response.status -eq "healthy" -or $response.status -eq "ok") { "Green" } else { "Yellow" }
        
        # Extract key details
        $details = ""
        if ($response.gradient) {
            $details = "Gradient: $($response.gradient.enabled)"
        }
        if ($response.mcp_gateway) {
            $details = "MCP: $($response.mcp_gateway)"
        }
        
        Write-Host "  │ $($svc.Name.PadRight(22)) │ " -NoNewline -ForegroundColor Gray
        Write-Host "$status_icon     " -NoNewline -ForegroundColor $status_color
        Write-Host " │ $($details.PadRight(15)) │" -ForegroundColor Gray
        
        $healthy++
    } catch {
        Write-Host "  │ $($svc.Name.PadRight(22)) │ ❌      │ Offline         │" -ForegroundColor Red
        $unhealthy++
    }
}

Write-Host "  └────────────────────────┴─────────┴─────────────────┘" -ForegroundColor Gray

# ============================================================================
# SUMMARY
# ============================================================================
Write-Host "`n╔═══════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║    Deployment Summary                             ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════╝" -ForegroundColor Cyan

Write-Host "`n  Droplet:        $DROPLET_IP" -ForegroundColor White
Write-Host "  Deploy Path:    $DEPLOY_PATH" -ForegroundColor White
Write-Host "  Healthy:        $healthy / $($services.Count)" -ForegroundColor $(if ($healthy -eq $services.Count) { "Green" } else { "Yellow" })
Write-Host "  Unhealthy:      $unhealthy" -ForegroundColor $(if ($unhealthy -eq 0) { "Green" } else { "Red" })

if ($unhealthy -gt 0) {
    Write-Host "`n⚠️  Some services are unhealthy. Check logs:" -ForegroundColor Yellow
    Write-Host "   ssh ${DROPLET_USER}@${DROPLET_IP} 'cd ${DEPLOY_PATH}/compose && docker compose logs'" -ForegroundColor Gray
    exit 1
}

Write-Host "`n✅ Deployment complete! All services healthy." -ForegroundColor Green

Write-Host "`n  Access URLs:" -ForegroundColor Cyan
Write-Host "  • MCP Gateway:       http://${DROPLET_IP}:8000" -ForegroundColor White
Write-Host "  • Orchestrator:      http://${DROPLET_IP}:8001" -ForegroundColor White
Write-Host "  • Feature Dev:       http://${DROPLET_IP}:8002" -ForegroundColor White
Write-Host "  • Code Review:       http://${DROPLET_IP}:8003" -ForegroundColor White
Write-Host "  • Infrastructure:    http://${DROPLET_IP}:8004" -ForegroundColor White
Write-Host "  • CI/CD:             http://${DROPLET_IP}:8005" -ForegroundColor White
Write-Host "  • Documentation:     http://${DROPLET_IP}:8006" -ForegroundColor White
Write-Host "  • Prometheus:        http://${DROPLET_IP}:9090" -ForegroundColor White

Write-Host "`n  Next Steps:" -ForegroundColor Cyan
Write-Host '  1. Test orchestrator: Invoke-RestMethod http://45.55.173.72:8001/tasks -Method POST -Body ''{"description":"test"}'' -ContentType ''application/json''' -ForegroundColor Gray
Write-Host "  2. Check Langfuse traces: https://us.cloud.langfuse.com" -ForegroundColor Gray
Write-Host "  3. Monitor metrics: http://45.55.173.72:9090" -ForegroundColor Gray

Write-Host "" -ForegroundColor White
