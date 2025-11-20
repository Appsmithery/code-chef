# Quick Linear Connection Test
# Tests connectivity to Linear workspace and project

param(
    [switch]$Remote,
    [string]$ProjectId = "78b3b839d36b"
)

$orchestratorUrl = if ($Remote) { "http://45.55.173.72:8001" } else { "http://localhost:8001" }

Write-Host ""
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Linear Integration Status Check" -ForegroundColor White
Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check orchestrator
Write-Host "[1/3] Checking orchestrator..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$orchestratorUrl/health" -Method Get -ErrorAction Stop
    Write-Host "  ✓ Orchestrator is running" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Cannot reach orchestrator at $orchestratorUrl" -ForegroundColor Red
    Write-Host "  Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Fix: Start the stack with 'cd deploy && docker compose up -d'" -ForegroundColor Yellow
    exit 1
}

# Step 2: Check Linear integration
Write-Host "[2/3] Checking Linear integration..." -ForegroundColor Yellow
if ($health.integrations.linear) {
    Write-Host "  ✓ Linear integration is ENABLED" -ForegroundColor Green
} else {
    Write-Host "  ✗ Linear integration is DISABLED" -ForegroundColor Red
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Red
    Write-Host "  Action Required: Configure Linear API Key" -ForegroundColor White
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Red
    Write-Host ""
    Write-Host "1. Get your API key:" -ForegroundColor Cyan
    Write-Host "   https://linear.app/vibecoding-roadmap/settings/api" -ForegroundColor White
    Write-Host ""
    Write-Host "2. Add to config/env/.env:" -ForegroundColor Cyan
    Write-Host "   LINEAR_API_KEY=lin_api_your_key_here" -ForegroundColor White
    Write-Host ""
    Write-Host "3. Restart orchestrator:" -ForegroundColor Cyan
    Write-Host "   cd deploy && docker compose restart orchestrator" -ForegroundColor White
    Write-Host ""
    exit 1
}

# Step 3: Test project access
Write-Host "[3/3] Testing project access..." -ForegroundColor Yellow
try {
    $roadmap = Invoke-RestMethod -Uri "$orchestratorUrl/linear/project/$ProjectId" -Method Get -ErrorAction Stop
    Write-Host "  ✓ Successfully connected to project!" -ForegroundColor Green
    Write-Host ""
    
    $project = $roadmap.roadmap.project
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  Project Details" -ForegroundColor White
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Name:        $($project.name)" -ForegroundColor White
    Write-Host "  State:       $($project.state)" -ForegroundColor Yellow
    Write-Host "  Progress:    $($project.progress)%" -ForegroundColor Yellow
    Write-Host "  Issues:      $($roadmap.roadmap.issues.Count)" -ForegroundColor White
    Write-Host ""
    
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  ✓ Linear Integration Working!" -ForegroundColor White
    Write-Host "═══════════════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  • View full roadmap: .\support\scripts\connect-linear-project.ps1" -ForegroundColor White
    Write-Host "  • API docs: See support/docs/LINEAR_SETUP.md" -ForegroundColor White
    Write-Host ""
    
} catch {
    Write-Host "  ✗ Failed to access project" -ForegroundColor Red
    
    if ($_.Exception.Response.StatusCode.value__ -eq 503) {
        Write-Host ""
        Write-Host "  The LINEAR_API_KEY is not configured or invalid." -ForegroundColor Yellow
    } elseif ($_.Exception.Response.StatusCode.value__ -eq 404) {
        Write-Host ""
        Write-Host "  Project not found. Verify project ID: $ProjectId" -ForegroundColor Yellow
    } else {
        Write-Host ""
        Write-Host "  Error: $_" -ForegroundColor Red
    }
    
    Write-Host ""
    exit 1
}
