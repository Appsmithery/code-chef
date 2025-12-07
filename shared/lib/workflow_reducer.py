"""Stateless workflow reducer for reproducible execution

This module implements pure reducer functions for workflow state management,
following event sourcing principles. All state transitions must go through
the reducer to ensure reproducibility and enable time-travel debugging.

Key Principles:
1. Pure Functions: No side effects, same inputs = same outputs
2. Immutability: Never mutate input state, always return new state
3. Event Sourcing: Events are the source of truth, state is derived
4. Determinism: Replaying events always produces the same final state
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from uuid import uuid4


class WorkflowAction(str, Enum):
    """Deterministic workflow actions for state transitions"""

    START_WORKFLOW = "start_workflow"
    COMPLETE_STEP = "complete_step"
    FAIL_STEP = "fail_step"
    APPROVE_GATE = "approve_gate"
    REJECT_GATE = "reject_gate"
    PAUSE_WORKFLOW = "pause_workflow"
    RESUME_WORKFLOW = "resume_workflow"
    ROLLBACK_STEP = "rollback_step"
    CANCEL_WORKFLOW = "cancel_workflow"
    RETRY_STEP = "retry_step"
    START_CHILD_WORKFLOW = "start_child_workflow"
    CHILD_WORKFLOW_COMPLETE = "child_workflow_complete"
    CREATE_SNAPSHOT = "create_snapshot"
    ANNOTATE = "annotate"
    CAPTURE_INSIGHT = "capture_insight"  # Cross-agent knowledge sharing


@dataclass(frozen=True)
class WorkflowEvent:
    """Immutable workflow event

    Events are the single source of truth for workflow state.
    All state transitions are represented as events.

    Attributes:
        event_id: Unique event identifier (UUID)
        workflow_id: Workflow this event belongs to
        action: Type of state transition
        step_id: Step this event relates to (optional for workflow-level events)
        data: Event-specific data (outputs, errors, approvals, etc.)
        timestamp: ISO 8601 timestamp of event creation
        event_version: Schema version for backward compatibility
        signature: HMAC-SHA256 signature for tamper detection (computed externally)
        parent_workflow_id: Parent workflow ID for child workflows (Task 5.1)
    """

    event_id: str = field(default_factory=lambda: str(uuid4()))
    workflow_id: str = ""
    action: WorkflowAction = WorkflowAction.START_WORKFLOW
    step_id: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    event_version: int = 1
    signature: Optional[str] = None
    parent_workflow_id: Optional[str] = None  # NEW: Task 5.1 - Parent workflow chains

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return asdict(self)


def workflow_reducer(state: Dict[str, Any], event: WorkflowEvent) -> Dict[str, Any]:
    """Pure reducer function: (state, event) → new_state

    This is the SINGLE SOURCE OF TRUTH for workflow state transitions.
    All state changes must go through this reducer for reproducibility.

    Purity Requirements:
    1. NO MUTATIONS: Never modify input state or event
    2. NO SIDE EFFECTS: No I/O, no network calls, no database writes
    3. DETERMINISTIC: Same inputs always produce same output
    4. NO RANDOMNESS: No random IDs, timestamps come from event

    Args:
        state: Current workflow state (immutable)
        event: Event to apply (immutable)

    Returns:
        New state with event applied (new dict instance)

    Example:
        >>> state = {"status": "initialized"}
        >>> event = WorkflowEvent(action=WorkflowAction.START_WORKFLOW)
        >>> new_state = workflow_reducer(state, event)
        >>> assert state != new_state  # Original state unchanged
        >>> assert new_state["status"] == "running"
    """

    # Create new state (NEVER mutate input)
    new_state = {**state, "events": [*state.get("events", []), event.to_dict()]}

    # Apply state transition based on action
    if event.action == WorkflowAction.START_WORKFLOW:
        new_state.update(
            {
                "workflow_id": event.workflow_id,
                "status": "running",
                "current_step": event.step_id,
                "steps_completed": [],
                "steps_failed": [],
                "outputs": {},
                "context": event.data.get("context", {}),
                "template_name": event.data.get("template_name"),
                "template_version": event.data.get("template_version", "1.0"),
                "started_at": event.timestamp,
                "participating_agents": event.data.get("participating_agents", []),
                "approvals": {},
                "rejections": {},
                "rollbacks": [],
                "retries": {},
                "child_workflows": [],
                "snapshots": [],
                "parent_workflow_id": event.parent_workflow_id,  # NEW: Task 5.1 - Track parent workflow
            }
        )

    elif event.action == WorkflowAction.COMPLETE_STEP:
        new_state.update(
            {
                "steps_completed": [
                    *new_state.get("steps_completed", []),
                    event.step_id,
                ],
                "outputs": {
                    **new_state.get("outputs", {}),
                    event.step_id: event.data.get("result"),
                },
            }
        )

        # Update current_step if next_step provided
        next_step = event.data.get("next_step")
        if next_step:
            new_state["current_step"] = next_step

        # Mark workflow complete if reached terminal step
        if next_step == "workflow_complete" or next_step is None:
            new_state["status"] = "completed"
            new_state["completed_at"] = event.timestamp

    elif event.action == WorkflowAction.FAIL_STEP:
        new_state.update(
            {
                "status": "failed",
                "steps_failed": [*new_state.get("steps_failed", []), event.step_id],
                "error": {
                    "step_id": event.step_id,
                    "error_type": event.data.get("error_type", "unknown"),
                    "message": event.data.get("error"),
                    "timestamp": event.timestamp,
                    "retriable": event.data.get("retriable", False),
                },
                "failed_at": event.timestamp,
            }
        )

    elif event.action == WorkflowAction.APPROVE_GATE:
        new_state["approvals"] = {
            **new_state.get("approvals", {}),
            event.step_id: {
                "approved": True,
                "approver": event.data.get("approver"),
                "approver_role": event.data.get("approver_role"),
                "comment": event.data.get("comment"),
                "timestamp": event.timestamp,
            },
        }

        # Resume workflow if paused for approval
        if new_state.get("status") == "paused":
            new_state["status"] = "running"

    elif event.action == WorkflowAction.REJECT_GATE:
        new_state.update(
            {
                "status": "rejected",
                "rejections": {
                    **new_state.get("rejections", {}),
                    event.step_id: {
                        "rejected": True,
                        "rejector": event.data.get("rejector"),
                        "rejector_role": event.data.get("rejector_role"),
                        "reason": event.data.get("reason"),
                        "timestamp": event.timestamp,
                    },
                },
                "rejected_at": event.timestamp,
            }
        )

    elif event.action == WorkflowAction.PAUSE_WORKFLOW:
        new_state.update(
            {
                "status": "paused",
                "paused_at": event.timestamp,
                "paused_step": event.step_id,
                "pause_reason": event.data.get("reason", "awaiting_approval"),
            }
        )

    elif event.action == WorkflowAction.RESUME_WORKFLOW:
        new_state.update(
            {
                "status": "running",
                "resumed_at": event.timestamp,
                "resume_decision": event.data.get("decision"),
            }
        )

    elif event.action == WorkflowAction.ROLLBACK_STEP:
        # Revert outputs for rolled-back step
        new_outputs = {**new_state.get("outputs", {})}
        new_outputs.pop(event.step_id, None)

        new_state.update(
            {
                "outputs": new_outputs,
                "steps_completed": [
                    s
                    for s in new_state.get("steps_completed", [])
                    if s != event.step_id
                ],
                "rollbacks": [
                    *new_state.get("rollbacks", []),
                    {
                        "step": event.step_id,
                        "reason": event.data.get("reason"),
                        "timestamp": event.timestamp,
                    },
                ],
            }
        )

    elif event.action == WorkflowAction.CANCEL_WORKFLOW:
        new_state.update(
            {
                "status": "cancelled",
                "cancelled_at": event.timestamp,
                "cancellation_reason": event.data.get("reason"),
                "cancelled_by": event.data.get("cancelled_by"),
            }
        )

    elif event.action == WorkflowAction.RETRY_STEP:
        # Track retry attempts
        retry_count = new_state.get("retries", {}).get(event.step_id, 0) + 1

        new_state["retries"] = {
            **new_state.get("retries", {}),
            event.step_id: retry_count,
        }

        # Update status if workflow was failed
        if new_state.get("status") == "failed":
            new_state["status"] = "running"

    elif event.action == WorkflowAction.START_CHILD_WORKFLOW:
        new_state["child_workflows"] = [
            *new_state.get("child_workflows", []),
            {
                "child_workflow_id": event.data.get("child_workflow_id"),
                "parent_step_id": event.step_id,
                "template_name": event.data.get("template_name"),
                "status": "running",
                "started_at": event.timestamp,
            },
        ]

    elif event.action == WorkflowAction.CHILD_WORKFLOW_COMPLETE:
        # Update child workflow status
        child_workflows = []
        for child in new_state.get("child_workflows", []):
            if child["child_workflow_id"] == event.data.get("child_workflow_id"):
                child = {
                    **child,
                    "status": event.data.get("status", "completed"),
                    "completed_at": event.timestamp,
                }
            child_workflows.append(child)

        new_state["child_workflows"] = child_workflows

    elif event.action == WorkflowAction.CREATE_SNAPSHOT:
        new_state["snapshots"] = [
            *new_state.get("snapshots", []),
            {
                "snapshot_id": event.data.get("snapshot_id"),
                "event_count": len(new_state.get("events", [])),
                "created_at": event.timestamp,
            },
        ]

    elif event.action == WorkflowAction.ANNOTATE:
        # Add operator annotation (for incident tracking)
        new_state["annotations"] = [
            *new_state.get("annotations", []),
            {
                "operator": event.data.get("operator"),
                "comment": event.data.get("comment"),
                "event_id": event.step_id,
                "timestamp": event.timestamp,
            },
        ]

    elif event.action == WorkflowAction.CAPTURE_INSIGHT:
        # Capture agent insight for cross-agent knowledge sharing
        # Insights are persisted to agent_memory Qdrant collection
        new_state["captured_insights"] = [
            *new_state.get("captured_insights", []),
            {
                "insight_id": event.data.get("insight_id"),
                "agent_id": event.data.get("agent_id"),
                "insight_type": event.data.get("insight_type"),
                "content": event.data.get("content"),
                "step_id": event.step_id,
                "timestamp": event.timestamp,
            },
        ]

    return new_state


def replay_workflow(events: List[WorkflowEvent]) -> Dict[str, Any]:
    """Replay all events to reconstruct workflow state

    This enables:
    1. Time-travel debugging: Reconstruct state at any point in time
    2. Audit logs: Full history of all state transitions
    3. State recovery: Rebuild state after crashes or corruption
    4. Testing: Verify reducer correctness with event sequences

    Args:
        events: Ordered list of workflow events

    Returns:
        Final workflow state after applying all events

    Example:
        >>> events = [
        ...     WorkflowEvent(action=WorkflowAction.START_WORKFLOW, step_id="step1"),
        ...     WorkflowEvent(action=WorkflowAction.COMPLETE_STEP, step_id="step1"),
        ... ]
        >>> final_state = replay_workflow(events)
        >>> assert final_state["status"] == "running"
        >>> assert "step1" in final_state["steps_completed"]
    """

    state = {"status": "initialized", "events": []}

    for event in events:
        state = workflow_reducer(state, event)

    return state


def get_state_at_timestamp(
    events: List[WorkflowEvent], timestamp: str
) -> Dict[str, Any]:
    """Time-travel debugging: Reconstruct state at specific timestamp

    Args:
        events: All workflow events
        timestamp: ISO 8601 timestamp to reconstruct state at

    Returns:
        Workflow state at the specified timestamp

    Example:
        >>> events = [...]  # All events
        >>> state = get_state_at_timestamp(events, "2024-01-15T10:30:00")
        >>> # State as it was at 10:30 AM on Jan 15, 2024
    """

    # Filter events up to timestamp
    events_until = [e for e in events if e.timestamp <= timestamp]

    return replay_workflow(events_until)


def validate_reducer_purity(state: Dict[str, Any], event: WorkflowEvent) -> None:
    """Validate that reducer is pure (does not mutate inputs)

    This is a testing utility to verify reducer correctness.

    Args:
        state: State to test with
        event: Event to test with

    Raises:
        AssertionError: If reducer mutates inputs
    """

    import copy

    # Deep copy inputs
    original_state = copy.deepcopy(state)
    original_event = copy.deepcopy(event)

    # Call reducer
    new_state = workflow_reducer(state, event)

    # Verify inputs unchanged
    assert state == original_state, "Reducer mutated input state!"
    assert event == original_event, "Reducer mutated input event!"
    assert new_state is not state, "Reducer returned same object!"


def validate_reducer_idempotency(state: Dict[str, Any], event: WorkflowEvent) -> None:
    """Validate that idempotent events produce idempotent results

    Some events should be idempotent (applying twice = applying once).
    Examples: PAUSE_WORKFLOW, CANCEL_WORKFLOW

    Args:
        state: State to test with
        event: Event to test with (should be idempotent)

    Raises:
        AssertionError: If event is not idempotent
    """

    # Apply event once
    state_once = workflow_reducer(state, event)

    # Apply event twice
    state_twice = workflow_reducer(state_once, event)

    # For idempotent events, both should be equivalent
    # (ignoring events list which grows)
    state_once_no_events = {k: v for k, v in state_once.items() if k != "events"}
    state_twice_no_events = {k: v for k, v in state_twice.items() if k != "events"}

    # Should be idempotent for these actions
    idempotent_actions = {
        WorkflowAction.PAUSE_WORKFLOW,
        WorkflowAction.CANCEL_WORKFLOW,
    }

    if event.action in idempotent_actions:
        assert (
            state_once_no_events == state_twice_no_events
        ), f"{event.action} should be idempotent!"


def get_workflow_chain(
    workflow_id: str, event_loader: callable
) -> List[Dict[str, Any]]:
    """Traverse parent workflows to build complete execution history

    This enables complete audit trails across parent-child workflow relationships.
    Inspired by Zen MCP Server's conversation threading pattern.

    Use Cases:
    1. PR deployment workflow spawns hotfix workflow as child
    2. Infrastructure deployment spawns configuration workflow
    3. Multi-level rollback chains for complex deployments

    Example:
        PR deployment (parent) → Hotfix (child) → Rollback (grandchild)

        get_workflow_chain("rollback-456", event_loader) returns:
        [
            {"workflow_id": "pr-123", "template_name": "pr-deployment", ...},
            {"workflow_id": "hotfix-234", "template_name": "hotfix", ...},
            {"workflow_id": "rollback-456", "template_name": "rollback", ...}
        ]

    Args:
        workflow_id: Starting workflow ID (typically child workflow)
        event_loader: Function that loads events for a workflow_id
                     Signature: (workflow_id: str) -> List[WorkflowEvent]
                     Example: lambda wid: db.query("SELECT * FROM events WHERE workflow_id = ?", wid)

    Returns:
        List of workflow states from root parent to current workflow (chronological order)

    Raises:
        ValueError: If circular reference detected in workflow chain
        RuntimeError: If max chain depth (20) exceeded

    Pattern Inspiration:
        Zen MCP Server's conversation threading uses continuation_id to link
        related conversations. This function adapts that pattern for workflow
        composition with parent_workflow_id tracking.

    Task: 5.1 - Parent Workflow Chains (Week 5 Zen Pattern Integration)
    """

    chain = []
    current_id = workflow_id
    seen_ids = set()
    max_depth = 20  # Prevent infinite loops (Zen pattern: 20 turn limit)

    while current_id and len(chain) < max_depth:
        # Circular reference detection
        if current_id in seen_ids:
            raise ValueError(
                f"Circular reference detected in workflow chain: {current_id}. "
                f"Chain so far: {[w['workflow_id'] for w in chain]}"
            )

        seen_ids.add(current_id)

        # Load events for current workflow
        try:
            events = event_loader(current_id)
        except Exception as e:
            raise RuntimeError(
                f"Failed to load events for workflow {current_id}: {e}"
            ) from e

        if not events:
            # Workflow not found - break chain traversal
            break

        # Reconstruct state from events
        state = replay_workflow(events)

        # Add to chain
        chain.append(state)

        # Move to parent workflow
        current_id = state.get("parent_workflow_id")

    # Check max depth
    if len(chain) >= max_depth and current_id:
        raise RuntimeError(
            f"Workflow chain exceeded max depth of {max_depth}. "
            f"Possible infinite loop or excessively deep hierarchy. "
            f"Last workflow: {chain[-1]['workflow_id']}"
        )

    # Reverse chain so root parent is first (chronological order)
    # Zen pattern: Present conversation turns chronologically for LLM comprehension
    chain.reverse()

    return chain


def get_workflow_chain_ids(workflow_id: str, event_loader: callable) -> List[str]:
    """Get workflow IDs in chain without full state reconstruction

    Lightweight alternative to get_workflow_chain() when only IDs are needed.

    Args:
        workflow_id: Starting workflow ID
        event_loader: Function that loads events for a workflow_id

    Returns:
        List of workflow IDs from root parent to current workflow

    Example:
        >>> get_workflow_chain_ids("rollback-456", event_loader)
        ["pr-123", "hotfix-234", "rollback-456"]
    """

    chain = get_workflow_chain(workflow_id, event_loader)
    return [state["workflow_id"] for state in chain]


def get_workflow_depth(workflow_id: str, event_loader: callable) -> int:
    """Get depth of workflow in parent-child hierarchy

    Useful for workflow composition analytics and depth limits.

    Args:
        workflow_id: Workflow ID to check
        event_loader: Function that loads events for a workflow_id

    Returns:
        Depth in hierarchy (1 = root workflow, 2 = child, 3 = grandchild, etc.)

    Example:
        >>> # PR deployment (root)
        >>> get_workflow_depth("pr-123", event_loader)
        1
        >>> # Hotfix (child of PR deployment)
        >>> get_workflow_depth("hotfix-234", event_loader)
        2
        >>> # Rollback (grandchild)
        >>> get_workflow_depth("rollback-456", event_loader)
        3
    """

    chain = get_workflow_chain(workflow_id, event_loader)
    return len(chain)
