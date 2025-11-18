param([switch]$DryRun)
$RepoRoot = "d:\INFRA\Dev-Tools\Dev-Tools"
$Agents = @("orchestrator", "feature-dev", "code-review", "infrastructure", "cicd", "documentation", "rag", "state", "langgraph")
Write-Host "Creating agent directories..." -ForegroundColor Cyan
foreach ($agent in $Agents) {
    $agentPath = Join-Path $RepoRoot "agents\$agent"
    foreach ($subdir in @("src", "config", "tests")) {
        $path = Join-Path $agentPath $subdir
        if ($DryRun) {
            Write-Host "  [DRY] Would create: $path" -ForegroundColor DarkGray
        } else {
            New-Item -ItemType Directory -Path $path -Force | Out-Null
            Write-Host "   Created: $path" -ForegroundColor Green
        }
    }
}
Write-Host "Done!" -ForegroundColor Green
