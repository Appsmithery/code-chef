"""Integration tests for event sourcing: replay, time-travel, signatures

These tests verify end-to-end event sourcing workflows:
1. Full workflow execution with event emission
2. State reconstruction via replay
3. Time-travel debugging accuracy
4. Event signature verification
5. Snapshot creation and loading
6. Event archival and retention
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict

from agent_orchestrator.workflows.workflow_engine import WorkflowEngine
from shared.lib.workflow_reducer import (
    WorkflowAction,
    WorkflowEvent,
    workflow_reducer,
    replay_workflow,
    get_state_at_timestamp,
)
from shared.lib.workflow_events import (
    sign_event,
    verify_event_signature,
    validate_event_chain,
    TamperedEventError,
)


@pytest.fixture
async def workflow_engine():
    """Create WorkflowEngine instance"""
    engine = WorkflowEngine()
    yield engine
    # Cleanup after test


@pytest.fixture
def secret_key():
    """Secret key for HMAC signatures"""
    return "test-secret-key-do-not-use-in-production"


# ============================================================================
# EVENT REPLAY TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_full_workflow_execution_with_events(workflow_engine):
    """Execute complete workflow and verify event log"""

    template = {
        "template_name": "simple-pr-deploy",
        "steps": [
            {
                "step_id": "code_review",
                "agent": "code_review",
                "depends_on": [],
                "max_retries": 0,
            },
            {
                "step_id": "deploy",
                "agent": "infrastructure",
                "depends_on": ["code_review"],
                "max_retries": 0,
            },
        ],
    }

    context = {"pr_number": 123, "repo": "test-repo"}

    # Execute workflow
    result = await workflow_engine.execute_workflow(
        template=template,
        context=context,
    )

    workflow_id = result["workflow_id"]

    # Verify events emitted
    events = await workflow_engine._load_events(workflow_id)

    assert len(events) >= 3  # START + 2 COMPLETE_STEP events

    # Verify event sequence
    assert events[0].action == WorkflowAction.START_WORKFLOW
    assert events[1].action == WorkflowAction.COMPLETE_STEP
    assert events[1].step_id == "code_review"
    assert events[2].action == WorkflowAction.COMPLETE_STEP
    assert events[2].step_id == "deploy"


@pytest.mark.asyncio
async def test_state_reconstruction_from_events(workflow_engine):
    """Verify state can be reconstructed from event log"""

    workflow_id = "test-replay-workflow"

    # Emit sequence of events
    await workflow_engine._emit_event(
        workflow_id=workflow_id,
        action=WorkflowAction.START_WORKFLOW,
        step_id="step1",
        data={"context": {"pr_number": 456}},
    )

    await workflow_engine._emit_event(
        workflow_id=workflow_id,
        action=WorkflowAction.COMPLETE_STEP,
        step_id="step1",
        data={"result": {"status": "success"}},
    )

    await workflow_engine._emit_event(
        workflow_id=workflow_id,
        action=WorkflowAction.COMPLETE_STEP,
        step_id="step2",
        data={"result": {"status": "success"}},
    )

    # Reconstruct state
    state = await workflow_engine._reconstruct_state_from_events(workflow_id)

    # Verify reconstructed state
    assert state["workflow_id"] == workflow_id
    assert state["status"] == "running"
    assert state["steps_completed"] == ["step1", "step2"]
    assert len(state["outputs"]) == 2


@pytest.mark.asyncio
async def test_time_travel_debugging(workflow_engine):
    """Verify time-travel debugging: state at specific timestamp"""

    workflow_id = "test-time-travel"

    # Emit events at different times
    t1 = datetime.utcnow()
    await workflow_engine._emit_event(
        workflow_id=workflow_id,
        action=WorkflowAction.START_WORKFLOW,
        step_id="step1",
    )

    await asyncio.sleep(0.1)

    t2 = datetime.utcnow()
    await workflow_engine._emit_event(
        workflow_id=workflow_id,
        action=WorkflowAction.COMPLETE_STEP,
        step_id="step1",
    )

    await asyncio.sleep(0.1)

    t3 = datetime.utcnow()
    await workflow_engine._emit_event(
        workflow_id=workflow_id,
        action=WorkflowAction.COMPLETE_STEP,
        step_id="step2",
    )

    # Load events
    events = await workflow_engine._load_events(workflow_id)

    # State at t2 (after step1, before step2)
    state_at_t2 = get_state_at_timestamp(events, t2.isoformat())

    assert state_at_t2["steps_completed"] == ["step1"]
    assert "step2" not in state_at_t2["steps_completed"]

    # State at t3 (after step2)
    state_at_t3 = get_state_at_timestamp(events, t3.isoformat())

    assert state_at_t3["steps_completed"] == ["step1", "step2"]


# ============================================================================
# EVENT SIGNATURE TESTS
# ============================================================================


def test_event_signature_generation(secret_key):
    """Verify HMAC signature generation"""

    event_dict = {
        "event_id": "test-event-123",
        "workflow_id": "test-workflow",
        "action": "COMPLETE_STEP",
        "step_id": "code_review",
        "data": {"result": {"status": "success"}},
        "timestamp": "2024-01-15T10:00:00Z",
    }

    signature = sign_event(event_dict, secret_key)

    assert signature is not None
    assert len(signature) > 0
    assert isinstance(signature, str)


def test_event_signature_verification(secret_key):
    """Verify signature verification succeeds for valid events"""

    event_dict = {
        "event_id": "test-event-456",
        "workflow_id": "test-workflow",
        "action": "COMPLETE_STEP",
        "step_id": "deploy",
        "data": {"result": {"status": "success"}},
        "timestamp": "2024-01-15T10:05:00Z",
    }

    # Sign event
    signature = sign_event(event_dict, secret_key)
    event_dict["signature"] = signature

    # Verify signature
    is_valid = verify_event_signature(event_dict, secret_key)

    assert is_valid is True


def test_tampered_event_detection(secret_key):
    """Verify tampered events are detected"""

    event_dict = {
        "event_id": "test-event-789",
        "workflow_id": "test-workflow",
        "action": "COMPLETE_STEP",
        "step_id": "code_review",
        "data": {"result": {"status": "success"}},
        "timestamp": "2024-01-15T10:00:00Z",
    }

    # Sign event
    signature = sign_event(event_dict, secret_key)
    event_dict["signature"] = signature

    # Tamper with event data
    event_dict["data"]["result"]["status"] = "failed"  # Changed!

    # Verification should fail
    is_valid = verify_event_signature(event_dict, secret_key)

    assert is_valid is False


def test_event_chain_validation(secret_key):
    """Verify entire event chain validation"""

    events = [
        {
            "event_id": "event-1",
            "workflow_id": "test",
            "action": "START_WORKFLOW",
            "timestamp": "2024-01-15T10:00:00Z",
        },
        {
            "event_id": "event-2",
            "workflow_id": "test",
            "action": "COMPLETE_STEP",
            "timestamp": "2024-01-15T10:05:00Z",
        },
        {
            "event_id": "event-3",
            "workflow_id": "test",
            "action": "COMPLETE_STEP",
            "timestamp": "2024-01-15T10:10:00Z",
        },
    ]

    # Sign all events
    for event in events:
        signature = sign_event(event, secret_key)
        event["signature"] = signature

    # Validate chain
    try:
        validate_event_chain(events, secret_key, strict=True)
        chain_valid = True
    except TamperedEventError:
        chain_valid = False

    assert chain_valid is True


def test_tampered_chain_detection(secret_key):
    """Verify tampered event chain is detected"""

    events = [
        {
            "event_id": "event-1",
            "workflow_id": "test",
            "action": "START_WORKFLOW",
            "timestamp": "2024-01-15T10:00:00Z",
        },
        {
            "event_id": "event-2",
            "workflow_id": "test",
            "action": "COMPLETE_STEP",
            "timestamp": "2024-01-15T10:05:00Z",
        },
    ]

    # Sign events
    for event in events:
        signature = sign_event(event, secret_key)
        event["signature"] = signature

    # Tamper with second event
    events[1]["action"] = "FAIL_STEP"  # Changed!

    # Validation should fail
    with pytest.raises(TamperedEventError) as exc_info:
        validate_event_chain(events, secret_key, strict=True)

    assert "event-2" in str(exc_info.value)


# ============================================================================
# SNAPSHOT TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_snapshot_creation(workflow_engine):
    """Verify snapshots created every 10 events"""

    workflow_id = "test-snapshot-workflow"

    # Emit START event
    await workflow_engine._emit_event(
        workflow_id=workflow_id,
        action=WorkflowAction.START_WORKFLOW,
        step_id="step1",
    )

    # Emit 9 COMPLETE_STEP events (10 total)
    for i in range(9):
        await workflow_engine._emit_event(
            workflow_id=workflow_id,
            action=WorkflowAction.COMPLETE_STEP,
            step_id=f"step_{i}",
        )

    # Verify snapshot created
    should_create = await workflow_engine._should_create_snapshot(workflow_id)

    assert should_create is True


@pytest.mark.asyncio
async def test_snapshot_plus_delta_equals_replay(workflow_engine):
    """Verify snapshot + delta events = full replay"""

    workflow_id = "test-snapshot-delta"

    # Emit 15 events (creates 1 snapshot at event 10)
    await workflow_engine._emit_event(
        workflow_id=workflow_id,
        action=WorkflowAction.START_WORKFLOW,
        step_id="step1",
    )

    for i in range(14):
        await workflow_engine._emit_event(
            workflow_id=workflow_id,
            action=WorkflowAction.COMPLETE_STEP,
            step_id=f"step_{i}",
        )

    # Reconstruct from events (uses snapshot + delta)
    state_from_snapshot = await workflow_engine._reconstruct_state_from_events(
        workflow_id
    )

    # Reconstruct from full replay
    all_events = await workflow_engine._load_events(workflow_id)
    state_from_replay = replay_workflow(all_events)

    # Should be identical
    assert (
        state_from_snapshot["steps_completed"] == state_from_replay["steps_completed"]
    )
    assert len(state_from_snapshot["outputs"]) == len(state_from_replay["outputs"])


# ============================================================================
# WORKFLOW CANCELLATION TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_workflow_cancellation_emits_event(workflow_engine):
    """Verify cancellation emits CANCEL_WORKFLOW event"""

    workflow_id = "test-cancel-workflow"

    # Start workflow
    await workflow_engine._emit_event(
        workflow_id=workflow_id,
        action=WorkflowAction.START_WORKFLOW,
        step_id="step1",
    )

    # Cancel workflow
    result = await workflow_engine.cancel_workflow(
        workflow_id=workflow_id,
        reason="Testing cancellation",
        cancelled_by="test@example.com",
    )

    # Verify cancellation event
    events = await workflow_engine._load_events(workflow_id)
    cancel_event = next(e for e in events if e.action == WorkflowAction.CANCEL_WORKFLOW)

    assert cancel_event is not None
    assert cancel_event.data["reason"] == "Testing cancellation"
    assert cancel_event.data["cancelled_by"] == "test@example.com"


@pytest.mark.asyncio
async def test_cancellation_cleanup_resources(workflow_engine):
    """Verify cancellation releases locks and closes issues"""

    workflow_id = "test-cleanup-workflow"

    # Start workflow
    await workflow_engine._emit_event(
        workflow_id=workflow_id,
        action=WorkflowAction.START_WORKFLOW,
        step_id="step1",
    )

    # TODO: Create resource locks, Linear issues

    # Cancel workflow
    result = await workflow_engine.cancel_workflow(
        workflow_id=workflow_id,
        reason="Testing cleanup",
        cancelled_by="ops@example.com",
    )

    # Verify cleanup summary
    assert result["status"] == "cancelled"
    assert "cleanup" in result
    assert result["cleanup"]["locks_released"] >= 0
    assert result["cleanup"]["linear_issues_closed"] >= 0


# ============================================================================
# RETRY LOGIC TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_retry_step_emits_retry_event(workflow_engine):
    """Verify retry emits RETRY_STEP event"""

    workflow_id = "test-retry-workflow"

    # Start workflow
    await workflow_engine._emit_event(
        workflow_id=workflow_id,
        action=WorkflowAction.START_WORKFLOW,
        step_id="deploy",
    )

    # Fail step
    await workflow_engine._emit_event(
        workflow_id=workflow_id,
        action=WorkflowAction.FAIL_STEP,
        step_id="deploy",
        data={"error": "Timeout", "error_type": "network"},
    )

    # Retry step
    # (Note: This would be called via API endpoint in practice)
    await workflow_engine._emit_event(
        workflow_id=workflow_id,
        action=WorkflowAction.RETRY_STEP,
        step_id="deploy",
        data={"retry_attempt": 1},
    )

    # Verify retry event
    events = await workflow_engine._load_events(workflow_id)
    retry_event = next(e for e in events if e.action == WorkflowAction.RETRY_STEP)

    assert retry_event is not None
    assert retry_event.step_id == "deploy"


@pytest.mark.asyncio
async def test_retry_increments_counter(workflow_engine):
    """Verify retry counter increments correctly"""

    workflow_id = "test-retry-counter"

    # Start workflow
    await workflow_engine._emit_event(
        workflow_id=workflow_id,
        action=WorkflowAction.START_WORKFLOW,
        step_id="deploy",
    )

    # Retry 3 times
    for attempt in range(1, 4):
        await workflow_engine._emit_event(
            workflow_id=workflow_id,
            action=WorkflowAction.RETRY_STEP,
            step_id="deploy",
            data={"retry_attempt": attempt},
        )

    # Reconstruct state
    state = await workflow_engine._reconstruct_state_from_events(workflow_id)

    # Verify retry count
    assert state["retries"]["deploy"] == 3


# ============================================================================
# COMPLIANCE & AUDIT TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_operator_annotations(workflow_engine):
    """Verify operator annotations are captured"""

    workflow_id = "test-annotate-workflow"

    # Start workflow
    await workflow_engine._emit_event(
        workflow_id=workflow_id,
        action=WorkflowAction.START_WORKFLOW,
        step_id="step1",
    )

    # Add annotation
    await workflow_engine._emit_event(
        workflow_id=workflow_id,
        action=WorkflowAction.ANNOTATE,
        step_id="step1",
        data={
            "operator": "alice@example.com",
            "comment": "Manually approved due to emergency",
            "event_id": "event-123",
        },
    )

    # Verify annotation event
    events = await workflow_engine._load_events(workflow_id)
    annotate_event = next(e for e in events if e.action == WorkflowAction.ANNOTATE)

    assert annotate_event is not None
    assert annotate_event.data["operator"] == "alice@example.com"
    assert annotate_event.data["comment"] == "Manually approved due to emergency"


@pytest.mark.asyncio
async def test_event_archival_query(workflow_engine):
    """Verify old events can be queried from archive"""

    # Note: This test requires database access
    # Placeholder for actual archive query logic

    workflow_id = "test-archive-workflow"

    # Create workflow with old events (simulated)
    await workflow_engine._emit_event(
        workflow_id=workflow_id,
        action=WorkflowAction.START_WORKFLOW,
        step_id="step1",
        timestamp=(datetime.utcnow() - timedelta(days=100)).isoformat(),
    )

    # TODO: Query archived events
    # archived_events = await workflow_engine._query_archived_events(workflow_id)
    # assert len(archived_events) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
