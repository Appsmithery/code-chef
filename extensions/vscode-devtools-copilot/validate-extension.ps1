#!/usr/bin/env pwsh
# VS Code Extension Validation Script

$ErrorActionPreference = "Stop"

Write-Host "🔍 Validating VS Code Extension..." -ForegroundColor Cyan

$extensionDir = "D:\INFRA\Dev-Tools\Dev-Tools\extensions\vscode-devtools-copilot"
$errors = @()
$warnings = @()

# Check required files
$requiredFiles = @(
    "package.json",
    "README.md",
    ".vscodeignore",
    "tsconfig.json",
    "Taskfile.yml",
    "src/extension.ts",
    "src/chatParticipant.ts",
    "src/orchestratorClient.ts",
    "src/contextExtractor.ts",
    "src/sessionManager.ts",
    "src/linearWatcher.ts",
    "prompts/system.md"
)

Write-Host "`n📁 Checking required files..." -ForegroundColor Yellow
foreach ($file in $requiredFiles) {
    $path = Join-Path $extensionDir $file
    if (Test-Path $path) {
        Write-Host "  ✅ $file" -ForegroundColor Green
    } else {
        $errors += "Missing file: $file"
        Write-Host "  ❌ $file" -ForegroundColor Red
    }
}

# Check compiled output
Write-Host "`n🔨 Checking compiled output..." -ForegroundColor Yellow
$compiledFiles = @(
    "out/extension.js",
    "out/chatParticipant.js",
    "out/orchestratorClient.js",
    "out/contextExtractor.js",
    "out/sessionManager.js",
    "out/linearWatcher.js"
)

foreach ($file in $compiledFiles) {
    $path = Join-Path $extensionDir $file
    if (Test-Path $path) {
        Write-Host "  ✅ $file" -ForegroundColor Green
    } else {
        $warnings += "Missing compiled file: $file (run 'npm run compile')"
        Write-Host "  ⚠️  $file" -ForegroundColor Yellow
    }
}

# Check node_modules
Write-Host "`n📦 Checking dependencies..." -ForegroundColor Yellow
$nodeModulesPath = Join-Path $extensionDir "node_modules"
if (Test-Path $nodeModulesPath) {
    Write-Host "  ✅ node_modules exists" -ForegroundColor Green
    
    $requiredDeps = @("axios", "eventsource", "typescript", "eslint")
    foreach ($dep in $requiredDeps) {
        $depPath = Join-Path $nodeModulesPath $dep
        if (Test-Path $depPath) {
            Write-Host "  ✅ $dep installed" -ForegroundColor Green
        } else {
            $warnings += "Missing dependency: $dep"
            Write-Host "  ⚠️  $dep not found" -ForegroundColor Yellow
        }
    }
} else {
    $errors += "node_modules not found (run 'npm install')"
    Write-Host "  ❌ node_modules not found" -ForegroundColor Red
}

# Check orchestrator connectivity
Write-Host "`n🌐 Checking orchestrator connectivity..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://45.55.173.72:8001/health" -TimeoutSec 5
    $health = $response.Content | ConvertFrom-Json
    Write-Host "  ✅ Orchestrator healthy (status: $($health.status))" -ForegroundColor Green
} catch {
    $warnings += "Cannot reach orchestrator: $_"
    Write-Host "  ⚠️  Orchestrator unreachable" -ForegroundColor Yellow
}

# Check MCP gateway connectivity
Write-Host "`n🔌 Checking MCP gateway connectivity..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://45.55.173.72:8000/health" -TimeoutSec 5
    Write-Host "  ✅ MCP Gateway healthy" -ForegroundColor Green
} catch {
    $warnings += "Cannot reach MCP gateway: $_"
    Write-Host "  ⚠️  MCP Gateway unreachable" -ForegroundColor Yellow
}

# Summary
Write-Host "`n" + ("="*60) -ForegroundColor Cyan
Write-Host "VALIDATION SUMMARY" -ForegroundColor Cyan
Write-Host ("="*60) -ForegroundColor Cyan

if ($errors.Count -eq 0 -and $warnings.Count -eq 0) {
    Write-Host "`n✅ All checks passed!" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Cyan
    Write-Host "  1. Press F5 to launch Extension Development Host" -ForegroundColor White
    Write-Host "  2. Open Copilot Chat (Ctrl+I)" -ForegroundColor White
    Write-Host "  3. Type: @devtools Add JWT authentication to my API" -ForegroundColor White
    exit 0
} else {
    if ($errors.Count -gt 0) {
        Write-Host ""
        Write-Host "ERRORS ($($errors.Count)):" -ForegroundColor Red
        foreach ($error in $errors) {
            Write-Host "  - $error" -ForegroundColor Red
        }
    }
    
    if ($warnings.Count -gt 0) {
        Write-Host ""
        Write-Host "WARNINGS ($($warnings.Count)):" -ForegroundColor Yellow
        foreach ($warning in $warnings) {
            Write-Host "  - $warning" -ForegroundColor Yellow
        }
    }
    
    if ($errors.Count -gt 0) {
        Write-Host ""
        Write-Host "Validation failed. Fix errors before proceeding." -ForegroundColor Red
        exit 1
    } else {
        Write-Host ""
        Write-Host "Validation passed with warnings. Extension may still work." -ForegroundColor Yellow
        exit 0
    }
}
