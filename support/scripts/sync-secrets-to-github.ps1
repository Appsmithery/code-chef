#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Sync environment secrets from local .env to GitHub Actions secrets

.DESCRIPTION
    Reads config/env/.env and uploads all sensitive credentials to GitHub Actions secrets.
    Uses GitHub CLI (gh) to set repository secrets securely.
    
    Prerequisites:
    - GitHub CLI installed: winget install GitHub.cli
    - Authenticated: gh auth login
    - Repository access: gh auth status

.PARAMETER DryRun
    Preview what would be synced without actually uploading

.PARAMETER Force
    Skip confirmation prompts

.PARAMETER Filter
    Only sync secrets matching this pattern (regex)

.EXAMPLE
    .\sync-secrets-to-github.ps1
    Interactive sync with confirmation

.EXAMPLE
    .\sync-secrets-to-github.ps1 -DryRun
    Preview what would be synced

.EXAMPLE
    .\sync-secrets-to-github.ps1 -Force -Filter "OAUTH2_PROXY"
    Sync only OAuth secrets without prompts
#>

[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$Force,
    [string]$Filter = ""
)

$ErrorActionPreference = "Stop"

# Configuration
$EnvFile = "$PSScriptRoot/../../config/env/.env"
$RepoOwner = "Appsmithery"
$RepoName = "code-chef"
$RepoFullName = "$RepoOwner/$RepoName"

# Secrets that should be synced to GitHub Actions
# Organized by category for clarity
$SecretKeys = @(
    # OAuth & Authentication
    "GITHUB_OAUTH_CLIENT_SECRET",
    "OAUTH2_PROXY_CLIENT_SECRET",
    "OAUTH2_PROXY_COOKIE_SECRET",
    
    # LLM Providers
    "CLAUDE_API_KEY",
    "MISTRAL_API_KEY",
    "PERPLEXITY_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    
    # DigitalOcean / Gradient
    "GRADIENT_API_KEY",
    "GRADIENT_MODEL_ACCESS_KEY",
    "DIGITAL_OCEAN_PAT",
    "DIGITALOCEAN_TOKEN",
    
    # LangSmith / Observability
    "LANGCHAIN_API_KEY",
    "LANGSMITH_API_KEY",
    "LANGSMITH_WORKSPACE_ID",
    "LANGGRAPH_API_KEY",
    
    # Linear Integration
    "LINEAR_API_KEY",
    "LINEAR_OAUTH_DEV_TOKEN",
    "LINEAR_WEBHOOK_SIGNING_SECRET",
    "LINEAR_TEAM_ID",
    
    # RAG / Vector Database
    "QDRANT_URL",
    "QDRANT_API_KEY",
    
    # Database
    "DB_PASSWORD",
    "POSTGRES_PASSWORD",
    
    # Orchestrator
    "ORCHESTRATOR_API_KEY",
    
    # Grafana Cloud
    "GRAFANA_CLOUD_API_TOKEN",
    "GRAFANA_API_KEY",
    
    # Supabase
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_TOKEN",
    
    # HuggingFace
    "HUGGINGFACE_TOKEN",
    
    # Docker Hub
    "DOCKER_PAT",
    "DOCKER_USERNAME",
    
    # GitHub
    "GITHUB_TOKEN"
)

# ============================================================================
# Helper Functions
# ============================================================================

function Write-Header {
    param([string]$Text)
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host " $Text" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Text)
    Write-Host "✓ $Text" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Text)
    Write-Host "⚠ $Text" -ForegroundColor Yellow
}

function Write-Info {
    param([string]$Text)
    Write-Host "ℹ $Text" -ForegroundColor Blue
}

function Test-GitHubCLI {
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        Write-Host "❌ GitHub CLI not found!" -ForegroundColor Red
        Write-Host "`nInstall with: winget install GitHub.cli" -ForegroundColor Yellow
        Write-Host "Then authenticate: gh auth login`n" -ForegroundColor Yellow
        exit 1
    }
    
    # Check authentication
    $authStatus = gh auth status 2>&1 | Out-String
    if ($authStatus -notmatch "Logged in to github.com") {
        Write-Host "❌ Not authenticated with GitHub!" -ForegroundColor Red
        Write-Host "`nRun: gh auth login`n" -ForegroundColor Yellow
        exit 1
    }
    
    Write-Success "GitHub CLI authenticated"
}

function Read-EnvFile {
    param([string]$Path)
    
    if (-not (Test-Path $Path)) {
        Write-Host "❌ .env file not found: $Path" -ForegroundColor Red
        exit 1
    }
    
    $secrets = @{}
    $content = Get-Content $Path -Raw
    
    # Parse .env file (handle comments, empty lines, quotes)
    $content -split "`n" | ForEach-Object {
        $line = $_.Trim()
        
        # Skip comments and empty lines
        if ($line -match "^#" -or $line -eq "") {
            return
        }
        
        # Parse KEY=VALUE
        if ($line -match "^([A-Z_][A-Z0-9_]*)=(.*)$") {
            $key = $matches[1]
            $value = $matches[2].Trim()
            
            # Remove quotes if present
            if ($value -match '^"(.*)"$' -or $value -match "^'(.*)'$") {
                $value = $matches[1]
            }
            
            # Only store non-empty values
            if ($value -ne "") {
                $secrets[$key] = $value
            }
        }
    }
    
    Write-Success "Parsed $($secrets.Count) environment variables from .env"
    return $secrets
}

function Get-SecretPreview {
    param([string]$Value)
    
    if ($Value.Length -le 10) {
        return "*" * $Value.Length
    }
    
    $start = $Value.Substring(0, 4)
    $end = $Value.Substring($Value.Length - 4, 4)
    $middle = "*" * [Math]::Min(20, $Value.Length - 8)
    
    return "$start$middle$end"
}

function Set-GitHubSecret {
    param(
        [string]$Key,
        [string]$Value,
        [string]$Repo
    )
    
    # Use gh secret set with stdin
    $Value | gh secret set $Key --repo $Repo
    
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to set secret $Key"
    }
}

# ============================================================================
# Main Script
# ============================================================================

Write-Header "GitHub Actions Secret Sync"

# Validate prerequisites
Test-GitHubCLI

# Read local .env file
Write-Info "Reading secrets from: $EnvFile"
$allSecrets = Read-EnvFile -Path $EnvFile

# Filter secrets to sync
$secretsToSync = @{}
foreach ($key in $SecretKeys) {
    if ($Filter -ne "" -and $key -notmatch $Filter) {
        continue
    }
    
    if ($allSecrets.ContainsKey($key)) {
        $secretsToSync[$key] = $allSecrets[$key]
    }
    else {
        Write-Warning "Secret $key not found in .env file"
    }
}

Write-Info "Found $($secretsToSync.Count) secrets to sync"

if ($secretsToSync.Count -eq 0) {
    Write-Warning "No secrets to sync!"
    exit 0
}

# Display summary
Write-Host "`nSecrets to sync:" -ForegroundColor Cyan
$secretsToSync.Keys | Sort-Object | ForEach-Object {
    $preview = Get-SecretPreview -Value $secretsToSync[$_]
    Write-Host "  • $_ = $preview" -ForegroundColor Gray
}

# Confirmation
if (-not $DryRun -and -not $Force) {
    Write-Host "`n⚠️  This will update secrets in: $RepoFullName" -ForegroundColor Yellow
    $confirm = Read-Host "`nContinue? (y/N)"
    if ($confirm -ne "y" -and $confirm -ne "Y") {
        Write-Info "Cancelled by user"
        exit 0
    }
}

# Sync secrets
if ($DryRun) {
    Write-Info "DRY RUN - No secrets will be uploaded"
    exit 0
}

Write-Header "Syncing Secrets"

$successCount = 0
$failureCount = 0

foreach ($key in $secretsToSync.Keys | Sort-Object) {
    try {
        Write-Host "Uploading $key... " -NoNewline
        Set-GitHubSecret -Key $key -Value $secretsToSync[$key] -Repo $RepoFullName
        Write-Host "✓" -ForegroundColor Green
        $successCount++
    }
    catch {
        Write-Host "✗" -ForegroundColor Red
        Write-Warning "Failed: $_"
        $failureCount++
    }
}

# Summary
Write-Header "Sync Complete"
Write-Success "$successCount secrets uploaded successfully"

if ($failureCount -gt 0) {
    Write-Warning "$failureCount secrets failed to upload"
    exit 1
}

$settingsUrl = "https://github.com/$RepoFullName/settings/secrets/actions"
Write-Host ""
Write-Host "Secrets are now available in GitHub Actions workflows." -ForegroundColor Green
Write-Host "View at: $settingsUrl" -ForegroundColor Blue
Write-Host ""
