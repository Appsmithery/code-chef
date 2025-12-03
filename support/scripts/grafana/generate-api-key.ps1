#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Generate Grafana API key for MCP server
.DESCRIPTION
    Creates a Grafana API key (service account token) for MCP server integration.
    This key allows the MCP server to query Grafana dashboards and datasources.
.PARAMETER GrafanaUrl
    Grafana URL - now uses Grafana Cloud (default: https://appsmithery.grafana.net)
.PARAMETER AdminUser
    Admin username (default: admin)
.PARAMETER AdminPassword
    Admin password (default: devtools_grafana_2024)
.PARAMETER KeyName
    API key name (default: MCP Server Access)
.PARAMETER Role
    Service account role: Admin, Editor, or Viewer (default: Viewer)
.EXAMPLE
    .\generate-api-key.ps1
.EXAMPLE
    .\generate-api-key.ps1 -Role Editor
#>

param(
    [string]$GrafanaUrl = "https://appsmithery.grafana.net",
    [string]$AdminUser = "admin",
    [string]$AdminPassword = "devtools_grafana_2024",
    [string]$KeyName = "MCP Server Access",
    [ValidateSet("Admin", "Editor", "Viewer")]
    [string]$Role = "Viewer"
)

Write-Host "Generating Grafana API key for MCP server..." -ForegroundColor Cyan

# Create basic auth header
$base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("${AdminUser}:${AdminPassword}"))
$headers = @{
    "Authorization" = "Basic $base64Auth"
    "Content-Type" = "application/json"
}

# Create API key using legacy API keys endpoint (simpler than service accounts)
$payload = @{
    name = $KeyName
    role = $Role
    secondsToLive = 0  # No expiration
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod `
        -Uri "$GrafanaUrl/api/auth/keys" `
        -Method Post `
        -Headers $headers `
        -Body $payload `
        -ErrorAction Stop
    
    Write-Host "API key created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "=== GRAFANA API KEY ===" -ForegroundColor Yellow
    Write-Host $response.key -ForegroundColor Cyan
    Write-Host "======================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Add this to config/env/.env:" -ForegroundColor White
    Write-Host "GRAFANA_API_KEY=$($response.key)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "API Key ID: $($response.id)" -ForegroundColor Gray
    Write-Host "API Key Name: $($response.name)" -ForegroundColor Gray
    
    exit 0
}
catch {
    Write-Error "Failed to create API key: $($_.Exception.Message)"
    if ($_.ErrorDetails) {
        Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
    exit 1
}
