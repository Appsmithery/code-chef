<#
.SYNOPSIS
    Build and push Dev-Tools images to Docker Hub
.DESCRIPTION
    Validates Docker Hub authentication, builds all or specified services,
    pushes to Docker Hub, and emits metadata for CI/CD tracking.
.PARAMETER Services
    Comma-separated service names to build/push (default: all)
.PARAMETER ImageTag
    Tag for images (default: git SHA)
.PARAMETER CleanupOnFailure
    Prune layers if build/push fails (default: $true in CI)
.EXAMPLE
    .\push-dockerhub.ps1
    .\push-dockerhub.ps1 -Services "orchestrator,feature-dev"
    .\push-dockerhub.ps1 -ImageTag "v1.2.3" -CleanupOnFailure $false
#>
param(
    [string]$Services = "all",
    [string]$ImageTag = "",
    [bool]$CleanupOnFailure = $true
)

$ErrorActionPreference = "Stop"

# Resolve image tag
if (-not $ImageTag) {
    try {
        $ImageTag = (git rev-parse --short HEAD).Trim()
    } catch {
        Write-Host "⚠ Git not available, using 'latest' tag" -ForegroundColor Yellow
        $ImageTag = "latest"
    }
}

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "[$timestamp] Starting Docker Hub push: tag=$ImageTag" -ForegroundColor Cyan

# Validate Docker Hub auth
try {
    $dockerInfo = docker info --format json 2>&1 | ConvertFrom-Json
    $username = $dockerInfo.Username
    
    if (-not $username) {
        throw "Not logged into Docker Hub. Run: docker login"
    }
    Write-Host "✓ Docker Hub authenticated as: $username" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker Hub auth failed: $_" -ForegroundColor Red
    Write-Host "Run: docker login" -ForegroundColor Yellow
    exit 1
}

# Prepare environment
$composeDir = Join-Path $PSScriptRoot ".." "compose"
Push-Location $composeDir

try {
    # Set env vars for compose
    $env:IMAGE_TAG = $ImageTag
    $env:DOCKER_USERNAME = $username

    Write-Host "`n[$timestamp] Environment:" -ForegroundColor Cyan
    Write-Host "  DOCKER_USERNAME: $username" -ForegroundColor Gray
    Write-Host "  IMAGE_TAG: $ImageTag" -ForegroundColor Gray
    Write-Host "  Working Directory: $composeDir" -ForegroundColor Gray

    # Build services
    Write-Host "`n[$timestamp] Building services..." -ForegroundColor Yellow
    if ($Services -eq "all") {
        docker compose build
    } else {
        $serviceList = $Services.Split(",") | ForEach-Object { $_.Trim() }
        docker compose build $serviceList
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Build failed with exit code $LASTEXITCODE"
    }
    Write-Host "✓ Build complete" -ForegroundColor Green

    # Push to Docker Hub
    Write-Host "`n[$timestamp] Pushing to Docker Hub..." -ForegroundColor Yellow
    if ($Services -eq "all") {
        docker compose push
    } else {
        $serviceList = $Services.Split(",") | ForEach-Object { $_.Trim() }
        docker compose push $serviceList
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Push failed with exit code $LASTEXITCODE"
    }
    Write-Host "✓ Push complete" -ForegroundColor Green

    # Emit metadata
    $reportsDir = Join-Path $PSScriptRoot ".." "reports"
    if (-not (Test-Path $reportsDir)) {
        New-Item -ItemType Directory -Path $reportsDir | Out-Null
    }

    $serviceNames = if ($Services -eq "all") { 
        @("gateway-mcp", "orchestrator", "feature-dev", "code-review", "infrastructure", "cicd", "documentation", "rag-context", "state-persistence", "langgraph")
    } else { 
        $Services.Split(",") | ForEach-Object { $_.Trim() }
    }

    $metadata = @{
        timestamp = $timestamp
        image_tag = $ImageTag
        username = $username
        services = $serviceNames
        images = $serviceNames | ForEach-Object { "$username/dev-tools-$_`:$ImageTag" }
    } | ConvertTo-Json -Depth 3

    $metadataFile = Join-Path $reportsDir "push-dockerhub-metadata.json"
    $metadata | Out-File $metadataFile -Encoding UTF8

    Write-Host "`n✓ Push successful!" -ForegroundColor Green
    Write-Host "Images published:" -ForegroundColor Cyan
    $serviceNames | ForEach-Object {
        Write-Host "  - $username/dev-tools-$_`:$ImageTag" -ForegroundColor Gray
    }
    Write-Host "`nMetadata: $metadataFile" -ForegroundColor Gray

} catch {
    Write-Host "`n✗ Push failed: $_" -ForegroundColor Red

    if ($CleanupOnFailure) {
        Write-Host "Cleaning up partial layers..." -ForegroundColor Yellow
        docker builder prune -f
        docker image prune -f
    }

    exit 1
} finally {
    Pop-Location
    
    # Always clean up builder cache
    Write-Host "`nCleaning builder cache..." -ForegroundColor Gray
    docker builder prune -f | Out-Null
}
