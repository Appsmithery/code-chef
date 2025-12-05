<#
.SYNOPSIS
    Build and install vscode-codechef extension across all VS Code windows.

.DESCRIPTION
    Compiles, packages, and installs the extension. All open VS Code windows
    will pick up the update after reload.

.PARAMETER Release
    If specified, bumps version and creates a git tag.

.PARAMETER BumpType
    Version bump type: patch, minor, major. Default: patch.

.EXAMPLE
    .\install-extension.ps1
    # Builds and installs current version

.EXAMPLE
    .\install-extension.ps1 -Release -BumpType minor
    # Bumps minor version, builds, installs, and tags
#>

param(
    [switch]$Release,
    [ValidateSet('patch', 'minor', 'major')]
    [string]$BumpType = 'patch'
)

$ErrorActionPreference = "Stop"
$ExtensionDir = "$PSScriptRoot\..\..\extensions\vscode-codechef"

Push-Location $ExtensionDir

try {
    Write-Host "Building vscode-codechef extension..." -ForegroundColor Cyan

    # Bump version if releasing
    if ($Release) {
        Write-Host "Bumping $BumpType version..." -ForegroundColor Yellow
        npm version $BumpType --no-git-tag-version
    }

    # Get current version
    $PackageJson = Get-Content package.json | ConvertFrom-Json
    $Version = $PackageJson.version
    Write-Host "Version: $Version" -ForegroundColor Green

    # Compile TypeScript
    Write-Host "Compiling TypeScript..." -ForegroundColor Cyan
    npm run compile
    if ($LASTEXITCODE -ne 0) { throw "Compilation failed" }

    # Package VSIX
    Write-Host "Packaging VSIX..." -ForegroundColor Cyan
    npx vsce package --no-update-package-json
    if ($LASTEXITCODE -ne 0) { throw "Packaging failed" }

    $VsixFile = "vscode-codechef-$Version.vsix"

    # Install extension
    Write-Host "Installing extension..." -ForegroundColor Cyan
    code --install-extension $VsixFile --force
    if ($LASTEXITCODE -ne 0) { throw "Installation failed" }

    # Git operations for release
    if ($Release) {
        Write-Host "Committing and tagging..." -ForegroundColor Yellow
        git add package.json
        git commit -m "chore(extension): bump version to $Version"
        git tag -a "extension-v$Version" -m "VS Code Extension v$Version"
        
        Write-Host "Push with: git push origin main --tags" -ForegroundColor Magenta
    }

    Write-Host ""
    Write-Host "Extension v$Version installed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "   1. Reload all VS Code windows: Ctrl+Shift+P -> Developer: Reload Window"
    Write-Host "   2. Or restart VS Code entirely"
    Write-Host ""
    
    if (-not $Release) {
        Write-Host "To release: .\install-extension.ps1 -Release -BumpType patch" -ForegroundColor DarkGray
    }
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
    exit 1
}
finally {
    Pop-Location
}
