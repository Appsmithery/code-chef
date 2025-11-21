# Linear Integration Phase 5 - State Service Implementation Complete ✅

**Commit:** `390d12c` - feat(linear): Add state service for task mappings and event bus integration

## What Was Implemented

### 1. PostgreSQL State Schema

**File:** `shared/services/state/migrations/004_task_linear_mappings.sql`

- Table: `task_linear_mappings` with fields:
  - `task_id` (unique): Orchestrator task identifier
  - `linear_issue_id`: Linear issue UUID
  - `linear_identifier`: Human-readable (e.g., "PR-123")
  - `agent_name`: Which agent owns the task
  - `parent_issue_id`, `parent_identifier`: Parent issue linking
  - `status`: todo, in_progress, done, canceled
  - `created_at`, `updated_at`, `completed_at`: Timestamps
- Auto-updating `updated_at` trigger
- Indexes on task_id, linear_issue_id, agent_name, status
- Example analytics queries included

### 2. State Client Library

**File:** `shared/lib/state_client.py` (450+ lines)

**Methods:**

- `connect()` - Establish asyncpg connection pool
- `store_task_mapping()` - Create new mapping with validation
- `get_task_mapping()` - Retrieve mapping by task_id
- `update_task_status()` - Update status with optional completion timestamp
- `get_agent_tasks()` - Query tasks by agent (with status filter)
- `get_parent_subtasks()` - Get all sub-tasks for parent issue
- `get_completion_stats()` - Completion rate analytics

**Features:**

- Connection pooling (2-10 connections)
- Error handling with logging
- Singleton pattern via `get_state_client()`
- Support for mark_completed flag to set completed_at

### 3. Event Bus Integration

**File:** `shared/services/webhooks/linear_webhook.py`

**Changes:**

- Import and initialize `event_bus` from `shared.lib.event_bus`
- Replace TODO comments with actual `event_bus.emit()` calls
- Publish `approval_decision` events with:
  - task_id, decision (approved/rejected), linear_issue, approved_by, reason
  - Source: "linear_webhook"
  - Correlation ID: task_id
- Three emission points:
  1. Status changes (approved/done → "approved", rejected/canceled → "rejected")
  2. Approval comments (`approve REQUEST_ID={id}`)
  3. Rejection comments (`reject REQUEST_ID={id} REASON="..."`)

### 4. Agent Integration Example (Updated)

**File:** `agent_feature-dev/linear_integration_example.py`

**New Integration:**

- Import `state_client` from `shared.lib.state_client`
- Initialize: `state_client = get_state_client()`
- Store mapping after Linear issue creation:
  ```python
  await state_client.store_task_mapping(
      task_id=task.task_id,
      linear_issue_id=linear_issue["id"],
      linear_identifier=linear_issue["identifier"],
      agent_name="feature-dev",
      parent_issue_id=parent_id,
      parent_identifier=task.orchestrator_issue_identifier,
      status="todo"
  )
  ```
- Update status throughout lifecycle:
  ```python
  await state_client.update_task_status(task.task_id, "in_progress")
  await state_client.update_task_status(task.task_id, "done", mark_completed=True)
  ```
- Error handling with cancelation

### 5. Documentation

**File:** `support/docs/LINEAR_STATE_SERVICE.md` (300+ lines)

**Sections:**

- Architecture diagram (Orchestrator → Agent → Linear + State)
- State schema details
- State client API reference with examples
- Agent integration pattern (complete workflow)
- Event bus integration (webhook → orchestrator)
- Deployment steps (migration, env vars, verification)
- Monitoring queries (completion rates, active tasks, avg times)
- Troubleshooting guide
- Next steps checklist

## Environment Variables Required

Add to `config/env/.env`:

```bash
# PostgreSQL State Service
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=devtools
POSTGRES_USER=devtools
POSTGRES_PASSWORD=<your-password>

# Linear Template IDs (6 HITL + 6 agent task templates)
LINEAR_HITL_ORCHESTRATOR_TEMPLATE_ID=<uuid>
LINEAR_HITL_FEATURE_DEV_TEMPLATE_ID=<uuid>
LINEAR_HITL_CODE_REVIEW_TEMPLATE_ID=<uuid>
LINEAR_HITL_INFRASTRUCTURE_TEMPLATE_ID=<uuid>
LINEAR_HITL_CICD_TEMPLATE_ID=<uuid>
LINEAR_HITL_DOCUMENTATION_TEMPLATE_ID=<uuid>

LINEAR_FEATURE_DEV_TEMPLATE_ID=<uuid>
LINEAR_CODE_REVIEW_TEMPLATE_ID=<uuid>
LINEAR_INFRASTRUCTURE_TEMPLATE_ID=<uuid>
LINEAR_CICD_TEMPLATE_ID=<uuid>
LINEAR_DOCUMENTATION_TEMPLATE_ID=<uuid>
LINEAR_ORCHESTRATOR_TEMPLATE_ID=<uuid>
```

## Deployment Checklist

- [ ] **Get Template UUIDs from Linear UI**

  - Go to Settings → Issue Templates
  - Copy UUID from URL for each template (12 total)
  - Add to `.env` file

- [ ] **Apply Database Migration**

  ```bash
  ssh root@45.55.173.72
  cd /opt/Dev-Tools
  docker compose exec postgres psql -U devtools -d devtools -f /migrations/004_task_linear_mappings.sql
  ```

- [ ] **Deploy Configuration**

  ```powershell
  .\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config
  ```

- [ ] **Verify State Service**

  ```bash
  docker compose logs state -f
  docker compose exec state python -c "from shared.lib.state_client import get_state_client; import asyncio; asyncio.run(get_state_client().connect())"
  ```

- [ ] **Test Webhook Events**

  - Update Linear approval issue status
  - Check orchestrator logs for `approval_decision` event
  - Verify event contains task_id, decision, linear_issue

- [ ] **Implement Orchestrator Subscriber**

  - Add to `agent_orchestrator/main.py`:

    ```python
    from shared.lib.event_bus import get_event_bus

    async def handle_approval_decision(event):
        task_id = event.data["task_id"]
        decision = event.data["decision"]
        if decision == "approved":
            await resume_task(task_id)
        else:
            await cancel_task(task_id, reason=event.data.get("reason"))

    event_bus = get_event_bus()
    event_bus.subscribe("approval_decision", handle_approval_decision)
    ```

- [ ] **Roll Out to Remaining Agents**

  - Copy pattern from `agent_feature-dev/linear_integration_example.py`
  - Implement for: orchestrator, code-review, infrastructure, cicd, documentation
  - Update each agent's `/tasks/accept` endpoint

- [ ] **Create Remaining Task Templates**

  - code-review-task.md
  - infrastructure-task.md
  - cicd-task.md
  - documentation-task.md
  - orchestrator-task.md

- [ ] **End-to-End Testing**
  - Submit task via @devtools command
  - Verify Linear sub-issue created
  - Check state mapping in PostgreSQL
  - Update approval status in Linear
  - Confirm orchestrator receives event

## Key Benefits

1. **Persistent State**: Task→Linear mappings survive agent restarts
2. **Dual Tracking**: Status updates in both Linear and PostgreSQL
3. **Analytics Ready**: SQL queries for completion rates, avg times
4. **Event-Driven**: Webhook publishes to event bus, orchestrator subscribes
5. **Production Pattern**: asyncpg connection pooling, error handling, logging
6. **Scalable**: Indexes on all query columns, auto-updating timestamps

## Next Actions

**Immediate (Blockers):**

1. Get Linear template UUIDs and configure in .env
2. Apply database migration on production
3. Implement orchestrator approval subscriber

**Follow-Up:** 4. Roll out to remaining 5 agents 5. Create remaining task template specs 6. End-to-end testing

## References

- **Implementation Plan**: `support/docs/LINEAR_INTEGRATION_IMPLEMENTATION.md`
- **State Service Docs**: `support/docs/LINEAR_STATE_SERVICE.md`
- **Example Agent**: `agent_feature-dev/linear_integration_example.py`
- **State Schema**: `shared/services/state/migrations/004_task_linear_mappings.sql`
- **Webhook Handler**: `shared/services/webhooks/linear_webhook.py`
- **Event Bus**: `shared/lib/event_bus.py`

---

**Status**: Phase 5 State Service Complete ✅  
**Commit**: 390d12c  
**Date**: November 20, 2025  
**Files Changed**: 6 files, 1377 insertions(+), 18 deletions(-)
