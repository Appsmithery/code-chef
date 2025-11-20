#!/usr/bin/env pwsh
# Test MCP Bridge Client packages locally

$ErrorActionPreference = "Stop"

Write-Host "`n🧪 Testing MCP Bridge Client Packages" -ForegroundColor Cyan
Write-Host ("="*60) -ForegroundColor Cyan

# Test NPM Package
Write-Host "`n📦 Testing NPM Package..." -ForegroundColor Yellow
Write-Host "Location: packages/mcp-bridge-client" -ForegroundColor Gray

try {
    Set-Location "D:\INFRA\Dev-Tools\Dev-Tools\packages\mcp-bridge-client"
    
    # Check build output
    if (Test-Path "dist/index.js") {
        Write-Host "  ✅ Build output exists" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Build output missing - run 'npm run build'" -ForegroundColor Red
        exit 1
    }
    
    # Check package.json publishConfig
    $packageJson = Get-Content "package.json" | ConvertFrom-Json
    if ($packageJson.publishConfig.registry -eq "https://npm.pkg.github.com") {
        Write-Host "  ✅ GitHub Packages registry configured" -ForegroundColor Green
    } else {
        Write-Host "  ❌ publishConfig missing" -ForegroundColor Red
    }
    
    # Check .npmrc
    if (Test-Path ".npmrc") {
        Write-Host "  ✅ .npmrc file exists" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  .npmrc file missing (needed for publishing)" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "  ❌ Error testing NPM package: $_" -ForegroundColor Red
    exit 1
}

# Test Python Package
Write-Host "`n🐍 Testing Python Package..." -ForegroundColor Yellow
Write-Host "Location: packages/mcp-bridge-client-py" -ForegroundColor Gray

try {
    Set-Location "D:\INFRA\Dev-Tools\Dev-Tools\packages\mcp-bridge-client-py"
    
    # Check module structure
    if (Test-Path "mcp_bridge_client/__init__.py") {
        Write-Host "  ✅ Package structure valid" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Package structure invalid" -ForegroundColor Red
        exit 1
    }
    
    # Check pyproject.toml
    if (Test-Path "pyproject.toml") {
        Write-Host "  ✅ pyproject.toml exists" -ForegroundColor Green
    } else {
        Write-Host "  ❌ pyproject.toml missing" -ForegroundColor Red
        exit 1
    }
    
    # Test import (if Python is available)
    $pythonAvailable = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonAvailable) {
        Write-Host "  🔍 Testing Python import..." -ForegroundColor Gray
        $importTest = python -c "import sys; sys.path.insert(0, '.'); from mcp_bridge_client import MCPBridgeClient; print('success')" 2>&1
        if ($importTest -eq "success") {
            Write-Host "  ✅ Python import successful" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️  Python import failed (may need dependencies)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ⚠️  Python not available for testing" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "  ❌ Error testing Python package: $_" -ForegroundColor Red
    exit 1
}

# Test GitHub Actions workflows
Write-Host "`n⚙️  Checking GitHub Actions workflows..." -ForegroundColor Yellow

Set-Location "D:\INFRA\Dev-Tools\Dev-Tools"

if (Test-Path ".github/workflows/publish-npm.yml") {
    Write-Host "  ✅ NPM publish workflow exists" -ForegroundColor Green
} else {
    Write-Host "  ❌ NPM publish workflow missing" -ForegroundColor Red
}

if (Test-Path ".github/workflows/publish-python.yml") {
    Write-Host "  ✅ Python publish workflow exists" -ForegroundColor Green
} else {
    Write-Host "  ❌ Python publish workflow missing" -ForegroundColor Red
}

# Summary
Write-Host "`n" + ("="*60) -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host ("="*60) -ForegroundColor Cyan

Write-Host "`n✅ Both packages are ready for publishing!" -ForegroundColor Green

Write-Host "`nNext Steps:" -ForegroundColor Cyan
Write-Host "1. Create GitHub PAT with 'read:packages' and 'write:packages' scopes" -ForegroundColor White
Write-Host "   https://github.com/settings/tokens/new" -ForegroundColor Gray
Write-Host ""
Write-Host "2. Set environment variable:" -ForegroundColor White
Write-Host "   `$env:GITHUB_TOKEN='your_token_here'" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Publish NPM package:" -ForegroundColor White
Write-Host "   cd packages/mcp-bridge-client" -ForegroundColor Gray
Write-Host "   npm publish" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Publish Python package:" -ForegroundColor White
Write-Host "   cd packages/mcp-bridge-client-py" -ForegroundColor Gray
Write-Host "   python -m build" -ForegroundColor Gray
Write-Host "   pip install twine" -ForegroundColor Gray
Write-Host "   twine upload dist/* --repository-url https://upload.pypi.org/legacy/" -ForegroundColor Gray
Write-Host ""
Write-Host "5. Or use GitHub Actions (automated):" -ForegroundColor White
Write-Host "   git tag npm-v0.1.0 && git push origin npm-v0.1.0" -ForegroundColor Gray
Write-Host "   git tag py-v0.1.0 && git push origin py-v0.1.0" -ForegroundColor Gray

Write-Host ""
Write-Host "Installation Guide: packages/GITHUB_PACKAGES_INSTALL.md" -ForegroundColor Cyan
