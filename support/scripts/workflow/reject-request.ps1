#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Reject a pending approval request.

.DESCRIPTION
    Updates approval_requests table to mark request as rejected.
    Records rejector ID, reason, and timestamp.

.PARAMETER RequestId
    UUID of approval request to reject (required)

.PARAMETER Reason
    Reason for rejection (required)

.PARAMETER RejectorId
    User ID of person rejecting (default: current Windows username)

.EXAMPLE
    .\reject-request.ps1 -RequestId abc-123 -Reason "Security concerns with database access"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$RequestId,
    
    [Parameter(Mandatory=$true)]
    [string]$Reason,
    
    [string]$RejectorId = $env:USERNAME,
    
    [string]$Host = "localhost",
    [int]$Port = 5432,
    [string]$Database = "devtools",
    [string]$User = "devtools",
    [string]$Password = $env:DB_PASSWORD
)

$ErrorActionPreference = "Stop"

Write-Host "=== Reject Request ===" -ForegroundColor Yellow
Write-Host "Request ID: $RequestId"
Write-Host "Rejector:   $RejectorId"
Write-Host "Reason:     $Reason"
Write-Host ""

# Check password
if (-not $Password) {
    Write-Error "Database password not provided. Set DB_PASSWORD environment variable."
    exit 1
}

# Set PGPASSWORD for psql
$env:PGPASSWORD = $Password

try {
    # Get request details
    $detailsQuery = @"
SELECT 
    risk_level,
    task_description,
    agent_name,
    status
FROM approval_requests
WHERE id = '$RequestId';
"@

    Write-Host "Fetching request details..." -ForegroundColor Yellow
    $details = psql -h $Host -p $Port -U $User -d $Database -t -A -c $detailsQuery 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Request not found: $details"
        exit 1
    }
    
    $fields = $details -split '\|'
    $riskLevel = $fields[0]
    $taskDesc = $fields[1]
    $agentName = $fields[2]
    $status = $fields[3]
    
    Write-Host "Risk Level:   $riskLevel"
    Write-Host "Task:         $taskDesc"
    Write-Host "Agent:        $agentName"
    Write-Host "Status:       $status"
    Write-Host ""
    
    # Check if already processed
    if ($status -ne "pending") {
        Write-Error "Request is not pending (status: $status)"
        exit 1
    }
    
    # Escape reason for SQL
    $escapedReason = $Reason -replace "'", "''"
    
    # Update request
    $updateQuery = @"
UPDATE approval_requests
SET status = 'rejected',
    approver_id = '$RejectorId',
    rejected_at = NOW(),
    rejection_reason = '$escapedReason',
    updated_at = NOW()
WHERE id = '$RequestId' AND status = 'pending'
RETURNING id;
"@

    Write-Host "Rejecting request..." -ForegroundColor Yellow
    $updateResult = psql -h $Host -p $Port -U $User -d $Database -t -A -c $updateQuery 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to reject: $updateResult"
        exit 1
    }
    
    if (-not $updateResult) {
        Write-Error "Request was not updated (may have been processed by another user)"
        exit 1
    }
    
    Write-Host ""
    Write-Host "Request rejected." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host "  - Workflow will be terminated"
    Write-Host "  - Agent '$agentName' will receive rejection notification"
    Write-Host "  - Reason will be logged for audit trail"
    
} catch {
    Write-Error "Rejection failed: $_"
    exit 1
} finally {
    Remove-Item env:PGPASSWORD -ErrorAction SilentlyContinue
}
