# Repository Audit & Documentation Update Plan

## Phase 1: Repository Audit

### 1.1 Identify Deprecated Files & Directories

**Scan for old microservices artifacts:**

```powershell
# Find old agent microservice directories (should be removed)
Get-ChildItem -Path . -Directory -Filter "agent_*" -Exclude "agent_orchestrator" | Where-Object {
    $_.Name -match "agent_(feature-dev|code-review|infrastructure|cicd|documentation)"
}

# Find orphaned Docker files
Get-ChildItem -Path . -Recurse -Filter "Dockerfile" | Where-Object {
    $_.Directory.Name -match "agent_(feature-dev|code-review|infrastructure|cicd|documentation)"
}

# Find old requirements.txt files
Get-ChildItem -Path . -Recurse -Filter "requirements.txt" | Where-Object {
    $_.Directory.Name -match "agent_(feature-dev|code-review|infrastructure|cicd|documentation)"
}
```

**Scan for obsolete configuration:**

```powershell
# Find old agent service configs in docker-compose
Select-String -Path "deploy/docker-compose.yml" -Pattern "feature-dev|code-review|infrastructure|cicd|documentation"

# Find old environment variable references
Select-String -Path "config/env/.env" -Pattern "FEATURE_DEV_URL|CODE_REVIEW_URL|INFRASTRUCTURE_URL|CICD_URL|DOCUMENTATION_URL"
```

**Scan for outdated documentation:**

```powershell
# Find docs referencing old architecture
Get-ChildItem -Path "support/docs" -Filter "*.md" -Recurse | ForEach-Object {
    Select-String -Path $_.FullName -Pattern "microservice|agent_feature-dev|agent_code-review|agent_infrastructure|agent_cicd|agent_documentation" -SimpleMatch
}

# Find READMEs in old agent directories
Get-ChildItem -Path . -Filter "README.md" -Recurse | Where-Object {
    $_.Directory.Name -match "agent_(feature-dev|code-review|infrastructure|cicd|documentation)"
}
```

### 1.2 Validate LangGraph Migration Completeness

**Check for import references to old agents:**

```powershell
# Scan Python files for old import paths
Get-ChildItem -Path . -Filter "*.py" -Recurse -Exclude "_archive" | ForEach-Object {
    Select-String -Path $_.FullName -Pattern "from agent_(feature-dev|code-review|infrastructure|cicd|documentation)" -SimpleMatch
}

# Check for HTTP calls to old agent endpoints
Get-ChildItem -Path . -Filter "*.py" -Recurse | ForEach-Object {
    Select-String -Path $_.FullName -Pattern "http://feature-dev:|http://code-review:|http://infrastructure:|http://cicd:|http://documentation:" -SimpleMatch
}
```

**Verify LangGraph files are complete:**

```powershell
# Check agent_orchestrator structure
Test-Path "agent_orchestrator/agents/*.py"
Test-Path "agent_orchestrator/tools/*.yaml"
Test-Path "agent_orchestrator/graph.py"
```

---

## Phase 2: Deprecation & Removal

### 2.1 Remove Old Agent Microservices

**Delete old agent directories:**

```bash
# Backup first (optional)
tar -czf _archive/old-agents-backup-$(date +%Y%m%d).tar.gz \
    agent_feature-dev agent_code-review agent_infrastructure agent_cicd agent_documentation

# Remove old agent directories
rm -rf agent_feature-dev agent_code-review agent_infrastructure agent_cicd agent_documentation
```

**Clean docker-compose.yml:**

```yaml
# Remove these service blocks from deploy/docker-compose.yml:
# - feature-dev (port 8002)
# - code-review (port 8003)
# - infrastructure (port 8004)
# - cicd (port 8005)
# - documentation (port 8006)
```

**Clean environment variables:**

```bash
# Remove from config/env/.env:
# FEATURE_DEV_URL=http://feature-dev:8002
# CODE_REVIEW_URL=http://code-review:8003
# INFRASTRUCTURE_URL=http://infrastructure:8004
# CICD_URL=http://cicd:8005
# DOCUMENTATION_URL=http://documentation:8006
```

### 2.2 Update Configuration Files

**Update `.env.template`:**

```bash
# Remove old agent URLs
# Add LangGraph-specific variables if needed
```

**Update mcp-agent-tool-mapping.yaml:**

```yaml
# Remove entries for old agent microservices
# Consolidate all tool mappings under orchestrator
```

**Update agents-manifest.json:**

```json
# Remove old agent microservice entries
# Update to reflect LangGraph agent nodes
```

---

## Phase 3: Documentation Updates

### 3.1 Core Documentation

**Update README.md (root):**

- Remove references to 6 microservices
- Add LangGraph architecture overview
- Update resource metrics (900MB → 154MB)
- Update deployment instructions

**Update README.md:**

- Document LangGraph workflow
- Add agent node descriptions
- Update API endpoints (`/orchestrate/langgraph`)
- Add progressive tool disclosure section

**Update ARCHITECTURE.md:**

- Replace microservices diagram with LangGraph flow
- Document supervisor routing pattern
- Explain conditional edges and state management
- Add PostgreSQL checkpointing details

### 3.2 Deployment Documentation

**Update DEPLOYMENT_AUTOMATION.md:**

- Remove old agent build steps
- Update resource requirements (2GB now sufficient)
- Document single orchestrator deployment
- Update health check endpoints

**Update `support/docs/DEPLOY.md`:**

- Remove multi-agent deployment steps
- Simplify to single orchestrator + gateway + postgres
- Update verification commands

**Update copilot-instructions.md:**

- Update architecture snapshot
- Remove old agent service URLs
- Document LangGraph agent nodes
- Update resource metrics

### 3.3 Operational Documentation

**Update `support/docs/NOTIFICATION_SYSTEM.md`:**

- Verify still accurate for LangGraph orchestrator
- Update code examples if needed

**Update `support/docs/AGENT_ENDPOINTS.md`:**

- Remove old agent endpoints (ports 8002-8006)
- Document new LangGraph endpoints
- Update health check table

**Create `support/docs/LANGGRAPH_ARCHITECTURE.md`:**

- Detailed LangGraph workflow documentation
- Agent node configurations
- State management patterns
- Tool disclosure strategies

### 3.4 Script Documentation

**Update script headers:**

```bash
# Review all scripts in support/scripts/
# Update comments referencing old architecture
# Remove scripts specific to old agents (if any)
```

---

## Phase 4: Validation & Testing

### 4.1 Automated Validation

**Create validation script:**

```powershell
# support/scripts/validation/validate-langgraph-migration.ps1

# Check no old agent directories exist
# Verify docker-compose.yml has 3 services only
# Confirm .env has no old agent URLs
# Validate all docs updated (keyword scan)
# Test orchestrator health endpoint
# Verify LangGraph workflow compiles
```

### 4.2 Manual Testing Checklist

- [ ] Clone fresh repo, verify no old agent dirs
- [ ] Run `docker compose up -d`, confirm 3 services only
- [ ] Test `/orchestrate/langgraph/status`, verify 6 agents available
- [ ] Submit test task via `/orchestrate/langgraph`, verify workflow executes
- [ ] Check resource usage: <500MB RAM, <1 CPU
- [ ] Verify Linear approval notifications still work
- [ ] Test HITL workflow end-to-end
- [ ] Validate LangSmith tracing captures all agent nodes

### 4.3 Documentation Review Checklist

- [ ] All markdown files updated (no microservices references)
- [ ] Code examples use new LangGraph patterns
- [ ] Architecture diagrams updated
- [ ] API documentation reflects new endpoints
- [ ] Deployment guides simplified
- [ ] Resource metrics updated throughout

---

## Phase 5: Final Cleanup & Commit

### 5.1 Git Operations

```bash
# Stage all changes
git add -A

# Commit with detailed message
git commit -m "refactor: Complete LangGraph migration - remove old agent microservices

BREAKING CHANGE: Removed 5 agent microservices (feature-dev, code-review, infrastructure, cicd, documentation)

- Deleted old agent directories and Docker files
- Cleaned docker-compose.yml (6 services → 3 services)
- Removed old agent URLs from .env
- Updated all documentation to reflect LangGraph architecture
- Updated deployment guides and scripts
- Verified resource usage: 154MB RAM, 0.2% CPU (from 900MB, 100% CPU)

Architecture changes:
- Single orchestrator container with 6 LangGraph agent nodes
- Supervisor routing with conditional edges
- PostgreSQL checkpointing for workflow state
- Progressive tool disclosure with LangChain function calling

All tests passing, droplet deployment validated."

# Push to main
git push origin main
```

### 5.2 Post-Deployment Verification

```powershell
# Deploy to droplet
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType full

# Verify services
ssh root@45.55.173.72 "docker compose ps"

# Check resource usage
ssh root@45.55.173.72 "docker stats --no-stream"

# Test health endpoints
curl http://45.55.173.72:8001/health
curl http://45.55.173.72:8001/orchestrate/langgraph/status
```

### 5.3 Update Linear Roadmap

```powershell
# Mark migration complete in Linear
python support/scripts/linear/agent-linear-update.py update-status --issue-id "DEV-123" --status "done"

# Update phase 4 sub-issues
python support/scripts/linear/agent-linear-update.py update-status --issue-id "DEV-132" --status "done"
```

---

## Summary

**Estimated Timeline:**

- Phase 1 (Audit): 1-2 hours
- Phase 2 (Removal): 30 minutes
- Phase 3 (Documentation): 2-3 hours
- Phase 4 (Validation): 1-2 hours
- Phase 5 (Cleanup): 30 minutes

**Total:** ~6-8 hours

**Deliverables:**

1. Clean repository with no old agent microservices
2. Simplified docker-compose.yml (3 services)
3. Updated documentation across 15+ files
4. Validation scripts for future migrations
5. Comprehensive commit history

**Benefits:**

- 83% memory reduction (900MB → 154MB)
- 99.8% CPU reduction (100% → 0.2%)
- Simplified architecture (easier to maintain)
- Faster deployments (5min vs 30min builds)
- Better documentation accuracy
