param(
    [string]$Repository = "alextorelli28/appsmithery",
    [bool]$DryRun = $true
)

$ErrorActionPreference = "Stop"

$username = $Repository.Split('/')[0]
$repoName = $Repository.Split('/')[1]
$token = $env:DOCKER_HUB_TOKEN

if (-not $token) {
    Write-Error "DOCKER_HUB_TOKEN environment variable not set"
    exit 1
}

# Authenticate with Personal Access Token
Write-Host "Authenticating with Docker Hub..." -ForegroundColor Cyan

# Step 1: Get bearer token using PAT
$authBody = @{
    username = $username
    password = $token
} | ConvertTo-Json

try {
    $authResponse = Invoke-RestMethod -Uri "https://hub.docker.com/v2/users/login" -Method POST -Body $authBody -ContentType "application/json"
    $bearerToken = $authResponse.token
}
catch {
    Write-Error "Authentication failed: $($_.Exception.Message)"
    exit 1
}

$headers = @{
    Authorization = "Bearer $bearerToken"
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
    "*-progressive-mcp",
    "sha256:*"
)

# Fetch all tags
Write-Host "Fetching tags for $Repository..." -ForegroundColor Cyan
$allTags = @()
$page = 1
$pageSize = 100

do {
    $url = "https://hub.docker.com/v2/repositories/$Repository/tags?page=$page&page_size=$pageSize"
    $response = Invoke-RestMethod -Uri $url -Method GET -Headers $headers
    $allTags += $response.results
    $page++
} while ($response.next)

Write-Host "Found $($allTags.Count) total tags" -ForegroundColor Green

# Filter tags to delete
$tagsToDelete = $allTags | Where-Object {
    $tag = $_.name
    
    # Keep protected tags
    if ($keepTags -contains $tag) {
        return $false
    }
    
    # Check if matches any delete pattern
    foreach ($pattern in $deletePatterns) {
        if ($tag -like $pattern) {
            return $true
        }
    }
    
    return $false
}

Write-Host "Found $($tagsToDelete.Count) tags to delete:" -ForegroundColor Yellow
$tagsToDelete | ForEach-Object { Write-Host "  - $($_.name)" -ForegroundColor Gray }

if ($DryRun) {
    Write-Host "`n[DRY RUN] No changes made" -ForegroundColor Cyan
    Write-Host "Run with -DryRun `$false to actually delete" -ForegroundColor Yellow
    exit 0
}

# Confirm deletion
Write-Host "`nWARNING: About to delete $($tagsToDelete.Count) tags!" -ForegroundColor Red
$confirm = Read-Host "Type DELETE to confirm"

if ($confirm -ne "DELETE") {
    Write-Host "Aborted" -ForegroundColor Yellow
    exit 0
}

# Delete tags
$deleted = 0
$failed = 0

foreach ($tag in $tagsToDelete) {
    $tagName = $tag.name
    $url = "https://hub.docker.com/v2/repositories/$Repository/tags/$tagName"
    
    try {
        Invoke-RestMethod -Uri $url -Method DELETE -Headers $headers | Out-Null
        Write-Host "Deleted: $tagName" -ForegroundColor Green
        $deleted++
    }
    catch {
        Write-Host "Failed: $tagName - $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    }
}

Write-Host "`nSummary:" -ForegroundColor Cyan
Write-Host "  Deleted: $deleted" -ForegroundColor Green
Write-Host "  Failed: $failed" -ForegroundColor Red
Write-Host "  Kept: $($keepTags.Count)" -ForegroundColor Yellow
