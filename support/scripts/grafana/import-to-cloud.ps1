#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Import dashboard to Grafana Cloud
.DESCRIPTION
    Imports the LLM Token Metrics dashboard into Grafana Cloud (appsmithery.grafana.net).
    Uses Grafana Cloud API token for authentication.
.PARAMETER DashboardPath
    Path to dashboard JSON file (default: config/grafana/dashboards/llm-token-metrics.json)
.PARAMETER GrafanaUrl
    Grafana Cloud URL (default: https://appsmithery.grafana.net)
.PARAMETER ApiToken
    Grafana Cloud API token (from .env: GRAFANA_CLOUD_API_TOKEN)
.EXAMPLE
    .\import-to-cloud.ps1
.EXAMPLE
    .\import-to-cloud.ps1 -DashboardPath "config/grafana/dashboards/custom-dashboard.json"
#>

param(
    [string]$DashboardPath = "config/grafana/dashboards/llm-token-metrics.json",
    [string]$GrafanaUrl = "https://appsmithery.grafana.net",
    [string]$ApiToken = $env:GRAFANA_CLOUD_API_TOKEN
)

# Change to repo root
Set-Location "$PSScriptRoot\..\..\..\"

# Load .env if ApiToken not provided
if (-not $ApiToken) {
    Write-Host "Loading API token from .env..." -ForegroundColor Cyan
    $envPath = "config/env/.env"
    if (Test-Path $envPath) {
        Get-Content $envPath | ForEach-Object {
            if ($_ -match '^GRAFANA_CLOUD_API_TOKEN=(.+)$') {
                $ApiToken = $matches[1]
            }
        }
    }
}

if (-not $ApiToken) {
    Write-Error "GRAFANA_CLOUD_API_TOKEN not found. Set it in .env or pass via -ApiToken parameter"
    exit 1
}

# Verify dashboard file exists
if (!(Test-Path $DashboardPath)) {
    Write-Error "Dashboard file not found: $DashboardPath"
    exit 1
}

Write-Host "Reading dashboard from: $DashboardPath" -ForegroundColor Cyan

# Read dashboard JSON
$dashboardContent = Get-Content $DashboardPath -Raw | ConvertFrom-Json

# Wrap dashboard for import API (add metadata)
$importPayload = @{
    dashboard = $dashboardContent.dashboard
    overwrite = $true
    message = "Imported to Grafana Cloud $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    folderId = 0
} | ConvertTo-Json -Depth 100

# Create bearer auth header for Grafana Cloud
$headers = @{
    "Authorization" = "Bearer $ApiToken"
    "Content-Type" = "application/json"
}

Write-Host "Importing dashboard to Grafana Cloud..." -ForegroundColor Cyan
Write-Host "Target: $GrafanaUrl" -ForegroundColor Gray

try {
    # Import dashboard
    $response = Invoke-RestMethod `
        -Uri "$GrafanaUrl/api/dashboards/db" `
        -Method Post `
        -Headers $headers `
        -Body $importPayload `
        -ErrorAction Stop
    
    Write-Host "Dashboard imported successfully to Grafana Cloud!" -ForegroundColor Green
    Write-Host "   Dashboard ID: $($response.id)" -ForegroundColor Gray
    Write-Host "   Dashboard UID: $($response.uid)" -ForegroundColor Gray
    Write-Host "   Dashboard URL: $GrafanaUrl/d/$($response.uid)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Open dashboard: $GrafanaUrl/d/$($response.uid)" -ForegroundColor Cyan
    
    # Also configure datasources if needed
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Configure Prometheus datasource in Grafana Cloud" -ForegroundColor White
    Write-Host "   - URL: http://45.55.173.72:9090" -ForegroundColor Gray
    Write-Host "   - Or use Grafana Cloud Agent to scrape metrics" -ForegroundColor Gray
    Write-Host "2. Open dashboard and verify metrics are flowing" -ForegroundColor White
    
    exit 0
}
catch {
    Write-Error "Failed to import dashboard: $($_.Exception.Message)"
    if ($_.ErrorDetails) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "- Verify API token has write permissions" -ForegroundColor Gray
    Write-Host "- Check Grafana Cloud URL is correct" -ForegroundColor Gray
    Write-Host "- Ensure dashboard JSON is valid" -ForegroundColor Gray
    exit 1
}
