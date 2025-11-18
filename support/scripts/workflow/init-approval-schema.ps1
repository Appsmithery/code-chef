#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Initialize HITL approval_requests table in PostgreSQL database.

.DESCRIPTION
    Applies the approval_requests.sql schema to the devtools database.
    Idempotent - safe to run multiple times.

.PARAMETER Host
    PostgreSQL host (default: localhost)

.PARAMETER Port
    PostgreSQL port (default: 5432)

.PARAMETER Database
    Database name (default: devtools)

.EXAMPLE
    .\init-approval-schema.ps1
    .\init-approval-schema.ps1 -Host postgres.example.com -Database production_db
#>

param(
    [string]$Host = "localhost",
    [int]$Port = 5432,
    [string]$Database = "devtools",
    [string]$User = "devtools",
    [string]$Password = $env:DB_PASSWORD
)

$ErrorActionPreference = "Stop"

# Resolve paths
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$SchemaFile = Join-Path $RepoRoot "config\state\approval_requests.sql"

Write-Host "=== HITL Schema Initialization ===" -ForegroundColor Cyan
Write-Host "Host:     $Host"
Write-Host "Port:     $Port"
Write-Host "Database: $Database"
Write-Host "Schema:   $SchemaFile"
Write-Host ""

# Check schema file exists
if (-not (Test-Path $SchemaFile)) {
    Write-Error "Schema file not found: $SchemaFile"
    exit 1
}

# Check password
if (-not $Password) {
    Write-Error "Database password not provided. Set DB_PASSWORD environment variable."
    exit 1
}

# Set PGPASSWORD for psql
$env:PGPASSWORD = $Password

try {
    # Test connection
    Write-Host "Testing database connection..." -ForegroundColor Yellow
    $testQuery = "SELECT version();"
    $result = psql -h $Host -p $Port -U $User -d $Database -t -A -c $testQuery 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to connect to database: $result"
        exit 1
    }
    
    Write-Host "Connected successfully." -ForegroundColor Green
    Write-Host ""
    
    # Apply schema
    Write-Host "Applying approval_requests schema..." -ForegroundColor Yellow
    psql -h $Host -p $Port -U $User -d $Database -f $SchemaFile
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to apply schema"
        exit 1
    }
    
    Write-Host ""
    Write-Host "Schema applied successfully." -ForegroundColor Green
    
    # Verify table exists
    Write-Host ""
    Write-Host "Verifying table structure..." -ForegroundColor Yellow
    $verifyQuery = @"
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns
WHERE table_name = 'approval_requests'
ORDER BY ordinal_position;
"@
    
    psql -h $Host -p $Port -U $User -d $Database -c $verifyQuery
    
    Write-Host ""
    Write-Host "=== Schema Initialization Complete ===" -ForegroundColor Green
    
} catch {
    Write-Error "Schema initialization failed: $_"
    exit 1
} finally {
    # Clear password from environment
    Remove-Item env:PGPASSWORD -ErrorAction SilentlyContinue
}
