Write-Host 'Closing VS Code...'
Get-Process Code -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

Write-Host 'Removing old versions...'
Remove-Item -Path "$env:USERPROFILE\.vscode\extensions\appsmithery.vscode-codechef-*" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host 'Installing v1.0.10...'
code --install-extension 'd:\APPS\code-chef\extensions\vscode-codechef\vscode-codechef-1.0.10.vsix' --force
Start-Sleep -Seconds 2

Write-Host 'Verifying...'
code --list-extensions | Select-String 'vscode-codechef'

Write-Host 'Opening VS Code...'
code
