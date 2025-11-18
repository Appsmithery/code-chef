param(
    [string]$Repository = "alextorelli28/appsmithery",
    [switch]$DryRun = $true
)

$ErrorActionPreference = "Stop"

# Authenticate Docker CLI with PAT
Write-Host "Authenticating Docker CLI..." -ForegroundColor Cyan
$env:DOCKER_HUB_TOKEN | docker login -u alextorelli28 --password-stdin

if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker login failed"
    exit 1
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

Write-Host "Fetching tags from Docker Hub..." -ForegroundColor Cyan

# Use Docker Hub API v2 (doesn't require JWT, uses Basic Auth with PAT)
$base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("alextorelli28:$env:DOCKER_HUB_TOKEN"))
$headers = @{
    Authorization = "Basic $base64Auth"
}

$allTags = @()
$nextUrl = "https://hub.docker.com/v2/repositories/$Repository/tags?page_size=100"

while ($nextUrl) {
    try {
        $response = Invoke-RestMethod -Uri $nextUrl -Headers $headers -Method GET
        $allTags += $response.results
        $nextUrl = $response.next
    }
    catch {
        Write-Error "Failed to fetch tags: $($_.Exception.Message)"
        exit 1
    }
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

Write-Host "Found $($tagsToDelete.Count) tags to delete:" -ForegroundColor Red
$tagsToDelete | ForEach-Object {
    $size = if ($_.full_size) { [math]::Round($_.full_size / 1MB, 1) } else { "?" }
    Write-Host "  - $($_.name) ($size MB)" -ForegroundColor DarkGray
}

if ($tagsToDelete.Count -eq 0) {
    Write-Host "No tags to delete" -ForegroundColor Green
    docker logout
    exit 0
}

if ($DryRun) {
    Write-Host "`n⚠️  DRY RUN MODE - No deletions performed" -ForegroundColor Yellow
    Write-Host "Run with -DryRun:`$false to actually delete" -ForegroundColor Cyan
    docker logout
    exit 0
}

# Confirm deletion
Write-Host "`nWARNING: About to delete $($tagsToDelete.Count) tags from $Repository!" -ForegroundColor Red
Write-Host "This action cannot be undone." -ForegroundColor Yellow
$confirm = Read-Host "Type 'DELETE' to confirm"

if ($confirm -ne "DELETE") {
    Write-Host "Aborted" -ForegroundColor Yellow
    docker logout
    exit 0
}

# Delete tags using Docker Hub API v2
Write-Host "`nDeleting tags..." -ForegroundColor Cyan
$deleted = 0
$failed = 0

foreach ($tag in $tagsToDelete) {
    $tagName = $tag.name
    $deleteUrl = "https://hub.docker.com/v2/repositories/$Repository/tags/$tagName"
    
    try {
        Invoke-RestMethod -Uri $deleteUrl -Headers $headers -Method DELETE | Out-Null
        Write-Host "Deleted: $tagName" -ForegroundColor Green
        $deleted++
        Start-Sleep -Milliseconds 200  # Rate limiting
    }
    catch {
        Write-Host "Failed: $tagName - $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    }
}

docker logout

Write-Host "`nSummary:" -ForegroundColor Cyan
Write-Host "  Deleted: $deleted tags" -ForegroundColor Green
Write-Host "  Failed: $failed tags" -ForegroundColor Red
Write-Host "  Kept: $($allTags.Count - $deleted) tags" -ForegroundColor Yellow

if ($deleted -gt 0) {
    Write-Host "`nTip: Untagged image layers will be garbage collected by Docker Hub within 24 hours" -ForegroundColor Cyan
}
