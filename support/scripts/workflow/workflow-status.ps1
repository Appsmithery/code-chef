#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Show detailed status of a workflow.

.DESCRIPTION
    Queries approval_requests and displays all approval requests associated
    with a workflow ID, showing execution timeline and current state.

.PARAMETER WorkflowId
    Workflow identifier (required)

.EXAMPLE
    .\workflow-status.ps1 -WorkflowId deploy-auth-2025-11
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$WorkflowId,
    
    [string]$Host = "localhost",
    [int]$Port = 5432,
    [string]$Database = "devtools",
    [string]$User = "devtools",
    [string]$Password = $env:DB_PASSWORD
)

$ErrorActionPreference = "Stop"

Write-Host "=== Workflow Status ===" -ForegroundColor Cyan
Write-Host "Workflow ID: $WorkflowId"
Write-Host ""

# Check password
if (-not $Password) {
    Write-Error "Database password not provided. Set DB_PASSWORD environment variable."
    exit 1
}

# Set PGPASSWORD for psql
$env:PGPASSWORD = $Password

try {
    # Get workflow summary
    $summaryQuery = @"
SELECT 
    COUNT(*) as total_requests,
    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
    SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
    SUM(CASE WHEN status = 'expired' THEN 1 ELSE 0 END) as expired,
    MIN(created_at) as workflow_started,
    MAX(updated_at) as last_activity
FROM approval_requests
WHERE workflow_id = '$WorkflowId';
"@

    Write-Host "Fetching workflow summary..." -ForegroundColor Yellow
    $summary = psql -h $Host -p $Port -U $User -d $Database -t -A -c $summaryQuery 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Query failed: $summary"
        exit 1
    }
    
    $fields = $summary -split '\|'
    $totalRequests = $fields[0]
    $pending = $fields[1]
    $approved = $fields[2]
    $rejected = $fields[3]
    $expired = $fields[4]
    $workflowStarted = $fields[5]
    $lastActivity = $fields[6]
    
    if ($totalRequests -eq "0") {
        Write-Host "No approval requests found for this workflow." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Possible reasons:"
        Write-Host "  - Workflow ID is incorrect"
        Write-Host "  - Workflow hasn't created any approval requests yet"
        Write-Host "  - All operations were auto-approved (low risk)"
        exit 0
    }
    
    Write-Host "Summary:" -ForegroundColor Cyan
    Write-Host "  Total Requests:  $totalRequests"
    Write-Host "  Pending:         $pending" -ForegroundColor $(if ($pending -gt 0) { "Yellow" } else { "White" })
    Write-Host "  Approved:        $approved" -ForegroundColor Green
    Write-Host "  Rejected:        $rejected" -ForegroundColor $(if ($rejected -gt 0) { "Red" } else { "White" })
    Write-Host "  Expired:         $expired" -ForegroundColor $(if ($expired -gt 0) { "Yellow" } else { "White" })
    Write-Host "  Started:         $workflowStarted"
    Write-Host "  Last Activity:   $lastActivity"
    Write-Host ""
    
    # Get detailed request list
    $detailsQuery = @"
SELECT 
    LEFT(id::text, 8) as req_id,
    agent_name,
    risk_level,
    LEFT(task_description, 35) as task,
    status,
    approver_id,
    TO_CHAR(created_at, 'MM-DD HH24:MI') as created,
    TO_CHAR(COALESCE(approved_at, rejected_at, updated_at), 'MM-DD HH24:MI') as resolved
FROM approval_requests
WHERE workflow_id = '$WorkflowId'
ORDER BY created_at ASC;
"@

    Write-Host "Approval Requests:" -ForegroundColor Cyan
    $details = psql -h $Host -p $Port -U $User -d $Database -c $detailsQuery 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host $details
    }
    
    Write-Host ""
    
    # Show pending actions
    if ($pending -gt 0) {
        Write-Host "Pending Actions:" -ForegroundColor Yellow
        Write-Host "  - $pending request(s) awaiting approval"
        Write-Host "  - Use: task workflow:list-pending"
        Write-Host "  - Approve: task workflow:approve REQUEST_ID=<id>"
    }
    
    if ($rejected -gt 0) {
        Write-Host ""
        Write-Host "Rejections:" -ForegroundColor Red
        $rejectionQuery = @"
SELECT rejection_reason 
FROM approval_requests 
WHERE workflow_id = '$WorkflowId' AND status = 'rejected'
ORDER BY rejected_at DESC
LIMIT 5;
"@
        psql -h $Host -p $Port -U $User -d $Database -t -A -c $rejectionQuery
    }
    
} catch {
    Write-Error "Failed to get workflow status: $_"
    exit 1
} finally {
    Remove-Item env:PGPASSWORD -ErrorAction SilentlyContinue
}
