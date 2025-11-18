#!/usr/bin/env pwsh
# Deploy DOCR Images to DigitalOcean Droplet
# Pulls pre-built images from registry and deploys with health validation

param(
    [string]$ImageTag,
    [string]$Registry = "registry.digitalocean.com/the-shop-infra",
    [switch]$SkipClean,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$DROPLET = "do-mcp-gateway"
$DEPLOY_PATH = "/opt/Dev-Tools"

function Write-Step { param($Message) Write-Host "`n[STEP] $Message" -ForegroundColor Cyan }
function Write-Info { param($Message) Write-Host "  -> $Message" -ForegroundColor Gray }
function Write-Success { param($Message) Write-Host "  [OK] $Message" -ForegroundColor Green }
function Write-Failure { param($Message) Write-Host "  [ERROR] $Message" -ForegroundColor Red }

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deploy to Droplet (Image Pull Mode)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Derive IMAGE_TAG from git if not provided
if (-not $ImageTag) {
    Write-Info "Deriving IMAGE_TAG from current git commit..."
    $gitSha = (git rev-parse --short HEAD).Trim()
    if (-not $gitSha) {
        Write-Failure "Unable to determine git SHA; pass -ImageTag explicitly."
        exit 1
    }
    $ImageTag = $gitSha
}

Write-Info "Using IMAGE_TAG = $ImageTag"
Write-Info "Using Registry = $Registry"

# Test SSH connection
Write-Step "Testing SSH connection"
ssh -o ConnectTimeout=5 $DROPLET "echo 'Connected successfully'" | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Failure "SSH connection failed"
    exit 1
}
Write-Success "SSH connection working"

# Pull latest code
Write-Step "Pulling latest code on droplet"
ssh $DROPLET "cd $DEPLOY_PATH && git pull origin main"
if ($LASTEXITCODE -ne 0) {
    Write-Failure "Git pull failed"
    exit 1
}
Write-Success "Code updated"

try {
    # Stop and remove old containers
    Write-Step "Stopping containers and removing orphans"
    ssh $DROPLET "export DOCKER_HOST=unix:///var/run/docker.sock ; cd $DEPLOY_PATH/deploy ; docker compose down --remove-orphans"
    if ($LASTEXITCODE -ne 0) {
        Write-Failure "docker compose down failed"
        throw "Compose down failed"
    }
    Write-Success "Containers stopped"

    if (-not $SkipClean) {
        Write-Step "Pruning old images and containers"
        ssh $DROPLET "export DOCKER_HOST=unix:///var/run/docker.sock ; docker container prune -f ; docker image prune -f"
        Write-Success "Cleanup complete"
    }

    # Pull images from registry
    Write-Step "Pulling images from $Registry (tag: $ImageTag)"
    ssh $DROPLET "export DOCKER_HOST=unix:///var/run/docker.sock ; export IMAGE_TAG=$ImageTag ; export DOCR_REGISTRY=$Registry ; cd $DEPLOY_PATH/deploy ; docker compose pull"
    if ($LASTEXITCODE -ne 0) {
        Write-Failure "docker compose pull failed"
        throw "Image pull failed"
    }
    Write-Success "Images pulled"

    # Start all services
    Write-Step "Starting all services"
    ssh $DROPLET "export DOCKER_HOST=unix:///var/run/docker.sock ; export IMAGE_TAG=$ImageTag ; export DOCR_REGISTRY=$Registry ; cd $DEPLOY_PATH/deploy ; docker compose up -d"
    if ($LASTEXITCODE -ne 0) {
        Write-Failure "Service start failed"
        throw "Compose up failed"
    }
    Write-Success "Services started"

    # Wait for services to be ready
    Write-Step "Waiting 15 seconds for services to initialize"
    Start-Sleep -Seconds 15

    # Health checks
    Write-Step "Running health checks"
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
        $result = ssh $DROPLET "export DOCKER_HOST=unix:///var/run/docker.sock ; curl -s -o /dev/null -w '%{http_code}' http://localhost:$($service.Port)/health" 2>$null
        if ($result -eq "200") {
            Write-Host "  $($service.Name) (port $($service.Port))" -ForegroundColor Green
            $healthyCount++
        } else {
            Write-Host "  $($service.Name) (port $($service.Port)) - HTTP $result" -ForegroundColor Red
        }
    }

    Write-Host ""
    Write-Host "$healthyCount/$($services.Count) services healthy" -ForegroundColor $(if ($healthyCount -eq $services.Count) { "Green" } else { "Yellow" })

    if ($healthyCount -lt $services.Count) {
        Write-Failure "Some services are unhealthy; streaming logs..."
        ssh $DROPLET "export DOCKER_HOST=unix:///var/run/docker.sock ; cd $DEPLOY_PATH/deploy ; docker compose logs --tail=50"
        throw "Health check failed for $($services.Count - $healthyCount) service(s)"
    }

} catch {
    Write-Failure $_
    Write-Step "Running emergency cleanup"
    ssh $DROPLET "export DOCKER_HOST=unix:///var/run/docker.sock ; docker system prune --volumes --force"
    exit 1
}

if (-not $SkipTests) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Running Validation Tests" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    # Run comprehensive validation script
    Write-Step "Running validate-tracing.sh on droplet"
    scp -q support/scripts/validate-tracing.sh ${DROPLET}:/tmp/validate-tracing.sh
    ssh $DROPLET "chmod +x /tmp/validate-tracing.sh ; /tmp/validate-tracing.sh"
    if ($LASTEXITCODE -ne 0) {
        Write-Failure "Validation script failed"
        exit 1
    }
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
Write-Host "   ssh $DROPLET 'cd $DEPLOY_PATH/deploy ; docker compose logs -f orchestrator'" -ForegroundColor Gray
Write-Host ""

Write-Host "5. Manual deployment commands (if script fails):" -ForegroundColor Yellow
Write-Host "   ssh $DROPLET" -ForegroundColor Gray
Write-Host "   cd /opt/Dev-Tools" -ForegroundColor Gray
Write-Host "   git pull origin main" -ForegroundColor Gray
Write-Host "   cd deploy" -ForegroundColor Gray
Write-Host "   docker compose pull" -ForegroundColor Gray
Write-Host "   docker compose up -d" -ForegroundColor Gray
Write-Host "   docker compose ps" -ForegroundColor Gray
Write-Host ""
