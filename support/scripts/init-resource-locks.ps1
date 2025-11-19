#!/usr/bin/env pwsh
<#
.SYNOPSIS
Initialize resource locking infrastructure in PostgreSQL

.DESCRIPTION
Creates tables, functions, and views for distributed resource locking using PostgreSQL advisory locks.
Run this once to set up the resource locking infrastructure.

.EXAMPLE
.\init-resource-locks.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Paths
$RepoRoot = (Get-Item $PSScriptRoot).Parent.Parent.FullName
$SqlFile = Join-Path $RepoRoot "config\state\resource_locks.sql"

# Database connection from environment
$DbHost = if ($env:POSTGRES_HOST) { $env:POSTGRES_HOST } else { "localhost" }
$DbPort = if ($env:POSTGRES_PORT) { $env:POSTGRES_PORT } else { "5432" }
$DbName = if ($env:POSTGRES_DB) { $env:POSTGRES_DB } else { "devtools" }
$DbUser = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "devtools" }
$DbPass = if ($env:POSTGRES_PASSWORD) { $env:POSTGRES_PASSWORD } else { "changeme" }

Write-Host "Initializing Resource Locking Infrastructure..." -ForegroundColor Cyan
Write-Host "Database: $DbHost`:$DbPort/$DbName" -ForegroundColor Gray

# Check if SQL file exists
if (-not (Test-Path $SqlFile)) {
    Write-Error "SQL file not found: $SqlFile"
    exit 1
}

# Set PGPASSWORD environment variable for psql
$env:PGPASSWORD = $DbPass

try {
    # Execute SQL file
    Write-Host "Executing SQL schema..." -ForegroundColor Yellow
    
    $psqlArgs = @(
        "-h", $DbHost,
        "-p", $DbPort,
        "-U", $DbUser,
        "-d", $DbName,
        "-f", $SqlFile,
        "-v", "ON_ERROR_STOP=1"
    )
    
    $output = & psql @psqlArgs 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to execute SQL file: $output"
        exit 1
    }
    
    Write-Host "Schema initialized successfully" -ForegroundColor Green
    
    # Verify tables created
    Write-Host "`nVerifying tables..." -ForegroundColor Yellow
    
    $verifyQuery = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('resource_locks', 'lock_history', 'lock_wait_queue') ORDER BY table_name;"
    
    $tables = & psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -t -c $verifyQuery 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Tables created successfully" -ForegroundColor Green
        $tables -split "`n" | Where-Object { $_.Trim() } | ForEach-Object {
            Write-Host "  - $($_.Trim())" -ForegroundColor Gray
        }
    }
    
    # Verify functions created
    Write-Host "`nVerifying functions..." -ForegroundColor Yellow
    
    $verifyFuncsQuery = "SELECT routine_name FROM information_schema.routines WHERE routine_schema = 'public' AND routine_name LIKE '%lock%' ORDER BY routine_name;"
    
    $functions = & psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -t -c $verifyFuncsQuery 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Functions created successfully" -ForegroundColor Green
        $functions -split "`n" | Where-Object { $_.Trim() } | ForEach-Object {
            Write-Host "  - $($_.Trim())" -ForegroundColor Gray
        }
    }
    
    # Verify views created
    Write-Host "`nVerifying views..." -ForegroundColor Yellow
    
    $verifyViewsQuery = "SELECT table_name FROM information_schema.views WHERE table_schema = 'public' AND table_name LIKE '%lock%' ORDER BY table_name;"
    
    $views = & psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -t -c $verifyViewsQuery 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Views created successfully" -ForegroundColor Green
        $views -split "`n" | Where-Object { $_.Trim() } | ForEach-Object {
            Write-Host "  - $($_.Trim())" -ForegroundColor Gray
        }
    }
    
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Resource Locking Infrastructure Ready!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "1. Import ResourceLockManager in agent code"
    Write-Host "2. Use context manager for automatic lock handling:"
    Write-Host "   async with lock_mgr.lock('resource:id', 'agent-name'):"
    Write-Host "       # Protected operation"
    Write-Host "3. Monitor locks via PostgreSQL views or monitoring script"
    Write-Host ""
    
} catch {
    Write-Error "Failed to initialize resource locks: $_"
    exit 1
} finally {
    # Clean up PGPASSWORD
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}
