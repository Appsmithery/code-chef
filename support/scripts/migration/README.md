# Repository Reorganization Migration Guide

## Quick Start

```powershell
# Preview changes without executing
.\scripts\migration\migrate-structure.ps1 -DryRun

# Execute full migration
.\scripts\migration\migrate-structure.ps1

# Validate without backup (faster)
.\scripts\migration\migrate-structure.ps1 -SkipBackup
```

## What This Does

Transforms the repository from **artifact-based** organization to **agent-centric** organization:

### Before (Artifact-Based)

```
Dev-Tools/
├── agents/
│   ├── orchestrator/
│   ├── feature_dev/
│   └── _shared/
├── containers/
│   ├── orchestrator/
│   └── feature-dev/
├── config/
└── compose/
```

### After (Agent-Centric)

```
Dev-Tools/
├── agents/
│   ├── orchestrator/
│   │   ├── src/          # Python code
│   │   ├── config/       # Agent-specific config
│   │   ├── tests/        # Agent tests
│   │   ├── Dockerfile    # Container build
│   │   ├── requirements.txt
│   │   └── README.md
│   ├── feature-dev/
│   └── _shared/          # Common utilities
├── gateway/
│   ├── src/
│   ├── servers/          # MCP servers
│   └── Dockerfile
└── infrastructure/
    ├── compose/          # Docker orchestration
    ├── config/           # Shared config (.env, etc)
    ├── scripts/          # Deployment scripts
    └── .github/          # CI/CD workflows
```

## Migration Steps

The main script (`migrate-structure.ps1`) orchestrates 8 automated steps:

1. **Pre-flight Checks**: Validate git repo, Docker running, check for uncommitted changes
2. **Create Backup**: Snapshot current structure to `backups/pre-reorganization-TIMESTAMP/`
3. **Create Directory Structure**: Scaffold new agent-centric folders
4. **Move Agent Files**: Copy Python code, Dockerfiles, requirements.txt to new locations
5. **Update Dockerfiles**: Rewrite `COPY` paths for new structure
6. **Update docker-compose.yml**: Rewrite build contexts and volume mounts
7. **Update CI/CD Workflows**: Rewrite GitHub Actions paths
8. **Cleanup Old Structure**: Remove obsolete directories (with confirmation)
9. **Validation**: Verify all agents have required files and Docker config is correct

## Individual Scripts

Each step can be run independently for troubleshooting:

```powershell
# Create new directory structure only
.\scripts\migration\create-agent-dirs.ps1

# Move files only
.\scripts\migration\move-agent-files.ps1

# Update Dockerfiles only
.\scripts\migration\update-dockerfiles.ps1

# Update docker-compose.yml only
.\scripts\migration\update-compose.ps1

# Update GitHub Actions only
.\scripts\migration\update-workflows.ps1

# Validate migration (no changes)
.\scripts\migration\validate-migration.ps1

# Clean up old structure (requires confirmation)
.\scripts\migration\cleanup-old-structure.ps1
```

## Post-Migration Checklist

After running the migration, manually verify:

### 1. Local Testing

```powershell
cd infrastructure/compose
docker compose build
docker compose up
```

Check health endpoints:

```powershell
curl http://localhost:8001/health  # orchestrator
curl http://localhost:8002/health  # feature-dev
# ... etc for all agents
```

### 2. Git Review

```powershell
git status                         # Review changes
git diff                           # Check file modifications
git add -A
git commit -m "refactor: reorganize to agent-centric structure"
```

### 3. CI/CD Validation

```powershell
git push origin main
```

Monitor GitHub Actions workflows:

- Should build all agents from new `agents/*/Dockerfile` paths
- Should push to Docker Hub with correct tags
- Should deploy to droplet successfully

### 4. Droplet Health Check

```bash
ssh root@45.55.173.72
cd /opt/Dev-Tools
docker compose ps                  # Check all services running
curl http://localhost:8000/health  # Gateway
curl http://localhost:8001/health  # Orchestrator
```

### 5. Documentation Updates

- [ ] Update README.md with new directory structure
- [ ] Update DEPLOYMENT.md with new paths
- [ ] Update agent README.md files with specific endpoints
- [ ] Archive old architecture docs to `docs/archive/`

## Rollback

If migration fails, restore from backup:

```powershell
$backup = Get-ChildItem backups/ | Sort-Object Name -Descending | Select-Object -First 1
Copy-Item -Path "$backup/*" -Destination . -Recurse -Force

# Reset compose location
mv infrastructure/compose/docker-compose.yml compose/docker-compose.yml

# Reset workflows
mv infrastructure/.github/workflows .github/

# Restart services
cd compose
docker compose down
docker compose up -d
```

## Common Issues

### Issue: `validate-migration.ps1` fails on Dockerfile paths

**Solution**: Run `update-dockerfiles.ps1` again, check for manual edits

### Issue: Docker build fails with "COPY failed"

**Solution**: Verify `docker-compose.yml` has `context: ../agents/<agent>` not `../containers/<agent>`

### Issue: CI/CD workflow fails

**Solution**: Check `.github/workflows/*.yml` updated paths match new structure

### Issue: Agent can't import shared code

**Solution**: Verify `agents/_shared/` preserved and Dockerfile copies it:

```dockerfile
COPY _shared/ /app/_shared/
COPY src/ /app/
```

## Benefits of New Structure

1. **Self-Contained Agents**: All agent artifacts in one directory
2. **Easier Development**: `cd agents/orchestrator` has everything you need
3. **Clearer Ownership**: Each agent directory is a logical unit
4. **Faster Onboarding**: New contributors see agent structure immediately
5. **Better Modularity**: Easy to extract agents to separate repos later
6. **Simpler CI/CD**: Build context = agent directory

## Questions?

See `docs/_temp/REORGANIZATION_PLAN.md` for the full planning document.

Contact: alex@appsmithery.co
