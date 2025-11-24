#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Import Grafana dashboard via API
.DESCRIPTION
    Imports the LLM Token Metrics dashboard into Grafana on the production droplet.
    Uses Grafana HTTP API with basic authentication.
.PARAMETER DashboardPath
    Path to dashboard JSON file (default: config/grafana/dashboards/llm-token-metrics.json)
.PARAMETER GrafanaUrl
    Grafana URL (default: http://45.55.173.72:3000)
.PARAMETER AdminUser
    Admin username (default: admin)
.PARAMETER AdminPassword
    Admin password (default: devtools_grafana_2024)
.EXAMPLE
    .\import-dashboard.ps1
.EXAMPLE
    .\import-dashboard.ps1 -DashboardPath "config/grafana/dashboards/custom-dashboard.json"
#>

param(
    [string]$DashboardPath = "config/grafana/dashboards/llm-token-metrics.json",
    [string]$GrafanaUrl = "http://45.55.173.72:3000",
    [string]$AdminUser = "admin",
    [string]$AdminPassword = "devtools_grafana_2024"
)

# Change to repo root
Set-Location "$PSScriptRoot\..\..\..\"

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
    message = "Imported via PowerShell script $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    folderId = 0
} | ConvertTo-Json -Depth 100

# Create basic auth header
$base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${AdminUser}:${AdminPassword}"))
$headers = @{
    "Authorization" = "Basic $base64Auth"
    "Content-Type" = "application/json"
}

Write-Host "Importing dashboard to Grafana..." -ForegroundColor Cyan

try {
    # Import dashboard
    $response = Invoke-RestMethod `
        -Uri "$GrafanaUrl/api/dashboards/db" `
        -Method Post `
        -Headers $headers `
        -Body $importPayload `
        -ErrorAction Stop
    
    Write-Host "Dashboard imported successfully!" -ForegroundColor Green
    Write-Host "   Dashboard ID: $($response.id)" -ForegroundColor Gray
    Write-Host "   Dashboard UID: $($response.uid)" -ForegroundColor Gray
    Write-Host "   Dashboard URL: $GrafanaUrl/d/$($response.uid)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Open dashboard: $GrafanaUrl/d/$($response.uid)" -ForegroundColor Cyan
    
    exit 0
}
catch {
    Write-Error "Failed to import dashboard: $($_.Exception.Message)"
    if ($_.ErrorDetails) {
        Write-Error "Response details available"
    }
    exit 1
}
