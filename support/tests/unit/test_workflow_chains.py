"""Unit tests for parent workflow chains (Task 5.1)

Tests verify:
1. Parent workflow ID tracking in WorkflowEvent and state
2. get_workflow_chain() traverses parent-child relationships correctly
3. Circular reference detection prevents infinite loops
4. Max depth limit (20 levels) enforced
5. Chain ordering (chronological: root parent first)
6. Helper functions: get_workflow_chain_ids(), get_workflow_depth()

Week 5: Zen Pattern Integration (DEV-176)
"""

import pytest
from typing import List

from shared.lib.workflow_reducer import (
    WorkflowAction,
    WorkflowEvent,
    workflow_reducer,
    replay_workflow,
    get_workflow_chain,
    get_workflow_chain_ids,
    get_workflow_depth,
)


# ============================================================================
# TEST FIXTURES
# ============================================================================


@pytest.fixture
def event_store():
    """In-memory event store for testing"""
    store = {}

    def _store_events(workflow_id: str, events: List[WorkflowEvent]):
        """Store events for a workflow"""
        store[workflow_id] = events

    def _load_events(workflow_id: str) -> List[WorkflowEvent]:
        """Load events for a workflow"""
        return store.get(workflow_id, [])

    _store_events.load = _load_events
    return _store_events


def create_workflow_with_events(
    workflow_id: str,
    parent_workflow_id: str = None,
    template_name: str = "test-workflow",
) -> List[WorkflowEvent]:
    """Helper to create a workflow with START_WORKFLOW event"""
    events = [
        WorkflowEvent(
            workflow_id=workflow_id,
            action=WorkflowAction.START_WORKFLOW,
            parent_workflow_id=parent_workflow_id,
            step_id="step1",
            data={"template_name": template_name},
        )
    ]
    return events


# ============================================================================
# PARENT WORKFLOW ID TRACKING TESTS
# ============================================================================


def test_workflow_event_has_parent_workflow_id_field():
    """WorkflowEvent dataclass has parent_workflow_id field"""
    event = WorkflowEvent(
        workflow_id="child-123",
        action=WorkflowAction.START_WORKFLOW,
        parent_workflow_id="parent-456",
    )

    assert event.parent_workflow_id == "parent-456"


def test_workflow_event_parent_workflow_id_optional():
    """parent_workflow_id is optional (None for root workflows)"""
    event = WorkflowEvent(
        workflow_id="root-123",
        action=WorkflowAction.START_WORKFLOW,
        parent_workflow_id=None,
    )

    assert event.parent_workflow_id is None


def test_start_workflow_stores_parent_workflow_id_in_state():
    """START_WORKFLOW action stores parent_workflow_id in state"""
    event = WorkflowEvent(
        workflow_id="child-123",
        action=WorkflowAction.START_WORKFLOW,
        parent_workflow_id="parent-456",
        data={"template_name": "hotfix"},
    )

    state = workflow_reducer({}, event)

    assert state["parent_workflow_id"] == "parent-456"


def test_start_workflow_without_parent_stores_none():
    """START_WORKFLOW without parent stores None in state"""
    event = WorkflowEvent(
        workflow_id="root-123",
        action=WorkflowAction.START_WORKFLOW,
        parent_workflow_id=None,
        data={"template_name": "pr-deployment"},
    )

    state = workflow_reducer({}, event)

    assert state["parent_workflow_id"] is None


# ============================================================================
# GET_WORKFLOW_CHAIN() TESTS
# ============================================================================


def test_single_workflow_chain(event_store):
    """Single workflow with no parent returns itself"""
    workflow_id = "solo-123"
    events = create_workflow_with_events(workflow_id, parent_workflow_id=None)
    event_store(workflow_id, events)

    chain = get_workflow_chain(workflow_id, event_store.load)

    assert len(chain) == 1
    assert chain[0]["workflow_id"] == workflow_id
    assert chain[0]["parent_workflow_id"] is None


def test_parent_child_chain(event_store):
    """Parent-child relationship traversed correctly"""
    parent_id = "parent-123"
    child_id = "child-456"

    # Create parent workflow (no parent)
    parent_events = create_workflow_with_events(
        parent_id, parent_workflow_id=None, template_name="pr-deployment"
    )
    event_store(parent_id, parent_events)

    # Create child workflow (with parent)
    child_events = create_workflow_with_events(
        child_id, parent_workflow_id=parent_id, template_name="hotfix"
    )
    event_store(child_id, child_events)

    # Get chain starting from child
    chain = get_workflow_chain(child_id, event_store.load)

    # Verify chain order (parent first, then child)
    assert len(chain) == 2
    assert chain[0]["workflow_id"] == parent_id
    assert chain[0]["template_name"] == "pr-deployment"
    assert chain[1]["workflow_id"] == child_id
    assert chain[1]["template_name"] == "hotfix"
    assert chain[1]["parent_workflow_id"] == parent_id


def test_three_level_workflow_hierarchy(event_store):
    """3-level hierarchy: grandparent → parent → child"""
    grandparent_id = "grandparent-111"
    parent_id = "parent-222"
    child_id = "child-333"

    # Create grandparent
    grandparent_events = create_workflow_with_events(
        grandparent_id, parent_workflow_id=None, template_name="deploy"
    )
    event_store(grandparent_id, grandparent_events)

    # Create parent (child of grandparent)
    parent_events = create_workflow_with_events(
        parent_id, parent_workflow_id=grandparent_id, template_name="configure"
    )
    event_store(parent_id, parent_events)

    # Create child (child of parent)
    child_events = create_workflow_with_events(
        child_id, parent_workflow_id=parent_id, template_name="rollback"
    )
    event_store(child_id, child_events)

    # Get chain starting from child
    chain = get_workflow_chain(child_id, event_store.load)

    # Verify chain order (grandparent → parent → child)
    assert len(chain) == 3
    assert chain[0]["workflow_id"] == grandparent_id
    assert chain[1]["workflow_id"] == parent_id
    assert chain[2]["workflow_id"] == child_id


def test_circular_reference_detection(event_store):
    """Circular parent references raise ValueError"""
    workflow_a = "workflow-a"
    workflow_b = "workflow-b"

    # Create circular reference: A → B → A
    events_a = create_workflow_with_events(
        workflow_a, parent_workflow_id=workflow_b, template_name="workflow-a"
    )
    event_store(workflow_a, events_a)

    events_b = create_workflow_with_events(
        workflow_b, parent_workflow_id=workflow_a, template_name="workflow-b"
    )
    event_store(workflow_b, events_b)

    # Should raise ValueError when circular reference detected
    with pytest.raises(ValueError, match="Circular reference detected"):
        get_workflow_chain(workflow_a, event_store.load)


def test_max_depth_protection(event_store):
    """Workflow chains limited to 20 levels"""
    # Create 25-level deep chain
    workflow_ids = [f"workflow-{i}" for i in range(25)]

    # Create chain: workflow-0 → workflow-1 → ... → workflow-24
    for i, workflow_id in enumerate(workflow_ids):
        parent_id = workflow_ids[i - 1] if i > 0 else None
        events = create_workflow_with_events(
            workflow_id, parent_workflow_id=parent_id, template_name=f"workflow-{i}"
        )
        event_store(workflow_id, events)

    # Should raise RuntimeError when max depth exceeded
    with pytest.raises(RuntimeError, match="exceeded max depth"):
        get_workflow_chain(workflow_ids[-1], event_store.load)


def test_workflow_not_found_breaks_chain(event_store):
    """Missing workflow in chain breaks traversal gracefully"""
    child_id = "child-123"
    missing_parent_id = "missing-parent-456"

    # Create child with reference to non-existent parent
    child_events = create_workflow_with_events(
        child_id, parent_workflow_id=missing_parent_id, template_name="child"
    )
    event_store(child_id, child_events)

    # Should return only child workflow (parent not found)
    chain = get_workflow_chain(child_id, event_store.load)

    assert len(chain) == 1
    assert chain[0]["workflow_id"] == child_id


def test_event_loader_failure_raises_runtime_error(event_store):
    """Event loader failure raises RuntimeError"""

    def failing_loader(workflow_id: str):
        raise Exception("Database connection failed")

    with pytest.raises(RuntimeError, match="Failed to load events"):
        get_workflow_chain("test-123", failing_loader)


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================


def test_get_workflow_chain_ids(event_store):
    """get_workflow_chain_ids() returns only workflow IDs"""
    parent_id = "parent-123"
    child_id = "child-456"

    parent_events = create_workflow_with_events(parent_id, parent_workflow_id=None)
    event_store(parent_id, parent_events)

    child_events = create_workflow_with_events(child_id, parent_workflow_id=parent_id)
    event_store(child_id, child_events)

    chain_ids = get_workflow_chain_ids(child_id, event_store.load)

    assert chain_ids == [parent_id, child_id]


def test_get_workflow_depth_root_workflow(event_store):
    """Root workflow has depth 1"""
    workflow_id = "root-123"
    events = create_workflow_with_events(workflow_id, parent_workflow_id=None)
    event_store(workflow_id, events)

    depth = get_workflow_depth(workflow_id, event_store.load)

    assert depth == 1


def test_get_workflow_depth_child_workflow(event_store):
    """Child workflow has depth 2"""
    parent_id = "parent-123"
    child_id = "child-456"

    parent_events = create_workflow_with_events(parent_id, parent_workflow_id=None)
    event_store(parent_id, parent_events)

    child_events = create_workflow_with_events(child_id, parent_workflow_id=parent_id)
    event_store(child_id, child_events)

    depth = get_workflow_depth(child_id, event_store.load)

    assert depth == 2


def test_get_workflow_depth_grandchild_workflow(event_store):
    """Grandchild workflow has depth 3"""
    grandparent_id = "grandparent-111"
    parent_id = "parent-222"
    child_id = "child-333"

    grandparent_events = create_workflow_with_events(
        grandparent_id, parent_workflow_id=None
    )
    event_store(grandparent_id, grandparent_events)

    parent_events = create_workflow_with_events(
        parent_id, parent_workflow_id=grandparent_id
    )
    event_store(parent_id, parent_events)

    child_events = create_workflow_with_events(child_id, parent_workflow_id=parent_id)
    event_store(child_id, child_events)

    depth = get_workflow_depth(child_id, event_store.load)

    assert depth == 3


# ============================================================================
# REAL-WORLD SCENARIO TESTS
# ============================================================================


def test_pr_deployment_with_hotfix_child(event_store):
    """Real-world: PR deployment spawns hotfix workflow"""
    pr_workflow_id = "pr-deploy-123"
    hotfix_workflow_id = "hotfix-234"

    # PR deployment (parent)
    pr_events = create_workflow_with_events(
        pr_workflow_id, parent_workflow_id=None, template_name="pr-deployment"
    )
    # Add deployment failure event
    pr_events.append(
        WorkflowEvent(
            workflow_id=pr_workflow_id,
            action=WorkflowAction.FAIL_STEP,
            step_id="deploy",
            data={"error": "memory leak detected"},
        )
    )
    event_store(pr_workflow_id, pr_events)

    # Hotfix spawned as child
    hotfix_events = create_workflow_with_events(
        hotfix_workflow_id, parent_workflow_id=pr_workflow_id, template_name="hotfix"
    )
    event_store(hotfix_workflow_id, hotfix_events)

    # Get chain
    chain = get_workflow_chain(hotfix_workflow_id, event_store.load)

    assert len(chain) == 2
    assert chain[0]["template_name"] == "pr-deployment"
    assert chain[0]["status"] == "failed"
    assert chain[1]["template_name"] == "hotfix"
    assert chain[1]["parent_workflow_id"] == pr_workflow_id


def test_infrastructure_deployment_with_rollback_chain(event_store):
    """Real-world: Infrastructure deployment → config → rollback"""
    deploy_id = "deploy-v2.0"
    config_id = "configure-nginx"
    rollback_id = "rollback-v1.9"

    # Main deployment
    deploy_events = create_workflow_with_events(
        deploy_id, parent_workflow_id=None, template_name="deploy-v2.0"
    )
    event_store(deploy_id, deploy_events)

    # Configuration (child of deployment)
    config_events = create_workflow_with_events(
        config_id, parent_workflow_id=deploy_id, template_name="configure-nginx"
    )
    event_store(config_id, config_events)

    # Rollback (child of configuration)
    rollback_events = create_workflow_with_events(
        rollback_id, parent_workflow_id=config_id, template_name="rollback-v1.9"
    )
    event_store(rollback_id, rollback_events)

    # Get chain starting from rollback
    chain = get_workflow_chain(rollback_id, event_store.load)

    # Verify audit trail
    assert len(chain) == 3
    assert chain[0]["template_name"] == "deploy-v2.0"
    assert chain[1]["template_name"] == "configure-nginx"
    assert chain[2]["template_name"] == "rollback-v1.9"

    # Verify depth
    assert get_workflow_depth(rollback_id, event_store.load) == 3


# ============================================================================
# INTEGRATION WITH EXISTING REDUCER TESTS
# ============================================================================


def test_parent_workflow_id_persists_across_events(event_store):
    """parent_workflow_id remains in state across multiple events"""
    workflow_id = "child-123"
    parent_id = "parent-456"

    # Start workflow with parent
    events = [
        WorkflowEvent(
            workflow_id=workflow_id,
            action=WorkflowAction.START_WORKFLOW,
            parent_workflow_id=parent_id,
            data={"template_name": "hotfix"},
        ),
        WorkflowEvent(
            workflow_id=workflow_id,
            action=WorkflowAction.COMPLETE_STEP,
            step_id="step1",
            data={"result": "success"},
        ),
        WorkflowEvent(
            workflow_id=workflow_id,
            action=WorkflowAction.COMPLETE_STEP,
            step_id="step2",
            data={"result": "success"},
        ),
    ]
    event_store(workflow_id, events)

    # Replay workflow
    final_state = replay_workflow(events)

    # Verify parent_workflow_id persists
    assert final_state["parent_workflow_id"] == parent_id
    assert len(final_state["steps_completed"]) == 2


def test_workflow_event_serialization_includes_parent_workflow_id():
    """WorkflowEvent.to_dict() includes parent_workflow_id"""
    event = WorkflowEvent(
        workflow_id="child-123",
        action=WorkflowAction.START_WORKFLOW,
        parent_workflow_id="parent-456",
    )

    event_dict = event.to_dict()

    assert "parent_workflow_id" in event_dict
    assert event_dict["parent_workflow_id"] == "parent-456"
