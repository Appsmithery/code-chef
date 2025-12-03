# Connect to Linear Project - AI DevOps Agent Platform
# Project URL: https://linear.app/vibecoding-roadmap/project/ai-devops-agent-platform-78b3b839d36b

param(
    [string]$ProjectId = "78b3b839d36b",
    [string]$OrchestratorUrl = "http://localhost:8001",
    [switch]$Remote
)

if ($Remote) {
    $OrchestratorUrl = "https://codechef.appsmithery.co/api"
}

Write-Host "Connecting to Linear Project: AI DevOps Agent Platform" -ForegroundColor Cyan
Write-Host "Project ID: $ProjectId" -ForegroundColor Yellow
Write-Host "Orchestrator URL: $OrchestratorUrl" -ForegroundColor Yellow
Write-Host ""

# Check orchestrator health
Write-Host "Checking orchestrator health..." -ForegroundColor Gray
try {
    $health = Invoke-RestMethod -Uri "$OrchestratorUrl/health" -Method Get
    Write-Host "✓ Orchestrator is healthy" -ForegroundColor Green
    
    if ($health.integrations.linear) {
        Write-Host "✓ Linear integration is enabled" -ForegroundColor Green
    } else {
        Write-Host "✗ Linear integration is NOT enabled" -ForegroundColor Red
        Write-Host "  To enable: Set LINEAR_API_KEY in config/env/.env" -ForegroundColor Yellow
        Write-Host "  Get your API key from: https://linear.app/vibecoding-roadmap/settings/api" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "✗ Failed to connect to orchestrator: $_" -ForegroundColor Red
    exit 1
}

# Fetch project roadmap
Write-Host ""
Write-Host "Fetching project roadmap..." -ForegroundColor Gray
try {
    $roadmap = Invoke-RestMethod -Uri "$OrchestratorUrl/linear/project/$ProjectId" -Method Get
    
    $project = $roadmap.roadmap.project
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Project: $($project.name)" -ForegroundColor White
    Write-Host "State: $($project.state)" -ForegroundColor Yellow
    Write-Host "Progress: $($project.progress)%" -ForegroundColor Yellow
    Write-Host "Description: $($project.description)" -ForegroundColor Gray
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    $issues = $roadmap.roadmap.issues
    Write-Host "Issues ($($issues.Count) total):" -ForegroundColor Cyan
    Write-Host ""
    
    foreach ($issue in $issues) {
        $priorityEmoji = switch ($issue.priority) {
            1 { "🔴" }  # Urgent
            2 { "🟠" }  # High
            3 { "🟡" }  # Normal
            4 { "🟢" }  # Low
            default { "⚪" }  # None
        }
        
        $stateColor = switch ($issue.state) {
            "Todo" { "White" }
            "In Progress" { "Yellow" }
            "Done" { "Green" }
            "Canceled" { "DarkGray" }
            default { "Gray" }
        }
        
        Write-Host "  $priorityEmoji [$($issue.state)]" -NoNewline -ForegroundColor $stateColor
        Write-Host " $($issue.title)" -ForegroundColor White
        Write-Host "     $($issue.url)" -ForegroundColor DarkGray
        if ($issue.assignee) {
            Write-Host "     Assignee: $($issue.assignee)" -ForegroundColor Gray
        }
        Write-Host ""
    }
    
    # Export to JSON for further processing
    $outputPath = "support/reports/linear-project-$ProjectId-$(Get-Date -Format 'yyyyMMdd-HHmmss').json"
    $roadmap | ConvertTo-Json -Depth 10 | Out-File -FilePath $outputPath -Encoding utf8
    Write-Host "✓ Project data exported to: $outputPath" -ForegroundColor Green
    
} catch {
    Write-Host "✗ Failed to fetch project roadmap: $_" -ForegroundColor Red
    
    if ($_.Exception.Response.StatusCode -eq 503) {
        Write-Host ""
        Write-Host "Linear integration is not configured." -ForegroundColor Yellow
        Write-Host "Please add LINEAR_API_KEY to config/env/.env" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Steps to configure:" -ForegroundColor Cyan
        Write-Host "1. Go to https://linear.app/vibecoding-roadmap/settings/api" -ForegroundColor White
        Write-Host "2. Create a new Personal API Key" -ForegroundColor White
        Write-Host "3. Add to config/env/.env: LINEAR_API_KEY=lin_api_..." -ForegroundColor White
        Write-Host "4. Restart the orchestrator: docker compose restart orchestrator" -ForegroundColor White
    }
    
    exit 1
}

Write-Host ""
Write-Host "✓ Successfully connected to Linear project!" -ForegroundColor Green
