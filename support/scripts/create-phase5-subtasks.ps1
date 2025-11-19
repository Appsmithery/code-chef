$env:LINEAR_API_KEY = "lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571"
$teamId = "f5b610be-ac34-4983-918b-2c9d00aa9b7a"
$parentId = "PR-56"
$backlogStateId = "8dd92e2f-e058-4af1-b8f7-c6cd65e20d18"

function Create-SubIssue($title, $description, $priority) {
    $mutation = @"
mutation {
  issueCreate(input: {
    teamId: "$teamId"
    parentId: "$parentId"
    title: "$title"
    description: "$description"
    priority: $priority
    stateId: "$backlogStateId"
  }) {
    success
    issue {
      id
      identifier
      title
      url
    }
  }
}
"@

    $body = @{ query = $mutation } | ConvertTo-Json -Depth 10
    $response = Invoke-RestMethod -Uri "https://api.linear.app/graphql" -Method Post -Headers @{
        "Authorization" = "Bearer $env:LINEAR_API_KEY"
        "Content-Type" = "application/json"
    } -Body $body

    if ($response.data.issueCreate.success) {
        $issue = $response.data.issueCreate.issue
        Write-Host "✅ Created: $($issue.identifier) - $($issue.title)" -ForegroundColor Green
        Write-Host "   URL: $($issue.url)"
    } else {
        Write-Host "❌ Failed to create: $title" -ForegroundColor Red
        Write-Host "   Error: $($response.errors)"
    }
    Start-Sleep -Milliseconds 500
}

Write-Host "`n📦 Creating Phase 5 sub-issues for PR-56...`n"

Create-SubIssue `
    "Task 5.3: Workspace-Level Approval Hub" `
    "Create workspace-level approval hub issue in Linear (PR-68), configure LinearWorkspaceClient for workspace-scoped operations, implement posting logic to central hub. **Completed**: ✅ PR-68 created, ✅ LinearWorkspaceClient operational, ✅ Posting with @lead-minion mentions working" `
    2

Create-SubIssue `
    "Task 5.4: Multi-Project Security Scoping" `
    "Implement LinearClientFactory with orchestrator/subagent routing, enforce project-scoped access for subagents, add security tests for cross-project isolation. Ensures subagents cannot access approval hub or other projects." `
    1

Create-SubIssue `
    "Task 5.5: Email Notification Fallback" `
    "Implement EmailNotifier for critical approvals, configure SMTP settings (smtp.gmail.com:587), add email templates for approval requests. Fallback for when Linear notifications are insufficient." `
    3

Create-SubIssue `
    "Task 5.6: Integration Testing and Documentation" `
    "End-to-end testing for approval workflow across multiple projects, multi-project isolation tests, operator guide for workspace hub setup, deployment documentation for droplet." `
    2

Write-Host ""
Write-Host "Phase 5 sub-issues created successfully!"
