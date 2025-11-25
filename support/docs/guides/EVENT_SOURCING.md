# Event Sourcing Architecture Guide

Complete guide to the event sourcing implementation for workflow state management.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Concepts](#core-concepts)
4. [Reducer Purity](#reducer-purity)
5. [Event Types](#event-types)
6. [Snapshot Strategy](#snapshot-strategy)
7. [Time-Travel Debugging](#time-travel-debugging)
8. [Compliance & Audit](#compliance--audit)
9. [Migration Strategy](#migration-strategy)
10. [API Reference](#api-reference)
11. [Best Practices](#best-practices)

## Overview

### What is Event Sourcing?

Event sourcing is a design pattern where **state is derived from a sequence of immutable events** rather than storing mutable state directly.

**Traditional Approach:**

```python
workflow.status = "completed"  # Direct mutation
```

**Event Sourcing Approach:**

```python
event = WorkflowEvent(action="COMPLETE_STEP", ...)
state = workflow_reducer(current_state, event)  # Pure function
```

### Benefits

- **Auditability**: Complete history of all state changes
- **Time-Travel Debugging**: Reconstruct state at any point in time
- **Compliance**: Tamper-proof event log with cryptographic signatures
- **Reproducibility**: Same events always produce same final state
- **Testing**: Property-based testing of reducer purity

## Architecture

### High-Level Flow

```
User Action
    ↓
API Endpoint (main.py)
    ↓
WorkflowEngine._emit_event()
    ↓
workflow_reducer(state, event) → new_state
    ↓
PostgreSQL (workflow_events table)
    ↓
State Reconstruction via replay_workflow(events)
```

### Components

1. **workflow_reducer.py**: Pure reducer function for state transitions
2. **workflow_events.py**: Event utilities (serialization, encryption, signatures)
3. **workflow_events.sql**: PostgreSQL schema for event storage
4. **workflow_engine.py**: Event emission and state reconstruction
5. **audit_reports.py**: PDF compliance report generation

### Database Schema

```sql
-- Immutable event log
CREATE TABLE workflow_events (
    event_id UUID PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    action TEXT NOT NULL,  -- WorkflowAction enum
    step_id TEXT,
    data JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_version INTEGER DEFAULT 2,
    signature TEXT  -- HMAC-SHA256
);

-- Performance snapshots (every 10 events)
CREATE TABLE workflow_snapshots (
    snapshot_id UUID PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    state JSONB NOT NULL,
    event_count INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cached metadata for fast queries
CREATE TABLE workflow_metadata (
    workflow_id TEXT PRIMARY KEY,
    template_name TEXT,
    status TEXT,
    current_step TEXT,
    total_events INTEGER,
    steps_completed INTEGER,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
);

-- Cold storage for 90+ day retention
CREATE TABLE workflow_events_archive (
    -- Same structure as workflow_events
    archived_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Core Concepts

### Events vs State

**Event (Immutable)**:

```python
WorkflowEvent(
    event_id="uuid-123",
    workflow_id="wf-abc",
    action=WorkflowAction.COMPLETE_STEP,
    step_id="code_review",
    data={"result": {"quality_score": 95}},
    timestamp="2024-01-15T10:00:00Z",
    signature="hmac-sha256-signature"
)
```

**State (Derived)**:

```python
{
    "workflow_id": "wf-abc",
    "status": "running",
    "current_step": "deploy",
    "steps_completed": ["code_review", "test"],
    "outputs": {
        "code_review": {"quality_score": 95},
        "test": {"passed": 42, "failed": 0}
    },
    "approvals": {},
    "events": [...]  # Full event history
}
```

### Event Sourcing Equation

```
State(t) = reducer(State(t-1), Event(t))
```

Where:

- `State(0)` = `{}` (empty initial state)
- `State(final)` = `replay_workflow([Event(1), Event(2), ..., Event(n)])`

## Reducer Purity

### Pure Function Requirements

The `workflow_reducer()` function must be **pure**:

1. **No Side Effects**: No I/O, no network calls, no database queries
2. **Deterministic**: Same inputs always produce same outputs
3. **No Mutations**: Never modify input `state` or `event` objects
4. **Idempotent** (where applicable): Multiple applications = single application

### Example: COMPLETE_STEP Reducer

```python
def workflow_reducer(state: Dict, event: WorkflowEvent) -> Dict:
    """Pure function: (state, event) → new_state"""

    # ✅ GOOD: Create new state (no mutations)
    new_state = {**state, "events": []}

    if event.action == WorkflowAction.COMPLETE_STEP:
        # ✅ GOOD: Create new list (no mutations)
        new_state["steps_completed"] = [
            *state.get("steps_completed", []),
            event.step_id
        ]

        # ✅ GOOD: Create new dict (no mutations)
        new_state["outputs"] = {
            **state.get("outputs", {}),
            event.step_id: event.data.get("result", {})
        }

        new_state["current_step"] = event.step_id

    # ❌ BAD: Mutation (violates purity)
    # state["steps_completed"].append(event.step_id)

    # ❌ BAD: Side effect (violates purity)
    # requests.post("http://api.example.com/notify")

    return new_state
```

### Testing Reducer Purity

```python
from hypothesis import given, strategies as st

@given(st.dictionaries(st.text(), st.integers()))
def test_reducer_never_mutates_inputs(state_dict):
    """Property: Reducer never mutates input state"""

    original_state = state_dict.copy()
    event = WorkflowEvent(action=WorkflowAction.START_WORKFLOW, ...)

    _ = workflow_reducer(state_dict, event)

    # Original state unchanged
    assert state_dict == original_state
```

## Event Types

### WorkflowAction Enum

14 workflow actions for state transitions:

```python
class WorkflowAction(str, Enum):
    # Lifecycle
    START_WORKFLOW = "start_workflow"
    COMPLETE_STEP = "complete_step"
    FAIL_STEP = "fail_step"

    # Approval Gates
    APPROVE_GATE = "approve_gate"
    REJECT_GATE = "reject_gate"

    # Workflow Control
    PAUSE_WORKFLOW = "pause_workflow"
    RESUME_WORKFLOW = "resume_workflow"
    CANCEL_WORKFLOW = "cancel_workflow"

    # Error Recovery
    ROLLBACK_STEP = "rollback_step"
    RETRY_STEP = "retry_step"

    # Parent-Child Workflows
    START_CHILD_WORKFLOW = "start_child_workflow"
    CHILD_WORKFLOW_COMPLETE = "child_workflow_complete"

    # Performance & Compliance
    CREATE_SNAPSHOT = "create_snapshot"
    ANNOTATE = "annotate"  # Operator comments
```

### Event Payload Examples

**START_WORKFLOW**:

```python
{
    "action": "START_WORKFLOW",
    "step_id": "step1",
    "data": {
        "context": {"pr_number": 123, "repo": "test-repo"},
        "template_name": "pr-deployment"
    }
}
```

**COMPLETE_STEP**:

```python
{
    "action": "COMPLETE_STEP",
    "step_id": "code_review",
    "data": {
        "result": {
            "quality_score": 95,
            "security_issues": 0,
            "recommendations": ["Add more tests"]
        }
    }
}
```

**APPROVE_GATE**:

```python
{
    "action": "APPROVE_GATE",
    "step_id": "deploy_approval",
    "data": {
        "approver": "alice@example.com",
        "approver_role": "tech_lead",
        "comment": "LGTM - approved for production",
        "linear_issue_id": "DEV-123"
    }
}
```

**FAIL_STEP**:

```python
{
    "action": "FAIL_STEP",
    "step_id": "deploy",
    "data": {
        "error": "Connection timeout after 30s",
        "error_type": "network",
        "stack_trace": "..."
    }
}
```

**RETRY_STEP**:

```python
{
    "action": "RETRY_STEP",
    "step_id": "deploy",
    "data": {
        "retry_attempt": 2,
        "max_retries": 3,
        "backoff_delay": 4.0
    }
}
```

**CANCEL_WORKFLOW**:

```python
{
    "action": "CANCEL_WORKFLOW",
    "step_id": "current_step",
    "data": {
        "reason": "Emergency hotfix deployed",
        "cancelled_by": "ops@example.com"
    }
}
```

**ANNOTATE**:

```python
{
    "action": "ANNOTATE",
    "step_id": "approval_gate",
    "data": {
        "operator": "bob@example.com",
        "comment": "Manually approved due to urgent customer escalation",
        "event_id": "event-abc-123"
    }
}
```

## Snapshot Strategy

### Why Snapshots?

Replaying 1000+ events for every state reconstruction is expensive. **Snapshots optimize performance** by storing periodic checkpoints.

### Snapshot Frequency

**Every 10 events** (configurable):

```python
async def _should_create_snapshot(workflow_id: str) -> bool:
    """Check if snapshot needed"""

    event_count = await self._get_event_count(workflow_id)

    return event_count % 10 == 0
```

### Snapshot Structure

```python
{
    "snapshot_id": "uuid-snapshot-123",
    "workflow_id": "wf-abc",
    "state": {
        "workflow_id": "wf-abc",
        "status": "running",
        "steps_completed": ["step1", "step2", ..., "step10"],
        "outputs": {...},
        "approvals": {...}
    },
    "event_count": 10,
    "created_at": "2024-01-15T10:00:00Z"
}
```

### State Reconstruction Algorithm

```
1. Load most recent snapshot (if exists)
2. Load delta events (events after snapshot)
3. Replay delta events through reducer
4. Return final state

Performance:
- Without snapshots: O(n) where n = total events
- With snapshots: O(k) where k = events since last snapshot (k ≤ 10)
- Speedup: 100+ events → 90% faster
```

### Example: Snapshot + Delta

```python
async def _reconstruct_state_from_events(workflow_id: str) -> Dict:
    """Reconstruct state using snapshot + delta events"""

    # 1. Load latest snapshot
    snapshot = await self._load_latest_snapshot(workflow_id)

    if snapshot:
        # Start from snapshot state
        state = snapshot['state']
        after_event_count = snapshot['event_count']
    else:
        # No snapshot - start from empty state
        state = {}
        after_event_count = 0

    # 2. Load delta events (events after snapshot)
    delta_events = await self._load_events(
        workflow_id,
        after_event_count=after_event_count
    )

    # 3. Replay delta events
    for event in delta_events:
        state = workflow_reducer(state, event)

    return state
```

## Time-Travel Debugging

### Use Cases

1. **Incident Investigation**: "What was the state at 10:15 AM when the failure occurred?"
2. **Compliance Audits**: "Show me the approval history for production deployment"
3. **Regression Testing**: "Replay events to reproduce the bug"

### Time-Travel API

**Get state at specific timestamp:**

```bash
curl http://localhost:8001/workflow/wf-abc/state-at/2024-01-15T10:15:00Z
```

```python
def get_state_at_timestamp(
    events: List[WorkflowEvent],
    timestamp: str
) -> Dict:
    """Reconstruct state at specific timestamp"""

    target_time = datetime.fromisoformat(timestamp)

    # Filter events before timestamp
    past_events = [
        e for e in events
        if datetime.fromisoformat(e.timestamp.replace('Z', '+00:00')) <= target_time
    ]

    # Replay filtered events
    return replay_workflow(past_events)
```

### Example: Time-Travel Investigation

```python
# Scenario: Workflow failed at 10:30 AM. What went wrong?

# 1. Get state at 10:25 AM (5 minutes before failure)
state_before = get_state_at_timestamp(events, "2024-01-15T10:25:00Z")
print(state_before["status"])  # "running"
print(state_before["current_step"])  # "deploy"

# 2. Get state at 10:30 AM (at failure time)
state_at_failure = get_state_at_timestamp(events, "2024-01-15T10:30:00Z")
print(state_at_failure["status"])  # "failed"
print(state_at_failure["error"])  # {"message": "Connection timeout", ...}

# 3. Find failure event
failure_event = next(
    e for e in events
    if e.action == WorkflowAction.FAIL_STEP
       and e.timestamp >= "2024-01-15T10:30:00Z"
)

print(failure_event.data["error"])  # "Connection timeout after 30s"
```

## Compliance & Audit

### HMAC Signatures

Every event is cryptographically signed using **HMAC-SHA256** to ensure integrity.

```python
def sign_event(event_dict: Dict, secret_key: str) -> str:
    """Generate HMAC-SHA256 signature"""

    # Canonical representation
    message = f"{event_dict['event_id']}|{event_dict['workflow_id']}|{event_dict['action']}|{event_dict['timestamp']}"

    signature = hmac.new(
        secret_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    return signature
```

### Tamper Detection

```python
def verify_event_signature(event_dict: Dict, secret_key: str) -> bool:
    """Verify event signature"""

    stored_signature = event_dict.get('signature')

    # Recompute signature
    computed_signature = sign_event(event_dict, secret_key)

    # Constant-time comparison (prevents timing attacks)
    return hmac.compare_digest(stored_signature, computed_signature)
```

### PDF Audit Reports

Generate comprehensive audit reports with:

- Workflow timeline (Gantt chart)
- Approval history with approver roles
- Resource lock acquisition/release
- Error events and retry attempts
- Signature verification status

```bash
# Generate audit report
curl http://localhost:8001/workflow/wf-abc/events/export?format=pdf > audit_report.pdf
```

Or use the automated script:

```bash
# Generate reports for all workflows completed in last 7 days
python support/scripts/generate_audit_reports.py

# Generate report for specific workflow
python support/scripts/generate_audit_reports.py --workflow-id wf-abc
```

### Event Retention Policy

**90-day retention** in main `workflow_events` table:

```sql
-- Archive old events
SELECT archive_old_events(90);

-- Compress archived events
-- (done by generate_audit_reports.py --compress)
```

## Migration Strategy

### Gradual Rollout Plan

**Week 4.1: New Workflows Only**

```bash
# Enable event sourcing for new workflows
USE_EVENT_SOURCING=true
```

**Week 4.2: Backfill Existing Workflows**

```bash
# Migrate completed workflows
python support/scripts/migrate_workflow_state_to_events.py --all

# Validate migrations
python support/scripts/migrate_workflow_state_to_events.py --validate-only
```

**Week 4.3: Dual-Write Mode**

```python
# Write to both old and new systems
await self._persist_legacy_state(workflow_id, state)  # Old system
await self._emit_event(workflow_id, action, data)      # Event sourcing

# Shadow read: Compare states
legacy_state = await self._load_legacy_state(workflow_id)
event_state = await self._reconstruct_state_from_events(workflow_id)

if legacy_state != event_state:
    logger.warning(f"State mismatch for {workflow_id}")
```

**Week 4.4: Full Cutover**

```python
# Remove legacy code
# Keep dual-write for 1 week as safety net
# Monitor for discrepancies
```

### Migration Script

```bash
# Dry run (no changes)
python support/scripts/migrate_workflow_state_to_events.py --dry-run

# Migrate specific workflow
python support/scripts/migrate_workflow_state_to_events.py --workflow-id abc-123

# Migrate all workflows
python support/scripts/migrate_workflow_state_to_events.py --all
```

## API Reference

### Event Endpoints

**GET /workflow/{id}/events**

- Query parameters: `limit`, `offset`, `action` (filter by action)
- Returns: List of events with pagination

**GET /workflow/{id}/events/export?format={json|csv|pdf}**

- Returns: File download with events
- PDF includes audit report with timeline

**POST /workflow/{id}/replay**

- Returns: Reconstructed state from events
- Use for debugging state issues

**GET /workflow/{id}/state-at/{timestamp}**

- Time-travel debugging
- Returns: State at specific ISO 8601 timestamp

**GET /workflow/{id}/snapshots**

- Returns: List of performance snapshots
- Use for monitoring snapshot creation

**POST /workflow/{id}/annotate**

- Body: `{operator, comment, event_id}`
- Returns: Annotation event
- Use for incident documentation

### Workflow Control Endpoints

**DELETE /workflow/{id}**

- Query params: `reason`, `cancelled_by`
- Returns: Cancellation summary with cleanup counts
- Comprehensive cleanup: locks, Linear issues, agents, children

**POST /workflow/{id}/retry-from/{step_id}**

- Query param: `max_retries` (default: 3)
- Returns: Retry status with backoff_delay
- Exponential backoff with jitter

## Best Practices

### 1. Keep Reducers Pure

```python
# ✅ GOOD
def workflow_reducer(state, event):
    return {**state, "status": "completed"}

# ❌ BAD
def workflow_reducer(state, event):
    state["status"] = "completed"  # Mutation!
    requests.post("http://api.example.com")  # Side effect!
    return state
```

### 2. Use Snapshots for Performance

```python
# ✅ GOOD: Create snapshot every 10 events
if event_count % 10 == 0:
    await self._create_snapshot(workflow_id, state)

# ❌ BAD: Never create snapshots (slow replays)
```

### 3. Sign All Events

```python
# ✅ GOOD: Sign events for tamper detection
signature = sign_event(event_dict, secret_key)
event_dict["signature"] = signature

# ❌ BAD: Skip signatures (no tamper detection)
```

### 4. Validate Event Chains

```python
# ✅ GOOD: Validate entire chain periodically
validate_event_chain(events, secret_key, strict=True)

# ❌ BAD: Trust events without verification
```

### 5. Use Time-Travel for Debugging

```python
# ✅ GOOD: Reconstruct state at failure time
state_at_failure = get_state_at_timestamp(events, failure_timestamp)

# ❌ BAD: Guess what state was at failure
```

### 6. Generate Audit Reports Regularly

```bash
# ✅ GOOD: Weekly cron job for compliance
0 2 * * 0 python support/scripts/generate_audit_reports.py

# ❌ BAD: Manual report generation
```

### 7. Archive Old Events

```sql
-- ✅ GOOD: Archive events older than 90 days
SELECT archive_old_events(90);

-- ❌ BAD: Keep all events in main table (slow queries)
```

### 8. Test Reducer Properties

```python
# ✅ GOOD: Property-based testing with hypothesis
@given(st.lists(st.builds(WorkflowEvent, ...)))
def test_reducer_is_associative(events):
    # Test that replay order doesn't matter for final state
    ...

# ❌ BAD: Only test happy path
```

## Troubleshooting

### Issue: State Mismatch After Replay

**Symptom**: Replayed state doesn't match expected state

**Diagnosis**:

```python
# 1. Load events
events = await workflow_engine._load_events(workflow_id)

# 2. Replay events
replayed_state = replay_workflow(events)

# 3. Compare with expected state
print(f"Expected: {expected_state}")
print(f"Replayed: {replayed_state}")
```

**Common Causes**:

- Reducer mutation (violates purity)
- Missing events in sequence
- Event order incorrect

**Solution**: Verify reducer purity with property-based tests

### Issue: Slow State Reconstruction

**Symptom**: `_reconstruct_state_from_events()` takes >1 second

**Diagnosis**:

```python
# Check event count
event_count = len(await workflow_engine._load_events(workflow_id))
print(f"Event count: {event_count}")

# Check snapshot count
snapshots = await workflow_engine._get_snapshots(workflow_id)
print(f"Snapshot count: {len(snapshots)}")
```

**Solution**: Verify snapshots are being created every 10 events

### Issue: Tampered Event Detected

**Symptom**: `TamperedEventError` raised during validation

**Diagnosis**:

```python
# Validate event chain
try:
    validate_event_chain(events, secret_key, strict=True)
except TamperedEventError as e:
    print(f"Tampered event: {e.event_id}")
```

**Solution**: Investigate event with invalid signature, check database integrity

## References

- [Event Sourcing Pattern (Martin Fowler)](https://martinfowler.com/eaaDev/EventSourcing.html)
- [CQRS and Event Sourcing (Microsoft)](https://docs.microsoft.com/en-us/azure/architecture/patterns/cqrs)
- [Property-Based Testing with Hypothesis](https://hypothesis.readthedocs.io/)
- [HMAC-SHA256 Specification (RFC 2104)](https://www.ietf.org/rfc/rfc2104.txt)
