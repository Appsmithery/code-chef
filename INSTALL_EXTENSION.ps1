#!/usr/bin/env pwsh
# code-chef Extension Installation Script
# Run this after closing ALL VS Code windows

Write-Host "`n=== code/chef Extension Installer ===" -ForegroundColor Cyan
Write-Host "This script will cleanly install the extension`n"

# Check if VS Code is running
$vscode = Get-Process -Name "Code" -ErrorAction SilentlyContinue
if ($vscode) {
    Write-Host "ERROR: VS Code is still running!" -ForegroundColor Red
    Write-Host "Please close ALL VS Code windows and run this script again.`n"
    exit 1
}

Write-Host "Step 1: Cleaning old installations..." -ForegroundColor Yellow
$extDir = "$env:USERPROFILE\.vscode\extensions"
Get-ChildItem $extDir -Directory | Where-Object { $_.Name -like "*codechef*" } | ForEach-Object {
    Write-Host "  Removing: $($_.Name)"
    Remove-Item $_.FullName -Recurse -Force
}

Write-Host "`nStep 2: Installing v1.0.4..." -ForegroundColor Yellow
$vsixPath = "d:\APPS\code-chef\extensions\vscode-codechef\vscode-codechef-1.0.4.vsix"
if (-not (Test-Path $vsixPath)) {
    Write-Host "ERROR: VSIX file not found at $vsixPath" -ForegroundColor Red
    exit 1
}

code --install-extension $vsixPath --force

Write-Host "`nStep 3: Verifying..." -ForegroundColor Yellow
Start-Sleep -Seconds 2
$installed = Get-ChildItem $extDir -Directory | Where-Object { $_.Name -like "*codechef*" }

if ($installed) {
    Write-Host "`nSUCCESS! Extension installed: $($installed.Name)" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Cyan
    Write-Host "1. Open VS Code"
    Write-Host "2. The extension should activate automatically"
    Write-Host "3. Open Copilot Chat and type: @chef hello"
    Write-Host ""
}
else {
    Write-Host "`nERROR: Installation failed!" -ForegroundColor Red
    Write-Host "Try running: code --install-extension $vsixPath --force" -ForegroundColor Yellow
}
