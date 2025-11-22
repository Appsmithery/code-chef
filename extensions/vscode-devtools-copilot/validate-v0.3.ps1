#!/usr/bin/env pwsh

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VS Code Extension v0.3 Validation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Check package.json version
Write-Host "`n[CHECK] package.json version..." -ForegroundColor Yellow
$version = (Get-Content package.json | ConvertFrom-Json).version
if ($version -eq "0.3.0") {
    Write-Host "  ✅ Version: $version" -ForegroundColor Green
} else {
    Write-Host "  ❌ Expected: 0.3.0, Got: $version" -ForegroundColor Red
    exit 1
}

# 2. Check for deprecated port references
Write-Host "`n[CHECK] No references to deprecated agent ports..." -ForegroundColor Yellow
$deprecatedPorts = @(8002, 8003, 8004, 8005, 8006)
$foundDeprecated = $false
foreach ($port in $deprecatedPorts) {
    $matches = Select-String -Path "src/*.ts", "README.md" -Pattern ":$port" -SimpleMatch -ErrorAction SilentlyContinue
    if ($matches) {
        Write-Host "  ❌ Found reference to port $port" -ForegroundColor Red
        $matches | ForEach-Object { Write-Host "     $($_.Filename):$($_.LineNumber)" -ForegroundColor Red }
        $foundDeprecated = $true
    }
}
if (-not $foundDeprecated) {
    Write-Host "  ✅ No deprecated ports found" -ForegroundColor Green
}

# 3. Check orchestrator health
Write-Host "`n[CHECK] Orchestrator health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://45.55.173.72:8001/health" -Method GET -TimeoutSec 5
    if ($health.status -eq "healthy" -or $health.status -eq "ok") {
        Write-Host "  ✅ Orchestrator healthy" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Orchestrator status: $($health.status)" -ForegroundColor Red
    }
} catch {
    Write-Host "  ❌ Cannot reach orchestrator: $_" -ForegroundColor Red
}

# 4. Check documentation links
Write-Host "`n[CHECK] Documentation links..." -ForegroundColor Yellow
$requiredDocs = @(
    "LINEAR_INTEGRATION_GUIDE.md",
    "LINEAR_HITL_WORKFLOW.md",
    "DEPLOYMENT_GUIDE.md"
)
$missingDocs = @()
foreach ($doc in $requiredDocs) {
    if (-not (Test-Path "../../support/docs/$doc")) {
        $missingDocs += $doc
    }
}
if ($missingDocs.Count -eq 0) {
    Write-Host "  ✅ All documentation links valid" -ForegroundColor Green
} else {
    Write-Host "  ❌ Missing docs: $($missingDocs -join ', ')" -ForegroundColor Red
}

# 5. Check TypeScript compilation
Write-Host "`n[CHECK] TypeScript compilation..." -ForegroundColor Yellow
npm run compile 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ TypeScript compiles without errors" -ForegroundColor Green
} else {
    Write-Host "  ❌ TypeScript compilation failed" -ForegroundColor Red
}

# 6. Check Linear hub issue setting
Write-Host "`n[CHECK] Linear hub issue configuration..." -ForegroundColor Yellow
$packageJson = Get-Content package.json | ConvertFrom-Json
$linearHubDefault = $packageJson.contributes.configuration.properties."devtools.linearHubIssue".default
if ($linearHubDefault -eq "DEV-68") {
    Write-Host "  ✅ Linear hub issue: $linearHubDefault" -ForegroundColor Green
} else {
    Write-Host "  ❌ Expected: DEV-68, Got: $linearHubDefault" -ForegroundColor Red
}

# 7. Check badge update
Write-Host "`n[CHECK] Badge reflects LangGraph architecture..." -ForegroundColor Yellow
$badgeDescription = $packageJson.badges[0].description
if ($badgeDescription -like "*LangGraph*") {
    Write-Host "  ✅ Badge: $badgeDescription" -ForegroundColor Green
} else {
    Write-Host "  ❌ Badge not updated: $badgeDescription" -ForegroundColor Red
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Validation Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
