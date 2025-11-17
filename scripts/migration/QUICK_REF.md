# Migration Quick Reference

## ⚡ Fast Commands

```powershell
# Preview what will happen
.\scripts\migration\migrate-structure.ps1 -DryRun

# Execute full migration
.\scripts\migration\migrate-structure.ps1

# Just scaffold directories (tested & working)
.\scripts\migration\scaffold-simple.ps1

# Validate current structure
.\scripts\migration\validate-migration.ps1
```

## 📋 Pre-Flight Checklist

- [ ] All changes committed (`git status` is clean)
- [ ] Docker Desktop is running
- [ ] No containers using old paths
- [ ] Backed up `.env` file (if modified)
- [ ] Read `scripts/migration/README.md`

## 🎯 Migration Steps (Automated)

1. Pre-flight checks
2. Create backup → `backups/pre-reorganization-TIMESTAMP/`
3. Create new directory structure
4. Move files from old to new locations
5. Update Dockerfiles (COPY paths)
6. Update docker-compose.yml (build contexts)
7. Update GitHub Actions (workflow paths)
8. Cleanup old structure (with confirmation)
9. Validate migration

## ✅ Post-Migration Validation

```powershell
# Local Docker test
cd infrastructure/compose
docker compose build
docker compose up

# Check health endpoints
curl http://localhost:8001/health  # orchestrator
curl http://localhost:8002/health  # feature-dev

# Commit changes
git add -A
git commit -m "refactor: reorganize to agent-centric structure"

# Deploy
git push origin main
```

## 🚨 Rollback

```powershell
$backup = Get-ChildItem backups/ | Sort-Object Name -Descending | Select-Object -First 1
Copy-Item -Path "$backup/*" -Destination . -Recurse -Force
cd compose; docker compose down; docker compose up -d
```

## 📁 New Structure

```
agents/
  orchestrator/
    src/          ← Python code
    config/       ← Agent config
    tests/        ← Tests
    Dockerfile    ← Build spec
    requirements.txt
    README.md
  feature-dev/
  _shared/        ← Common code

gateway/          ← MCP gateway (root level)

infrastructure/
  compose/        ← docker-compose.yml
  config/         ← .env, secrets
  scripts/        ← Deployment
  .github/        ← CI/CD
```

## 🔍 Troubleshooting

| Issue                                | Solution                                     |
| ------------------------------------ | -------------------------------------------- |
| Parse error in create-agent-dirs.ps1 | Use `scaffold-simple.ps1` instead            |
| Docker build fails                   | Check `update-dockerfiles.ps1` ran correctly |
| Compose can't find contexts          | Check `update-compose.ps1` completed         |
| CI/CD fails                          | Verify `update-workflows.ps1` updated paths  |
| Import errors in agents              | Ensure `_shared/` preserved correctly        |

## 📊 Status Check

```powershell
# Verify structure exists
Get-ChildItem agents/orchestrator/     # Should show: src/, config/, tests/, Dockerfile, requirements.txt

# Verify compose config
Select-String "context: ../agents/" infrastructure/compose/docker-compose.yml

# Verify workflows
Select-String "agents/.*/src/" infrastructure/.github/workflows/*.yml
```

## 🎓 Key Changes

| Old Path                             | New Path                                    |
| ------------------------------------ | ------------------------------------------- |
| `agents/orchestrator/*.py`           | `agents/orchestrator/src/*.py`              |
| `containers/orchestrator/Dockerfile` | `agents/orchestrator/Dockerfile`            |
| `compose/docker-compose.yml`         | `infrastructure/compose/docker-compose.yml` |
| `config/env/.env`                    | `infrastructure/config/env/.env`            |
| `.github/workflows/`                 | `infrastructure/.github/workflows/`         |
| `mcp/gateway/`                       | `gateway/src/`                              |

## ⏱️ Estimated Time

- Dry-run: 30 seconds
- Full migration: 2-3 minutes
- Local Docker build test: 5-10 minutes
- CI/CD deployment: 8-12 minutes

---

**Questions?** See `scripts/migration/README.md` for detailed documentation.
