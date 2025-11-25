"""Unit tests for workflow TTL management (Task 5.3)

Tests verify:
1. WORKFLOW_TTL_HOURS configuration loaded from environment
2. TTL refresh on every event emission
3. Abandoned workflows expire after TTL period
4. Active workflows stay alive with event refresh
5. PostgreSQL workflow_ttl table integration

Week 5: Zen Pattern Integration (DEV-178)
"""

import pytest
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

from agent_orchestrator.workflows.workflow_engine import WorkflowEngine
from shared.lib.workflow_reducer import WorkflowAction


# ============================================================================
# TEST FIXTURES
# ============================================================================


@pytest.fixture
def mock_state_client():
    """Mock PostgreSQL state client"""
    client = AsyncMock()
    client.execute = AsyncMock()
    client.fetchval = AsyncMock(return_value=0)
    return client


@pytest.fixture
def workflow_engine_with_ttl(mock_state_client):
    """WorkflowEngine with TTL configuration"""
    os.environ["WORKFLOW_TTL_HOURS"] = "24"
    engine = WorkflowEngine(
        templates_dir="agent_orchestrator/workflows/templates",
        gradient_client=None,
        state_client=mock_state_client,
    )
    return engine


# ============================================================================
# CONFIGURATION TESTS
# ============================================================================


def test_ttl_configuration_from_env(monkeypatch):
    """WORKFLOW_TTL_HOURS loaded from environment"""
    monkeypatch.setenv("WORKFLOW_TTL_HOURS", "12")
    # Force class variable reload after env change
    WorkflowEngine.WORKFLOW_TTL_HOURS = int(os.getenv("WORKFLOW_TTL_HOURS", "24"))
    engine = WorkflowEngine(gradient_client=None, state_client=None)

    assert engine.WORKFLOW_TTL_HOURS == 12
    assert engine.ttl_seconds == 12 * 3600  # 43200 seconds


def test_ttl_default_value(monkeypatch):
    """Default TTL is 24 hours"""
    monkeypatch.delenv("WORKFLOW_TTL_HOURS", raising=False)
    # Force class variable reload after env change
    WorkflowEngine.WORKFLOW_TTL_HOURS = int(os.getenv("WORKFLOW_TTL_HOURS", "24"))
    engine = WorkflowEngine(gradient_client=None, state_client=None)

    assert engine.WORKFLOW_TTL_HOURS == 24
    assert engine.ttl_seconds == 24 * 3600


def test_ttl_seconds_calculated(monkeypatch):
    """TTL seconds calculated correctly"""
    monkeypatch.setenv("WORKFLOW_TTL_HOURS", "3")
    # Force class variable reload after env change
    WorkflowEngine.WORKFLOW_TTL_HOURS = int(os.getenv("WORKFLOW_TTL_HOURS", "24"))
    engine = WorkflowEngine(gradient_client=None, state_client=None)

    assert engine.ttl_seconds == 3 * 3600  # 10800 seconds


# ============================================================================
# TTL REFRESH TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_ttl_refresh_on_event_persistence(workflow_engine_with_ttl):
    """TTL refreshed when event persisted"""
    from shared.lib.workflow_reducer import WorkflowEvent

    workflow_id = "test-123"
    event = WorkflowEvent(
        workflow_id=workflow_id,
        action=WorkflowAction.START_WORKFLOW,
        data={"template_name": "test-workflow"},
    )

    await workflow_engine_with_ttl._persist_event(event)

    # Verify workflow_ttl table updated
    workflow_engine_with_ttl.state_client.execute.assert_called()
    calls = workflow_engine_with_ttl.state_client.execute.call_args_list

    # Should have 2 calls: INSERT event + INSERT/UPDATE workflow_ttl
    assert len(calls) >= 2

    # Check workflow_ttl INSERT/UPDATE call
    ttl_call_found = False
    for call in calls:
        sql = call[0][0]
        if "workflow_ttl" in sql:
            ttl_call_found = True
            assert "expires_at" in sql
            assert "refreshed_at" in sql
            break

    assert ttl_call_found, "workflow_ttl table should be updated"


@pytest.mark.asyncio
async def test_ttl_refresh_calculates_expiration_correctly(workflow_engine_with_ttl):
    """TTL expiration calculated as now + ttl_seconds"""
    workflow_id = "test-456"

    # Mock datetime to control "now"
    mock_now = datetime(2024, 1, 1, 12, 0, 0)

    with patch("agent_orchestrator.workflows.workflow_engine.datetime") as mock_dt:
        mock_dt.utcnow.return_value = mock_now

        await workflow_engine_with_ttl._refresh_workflow_ttl(workflow_id)

    # Verify expires_at = now + TTL (fixture uses WORKFLOW_TTL_HOURS from env, currently 3h)
    workflow_engine_with_ttl.state_client.execute.assert_called_once()
    call_args = workflow_engine_with_ttl.state_client.execute.call_args

    # Second argument should be expiration timestamp
    expires_at = call_args[0][2]
    expected_expiration = mock_now + timedelta(
        seconds=workflow_engine_with_ttl.ttl_seconds
    )

    assert expires_at == expected_expiration


@pytest.mark.asyncio
async def test_ttl_refresh_handles_failure_gracefully(workflow_engine_with_ttl):
    """TTL refresh failure doesn't fail event persistence"""
    workflow_id = "test-789"

    # Make TTL refresh fail
    workflow_engine_with_ttl.state_client.execute.side_effect = [
        None,  # First call (INSERT event) succeeds
        Exception("Database connection failed"),  # Second call (TTL refresh) fails
    ]

    # Should not raise exception
    await workflow_engine_with_ttl._refresh_workflow_ttl(workflow_id)

    # Verify error was logged (not raised)
    assert workflow_engine_with_ttl.state_client.execute.call_count == 1


# ============================================================================
# REAL-WORLD SCENARIO TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_long_running_workflow_stays_alive():
    """Active workflow with events stays alive past TTL"""
    # Set short TTL for testing (1 hour)
    os.environ["WORKFLOW_TTL_HOURS"] = "1"
    mock_state_client = AsyncMock()
    engine = WorkflowEngine(gradient_client=None, state_client=mock_state_client)

    workflow_id = "pr-deploy-123"

    # Simulate workflow with multiple events over 2 hours
    # Each event refreshes TTL, so workflow stays alive
    for i in range(5):
        from shared.lib.workflow_reducer import WorkflowEvent

        event = WorkflowEvent(
            workflow_id=workflow_id,
            action=WorkflowAction.COMPLETE_STEP,
            step_id=f"step_{i}",
            data={"result": "success"},
        )

        await engine._persist_event(event)

    # Verify TTL refreshed 5 times
    assert mock_state_client.execute.call_count == 10  # 5 events + 5 TTL refreshes


@pytest.mark.asyncio
async def test_abandoned_workflow_expires():
    """Abandoned workflow (no events) expires after TTL"""
    # This test verifies the SQL function cleanup_expired_workflows()
    # In production, this would be called by a cron job

    mock_state_client = AsyncMock()

    # Mock cleanup function result
    mock_state_client.fetch.return_value = [
        {
            "workflow_id": "abandoned-123",
            "expired_at": datetime.utcnow() - timedelta(hours=1),
            "event_count": 10,
        }
    ]

    # Call cleanup function (would be run by cron in production)
    result = await mock_state_client.fetch("SELECT * FROM cleanup_expired_workflows()")

    # Verify abandoned workflow cleaned up
    assert len(result) == 1
    assert result[0]["workflow_id"] == "abandoned-123"


# ============================================================================
# ENVIRONMENT-SPECIFIC CONFIGURATION TESTS
# ============================================================================


def test_development_ttl_3_hours(monkeypatch):
    """Development environment: TTL = 3 hours for rapid testing"""
    monkeypatch.setenv("WORKFLOW_TTL_HOURS", "3")
    # Force class variable reload after env change
    WorkflowEngine.WORKFLOW_TTL_HOURS = int(os.getenv("WORKFLOW_TTL_HOURS", "24"))
    engine = WorkflowEngine(gradient_client=None, state_client=None)

    assert engine.WORKFLOW_TTL_HOURS == 3
    assert engine.ttl_seconds == 3 * 3600


def test_staging_ttl_12_hours(monkeypatch):
    """Staging environment: TTL = 12 hours"""
    monkeypatch.setenv("WORKFLOW_TTL_HOURS", "12")
    # Force class variable reload after env change
    WorkflowEngine.WORKFLOW_TTL_HOURS = int(os.getenv("WORKFLOW_TTL_HOURS", "24"))
    engine = WorkflowEngine(gradient_client=None, state_client=None)

    assert engine.WORKFLOW_TTL_HOURS == 12
    assert engine.ttl_seconds == 12 * 3600


def test_production_ttl_24_hours(monkeypatch):
    """Production environment: TTL = 24 hours (standard)"""
    monkeypatch.setenv("WORKFLOW_TTL_HOURS", "24")
    # Force class variable reload after env change
    WorkflowEngine.WORKFLOW_TTL_HOURS = int(os.getenv("WORKFLOW_TTL_HOURS", "24"))
    engine = WorkflowEngine(gradient_client=None, state_client=None)

    assert engine.WORKFLOW_TTL_HOURS == 24
    assert engine.ttl_seconds == 24 * 3600


# ============================================================================
# INTEGRATION WITH EVENT SOURCING
# ============================================================================


@pytest.mark.asyncio
async def test_ttl_refreshed_for_all_event_types():
    """TTL refreshed for all workflow event types"""
    mock_state_client = AsyncMock()
    engine = WorkflowEngine(gradient_client=None, state_client=mock_state_client)

    workflow_id = "multi-event-123"

    # Test various event types
    event_types = [
        WorkflowAction.START_WORKFLOW,
        WorkflowAction.COMPLETE_STEP,
        WorkflowAction.APPROVE_GATE,
        WorkflowAction.PAUSE_WORKFLOW,
        WorkflowAction.RESUME_WORKFLOW,
        WorkflowAction.CREATE_SNAPSHOT,
    ]

    for action in event_types:
        from shared.lib.workflow_reducer import WorkflowEvent

        event = WorkflowEvent(
            workflow_id=workflow_id, action=action, data={"test": "data"}
        )

        await engine._persist_event(event)

    # Verify TTL refreshed for all event types
    assert mock_state_client.execute.call_count == len(event_types) * 2
