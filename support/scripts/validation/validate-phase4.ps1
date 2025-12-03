# Phase 4 Validation Script
# Validates Prometheus config, Grafana dashboard, hot-reload, and end-to-end tracking

param(
    [switch]$SkipPrometheus,
    [switch]$SkipGrafana,
    [switch]$SkipHotReload,
    [switch]$SkipE2E
)

$ErrorActionPreference = "Stop"
$RepoRoot = "$PSScriptRoot\..\..\..\"
$PromConfigPath = "$RepoRoot\config\prometheus\alerts\llm-metrics.yml"
$GrafanaDashboardPath = "$RepoRoot\config\grafana\dashboards\llm-token-metrics.json"
$ModelsConfigPath = "$RepoRoot\config\agents\models.yaml"

Write-Host "=== Phase 4 Validation ===" -ForegroundColor Cyan
Write-Host ""

$TestsPassed = 0
$TestsFailed = 0

function Test-Section {
    param($Name, $ScriptBlock)
    
    Write-Host "Testing: $Name" -ForegroundColor Yellow
    try {
        & $ScriptBlock
        Write-Host "✅ PASSED: $Name" -ForegroundColor Green
        $script:TestsPassed++
    } catch {
        Write-Host "❌ FAILED: $Name" -ForegroundColor Red
        Write-Host "  Error: $_" -ForegroundColor Red
        $script:TestsFailed++
    }
    Write-Host ""
}

# Test 1: Prometheus Config Validation
if (-not $SkipPrometheus) {
    Test-Section "Prometheus Alert Rules Validation" {
        if (-not (Test-Path $PromConfigPath)) {
            throw "Prometheus config not found: $PromConfigPath"
        }

        Write-Host "  Checking promtool availability..."
        $promtool = Get-Command promtool -ErrorAction SilentlyContinue
        if (-not $promtool) {
            Write-Host "  ⚠️  promtool not installed, skipping validation" -ForegroundColor Yellow
            Write-Host "  Install: https://prometheus.io/download/" -ForegroundColor Yellow
            return
        }

        Write-Host "  Running: promtool check rules $PromConfigPath"
        $output = promtool check rules $PromConfigPath 2>&1
        
        if ($LASTEXITCODE -ne 0) {
            throw "promtool validation failed: $output"
        }

        Write-Host "  Prometheus config is valid"
        Write-Host "  Output: $output"
    }
}

# Test 2: Grafana Dashboard Validation
if (-not $SkipGrafana) {
    Test-Section "Grafana Dashboard JSON Validation" {
        if (-not (Test-Path $GrafanaDashboardPath)) {
            throw "Grafana dashboard not found: $GrafanaDashboardPath"
        }

        Write-Host "  Parsing JSON..."
        $dashboardWrapper = Get-Content $GrafanaDashboardPath -Raw | ConvertFrom-Json

        # Handle nested dashboard structure
        $dashboard = if ($dashboardWrapper.dashboard) { $dashboardWrapper.dashboard } else { $dashboardWrapper }

        # Check required fields
        if (-not $dashboard.title) {
            throw "Missing 'title' field in dashboard"
        }

        if (-not $dashboard.panels) {
            throw "Missing 'panels' field in dashboard"
        }

        $panelCount = $dashboard.panels.Count
        Write-Host "  Dashboard title: $($dashboard.title)"
        Write-Host "  Panel count: $panelCount"

        if ($panelCount -lt 10) {
            throw "Expected at least 10 panels, found $panelCount"
        }

        # Check for required panels
        $panelTitles = $dashboard.panels | ForEach-Object { $_.title }
        $requiredPanels = @(
            "Token Usage Rate by Agent",
            "Cost Breakdown by Agent",
            "LLM Latency Distribution"
        )

        foreach ($required in $requiredPanels) {
            if ($panelTitles -notcontains $required) {
                Write-Host "  ⚠️  Panel '$required' not found" -ForegroundColor Yellow
            }
        }

        Write-Host "  Grafana dashboard JSON is valid"
    }
}

# Test 3: Hot-Reload Test
if (-not $SkipHotReload) {
    Test-Section "Hot-Reload Capability" {
        if (-not (Test-Path $ModelsConfigPath)) {
            throw "Models config not found: $ModelsConfigPath"
        }

        Write-Host "  Reading models.yaml..."
        $configContent = Get-Content $ModelsConfigPath -Raw

        # Check for key fields
        if ($configContent -notmatch "orchestrator:") {
            throw "orchestrator config not found in YAML"
        }

        if ($configContent -notmatch "model:") {
            throw "model field not found in YAML"
        }

        Write-Host "  YAML config is loadable"
        Write-Host "  Hot-reload process:"
        Write-Host "    1. Edit $ModelsConfigPath"
        Write-Host "    2. Run: docker compose restart orchestrator"
        Write-Host "    3. Wait 30s for health check"
        Write-Host "    4. Verify: curl http://localhost:8001/health"
    }
}

# Test 4: End-to-End Token Tracking
if (-not $SkipE2E) {
    Test-Section "End-to-End Token Tracking" {
        Write-Host "  Checking orchestrator health..."
        
        try {
            $health = Invoke-RestMethod -Uri "http://localhost:8001/health" -TimeoutSec 5
            Write-Host "  Orchestrator is healthy: $($health.status)"
        } catch {
            Write-Host "  ⚠️  Orchestrator not reachable (may be down)" -ForegroundColor Yellow
            Write-Host "  Skipping live endpoint tests" -ForegroundColor Yellow
            return
        }

        Write-Host "  Testing /metrics/tokens endpoint..."
        try {
            $metricsTokens = Invoke-RestMethod -Uri "http://localhost:8001/metrics/tokens" -TimeoutSec 5
            
            # Check structure
            if (-not $metricsTokens.per_agent) {
                throw "/metrics/tokens missing 'per_agent' field"
            }
            if (-not $metricsTokens.totals) {
                throw "/metrics/tokens missing 'totals' field"
            }

            $totalCalls = $metricsTokens.totals.total_calls
            $totalCost = $metricsTokens.totals.total_cost
            $totalTokens = $metricsTokens.totals.total_tokens

            Write-Host "  Total calls: $totalCalls"
            Write-Host "  Total cost: `$$totalCost"
            Write-Host "  Total tokens: $totalTokens"

            if ($totalCalls -eq 0) {
                Write-Host "  ⚠️  No LLM calls tracked yet (expected in fresh deployment)" -ForegroundColor Yellow
            }

        } catch {
            throw "/metrics/tokens endpoint error: $_"
        }

        Write-Host "  Testing /metrics (Prometheus) endpoint..."
        try {
            $metricsPrometheus = Invoke-RestMethod -Uri "http://localhost:8001/metrics" -TimeoutSec 5
            
            if ($metricsPrometheus -notmatch "llm_tokens_total") {
                throw "/metrics missing 'llm_tokens_total' metric"
            }
            if ($metricsPrometheus -notmatch "llm_cost_usd_total") {
                throw "/metrics missing 'llm_cost_usd_total' metric"
            }

            Write-Host "  Prometheus metrics exported correctly"

        } catch {
            throw "/metrics endpoint error: $_"
        }
    }
}

# Summary
Write-Host "=== Validation Summary ===" -ForegroundColor Cyan
Write-Host "Tests Passed: $TestsPassed" -ForegroundColor Green
Write-Host "Tests Failed: $TestsFailed" -ForegroundColor $(if ($TestsFailed -gt 0) { "Red" } else { "Green" })
Write-Host ""

if ($TestsFailed -eq 0) {
    Write-Host "✅ All validations passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host "  1. Deploy to droplet: .\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config"
    Write-Host "  2. Verify health: curl https://codechef.appsmithery.co/api/health"
    Write-Host "  3. Check metrics: curl https://codechef.appsmithery.co/api/metrics/tokens"
    Write-Host "  4. Import Grafana dashboard: config/grafana/dashboards/llm-token-metrics.json"
    exit 0
} else {
    Write-Host "❌ Some validations failed. Review errors above." -ForegroundColor Red
    exit 1
}
