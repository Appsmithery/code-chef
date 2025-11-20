#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Intelligent deployment script for Dev-Tools with config-vs-code detection

.DESCRIPTION
    Automatically detects whether changes are config-only or require rebuild:
    - Config changes (.env, .yaml): Fast down+up deployment (30s)
    - Code changes (.py, Dockerfile, requirements.txt): Full rebuild (10min)
    - Automatic health validation and rollback support

.PARAMETER DeployType
    'auto' (detect changes), 'config' (env only), 'full' (rebuild), 'quick' (restart)

.PARAMETER Registry
    Docker registry for images (default: DOCR)

.PARAMETER ImageTag
    Specific image tag (default: git SHA)

.PARAMETER SkipHealthCheck
    Skip post-deployment health validation

.PARAMETER Rollback
    Rollback to previous git commit and restart services
#>

param(
    [ValidateSet('auto', 'config', 'full', 'quick')]
    [string]$DeployType = 'auto',
    
    [string]$ImageTag,
    [string]$Registry = "registry.digitalocean.com/the-shop-infra",
    [switch]$SkipClean,
    [switch]$SkipTests,
    [switch]$SkipHealthCheck,
    [switch]$Rollback
)

$ErrorActionPreference = "Stop"
$DROPLET = "do-mcp-gateway"
$DEPLOY_PATH = "/opt/Dev-Tools"
$LOCAL_ENV_PATH = "config/env/.env"

function Write-Step { param($Message) Write-Host "`n[STEP] $Message" -ForegroundColor Cyan }
function Write-Info { param($Message) Write-Host "  -> $Message" -ForegroundColor Gray }
function Write-Success { param($Message) Write-Host "  [OK] $Message" -ForegroundColor Green }
function Write-Failure { param($Message) Write-Host "  [ERROR] $Message" -ForegroundColor Red }

function Get-ChangedFiles {
    Write-Info "Detecting local changes..."
    
    # Get uncommitted changes
    $gitStatus = git status --porcelain 2>$null
    $uncommitted = git diff --name-only 2>$null
    
    $allChanges = @()
    if ($gitStatus) { $allChanges += ($gitStatus | ForEach-Object { $_ -replace '^\s*[MAD]\s+', '' }) }
    if ($uncommitted) { $allChanges += ($uncommitted -split "`n") }
    
    return $allChanges | Where-Object { $_ -and $_.Trim() } | Select-Object -Unique
}

function Get-DeploymentStrategy {
    $changedFiles = Get-ChangedFiles
    
    if (-not $changedFiles) {
        Write-Info "No local changes detected - using quick restart"
        return "quick"
    }
    
    Write-Info "Changed files:"
    $changedFiles | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
    
    # Categorize changes
    $configChanges = $changedFiles | Where-Object { 
        $_ -match "^config/env/" -or $_ -match "\.env$" -or $_ -match "\.yaml$" -or $_ -match "\.yml$"
    }
    
    $codeChanges = $changedFiles | Where-Object {
        $_ -match "\.(py|ts|js|Dockerfile|txt)$" -or $_ -match "requirements\.txt" -or $_ -match "package\.json"
    }
    
    if ($codeChanges) {
        Write-Info "Code/dependency changes detected → FULL REBUILD required"
        return "full"
    } elseif ($configChanges) {
        Write-Info "Config-only changes detected → FAST deployment (down+up)"
        return "config"
    } else {
        Write-Info "Documentation/non-critical changes → QUICK restart"
        return "quick"
    }
}

function Deploy-ConfigOnly {
    Write-Step "Fast deployment: Config changes only"
    
    # Validate .env exists
    if (-not (Test-Path $LOCAL_ENV_PATH)) {
        Write-Failure "Local .env file not found: $LOCAL_ENV_PATH"
        return $false
    }
    
    # Copy .env to droplet
    Write-Info "Uploading config/env/.env..."
    scp -q "$LOCAL_ENV_PATH" "${DROPLET}:${DEPLOY_PATH}/config/env/.env"
    if ($LASTEXITCODE -ne 0) {
        Write-Failure "Failed to upload .env file"
        return $false
    }
    Write-Success ".env uploaded"
    
    # Pull latest code (for template updates)
    Write-Info "Pulling latest code on droplet..."
    ssh $DROPLET "cd $DEPLOY_PATH && git stash && git pull origin main"
    if ($LASTEXITCODE -ne 0) {
        Write-Failure "Git pull failed on droplet"
        return $false
    }
    Write-Success "Code updated"
    
    # CRITICAL: Must use down+up to reload environment variables
    Write-Info "Restarting services (down+up to reload .env)..."
    ssh $DROPLET "cd $DEPLOY_PATH/deploy && docker compose down && docker compose up -d"
    if ($LASTEXITCODE -ne 0) {
        Write-Failure "Service restart failed"
        return $false
    }
    Write-Success "Services restarted"
    
    return $true
}

function Deploy-FullRebuild {
    Write-Step "Full deployment: Code changes detected"
    
    # Ensure local changes are committed
    $uncommitted = git status --porcelain
    if ($uncommitted) {
        Write-Failure "You have uncommitted changes. Commit or stash them first."
        Write-Info "Run: git add . && git commit -m 'your message' && git push origin main"
        return $false
    }
    
    # Push to main
    Write-Info "Pushing to main branch..."
    git push origin main
    if ($LASTEXITCODE -ne 0) {
        Write-Failure "Failed to push to main branch"
        return $false
    }
    Write-Success "Code pushed"
    
    # Copy .env (not in git)
    if (Test-Path $LOCAL_ENV_PATH) {
        Write-Info "Uploading .env..."
        scp -q "$LOCAL_ENV_PATH" "${DROPLET}:${DEPLOY_PATH}/config/env/.env"
    }
    
    # Pull and rebuild on droplet
    Write-Info "Pulling code, rebuilding, and deploying..."
    ssh $DROPLET @"
cd $DEPLOY_PATH && \
git pull origin main && \
cd deploy && \
docker compose down --remove-orphans && \
docker compose build --no-cache && \
docker compose up -d
"@
    
    if ($LASTEXITCODE -ne 0) {
        Write-Failure "Rebuild and deployment failed"
        return $false
    }
    Write-Success "Full rebuild completed"
    
    return $true
}

function Deploy-QuickRestart {
    Write-Step "Quick restart: No critical changes"
    
    ssh $DROPLET "cd $DEPLOY_PATH/deploy && docker compose restart"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Services restarted"
        return $true
    } else {
        Write-Failure "Restart failed"
        return $false
    }
}

function Test-HealthEndpoints {
    Write-Step "Validating service health"
    
    Write-Info "Waiting 15 seconds for services to stabilize..."
    Start-Sleep -Seconds 15
    
    $endpoints = @(
        @{Port=8001; Name="Orchestrator"},
        @{Port=8002; Name="Feature-Dev"},
        @{Port=8003; Name="Code-Review"},
        @{Port=8004; Name="Infrastructure"},
        @{Port=8005; Name="CI/CD"},
        @{Port=8006; Name="Documentation"}
    )
    
    $healthyCount = 0
    foreach ($ep in $endpoints) {
        $health = ssh $DROPLET "curl -s http://localhost:$($ep.Port)/health 2>/dev/null"
        
        if ($health -match '"status"\s*:\s*"ok"') {
            Write-Host "  ✓ $($ep.Name) (port $($ep.Port))" -ForegroundColor Green
            $healthyCount++
        } else {
            Write-Host "  ✗ $($ep.Name) (port $($ep.Port))" -ForegroundColor Red
        }
    }
    
    Write-Host ""
    if ($healthyCount -eq $endpoints.Count) {
        Write-Success "All $healthyCount services healthy"
        return $true
    } else {
        Write-Failure "$($endpoints.Count - $healthyCount) service(s) unhealthy"
        return $false
    }
}

function Invoke-Rollback {
    Write-Step "Rolling back to previous commit"
    
    ssh $DROPLET @"
cd $DEPLOY_PATH && \
git reset --hard HEAD~1 && \
cd deploy && \
docker compose down && \
docker compose up -d
"@
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Rollback completed"
        return $true
    } else {
        Write-Failure "Rollback failed"
        return $false
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Dev-Tools Intelligent Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Target: $DROPLET ($DEPLOY_PATH)" -ForegroundColor Gray
Write-Host ""

# Handle rollback
if ($Rollback) {
    if (Invoke-Rollback) {
        exit 0
    } else {
        exit 1
    }
}

# Test SSH connection
Write-Step "Testing SSH connection"
ssh -o ConnectTimeout=5 $DROPLET "echo 'Connected'" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Failure "SSH connection failed"
    exit 1
}
Write-Success "SSH connection working"

# Determine deployment strategy
$strategy = if ($DeployType -eq 'auto') {
    Get-DeploymentStrategy
} else {
    Write-Info "Using explicit strategy: $DeployType"
    $DeployType
}

Write-Host ""
Write-Host "Deployment Strategy: $strategy" -ForegroundColor Yellow -BackgroundColor DarkBlue
Write-Host ""

# Execute deployment based on strategy
$deploySuccess = switch ($strategy) {
    'config' { Deploy-ConfigOnly }
    'full'   { Deploy-FullRebuild }
    'quick'  { Deploy-QuickRestart }
    default  {
        Write-Failure "Unknown strategy: $strategy"
        $false
    }
}

if (-not $deploySuccess) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "Deployment Failed" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Rollback: .\deploy-to-droplet.ps1 -Rollback" -ForegroundColor Yellow
    Write-Host "Logs: ssh $DROPLET 'cd $DEPLOY_PATH/deploy && docker compose logs --tail=100'" -ForegroundColor Yellow
    exit 1
}

# Health checks (unless skipped)
if (-not $SkipHealthCheck) {
    $healthy = Test-HealthEndpoints
    
    if (-not $healthy) {
        Write-Host ""
        Write-Failure "Some services are unhealthy"
        Write-Info "Rollback: .\deploy-to-droplet.ps1 -Rollback"
        Write-Info "Logs: ssh $DROPLET 'cd $DEPLOY_PATH/deploy && docker compose logs --tail=100'"
        exit 1
    }
}

# Optional validation tests
if (-not $SkipTests -and $strategy -in @('full', 'config')) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Running Validation Tests" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    if (Test-Path "support/scripts/validation/validate-tracing.sh") {
        Write-Step "Running validate-tracing.sh on droplet"
        scp -q support/scripts/validation/validate-tracing.sh ${DROPLET}:/tmp/validate-tracing.sh
        ssh $DROPLET "chmod +x /tmp/validate-tracing.sh && /tmp/validate-tracing.sh"
        
        if ($LASTEXITCODE -ne 0) {
            Write-Failure "Validation tests failed (non-blocking)"
        } else {
            Write-Success "Validation tests passed"
        }
    } else {
        Write-Info "Validation script not found - skipping"
    }
}

# Success summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Strategy: $strategy" -ForegroundColor Cyan
Write-Host "Droplet: $DROPLET_IP ($DEPLOY_PATH)" -ForegroundColor Cyan
Write-Host ""

Write-Host "Quick Checks:" -ForegroundColor Yellow
Write-Host "  • LangSmith Traces: https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects/p/f967bb5e-2e61-434f-8ee1-0df8c22bc046" -ForegroundColor Cyan
Write-Host "  • Test Orchestrator: ssh $DROPLET 'curl -X POST http://localhost:8001/orchestrate -H Content-Type:application/json -d \"{\\\"description\\\":\\\"test\\\",\\\"priority\\\":\\\"high\\\"}\"'" -ForegroundColor Gray
Write-Host "  • View Logs: ssh $DROPLET 'cd $DEPLOY_PATH/deploy && docker compose logs -f orchestrator'" -ForegroundColor Gray
Write-Host ""

if ($strategy -eq 'config') {
    Write-Host "Config Deployment Notes:" -ForegroundColor Yellow
    Write-Host "  ✓ Environment variables reloaded (down+up cycle)" -ForegroundColor Green
    Write-Host "  ✓ No rebuild required (30s deployment)" -ForegroundColor Green
    Write-Host ""
}

exit 0
