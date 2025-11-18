#!/usr/bin/env pwsh
<#
.SYNOPSIS
    List pending approval requests from PostgreSQL database.

.DESCRIPTION
    Queries approval_requests table for all pending requests that haven't expired.
    Displays in formatted table with risk level, agent, description, and expiration.

.PARAMETER Host
    PostgreSQL host (default: localhost)

.PARAMETER Role
    Filter by approver role (optional)

.EXAMPLE
    .\list-pending-approvals.ps1
    .\list-pending-approvals.ps1 -Role tech_lead
#>

param(
    [string]$Host = "localhost",
    [int]$Port = 5432,
    [string]$Database = "devtools",
    [string]$User = "devtools",
    [string]$Password = $env:DB_PASSWORD,
    [string]$Role = $null
)

$ErrorActionPreference = "Stop"

Write-Host "=== Pending Approval Requests ===" -ForegroundColor Cyan
Write-Host ""

# Check password
if (-not $Password) {
    Write-Error "Database password not provided. Set DB_PASSWORD environment variable."
    exit 1
}

# Set PGPASSWORD for psql
$env:PGPASSWORD = $Password

try {
    $query = @"
SELECT 
    id,
    LEFT(workflow_id, 20) as workflow,
    agent_name,
    risk_level,
    LEFT(task_description, 40) as description,
    TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI') as created,
    TO_CHAR(expires_at, 'YYYY-MM-DD HH24:MI') as expires,
    EXTRACT(EPOCH FROM (expires_at - NOW())) / 60 as minutes_remaining
FROM approval_requests
WHERE status = 'pending' 
  AND expires_at > NOW()
ORDER BY risk_level DESC, created_at ASC;
"@

    Write-Host "Querying database..." -ForegroundColor Yellow
    
    $result = psql -h $Host -p $Port -U $User -d $Database -c $query 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Query failed: $result"
        exit 1
    }
    
    Write-Host $result
    
    Write-Host ""
    Write-Host "Legend:" -ForegroundColor Cyan
    Write-Host "  critical → Requires devops-engineer approval"
    Write-Host "  high     → Requires tech-lead or devops-engineer"
    Write-Host "  medium   → Requires tech-lead or higher"
    Write-Host "  low      → Auto-approved (shouldn't appear here)"
    Write-Host ""
    Write-Host "To approve: task workflow:approve REQUEST_ID=<id>" -ForegroundColor Green
    Write-Host "To reject:  task workflow:reject REQUEST_ID=<id> REASON=\"...\"" -ForegroundColor Yellow
    
} catch {
    Write-Error "Failed to list approvals: $_"
    exit 1
} finally {
    Remove-Item env:PGPASSWORD -ErrorAction SilentlyContinue
}
