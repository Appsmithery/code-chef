<#
.SYNOPSIS
    Validates environment configuration before deployment
.DESCRIPTION
    Checks .env file for required variables, placeholder values, and secrets files
.PARAMETER EnvPath
    Path to .env file (default: config/env/.env)
.PARAMETER Strict
    Enable strict mode - fail on warnings
#>

param(
    [string]$EnvPath = "config/env/.env",
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
$script:ErrorCount = 0
$script:WarningCount = 0

function Write-ValidationError {
    param([string]$Message)
    Write-Host "ERROR: $Message" -ForegroundColor Red
    $script:ErrorCount++
}

function Write-ValidationWarning {
    param([string]$Message)
    Write-Host "WARNING: $Message" -ForegroundColor Yellow
    $script:WarningCount++
    if ($Strict) { $script:ErrorCount++ }
}

function Write-ValidationSuccess {
    param([string]$Message)
    Write-Host "OK: $Message" -ForegroundColor Green
}

function Write-ValidationInfo {
    param([string]$Message)
    Write-Host "INFO: $Message" -ForegroundColor Cyan
}

# Resolve paths
$RepoRoot = (Get-Item $PSScriptRoot).Parent.Parent.Parent.FullName
$EnvFilePath = Join-Path $RepoRoot $EnvPath
$SecretsDir = Join-Path $RepoRoot "config/env/secrets"

Write-Host "`nDev-Tools Environment Validation`n" -ForegroundColor Cyan

# Check if .env file exists
if (-not (Test-Path $EnvFilePath)) {
    Write-ValidationError ".env file not found at: $EnvFilePath"
    Write-Host "`nCopy from template: config/env/.env.template`n" -ForegroundColor Yellow
    exit 1
}

Write-ValidationSuccess "Found .env file: $EnvFilePath"

# Parse .env file
$EnvVars = @{}
$LineNumber = 0
Get-Content $EnvFilePath | ForEach-Object {
    $LineNumber++
    $line = $_.Trim()
    
    # Skip comments and empty lines
    if ($line -match '^\s*#' -or $line -eq '') { return }
    
    # Parse KEY=VALUE
    if ($line -match '^([^=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        
        # Remove quotes
        $value = $value -replace '^["'']|["'']$', ''
        
        $EnvVars[$key] = @{
            Value = $value
            Line = $LineNumber
        }
    }
}

Write-ValidationInfo "Parsed $($EnvVars.Count) environment variables"

# Define required variables by category
$RequiredVars = @{
    "Core" = @(
        "DOCKER_USERNAME",
        "IMAGE_TAG"
    )
    "Gradient AI" = @(
        "GRADIENT_API_KEY",
        "GRADIENT_BASE_URL"
    )
    "LangSmith" = @(
        "LANGCHAIN_API_KEY",
        "LANGCHAIN_PROJECT",
        "LANGCHAIN_TRACING_V2"
    )
    "Linear" = @(
        "LINEAR_API_KEY",
        "LINEAR_TEAM_ID",
        "LINEAR_APPROVAL_HUB_ISSUE_ID"
    )
    "Database" = @(
        "POSTGRES_PASSWORD",
        "DB_PASSWORD"
    )
}

# Placeholder patterns to detect
$PlaceholderPatterns = @(
    'placeholder',
    'changeme',
    'your-.*-here',
    'replace-this',
    'TODO',
    'FIXME',
    'xxx+',
    'example\.com'
)

Write-Host "`nChecking Required Variables...`n" -ForegroundColor Cyan

foreach ($category in $RequiredVars.Keys) {
    Write-Host "$category Configuration:" -ForegroundColor White
    
    foreach ($varName in $RequiredVars[$category]) {
        if (-not $EnvVars.ContainsKey($varName)) {
            Write-ValidationError "Missing required variable: $varName"
            continue
        }
        
        $value = $EnvVars[$varName].Value
        
        if ([string]::IsNullOrWhiteSpace($value)) {
            Write-ValidationError "$varName is empty"
            continue
        }
        
        # Check for placeholder values
        $isPlaceholder = $false
        foreach ($pattern in $PlaceholderPatterns) {
            if ($value -match $pattern) {
                Write-ValidationError "$varName contains placeholder value"
                $isPlaceholder = $true
                break
            }
        }
        
        if (-not $isPlaceholder) {
            $maskedValue = if ($varName -match 'PASSWORD|SECRET|KEY|TOKEN') {
                "***"
            } else {
                $value
            }
            Write-ValidationSuccess "$varName = $maskedValue"
        }
    }
    Write-Host ""
}

Write-Host "Checking Secrets Files...`n" -ForegroundColor Cyan

$RequiredSecrets = @(
    "db_password.txt",
    "linear_oauth_token.txt",
    "linear_webhook_secret.txt"
)

if (-not (Test-Path $SecretsDir)) {
    Write-ValidationError "Secrets directory not found: $SecretsDir"
} else {
    foreach ($secretFile in $RequiredSecrets) {
        $secretPath = Join-Path $SecretsDir $secretFile
        if (-not (Test-Path $secretPath)) {
            Write-ValidationError "Missing secret file: $secretFile"
        } else {
            $content = Get-Content $secretPath -Raw
            if ([string]::IsNullOrWhiteSpace($content)) {
                Write-ValidationError "Secret file is empty: $secretFile"
            } elseif ($content.Length -lt 8) {
                Write-ValidationWarning "Secret file suspiciously short: $secretFile"
            } else {
                Write-ValidationSuccess "Secret file exists: $secretFile"
            }
        }
    }
}

# Summary
Write-Host "`nValidation Summary`n" -ForegroundColor Cyan

if ($script:ErrorCount -eq 0 -and $script:WarningCount -eq 0) {
    Write-Host "All checks passed! Environment is ready for deployment.`n" -ForegroundColor Green
    exit 0
} elseif ($script:ErrorCount -eq 0) {
    Write-Host "Validation passed with $script:WarningCount warning(s).`n" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "Validation failed with $script:ErrorCount error(s) and $script:WarningCount warning(s).`n" -ForegroundColor Red
    exit 1
}
