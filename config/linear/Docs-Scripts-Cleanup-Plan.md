# Support Directory Cleanup Plan

## Current State Analysis

### `support/docs/` - 27 loose files at root

**Architecture/Design (9 files):**

- ARCHITECTURE.md
- DEPLOYMENT_ARCHITECTURE.md
- HYBRID_ARCHITECTURE.md
- MULTI_AGENT_WORKFLOWS.md
- TASK_ORCHESTRATION.md
- SHARED_LIB_NOTIFICATIONS.md
- MCP_INTEGRATION.md
- LANGGRAPH_INTEGRATION.md
- RAG_DOCUMENTATION_AGGREGATION.md

**Deployment/Operations (9 files):**

- DEPLOYMENT.md
- DIGITALOCEAN_QUICK_DEPLOY.md
- DOCKER_CLEANUP.md
- DOCKER_HUB_DEPLOYMENT.md
- DOCR-implementation.md
- PRE_DEPLOYMENT_CHECKLIST.md
- SECRETS_MANAGEMENT.md
- PROMETHEUS_METRICS.md
- QDRANT_COLLECTIONS.md

**Integration Guides (4 files):**

- GRADIENT_AI_QUICK_START.md
- LANGSMITH_EXAMPLES.md
- LANGSMITH_TRACING.md
- LLM_MULTI_PROVIDER.md

**User Guides (2 files):**

- SETUP_GUIDE.md
- HANDBOOK.md

**Frontend (1 file):**

- CONFIGURE_AGENTS_UI.md
- FRONTEND_INTEGRATION.md

**Outdated/Completed (2 files):**

- PHASE_6_COMPLETE.md → \_archive or remove
- Docs-Scripts-Reorg.md → \_archive or remove

### `support/scripts/` - 19 loose files at root

**Workflow Examples (3 files):**

- example_workflow_code_review_dev.py
- example_workflow_parallel_docs.py
- example_workflow_review_deploy.py

**Workflow Executors (3 files):**

- workflow_monitor.py
- workflow_pr_deploy.py
- workflow_self_healing.py

**Testing Scripts (5 files):**

- test-chat-endpoint.py
- test_inter_agent_communication.py
- test_resource_locks.py
- test_workflow_state.py
- list-gradient-models.py

**Initialization Scripts (2 files):**

- init-resource-locks.ps1
- init-workflow-state.ps1

**Migration/Maintenance (2 files):**

- analyze_imports.py
- fix_deprecated_imports.py

**Registry/Admin (2 files):**

- generate-registry-integration.py
- connect-linear-project.ps1

**Linear Integration (1 file):**

- update-roadmap-with-approvals.py

**Docker Operations (1 file):**

- prune-dockerhub-manual.ps1

**Meta (1 file):**

- reorg-support.ps1 → keep at root (reorganization tool)

---

## Proposed Reorganization

### `support/docs/` → Target: 3 files at root (README.md, ARCHITECTURE.md, SETUP_GUIDE.md)

#### Move to `architecture/`

- [x] DEPLOYMENT_ARCHITECTURE.md
- [x] HYBRID_ARCHITECTURE.md
- [x] MULTI_AGENT_WORKFLOWS.md
- [x] TASK_ORCHESTRATION.md
- [x] SHARED_LIB_NOTIFICATIONS.md
- [x] MCP_INTEGRATION.md
- [x] LANGGRAPH_INTEGRATION.md
- [x] LANGGRAPH_QUICK_REF.md
- [x] RAG_DOCUMENTATION_AGGREGATION.md

#### Move to `operations/`

- [x] DEPLOYMENT.md
- [x] DIGITALOCEAN_QUICK_DEPLOY.md
- [x] DOCKER_CLEANUP.md
- [x] DOCKER_HUB_DEPLOYMENT.md
- [x] DOCR-implementation.md
- [x] PRE_DEPLOYMENT_CHECKLIST.md
- [x] SECRETS_MANAGEMENT.md
- [x] PROMETHEUS_METRICS.md
- [x] QDRANT_COLLECTIONS.md

#### Move to `guides/integration/`

- [x] GRADIENT_AI_QUICK_START.md
- [x] LANGSMITH_EXAMPLES.md
- [x] LANGSMITH_TRACING.md
- [x] LLM_MULTI_PROVIDER.md

#### Move to `guides/` (general guides)

- [x] HANDBOOK.md
- [x] CONFIGURE_AGENTS_UI.md
- [x] FRONTEND_INTEGRATION.md

#### Archive or Remove

- [x] PHASE_6_COMPLETE.md → Move to `_archive/` or delete
- [x] Docs-Scripts-Reorg.md → Move to `_archive/` (this is a planning doc)

#### Keep at Root (3 files)

- README.md (index/navigation)
- ARCHITECTURE.md (primary overview)
- SETUP_GUIDE.md (first-stop for new users)

---

### `support/scripts/` → Target: 2 files at root (README.md, reorg-support.ps1)

#### Create `workflow/` subdirectory (if not exists) and move:

- [x] example_workflow_code_review_dev.py
- [x] example_workflow_parallel_docs.py
- [x] example_workflow_review_deploy.py
- [x] workflow_monitor.py
- [x] workflow_pr_deploy.py
- [x] workflow_self_healing.py

#### Create `testing/` or merge into `validation/`:

- [x] test-chat-endpoint.py
- [x] test_inter_agent_communication.py
- [x] test_resource_locks.py
- [x] test_workflow_state.py
- [x] list-gradient-models.py

#### Create `init/` or `setup/` subdirectory:

- [x] init-resource-locks.ps1
- [x] init-workflow-state.ps1

#### Move to existing subdirectories:

- [x] prune-dockerhub-manual.ps1 → `docker/`
- [x] update-roadmap-with-approvals.py → `linear/`
- [x] connect-linear-project.ps1 → `linear/`

#### Create `maintenance/` or move to `admin/`:

- [x] analyze_imports.py
- [x] fix_deprecated_imports.py
- [x] generate-registry-integration.py

#### Keep at Root (2 files)

- README.md (index/navigation)
- reorg-support.ps1 (reorganization tool)

---

## Implementation Steps

### Phase 1: Backup Current State (5 minutes)

```powershell
# Create timestamped backup
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
Compress-Archive -Path "support/docs/*","support/scripts/*" -DestinationPath "_archive/support-cleanup-backup-$timestamp.zip"
```

### Phase 2: Create Missing Subdirectories (2 minutes)

```powershell
# Scripts subdirectories
New-Item -ItemType Directory -Force -Path "support/scripts/workflow"
New-Item -ItemType Directory -Force -Path "support/scripts/testing"
New-Item -ItemType Directory -Force -Path "support/scripts/init"
New-Item -ItemType Directory -Force -Path "support/scripts/maintenance"

# Docs subdirectory (chatmodes already exists, just confirm)
Get-Item "support/docs/chatmodes" -ErrorAction SilentlyContinue
```

### Phase 3: Move Documentation Files (10 minutes)

```powershell
# To architecture/
Move-Item "support/docs/DEPLOYMENT_ARCHITECTURE.md" "support/docs/architecture/"
Move-Item "support/docs/HYBRID_ARCHITECTURE.md" "support/docs/architecture/"
Move-Item "support/docs/MULTI_AGENT_WORKFLOWS.md" "support/docs/architecture/"
Move-Item "support/docs/TASK_ORCHESTRATION.md" "support/docs/architecture/"
Move-Item "support/docs/SHARED_LIB_NOTIFICATIONS.md" "support/docs/architecture/"
Move-Item "support/docs/MCP_INTEGRATION.md" "support/docs/architecture/"
Move-Item "support/docs/LANGGRAPH_INTEGRATION.md" "support/docs/architecture/"
Move-Item "support/docs/LANGGRAPH_QUICK_REF.md" "support/docs/architecture/"
Move-Item "support/docs/RAG_DOCUMENTATION_AGGREGATION.md" "support/docs/architecture/"

# To operations/
Move-Item "support/docs/DEPLOYMENT.md" "support/docs/operations/"
Move-Item "support/docs/DIGITALOCEAN_QUICK_DEPLOY.md" "support/docs/operations/"
Move-Item "support/docs/DOCKER_CLEANUP.md" "support/docs/operations/"
Move-Item "support/docs/DOCKER_HUB_DEPLOYMENT.md" "support/docs/operations/"
Move-Item "support/docs/DOCR-implementation.md" "support/docs/operations/"
Move-Item "support/docs/PRE_DEPLOYMENT_CHECKLIST.md" "support/docs/operations/"
Move-Item "support/docs/SECRETS_MANAGEMENT.md" "support/docs/operations/"
Move-Item "support/docs/PROMETHEUS_METRICS.md" "support/docs/operations/"
Move-Item "support/docs/QDRANT_COLLECTIONS.md" "support/docs/operations/"

# To guides/integration/
Move-Item "support/docs/GRADIENT_AI_QUICK_START.md" "support/docs/guides/integration/"
Move-Item "support/docs/LANGSMITH_EXAMPLES.md" "support/docs/guides/integration/"
Move-Item "support/docs/LANGSMITH_TRACING.md" "support/docs/guides/integration/"
Move-Item "support/docs/LLM_MULTI_PROVIDER.md" "support/docs/guides/integration/"

# To guides/ (general)
Move-Item "support/docs/HANDBOOK.md" "support/docs/guides/"
Move-Item "support/docs/CONFIGURE_AGENTS_UI.md" "support/docs/guides/"
Move-Item "support/docs/FRONTEND_INTEGRATION.md" "support/docs/guides/"

# Archive or delete
Move-Item "support/docs/PHASE_6_COMPLETE.md" "_archive/docs-historical/" -Force
Move-Item "support/docs/Docs-Scripts-Reorg.md" "_archive/docs-historical/" -Force
```

### Phase 4: Move Script Files (10 minutes)

```powershell
# To workflow/
Move-Item "support/scripts/example_workflow_code_review_dev.py" "support/scripts/workflow/"
Move-Item "support/scripts/example_workflow_parallel_docs.py" "support/scripts/workflow/"
Move-Item "support/scripts/example_workflow_review_deploy.py" "support/scripts/workflow/"
Move-Item "support/scripts/workflow_monitor.py" "support/scripts/workflow/"
Move-Item "support/scripts/workflow_pr_deploy.py" "support/scripts/workflow/"
Move-Item "support/scripts/workflow_self_healing.py" "support/scripts/workflow/"

# To testing/ (or validation/)
Move-Item "support/scripts/test-chat-endpoint.py" "support/scripts/testing/"
Move-Item "support/scripts/test_inter_agent_communication.py" "support/scripts/testing/"
Move-Item "support/scripts/test_resource_locks.py" "support/scripts/testing/"
Move-Item "support/scripts/test_workflow_state.py" "support/scripts/testing/"
Move-Item "support/scripts/list-gradient-models.py" "support/scripts/testing/"

# To init/
Move-Item "support/scripts/init-resource-locks.ps1" "support/scripts/init/"
Move-Item "support/scripts/init-workflow-state.ps1" "support/scripts/init/"

# To existing subdirectories
Move-Item "support/scripts/prune-dockerhub-manual.ps1" "support/scripts/docker/"
Move-Item "support/scripts/update-roadmap-with-approvals.py" "support/scripts/linear/"
Move-Item "support/scripts/connect-linear-project.ps1" "support/scripts/linear/"

# To maintenance/ (or admin/)
Move-Item "support/scripts/analyze_imports.py" "support/scripts/maintenance/"
Move-Item "support/scripts/fix_deprecated_imports.py" "support/scripts/maintenance/"
Move-Item "support/scripts/generate-registry-integration.py" "support/scripts/maintenance/"
```

### Phase 5: Update README Files (5 minutes)

Update `support/docs/README.md` to reflect:

- Minimal root (3 files)
- New file locations
- Updated quick links

Update `support/scripts/README.md` to reflect:

- Minimal root (2 files)
- New subdirectories (workflow/, testing/, init/, maintenance/)
- Updated command examples

### Phase 6: Update Cross-References (10 minutes)

Search and update references in:

- `.github/copilot-instructions.md`
- `config/linear/*.md`
- `deploy/docker-compose.yml` (volume mounts)
- Agent `main.py` files (if any hardcoded paths)
- Other markdown files

### Phase 7: Validate & Commit (5 minutes)

```powershell
# Verify key files exist
Test-Path "support/docs/ARCHITECTURE.md"
Test-Path "support/docs/architecture/MCP_INTEGRATION.md"
Test-Path "support/scripts/workflow/workflow_monitor.py"
Test-Path "support/scripts/testing/test-chat-endpoint.py"

# Commit changes
git add support/
git commit -m "refactor: minimize root files in support/ subdirectories

- Moved 24 docs from root to subdirectories (27→3 files at root)
- Moved 17 scripts from root to subdirectories (19→2 files at root)
- Added workflow/, testing/, init/, maintenance/ script subdirectories
- Archived outdated files (PHASE_6_COMPLETE.md, Docs-Scripts-Reorg.md)
- Updated README files with new structure
- Updated cross-references in copilot-instructions.md"
```

---

## Expected Results

### Before

```
support/docs/        (27 files at root + subdirs)
support/scripts/     (19 files at root + subdirs)
```

### After

```
support/docs/
├── README.md                 # Navigation
├── ARCHITECTURE.md           # Primary overview
├── SETUP_GUIDE.md            # Getting started
├── architecture/             # 14 files (5 existing + 9 new)
├── api/                      # 1 file
├── guides/                   # 3 files
│   ├── integration/          # 6 files (2 existing + 4 new)
│   └── implementation/       # 1 file
├── operations/               # 10 files (1 existing + 9 new)
├── testing/                  # (existing)
└── chatmodes/                # (existing)

support/scripts/
├── README.md                 # Navigation
├── reorg-support.ps1         # Cleanup tool
├── admin/                    # (existing)
├── agents/                   # (existing)
├── config/                   # (existing)
├── data/                     # (existing)
├── deploy/                   # (existing)
├── dev/                      # (existing)
├── docker/                   # 4+ files
├── linear/                   # 6 files (3 existing + 3 new)
├── validation/               # (existing)
├── workflow/                 # 6 files (new)
├── testing/                  # 5 files (new)
├── init/                     # 2 files (new)
└── maintenance/              # 3 files (new)
```

---

## Benefits

- ✅ **Minimal Root Clutter** - Only essential files at root
- ✅ **Logical Grouping** - Files organized by purpose
- ✅ **Easy Navigation** - Clear subdirectory structure
- ✅ **Scalable** - Room for future additions
- ✅ **Archived History** - Outdated files preserved in `_archive/`

---

## Rollback Plan

```powershell
# Restore from backup
$backupFile = Get-ChildItem "_archive/support-cleanup-backup-*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Expand-Archive -Path $backupFile.FullName -DestinationPath "." -Force
```

---

**Ready to execute?** Say "proceed with cleanup" to start automated execution.
