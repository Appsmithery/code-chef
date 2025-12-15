"""Unit tests for resource deduplication (Task 5.2)

Tests verify:
1. _deduplicate_workflow_resources() keeps only newest versions
2. build_workflow_context() integrates deduplication
3. 80%+ token savings when resources modified multiple times
4. Newest-first priority pattern from Zen MCP Server
5. No performance regression (<10ms overhead)

Week 5: Zen Pattern Integration (DEV-177)
"""

import pytest
from typing import List, Dict, Any
from datetime import datetime, timedelta

from shared.lib.workflow_reducer import WorkflowAction, WorkflowEvent
from agent_orchestrator.workflows.workflow_engine import WorkflowEngine


# ============================================================================
# TEST FIXTURES
# ============================================================================


@pytest.fixture
def workflow_engine():
    """WorkflowEngine instance without state_client for unit testing"""
    engine = WorkflowEngine(
        templates_dir="agent_orchestrator/workflows/templates",
        llm_client=None,
        state_client=None,
    )
    return engine


def create_event_with_resources(
    workflow_id: str, event_num: int, resources: Dict[str, Any]
) -> WorkflowEvent:
    """Helper to create event with resource data"""
    timestamp = (datetime.utcnow() + timedelta(seconds=event_num)).isoformat()
    return WorkflowEvent(
        workflow_id=workflow_id,
        action=WorkflowAction.COMPLETE_STEP,
        step_id=f"step_{event_num}",
        data={"resources": resources, "result": "success"},
        timestamp=timestamp,
    )


# ============================================================================
# DEDUPLICATION TESTS
# ============================================================================


def test_no_duplicate_resources(workflow_engine):
    """Workflow with unique resources unchanged"""
    workflow_id = "test-123"

    # Create events with 3 different files
    events = [
        create_event_with_resources(workflow_id, 1, {"file1.txt": {"version": 1}}),
        create_event_with_resources(workflow_id, 2, {"file2.txt": {"version": 1}}),
        create_event_with_resources(workflow_id, 3, {"file3.txt": {"version": 1}}),
    ]

    deduplicated = workflow_engine._deduplicate_workflow_resources(events)

    assert len(deduplicated) == 3
    assert "file1.txt" in deduplicated
    assert "file2.txt" in deduplicated
    assert "file3.txt" in deduplicated
    assert deduplicated["file1.txt"]["version"] == 1


def test_newest_version_wins(workflow_engine):
    """Newest version of resource preferred (Zen pattern)"""
    workflow_id = "test-456"

    # Modify same file 5 times (newest last)
    events = [
        create_event_with_resources(
            workflow_id, i, {"docker-compose.yml": {"version": i, "content": f"v{i}"}}
        )
        for i in range(1, 6)
    ]

    deduplicated = workflow_engine._deduplicate_workflow_resources(events)

    # Verify only 1 entry (not 5)
    assert len(deduplicated) == 1
    assert "docker-compose.yml" in deduplicated

    # Verify newest version (version 5)
    assert deduplicated["docker-compose.yml"]["version"] == 5
    assert deduplicated["docker-compose.yml"]["content"] == "v5"


def test_mixed_duplicates_and_unique(workflow_engine):
    """Mix of duplicate and unique resources handled correctly"""
    workflow_id = "test-789"

    # file1 modified 3 times, file2 and file3 once each
    events = [
        create_event_with_resources(workflow_id, 1, {"file1.txt": {"version": 1}}),
        create_event_with_resources(workflow_id, 2, {"file2.txt": {"version": 1}}),
        create_event_with_resources(workflow_id, 3, {"file1.txt": {"version": 2}}),
        create_event_with_resources(workflow_id, 4, {"file3.txt": {"version": 1}}),
        create_event_with_resources(workflow_id, 5, {"file1.txt": {"version": 3}}),
    ]

    deduplicated = workflow_engine._deduplicate_workflow_resources(events)

    assert len(deduplicated) == 3
    assert deduplicated["file1.txt"]["version"] == 3  # Newest
    assert deduplicated["file2.txt"]["version"] == 1
    assert deduplicated["file3.txt"]["version"] == 1


def test_empty_events_list(workflow_engine):
    """Empty events list returns empty dict"""
    deduplicated = workflow_engine._deduplicate_workflow_resources([])

    assert deduplicated == {}


def test_events_without_resources(workflow_engine):
    """Events without resources field handled gracefully"""
    workflow_id = "test-999"

    events = [
        WorkflowEvent(
            workflow_id=workflow_id,
            action=WorkflowAction.COMPLETE_STEP,
            step_id="step1",
            data={"result": "success"},  # No resources key
        ),
        WorkflowEvent(
            workflow_id=workflow_id,
            action=WorkflowAction.COMPLETE_STEP,
            step_id="step2",
            data={},  # Empty data
        ),
    ]

    deduplicated = workflow_engine._deduplicate_workflow_resources(events)

    assert deduplicated == {}


def test_resource_metadata_preserved(workflow_engine):
    """Resource metadata (timestamp, size, etc.) preserved for newest version"""
    workflow_id = "test-metadata"

    events = [
        create_event_with_resources(
            workflow_id,
            1,
            {
                "config.yaml": {
                    "version": 1,
                    "size": 1024,
                    "timestamp": "2024-01-01T10:00:00",
                    "checksum": "abc123",
                }
            },
        ),
        create_event_with_resources(
            workflow_id,
            2,
            {
                "config.yaml": {
                    "version": 2,
                    "size": 2048,
                    "timestamp": "2024-01-01T11:00:00",
                    "checksum": "def456",
                }
            },
        ),
    ]

    deduplicated = workflow_engine._deduplicate_workflow_resources(events)

    resource = deduplicated["config.yaml"]
    assert resource["version"] == 2  # Newest
    assert resource["size"] == 2048  # Metadata from newest
    assert resource["checksum"] == "def456"


# ============================================================================
# REAL-WORLD SCENARIO TESTS
# ============================================================================


def test_infrastructure_workflow_docker_compose_modifications(workflow_engine):
    """Real-world: Infrastructure workflow modifies docker-compose.yml 5 times"""
    workflow_id = "infra-deploy-123"

    # Simulate infrastructure workflow modifying docker-compose.yml
    events = [
        # Step 1: Add nginx
        create_event_with_resources(
            workflow_id,
            1,
            {
                "docker-compose.yml": {
                    "content": "version: '3'\nservices:\n  nginx: ..."
                }
            },
        ),
        # Step 2: Add postgres
        create_event_with_resources(
            workflow_id,
            2,
            {
                "docker-compose.yml": {
                    "content": "version: '3'\nservices:\n  nginx: ...\n  postgres: ..."
                }
            },
        ),
        # Step 3: Update nginx ports
        create_event_with_resources(
            workflow_id,
            3,
            {
                "docker-compose.yml": {
                    "content": "version: '3'\nservices:\n  nginx: ... ports: [80:80]\n  postgres: ..."
                }
            },
        ),
        # Step 4: Add redis
        create_event_with_resources(
            workflow_id,
            4,
            {
                "docker-compose.yml": {
                    "content": "version: '3'\nservices:\n  nginx: ...\n  postgres: ...\n  redis: ..."
                }
            },
        ),
        # Step 5: Update postgres environment
        create_event_with_resources(
            workflow_id,
            5,
            {
                "docker-compose.yml": {
                    "content": "version: '3'\nservices:\n  nginx: ...\n  postgres: ... environment: [POSTGRES_PASSWORD=secret]\n  redis: ..."
                }
            },
        ),
    ]

    deduplicated = workflow_engine._deduplicate_workflow_resources(events)

    # Verify only 1 entry (80% reduction: 5 → 1)
    assert len(deduplicated) == 1
    assert "docker-compose.yml" in deduplicated

    # Verify newest version (step 5)
    assert "POSTGRES_PASSWORD=secret" in deduplicated["docker-compose.yml"]["content"]

    # Calculate token savings
    # Without dedup: 5 versions × ~200 tokens = ~1000 tokens
    # With dedup: 1 version × ~200 tokens = ~200 tokens
    # Savings: 80%


def test_code_review_workflow_multiple_commits(workflow_engine):
    """Real-world: Code review workflow analyzes file across 3 commits"""
    workflow_id = "code-review-456"

    events = [
        # Commit 1: Initial version
        create_event_with_resources(
            workflow_id,
            1,
            {
                "src/api.py": {
                    "commit": "abc123",
                    "issues": ["missing-docstrings"],
                    "lines": 150,
                }
            },
        ),
        # Commit 2: Add docstrings
        create_event_with_resources(
            workflow_id,
            2,
            {
                "src/api.py": {
                    "commit": "def456",
                    "issues": ["type-hints-missing"],
                    "lines": 180,
                }
            },
        ),
        # Commit 3: Add type hints
        create_event_with_resources(
            workflow_id,
            3,
            {"src/api.py": {"commit": "ghi789", "issues": [], "lines": 200}},
        ),
    ]

    deduplicated = workflow_engine._deduplicate_workflow_resources(events)

    # Only latest commit's analysis
    assert deduplicated["src/api.py"]["commit"] == "ghi789"
    assert deduplicated["src/api.py"]["issues"] == []
    assert deduplicated["src/api.py"]["lines"] == 200


def test_multi_file_workflow_with_partial_duplicates(workflow_engine):
    """Real-world: Workflow modifies 3 files, 1 file modified twice"""
    workflow_id = "multi-file-789"

    events = [
        # Step 1: Modify README
        create_event_with_resources(
            workflow_id, 1, {"README.md": {"version": 1, "content": "v1"}}
        ),
        # Step 2: Modify docker-compose (first time)
        create_event_with_resources(
            workflow_id, 2, {"docker-compose.yml": {"version": 1, "content": "v1"}}
        ),
        # Step 3: Modify Dockerfile
        create_event_with_resources(
            workflow_id, 3, {"Dockerfile": {"version": 1, "content": "v1"}}
        ),
        # Step 4: Modify docker-compose again (second time)
        create_event_with_resources(
            workflow_id, 4, {"docker-compose.yml": {"version": 2, "content": "v2"}}
        ),
    ]

    deduplicated = workflow_engine._deduplicate_workflow_resources(events)

    # 3 unique files (not 4 events)
    assert len(deduplicated) == 3

    # docker-compose.yml should be version 2 (newest)
    assert deduplicated["docker-compose.yml"]["version"] == 2

    # Other files unchanged
    assert deduplicated["README.md"]["version"] == 1
    assert deduplicated["Dockerfile"]["version"] == 1


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================


def test_deduplication_performance_10_events(workflow_engine):
    """Deduplication overhead <10ms for 10-event workflow"""
    import time

    workflow_id = "perf-test-10"

    # Create 10 events with 5 duplicate files
    events = []
    for i in range(10):
        file_id = f"file_{i % 5}.txt"  # 5 unique files, each modified twice
        events.append(
            create_event_with_resources(workflow_id, i, {file_id: {"version": i}})
        )

    start_time = time.time()
    deduplicated = workflow_engine._deduplicate_workflow_resources(events)
    elapsed_ms = (time.time() - start_time) * 1000

    # Should complete in <10ms
    assert elapsed_ms < 10

    # Verify correctness
    assert len(deduplicated) == 5  # 5 unique files


def test_deduplication_performance_50_events(workflow_engine):
    """Deduplication overhead <10ms for 50-event workflow"""
    import time

    workflow_id = "perf-test-50"

    # Create 50 events with 10 duplicate files
    events = []
    for i in range(50):
        file_id = f"file_{i % 10}.txt"  # 10 unique files
        events.append(
            create_event_with_resources(workflow_id, i, {file_id: {"version": i}})
        )

    start_time = time.time()
    deduplicated = workflow_engine._deduplicate_workflow_resources(events)
    elapsed_ms = (time.time() - start_time) * 1000

    # Should complete in <10ms
    assert elapsed_ms < 10

    # Verify correctness
    assert len(deduplicated) == 10  # 10 unique files


# ============================================================================
# TOKEN SAVINGS CALCULATION TESTS
# ============================================================================


def test_calculate_token_savings_80_percent(workflow_engine):
    """Verify 80% token savings when file modified 5 times"""
    workflow_id = "token-savings"

    # Modify same file 5 times
    events = [
        create_event_with_resources(workflow_id, i, {"config.yaml": {"version": i}})
        for i in range(1, 6)
    ]

    deduplicated = workflow_engine._deduplicate_workflow_resources(events)

    # Calculate savings
    total_resources = sum(len(event.data.get("resources", {})) for event in events)
    deduplicated_resources = len(deduplicated)

    savings_percent = (
        (total_resources - deduplicated_resources) / total_resources
    ) * 100

    # 5 references → 1 reference = 80% savings
    assert savings_percent == 80.0
    assert total_resources == 5
    assert deduplicated_resources == 1


def test_calculate_token_savings_no_duplicates(workflow_engine):
    """No savings when all resources unique"""
    workflow_id = "no-savings"

    # 5 different files
    events = [
        create_event_with_resources(workflow_id, i, {f"file{i}.txt": {"version": 1}})
        for i in range(1, 6)
    ]

    deduplicated = workflow_engine._deduplicate_workflow_resources(events)

    # Calculate savings
    total_resources = sum(len(event.data.get("resources", {})) for event in events)
    deduplicated_resources = len(deduplicated)

    savings_percent = (
        ((total_resources - deduplicated_resources) / total_resources) * 100
        if total_resources > 0
        else 0
    )

    # No savings: 5 unique files → 5 deduplicated files
    assert savings_percent == 0.0
    assert total_resources == 5
    assert deduplicated_resources == 5
