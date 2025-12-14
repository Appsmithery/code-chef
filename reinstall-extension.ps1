#!/usr/bin/env pwsh
# Clean reinstall of code/chef extension

Write-Host "🧹 Cleaning up old extension versions..." -ForegroundColor Yellow

# Kill all VS Code processes
Write-Host "Closing VS Code..." -ForegroundColor Cyan
Get-Process Code -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

# Remove all installed versions
Write-Host "Removing old versions..." -ForegroundColor Cyan
Remove-Item -Path "$env:USERPROFILE\.vscode\extensions\appsmithery.vscode-codechef-*" -Recurse -Force -ErrorAction SilentlyContinue

# Install v1.0.3
Write-Host "📦 Installing v1.0.3..." -ForegroundColor Green
code --install-extension "d:\APPS\code-chef\extensions\vscode-codechef\vscode-codechef-1.0.3.vsix" --force

# Wait for installation
Start-Sleep -Seconds 2

# Verify installation
Write-Host "✅ Verifying installation..." -ForegroundColor Green
$installed = code --list-extensions | Select-String "vscode-codechef"
if ($installed) {
    Write-Host "✅ Extension installed: $installed" -ForegroundColor Green
    Write-Host "`n🚀 Opening VS Code..." -ForegroundColor Cyan
    code
}
else {
    Write-Host "❌ Installation failed!" -ForegroundColor Red
    exit 1
}

Write-Host "`n✅ Done! After VS Code opens:" -ForegroundColor Green
Write-Host "1. Open Copilot Chat (Ctrl+Alt+I)" -ForegroundColor Cyan
Write-Host "2. Type: @chef hello" -ForegroundColor Cyan
Write-Host "3. Verify the chat participant is working" -ForegroundColor Cyan
