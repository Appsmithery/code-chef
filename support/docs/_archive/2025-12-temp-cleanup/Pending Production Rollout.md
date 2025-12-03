# 📋 Pending Production Rollout

## **DEV-174 (Event Sourcing) - Rollout Plan:**

| Week    | Phase              | Status       | Actions                                              |
| ------- | ------------------ | ------------ | ---------------------------------------------------- |
| **4.1** | New Workflows Only | ✅ Completed | Set `USE_EVENT_SOURCING=true`, monitor new workflows |
| **4.2** | Backfill Existing  | ⏭️ Skipped   | No production workflows to migrate (29 test records) |
| **4.3** | Dual-Write Mode    | ⏭️ Skipped   | Event sourcing always active, no dual-write needed   |
| **4.4** | Full Cutover       | ✅ Completed | Legacy table archived as `workflows_legacy`          |

**🎉 Event Sourcing Rollout Complete (2025-11-26)**

**Week 4.1 - Infrastructure Deployment:**

- ✅ Deployed `workflow_events.sql` schema (events, snapshots, TTL, parent chains)
- ✅ Deployed `agent_registry.sql` schema (fixed 500 errors)
- ✅ Added `USE_EVENT_SOURCING=true` to production `.env` (documentation only)
- ✅ Restarted all services with config deployment
- ✅ Verified `workflow_events` table accessible (0 events, ready for production)

**Weeks 4.2-4.3 - Migration Skipped:**

- 📊 Legacy `workflows` table contained only 29 test records (Nov 18-22, 2025)
- 🔍 Status: 23 approval_pending, 6 pending (no completed workflows)
- ⏭️ **Decision**: Skip migration, proceed directly to full cutover

**Week 4.4 - Full Cutover:**

- ✅ Renamed `workflows` → `workflows_legacy` (archived for reference)
- ✅ Event sourcing is now the sole source of truth
- ✅ All future workflows will persist events to `workflow_events` table

**Architecture Notes:**

- Event sourcing is built into `workflow_engine.py` and always active when `state_client` is provided
- No feature flag exists in code - event sourcing is production-ready by default
- The `USE_EVENT_SOURCING` env var was added for documentation/clarity only

### 🚀 Recommended Next Actions

**Priority 1: RAG Collection Population**

Per DEV-183 proposal:

- Implement `code_patterns` indexing (extract from agent_orchestrator)
- Implement `feature_specs` indexing (Linear project descriptions)
- Implement `issue_tracker` indexing (Linear issue sync)
- Implement `task_context` indexing (workflow history)

**Priority 2: Agent Memory**

Per DEV-167:

- Port Zen conversation memory system
- Implement `agent_memory` collection population
- Add workflow continuation API

---

**Summary**: The Linear roadmap is in excellent shape with **90% completion**. All major architecture phases are done and deployed. The main pending work is:

1. **RAG Collection Population** (DEV-183 proposed)
2. **Agent Memory Implementation** (DEV-167)
