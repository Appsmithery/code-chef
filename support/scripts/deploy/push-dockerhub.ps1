<#
.SYNOPSIS
    Build and push Dev-Tools images to Docker Hub
#>
param(
    [string]$Services = "all",
    [string]$ImageTag = "",
    [bool]$CleanupOnFailure = $true
)

$ErrorActionPreference = "Stop"

if (-not $ImageTag) {
    try {
        $ImageTag = (git rev-parse --short HEAD).Trim()
    } catch {
        $ImageTag = "latest"
    }
}

Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting Docker Hub push: tag=$ImageTag" -ForegroundColor Cyan

# Check Docker Hub auth
$dockerConfig = "$env:USERPROFILE\.docker\config.json"
if (-not (Test-Path $dockerConfig)) {
    Write-Host "[ERROR] Docker config not found. Run: docker login" -ForegroundColor Red
    exit 1
}

$config = Get-Content $dockerConfig | ConvertFrom-Json
if (-not $config.auths.'https://index.docker.io/v1/') {
    Write-Host "[ERROR] Not logged into Docker Hub. Run: docker login" -ForegroundColor Red
    exit 1
}

# Get username from .env
$envFile = "$PSScriptRoot\..\config\env\.env"
$username = "alextorelli28"
if (Test-Path $envFile) {
    $env:CONTENT = Get-Content $envFile -Raw
    if ($env:CONTENT -match "DOCKER_USERNAME=(\S+)") {
        $username = $matches[1]
    }
}

Write-Host "[OK] Docker Hub authenticated as: $username" -ForegroundColor Green

# Build and push
$composeDir = "$PSScriptRoot\..\compose"
Push-Location $composeDir

try {
    $env:IMAGE_TAG = $ImageTag
    $env:DOCKER_USERNAME = $username

    Write-Host "`nBuilding services..." -ForegroundColor Yellow
    if ($Services -eq "all") {
        docker compose build
    } else {
        $serviceList = $Services.Split(",") | ForEach-Object { $_.Trim() }
        docker compose build $serviceList
    }

    if ($LASTEXITCODE -ne 0) { throw "Build failed" }
    Write-Host "[OK] Build complete" -ForegroundColor Green

    Write-Host "`nPushing to Docker Hub..." -ForegroundColor Yellow
    if ($Services -eq "all") {
        docker compose push
    } else {
        docker compose push $serviceList
    }

    if ($LASTEXITCODE -ne 0) { throw "Push failed" }
    
    Write-Host "`n[SUCCESS] Push successful!" -ForegroundColor Green
    Write-Host "Images: $username/dev-tools-*:$ImageTag" -ForegroundColor Cyan

} catch {
    Write-Host "`n[ERROR] Failed: $_" -ForegroundColor Red
    if ($CleanupOnFailure) {
        docker builder prune -f | Out-Null
        docker image prune -f | Out-Null
    }
    exit 1
} finally {
    Pop-Location
    docker builder prune -f | Out-Null
}
