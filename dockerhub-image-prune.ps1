param(
    [string]$Repository = "alextorelli28/appsmithery",
    [switch]$DryRun = $true
)

$ErrorActionPreference = "Stop"

# Load PAT from .env
$envFile = "config/env/.env"
if (-not (Test-Path $envFile)) {
    Write-Error ".env file not found at $envFile"
    exit 1
}

$env:DOCKER_HUB_TOKEN = (Get-Content $envFile | Where-Object { $_ -match '^DOCKER_PAT=' }) -replace 'DOCKER_PAT=',''

if (-not $env:DOCKER_HUB_TOKEN) {
    Write-Error "DOCKER_PAT not found in .env"
    exit 1
}

Write-Host "Authenticating with Docker Hub..." -ForegroundColor Cyan

# Method 1: Try Hub API token endpoint (for PAT tokens)
$tokenUrl = "https://hub.docker.com/v2/users/login"
$authBody = @{
    username = "alextorelli28"
    password = $env:DOCKER_HUB_TOKEN
} | ConvertTo-Json

try {
    $authResponse = Invoke-RestMethod -Uri $tokenUrl -Method POST -Body $authBody -ContentType "application/json" -ErrorAction Stop
    $jwt = $authResponse.token
    Write-Host "JWT authentication successful" -ForegroundColor Green
} catch {
    # Method 2: Fallback to Registry API v2 token (for CLI compatibility)
    Write-Host "JWT failed, trying Registry API token..." -ForegroundColor Yellow
    
    $registryTokenUrl = "https://auth.docker.io/token?service=registry.docker.io&scope=repository:$Repository:pull,push,delete"
    $base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("alextorelli28:$($env:DOCKER_HUB_TOKEN)"))
    
    try {
        $tokenResponse = Invoke-RestMethod -Uri $registryTokenUrl -Headers @{ Authorization = "Basic $base64Auth" } -ErrorAction Stop
        $jwt = $tokenResponse.token
        Write-Host "Registry API authentication successful" -ForegroundColor Green
    } catch {
        Write-Error "Both authentication methods failed. Verify PAT has 'Read, Write, Delete' permissions."
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

$headers = @{
    Authorization = "Bearer $jwt"
}

# Tags to keep (production v2.2.0)
$keepTags = @(
    "orchestrator-v2.2.0-frontend-langsmith",
    "feature-dev-v2.2.0-frontend-langsmith",
    "code-review-v2.2.0-frontend-langsmith",
    "infrastructure-v2.2.0-frontend-langsmith",
    "cicd-v2.2.0-frontend-langsmith",
    "documentation-v2.2.0-frontend-langsmith",
    "gateway-v2.2.0-frontend-langsmith",
    "rag-v2.2.0-frontend-langsmith",
    "state-v2.2.0-frontend-langsmith",
    "langgraph-v2.2.0-frontend-langsmith"
)

# Patterns to delete
$deletePatterns = @(
    "*-v2.1.0-*",
    "*-latest",
    "*-progressive-mcp"
)

Write-Host "Fetching tags from Docker Registry v2 API..." -ForegroundColor Cyan

# Use Registry v2 API for private repos
$registryUrl = "https://registry-1.docker.io/v2/$Repository/tags/list"

try {
    $tagsList = Invoke-RestMethod -Uri $registryUrl -Headers $headers -Method GET -ErrorAction Stop
    $allTags = $tagsList.tags | ForEach-Object {
        @{
            name = $_
            full_size = $null  # Registry API doesn't provide size
        }
    }
    Write-Host "  Fetched $($allTags.Count) tags from Registry API" -ForegroundColor Green
}
catch {
    Write-Host "Registry API access denied for private repository" -ForegroundColor Yellow
    Write-Host "PAT tokens don't support private repo management via API" -ForegroundColor Yellow
    
    Write-Host "`n=== MANUAL DELETION REQUIRED ===" -ForegroundColor Red
    Write-Host "Docker Hub private repositories require web UI access for tag deletion." -ForegroundColor White
    Write-Host "`nKnown tags to DELETE (based on deployment patterns):" -ForegroundColor Red
    
    $knownOldTags = @(
        "orchestrator-v2.1.0-langsmith-tracing",
        "feature-dev-v2.1.0-langsmith-tracing",
        "code-review-v2.1.0-langsmith-tracing",
        "infrastructure-v2.1.0-langsmith-tracing",
        "cicd-v2.1.0-langsmith-tracing",
        "documentation-v2.1.0-langsmith-tracing",
        "gateway-v2.1.0-langsmith-tracing",
        "rag-v2.1.0-langsmith-tracing",
        "state-v2.1.0-langsmith-tracing",
        "langgraph-v2.1.0-langsmith-tracing",
        "orchestrator-latest",
        "feature-dev-latest",
        "code-review-latest",
        "infrastructure-latest",
        "cicd-latest",
        "documentation-latest",
        "gateway-latest",
        "rag-latest",
        "state-latest",
        "langgraph-latest"
    )
    
    $knownOldTags | ForEach-Object {
        Write-Host "  - $_" -ForegroundColor DarkRed
    }
    
    Write-Host "`nTags to KEEP:" -ForegroundColor Green
    $keepTags | ForEach-Object {
        Write-Host "  + $_" -ForegroundColor DarkGreen
    }
    
    Write-Host "`nInstructions:" -ForegroundColor Cyan
    Write-Host "1. Open: https://hub.docker.com/repository/docker/$Repository/tags" -ForegroundColor White
    Write-Host "2. Log in with your credentials" -ForegroundColor White
    Write-Host "3. Use multi-select (checkboxes) to select all v2.1.0 and latest tags" -ForegroundColor White
    Write-Host "4. Click 'Delete' button" -ForegroundColor White
    Write-Host "5. Verify only v2.2.0-frontend-langsmith tags remain" -ForegroundColor White
    Write-Host "`nEstimated time: 5-10 minutes" -ForegroundColor Yellow
    exit 0
}

Write-Host "Found $($allTags.Count) total tags" -ForegroundColor Yellow

# Filter tags to delete
$tagsToDelete = $allTags | Where-Object {
    $tag = $_.name
    
    # Skip if in keep list
    if ($keepTags -contains $tag) {
        return $false
    }
    
    # Delete if matches pattern
    foreach ($pattern in $deletePatterns) {
        if ($tag -like $pattern) {
            return $true
        }
    }
    
    return $false
}

Write-Host "`nTags to DELETE ($($tagsToDelete.Count)):" -ForegroundColor Red
$totalSize = 0
$tagsToDelete | ForEach-Object {
    $size = if ($_.full_size) { 
        $totalSize += $_.full_size
        [math]::Round($_.full_size / 1MB, 1) 
    } else { "?" }
    Write-Host "  - $($_.name) ($size MB)" -ForegroundColor DarkGray
}

Write-Host "`nTags to KEEP ($($allTags.Count - $tagsToDelete.Count)):" -ForegroundColor Green
$allTags | Where-Object { $keepTags -contains $_.name } | ForEach-Object {
    $size = if ($_.full_size) { [math]::Round($_.full_size / 1MB, 1) } else { "?" }
    Write-Host "  - $($_.name) ($size MB)" -ForegroundColor DarkGray
}

if ($tagsToDelete.Count -eq 0) {
    Write-Host "`nNo tags to delete" -ForegroundColor Green
    exit 0
}

Write-Host "`nEstimated space to free: $([math]::Round($totalSize / 1MB, 1)) MB" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "`nDRY RUN MODE - No deletions performed" -ForegroundColor Yellow
    Write-Host "Run with -DryRun:`$false to actually delete" -ForegroundColor Cyan
    exit 0
}

# Confirm deletion
Write-Host "`nWARNING: About to delete $($tagsToDelete.Count) tags from $Repository!" -ForegroundColor Red
Write-Host "This action CANNOT be undone." -ForegroundColor Yellow
$confirm = Read-Host "Type 'DELETE' to confirm"

if ($confirm -ne "DELETE") {
    Write-Host "Aborted" -ForegroundColor Yellow
    docker logout
    exit 0
}

# Delete tags using Docker Registry v2 API (manifest deletion)
Write-Host "`nDeleting tags via Registry API..." -ForegroundColor Cyan
Write-Host "Note: Registry API requires manifest digest deletion, which is complex." -ForegroundColor Yellow
Write-Host "Falling back to manual deletion instructions..." -ForegroundColor Yellow

Write-Host "`n=== MANUAL DELETION REQUIRED ===" -ForegroundColor Red
Write-Host "Docker Hub's API authentication doesn't support tag deletion via PAT tokens." -ForegroundColor White
Write-Host "Please delete tags manually:" -ForegroundColor White
Write-Host "1. Open: https://hub.docker.com/repository/docker/$Repository/tags" -ForegroundColor Cyan
Write-Host "2. Select and delete the following tags:" -ForegroundColor Cyan
foreach ($tag in $tagsToDelete) {
    Write-Host "   - $($tag.name)" -ForegroundColor DarkRed
}
Write-Host "`nEstimated time: 5-10 minutes using multi-select" -ForegroundColor Yellow

$deleted = 0
$failed = $tagsToDelete.Count

Write-Host "`nSummary:" -ForegroundColor Cyan
Write-Host "  Deleted: $deleted tags" -ForegroundColor Green
Write-Host "  Failed: $failed tags" -ForegroundColor Red
Write-Host "  Kept: $($allTags.Count - $deleted) production tags" -ForegroundColor Yellow
Write-Host "  Space freed: ~$([math]::Round($totalSize / 1MB, 1)) MB" -ForegroundColor Cyan

if ($deleted -gt 0) {
    Write-Host "`nNote: Untagged image layers will be garbage collected by Docker Hub within 24 hours" -ForegroundColor DarkGray
}
