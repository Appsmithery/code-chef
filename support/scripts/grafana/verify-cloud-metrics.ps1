#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Verify Grafana Cloud metrics ingestion
.DESCRIPTION
    Checks if metrics from Dev-Tools droplet are flowing to Grafana Cloud
#>

$ErrorActionPreference = "Stop"

$GRAFANA_CLOUD_URL = "https://appsmithery.grafana.net"
$PROMETHEUS_URL = "https://prometheus-prod-56-prod-us-east-2.grafana.net/api/prom"
$ORG_ID = "1534681"
$API_TOKEN = $env:GRAFANA_CLOUD_API_TOKEN

if (-not $API_TOKEN) {
    Write-Host "❌ GRAFANA_CLOUD_API_TOKEN not set" -ForegroundColor Red
    Write-Host "Run: `$env:GRAFANA_CLOUD_API_TOKEN='glsa_gYG6QyRKAKYInZSNQ8inn5SMdFh47fmV_375df6c0'" -ForegroundColor Yellow
    exit 1
}

Write-Host "=== Grafana Cloud Metrics Verification ===" -ForegroundColor Cyan
Write-Host ""

# Test 1: Check agent health metrics
Write-Host "[1/5] Checking Grafana Agent metrics..." -ForegroundColor Yellow
$query1 = "up{cluster='dev-tools'}"
$url1 = "$PROMETHEUS_URL/query?query=$([System.Web.HttpUtility]::UrlEncode($query1))"

try {
    $response1 = Invoke-RestMethod -Uri $url1 -Headers @{
        Authorization = "Bearer $API_TOKEN"
        "X-Scope-OrgID" = $ORG_ID
    } -Method Get
    
    if ($response1.status -eq "success" -and $response1.data.result.Count -gt 0) {
        Write-Host "✅ Found $($response1.data.result.Count) services reporting metrics" -ForegroundColor Green
        $response1.data.result | ForEach-Object {
            $service = $_.metric.service
            $value = $_.value[1]
            $status = if ($value -eq "1") { "UP" } else { "DOWN" }
            Write-Host "   - $service : $status" -ForegroundColor $(if ($value -eq "1") { "Green" } else { "Red" })
        }
    } else {
        Write-Host "⚠️  No agent metrics found yet" -ForegroundColor Yellow
        Write-Host "   Wait 15-30 seconds for first scrape" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Failed to query metrics: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 2: Check LLM token metrics
Write-Host "[2/5] Checking LLM token metrics..." -ForegroundColor Yellow
$query2 = "llm_tokens_total{cluster='dev-tools'}"
$url2 = "$PROMETHEUS_URL/query?query=$([System.Web.HttpUtility]::UrlEncode($query2))"

try {
    $response2 = Invoke-RestMethod -Uri $url2 -Headers @{
        Authorization = "Bearer $API_TOKEN"
        "X-Scope-OrgID" = $ORG_ID
    } -Method Get
    
    if ($response2.status -eq "success" -and $response2.data.result.Count -gt 0) {
        Write-Host "✅ Found LLM token metrics" -ForegroundColor Green
        $response2.data.result | Select-Object -First 3 | ForEach-Object {
            $agent = $_.metric.agent_name
            $type = $_.metric.token_type
            $value = [math]::Round($_.value[1])
            Write-Host "   - $agent ($type): $value tokens" -ForegroundColor Cyan
        }
    } else {
        Write-Host "⚠️  No LLM metrics found yet" -ForegroundColor Yellow
        Write-Host "   Trigger a test call to generate metrics" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Failed to query LLM metrics: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 3: Check LLM cost metrics
Write-Host "[3/5] Checking LLM cost metrics..." -ForegroundColor Yellow
$query3 = "llm_cost_usd_total{cluster='dev-tools'}"
$url3 = "$PROMETHEUS_URL/query?query=$([System.Web.HttpUtility]::UrlEncode($query3))"

try {
    $response3 = Invoke-RestMethod -Uri $url3 -Headers @{
        Authorization = "Bearer $API_TOKEN"
        "X-Scope-OrgID" = $ORG_ID
    } -Method Get
    
    if ($response3.status -eq "success" -and $response3.data.result.Count -gt 0) {
        Write-Host "✅ Found LLM cost metrics" -ForegroundColor Green
        $totalCost = ($response3.data.result | ForEach-Object { [double]$_.value[1] } | Measure-Object -Sum).Sum
        Write-Host "   Total cost: `$$([math]::Round($totalCost, 4))" -ForegroundColor Green
    } else {
        Write-Host "⚠️  No cost metrics found yet" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Failed to query cost metrics: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 4: Check data freshness
Write-Host "[4/5] Checking data freshness..." -ForegroundColor Yellow
$query4 = "time() - max(up{cluster='dev-tools'})"
$url4 = "$PROMETHEUS_URL/query?query=$([System.Web.HttpUtility]::UrlEncode($query4))"

try {
    $response4 = Invoke-RestMethod -Uri $url4 -Headers @{
        Authorization = "Bearer $API_TOKEN"
        "X-Scope-OrgID" = $ORG_ID
    } -Method Get
    
    if ($response4.status -eq "success" -and $response4.data.result.Count -gt 0) {
        $ageSeconds = [math]::Round([double]$response4.data.result[0].value[1])
        if ($ageSeconds -lt 30) {
            Write-Host "✅ Data is fresh (${ageSeconds}s old)" -ForegroundColor Green
        } else {
            Write-Host "⚠️  Data is stale (${ageSeconds}s old)" -ForegroundColor Yellow
            Write-Host "   Check Grafana Alloy status: ssh do-mcp-gateway 'systemctl status alloy'" -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "⚠️  Cannot determine data freshness" -ForegroundColor Yellow
}
Write-Host ""

# Test 5: Open dashboard
Write-Host "[5/5] Dashboard access..." -ForegroundColor Yellow
$dashboardUrl = "https://appsmithery.grafana.net/d/ed621f5b-cc44-43e6-be73-ab9922cb36fc"
Write-Host "Dashboard URL: $dashboardUrl" -ForegroundColor Cyan
Write-Host ""

Write-Host "=== Verification Summary ===" -ForegroundColor Green
Write-Host ""
Write-Host "Commands:" -ForegroundColor Cyan
Write-Host "  1. Open dashboard in browser:"
Write-Host "     start $dashboardUrl"
Write-Host ""
Write-Host "  2. Check Alloy agent logs:"
Write-Host "     ssh do-mcp-gateway 'journalctl -u alloy -f'" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Restart agent if needed:"
Write-Host "     ssh do-mcp-gateway 'systemctl restart alloy'" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. Query metrics directly (Explore):"
Write-Host "     https://appsmithery.grafana.net/explore"
Write-Host "     Query: up with cluster label dev-tools"
Write-Host ""
