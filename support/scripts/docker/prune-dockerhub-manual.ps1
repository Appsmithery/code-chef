param(
    [string]$Repository = "alextorelli28/appsmithery",
    [switch]$Execute = $false
)

$ErrorActionPreference = "Stop"

Write-Host "`n=== Docker Hub Tag Cleanup Tool ===" -ForegroundColor Cyan
Write-Host "Repository: $Repository`n" -ForegroundColor Yellow

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

# List of tags to delete manually (generated from previous exports)
# These match patterns: *-v2.1.0-*, *-latest, *-progressive-mcp
$tagsToDelete = @(
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

Write-Host "Tags to KEEP:" -ForegroundColor Green
$keepTags | ForEach-Object { Write-Host "  + $_" -ForegroundColor DarkGreen }

Write-Host "`nTags to DELETE:" -ForegroundColor Red
$tagsToDelete | ForEach-Object { Write-Host "  - $_" -ForegroundColor DarkRed }

Write-Host "`nTotal: Keep $($keepTags.Count) | Delete $($tagsToDelete.Count)" -ForegroundColor Yellow

if (-not $Execute) {
    Write-Host "`n[DRY RUN] No changes made" -ForegroundColor Cyan
    Write-Host "To execute deletion, visit: https://hub.docker.com/repository/docker/$Repository/tags" -ForegroundColor Yellow
    Write-Host "Or run this script with -Execute flag (requires manual Docker Hub UI access)" -ForegroundColor Yellow
    
    Write-Host "`nGenerated CLI commands for manual execution:" -ForegroundColor Cyan
    Write-Host "# Copy and paste these into Docker Hub UI or use browser automation" -ForegroundColor Gray
    $tagsToDelete | ForEach-Object {
        Write-Host "Delete tag: $_" -ForegroundColor DarkGray
    }
    
    exit 0
}

Write-Host "`n=== MANUAL DELETION INSTRUCTIONS ===" -ForegroundColor Yellow
Write-Host "Docker Hub API requires web authentication. Please:" -ForegroundColor White
Write-Host "1. Open: https://hub.docker.com/repository/docker/$Repository/tags" -ForegroundColor Cyan
Write-Host "2. Log in with your credentials" -ForegroundColor Cyan
Write-Host "3. Search and delete each tag listed above" -ForegroundColor Cyan
Write-Host "4. Verify only v2.2.0-frontend-langsmith tags remain" -ForegroundColor Cyan
Write-Host "`nEstimated time: 5-10 minutes for $($tagsToDelete.Count) tags`n" -ForegroundColor Yellow
