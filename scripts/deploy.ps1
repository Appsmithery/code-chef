#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy Dev-Tools agent stack (local or remote)

.DESCRIPTION
    Automated deployment script for Dev-Tools with validation and health checks.
    Supports both local deployment and remote deployment to DigitalOcean droplet.

.PARAMETER Target
    Deployment target: 'local' or 'remote' (default: local)

.PARAMETER SkipBuild
    Skip container rebuild (faster, use only if code unchanged)

.PARAMETER SkipValidation
    Skip pre-deployment validation checks

.EXAMPLE
    ./scripts/deploy.ps1
    Deploy locally with full validation

.EXAMPLE
    ./scripts/deploy.ps1 -Target remote
    Deploy to DigitalOcean droplet

.EXAMPLE
    ./scripts/deploy.ps1 -SkipBuild
    Deploy locally without rebuilding containers
#>

param(
    [Parameter()]
    [ValidateSet('local', 'remote')]
    [string]$Target = 'local',
    
    [Parameter()]
    [switch]$SkipBuild,
    
    [Parameter()]
    [switch]$SkipValidation
)

$ErrorActionPreference = "Stop"

# Colors
function Write-Step { param($msg) Write-Host "`n[STEP] $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Error-Custom { param($msg) Write-Host "  [ERROR] $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "  -> $msg" -ForegroundColor Gray }

# Header
Write-Host "`n==========================================" -ForegroundColor Magenta
Write-Host "  🚀 Dev-Tools Deployment Script" -ForegroundColor Magenta
Write-Host "==========================================" -ForegroundColor Magenta
Write-Host "  Target: $Target" -ForegroundColor White
Write-Host "  Skip Build: $SkipBuild" -ForegroundColor White
Write-Host "  Skip Validation: $SkipValidation" -ForegroundColor White
Write-Host "==========================================" -ForegroundColor Magenta

# Validation
if (-not $SkipValidation) {
    Write-Step "Validating environment..."
    
    # Check .env file
    if (-not (Test-Path "config/env/.env")) {
        Write-Error-Custom ".env file not found!"
        Write-Info "Run: cp config/env/.env.example config/env/.env"
        exit 1
    }
    Write-Success ".env file exists"
    
    # Check required env vars
    $env_content = Get-Content "config/env/.env" -Raw
    $required_vars = @(
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_PUBLIC_KEY",
        "GRADIENT_API_KEY"
    )
    
    $missing_vars = @()
    foreach ($var in $required_vars) {
        if ($env_content -notmatch "$var=.+") {
            $missing_vars += $var
        }
    }
    
    if ($missing_vars.Count -gt 0) {
        Write-Error-Custom "Missing required environment variables:"
        foreach ($var in $missing_vars) {
            Write-Info "  - $var"
        }
        exit 1
    }
    Write-Success "All required environment variables set"
    
    # Check Docker
    try {
        docker --version | Out-Null
        Write-Success "Docker available"
    } catch {
        Write-Error-Custom "Docker not found! Install Docker first."
        exit 1
    }
    
    try {
        docker-compose --version | Out-Null
        Write-Success "Docker Compose available"
    } catch {
        Write-Error-Custom "Docker Compose not found! Install it first."
        exit 1
    }
    
    # Check secrets (if Linear configured)
    if (Test-Path "config/env/secrets/linear_oauth_token.txt") {
        Write-Success "Linear secrets configured"
    } else {
        Write-Info "Linear secrets not found (optional)"
    }
}

# Local Deployment
if ($Target -eq 'local') {
    Write-Step "Deploying locally..."
    
    Set-Location "compose"
    
    # Build containers
    if (-not $SkipBuild) {
        Write-Info "Building containers (this may take 5-10 minutes)..."
        docker-compose build
        if ($LASTEXITCODE -ne 0) {
            Write-Error-Custom "Build failed!"
            exit 1
        }
        Write-Success "Containers built"
    } else {
        Write-Info "Skipping build"
    }
    
    # Start services
    Write-Info "Starting services..."
    docker-compose up -d
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Deployment failed!"
        exit 1
    }
    Write-Success "Services started"
    
    # Wait for services
    Write-Info "Waiting for services to initialize (15 seconds)..."
    Start-Sleep -Seconds 15
    
    # Check status
    Write-Step "Verifying deployment..."
    $status = docker-compose ps
    Write-Host $status
    
    # Health checks
    Write-Step "Running health checks..."
    $ports = @(8000, 8001, 8002, 8003, 8004, 8005, 8006, 8007, 8008)
    $failed = @()
    
    foreach ($port in $ports) {
        try {
            $response = Invoke-RestMethod "http://localhost:$port/health" -TimeoutSec 5 -ErrorAction Stop
            if ($response.status -eq "healthy") {
                Write-Success "Port $port - healthy"
            } else {
                Write-Info "Port $port - $($response.status)"
            }
        } catch {
            $failed += $port
            Write-Error-Custom "Port $port - DOWN"
        }
    }
    
    if ($failed.Count -eq 0) {
        Write-Host "`n✨ Deployment successful!" -ForegroundColor Green
        Write-Info "All services are healthy"
        Write-Info "View logs: docker-compose logs -f"
        Write-Info "Stop services: docker-compose down"
    } else {
        Write-Host "`n⚠️  Some services failed health checks" -ForegroundColor Yellow
        Write-Info "Failed ports: $($failed -join ', ')"
        Write-Info "Check logs: docker-compose logs <service-name>"
    }
    
    Set-Location ..
}

# Remote Deployment
if ($Target -eq 'remote') {
    Write-Step "Deploying to remote droplet..."
    
    $DROPLET_IP = "45.55.173.72"
    $DROPLET_USER = "root"
    $DEPLOY_PATH = "/opt/Dev-Tools"
    
    Write-Info "Target: $DROPLET_USER@$DROPLET_IP $DEPLOY_PATH"
    
    # Check SSH access
    Write-Info "Testing SSH connection..."
    $test = ssh -o ConnectTimeout=5 "$DROPLET_USER@$DROPLET_IP" "echo OK" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Cannot connect to droplet!"
        Write-Info "Run: ssh $DROPLET_USER@$DROPLET_IP"
        exit 1
    }
    Write-Success "SSH connection OK"
    
    # Sync .env file
    Write-Info "Copying .env file to droplet..."
    scp "config/env/.env" "${DROPLET_USER}@${DROPLET_IP}:${DEPLOY_PATH}/config/env/.env"
    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Failed to copy .env file!"
        exit 1
    }
    Write-Success ".env file copied"
    
    # Sync secrets
    if (Test-Path "config/env/secrets") {
        Write-Info "Copying secrets to droplet..."
        ssh "$DROPLET_USER@$DROPLET_IP" "mkdir -p $DEPLOY_PATH/config/env/secrets"
        scp -r "config/env/secrets/*" "${DROPLET_USER}@${DROPLET_IP}:${DEPLOY_PATH}/config/env/secrets/"
        Write-Success "Secrets copied"
    }
    
    # Deploy on droplet
    Write-Info "Executing deployment on droplet..."
    
    # Execute commands directly via SSH (avoiding multiline script issues)
    ssh "$DROPLET_USER@$DROPLET_IP" "cd $DEPLOY_PATH && git pull origin main"
    ssh "$DROPLET_USER@$DROPLET_IP" "cd $DEPLOY_PATH/compose && docker compose build"
    ssh "$DROPLET_USER@$DROPLET_IP" "cd $DEPLOY_PATH/compose && docker compose up -d"
    ssh "$DROPLET_USER@$DROPLET_IP" "sleep 10 && cd $DEPLOY_PATH/compose && docker compose ps"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Remote deployment completed"
        Write-Info "Services accessible at:"
        Write-Info "  - Gateway: http://$DROPLET_IP:8000"
        Write-Info "  - Orchestrator: http://$DROPLET_IP:8001"
        Write-Info "  - Prometheus: http://$DROPLET_IP:9090"
    } else {
        Write-Error-Custom "Remote deployment failed!"
        Write-Info "Check droplet logs: ssh $DROPLET_USER@$DROPLET_IP"
        exit 1
    }
}

Write-Host "`n==========================================" -ForegroundColor Magenta
Write-Host "  🎉 Deployment Complete!" -ForegroundColor Magenta
Write-Host "==========================================" -ForegroundColor Magenta
Write-Host ""
