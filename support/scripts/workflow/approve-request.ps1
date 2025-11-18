#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Approve a pending approval request.

.DESCRIPTION
    Updates approval_requests table to mark request as approved.
    Records approver ID, role, timestamp, and optional justification.

.PARAMETER RequestId
    UUID of approval request to approve (required)

.PARAMETER ApproverId
    User ID of approver (default: current Windows username)

.PARAMETER ApproverRole
    Role of approver - developer, tech_lead, devops_engineer (default: tech_lead)

.PARAMETER Justification
    Optional justification text for approval

.EXAMPLE
    .\approve-request.ps1 -RequestId abc-123-def-456
    .\approve-request.ps1 -RequestId abc-123 -ApproverRole devops_engineer -Justification "Reviewed infrastructure changes"
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$RequestId,
    
    [string]$ApproverId = $env:USERNAME,
    [string]$ApproverRole = "tech_lead",
    [string]$Justification = $null,
    
    [string]$Host = "localhost",
    [int]$Port = 5432,
    [string]$Database = "devtools",
    [string]$User = "devtools",
    [string]$Password = $env:DB_PASSWORD
)

$ErrorActionPreference = "Stop"

Write-Host "=== Approve Request ===" -ForegroundColor Cyan
Write-Host "Request ID: $RequestId"
Write-Host "Approver:   $ApproverId ($ApproverRole)"
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
    status,
    expires_at
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
    $expiresAt = $fields[4]
    
    Write-Host "Risk Level:   $riskLevel" -ForegroundColor $(if ($riskLevel -eq "critical") { "Red" } elseif ($riskLevel -eq "high") { "Yellow" } else { "White" })
    Write-Host "Task:         $taskDesc"
    Write-Host "Agent:        $agentName"
    Write-Host "Status:       $status"
    Write-Host "Expires:      $expiresAt"
    Write-Host ""
    
    # Check if already processed
    if ($status -ne "pending") {
        Write-Error "Request is not pending (status: $status)"
        exit 1
    }
    
    # Update request
    $justificationParam = if ($Justification) { "'$Justification'" } else { "NULL" }
    
    $updateQuery = @"
UPDATE approval_requests
SET status = 'approved',
    approver_id = '$ApproverId',
    approver_role = '$ApproverRole',
    approved_at = NOW(),
    approval_justification = $justificationParam,
    updated_at = NOW()
WHERE id = '$RequestId' AND status = 'pending'
RETURNING id;
"@

    Write-Host "Approving request..." -ForegroundColor Green
    $updateResult = psql -h $Host -p $Port -U $User -d $Database -t -A -c $updateQuery 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to approve: $updateResult"
        exit 1
    }
    
    if (-not $updateResult) {
        Write-Error "Request was not updated (may have been processed by another user)"
        exit 1
    }
    
    Write-Host ""
    Write-Host "Request approved successfully." -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host "  - Workflow will resume automatically on next check"
    Write-Host "  - Agent '$agentName' will receive approval notification"
    Write-Host "  - Check workflow status: task workflow:status WORKFLOW_ID=<id>"
    
} catch {
    Write-Error "Approval failed: $_"
    exit 1
} finally {
    Remove-Item env:PGPASSWORD -ErrorAction SilentlyContinue
}
