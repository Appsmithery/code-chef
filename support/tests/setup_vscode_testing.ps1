# VS Code Python Testing Setup Verification Script
# Run: .\support\tests\setup_vscode_testing.ps1

Write-Host "================================" -ForegroundColor Cyan
Write-Host "VS Code Testing Setup Verification" -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

# Check Python installation
Write-Host "1. Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "   ✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "   ✗ Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

# Check pip
Write-Host "`n2. Checking pip..." -ForegroundColor Yellow
try {
    $pipVersion = pip --version 2>&1
    Write-Host "   ✓ pip found: $pipVersion" -ForegroundColor Green
} catch {
    Write-Host "   ✗ pip not found" -ForegroundColor Red
    exit 1
}

# Check if pytest is installed
Write-Host "`n3. Checking pytest installation..." -ForegroundColor Yellow
$pytestCheck = & { pytest --version 2>&1 } | Out-String
if ($LASTEXITCODE -eq 0) {
    Write-Host "   [OK] pytest found: $pytestCheck" -ForegroundColor Green
} else {
    Write-Host "   [WARN] pytest not found. Installing test dependencies..." -ForegroundColor Yellow
    pip install -r support/tests/requirements.txt
}

# Check test dependencies
Write-Host "`n4. Checking test dependencies..." -ForegroundColor Yellow
$requiredPackages = @(
    "pytest",
    "pytest-asyncio",
    "pytest-cov",
    "httpx",
    "asyncpg",
    "langchain",
    "qdrant-client"
)

$missingPackages = @()
foreach ($package in $requiredPackages) {
    $installed = pip show $package 2>$null
    if ($installed) {
        Write-Host "   [OK] $package installed" -ForegroundColor Green
    } else {
        Write-Host "   [MISSING] $package missing" -ForegroundColor Red
        $missingPackages += $package
    }
}

if ($missingPackages.Count -gt 0) {
    Write-Host "`n   Installing missing packages..." -ForegroundColor Yellow
    pip install -r support/tests/requirements.txt
}

# Check VS Code configuration files
Write-Host "`n5. Checking VS Code configuration..." -ForegroundColor Yellow

$configFiles = @(
    ".vscode/settings.json",
    ".vscode/launch.json",
    ".vscode/tasks.json",
    "support/tests/pytest.ini",
    "support/tests/conftest.py",
    "support/tests/requirements.txt"
)

foreach ($file in $configFiles) {
    if (Test-Path $file) {
        Write-Host "   [OK] $file exists" -ForegroundColor Green
    } else {
        Write-Host "   [MISSING] $file missing" -ForegroundColor Red
    }
}

# Test discovery
Write-Host "`n6. Running test discovery..." -ForegroundColor Yellow
$testOutput = & { pytest support/tests --collect-only -q 2>&1 } | Out-String
if ($LASTEXITCODE -eq 0) {
    $testCount = ($testOutput | Select-String "test" | Measure-Object).Count
    Write-Host "   [OK] Discovered $testCount test items" -ForegroundColor Green
} else {
    Write-Host "   [ERROR] Test discovery failed" -ForegroundColor Red
}

# Check test structure
Write-Host "`n7. Checking test directory structure..." -ForegroundColor Yellow
$testDirs = @(
    "support/tests/e2e",
    "support/tests/integration",
    "support/tests/workflows",
    "support/tests/hitl",
    "support/tests/performance"
)

foreach ($dir in $testDirs) {
    if (Test-Path $dir) {
        $fileCount = (Get-ChildItem $dir -Filter "test_*.py" | Measure-Object).Count
        Write-Host "   [OK] $dir - $fileCount test files" -ForegroundColor Green
    } else {
        Write-Host "   [MISSING] $dir missing" -ForegroundColor Red
    }
}

# Check environment file
Write-Host "`n8. Checking environment configuration..." -ForegroundColor Yellow
if (Test-Path "config/env/.env") {
    Write-Host "   [OK] .env file exists" -ForegroundColor Green
    
    # Check for important keys
    $envContent = Get-Content "config/env/.env" -Raw
    $keys = @("DATABASE_URL", "GRADIENT_API_KEY", "LINEAR_API_KEY")
    
    foreach ($key in $keys) {
        if ($envContent -match "$key=") {
            Write-Host "   [OK] $key configured" -ForegroundColor Green
        } else {
            Write-Host "   [WARN] $key not set (optional for mocked tests)" -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "   [WARN] .env file not found (copy from .env.template)" -ForegroundColor Yellow
}

# Run a simple test
Write-Host "`n9. Running sample test..." -ForegroundColor Yellow
$null = & { pytest support/tests/e2e/test_feature_workflow.py::TestFeatureDevelopmentWorkflow::test_high_risk_approval_flow -v 2>&1 } | Out-String
if ($LASTEXITCODE -eq 0) {
    Write-Host "   [OK] Sample test passed" -ForegroundColor Green
} else {
    Write-Host "   [WARN] Sample test failed (check output)" -ForegroundColor Yellow
}

# Summary
Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "Setup Verification Complete" -ForegroundColor Cyan
Write-Host "================================`n" -ForegroundColor Cyan

Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Open VS Code Test Explorer: View → Testing (or Ctrl+Shift+T)" -ForegroundColor White
Write-Host "2. Tests should auto-discover. If not, click Refresh icon" -ForegroundColor White
Write-Host "3. Click ▶️ next to any test to run it" -ForegroundColor White
Write-Host "4. Right-click → Debug Test to debug with breakpoints" -ForegroundColor White
Write-Host "`nDocumentation: support/tests/VSCODE_TESTING.md`n" -ForegroundColor Cyan
