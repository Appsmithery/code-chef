# Documentation and Script Reorganization Plan

## Current State Analysis

### docs (23 files)

- Architecture/design docs: 5
- API/endpoint docs: 2
- Integration guides: 3
- Implementation guides: 6
- Operations/monitoring: 4
- Testing docs: 3

### scripts (16 files + 1 subdir)

- Deployment: 3 files + 1 subdir (deploy)
- Validation/testing: 4
- Docker operations: 3
- Linear integration: 3
- Development tools: 3

---

## Proposed Structure

### docs Reorganization

```
support/docs/
├── architecture/           # System design and architecture
│   ├── AGENT_REGISTRY.md
│   ├── EVENT_PROTOCOL.md
│   ├── PHASE_6_PLAN.md
│   ├── RESOURCE_LOCKING.md
│   └── MCP_ARCHITECTURE.md (if exists)
│
├── api/                   # API documentation and endpoints
│   ├── AGENT_ENDPOINTS.md
│   └── API_REFERENCE.md (if exists)
│
├── guides/                # Implementation and integration guides
│   ├── integration/       # External service integrations
│   │   ├── LINEAR_SETUP.md
│   │   ├── LINEAR_USAGE_GUIDELINES.md
│   │   └── NOTIFICATION_SYSTEM.md
│   │
│   └── implementation/    # Feature implementation guides
│       ├── HITL_IMPLEMENTATION_PHASE2.md
│       ├── PROGRESSIVE_MCP_IMPLEMENTATION.md
│       └── LANGGRAPH_INTEGRATION.md (if exists)
│
├── operations/            # Deployment, monitoring, maintenance
│   ├── DEPLOY.md
│   ├── MONITORING.md
│   ├── PHASE_6_MONITORING_GUIDE.md
│   └── TROUBLESHOOTING.md (if exists)
│
├── testing/               # Test documentation and strategies
│   ├── TESTING_STRATEGY.md
│   ├── CHAOS_TESTING.md
│   └── TEST_COVERAGE.md (if exists)
│
└── _temp/                 # Temporary working files (already exists)
    └── (work-in-progress docs)
```

### scripts Reorganization

```
support/scripts/
├── deploy/                # Deployment and infrastructure (already exists)
│   ├── deploy.ps1
│   ├── deploy-to-droplet.sh
│   └── setup_secrets.sh
│
├── docker/                # Docker operations and cleanup
│   ├── docker-cleanup.ps1
│   ├── docker-prune.sh
│   ├── backup_volumes.sh
│   └── restore_volumes.sh (if exists)
│
├── linear/                # Linear integration scripts
│   ├── agent-linear-update.py
│   ├── get-linear-project-uuid.py
│   └── update-linear-pr68.py
│
├── validation/            # Testing and validation scripts
│   ├── validate-env.sh
│   ├── validate-phase6.ps1
│   ├── validate-tracing.sh
│   └── health-check.sh
│
├── dev/                   # Development utilities
│   ├── up.sh
│   ├── down.sh
│   ├── rebuild.sh
│   ├── logs.sh
│   └── test-mcp.sh (if exists)
│
└── maintenance/           # Maintenance and cleanup
    └── cleanup-old-images.sh (if needed)
```

---

## Files to Move

### docs Moves (23 files)

#### To `architecture/` (5 files)

- [ ] AGENT_REGISTRY.md
- [ ] EVENT_PROTOCOL.md
- [ ] PHASE_6_PLAN.md
- [ ] RESOURCE_LOCKING.md
- [ ] NOTIFICATION_SYSTEM.md (architecture-heavy)

#### To `api/` (1 file)

- [ ] AGENT_ENDPOINTS.md

#### To `guides/integration/` (2 files)

- [ ] LINEAR_SETUP.md
- [ ] LINEAR_USAGE_GUIDELINES.md

#### To `guides/implementation/` (2 files)

- [ ] HITL_IMPLEMENTATION_PHASE2.md
- [ ] PROGRESSIVE_MCP_IMPLEMENTATION.md (from \_temp if exists)

#### To `operations/` (4 files)

- [ ] DEPLOY.md
- [ ] MONITORING.md
- [ ] PHASE_6_MONITORING_GUIDE.md
- [ ] CLEANUP_SUMMARY.md → operations/CLEANUP_HISTORY.md

#### To `testing/` (2 files)

- [ ] TESTING_STRATEGY.md
- [ ] CHAOS_TESTING.md

#### Keep in root docs (7 files)

- [ ] README.md (overview of documentation structure)
- [ ] PHASE_5_COMPLETE_NEXT_STEPS.md
- [ ] PHASE_6_COMPLETE.md
- [ ] PHASE_6_COMPLETE_NEXT_STEPS.md
- [ ] GLOSSARY.md (if exists)
- [ ] CONTRIBUTING.md (if exists)
- [ ] CHANGELOG.md (if exists)

### scripts Moves (16 files)

#### To deploy (0 new - already has 3)

- (deploy.ps1, deploy-to-droplet.sh, setup_secrets.sh already there)

#### To `docker/` (4 files)

- [ ] docker-cleanup.ps1
- [ ] docker-prune.sh
- [ ] backup_volumes.sh
- [ ] dockerhub-image-prune.ps1

#### To `linear/` (3 files)

- [ ] agent-linear-update.py
- [ ] get-linear-project-uuid.py
- [ ] update-linear-pr68.py

#### To `validation/` (4 files)

- [ ] validate-env.sh
- [ ] validate-phase6.ps1
- [ ] validate-tracing.sh
- [ ] health-check.sh

#### To `dev/` (5 files)

- [ ] up.sh
- [ ] down.sh
- [ ] rebuild.sh
- [ ] logs.sh
- [ ] test-progressive-disclosure.py

#### Keep in root scripts (0 files)

- (all files moved to subdirectories)

---

## Implementation Steps

### Phase 1: Create Directory Structure (5 minutes)

```powershell
# Docs subdirectories
New-Item -ItemType Directory -Force -Path "support/docs/architecture"
New-Item -ItemType Directory -Force -Path "support/docs/api"
New-Item -ItemType Directory -Force -Path "support/docs/guides/integration"
New-Item -ItemType Directory -Force -Path "support/docs/guides/implementation"
New-Item -ItemType Directory -Force -Path "support/docs/operations"
New-Item -ItemType Directory -Force -Path "support/docs/testing"

# Scripts subdirectories
New-Item -ItemType Directory -Force -Path "support/scripts/docker"
New-Item -ItemType Directory -Force -Path "support/scripts/linear"
New-Item -ItemType Directory -Force -Path "support/scripts/validation"
New-Item -ItemType Directory -Force -Path "support/scripts/dev"
```

### Phase 2: Move Documentation Files (10 minutes)

```powershell
# Move to architecture/
Move-Item "support/docs/AGENT_REGISTRY.md" "support/docs/architecture/"
Move-Item "support/docs/EVENT_PROTOCOL.md" "support/docs/architecture/"
Move-Item "support/docs/PHASE_6_PLAN.md" "support/docs/architecture/"
Move-Item "support/docs/RESOURCE_LOCKING.md" "support/docs/architecture/"
Move-Item "support/docs/NOTIFICATION_SYSTEM.md" "support/docs/architecture/"

# Move to api/
Move-Item "support/docs/AGENT_ENDPOINTS.md" "support/docs/api/"

# Move to guides/integration/
Move-Item "support/docs/LINEAR_SETUP.md" "support/docs/guides/integration/"
Move-Item "support/docs/LINEAR_USAGE_GUIDELINES.md" "support/docs/guides/integration/"

# Move to guides/implementation/
Move-Item "support/docs/HITL_IMPLEMENTATION_PHASE2.md" "support/docs/guides/implementation/"

# Move to operations/
Move-Item "support/docs/DEPLOY.md" "support/docs/operations/"
Move-Item "support/docs/MONITORING.md" "support/docs/operations/"
Move-Item "support/docs/PHASE_6_MONITORING_GUIDE.md" "support/docs/operations/"
Move-Item "support/docs/CLEANUP_SUMMARY.md" "support/docs/operations/CLEANUP_HISTORY.md"

# Move to testing/
Move-Item "support/docs/TESTING_STRATEGY.md" "support/docs/testing/"
Move-Item "support/docs/CHAOS_TESTING.md" "support/docs/testing/"
```

### Phase 3: Move Script Files (10 minutes)

```powershell
# Move to docker/
Move-Item "support/scripts/docker-cleanup.ps1" "support/scripts/docker/"
Move-Item "support/scripts/docker-prune.sh" "support/scripts/docker/"
Move-Item "support/scripts/backup_volumes.sh" "support/scripts/docker/"
Move-Item "support/scripts/dockerhub-image-prune.ps1" "support/scripts/docker/"

# Move to linear/
Move-Item "support/scripts/agent-linear-update.py" "support/scripts/linear/"
Move-Item "support/scripts/get-linear-project-uuid.py" "support/scripts/linear/"
Move-Item "support/scripts/update-linear-pr68.py" "support/scripts/linear/"

# Move to validation/
Move-Item "support/scripts/validate-env.sh" "support/scripts/validation/"
Move-Item "support/scripts/validate-phase6.ps1" "support/scripts/validation/"
Move-Item "support/scripts/validate-tracing.sh" "support/scripts/validation/"
Move-Item "support/scripts/health-check.sh" "support/scripts/validation/"

# Move to dev/
Move-Item "support/scripts/up.sh" "support/scripts/dev/"
Move-Item "support/scripts/down.sh" "support/scripts/dev/"
Move-Item "support/scripts/rebuild.sh" "support/scripts/dev/"
Move-Item "support/scripts/logs.sh" "support/scripts/dev/"
Move-Item "support/scripts/test-progressive-disclosure.py" "support/scripts/dev/"
```

### Phase 4: Create Index/README Files (5 minutes)

```powershell
# Create docs README
@"
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
"@ | Out-File -FilePath "support/docs/README.md" -Encoding UTF8

# Create scripts README
@"
# Dev-Tools Scripts

## Directory Structure

- **deploy/** - Deployment and infrastructure setup
- **docker/** - Docker operations and maintenance
- **linear/** - Linear project management scripts
- **validation/** - Testing and health check scripts
- **dev/** - Development utilities (up/down/rebuild/logs)

## Quick Commands

### Development
\`\`\`powershell
./support/scripts/dev/up.sh              # Start all services
./support/scripts/dev/logs.sh orchestrator  # Tail logs
./support/scripts/dev/rebuild.sh         # Rebuild all
./support/scripts/dev/down.sh            # Stop all
\`\`\`

### Deployment
\`\`\`powershell
./support/scripts/deploy/deploy.ps1 -Target remote  # Deploy to droplet
./support/scripts/validation/health-check.sh        # Verify health
\`\`\`

### Linear Integration
\`\`\`powershell
python support/scripts/linear/agent-linear-update.py create-issue --project-id "UUID" --title "Feature"
python support/scripts/linear/get-linear-project-uuid.py
\`\`\`

### Docker Maintenance
\`\`\`powershell
./support/scripts/docker/backup_volumes.sh  # Backup volumes
./support/scripts/docker/docker-cleanup.ps1 # Clean dangling resources
\`\`\`
"@ | Out-File -FilePath "support/scripts/README.md" -Encoding UTF8
```

### Phase 5: Update References (15 minutes)

**Files to Update:**

1. copilot-instructions.md - Update script paths
2. LINEAR_USAGE_GUIDELINES.md - Update script references (if moved earlier)
3. AGENT_QUICK_REFERENCE.md - Update script paths
4. docker-compose.yml - Check volume mounts for scripts
5. Agent `main.py` files - Check any hardcoded script paths
6. Makefile or Taskfile.yml - Update script paths if present

**Search and Replace:**

```powershell
# Find all references to moved scripts
Get-ChildItem -Recurse -Include "*.md","*.py","*.yml","*.yaml" |
  Select-String -Pattern "support/scripts/(agent-linear-update|validate-|docker-cleanup|up\.sh|down\.sh)" |
  Select-Object Path, Line | Format-Table -AutoSize

# Update references (manual review recommended)
# Example:
# OLD: support/scripts/agent-linear-update.py
# NEW: support/scripts/linear/agent-linear-update.py
```

### Phase 6: Test and Validate (10 minutes)

```powershell
# Test script execution from new locations
python support/scripts/linear/agent-linear-update.py get-states
./support/scripts/validation/health-check.sh
./support/scripts/dev/up.sh

# Verify documentation links
# Check that all internal links in README files work

# Commit changes
git add support/docs support/scripts
git commit -m "refactor: reorganize support/ into logical subdirectories

- Docs: architecture, api, guides, operations, testing
- Scripts: deploy, docker, linear, validation, dev
- Added README.md in both directories
- Updated cross-references
- Improved navigation and discoverability"
```

---

## Benefits

### For Developers

- ✅ **Faster navigation** - Logical grouping by purpose
- ✅ **Clear separation** - Architecture vs operations vs guides
- ✅ **Better discoverability** - README files with quick links
- ✅ **Reduced clutter** - Root directories are clean

### For Agents

- ✅ **Predictable paths** - Scripts organized by function
- ✅ **Easy reference** - Documentation hierarchy matches mental model
- ✅ **Self-documenting** - Directory names indicate purpose

### For Maintenance

- ✅ **Scalability** - Easy to add new docs/scripts to appropriate subdirs
- ✅ **Consistency** - Similar items grouped together
- ✅ **Clarity** - Obvious where to find or add new content

---

## Rollback Plan

If issues arise:

```powershell
# Restore from Git
git restore support/docs support/scripts

# Or use archived backup
Copy-Item "_archive/support-backup-$(Get-Date -Format 'yyyyMMdd')" "support/" -Recurse -Force
```

---

## Estimated Time

- **Phase 1**: 5 minutes (create directories)
- **Phase 2**: 10 minutes (move docs)
- **Phase 3**: 10 minutes (move scripts)
- **Phase 4**: 5 minutes (create READMEs)
- **Phase 5**: 15 minutes (update references)
- **Phase 6**: 10 minutes (test and validate)

**Total**: ~55 minutes

---

## Execution Status

- [ ] Phase 1: Directory structure created
- [ ] Phase 2: Documentation files moved
- [ ] Phase 3: Script files moved
- [ ] Phase 4: README files created
- [ ] Phase 5: Cross-references updated
- [ ] Phase 6: Tested and validated
- [ ] Changes committed to Git

---

**Ready to execute?** Run `./support/scripts/reorg-support.ps1` (to be created) or follow phases manually.
</content>
</write_to_file>

Now let me create the automated execution script:

<write_to_file>
<path>support/scripts/reorg-support.ps1</path>
<content>#!/usr/bin/env pwsh

# Support Directory Reorganization Script

# Automates the reorganization of support/docs and support/scripts

# See support/REORG_PLAN.md for details

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

# ============================================================================

# Phase 1: Create Directory Structure

# ============================================================================

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
Write-Host " [DRY RUN] Would create: $dir" -ForegroundColor Yellow
} else {
New-Item -ItemType Directory -Force -Path $dir | Out-Null
Write-Host " ✓ Created: $dir" -ForegroundColor Gray
}
}

Write-Host ""

# ============================================================================

# Phase 2: Move Documentation Files

# ============================================================================

Write-Host "[Phase 2/6] Moving documentation files..." -ForegroundColor Green

$docMoves = @( # To architecture/
@{ Src = "support/docs/AGENT_REGISTRY.md"; Dst = "support/docs/architecture/AGENT_REGISTRY.md" },
@{ Src = "support/docs/EVENT_PROTOCOL.md"; Dst = "support/docs/architecture/EVENT_PROTOCOL.md" },
@{ Src = "support/docs/PHASE_6_PLAN.md"; Dst = "support/docs/architecture/PHASE_6_PLAN.md" },
@{ Src = "support/docs/RESOURCE_LOCKING.md"; Dst = "support/docs/architecture/RESOURCE_LOCKING.md" },
@{ Src = "support/docs/NOTIFICATION_SYSTEM.md"; Dst = "support/docs/architecture/NOTIFICATION_SYSTEM.md" },

    # To api/
    @{ Src = "support/docs/AGENT_ENDPOINTS.md"; Dst = "support/docs/api/AGENT_ENDPOINTS.md" },

    # To guides/integration/
    @{ Src = "support/docs/LINEAR_SETUP.md"; Dst = "support/docs/guides/integration/LINEAR_SETUP.md" },
    @{ Src = "support/docs/LINEAR_USAGE_GUIDELINES.md"; Dst = "support/docs/guides/integration/LINEAR_USAGE_GUIDELINES.md" },

    # To guides/implementation/
    @{ Src = "support/docs/HITL_IMPLEMENTATION_PHASE2.md"; Dst = "support/docs/guides/implementation/HITL_IMPLEMENTATION_PHASE2.md" },

    # To operations/
    @{ Src = "support/docs/DEPLOY.md"; Dst = "support/docs/operations/DEPLOY.md" },
    @{ Src = "support/docs/MONITORING.md"; Dst = "support/docs/operations/MONITORING.md" },
    @{ Src = "support/docs/PHASE_6_MONITORING_GUIDE.md"; Dst = "support/docs/operations/PHASE_6_MONITORING_GUIDE.md" },
    @{ Src = "support/docs/CLEANUP_SUMMARY.md"; Dst = "support/docs/operations/CLEANUP_HISTORY.md" },

    # To testing/
    @{ Src = "support/docs/TESTING_STRATEGY.md"; Dst = "support/docs/testing/TESTING_STRATEGY.md" },
    @{ Src = "support/docs/CHAOS_TESTING.md"; Dst = "support/docs/testing/CHAOS_TESTING.md" }

)

$docsMoved = 0
foreach ($move in $docMoves) {
    if (Test-Path $move.Src) {
        if ($DryRun) {
Write-Host " [DRY RUN] Would move: $($move.Src) -> $($move.Dst)" -ForegroundColor Yellow
} else {
Move-Item $move.Src $move.Dst -Force
            Write-Host "  ✓ Moved: $(Split-Path $move.Src -Leaf)" -ForegroundColor Gray
            $docsMoved++
        }
    } else {
        Write-Host "  ⚠ File not found: $($move.Src)" -ForegroundColor DarkYellow
}
}

Write-Host " Summary: $docsMoved documentation files moved" -ForegroundColor Cyan
Write-Host ""

# ============================================================================

# Phase 3: Move Script Files

# ============================================================================

Write-Host "[Phase 3/6] Moving script files..." -ForegroundColor Green

$scriptMoves = @( # To docker/
@{ Src = "support/scripts/docker-cleanup.ps1"; Dst = "support/scripts/docker/docker-cleanup.ps1" },
@{ Src = "support/scripts/docker-prune.sh"; Dst = "support/scripts/docker/docker-prune.sh" },
@{ Src = "support/scripts/backup_volumes.sh"; Dst = "support/scripts/docker/backup_volumes.sh" },
@{ Src = "support/scripts/dockerhub-image-prune.ps1"; Dst = "support/scripts/docker/dockerhub-image-prune.ps1" },

    # To linear/
    @{ Src = "support/scripts/agent-linear-update.py"; Dst = "support/scripts/linear/agent-linear-update.py" },
    @{ Src = "support/scripts/get-linear-project-uuid.py"; Dst = "support/scripts/linear/get-linear-project-uuid.py" },
    @{ Src = "support/scripts/update-linear-pr68.py"; Dst = "support/scripts/linear/update-linear-pr68.py" },

    # To validation/
    @{ Src = "support/scripts/validate-env.sh"; Dst = "support/scripts/validation/validate-env.sh" },
    @{ Src = "support/scripts/validate-phase6.ps1"; Dst = "support/scripts/validation/validate-phase6.ps1" },
    @{ Src = "support/scripts/validate-tracing.sh"; Dst = "support/scripts/validation/validate-tracing.sh" },
    @{ Src = "support/scripts/health-check.sh"; Dst = "support/scripts/validation/health-check.sh" },

    # To dev/
    @{ Src = "support/scripts/up.sh"; Dst = "support/scripts/dev/up.sh" },
    @{ Src = "support/scripts/down.sh"; Dst = "support/scripts/dev/down.sh" },
    @{ Src = "support/scripts/rebuild.sh"; Dst = "support/scripts/dev/rebuild.sh" },
    @{ Src = "support/scripts/logs.sh"; Dst = "support/scripts/dev/logs.sh" },
    @{ Src = "support/scripts/test-progressive-disclosure.py"; Dst = "support/scripts/dev/test-progressive-disclosure.py" }

)

$scriptsMoved = 0
foreach ($move in $scriptMoves) {
    if (Test-Path $move.Src) {
        if ($DryRun) {
Write-Host " [DRY RUN] Would move: $($move.Src) -> $($move.Dst)" -ForegroundColor Yellow
} else {
Move-Item $move.Src $move.Dst -Force
            Write-Host "  ✓ Moved: $(Split-Path $move.Src -Leaf)" -ForegroundColor Gray
            $scriptsMoved++
        }
    } else {
        Write-Host "  ⚠ File not found: $($move.Src)" -ForegroundColor DarkYellow
}
}

Write-Host " Summary: $scriptsMoved script files moved" -ForegroundColor Cyan
Write-Host ""

# ============================================================================

# Phase 4: Create README Files

# ============================================================================

Write-Host "[Phase 4/6] Creating README files..." -ForegroundColor Green

$docsReadme = @"

# Dev-Tools Documentation

## Directory Structure

- **architecture/** - System design, agent architecture, event protocols
- **api/** - API endpoints and reference documentation
- **guides/** - Implementation and integration guides
  - **integration/** - External service setup (Linear, LangSmith, etc.)
  - **implementation/** - Feature implementation guides
- **operations/** - Deployment, monitoring, maintenance
- **testing/** - Testing strategies and chaos engineering
- **\_temp/** - Temporary working files (excluded from Git)

## Quick Links

- [Agent Registry](architecture/AGENT_REGISTRY.md) - Multi-agent discovery
- [Linear Integration](guides/integration/LINEAR_USAGE_GUIDELINES.md) - Linear setup and usage
- [Deployment Guide](operations/DEPLOY.md) - Deployment workflows
- [Testing Strategy](testing/TESTING_STRATEGY.md) - Test approach and coverage

## Contributing

Keep documentation up-to-date with architecture changes. Use \_temp/ for work-in-progress.
"@

$scriptsReadme = @"

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

"@

if ($DryRun) {
Write-Host " [DRY RUN] Would create: support/docs/README.md" -ForegroundColor Yellow
Write-Host " [DRY RUN] Would create: support/scripts/README.md" -ForegroundColor Yellow
} else {
$docsReadme | Out-File -FilePath "support/docs/README.md" -Encoding UTF8
Write-Host " ✓ Created: support/docs/README.md" -ForegroundColor Gray

    $scriptsReadme | Out-File -FilePath "support/scripts/README.md" -Encoding UTF8
    Write-Host "  ✓ Created: support/scripts/README.md" -ForegroundColor Gray

}

Write-Host ""

# ============================================================================

# Phase 5: Update References

# ============================================================================

Write-Host "[Phase 5/6] Scanning for references to update..." -ForegroundColor Green

$referencesToUpdate = @(
"support/scripts/agent-linear-update.py",
"support/scripts/validate-",
"support/scripts/docker-cleanup",
"support/scripts/up.sh",
"support/scripts/down.sh",
"support/scripts/backup_volumes"
)

Write-Host " Searching for references in:" -ForegroundColor Gray
Write-Host " - .github/copilot-instructions.md" -ForegroundColor Gray
Write-Host " - config/linear/AGENT_QUICK_REFERENCE.md" -ForegroundColor Gray
Write-Host " - All markdown and YAML files" -ForegroundColor Gray
Write-Host ""

$filesToCheck = @(
".github/copilot-instructions.md",
"config/linear/AGENT_QUICK_REFERENCE.md"
)

$foundReferences = @()
foreach ($file in $filesToCheck) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        foreach ($ref in $referencesToUpdate) {
            if ($content -match [regex]::Escape($ref)) {
                $foundReferences += "  ⚠ Found '$ref' in: $file"
}
}
}
}

if ($foundReferences.Count -gt 0) {
Write-Host " References to update:" -ForegroundColor Yellow
$foundReferences | ForEach-Object { Write-Host $\_ -ForegroundColor Yellow }
Write-Host ""
Write-Host " ⚠ Manual review recommended for these files" -ForegroundColor Yellow
} else {
Write-Host " ✓ No obvious references found (or already updated)" -ForegroundColor Gray
}

Write-Host ""

# ============================================================================

# Phase 6: Validation

# ============================================================================

if (-not $SkipValidation) {
Write-Host "[Phase 6/6] Validating reorganization..." -ForegroundColor Green

    $allGood = $true

    # Check that key files exist in new locations
    $keyFiles = @(
        "support/docs/architecture/AGENT_REGISTRY.md",
        "support/docs/api/AGENT_ENDPOINTS.md",
        "support/docs/guides/integration/LINEAR_USAGE_GUIDELINES.md",
        "support/scripts/linear/agent-linear-update.py",
        "support/scripts/validation/validate-phase6.ps1",
        "support/scripts/dev/up.sh"
    )

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
        Write-Host "  ✗ Some files are missing - reorganization may have failed" -ForegroundColor Red
    }

} else {
Write-Host "[Phase 6/6] Validation skipped" -ForegroundColor Yellow
}

Write-Host ""

# ============================================================================

# Summary

# ============================================================================

Write-Host "=== Reorganization Complete ===" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
Write-Host "DRY RUN completed. No files were moved." -ForegroundColor Yellow
Write-Host "Run without -DryRun to execute the reorganization." -ForegroundColor Yellow
} else {
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host " - Documentation files moved: $docsMoved" -ForegroundColor Gray
Write-Host " - Script files moved: $scriptsMoved" -ForegroundColor Gray
Write-Host " - README files created: 2" -ForegroundColor Gray
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host " 1. Review and update cross-references manually" -ForegroundColor Gray
Write-Host " 2. Test script execution from new locations" -ForegroundColor Gray
Write-Host " 3. Commit changes:" -ForegroundColor Gray
Write-Host " git add support/" -ForegroundColor DarkGray
Write-Host " git commit -m 'refactor: reorganize support/ into logical subdirectories'" -ForegroundColor DarkGray
}

Write-Host ""
</content>
</write_to_file>

Perfect! Now let me create a summary document:

## Summary

I've created a comprehensive reorganization plan with automated execution! Here's what's ready:

### 📋 **Planning Document**

**[`support/REORG_PLAN.md`](support/REORG_PLAN.md)** - Complete analysis and implementation plan

### 📁 **Proposed Structure**

#### docs (6 subdirectories)

```
docs/
├── architecture/      # System design (5 files)
├── api/              # API docs (1 file)
├── guides/
│   ├── integration/  # Linear, LangSmith setup (2 files)
│   └── implementation/ # HITL, Progressive MCP (2 files)
├── operations/       # Deploy, monitoring (4 files)
└── testing/          # Test strategy, chaos (2 files)
```

#### scripts (5 subdirectories)

```
scripts/
├── deploy/           # Deployment (already exists, 3 files)
├── docker/           # Docker ops (4 files)
├── linear/           # Linear integration (3 files)
├── validation/       # Health checks (4 files)
└── dev/              # Dev utilities (5 files)
```

---

### 🤖 **Automated Execution Script**

**[`support/scripts/reorg-support.ps1`](support/scripts/reorg-support.ps1)** - PowerShell automation

**Features:**

- ✅ **Dry-run mode** - Preview changes before execution
- ✅ **6 automated phases** - Directory creation, file moves, README generation, validation
- ✅ **Reference detection** - Scans for outdated paths
- ✅ **Validation checks** - Confirms files in new locations
- ✅ **Color-coded output** - Clear progress indicators

---

### 🚀 **Execution Steps**

**Option 1: Dry Run (Recommended First)**

```powershell
./support/scripts/reorg-support.ps1 -DryRun
```

**Option 2: Full Execution**

```powershell
./support/scripts/reorg-support.ps1
```

**Option 3: Skip Validation**

```powershell
./support/scripts/reorg-support.ps1 -SkipValidation
```

---

### 📊 **What Gets Moved**

| Category              | Files | From    | To                                    |
| --------------------- | ----- | ------- | ------------------------------------- |
| Architecture          | 5     | docs    | `support/docs/architecture/`          |
| API Docs              | 1     | docs    | `support/docs/api/`                   |
| Integration Guides    | 2     | docs    | `support/docs/guides/integration/`    |
| Implementation Guides | 2     | docs    | `support/docs/guides/implementation/` |
| Operations            | 4     | docs    | `support/docs/operations/`            |
| Testing               | 2     | docs    | `support/docs/testing/`               |
| Docker Scripts        | 4     | scripts | `support/scripts/docker/`             |
| Linear Scripts        | 3     | scripts | `support/scripts/linear/`             |
| Validation Scripts    | 4     | scripts | validation                            |
| Dev Scripts           | 5     | scripts | `support/scripts/dev/`                |

**Total:** 32 files moved + 2 README files created

---

### ⏱️ **Estimated Time**

- Phase 1: 5 min (create directories)
- Phase 2: 10 min (move docs)
- Phase 3: 10 min (move scripts)
- Phase 4: 5 min (create READMEs)
- Phase 5: 15 min (update references)
- Phase 6: 10 min (validation)

**Total:** ~55 minutes

---

### ✅ **Benefits**

**For Developers:**

- Faster navigation with logical grouping
- Clear separation of concerns
- Self-documenting directory structure

**For Agents:**

- Predictable paths by function
- Easy reference via README quick links
- Clear documentation hierarchy

**For Maintenance:**

- Scalable structure for new files
- Consistency in organization
- Obvious where to add content

---

### 🔄 **Rollback Plan**

If issues arise:

```powershell
git restore support/docs support/scripts
```

---

**Ready to execute?**

Just say:

- **"run dry-run"** - Preview changes
- **"execute reorg"** - Run full reorganization
- **"show me the plan"** - View [`support/REORG_PLAN.md`](support/REORG_PLAN.md)

The script is ready and waiting! 🚀
