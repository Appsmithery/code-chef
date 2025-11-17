#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Main orchestrator for repository reorganization

.DESCRIPTION
    Coordinates the migration from artifact-based to agent-centric organization.
    Runs all migration scripts in correct order with validation at each step.

.PARAMETER DryRun
    Show what would be done without making changes

.PARAMETER SkipBackup
    Skip creating backup (not recommended)

.EXAMPLE
    .\migrate-structure.ps1 -DryRun
    Preview changes without executing

.EXAMPLE
    .\migrate-structure.ps1
    Execute full migration
#>

param(
    [switch]$DryRun,
    [switch]$SkipBackup
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir

# Colors
function Write-Step { param($msg) Write-Host "`n[STEP] $msg" -ForegroundColor Cyan }
function Write-Success { param($msg) Write-Host "  ✓ $msg" -ForegroundColor Green }
function Write-Warning-Custom { param($msg) Write-Host "  ! $msg" -ForegroundColor Yellow }
function Write-Error-Custom { param($msg) Write-Host "  ✗ $msg" -ForegroundColor Red }

Write-Host "`n╔════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Dev-Tools Repository Reorganization      ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Cyan

if ($DryRun) {
    Write-Warning-Custom "DRY RUN MODE - No changes will be made"
}

# Step 0: Pre-flight checks
Write-Step "Pre-flight Checks"

# Check we're in repo root
if (!(Test-Path "$RepoRoot/.git")) {
    Write-Error-Custom "Not in git repository root!"
    exit 1
}
Write-Success "Git repository detected"

# Check for uncommitted changes
$gitStatus = git status --porcelain
if ($gitStatus -and !$DryRun) {
    Write-Warning-Custom "Uncommitted changes detected. Commit or stash before migration."
    $response = Read-Host "Continue anyway? (y/N)"
    if ($response -ne 'y') {
        exit 1
    }
}

# Check Docker is running
try {
    docker ps > $null 2>&1
    Write-Success "Docker is running"
} catch {
    Write-Error-Custom "Docker is not running. Start Docker Desktop first."
    exit 1
}

# Step 1: Create backup
if (!$SkipBackup -and !$DryRun) {
    Write-Step "Creating Backup"
    $backupDir = "$RepoRoot/backups/pre-reorganization-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
    
    @('agents', 'containers', 'mcp', 'compose', 'config', '.github/workflows') | ForEach-Object {
        if (Test-Path "$RepoRoot/$_") {
            Copy-Item -Path "$RepoRoot/$_" -Destination "$backupDir/" -Recurse -Force
        }
    }
    Write-Success "Backup created: $backupDir"
}

# Step 2: Create new directory structure
Write-Step "Creating New Directory Structure"
& "$ScriptDir/create-agent-dirs.ps1" -DryRun:$DryRun
if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Failed to create directory structure"
    exit 1
}

# Step 3: Move agent files
Write-Step "Moving Agent Files"
& "$ScriptDir/move-agent-files.ps1" -DryRun:$DryRun
if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Failed to move agent files"
    exit 1
}

# Step 4: Update Dockerfiles
Write-Step "Updating Dockerfiles"
& "$ScriptDir/update-dockerfiles.ps1" -DryRun:$DryRun
if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Failed to update Dockerfiles"
    exit 1
}

# Step 5: Update docker-compose.yml
Write-Step "Updating Docker Compose Configuration"
& "$ScriptDir/update-compose.ps1" -DryRun:$DryRun
if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Failed to update compose file"
    exit 1
}

# Step 6: Update workflows
Write-Step "Updating CI/CD Workflows"
& "$ScriptDir/update-workflows.ps1" -DryRun:$DryRun
if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Failed to update workflows"
    exit 1
}

# Step 7: Cleanup old structure
Write-Step "Cleaning Up Old Structure"
& "$ScriptDir/cleanup-old-structure.ps1" -DryRun:$DryRun
if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Failed cleanup"
    exit 1
}

# Step 8: Validation
Write-Step "Validating Migration"
& "$ScriptDir/validate-migration.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Validation failed!"
    exit 1
}

# Summary
Write-Host "`n╔════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  Migration Complete!                       ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════╝" -ForegroundColor Green

if (!$DryRun) {
    Write-Host "`nNext Steps:" -ForegroundColor Yellow
    Write-Host "1. Review changes: git status" -ForegroundColor Gray
    Write-Host "2. Test locally: cd infrastructure/compose && docker compose up" -ForegroundColor Gray
    Write-Host "3. Commit changes: git add -A && git commit -m 'refactor: reorganize to agent-centric structure'" -ForegroundColor Gray
    Write-Host "4. Push & validate CI/CD: git push origin main" -ForegroundColor Gray
    Write-Host "`nBackup location: backups/pre-reorganization-*`n" -ForegroundColor Cyan
} else {
    Write-Host "`nDry run complete. Run without -DryRun to execute migration.`n" -ForegroundColor Yellow
}
