#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Clean up expired approval requests.

.DESCRIPTION
    Marks all expired approval requests (status=pending, expires_at < NOW)
    as expired. Runs as maintenance task to keep database clean.

.EXAMPLE
    .\clean-expired-approvals.ps1
#>

param(
    [string]$Host = "localhost",
    [int]$Port = 5432,
    [string]$Database = "devtools",
    [string]$User = "devtools",
    [string]$Password = $env:DB_PASSWORD
)

$ErrorActionPreference = "Stop"

Write-Host "=== Clean Expired Approvals ===" -ForegroundColor Cyan
Write-Host ""

# Check password
if (-not $Password) {
    Write-Error "Database password not provided. Set DB_PASSWORD environment variable."
    exit 1
}

# Set PGPASSWORD for psql
$env:PGPASSWORD = $Password

try {
    # Find expired requests
    $findQuery = @"
SELECT 
    id,
    LEFT(workflow_id, 20) as workflow,
    agent_name,
    LEFT(task_description, 30) as task,
    TO_CHAR(expires_at, 'YYYY-MM-DD HH24:MI') as expired_at
FROM approval_requests
WHERE status = 'pending' AND expires_at < NOW()
ORDER BY expires_at DESC
LIMIT 20;
"@

    Write-Host "Finding expired requests..." -ForegroundColor Yellow
    $expiredList = psql -h $Host -p $Port -U $User -d $Database -c $findQuery 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Query failed: $expiredList"
        exit 1
    }
    
    Write-Host $expiredList
    Write-Host ""
    
    # Update expired requests
    $updateQuery = @"
UPDATE approval_requests
SET status = 'expired',
    updated_at = NOW()
WHERE status = 'pending' AND expires_at < NOW()
RETURNING id;
"@

    Write-Host "Marking as expired..." -ForegroundColor Yellow
    $updateResult = psql -h $Host -p $Port -U $User -d $Database -t -A -c $updateQuery 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Update failed: $updateResult"
        exit 1
    }
    
    $expiredIds = $updateResult -split "`n" | Where-Object { $_ -ne "" }
    $expiredCount = $expiredIds.Count
    
    if ($expiredCount -eq 0) {
        Write-Host "No expired requests found." -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "Marked $expiredCount request(s) as expired." -ForegroundColor Green
        Write-Host ""
        Write-Host "Impact:" -ForegroundColor Cyan
        Write-Host "  - Workflows for these requests will be terminated"
        Write-Host "  - Agents will need to re-submit tasks"
        Write-Host "  - Audit trail preserved in database"
    }
    
} catch {
    Write-Error "Cleanup failed: $_"
    exit 1
} finally {
    Remove-Item env:PGPASSWORD -ErrorAction SilentlyContinue
}
