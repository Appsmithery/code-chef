#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy Dev-Tools Hybrid Architecture (Gradient AI Agents + Docker Infrastructure)

.DESCRIPTION
    This script deploys the hybrid architecture where:
    - Agent services run as Gradient AI managed services (.agents.do-ai.run)
    - Infrastructure services run in Docker on the droplet (gateway, rag, state, databases)

.PARAMETER Target
    Deployment target: 'local' or 'remote' (default: remote)

.PARAMETER SkipBuild
    Skip building Docker images (default: false)

.EXAMPLE
    .\scripts\deploy-hybrid.ps1
    .\scripts\deploy-hybrid.ps1 -Target local -SkipBuild
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('local', 'remote')]
    [string]$Target = 'remote',
    
    [Parameter(Mandatory=$false)]
    [switch]$SkipBuild = $false
)

$ErrorActionPreference = "Stop"

# Configuration
$DROPLET_IP = "45.55.173.72"
$DROPLET_USER = "root"
$DEPLOY_PATH = "/opt/Dev-Tools"
$GRADIENT_AGENTS = @(
    @{Name="DevTools Orchestrator"; URL="https://zqavbvjov22wijsmbqtkqy4r.agents.do-ai.run"},
    @{Name="Feature Development Agent"; URL="https://mdu2tzvveslhs6spm36znwul.agents.do-ai.run"},
    @{Name="Code Review Agent"; URL="https://miml4tgrdvjufzudn5udh2sp.agents.do-ai.run"},
    @{Name="Infrastructure Agent"; URL="https://r2eqzfrjao62mdzdbtolmq3sa.agents.do-ai.run"},
    @{Name="CI/CD Agent"; URL="https://dxoc7qrjjgbvj7ybct7nogbp.agents.do-ai.run"},
    @{Name="Documentation Agent"; URL="https://tzyvehgqf3pgl4z46rrzbbs.agents.do-ai.run"}
)
$DOCKER_SERVICES = @("gateway-mcp", "rag-context", "state-persistence", "qdrant", "postgres", "prometheus")

Write-Host "`n🚀 Dev-Tools Hybrid Deployment" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Target: $Target" -ForegroundColor Yellow
Write-Host "Droplet: $DROPLET_IP" -ForegroundColor Yellow
Write-Host "`n"

# Step 1: Validate environment
Write-Host "📋 Step 1: Validating environment..." -ForegroundColor Green
if (-not (Test-Path "config/env/.env")) {
    Write-Error "❌ config/env/.env not found. Copy from .env.template and configure."
    exit 1
}

# Check for required environment variables
$envContent = Get-Content "config/env/.env" -Raw
$requiredVars = @(
    "GRADIENT_MODEL_ACCESS_KEY",
    "GRADIENT_API_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "QDRANT_CLOUD_API_KEY",
    "DIGITAL_OCEAN_PAT"
)

foreach ($var in $requiredVars) {
    if ($envContent -notmatch "$var=.+") {
        Write-Error "❌ Required environment variable $var is missing or empty in .env"
        exit 1
    }
}
Write-Host "✅ Environment validated" -ForegroundColor Green

# Step 2: Verify Gradient AI Agents
Write-Host "`n🤖 Step 2: Verifying Gradient AI agents..." -ForegroundColor Green
$agentStatus = @()
foreach ($agent in $GRADIENT_AGENTS) {
    try {
        $response = Invoke-RestMethod -Uri "$($agent.URL)/health" -Method Get -TimeoutSec 10 -ErrorAction Stop
        $status = "✅ Online"
        $agentStatus += @{Name=$agent.Name; Status=$status; URL=$agent.URL}
        Write-Host "  $status - $($agent.Name)" -ForegroundColor Green
    } catch {
        $status = "⚠️  Offline/Unreachable"
        $agentStatus += @{Name=$agent.Name; Status=$status; URL=$agent.URL}
        Write-Host "  $status - $($agent.Name)" -ForegroundColor Yellow
    }
}

# Step 3: Build Docker images (infrastructure only)
if (-not $SkipBuild) {
    Write-Host "`n🔨 Step 3: Building Docker infrastructure images..." -ForegroundColor Green
    $imagesToBuild = @("gateway-mcp", "rag-context", "state-persistence")
    
    foreach ($service in $imagesToBuild) {
        Write-Host "  Building $service..." -ForegroundColor Cyan
        docker compose -f compose/docker-compose.yml build $service
        if ($LASTEXITCODE -ne 0) {
            Write-Error "❌ Failed to build $service"
            exit 1
        }
    }
    Write-Host "✅ Images built successfully" -ForegroundColor Green
}
else {
    Write-Host "`n⏭️  Step 3: Skipping image build (--SkipBuild flag set)" -ForegroundColor Yellow
}

# Step 4: Deploy to target
if ($Target -eq "remote") {
    Write-Host "`n🌐 Step 4: Deploying to remote droplet ($DROPLET_IP)..." -ForegroundColor Green
    
    # Test SSH connectivity
    Write-Host "  Testing SSH connection..." -ForegroundColor Cyan
    $sshTest = ssh -o ConnectTimeout=5 -o BatchMode=yes $DROPLET_USER@$DROPLET_IP "echo 'Connection successful'" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Cannot connect to droplet. Ensure SSH keys are configured."
        exit 1
    }
    Write-Host "  ✅ SSH connection verified" -ForegroundColor Green
    
    # Sync code to droplet
    Write-Host "  Syncing code to droplet..." -ForegroundColor Cyan
    ssh $DROPLET_USER@$DROPLET_IP "cd $DEPLOY_PATH && git pull origin main"
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "⚠️  Git pull failed. Ensure droplet has git repo initialized."
    }
    
    # Copy .env file
    Write-Host "  Copying .env file..." -ForegroundColor Cyan
    scp config/env/.env ${DROPLET_USER}@${DROPLET_IP}:${DEPLOY_PATH}/config/env/.env
    
    # Deploy Docker services
    Write-Host "  Starting Docker infrastructure services..." -ForegroundColor Cyan
    $servicesList = $DOCKER_SERVICES -join " "
    ssh $DROPLET_USER@$DROPLET_IP @"
cd $DEPLOY_PATH
docker compose -f compose/docker-compose.yml pull $servicesList
docker compose -f compose/docker-compose.yml up -d $servicesList
"@
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Failed to start Docker services on droplet"
        exit 1
    }
    
    Write-Host "  ✅ Docker services started" -ForegroundColor Green
    
    # Wait for services to be ready
    Write-Host "  Waiting for services to be ready (15s)..." -ForegroundColor Cyan
    Start-Sleep -Seconds 15
    
    # Verify gateway health
    Write-Host "`n🏥 Step 5: Verifying deployment health..." -ForegroundColor Green
    try {
        $gatewayHealth = Invoke-RestMethod -Uri "http://${DROPLET_IP}:8000/health" -Method Get -TimeoutSec 10
        Write-Host "  ✅ Gateway: $($gatewayHealth.status)" -ForegroundColor Green
        Write-Host "     Version: $($gatewayHealth.version)" -ForegroundColor Gray
        Write-Host "     MCP Servers: $($gatewayHealth.mcp_servers_count)" -ForegroundColor Gray
    } catch {
        Write-Warning "⚠️  Gateway health check failed: $_"
    }
}
else {
    # Local deployment
    Write-Host "`n💻 Step 4: Deploying locally..." -ForegroundColor Green
    $servicesList = $DOCKER_SERVICES -join " "
    docker compose -f compose/docker-compose.yml up -d $servicesList
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "❌ Failed to start local Docker services"
        exit 1
    }
    
    Write-Host "  Waiting for services to be ready (15s)..." -ForegroundColor Cyan
    Start-Sleep -Seconds 15
    
    # Verify local gateway
    Write-Host "`n🏥 Step 5: Verifying deployment health..." -ForegroundColor Green
    try {
        $gatewayHealth = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 10
        Write-Host "  ✅ Gateway: $($gatewayHealth.status)" -ForegroundColor Green
    } catch {
        Write-Warning "⚠️  Gateway health check failed: $_"
    }
}

# Summary
Write-Host "`n" -NoNewline
Write-Host "✅ Deployment Complete!" -ForegroundColor Green
Write-Host "========================" -ForegroundColor Green
Write-Host "`nArchitecture Overview:" -ForegroundColor Cyan
Write-Host "  🤖 Gradient AI Agents (Managed):" -ForegroundColor Yellow
foreach ($agent in $agentStatus) {
    Write-Host "     $($agent.Status) $($agent.Name)" -ForegroundColor Gray
    Write-Host "        $($agent.URL)" -ForegroundColor DarkGray
}

Write-Host "`n  🐳 Docker Infrastructure (Droplet $DROPLET_IP):" -ForegroundColor Yellow
foreach ($service in $DOCKER_SERVICES) {
    Write-Host "     • $service" -ForegroundColor Gray
}

Write-Host "`nNext Steps:" -ForegroundColor Cyan
Write-Host "  1. Configure Gradient AI agents to use gateway: http://${DROPLET_IP}:8000" -ForegroundColor White
Write-Host "  2. Test agent endpoints by calling .agents.do-ai.run URLs" -ForegroundColor White
Write-Host "  3. Monitor with Prometheus: http://${DROPLET_IP}:9090" -ForegroundColor White
Write-Host "  4. View traces in Langfuse: https://us.cloud.langfuse.com" -ForegroundColor White
Write-Host "`n"
