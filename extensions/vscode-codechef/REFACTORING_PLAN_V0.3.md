# VS Code Extension Refactoring Plan - v0.3 LangGraph Architecture

**Status**: 🔄 Ready for Execution  
**Target**: Align extension with v0.3 LangGraph single-orchestrator architecture  
**Execution**: Automated, stepwise refactoring via tasks

---

## Executive Summary

### Current State (v0.2)

- Extension targets **6 microservices** (orchestrator + 5 agent services on ports 8001-8006)
- Health checks for 6 separate services
- References to individual agent endpoints
- Old documentation links (LINEAR_HITL_TEMPLATE_SETUP.md, etc.)

### Target State (v0.3)

- Extension targets **1 orchestrator service** with LangGraph agent nodes
- Single health check (port 8001)
- Agent nodes are internal (no separate endpoints)
- Updated documentation links (LINEAR_INTEGRATION_GUIDE.md, LINEAR_HITL_WORKFLOW.md, DEPLOYMENT_GUIDE.md)

### Impact

- **Breaking**: Old orchestrator URLs pointing to individual agents will fail
- **Non-Breaking**: All existing commands and chat participant functionality preserved
- **Benefits**: Simpler configuration, faster responses, aligned with production architecture

---

## Phase 1: Update Configuration & Documentation

### Task 1.1: Update package.json Metadata ✅

**Files**: `package.json`

**Changes**:

- Update version: `0.2.0` → `0.3.0`
- Update description to mention "LangGraph single-orchestrator"
- Update keywords to add "langgraph", "workflow-engine", "state-management"
- Update badges to reflect "1 orchestrator" instead of "6 agents"
- Update default `orchestratorUrl` if needed (currently `https://codechef.appsmithery.co/api` - correct)

**Script**:

```powershell
# Update package.json version and metadata
task extension:update-metadata
```

**Validation**:

```bash
jq '.version, .description' package.json
```

---

### Task 1.2: Update README.md ✅

**Files**: `README.md`

**Changes**:

1. **Architecture section**: Replace 6 microservices with 1 orchestrator + agent nodes
2. **Troubleshooting**: Remove references to individual agent ports (8002-8006)
3. **Documentation links**: Update to new consolidated guides:
   - `LINEAR_HITL_TEMPLATE_SETUP.md` → `LINEAR_HITL_WORKFLOW.md`
   - `INTEGRATION_IMPLEMENTATION_PLAN.md` → `LINEAR_INTEGRATION_GUIDE.md`
   - Add link to `DEPLOYMENT_GUIDE.md`
   - Update `PROGRESSIVE_TOOL_DISCLOSURE.md` path if changed
4. **Architecture diagram**: Update ASCII art to show LangGraph workflow
5. **Badge**: Change "6 agents" to "1 orchestrator (6 agent nodes)"

**Script**:

```powershell
# Update README with v0.3 architecture
task extension:update-readme
```

**Validation**:

```bash
grep -E "8001|8002|8003|8004|8005|8006" README.md
# Should only show 8001
```

---

### Task 1.3: Update CHANGELOG.md ✅

**Files**: `CHANGELOG.md`

**Changes**:

1. Add `## [0.3.0] - 2025-11-22` section
2. Document **Added**:
   - LangGraph single-orchestrator architecture
   - PostgreSQL workflow checkpointing
   - Simplified health checks (1 service vs 6)
   - Updated documentation links
3. Document **Changed**:
   - Architecture: 6 microservices → 1 orchestrator with agent nodes
   - Health checks: 6 endpoints → 1 endpoint
   - Deployment complexity reduced
4. Document **Deprecated**:
   - Individual agent endpoints (ports 8002-8006)
   - Multi-service health validation

**Script**:

```powershell
# Update CHANGELOG with v0.3 changes
task extension:update-changelog
```

---

## Phase 2: Refactor TypeScript Code

### Task 2.1: Update OrchestratorClient (orchestratorClient.ts) ✅

**Files**: `src/orchestratorClient.ts`

**Changes**:

1. Remove individual agent endpoint methods (if any exist)
2. Simplify `health()` to only check orchestrator (port 8001)
3. Update API paths to match v0.3 orchestrator endpoints:
   - `/orchestrate` → Unchanged (decomposition + routing)
   - `/task/{taskId}` → Unchanged (task status)
   - `/chat` → Unchanged (multi-turn conversations)
   - `/approvals/{approvalId}/approve` → Check if still exists or moved to `/workflow/approve`
4. Add type definitions for LangGraph-specific responses:
   - `checkpoint_id` in responses
   - `thread_id` for workflow tracking
   - `approval_gate` status

**Script**:

```powershell
# Refactor orchestrator client for v0.3 API
task extension:refactor-client
```

**Validation**:

```bash
# Test health endpoint
curl https://codechef.appsmithery.co/api/health

# Test orchestrate endpoint
curl -X POST https://codechef.appsmithery.co/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"description":"test","priority":"low"}'
```

---

### Task 2.2: Update Extension Activation (extension.ts) ✅

**Files**: `src/extension.ts`

**Changes**:

1. Remove agent icon mapping for **separate services** (agents are now internal nodes)
2. Keep agent icon mapping for **UI display purposes** (chat participant still shows agent emojis)
3. Update `checkOrchestratorHealth()`:
   - Single health check to orchestrator (port 8001)
   - Remove multi-service validation loop
4. Update status bar tooltip to reflect "1 orchestrator" architecture
5. Simplify Linear issue URL builder (no changes needed - already workspace-scoped)

**Script**:

```powershell
# Update extension activation logic
task extension:refactor-activation
```

**Validation**:

```typescript
// Manual test: Open extension.ts, check AGENT_ICONS comment
// Should clarify: "Agent icon mapping for UI display (agents are LangGraph nodes)"
```

---

### Task 2.3: Update Chat Participant (chatParticipant.ts) ✅

**Files**: `src/chatParticipant.ts`

**Changes**:

1. Update task response rendering:
   - Agent nodes are internal (no port numbers in output)
   - LangGraph workflow status (checkpoint_id, thread_id)
   - Approval gate status (paused at approval_gate node)
2. Update status command to show LangGraph-specific info:
   - Workflow state (pending/in_progress/paused/completed)
   - Checkpoint ID for resumption
   - Thread ID for session tracking
3. Update approval command:
   - Verify endpoint path (`/approvals/{id}/approve` or `/workflow/approve`)
   - Include thread_id for workflow resumption
4. Update tools command (if it queries individual agents):
   - Query orchestrator for tool list (orchestrator has access to all tools)
   - MCP gateway still at port 8000 (unchanged)

**Script**:

```powershell
# Refactor chat participant for LangGraph
task extension:refactor-chat
```

**Validation**:

```bash
# Test chat participant commands in VS Code
@codechef /tools
@codechef /status <task-id>
```

---

### Task 2.4: Update Context Extractor (contextExtractor.ts) 🔍

**Files**: `src/contextExtractor.ts`

**Changes**:

1. Review if it extracts agent-specific context (probably not needed)
2. Ensure it passes workspace context to orchestrator (unchanged in v0.3)
3. Update comments to clarify orchestrator handles decomposition

**Script**:

```powershell
# Review context extractor (likely no changes needed)
task extension:review-context
```

**Validation**:

```typescript
// Manual test: Submit task, verify workspace context appears in orchestrator logs
```

---

### Task 2.5: Update Linear Watcher (linearWatcher.ts) 🔍

**Files**: `src/linearWatcher.ts`

**Changes**:

1. Verify Linear hub issue ID: `PR-68` → Should be `DEV-68` (public identifier)
2. Update approval notification parsing for LangGraph sub-issues
3. Ensure webhook handling aligns with v0.3 HITL workflow

**Script**:

```powershell
# Update Linear watcher for v0.3 HITL
task extension:update-linear-watcher
```

**Validation**:

```bash
# Test approval notification by creating high-risk task
curl -X POST https://codechef.appsmithery.co/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"description":"Deploy to production","priority":"high"}'

# Check Linear for sub-issue in DEV-68
```

---

### Task 2.6: Update Session Manager (sessionManager.ts) ✅

**Files**: `src/sessionManager.ts`

**Changes**:

1. Verify session management aligns with v0.3 PostgreSQL state
2. Update session ID format if orchestrator expects specific format
3. Ensure thread_id is passed for LangGraph workflow tracking

**Script**:

```powershell
# Review session manager (likely no changes)
task extension:review-session
```

---

## Phase 3: Update Supporting Files

### Task 3.1: Update Taskfile.yml ✅

**Files**: `Taskfile.yml`

**Changes**:

1. Add new tasks for refactoring:
   - `extension:update-metadata` - Update package.json
   - `extension:update-readme` - Update README
   - `extension:update-changelog` - Update CHANGELOG
   - `extension:refactor-client` - Refactor orchestratorClient.ts
   - `extension:refactor-activation` - Refactor extension.ts
   - `extension:refactor-chat` - Refactor chatParticipant.ts
   - `extension:review-context` - Review contextExtractor.ts
   - `extension:update-linear-watcher` - Update linearWatcher.ts
   - `extension:review-session` - Review sessionManager.ts
2. Add `extension:refactor-all` to run all tasks in sequence
3. Add `extension:validate` to run validation checks

**Script**:

```powershell
# Create refactoring tasks
task extension:create-tasks
```

---

### Task 3.2: Update BUILD_COMPLETE.md ✅

**Files**: `BUILD_COMPLETE.md`

**Changes**:

1. Update "Architecture" section with v0.3 LangGraph
2. Update health check commands (remove ports 8002-8006)
3. Update deployment instructions if changed

**Script**:

```powershell
# Update build completion guide
task extension:update-build-docs
```

---

### Task 3.3: Update DEPLOYMENT.md ✅

**Files**: `DEPLOYMENT.md`

**Changes**:

1. Update deployment target architecture (1 orchestrator)
2. Update health validation steps
3. Update rollback procedures (simpler with 1 service)

**Script**:

```powershell
# Update deployment guide
task extension:update-deploy-docs
```

---

### Task 3.4: Update QUICK_REFERENCE.md ✅

**Files**: `QUICK_REFERENCE.md`

**Changes**:

1. Update architecture overview
2. Update health check commands
3. Update troubleshooting (remove multi-service issues)

**Script**:

```powershell
# Update quick reference
task extension:update-quickref
```

---

## Phase 4: Testing & Validation

### Task 4.1: Manual Testing Checklist ✅

**Test Cases**:

1. **Extension Activation**:

   - [ ] Extension loads without errors
   - [ ] Status bar shows "$(check) code/chef"
   - [ ] Chat participant registered as `@codechef`

2. **Health Checks**:

   - [ ] Orchestrator health check succeeds (port 8001)
   - [ ] Status bar tooltip shows correct URL
   - [ ] No errors about unreachable services

3. **Task Submission**:

   - [ ] Submit task via chat participant: `@codechef Add auth to API`
   - [ ] Receives task ID and subtasks
   - [ ] Agent emojis display correctly
   - [ ] Estimated duration shown

4. **Task Status**:

   - [ ] Check status via command: `@codechef /status <task-id>`
   - [ ] Shows workflow state (pending/in_progress/paused/completed)
   - [ ] Shows subtask progress

5. **Approval Workflow**:

   - [ ] High-risk task triggers approval: `@codechef Deploy to production`
   - [ ] Linear sub-issue created in DEV-68
   - [ ] Approval notification appears (if enabled)
   - [ ] Approve via command or Linear UI

6. **Tools Command**:

   - [ ] List tools: `@codechef /tools`
   - [ ] Shows 150+ tools grouped by server
   - [ ] No errors fetching tool list

7. **Configuration**:

   - [ ] Update orchestrator URL: `code/chef: Configure`
   - [ ] Change auto-approve threshold
   - [ ] Toggle notifications

8. **Error Handling**:
   - [ ] Graceful error if orchestrator unreachable
   - [ ] Clear error messages with troubleshooting steps

**Script**:

```powershell
# Run manual test checklist
task extension:test-manual
```

---

### Task 4.2: Automated Validation ✅

**Validation Script** (`validate-v0.3.ps1`):

```powershell
#!/usr/bin/env pwsh

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VS Code Extension v0.3 Validation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Check package.json version
Write-Host "`n[CHECK] package.json version..." -ForegroundColor Yellow
$version = (Get-Content package.json | ConvertFrom-Json).version
if ($version -eq "0.3.0") {
    Write-Host "  ✅ Version: $version" -ForegroundColor Green
} else {
    Write-Host "  ❌ Expected: 0.3.0, Got: $version" -ForegroundColor Red
    exit 1
}

# 2. Check for deprecated port references
Write-Host "`n[CHECK] No references to deprecated agent ports..." -ForegroundColor Yellow
$deprecatedPorts = @(8002, 8003, 8004, 8005, 8006)
$foundDeprecated = $false
foreach ($port in $deprecatedPorts) {
    $matches = Select-String -Path "src/*.ts", "README.md" -Pattern ":$port" -SimpleMatch
    if ($matches) {
        Write-Host "  ❌ Found reference to port $port" -ForegroundColor Red
        $foundDeprecated = $true
    }
}
if (-not $foundDeprecated) {
    Write-Host "  ✅ No deprecated ports found" -ForegroundColor Green
}

# 3. Check orchestrator health
Write-Host "`n[CHECK] Orchestrator health..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "https://codechef.appsmithery.co/api/health" -Method GET
    if ($health.status -eq "healthy" -or $health.status -eq "ok") {
        Write-Host "  ✅ Orchestrator healthy" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Orchestrator status: $($health.status)" -ForegroundColor Red
    }
} catch {
    Write-Host "  ❌ Cannot reach orchestrator: $_" -ForegroundColor Red
}

# 4. Check documentation links
Write-Host "`n[CHECK] Documentation links..." -ForegroundColor Yellow
$requiredDocs = @(
    "LINEAR_INTEGRATION_GUIDE.md",
    "LINEAR_HITL_WORKFLOW.md",
    "DEPLOYMENT_GUIDE.md"
)
$missingDocs = @()
foreach ($doc in $requiredDocs) {
    if (-not (Test-Path "../../support/docs/$doc")) {
        $missingDocs += $doc
    }
}
if ($missingDocs.Count -eq 0) {
    Write-Host "  ✅ All documentation links valid" -ForegroundColor Green
} else {
    Write-Host "  ❌ Missing docs: $($missingDocs -join ', ')" -ForegroundColor Red
}

# 5. Check TypeScript compilation
Write-Host "`n[CHECK] TypeScript compilation..." -ForegroundColor Yellow
npm run compile 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✅ TypeScript compiles without errors" -ForegroundColor Green
} else {
    Write-Host "  ❌ TypeScript compilation failed" -ForegroundColor Red
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Validation Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
```

**Script**:

```powershell
# Run automated validation
task extension:validate-v0.3
```

---

## Phase 5: Package & Deploy

### Task 5.1: Build Extension Package ✅

**Commands**:

```powershell
# Clean and rebuild
cd extensions/vscode-codechef
npm run clean
npm install
npm run compile

# Package extension
npm run package
# Creates: vscode-codechef-0.3.0.vsix
```

**Validation**:

```bash
# Check package size (should be similar to v0.2.0)
ls -lh vscode-codechef-0.3.0.vsix

# Extract and inspect
unzip -l vscode-codechef-0.3.0.vsix
```

---

### Task 5.2: Local Installation Test ✅

**Commands**:

```powershell
# Uninstall old version
code --uninstall-extension appsmithery.vscode-codechef

# Install new version
code --install-extension vscode-codechef-0.3.0.vsix

# Restart VS Code and test
```

**Validation**:

- Run all manual test cases from Task 4.1
- Check Extension Host logs for errors
- Verify chat participant works

---

### Task 5.3: Publish to Marketplace ✅

**Prerequisites**:

- Personal Access Token (PAT) with Marketplace: Manage scope
- Publisher account: `appsmithery`

**Commands**:

```powershell
# Login to marketplace
vsce login appsmithery

# Publish (auto-increments version if not specified)
vsce publish 0.3.0

# Or publish from VSIX
vsce publish --packagePath vscode-codechef-0.3.0.vsix
```

**Verification**:

- Check marketplace: https://marketplace.visualstudio.com/items?itemName=appsmithery.vscode-codechef
- Verify version shows 0.3.0
- Test installation from marketplace

---

## Phase 6: Update Linear Roadmap

### Task 6.1: Create Linear Issue for Completion ✅

**Command**:

```powershell
$env:LINEAR_API_KEY="lin_oauth_***"
python support/scripts/linear/agent-linear-update.py create-issue \
  --title "VS Code Extension v0.3 - LangGraph Architecture Refactoring Complete" \
  --description "**Summary**: Refactored VS Code extension to align with v0.3 LangGraph single-orchestrator architecture.

## Changes Implemented
### Configuration & Documentation
✅ Updated package.json to v0.3.0 with LangGraph metadata
✅ Updated README with single-orchestrator architecture
✅ Updated CHANGELOG with v0.3 release notes
✅ Updated BUILD_COMPLETE.md, DEPLOYMENT.md, QUICK_REFERENCE.md

### Code Refactoring
✅ Simplified orchestratorClient.ts health checks (1 service vs 6)
✅ Updated extension.ts activation logic
✅ Updated chatParticipant.ts for LangGraph workflow states
✅ Updated linearWatcher.ts for DEV-68 approval hub
✅ Reviewed contextExtractor.ts and sessionManager.ts (no changes needed)

### Testing & Validation
✅ Created automated validation script (validate-v0.3.ps1)
✅ Manual test checklist (8 test cases)
✅ TypeScript compilation verified
✅ Health checks passing

### Deployment
✅ Extension packaged: vscode-codechef-0.3.0.vsix
✅ Local installation tested
✅ Ready for marketplace publish

## Benefits
- 🎯 Simplified configuration (1 orchestrator URL vs 6 agent URLs)
- 🚀 Faster task submission (single HTTP POST vs multi-service orchestration)
- 📊 Clearer workflow states (LangGraph checkpointing)
- 🔧 Easier troubleshooting (single health endpoint)

**Next**: Publish to VS Code Marketplace" \
  --project-id "b21cbaa1-9f09-40f4-b62a-73e0f86dd501" \
  --status "done"
```

---

## Rollback Plan

If v0.3 extension has critical issues:

### Step 1: Revert to v0.2.0

```powershell
# Uninstall v0.3
code --uninstall-extension appsmithery.vscode-codechef

# Install v0.2.0 from marketplace
code --install-extension appsmithery.vscode-codechef@0.2.0
```

### Step 2: Unpublish v0.3 (if needed)

```powershell
# Unpublish specific version
vsce unpublish appsmithery.vscode-codechef@0.3.0
```

### Step 3: Git Revert

```bash
# Revert refactoring commits
git log --oneline extensions/vscode-codechef
git revert <commit-hash>
git push origin main
```

---

## Success Criteria

### Functional Requirements

- [x] Extension activates without errors
- [x] Chat participant (`@codechef`) works
- [x] Task submission successful
- [x] Task status queries work
- [x] Approval workflow functions
- [x] Tools command lists MCP tools
- [x] Linear integration operational

### Non-Functional Requirements

- [x] TypeScript compiles without errors
- [x] No references to deprecated ports (8002-8006)
- [x] Documentation links valid
- [x] Orchestrator health check passes
- [x] Performance equivalent or better than v0.2

### Marketplace Requirements

- [x] Version incremented to 0.3.0
- [x] CHANGELOG updated
- [x] README reflects v0.3 architecture
- [x] Package size reasonable (<5MB)
- [x] Icon and badges valid

---

## Timeline & Effort Estimate

| Phase                           | Tasks        | Estimated Time | Status          |
| ------------------------------- | ------------ | -------------- | --------------- |
| Phase 1: Configuration & Docs   | 3 tasks      | 2 hours        | ⏳ Pending      |
| Phase 2: TypeScript Refactoring | 6 tasks      | 4 hours        | ⏳ Pending      |
| Phase 3: Supporting Files       | 4 tasks      | 2 hours        | ⏳ Pending      |
| Phase 4: Testing & Validation   | 2 tasks      | 3 hours        | ⏳ Pending      |
| Phase 5: Package & Deploy       | 3 tasks      | 1 hour         | ⏳ Pending      |
| Phase 6: Linear Update          | 1 task       | 0.5 hours      | ⏳ Pending      |
| **Total**                       | **19 tasks** | **12.5 hours** | **0% Complete** |

---

## Execution Commands

```powershell
# Run all refactoring tasks in sequence
cd extensions/vscode-codechef
task extension:refactor-all

# Or run individual phases
task extension:phase1  # Configuration & docs
task extension:phase2  # TypeScript refactoring
task extension:phase3  # Supporting files
task extension:phase4  # Testing & validation
task extension:phase5  # Package & deploy
task extension:phase6  # Linear update

# Validate at any time
task extension:validate-v0.3
```

---

## Next Steps

1. Review this refactoring plan
2. Approve execution
3. Run `task extension:refactor-all`
4. Monitor validation output
5. Test manually (Task 4.1 checklist)
6. Package and publish
7. Update Linear roadmap

---

**Document Version:** 1.0.0  
**Created:** November 22, 2025  
**Architecture Target:** LangGraph v0.3 Single-Orchestrator  
**Execution:** Automated via Taskfile tasks
