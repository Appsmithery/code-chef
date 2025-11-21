# Linear Integration - Phase 5 State Service

## Overview

Phase 5 implementation now includes PostgreSQL-backed state management for task-to-Linear mappings. This enables agents to track which Linear issues correspond to orchestrator task IDs throughout the task lifecycle.

## Architecture

```
┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│ Orchestrator │────▶│ Feature-Dev   │────▶│ Linear API   │
│              │     │ Agent         │     │              │
└──────────────┘     └───────────────┘     └──────────────┘
                            │                      │
                            │                      │
                            ▼                      ▼
                     ┌─────────────┐       ┌──────────────┐
                     │ State       │       │ Linear Issue │
                     │ Service     │       │ (Sub-Task)   │
                     │ (PostgreSQL)│       └──────────────┘
                     └─────────────┘
                            │
                            ├─ Task ID
                            ├─ Linear Issue ID
                            ├─ Status (todo/in_progress/done)
                            └─ Timestamps
```

## State Schema

**Table:** `task_linear_mappings`

```sql
CREATE TABLE task_linear_mappings (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL UNIQUE,
    linear_issue_id VARCHAR(255) NOT NULL,
    linear_identifier VARCHAR(50) NOT NULL,  -- e.g., "PR-123"
    agent_name VARCHAR(50) NOT NULL,
    parent_issue_id VARCHAR(255),
    parent_identifier VARCHAR(50),
    status VARCHAR(50) DEFAULT 'todo',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

## State Client API

### Initialization

```python
from shared.lib.state_client import get_state_client

state_client = get_state_client()
await state_client.connect()
```

### Store Mapping

```python
await state_client.store_task_mapping(
    task_id="abc123-def456",
    linear_issue_id="550e8400-e29b-41d4-a716-446655440000",
    linear_identifier="PR-123",
    agent_name="feature-dev",
    parent_issue_id="parent-uuid",
    parent_identifier="PR-68",
    status="todo"
)
```

### Get Mapping

```python
mapping = await state_client.get_task_mapping("abc123-def456")
# Returns: {
#     "task_id": "abc123-def456",
#     "linear_issue_id": "550e8400-e29b-41d4-a716-446655440000",
#     "linear_identifier": "PR-123",
#     "agent_name": "feature-dev",
#     "status": "todo",
#     ...
# }
```

### Update Status

```python
# Update to in_progress
await state_client.update_task_status("abc123-def456", "in_progress")

# Mark as done (sets completed_at timestamp)
await state_client.update_task_status("abc123-def456", "done", mark_completed=True)
```

### Query Operations

```python
# Get all tasks for agent
tasks = await state_client.get_agent_tasks("feature-dev")

# Get active tasks only
active = await state_client.get_agent_tasks("feature-dev", status="in_progress")

# Get sub-tasks for parent
subtasks = await state_client.get_parent_subtasks("PR-68")

# Get completion stats
stats = await state_client.get_completion_stats("feature-dev")
# Returns: {
#     "total_tasks": 10,
#     "completed": 8,
#     "in_progress": 1,
#     "canceled": 1,
#     "completion_rate": 80.0
# }
```

## Agent Integration Pattern

All agents should follow this pattern when accepting tasks:

```python
from shared.lib.linear_workspace_client import get_linear_workspace_client
from shared.lib.state_client import get_state_client

linear_client = get_linear_workspace_client()
state_client = get_state_client()

@app.post("/tasks/accept")
async def accept_task(task: TaskAssignment):
    # 1. Create Linear sub-issue from template
    linear_issue = await linear_client.create_issue_from_template(
        template_id=TEMPLATE_ID,
        template_variables={...},
        parent_id=task.orchestrator_issue_id
    )

    # 2. Store mapping in state service
    await state_client.store_task_mapping(
        task_id=task.task_id,
        linear_issue_id=linear_issue["id"],
        linear_identifier=linear_issue["identifier"],
        agent_name="your-agent-name",
        parent_issue_id=task.orchestrator_issue_id,
        parent_identifier=task.orchestrator_issue_identifier,
        status="todo"
    )

    # 3. Execute task with status updates
    await linear_client.update_issue_status(linear_issue["id"], "in_progress")
    await state_client.update_task_status(task.task_id, "in_progress")

    # ... perform work ...

    # 4. Mark complete (both Linear and state)
    await linear_client.update_issue_status(linear_issue["id"], "done")
    await state_client.update_task_status(task.task_id, "done", mark_completed=True)

    # 5. Add completion comment
    await linear_client.add_comment(linear_issue["id"], "Task completed ✅")

    return TaskResult(
        status="completed",
        linear_issue=linear_issue["identifier"],
        linear_issue_id=linear_issue["id"],
        summary="..."
    )
```

## Event Bus Integration

Webhook handler now publishes approval decisions to event bus:

```python
# In webhook handler (shared/services/webhooks/linear_webhook.py)
await event_bus.emit(
    event_type="approval_decision",
    data={
        "task_id": task_id,
        "decision": "approved",  # or "rejected"
        "linear_issue": issue_identifier,
        "approved_by": "user@example.com",
        "reason": "..."  # for rejections
    },
    source="linear_webhook",
    correlation_id=task_id
)
```

Orchestrator should subscribe to approval decisions:

```python
# In orchestrator main.py
from shared.lib.event_bus import get_event_bus

event_bus = get_event_bus()

async def handle_approval_decision(event):
    task_id = event.data["task_id"]
    decision = event.data["decision"]

    if decision == "approved":
        # Resume task execution
        await resume_task(task_id)
    else:
        # Cancel task
        await cancel_task(task_id, reason=event.data.get("reason"))

# Subscribe at startup
event_bus.subscribe("approval_decision", handle_approval_decision)
```

## Deployment Steps

### 1. Apply Database Migration

```bash
ssh root@45.55.173.72
cd /opt/Dev-Tools
docker compose exec postgres psql -U devtools -d devtools_state -f /migrations/004_task_linear_mappings.sql
```

### 2. Update Environment Variables

Add to `config/env/.env`:

```bash
# State Service (PostgreSQL)
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=devtools_state
POSTGRES_USER=devtools
POSTGRES_PASSWORD=<your-password>

# Linear Template IDs (get from Linear UI)
LINEAR_HITL_ORCHESTRATOR_TEMPLATE_ID=<template-uuid>
LINEAR_HITL_FEATURE_DEV_TEMPLATE_ID=<template-uuid>
LINEAR_HITL_CODE_REVIEW_TEMPLATE_ID=<template-uuid>
LINEAR_HITL_INFRASTRUCTURE_TEMPLATE_ID=<template-uuid>
LINEAR_HITL_CICD_TEMPLATE_ID=<template-uuid>
LINEAR_HITL_DOCUMENTATION_TEMPLATE_ID=<template-uuid>

# Agent Task Template IDs
LINEAR_FEATURE_DEV_TEMPLATE_ID=<template-uuid>
LINEAR_CODE_REVIEW_TEMPLATE_ID=<template-uuid>
LINEAR_INFRASTRUCTURE_TEMPLATE_ID=<template-uuid>
LINEAR_CICD_TEMPLATE_ID=<template-uuid>
LINEAR_DOCUMENTATION_TEMPLATE_ID=<template-uuid>
LINEAR_ORCHESTRATOR_TEMPLATE_ID=<template-uuid>
```

### 3. Deploy Configuration

```powershell
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config
```

### 4. Verify State Service

```bash
ssh root@45.55.173.72
cd /opt/Dev-Tools/deploy
docker compose logs state -f

# Test connection
docker compose exec state python -c "
from shared.lib.state_client import get_state_client
import asyncio
async def test():
    client = get_state_client()
    await client.connect()
    print('✅ State client connected')
asyncio.run(test())
"
```

### 5. Test Agent Integration

```bash
# Create test task via API
curl -X POST http://localhost:8002/tasks/accept \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test-123",
    "description": "Test task",
    "orchestrator_issue_id": "parent-uuid",
    "orchestrator_issue_identifier": "PR-68",
    "complexity": "medium",
    "requirements": "Test requirements",
    "acceptance_criteria": ["Criterion 1", "Criterion 2"]
  }'

# Verify mapping stored
docker compose exec postgres psql -U devtools -d devtools_state -c "
SELECT task_id, linear_identifier, status
FROM task_linear_mappings
WHERE task_id='test-123';
"
```

## Monitoring

### Metrics

State client provides completion statistics:

```python
stats = await state_client.get_completion_stats("feature-dev")
# {
#     "total_tasks": 10,
#     "completed": 8,
#     "in_progress": 1,
#     "canceled": 1,
#     "completion_rate": 80.0
# }
```

### Dashboard Queries

```sql
-- Active tasks by agent
SELECT agent_name, COUNT(*) as active_tasks
FROM task_linear_mappings
WHERE status = 'in_progress'
GROUP BY agent_name;

-- Completion rate by agent
SELECT
    agent_name,
    COUNT(*) as total,
    SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as completed,
    ROUND(100.0 * SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) / COUNT(*), 2) as rate
FROM task_linear_mappings
GROUP BY agent_name;

-- Average completion time by agent
SELECT
    agent_name,
    COUNT(*) as completed_tasks,
    AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) / 60 as avg_minutes
FROM task_linear_mappings
WHERE status = 'done' AND completed_at IS NOT NULL
GROUP BY agent_name;

-- Sub-tasks for approval hub (PR-68)
SELECT
    task_id,
    linear_identifier,
    agent_name,
    status,
    created_at
FROM task_linear_mappings
WHERE parent_identifier = 'PR-68'
ORDER BY created_at DESC
LIMIT 10;
```

## Troubleshooting

### Connection Errors

```python
# Check PostgreSQL connection
docker compose exec postgres psql -U devtools -d devtools_state -c "\dt"

# Check environment variables
docker compose exec orchestrator env | grep POSTGRES
```

### Missing Mappings

```python
# Verify mapping creation
mapping = await state_client.get_task_mapping("task-id")
if not mapping:
    logger.error(f"No mapping found for task {task_id}")
    # Manually create mapping or investigate store_task_mapping call
```

### Stale Status

```python
# Force status update
await state_client.update_task_status("task-id", "done", mark_completed=True)

# Check updated_at timestamp
mapping = await state_client.get_task_mapping("task-id")
logger.info(f"Last updated: {mapping['updated_at']}")
```

## Next Steps

1. **Get Template UUIDs**: Go to Linear → Settings → Issue Templates → copy UUID from URL for each template
2. **Add to .env**: Configure `LINEAR_*_TEMPLATE_ID` environment variables
3. **Apply Migration**: Run `004_task_linear_mappings.sql` on production database
4. **Deploy Config**: Use `deploy-to-droplet.ps1 -DeployType config` to update environment
5. **Roll Out to Agents**: Copy pattern from `agent_feature-dev/linear_integration_example.py` to remaining 5 agents
6. **Orchestrator Integration**: Add approval decision subscriber in orchestrator main.py
7. **Test End-to-End**: Submit task → creates approval → agent accepts → creates sub-issue → completes → updates status

## References

- **State Schema**: `shared/services/state/migrations/004_task_linear_mappings.sql`
- **State Client**: `shared/lib/state_client.py`
- **Example Implementation**: `agent_feature-dev/linear_integration_example.py`
- **Webhook Handler**: `shared/services/webhooks/linear_webhook.py`
- **Event Bus**: `shared/lib/event_bus.py`
