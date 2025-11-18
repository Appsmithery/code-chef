param([switch]$DryRun)

$RepoRoot = "d:\INFRA\Dev-Tools\Dev-Tools"

$AgentMappings = @{
    'orchestrator' = @{ OldSrc = 'agents/orchestrator'; OldContainer = 'containers/orchestrator' }
    'feature-dev' = @{ OldSrc = 'agents/feature_dev'; OldContainer = 'containers/feature-dev' }
    'code-review' = @{ OldSrc = 'agents/code_review'; OldContainer = 'containers/code-review' }
    'infrastructure' = @{ OldSrc = 'agents/infrastructure'; OldContainer = 'containers/infrastructure' }
    'cicd' = @{ OldSrc = 'agents/cicd'; OldContainer = 'containers/cicd' }
    'documentation' = @{ OldSrc = 'agents/documentation'; OldContainer = 'containers/documentation' }
    'rag' = @{ OldSrc = 'agents/rag'; OldContainer = 'containers/rag' }
    'state' = @{ OldSrc = 'agents/state'; OldContainer = 'containers/state' }
    'langgraph' = @{ OldSrc = 'agents/langgraph'; OldContainer = 'containers/langgraph' }
}

Write-Host "Moving agent files..." -ForegroundColor Cyan

foreach ($agent in $AgentMappings.Keys) {
    Write-Host "`nProcessing: $agent" -ForegroundColor Yellow
    $mapping = $AgentMappings[$agent]
    $oldSrcPath = Join-Path $RepoRoot $mapping.OldSrc
    $oldContainerPath = Join-Path $RepoRoot $mapping.OldContainer
    $newBase = Join-Path $RepoRoot "agents/$agent"
    
    # Move Python files
    if (Test-Path $oldSrcPath) {
        Get-ChildItem -Path $oldSrcPath -Filter "*.py" -File | ForEach-Object {
            $dest = Join-Path "$newBase/src" $_.Name
            if ($DryRun) {
                Write-Host "  [DRY] Would move: $($_.Name) -> src/" -ForegroundColor DarkGray
            } else {
                Copy-Item -Path $_.FullName -Destination $dest -Force
                Write-Host "  Moved: $($_.Name) -> src/" -ForegroundColor Green
            }
        }
        
        # Move requirements.txt
        $reqFile = Join-Path $oldSrcPath "requirements.txt"
        if (Test-Path $reqFile) {
            $dest = Join-Path $newBase "requirements.txt"
            if ($DryRun) {
                Write-Host "  [DRY] Would move: requirements.txt" -ForegroundColor DarkGray
            } else {
                Copy-Item -Path $reqFile -Destination $dest -Force
                Write-Host "  Moved: requirements.txt" -ForegroundColor Green
            }
        }
    }
    
    # Move Dockerfile
    if (Test-Path $oldContainerPath) {
        $dockerfile = Join-Path $oldContainerPath "Dockerfile"
        if (Test-Path $dockerfile) {
            $dest = Join-Path $newBase "Dockerfile"
            if ($DryRun) {
                Write-Host "  [DRY] Would move: Dockerfile" -ForegroundColor DarkGray
            } else {
                Copy-Item -Path $dockerfile -Destination $dest -Force
                Write-Host "  Moved: Dockerfile" -ForegroundColor Green
            }
        }
    }
}

Write-Host "`nDone!" -ForegroundColor Green
exit 0
