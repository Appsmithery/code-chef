# Repository Reorganization - Migration Scripts Complete

**Status**: ✅ Scaffolding and automation scripts created  
**Date**: $(Get-Date -Format "yyyy-MM-dd HH:mm")  
**Phase**: Ready for execution

## What's Been Created

### 1. Main Orchestrator Script

**File**: `scripts/migration/migrate-structure.ps1`

- Coordinates all migration steps
- Includes pre-flight checks (git status, Docker running)
- Creates automatic backup before migration
- Runs all sub-scripts in correct order
- Validates migration success
- Supports `-DryRun` mode for safe preview

### 2. Directory Scaffolding

**File**: `scripts/migration/create-agent-dirs.ps1` (has syntax issues)  
**File**: `scripts/migration/scaffold-simple.ps1` (**working version**)

- Creates agent-centric directory structure
- Generates src/, config/, tests/ for each agent
- Creates README.md templates
- **Tested successfully in dry-run mode** ✅

### 3. File Movement Script

**File**: `scripts/migration/move-agent-files.ps1`

- Moves Python source files from `agents/<agent>/` to `agents/<agent>/src/`
- Moves Dockerfiles from `containers/<agent>/` to `agents/<agent>/`
- Moves requirements.txt to agent root
- Migrates MCP gateway from `mcp/gateway/` to `gateway/`

### 4. Dockerfile Updater

**File**: `scripts/migration/update-dockerfiles.ps1`

- Rewrites COPY paths for new structure
- Changes `COPY agents/X/` to `COPY src/`
- Updates shared code paths

### 5. Docker Compose Updater

**File**: `scripts/migration/update-compose.ps1`

- Updates build contexts from `containers/*` to `agents/*`
- Updates volume mount paths
- Moves compose file to `infrastructure/compose/`

### 6. GitHub Actions Updater

**File**: `scripts/migration/update-workflows.ps1`

- Rewrites workflow file paths
- Updates build context paths
- Moves workflows to `infrastructure/.github/workflows/`

### 7. Cleanup Script

**File**: `scripts/migration/cleanup-old-structure.ps1`

- Removes obsolete directories (containers/, mcp/, old compose/)
- Requires explicit confirmation
- Safe to run after validation passes

### 8. Migration Validator

**File**: `scripts/migration/validate-migration.ps1`

- Checks all agents have required structure (src/, Dockerfile, requirements.txt)
- Validates docker-compose.yml uses new paths
- Verifies no old paths remain
- **No changes made** - read-only verification

### 9. Documentation

**File**: `scripts/migration/README.md`

- Complete migration guide
- Step-by-step instructions
- Troubleshooting section
- Rollback procedures
- Post-migration checklist

## How to Use

### Preview Mode (Recommended First Step)

```powershell
.\scripts\migration\migrate-structure.ps1 -DryRun
```

Shows what would be done without making changes.

### Execute Migration

```powershell
# Full migration with backup
.\scripts\migration\migrate-structure.ps1

# Skip backup (faster, not recommended)
.\scripts\migration\migrate-structure.ps1 -SkipBackup
```

### Individual Steps (for troubleshooting)

```powershell
# Just scaffold new directories
.\scripts\migration\scaffold-simple.ps1 -DryRun
.\scripts\migration\scaffold-simple.ps1

# Just validate current structure
.\scripts\migration\validate-migration.ps1

# Just move files
.\scripts\migration\move-agent-files.ps1 -DryRun
```

## Testing Status

✅ **Passed**: `scaffold-simple.ps1 -DryRun` - Successfully previewed directory creation  
⏸️ **Pending**: Full migration execution (waiting for user approval)  
⏸️ **Pending**: Validation after migration  
⏸️ **Pending**: Local Docker Compose build test  
⏸️ **Pending**: CI/CD deployment test

## Known Issues

1. **create-agent-dirs.ps1**: PowerShell parsing error with HERE-strings
   - **Workaround**: Use `scaffold-simple.ps1` instead (tested and working)
   - Both create the same directory structure

## Next Steps (User Actions Required)

1. **Review the plan**: Read `scripts/migration/README.md`
2. **Test dry-run**: Run `.\scripts\migration\migrate-structure.ps1 -DryRun`
3. **Check current status**: Ensure no uncommitted changes (`git status`)
4. **Execute migration**: Run `.\scripts\migration\migrate-structure.ps1`
5. **Validate locally**: Test `docker compose build` with new structure
6. **Commit changes**: `git add -A && git commit -m "refactor: reorganize to agent-centric structure"`
7. **Deploy to droplet**: Push and verify CI/CD pipeline

## Rollback Plan

If migration fails:

```powershell
# Restore from backup
$backup = Get-ChildItem backups/ | Sort-Object Name -Descending | Select-Object -First 1
Copy-Item -Path "$backup/*" -Destination . -Recurse -Force

# Reset services
cd compose
docker compose down
docker compose up -d
```

Backup location: `backups/pre-reorganization-YYYYMMDD-HHmmss/`

## File Manifest

```
scripts/migration/
├── migrate-structure.ps1           # Main orchestrator (READY)
├── create-agent-dirs.ps1           # Directory scaffolding (SYNTAX ERROR)
├── scaffold-simple.ps1             # Directory scaffolding (WORKING) ✅
├── move-agent-files.ps1            # File movement (READY)
├── update-dockerfiles.ps1          # Dockerfile updater (READY)
├── update-compose.ps1              # Compose updater (READY)
├── update-workflows.ps1            # Workflow updater (READY)
├── cleanup-old-structure.ps1       # Cleanup script (READY)
├── validate-migration.ps1          # Validator (READY) ✅
└── README.md                       # Documentation (COMPLETE) ✅
```

## Architecture Snapshot

### Before Migration

```
Dev-Tools/
├── agents/           # Python source
├── containers/       # Dockerfiles
├── compose/          # docker-compose.yml
├── config/           # Shared config
└── .github/          # CI/CD workflows
```

### After Migration

```
Dev-Tools/
├── agents/
│   ├── orchestrator/
│   │   ├── src/              # Python code
│   │   ├── config/           # Agent config
│   │   ├── tests/            # Tests
│   │   ├── Dockerfile        # Build spec
│   │   ├── requirements.txt  # Dependencies
│   │   └── README.md         # Documentation
│   ├── feature-dev/
│   └── _shared/              # Common utilities
├── gateway/                   # MCP gateway (top-level)
└── infrastructure/
    ├── compose/               # Docker orchestration
    ├── config/                # Shared config (.env)
    ├── scripts/               # Deployment scripts
    └── .github/               # CI/CD workflows
```

## References

- **Planning Document**: `docs/_temp/REORGANIZATION_PLAN.md`
- **Migration Guide**: `scripts/migration/README.md`
- **Architecture Instructions**: `.github/copilot-instructions.md`

---

**Ready to proceed?** Run `.\scripts\migration\migrate-structure.ps1 -DryRun` to preview changes.
