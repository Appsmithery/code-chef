param(
    [switch]$DryRun = $true,
    [string]$Repository = "alextorelli28/appsmithery"
)

$ErrorActionPreference = "Stop"

# Docker Hub credentials
$username = "alextorelli28"
$token = $env:DOCKER_HUB_TOKEN  # Set via: $env:DOCKER_HUB_TOKEN = "your-token"

if (-not $token) {
    Write-Error "DOCKER_HUB_TOKEN environment variable not set"
    exit 1
}

# Authenticate
$authBody = @{
    username = $username
    password = $token
} | ConvertTo-Json

$authResponse = Invoke-RestMethod -Uri "https://hub.docker.com/v2/users/login" -Method POST -Body $authBody -ContentType "application/json"
$jwtToken = $authResponse.token

$headers = @{
    Authorization = "Bearer $jwtToken"
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

Write-Host "🔍 Fetching all tags from $Repository..." -ForegroundColor Cyan

# Get all tags (paginated)
$allTags = @()
$nextUrl = "https://hub.docker.com/v2/repositories/$Repository/tags?page_size=100"

while ($nextUrl) {
    $response = Invoke-RestMethod -Uri $nextUrl -Headers $headers -Method GET
    $allTags += $response.results
    $nextUrl = $response.next
}

Write-Host "📊 Found $($allTags.Count) total tags" -ForegroundColor Yellow

# Filter tags to delete
$tagsToDelete = $allTags | Where-Object {
    $tag = $_.name
    
    # Keep if in keepTags list
    if ($keepTags -contains $tag) {
        return $false
    }
    
    # Delete if matches any delete pattern
    foreach ($pattern in $deletePatterns) {
        if ($tag -like $pattern) {
            return $true
        }
    }
    
    return $false
}

Write-Host "🗑️  Tags to delete: $($tagsToDelete.Count)" -ForegroundColor Red

# Show what will be deleted
$tagsToDelete | ForEach-Object {
    $size = if ($_.full_size) { [math]::Round($_.full_size / 1MB, 1) } else { "?" }
    Write-Host "  - $($_.name) ($size MB)" -ForegroundColor DarkGray
}

if ($tagsToDelete.Count -eq 0) {
    Write-Host "✅ No tags to delete" -ForegroundColor Green
    exit 0
}

if ($DryRun) {
    Write-Host "`n⚠️  DRY RUN MODE - No tags will be deleted" -ForegroundColor Yellow
    Write-Host "Run with -DryRun:`$false to actually delete" -ForegroundColor Yellow
    exit 0
}

# Confirm deletion
Write-Host "`n⚠️  WARNING: About to delete $($tagsToDelete.Count) tags!" -ForegroundColor Red
$confirm = Read-Host "Type 'DELETE' to confirm"

if ($confirm -ne "DELETE") {
    Write-Host "❌ Aborted" -ForegroundColor Yellow
    exit 0
}

# Delete tags
$deleted = 0
$failed = 0

foreach ($tag in $tagsToDelete) {
    try {
        $deleteUrl = "https://hub.docker.com/v2/repositories/$Repository/tags/$($tag.name)"
        Invoke-RestMethod -Uri $deleteUrl -Headers $headers -Method DELETE | Out-Null
        Write-Host "✅ Deleted: $($tag.name)" -ForegroundColor Green
        $deleted++
    } catch {
        Write-Host "❌ Failed: $($tag.name) - $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    }
    
    Start-Sleep -Milliseconds 100  # Rate limiting
}

Write-Host "`n📊 Summary:" -ForegroundColor Cyan
Write-Host "  ✅ Deleted: $deleted tags" -ForegroundColor Green
Write-Host "  ❌ Failed: $failed tags" -ForegroundColor Red
Write-Host "  📦 Kept: $($allTags.Count - $tagsToDelete.Count) tags" -ForegroundColor Yellow