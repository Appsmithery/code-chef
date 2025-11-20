# Repository Cleanup Plan - November 19, 2025

## Overview

This document identifies deprecated/irrelevant files in `support/docs/` and `support/scripts/` for cleanup after Phase 6 completion.

---

## 📋 Deprecated Linear Scripts (Can be Archived/Removed)

### **Reason**: Replaced by `agent-linear-update.py` (project-agnostic, unified script)

| File                                       | Status        | Reason                                          | Action      |
| ------------------------------------------ | ------------- | ----------------------------------------------- | ----------- |
| `support/scripts/update-linear-phase2.py`  | ❌ Deprecated | Phase-specific, use agent-linear-update.py      | **ARCHIVE** |
| `support/scripts/update-linear-phase5.py`  | ❌ Deprecated | Phase-specific, use agent-linear-update.py      | **ARCHIVE** |
| `support/scripts/update-linear-phase6.py`  | ❌ Deprecated | Phase-specific, use agent-linear-update.py      | **ARCHIVE** |
| `support/scripts/update-phase5-linear.py`  | ❌ Deprecated | Duplicate of update-linear-phase5.py            | **ARCHIVE** |
| `support/scripts/update-linear-graphql.py` | ❌ Deprecated | Generic updates now in agent-linear-update.py   | **ARCHIVE** |
| `support/scripts/create-hitl-subtasks.py`  | ❌ Deprecated | Replaced by agent-linear-update.py create-phase | **ARCHIVE** |
| `support/scripts/mark-hitl-complete.py`    | ❌ Deprecated | Use agent-linear-update.py update-status        | **ARCHIVE** |

**Keep**:

- ✅ `agent-linear-update.py` - Primary script (project-agnostic)
- ✅ `get-linear-project-uuid.py` - Utility for discovering project UUIDs
- ✅ `update-linear-pr68.py` - HITL approval hub (manual fallback)

---

## 📋 Phase-Specific Task Scripts (Can be Archived)

### **Reason**: Phase 5/6 completed, historical artifacts only

| File                                               | Status        | Reason              | Action      |
| -------------------------------------------------- | ------------- | ------------------- | ----------- |
| `support/scripts/create-phase5-subtasks.ps1`       | ⏸️ Historical | Phase 5 complete    | **ARCHIVE** |
| `support/scripts/create-phase5-subtasks.py`        | ⏸️ Historical | Phase 5 complete    | **ARCHIVE** |
| `support/scripts/create-phase5-subtasks-fixed.ps1` | ⏸️ Historical | Phase 5 complete    | **ARCHIVE** |
| `support/scripts/mark-phase5-tasks-done.py`        | ⏸️ Historical | Phase 5 complete    | **ARCHIVE** |
| `support/scripts/validate-phase6.ps1`              | ⏸️ Historical | Phase 6 complete    | **ARCHIVE** |
| `support/scripts/update-linear-progress.ps1`       | ⏸️ Historical | One-time use script | **ARCHIVE** |

---

## 📋 Temporary/Planning Documentation (Can be Archived)

### **Reason**: Planning/temporary docs superseded by implementation

| File                                            | Status        | Reason                                                             | Action      |
| ----------------------------------------------- | ------------- | ------------------------------------------------------------------ | ----------- |
| `support/docs/temp-mcp-tool-disclosure-plan.md` | ⏸️ Temporary  | Implementation complete, prefix indicates temp                     | **ARCHIVE** |
| `support/docs/pre-flight-v2.md`                 | ⏸️ Temporary  | Pre-deployment planning, superseded by PRE_DEPLOYMENT_CHECKLIST.md | **ARCHIVE** |
| `support/docs/Phase-6-Overview.md`              | ⏸️ Historical | Superseded by PHASE_6_COMPLETE.md                                  | **ARCHIVE** |
| `support/docs/Phase-6-Implementation-Audit.md`  | ⏸️ Historical | Audit complete, captured in PHASE_6_COMPLETE.md                    | **ARCHIVE** |

---

## 📋 Duplicate/Superseded Documentation (Consolidate or Archive)

| File                                          | Status        | Reason                                           | Action      |
| --------------------------------------------- | ------------- | ------------------------------------------------ | ----------- |
| `support/docs/PHASE_5_PLAN.md`                | ⏸️ Historical | Phase 5 complete, keep for reference             | **ARCHIVE** |
| `support/docs/PHASE_5_TESTING.md`             | ⏸️ Historical | Testing complete                                 | **ARCHIVE** |
| `support/docs/PHASE_5_COMPLETE_NEXT_STEPS.md` | ⏸️ Historical | Next steps captured in Phase 6                   | **ARCHIVE** |
| `support/docs/PHASE_6_PLAN.md`                | ⏸️ Historical | Phase 6 complete                                 | **ARCHIVE** |
| `support/docs/PHASE_6_COMPLETE_NEXT_STEPS.md` | ⏸️ Historical | Superseded by Phase 7 planning (if/when created) | **ARCHIVE** |
| `support/docs/CLEANUP_SUMMARY.md`             | ⏸️ Historical | Repository cleanup from Nov 19, one-time report  | **ARCHIVE** |

---

## 📋 Test/Example Scripts (Keep or Archive)

| File                                                  | Status        | Reason                          | Action      |
| ----------------------------------------------------- | ------------- | ------------------------------- | ----------- |
| `support/scripts/example_workflow_code_review_dev.py` | ✅ Keep       | Reference example for workflows | **KEEP**    |
| `support/scripts/example_workflow_parallel_docs.py`   | ✅ Keep       | Reference example for workflows | **KEEP**    |
| `support/scripts/example_workflow_review_deploy.py`   | ✅ Keep       | Reference example for workflows | **KEEP**    |
| `support/scripts/test-chat-endpoint.py`               | ✅ Keep       | Active testing utility          | **KEEP**    |
| `support/scripts/test-linear-connection.ps1`          | ⏸️ Historical | One-time connectivity test      | **ARCHIVE** |
| `support/scripts/test-progressive-disclosure.ps1`     | ⏸️ Historical | One-time feature test           | **ARCHIVE** |
| `support/scripts/test_inter_agent_communication.py`   | ✅ Keep       | Phase 6 validation test         | **KEEP**    |
| `support/scripts/test_resource_locks.py`              | ✅ Keep       | Phase 6 validation test         | **KEEP**    |
| `support/scripts/test_workflow_state.py`              | ✅ Keep       | Phase 6 validation test         | **KEEP**    |

---

## 📋 PowerShell Scripts (Review for Deprecation)

| File                                         | Status   | Reason                              | Action     |
| -------------------------------------------- | -------- | ----------------------------------- | ---------- |
| `support/scripts/connect-linear-project.ps1` | ⏸️ Check | May be superseded by Python scripts | **REVIEW** |
| `support/scripts/init-resource-locks.ps1`    | ✅ Keep  | Database initialization utility     | **KEEP**   |
| `support/scripts/init-workflow-state.ps1`    | ✅ Keep  | Database initialization utility     | **KEEP**   |
| `support/scripts/prune-dockerhub-manual.ps1` | ✅ Keep  | Manual Docker maintenance           | **KEEP**   |

---

## ✅ Core Documentation to Keep

### Architecture & Design

- ✅ `ARCHITECTURE.md` - System architecture overview
- ✅ `DEPLOYMENT_ARCHITECTURE.md` - Deployment patterns
- ✅ `HYBRID_ARCHITECTURE.md` - Hybrid architecture approach
- ✅ `HANDBOOK.md` - Project handbook
- ✅ `README.md` - Documentation index

### Integration & Setup

- ✅ `MCP_INTEGRATION.md` - MCP integration details
- ✅ `LANGGRAPH_INTEGRATION.md` - LangGraph setup
- ✅ `LANGSMITH_TRACING.md` - Tracing configuration
- ✅ `GRADIENT_AI_QUICK_START.md` - LLM integration
- ✅ `LINEAR_SETUP.md` - Linear OAuth setup
- ✅ `LINEAR_USAGE_GUIDELINES.md` - Linear workflow documentation
- ✅ `SETUP_GUIDE.md` - General setup

### Operations

- ✅ `DEPLOYMENT.md` - Deployment procedures
- ✅ `DOCKER_HUB_DEPLOYMENT.md` - Docker Hub workflows
- ✅ `DIGITALOCEAN_QUICK_DEPLOY.md` - Cloud deployment
- ✅ `DOCR-implementation.md` - DigitalOcean Container Registry
- ✅ `PRE_DEPLOYMENT_CHECKLIST.md` - Pre-deployment validation
- ✅ `SECRETS_MANAGEMENT.md` - Secrets handling
- ✅ `DOCKER_CLEANUP.md` - Docker maintenance

### Phase 6 Completion

- ✅ `PHASE_6_COMPLETE.md` - Phase 6 summary
- ✅ `PHASE_6_MONITORING_GUIDE.md` - Monitoring procedures
- ✅ `AGENT_REGISTRY.md` - Agent registry documentation
- ✅ `RESOURCE_LOCKING.md` - Resource locking system
- ✅ `EVENT_PROTOCOL.md` - Inter-agent communication
- ✅ `MULTI_AGENT_WORKFLOWS.md` - Workflow patterns

### Reference

- ✅ `AGENT_ENDPOINTS.md` - API endpoints
- ✅ `PROMETHEUS_METRICS.md` - Metrics definitions
- ✅ `QDRANT_COLLECTIONS.md` - Vector DB collections
- ✅ `LANGSMITH_EXAMPLES.md` - Tracing examples
- ✅ `LANGGRAPH_QUICK_REF.md` - Quick reference
- ✅ `LLM_MULTI_PROVIDER.md` - Multi-provider LLM
- ✅ `NOTIFICATION_SYSTEM.md` - Notification architecture
- ✅ `SHARED_LIB_NOTIFICATIONS.md` - Notification library
- ✅ `HITL_IMPLEMENTATION_PHASE2.md` - HITL workflows
- ✅ `RAG_DOCUMENTATION_AGGREGATION.md` - RAG system
- ✅ `TASK_ORCHESTRATION.md` - Task routing
- ✅ `FRONTEND_INTEGRATION.md` - Frontend integration
- ✅ `CONFIGURE_AGENTS_UI.md` - UI configuration

---

## 📂 Proposed Archive Structure

```
_archive/
├── docs-historical/
│   ├── phases/
│   │   ├── PHASE_5_PLAN.md
│   │   ├── PHASE_5_TESTING.md
│   │   ├── PHASE_5_COMPLETE_NEXT_STEPS.md
│   │   ├── PHASE_6_PLAN.md
│   │   ├── PHASE_6_COMPLETE_NEXT_STEPS.md
│   │   ├── Phase-6-Overview.md
│   │   └── Phase-6-Implementation-Audit.md
│   ├── planning/
│   │   ├── temp-mcp-tool-disclosure-plan.md
│   │   └── pre-flight-v2.md
│   └── reports/
│       └── CLEANUP_SUMMARY.md
│
└── scripts-deprecated/
    ├── linear-legacy/
    │   ├── update-linear-phase2.py
    │   ├── update-linear-phase5.py
    │   ├── update-linear-phase6.py
    │   ├── update-phase5-linear.py
    │   ├── update-linear-graphql.py
    │   ├── create-hitl-subtasks.py
    │   └── mark-hitl-complete.py
    ├── phase-tasks/
    │   ├── create-phase5-subtasks.ps1
    │   ├── create-phase5-subtasks.py
    │   ├── create-phase5-subtasks-fixed.ps1
    │   ├── mark-phase5-tasks-done.py
    │   ├── validate-phase6.ps1
    │   └── update-linear-progress.ps1
    └── one-time-tests/
        ├── test-linear-connection.ps1
        └── test-progressive-disclosure.ps1
```

---

## 🎯 Cleanup Actions

### Step 1: Create Archive Structure

```powershell
New-Item -ItemType Directory -Path "_archive/docs-historical/phases" -Force
New-Item -ItemType Directory -Path "_archive/docs-historical/planning" -Force
New-Item -ItemType Directory -Path "_archive/docs-historical/reports" -Force
New-Item -ItemType Directory -Path "_archive/scripts-deprecated/linear-legacy" -Force
New-Item -ItemType Directory -Path "_archive/scripts-deprecated/phase-tasks" -Force
New-Item -ItemType Directory -Path "_archive/scripts-deprecated/one-time-tests" -Force
```

### Step 2: Move Deprecated Documentation

```powershell
# Phase documentation
Move-Item "support/docs/PHASE_5_*.md" "_archive/docs-historical/phases/"
Move-Item "support/docs/PHASE_6_PLAN.md" "_archive/docs-historical/phases/"
Move-Item "support/docs/PHASE_6_COMPLETE_NEXT_STEPS.md" "_archive/docs-historical/phases/"
Move-Item "support/docs/Phase-6-*.md" "_archive/docs-historical/phases/"

# Planning docs
Move-Item "support/docs/temp-mcp-tool-disclosure-plan.md" "_archive/docs-historical/planning/"
Move-Item "support/docs/pre-flight-v2.md" "_archive/docs-historical/planning/"

# Reports
Move-Item "support/docs/CLEANUP_SUMMARY.md" "_archive/docs-historical/reports/"
```

### Step 3: Move Deprecated Scripts

```powershell
# Linear legacy
Move-Item "support/scripts/update-linear-phase*.py" "_archive/scripts-deprecated/linear-legacy/"
Move-Item "support/scripts/update-phase5-linear.py" "_archive/scripts-deprecated/linear-legacy/"
Move-Item "support/scripts/update-linear-graphql.py" "_archive/scripts-deprecated/linear-legacy/"
Move-Item "support/scripts/create-hitl-subtasks.py" "_archive/scripts-deprecated/linear-legacy/"
Move-Item "support/scripts/mark-hitl-complete.py" "_archive/scripts-deprecated/linear-legacy/"

# Phase tasks
Move-Item "support/scripts/create-phase5-*.ps1" "_archive/scripts-deprecated/phase-tasks/"
Move-Item "support/scripts/create-phase5-*.py" "_archive/scripts-deprecated/phase-tasks/"
Move-Item "support/scripts/mark-phase5-tasks-done.py" "_archive/scripts-deprecated/phase-tasks/"
Move-Item "support/scripts/validate-phase6.ps1" "_archive/scripts-deprecated/phase-tasks/"
Move-Item "support/scripts/update-linear-progress.ps1" "_archive/scripts-deprecated/phase-tasks/"

# One-time tests
Move-Item "support/scripts/test-linear-connection.ps1" "_archive/scripts-deprecated/one-time-tests/"
Move-Item "support/scripts/test-progressive-disclosure.ps1" "_archive/scripts-deprecated/one-time-tests/"
```

### Step 4: Git Cleanup

```powershell
git add -A
git commit -m "chore: archive deprecated docs and scripts from Phase 5/6

Moved to _archive/:
- 9 phase-specific documentation files
- 2 temporary planning documents
- 1 cleanup report
- 7 deprecated Linear scripts (replaced by agent-linear-update.py)
- 6 phase-specific task scripts (historical)
- 2 one-time test scripts

Rationale:
- Phase 5/6 complete, planning docs now historical
- agent-linear-update.py replaces all phase-specific Linear scripts
- One-time test scripts no longer needed
- Preserves history while cleaning active workspace

Active scripts: agent-linear-update.py, get-linear-project-uuid.py, update-linear-pr68.py
Active docs: 30+ current architecture, integration, and operational guides"
```

---

## 📊 Summary

**Files to Archive:**

- Documentation: 12 files (~250 KB)
- Scripts: 15 files (~180 KB)
- **Total**: 27 files

**Files to Keep:**

- Documentation: 35+ active guides
- Scripts: 20+ active utilities and examples

**Benefits:**

- ✅ Cleaner workspace for Phase 7+
- ✅ Preserved history in \_archive/
- ✅ Clear separation of active vs. historical
- ✅ Easier navigation for developers
- ✅ Reduced confusion about which scripts to use

---

**Status**: Ready for execution  
**Risk**: Low (files preserved in \_archive/)  
**Estimated Time**: 5-10 minutes
