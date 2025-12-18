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

$ErrorActionPreference = "Stop"

# Validate API key
if ([string]::IsNullOrWhiteSpace($ApiKey)) {
    Write-Host ""
    Write-Host "ERROR: GRAFANA_CLOUD_API_TOKEN not set" -ForegroundColor Red
    Write-Host ""
    Write-Host "To create an API key:" -ForegroundColor Cyan
    Write-Host "1. Go to $GrafanaUrl"
    Write-Host "2. Settings -> API Keys -> Add API Key"
    Write-Host "3. Name: 'Dashboard Upload', Role: Editor"
    Write-Host "4. Copy the key and set: `$env:GRAFANA_CLOUD_API_TOKEN='glsa_...'"
    Write-Host ""
    exit 1
}

# Validate dashboard directory
$RepoRoot = Split-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) -Parent
$DashboardPath = Join-Path $RepoRoot $DashboardDir

if (-not (Test-Path $DashboardPath)) {
    Write-Host "ERROR: Dashboard directory not found: $DashboardPath" -ForegroundColor Red
    exit 1
}

# Get all dashboard JSON files
$DashboardFiles = Get-ChildItem -Path $DashboardPath -Filter "*.json" | 
Where-Object { $_.Name -ne "dashboard-provider.yml" }

if ($DashboardFiles.Count -eq 0) {
    Write-Host "WARNING: No dashboard JSON files found in $DashboardPath" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "         Grafana Cloud Dashboard Upload" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Grafana URL:    $GrafanaUrl" -ForegroundColor White
Write-Host "Dashboard Dir:  $DashboardPath" -ForegroundColor White
Write-Host "Dashboards:     $($DashboardFiles.Count)" -ForegroundColor White
if ($DryRun) { Write-Host "Mode:           DRY RUN (no changes)" -ForegroundColor Yellow }
Write-Host ""

$SuccessCount = 0
$FailCount = 0
$SkipCount = 0

foreach ($File in $DashboardFiles) {
    Write-Host "----------------------------------------------------------------" -ForegroundColor Gray
    Write-Host "Processing: $($File.Name)" -ForegroundColor Cyan
    
    try {
        # Read and parse dashboard JSON
        $DashboardJson = Get-Content $File.FullName -Raw | ConvertFrom-Json
        
        # Extract title for display
        $Title = $DashboardJson.dashboard.title
        Write-Host "   Title: $Title" -ForegroundColor White
        
        if ($DryRun) {
            Write-Host "   [DRY RUN] Would upload to $GrafanaUrl/api/dashboards/db" -ForegroundColor Yellow
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
        
        Write-Host "   Uploading..." -ForegroundColor Gray
        $Response = Invoke-RestMethod -Uri $ApiEndpoint `
            -Method Post `
            -Headers $Headers `
            -Body $Payload `
            -ErrorAction Stop
        
        Write-Host "   SUCCESS: Uploaded successfully" -ForegroundColor Green
        Write-Host "   Dashboard ID: $($Response.id)" -ForegroundColor Gray
        Write-Host "   URL: $GrafanaUrl$($Response.url)" -ForegroundColor Gray
        $SuccessCount++
        
    }
    catch {
        Write-Host "   FAILED: $($_.Exception.Message)" -ForegroundColor Red
        if ($_.ErrorDetails.Message) {
            $ErrorDetail = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue
            if ($ErrorDetail) {
                Write-Host "   Details: $($ErrorDetail.message)" -ForegroundColor Red
            }
        }
        $FailCount++
    }
    
    Write-Host ""
}

# Summary
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Upload Summary" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
if ($DryRun) {
    Write-Host "Would upload: $SkipCount dashboards" -ForegroundColor Yellow
}
else {
    Write-Host "Success: $SuccessCount" -ForegroundColor Green
    if ($FailCount -gt 0) {
        Write-Host "Failed:  $FailCount" -ForegroundColor Red
    }
    if ($SkipCount -gt 0) {
        Write-Host "Skipped: $SkipCount" -ForegroundColor Yellow
    }
}
Write-Host "================================================================" -ForegroundColor Cyan

if ($FailCount -gt 0) {
    exit 1
}

if (-not $DryRun) {
    Write-Host ""
    Write-Host "All dashboards uploaded successfully!" -ForegroundColor Green
    Write-Host "View them at: $GrafanaUrl/dashboards" -ForegroundColor Cyan
}
