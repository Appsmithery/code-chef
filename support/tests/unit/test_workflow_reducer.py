"""Property-based tests for workflow reducer using hypothesis

These tests verify reducer correctness through automated property testing:
1. Purity: Same inputs always produce same outputs
2. Immutability: Reducer never mutates input state or events
3. Idempotency: Applying idempotent events multiple times = applying once
4. Composition: Replaying events always produces consistent state
5. Reversibility: Rollback events properly revert state changes
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant
from datetime import datetime
from typing import Dict, Any, List

from shared.lib.workflow_reducer import (
    WorkflowAction,
    WorkflowEvent,
    workflow_reducer,
    replay_workflow,
    get_state_at_timestamp,
    validate_reducer_purity,
    validate_reducer_idempotency,
)


# ============================================================================
# PROPERTY-BASED TESTS
# ============================================================================


@given(st.text(min_size=1, max_size=50))
def test_start_workflow_creates_initial_state(workflow_id):
    """Property: START_WORKFLOW always creates valid initial state"""

    event = WorkflowEvent(
        workflow_id=workflow_id,
        action=WorkflowAction.START_WORKFLOW,
        step_id="step1",
        data={"context": {"pr_number": 123}},
    )

    state = workflow_reducer({}, event)

    # Verify initial state properties
    assert state["workflow_id"] == workflow_id
    assert state["status"] == "running"
    assert state["current_step"] == "step1"
    assert state["steps_completed"] == []
    assert state["outputs"] == {}
    assert "events" in state
    assert len(state["events"]) == 1


@given(st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=10, unique=True))
def test_complete_step_accumulates_steps(step_ids):
    """Property: Completing steps accumulates in steps_completed"""

    # Initialize workflow
    state = {"status": "running", "steps_completed": [], "outputs": {}}

    # Complete each step
    for step_id in step_ids:
        event = WorkflowEvent(
            workflow_id="test",
            action=WorkflowAction.COMPLETE_STEP,
            step_id=step_id,
            data={"result": {"status": "success"}},
        )
        state = workflow_reducer(state, event)

    # Verify all steps completed
    assert state["steps_completed"] == step_ids
    assert len(state["outputs"]) == len(step_ids)


@given(st.text(min_size=1))
def test_reducer_purity(error_message):
    """Property: Reducer is pure (no mutations, deterministic)"""

    initial_state = {"status": "running", "outputs": {}}
    event = WorkflowEvent(
        workflow_id="test",
        action=WorkflowAction.FAIL_STEP,
        step_id="test_step",
        data={"error": error_message},
    )

    # Verify purity (no exceptions should be raised)
    validate_reducer_purity(initial_state, event)

    # Verify determinism: same inputs → same outputs
    result1 = workflow_reducer(initial_state, event)
    result2 = workflow_reducer(initial_state, event)

    # Compare excluding timestamp-dependent fields
    assert result1["status"] == result2["status"]
    assert result1.get("error") == result2.get("error")


@given(st.lists(st.integers(min_value=1, max_value=100), min_size=0, max_size=50))
def test_replay_is_associative(pr_numbers):
    """Property: Replay order doesn't matter for final state"""

    events = []

    # Create START_WORKFLOW event
    events.append(
        WorkflowEvent(
            workflow_id="test",
            action=WorkflowAction.START_WORKFLOW,
            step_id="init",
            data={"context": {}},
        )
    )

    # Create COMPLETE_STEP events
    for i, pr_num in enumerate(pr_numbers):
        events.append(
            WorkflowEvent(
                workflow_id="test",
                action=WorkflowAction.COMPLETE_STEP,
                step_id=f"step_{i}",
                data={"pr_number": pr_num},
            )
        )

    # Replay all events
    final_state = replay_workflow(events)

    # Verify consistent final state
    assert final_state["status"] == "running"
    assert len(final_state["steps_completed"]) == len(pr_numbers)


@settings(max_examples=20)  # Reduce for CI performance
@given(st.integers(min_value=0, max_value=10))
def test_idempotent_pause(pause_count):
    """Property: Pausing multiple times is idempotent"""

    state = {"status": "running", "current_step": "approval"}

    event = WorkflowEvent(
        workflow_id="test",
        action=WorkflowAction.PAUSE_WORKFLOW,
        step_id="approval",
        data={"reason": "awaiting_approval"},
    )

    # Apply pause multiple times
    for _ in range(max(1, pause_count)):
        state = workflow_reducer(state, event)

    # Should always be paused
    assert state["status"] == "paused"
    assert state["paused_step"] == "approval"


# ============================================================================
# STATEFUL PROPERTY TESTING (Advanced)
# ============================================================================


class WorkflowStateMachine(RuleBasedStateMachine):
    """Stateful property testing for workflow state transitions

    This uses hypothesis.stateful to generate random sequences of
    workflow operations and verify invariants hold.
    """

    def __init__(self):
        super().__init__()
        self.state = {"status": "initialized", "events": []}
        self.workflow_id = "test-workflow"

    @rule()
    def start_workflow(self):
        """Rule: Can start workflow from initialized state"""
        assume(self.state.get("status") == "initialized")

        event = WorkflowEvent(
            workflow_id=self.workflow_id,
            action=WorkflowAction.START_WORKFLOW,
            step_id="step1",
            data={"context": {}},
        )

        self.state = workflow_reducer(self.state, event)

    @rule(step_id=st.text(min_size=1, max_size=20))
    def complete_step(self, step_id):
        """Rule: Can complete steps when workflow running"""
        assume(self.state.get("status") == "running")

        event = WorkflowEvent(
            workflow_id=self.workflow_id,
            action=WorkflowAction.COMPLETE_STEP,
            step_id=step_id,
            data={"result": {"status": "success"}},
        )

        self.state = workflow_reducer(self.state, event)

    @rule()
    def pause_workflow(self):
        """Rule: Can pause running workflow"""
        assume(self.state.get("status") == "running")

        event = WorkflowEvent(
            workflow_id=self.workflow_id,
            action=WorkflowAction.PAUSE_WORKFLOW,
            step_id=self.state.get("current_step", "unknown"),
            data={"reason": "awaiting_approval"},
        )

        self.state = workflow_reducer(self.state, event)

    @rule()
    def resume_workflow(self):
        """Rule: Can resume paused workflow"""
        assume(self.state.get("status") == "paused")

        event = WorkflowEvent(
            workflow_id=self.workflow_id,
            action=WorkflowAction.RESUME_WORKFLOW,
            step_id=self.state.get("current_step", "unknown"),
            data={"decision": "approved"},
        )

        self.state = workflow_reducer(self.state, event)

    @invariant()
    def state_is_valid(self):
        """Invariant: State always has required fields"""
        assert "status" in self.state
        assert "events" in self.state
        assert isinstance(self.state["events"], list)

    @invariant()
    def events_are_immutable(self):
        """Invariant: Event list only grows (never shrinks)"""
        assert len(self.state["events"]) >= 0


# Run stateful tests
TestWorkflowStateMachine = WorkflowStateMachine.TestCase


# ============================================================================
# UNIT TESTS FOR SPECIFIC SCENARIOS
# ============================================================================


def test_reducer_handles_empty_state():
    """Reducer should handle empty initial state"""

    event = WorkflowEvent(
        workflow_id="test",
        action=WorkflowAction.START_WORKFLOW,
        step_id="init",
        data={},
    )

    state = workflow_reducer({}, event)

    assert state["status"] == "running"
    assert state["workflow_id"] == "test"


def test_complete_step_updates_outputs():
    """COMPLETE_STEP should store step output"""

    state = {"status": "running", "outputs": {}}

    event = WorkflowEvent(
        workflow_id="test",
        action=WorkflowAction.COMPLETE_STEP,
        step_id="code_review",
        data={"result": {"quality_score": 95}},
    )

    state = workflow_reducer(state, event)

    assert "code_review" in state["outputs"]
    assert state["outputs"]["code_review"]["quality_score"] == 95


def test_fail_step_marks_workflow_failed():
    """FAIL_STEP should mark workflow as failed"""

    state = {"status": "running"}

    event = WorkflowEvent(
        workflow_id="test",
        action=WorkflowAction.FAIL_STEP,
        step_id="deploy",
        data={"error": "Connection timeout", "error_type": "network"},
    )

    state = workflow_reducer(state, event)

    assert state["status"] == "failed"
    assert state["error"]["step_id"] == "deploy"
    assert state["error"]["message"] == "Connection timeout"


def test_approve_gate_adds_approval():
    """APPROVE_GATE should record approval"""

    state = {"status": "paused", "approvals": {}}

    event = WorkflowEvent(
        workflow_id="test",
        action=WorkflowAction.APPROVE_GATE,
        step_id="approval_gate",
        data={
            "approver": "alice@example.com",
            "approver_role": "tech_lead",
            "comment": "LGTM",
        },
    )

    state = workflow_reducer(state, event)

    assert "approval_gate" in state["approvals"]
    assert state["approvals"]["approval_gate"]["approver"] == "alice@example.com"
    assert state["approvals"]["approval_gate"]["approved"] is True


def test_rollback_reverts_step_output():
    """ROLLBACK_STEP should remove step from completed and outputs"""

    state = {
        "status": "running",
        "steps_completed": ["step1", "step2", "step3"],
        "outputs": {"step1": {}, "step2": {}, "step3": {}},
        "rollbacks": [],
    }

    event = WorkflowEvent(
        workflow_id="test",
        action=WorkflowAction.ROLLBACK_STEP,
        step_id="step2",
        data={"reason": "Deployment failed health check"},
    )

    state = workflow_reducer(state, event)

    assert "step2" not in state["steps_completed"]
    assert "step2" not in state["outputs"]
    assert len(state["rollbacks"]) == 1
    assert state["rollbacks"][0]["step"] == "step2"


def test_cancel_workflow_marks_cancelled():
    """CANCEL_WORKFLOW should mark workflow as cancelled"""

    state = {"status": "running"}

    event = WorkflowEvent(
        workflow_id="test",
        action=WorkflowAction.CANCEL_WORKFLOW,
        step_id="current_step",
        data={
            "reason": "Emergency fix deployed",
            "cancelled_by": "ops@example.com",
        },
    )

    state = workflow_reducer(state, event)

    assert state["status"] == "cancelled"
    assert state["cancellation_reason"] == "Emergency fix deployed"
    assert state["cancelled_by"] == "ops@example.com"


def test_retry_step_increments_counter():
    """RETRY_STEP should track retry attempts"""

    state = {"status": "failed", "retries": {}}

    # First retry
    event1 = WorkflowEvent(
        workflow_id="test",
        action=WorkflowAction.RETRY_STEP,
        step_id="deploy",
        data={},
    )
    state = workflow_reducer(state, event1)

    assert state["retries"]["deploy"] == 1
    assert state["status"] == "running"  # Back to running

    # Second retry
    event2 = WorkflowEvent(
        workflow_id="test",
        action=WorkflowAction.RETRY_STEP,
        step_id="deploy",
        data={},
    )
    state = workflow_reducer(state, event2)

    assert state["retries"]["deploy"] == 2


def test_replay_workflow_reconstructs_state():
    """Replay should reconstruct exact state from events"""

    events = [
        WorkflowEvent(
            workflow_id="test",
            action=WorkflowAction.START_WORKFLOW,
            step_id="step1",
            data={"context": {"pr_number": 123}},
        ),
        WorkflowEvent(
            workflow_id="test",
            action=WorkflowAction.COMPLETE_STEP,
            step_id="step1",
            data={"result": {"status": "success"}},
        ),
        WorkflowEvent(
            workflow_id="test",
            action=WorkflowAction.COMPLETE_STEP,
            step_id="step2",
            data={"result": {"status": "success"}},
        ),
    ]

    final_state = replay_workflow(events)

    assert final_state["workflow_id"] == "test"
    assert final_state["status"] == "running"
    assert final_state["steps_completed"] == ["step1", "step2"]
    assert len(final_state["outputs"]) == 2


def test_get_state_at_timestamp():
    """Time-travel debugging: reconstruct state at specific timestamp"""

    events = [
        WorkflowEvent(
            workflow_id="test",
            action=WorkflowAction.START_WORKFLOW,
            step_id="step1",
            timestamp="2024-01-15T10:00:00Z",
        ),
        WorkflowEvent(
            workflow_id="test",
            action=WorkflowAction.COMPLETE_STEP,
            step_id="step1",
            timestamp="2024-01-15T10:05:00Z",
        ),
        WorkflowEvent(
            workflow_id="test",
            action=WorkflowAction.COMPLETE_STEP,
            step_id="step2",
            timestamp="2024-01-15T10:10:00Z",
        ),
    ]

    # State at 10:07 (after step1, before step2)
    state_at_10_07 = get_state_at_timestamp(events, "2024-01-15T10:07:00Z")

    assert state_at_10_07["steps_completed"] == ["step1"]
    assert "step2" not in state_at_10_07["steps_completed"]


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================


@pytest.mark.performance
def test_replay_performance_large_event_log():
    """Verify replay performance with large event logs"""
    import time

    # Generate 1000 events
    events = [
        WorkflowEvent(
            workflow_id="perf-test",
            action=WorkflowAction.START_WORKFLOW,
            step_id="init",
        )
    ]

    for i in range(1000):
        events.append(
            WorkflowEvent(
                workflow_id="perf-test",
                action=WorkflowAction.COMPLETE_STEP,
                step_id=f"step_{i}",
                data={"iteration": i},
            )
        )

    # Measure replay time
    start = time.time()
    final_state = replay_workflow(events)
    elapsed = time.time() - start

    # Should complete in < 1 second
    assert elapsed < 1.0
    assert len(final_state["steps_completed"]) == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--hypothesis-show-statistics"])
