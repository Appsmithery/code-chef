#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Upload Grafana dashboards to Grafana Cloud via API
.DESCRIPTION
    Reads dashboard JSON files from config/grafana/dashboards/ and uploads
    them to Grafana Cloud using the REST API. Requires GRAFANA_CLOUD_API_TOKEN
    environment variable or pass via -ApiKey parameter.
.PARAMETER ApiKey
    Grafana Cloud API key (overrides environment variable)
.PARAMETER GrafanaUrl
    Grafana Cloud instance URL (default: https://appsmithery.grafana.net)
.PARAMETER DashboardDir
    Directory containing dashboard JSON files (default: config/grafana/dashboards)
.PARAMETER DryRun
    Preview what would be uploaded without actually uploading
.EXAMPLE
    .\upload_dashboards.ps1
.EXAMPLE
    .\upload_dashboards.ps1 -ApiKey "glsa_xyz123..." -DryRun
#>

param(
    [Parameter(Mandatory = $false)]
    [string]$ApiKey = $env:GRAFANA_CLOUD_API_TOKEN,
    
    [Parameter(Mandatory = $false)]
    [string]$GrafanaUrl = "https://appsmithery.grafana.net",
    
    [Parameter(Mandatory = $false)]
    [string]$DashboardDir = "config/grafana/dashboards",
    
    [Parameter(Mandatory = $false)]
    [switch]$DryRun
)

# ANSI color codes
$ColorReset = "`e[0m"
$ColorGreen = "`e[32m"
$ColorYellow = "`e[33m"
$ColorRed = "`e[31m"
$ColorBlue = "`e[34m"
$ColorCyan = "`e[36m"

function Write-Status {
    param([string]$Message, [string]$Color = $ColorReset)
    Write-Host "${Color}${Message}${ColorReset}"
}

function Write-Success { param([string]$Message) Write-Status $Message $ColorGreen }
function Write-Warning { param([string]$Message) Write-Status $Message $ColorYellow }
function Write-Error { param([string]$Message) Write-Status $Message $ColorRed }
function Write-Info { param([string]$Message) Write-Status $Message $ColorBlue }
function Write-Detail { param([string]$Message) Write-Status $Message $ColorCyan }

# Validate API key
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    Write-Error "❌ Error: GRAFANA_CLOUD_API_TOKEN not set"
    Write-Info "Set it via environment variable or pass -ApiKey parameter"
    Write-Info ""
    Write-Info "To create an API key:"
    Write-Info "1. Go to $GrafanaUrl"
    Write-Info "2. Settings → API Keys → Add API Key"
    Write-Info "3. Name: 'Dashboard Upload', Role: Editor"
    Write-Info "4. Copy the key and set: `$env:GRAFANA_CLOUD_API_TOKEN='glsa_...'"
    exit 1
}

# Validate dashboard directory
$RepoRoot = Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$DashboardPath = Join-Path $RepoRoot $DashboardDir

if (-not (Test-Path $DashboardPath)) {
    Write-Error "❌ Error: Dashboard directory not found: $DashboardPath"
    exit 1
}

# Get all dashboard JSON files
$DashboardFiles = Get-ChildItem -Path $DashboardPath -Filter "*.json" | 
Where-Object { $_.Name -ne "dashboard-provider.yml" }

if ($DashboardFiles.Count -eq 0) {
    Write-Warning "⚠️  No dashboard JSON files found in $DashboardPath"
    exit 0
}

Write-Info "╔══════════════════════════════════════════════════════════════╗"
Write-Info "║         Grafana Cloud Dashboard Upload                      ║"
Write-Info "╚══════════════════════════════════════════════════════════════╝"
Write-Info ""
Write-Info "Grafana URL:    $GrafanaUrl"
Write-Info "Dashboard Dir:  $DashboardPath"
Write-Info "Dashboards:     $($DashboardFiles.Count)"
if ($DryRun) { Write-Warning "Mode:           DRY RUN (no changes will be made)" }
Write-Info ""

$SuccessCount = 0
$FailCount = 0
$SkipCount = 0

foreach ($File in $DashboardFiles) {
    Write-Detail "──────────────────────────────────────────────────────────────"
    Write-Info "📊 Processing: $($File.Name)"
    
    try {
        # Read and parse dashboard JSON
        $DashboardJson = Get-Content $File.FullName -Raw | ConvertFrom-Json
        
        # Extract title for display
        $Title = $DashboardJson.dashboard.title
        Write-Detail "   Title: $Title"
        
        if ($DryRun) {
            Write-Warning "   [DRY RUN] Would upload to $GrafanaUrl/api/dashboards/db"
            $SkipCount++
            continue
        }
        
        # Prepare API payload
        $Payload = @{
            dashboard = $DashboardJson.dashboard
            overwrite = $true
            message   = "Uploaded via API on $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
        } | ConvertTo-Json -Depth 100 -Compress
        
        # Upload to Grafana
        $Headers = @{
            "Authorization" = "Bearer $ApiKey"
            "Content-Type"  = "application/json"
        }
        
        $ApiEndpoint = "$GrafanaUrl/api/dashboards/db"
        
        Write-Detail "   Uploading..."
        $Response = Invoke-RestMethod -Uri $ApiEndpoint `
            -Method Post `
            -Headers $Headers `
            -Body $Payload `
            -ErrorAction Stop
        
        Write-Success "   ✅ Uploaded successfully"
        Write-Detail "   Dashboard ID: $($Response.id)"
        Write-Detail "   URL: $GrafanaUrl$($Response.url)"
        $SuccessCount++
        
    }
    catch {
        Write-Error "   ❌ Failed to upload"
        Write-Error "   Error: $($_.Exception.Message)"
        if ($_.ErrorDetails.Message) {
            $ErrorDetail = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue
            if ($ErrorDetail) {
                Write-Error "   Details: $($ErrorDetail.message)"
            }
        }
        $FailCount++
    }
    
    Write-Host ""
}

# Summary
Write-Info "══════════════════════════════════════════════════════════════"
Write-Info "📈 Upload Summary"
Write-Info "══════════════════════════════════════════════════════════════"
if ($DryRun) {
    Write-Warning "Would upload: $SkipCount dashboards"
}
else {
    Write-Success "✅ Success: $SuccessCount"
    if ($FailCount -gt 0) {
        Write-Error "❌ Failed:  $FailCount"
    }
    if ($SkipCount -gt 0) {
        Write-Warning "⏭️  Skipped: $SkipCount"
    }
}
Write-Info "══════════════════════════════════════════════════════════════"

if ($FailCount -gt 0) {
    exit 1
}

if (-not $DryRun) {
    Write-Info ""
    Write-Success "🎉 All dashboards uploaded successfully!"
    Write-Info "View them at: $GrafanaUrl/dashboards"
}
