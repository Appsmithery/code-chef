#!/usr/bin/env pwsh
# Support Directory Reorganization Script
# Automates the reorganization of support/docs and support/scripts

param(
    [switch]$DryRun,
    [switch]$SkipValidation
)

$ErrorActionPreference = "Stop"

Write-Host "=== Support Directory Reorganization ===" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "DRY RUN MODE - No files will be moved" -ForegroundColor Yellow
    Write-Host ""
}

# Phase 1: Create Directory Structure
Write-Host "[Phase 1/6] Creating directory structure..." -ForegroundColor Green

$docsSubdirs = @(
    "support/docs/architecture",
    "support/docs/api",
    "support/docs/guides/integration",
    "support/docs/guides/implementation",
    "support/docs/operations",
    "support/docs/testing"
)

$scriptsSubdirs = @(
    "support/scripts/docker",
    "support/scripts/linear",
    "support/scripts/validation",
    "support/scripts/dev"
)

$allSubdirs = $docsSubdirs + $scriptsSubdirs

foreach ($dir in $allSubdirs) {
    if ($DryRun) {
        Write-Host "  [DRY RUN] Would create: $dir" -ForegroundColor Yellow
    } else {
        New-Item -ItemType Directory -Force -Path $dir | Out-Null
        Write-Host "  ✓ Created: $dir" -ForegroundColor Gray
    }
}

Write-Host ""

# Phase 2: Move Documentation Files
Write-Host "[Phase 2/6] Moving documentation files..." -ForegroundColor Green

$docMoves = @(
    @{ Src = "support/docs/AGENT_REGISTRY.md"; Dst = "support/docs/architecture/AGENT_REGISTRY.md" },
    @{ Src = "support/docs/EVENT_PROTOCOL.md"; Dst = "support/docs/architecture/EVENT_PROTOCOL.md" },
    @{ Src = "support/docs/PHASE_6_PLAN.md"; Dst = "support/docs/architecture/PHASE_6_PLAN.md" },
    @{ Src = "support/docs/RESOURCE_LOCKING.md"; Dst = "support/docs/architecture/RESOURCE_LOCKING.md" },
    @{ Src = "support/docs/NOTIFICATION_SYSTEM.md"; Dst = "support/docs/architecture/NOTIFICATION_SYSTEM.md" },
    @{ Src = "support/docs/AGENT_ENDPOINTS.md"; Dst = "support/docs/api/AGENT_ENDPOINTS.md" },
    @{ Src = "support/docs/LINEAR_SETUP.md"; Dst = "support/docs/guides/integration/LINEAR_SETUP.md" },
    @{ Src = "support/docs/LINEAR_USAGE_GUIDELINES.md"; Dst = "support/docs/guides/integration/LINEAR_USAGE_GUIDELINES.md" },
    @{ Src = "support/docs/HITL_IMPLEMENTATION_PHASE2.md"; Dst = "support/docs/guides/implementation/HITL_IMPLEMENTATION_PHASE2.md" },
    @{ Src = "support/docs/DEPLOY.md"; Dst = "support/docs/operations/DEPLOY.md" },
    @{ Src = "support/docs/MONITORING.md"; Dst = "support/docs/operations/MONITORING.md" },
    @{ Src = "support/docs/PHASE_6_MONITORING_GUIDE.md"; Dst = "support/docs/operations/PHASE_6_MONITORING_GUIDE.md" },
    @{ Src = "support/docs/CLEANUP_SUMMARY.md"; Dst = "support/docs/operations/CLEANUP_HISTORY.md" },
    @{ Src = "support/docs/TESTING_STRATEGY.md"; Dst = "support/docs/testing/TESTING_STRATEGY.md" },
    @{ Src = "support/docs/CHAOS_TESTING.md"; Dst = "support/docs/testing/CHAOS_TESTING.md" }
)

$docsMoved = 0
foreach ($move in $docMoves) {
    if (Test-Path $move['Src']) {
        if ($DryRun) {
            Write-Host "  [DRY RUN] Would move: $($move['Src']) -> $($move['Dst'])" -ForegroundColor Yellow
        } else {
            Move-Item $move['Src'] $move['Dst'] -Force
            Write-Host "  ✓ Moved: $(Split-Path $move['Src'] -Leaf)" -ForegroundColor Gray
            $docsMoved++
        }
    } else {
        Write-Host "  ⚠ File not found: $($move['Src'])" -ForegroundColor DarkYellow
    }
}

Write-Host "  Summary: $docsMoved documentation files moved" -ForegroundColor Cyan
Write-Host ""

# Phase 3: Move Script Files
Write-Host "[Phase 3/6] Moving script files..." -ForegroundColor Green

$scriptMoves = @(
    @{ Src = "support/scripts/docker-cleanup.ps1"; Dst = "support/scripts/docker/docker-cleanup.ps1" },
    @{ Src = "support/scripts/docker-prune.sh"; Dst = "support/scripts/docker/docker-prune.sh" },
    @{ Src = "support/scripts/backup_volumes.sh"; Dst = "support/scripts/docker/backup_volumes.sh" },
    @{ Src = "support/scripts/dockerhub-image-prune.ps1"; Dst = "support/scripts/docker/dockerhub-image-prune.ps1" },
    @{ Src = "support/scripts/agent-linear-update.py"; Dst = "support/scripts/linear/agent-linear-update.py" },
    @{ Src = "support/scripts/get-linear-project-uuid.py"; Dst = "support/scripts/linear/get-linear-project-uuid.py" },
    @{ Src = "support/scripts/update-linear-pr68.py"; Dst = "support/scripts/linear/update-linear-pr68.py" },
    @{ Src = "support/scripts/validate-env.sh"; Dst = "support/scripts/validation/validate-env.sh" },
    @{ Src = "support/scripts/validate-phase6.ps1"; Dst = "support/scripts/validation/validate-phase6.ps1" },
    @{ Src = "support/scripts/validate-tracing.sh"; Dst = "support/scripts/validation/validate-tracing.sh" },
    @{ Src = "support/scripts/health-check.sh"; Dst = "support/scripts/validation/health-check.sh" },
    @{ Src = "support/scripts/up.sh"; Dst = "support/scripts/dev/up.sh" },
    @{ Src = "support/scripts/down.sh"; Dst = "support/scripts/dev/down.sh" },
    @{ Src = "support/scripts/rebuild.sh"; Dst = "support/scripts/dev/rebuild.sh" },
    @{ Src = "support/scripts/logs.sh"; Dst = "support/scripts/dev/logs.sh" },
    @{ Src = "support/scripts/test-progressive-disclosure.py"; Dst = "support/scripts/dev/test-progressive-disclosure.py" }
)

$scriptsMoved = 0
foreach ($move in $scriptMoves) {
    if (Test-Path $move['Src']) {
        if ($DryRun) {
            Write-Host "  [DRY RUN] Would move: $($move['Src']) -> $($move['Dst'])" -ForegroundColor Yellow
        } else {
            Move-Item $move['Src'] $move['Dst'] -Force
            Write-Host "  ✓ Moved: $(Split-Path $move['Src'] -Leaf)" -ForegroundColor Gray
            $scriptsMoved++
        }
    } else {
        Write-Host "  ⚠ File not found: $($move['Src'])" -ForegroundColor DarkYellow
    }
}

Write-Host "  Summary: $scriptsMoved script files moved" -ForegroundColor Cyan
Write-Host ""

# Phase 4: Create README Files
Write-Host "[Phase 4/6] Creating README files..." -ForegroundColor Green

$docsReadme = @'
# Dev-Tools Documentation

## Directory Structure

- **architecture/** - System design, agent architecture, event protocols
- **api/** - API endpoints and reference documentation
- **guides/** - Implementation and integration guides
  - **integration/** - External service setup (Linear, LangSmith, etc.)
  - **implementation/** - Feature implementation guides
- **operations/** - Deployment, monitoring, maintenance
- **testing/** - Testing strategies and chaos engineering
- **_temp/** - Temporary working files (excluded from Git)

## Quick Links

- [Agent Registry](architecture/AGENT_REGISTRY.md) - Multi-agent discovery
- [Linear Integration](guides/integration/LINEAR_USAGE_GUIDELINES.md) - Linear setup and usage
- [Deployment Guide](operations/DEPLOY.md) - Deployment workflows
- [Testing Strategy](testing/TESTING_STRATEGY.md) - Test approach and coverage

## Contributing

Keep documentation up-to-date with architecture changes. Use _temp/ for work-in-progress.
'@

$scriptsReadme = @'
# Dev-Tools Scripts

## Directory Structure

- **deploy/** - Deployment and infrastructure setup
- **docker/** - Docker operations and maintenance
- **linear/** - Linear project management scripts
- **validation/** - Testing and health check scripts
- **dev/** - Development utilities (up/down/rebuild/logs)

## Quick Commands

### Development
```powershell
./support/scripts/dev/up.sh              # Start all services
./support/scripts/dev/logs.sh orchestrator  # Tail logs
./support/scripts/dev/rebuild.sh         # Rebuild all
./support/scripts/dev/down.sh            # Stop all
```

### Deployment
```powershell
./support/scripts/deploy/deploy.ps1 -Target remote  # Deploy to droplet
./support/scripts/validation/health-check.sh        # Verify health
```

### Linear Integration
```powershell
python support/scripts/linear/agent-linear-update.py create-issue --project-id "UUID" --title "Feature"
python support/scripts/linear/get-linear-project-uuid.py
```

### Docker Maintenance
```powershell
./support/scripts/docker/backup_volumes.sh  # Backup volumes
./support/scripts/docker/docker-cleanup.ps1 # Clean dangling resources
```
'@

if ($DryRun) {
    Write-Host "  [DRY RUN] Would create: support/docs/README.md" -ForegroundColor Yellow
    Write-Host "  [DRY RUN] Would create: support/scripts/README.md" -ForegroundColor Yellow
} else {
    $docsReadme | Out-File -FilePath "support/docs/README.md" -Encoding UTF8
    Write-Host "  ✓ Created: support/docs/README.md" -ForegroundColor Gray
    
    $scriptsReadme | Out-File -FilePath "support/scripts/README.md" -Encoding UTF8
    Write-Host "  ✓ Created: support/scripts/README.md" -ForegroundColor Gray
}

Write-Host ""

# Phase 5: Update References
Write-Host "[Phase 5/6] Scanning for references to update..." -ForegroundColor Green

$filesToCheck = @(
    ".github/copilot-instructions.md",
    "config/linear/AGENT_QUICK_REFERENCE.md"
)

$foundReferences = @()
foreach ($file in $filesToCheck) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        if ($content -match "support/scripts/(agent-linear-update|validate-|docker-cleanup|up\.sh|down\.sh|backup_volumes)") {
            $foundReferences += "  ⚠ Found old paths in: $file"
        }
    }
}

if ($foundReferences.Count -gt 0) {
    Write-Host "  References to update:" -ForegroundColor Yellow
    $foundReferences | ForEach-Object { Write-Host $_ -ForegroundColor Yellow }
    Write-Host ""
    Write-Host "  ⚠ Manual review recommended" -ForegroundColor Yellow
} else {
    Write-Host "  ✓ No obvious references found" -ForegroundColor Gray
}

Write-Host ""

# Phase 6: Validation
if (-not $SkipValidation) {
    Write-Host "[Phase 6/6] Validating reorganization..." -ForegroundColor Green
    
    $keyFiles = @(
        "support/docs/architecture/AGENT_REGISTRY.md",
        "support/docs/api/AGENT_ENDPOINTS.md",
        "support/docs/guides/integration/LINEAR_USAGE_GUIDELINES.md",
        "support/scripts/linear/agent-linear-update.py",
        "support/scripts/validation/validate-phase6.ps1",
        "support/scripts/dev/up.sh"
    )
    
    $allGood = $true
    foreach ($file in $keyFiles) {
        if (Test-Path $file) {
            Write-Host "  ✓ Found: $file" -ForegroundColor Gray
        } else {
            Write-Host "  ✗ Missing: $file" -ForegroundColor Red
            $allGood = $false
        }
    }
    
    Write-Host ""
    
    if ($allGood) {
        Write-Host "  ✓ All key files found in new locations" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Some files are missing" -ForegroundColor Red
    }
} else {
    Write-Host "[Phase 6/6] Validation skipped" -ForegroundColor Yellow
}

Write-Host ""

# Summary
Write-Host "=== Reorganization Complete ===" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "DRY RUN completed. No files were moved." -ForegroundColor Yellow
    Write-Host "Run without -DryRun to execute the reorganization." -ForegroundColor Yellow
} else {
    Write-Host "Summary:" -ForegroundColor Cyan
    Write-Host "  - Documentation files moved: $docsMoved" -ForegroundColor Gray
    Write-Host "  - Script files moved: $scriptsMoved" -ForegroundColor Gray
    Write-Host "  - README files created: 2" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Review and update cross-references" -ForegroundColor Gray
    Write-Host "  2. Test script execution" -ForegroundColor Gray
    Write-Host "  3. Commit changes: git add support/ && git commit -m 'refactor: reorganize support/'" -ForegroundColor Gray
}

Write-Host ""
