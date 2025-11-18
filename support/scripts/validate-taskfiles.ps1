#!/usr/bin/env pwsh
# Validate Dev-Tools Taskfile rebuild

Write-Host "`n=== Dev-Tools Taskfile Validation ===" -ForegroundColor Cyan
Write-Host "Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray

# Check root Taskfile
Write-Host "`n[1/5] Root Taskfile" -ForegroundColor Yellow
if (Test-Path "Taskfile.yml") {
    Write-Host "  ✓ Taskfile.yml exists" -ForegroundColor Green
    $rootTasks = task --list 2>&1 | Select-String -Pattern "^\*" | Measure-Object
    Write-Host "  ✓ $($rootTasks.Count) root tasks available" -ForegroundColor Green
} else {
    Write-Host "  ✗ Taskfile.yml missing" -ForegroundColor Red
    exit 1
}

# Check agent Taskfiles
Write-Host "`n[2/5] Agent Taskfiles" -ForegroundColor Yellow
$agents = @("orchestrator", "feature-dev", "code-review", "documentation", "infrastructure", "cicd")
$agentCount = 0
foreach ($agent in $agents) {
    $path = "agents\$agent\Taskfile.yml"
    if (Test-Path $path) {
        Write-Host "  ✓ $agent" -ForegroundColor Green
        $agentCount++
    } else {
        Write-Host "  ✗ $agent missing" -ForegroundColor Red
    }
}
Write-Host "  Summary: $agentCount/$($agents.Count) agents configured" -ForegroundColor $(if($agentCount -eq $agents.Count){"Green"}else{"Red"})

# Check Dockerfiles
Write-Host "`n[3/5] Dockerfiles with Task Runner" -ForegroundColor Yellow
$dockerCount = 0
foreach ($agent in $agents) {
    $path = "containers\$agent\Dockerfile"
    if (Test-Path $path) {
        $content = Get-Content $path -Raw
        if ($content -match "taskfile.dev") {
            Write-Host "  ✓ $agent" -ForegroundColor Green
            $dockerCount++
        } else {
            Write-Host "  ✗ $agent missing Task runner" -ForegroundColor Red
        }
    } else {
        Write-Host "  ✗ $agent Dockerfile missing" -ForegroundColor Red
    }
}
Write-Host "  Summary: $dockerCount/$($agents.Count) Dockerfiles updated" -ForegroundColor $(if($dockerCount -eq $agents.Count){"Green"}else{"Red"})

# Check documentation
Write-Host "`n[4/5] Documentation" -ForegroundColor Yellow
$docs = @{
    "TASKFILE_WORKFLOWS.md" = "docs\TASKFILE_WORKFLOWS.md"
    "TASKFILE_REBUILD.md" = "docs\TASKFILE_REBUILD.md"
    "AGENT_ENDPOINTS.md" = "docs\AGENT_ENDPOINTS.md"
}
$docCount = 0
foreach ($doc in $docs.GetEnumerator()) {
    if (Test-Path $doc.Value) {
        Write-Host "  ✓ $($doc.Key)" -ForegroundColor Green
        $docCount++
    } else {
        Write-Host "  ✗ $($doc.Key) missing" -ForegroundColor Red
    }
}

# Check old automation removed
Write-Host "`n[5/5] Old Automation Cleanup" -ForegroundColor Yellow
$oldPaths = @(".taskfiles", "scripts\tasks", "scripts\docs", "scripts\reports", "scripts\repo")
$cleanCount = 0
foreach ($path in $oldPaths) {
    if (-not (Test-Path $path)) {
        Write-Host "  ✓ $path removed" -ForegroundColor Green
        $cleanCount++
    } else {
        Write-Host "  ✗ $path still exists" -ForegroundColor Red
    }
}

# Summary
Write-Host "`n=== Validation Summary ===" -ForegroundColor Cyan
Write-Host "  Root Taskfile: $(if(Test-Path 'Taskfile.yml'){'✓'}else{'✗'})" -ForegroundColor $(if(Test-Path 'Taskfile.yml'){"Green"}else{"Red"})
Write-Host "  Agent Taskfiles: $agentCount/$($agents.Count)" -ForegroundColor $(if($agentCount -eq $agents.Count){"Green"}else{"Yellow"})
Write-Host "  Dockerfiles: $dockerCount/$($agents.Count)" -ForegroundColor $(if($dockerCount -eq $agents.Count){"Green"}else{"Yellow"})
Write-Host "  Documentation: $docCount/$($docs.Count)" -ForegroundColor $(if($docCount -eq $docs.Count){"Green"}else{"Yellow"})
Write-Host "  Cleanup: $cleanCount/$($oldPaths.Count)" -ForegroundColor $(if($cleanCount -eq $oldPaths.Count){"Green"}else{"Yellow"})

if ($agentCount -eq $agents.Count -and $dockerCount -eq $agents.Count -and $docCount -eq $docs.Count -and $cleanCount -eq $oldPaths.Count) {
    Write-Host "`n[SUCCESS] All validation checks passed!" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Cyan
    Write-Host "  1. Start containers: task compose:up"
    Write-Host "  2. Check health: task health"
    Write-Host "  3. Review workflows: docs\TASKFILE_WORKFLOWS.md"
    exit 0
} else {
    Write-Host "`n[FAILED] Some validation checks failed" -ForegroundColor Red
    exit 1
}
