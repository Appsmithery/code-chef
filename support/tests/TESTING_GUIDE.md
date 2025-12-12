# Testing Guide: Dev-Tools Test Suite

**Last Updated**: December 12, 2025

## Quick Start

```powershell
# Install test dependencies
pip install -r support/tests/requirements.txt

# Run all tests (via VS Code Task or terminal)
pytest support/tests -v

# Run specific test categories
pytest support/tests/unit -v                    # Unit tests (fast, mocked)
pytest support/tests/integration -v             # Integration (requires services)
pytest support/tests/e2e -v                     # End-to-end workflows
pytest support/tests -m modelops -v             # ModelOps tests
pytest support/tests -m hitl -v                 # HITL tests
pytest support/tests -m evaluation -v           # Evaluation/A/B testing

# Run with coverage
pytest support/tests -v --cov=agent_orchestrator --cov=shared --cov-report=html

# Run property-based tests with more examples
$env:HYPOTHESIS_PROFILE="thorough"; pytest support/tests/unit/test_workflow_reducer.py -v
```

## Test Categories

| Category        | Purpose                    | Service Dependencies           | Run Time  |
| --------------- | -------------------------- | ------------------------------ | --------- |
| **Unit**        | Fast, isolated logic tests | None (mocked)                  | <5 min    |
| **Integration** | Service integration tests  | PostgreSQL, Prometheus         | 10-15 min |
| **E2E**         | Full workflow tests        | All services + Linear + GitHub | 20-30 min |
| **ModelOps**    | Training, eval, deployment | HuggingFace Space, LangSmith   | 5-90 min  |
| **HITL**        | Approval workflow tests    | PostgreSQL, Linear API         | 5-10 min  |
| **Evaluation**  | A/B testing & benchmarks   | PostgreSQL, LangSmith          | 10-20 min |
| **Performance** | Load & concurrency tests   | All services                   | 15-20 min |

## Environment Variables

### Required for Tests

```powershell
# Core Services
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/devtools"
$env:TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/devtools_test"

# ModelOps
$env:AUTOTRAIN_SPACE_URL="https://alextorelli-code-chef-modelops-trainer.hf.space"
$env:HUGGINGFACE_TOKEN="hf_***"

# LangSmith (with new project structure)
$env:LANGCHAIN_TRACING_V2="true"
$env:LANGCHAIN_API_KEY="lsv2_sk_***"
$env:LANGCHAIN_PROJECT="code-chef-production"  # or training, evaluation, experiments
$env:TRACE_ENVIRONMENT="production"  # or training, evaluation, test
$env:EXPERIMENT_GROUP="code-chef"  # or baseline

# HITL
$env:LINEAR_API_KEY="lin_api_***"
$env:LINEAR_TEAM_ID="dev-ops"
$env:LINEAR_PROJECT_ID="codechef-78b3b839d36b"

# GitHub (for Phase 2 HITL)
$env:GITHUB_TOKEN="ghp_***"

# Gradient AI
$env:GRADIENT_API_KEY="***"
$env:GRADIENT_WORKSPACE_ID="***"
```

## VS Code Integration

Tests are fully integrated with VS Code's Test Explorer:

1. **Open Test Explorer**: Click beaker icon in Activity Bar (or `Ctrl+Shift+P` → "Testing: Focus on Test Explorer View")
2. **Run tests**: Click ▶️ next to test file, class, or method
3. **Debug tests**: Right-click → "Debug Test"
4. **Use Tasks**: `Ctrl+Shift+P` → "Tasks: Run Task" → Select test task

See `support/tests/VSCODE_TESTING.md` for complete VS Code testing guide.

## Test Structure

### Unit Tests: `test_workflow_reducer.py`

**Property-Based Tests** (using Hypothesis):

- `test_start_workflow_creates_initial_state()` - Verify START_WORKFLOW creates valid initial state
- `test_complete_step_accumulates_steps()` - Verify COMPLETE_STEP accumulates in steps_completed
- `test_reducer_purity()` - Verify reducer never mutates inputs (deterministic)
- `test_replay_is_associative()` - Verify replay order doesn't affect final state
- `test_idempotent_pause()` - Verify PAUSE_WORKFLOW is idempotent

**Stateful Property Tests**:

- `WorkflowStateMachine` - Random sequences of workflow operations with invariants

**Unit Tests**:

- `test_reducer_handles_empty_state()` - Reducer works with empty initial state
- `test_complete_step_updates_outputs()` - COMPLETE_STEP stores step output
- `test_fail_step_marks_workflow_failed()` - FAIL_STEP marks workflow as failed
- `test_approve_gate_adds_approval()` - APPROVE_GATE records approval
- `test_rollback_reverts_step_output()` - ROLLBACK_STEP removes from completed
- `test_cancel_workflow_marks_cancelled()` - CANCEL_WORKFLOW marks cancelled
- `test_retry_step_increments_counter()` - RETRY_STEP tracks retry attempts
- `test_replay_workflow_reconstructs_state()` - Replay reconstructs exact state
- `test_get_state_at_timestamp()` - Time-travel debugging accuracy

**Performance Tests**:

- `test_replay_performance_large_event_log()` - Verify replay <1s for 1000 events

### Integration Tests: `test_event_replay.py`

**Event Replay Tests**:

- `test_full_workflow_execution_with_events()` - Execute workflow and verify event log
- `test_state_reconstruction_from_events()` - Verify state reconstruction from events
- `test_time_travel_debugging()` - Verify state-at-timestamp accuracy

**Event Signature Tests**:

- `test_event_signature_generation()` - Verify HMAC signature generation
- `test_event_signature_verification()` - Verify signature verification succeeds
- `test_tampered_event_detection()` - Verify tampered events detected
- `test_event_chain_validation()` - Verify entire event chain validation
- `test_tampered_chain_detection()` - Verify tampered chain detected

**Snapshot Tests**:

- `test_snapshot_creation()` - Verify snapshots created every 10 events
- `test_snapshot_plus_delta_equals_replay()` - Verify snapshot + delta = full replay

**Workflow Cancellation Tests**:

- `test_workflow_cancellation_emits_event()` - Verify CANCEL_WORKFLOW event
- `test_cancellation_cleanup_resources()` - Verify cleanup (locks, issues, agents)

**Retry Logic Tests**:

- `test_retry_step_emits_retry_event()` - Verify RETRY_STEP event emission
- `test_retry_increments_counter()` - Verify retry counter increments

**Compliance & Audit Tests**:

- `test_operator_annotations()` - Verify ANNOTATE event captured
- `test_event_archival_query()` - Verify old events queryable from archive

## Test Configuration

### Hypothesis Profiles

Configure property-based test thoroughness:

```powershell
# CI profile: Fast (20 examples)
$env:HYPOTHESIS_PROFILE="ci"
pytest support/tests/unit/test_workflow_reducer.py

# Dev profile: Default (100 examples)
$env:HYPOTHESIS_PROFILE="dev"
pytest support/tests/unit/test_workflow_reducer.py

# Thorough profile: Comprehensive (500 examples)
$env:HYPOTHESIS_PROFILE="thorough"
pytest support/tests/unit/test_workflow_reducer.py
```

### Test Markers

Run specific test categories:

```powershell
# Unit tests only (fast, mocked)
pytest -m unit

# Integration tests (requires services)
pytest -m integration

# Performance tests
pytest -m performance

# Async tests
pytest -m asyncio

# All tests except slow
pytest -m "not slow"
```

### Test Fixtures

Available fixtures in `conftest.py`:

- `secret_key` - HMAC secret key for event signatures
- `sample_workflow_template` - Sample workflow with 3 steps
- `sample_workflow_context` - Sample context (pr_number, repo, branch, author)
- `mock_gradient_client` - Mock Gradient AI client (model-agnostic)
- `mock_mcp_client` - Mock MCP client
- `mock_linear_client` - Mock Linear GraphQL client
- `mock_rag_client` - Mock RAG semantic search client
- `db_pool` - PostgreSQL connection pool
- `clean_db` - Clean database before each test

## RAG Testing

### RAG Collection Validation

Validate RAG collections are properly indexed:

```powershell
# Test Qdrant Cloud connectivity
python support/scripts/validation/test_qdrant_cloud.py

# Verify collection health
curl http://localhost:8007/collections
curl http://localhost:8007/health
```

**Active Collections** (as of December 2025):
| Collection | Vectors | Purpose |
|------------|---------|---------|
| `code_patterns` | 505 | Python AST patterns |
| `issue_tracker` | 155 | Linear issues |
| `library_registry` | 56 | Context7 library IDs |
| `vendor-docs` | 94 | API documentation |
| `feature_specs` | 4 | Linear projects |

### Semantic Search Testing

```python
# Test RAG query
import httpx

response = httpx.post("http://localhost:8007/query", json={
    "query": "workflow execution patterns",
    "collection": "code_patterns",
    "limit": 5
})
assert response.status_code == 200
assert len(response.json()["results"]) > 0
```

## Running Tests in CI/CD

### GitHub Actions Workflow

```yaml
- name: Install test dependencies
  run: pip install -r support/tests/requirements.txt

- name: Run unit tests
  run: pytest support/tests/unit/test_workflow_reducer.py -v --hypothesis-profile=ci

- name: Run integration tests
  run: pytest support/tests/integration/test_event_replay.py -v
  env:
    TEST_DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_devtools

- name: Generate coverage report
  run: |
    pytest support/tests -v \
      --cov=shared.lib.workflow_reducer \
      --cov=shared.lib.workflow_events \
      --cov=agent_orchestrator.workflows.workflow_engine \
      --cov-report=html \
      --cov-report=term-missing

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

## Test Development Guidelines

### Writing Property-Based Tests

Use Hypothesis strategies to generate test data:

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=50))
def test_workflow_id_handling(workflow_id):
    """Property: Workflow ID always handled correctly"""
    event = WorkflowEvent(workflow_id=workflow_id, ...)
    state = workflow_reducer({}, event)
    assert state["workflow_id"] == workflow_id
```

### Writing Stateful Tests

Use `RuleBasedStateMachine` for complex state transitions:

```python
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant

class WorkflowStateMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.state = {"status": "initialized"}

    @rule()
    def start_workflow(self):
        assume(self.state["status"] == "initialized")
        # Apply START_WORKFLOW

    @invariant()
    def state_is_valid(self):
        assert "status" in self.state
```

### Writing Integration Tests

Use async fixtures for real services:

```python
@pytest.mark.asyncio
async def test_full_workflow(workflow_engine):
    """Integration test with real WorkflowEngine"""
    result = await workflow_engine.execute_workflow(template, context)
    events = await workflow_engine._load_events(result["workflow_id"])
    assert len(events) > 0
```

## Test Coverage Gaps

The following gaps have been identified and prioritized for implementation:

### Critical Priority (15 gaps)

- ModelOps training job lifecycle tests (submission, monitoring, cancellation)
- LangSmith schema compliance tests (required metadata fields)
- Tool loading strategy tests (MINIMAL/PROGRESSIVE/FULL)
- HITL Phase 1 dedicated tests (core approval workflow)
- Deployment rollback procedures
- A/B test baseline/code-chef separation
- Config hash generation and validation
- Training data export from LangSmith
- Evaluation comparison engine edge cases
- Model registry CRUD validation
- Webhook signature validation
- Cost tracking per experiment group
- Agent tool binding at invoke time
- Progressive tool loader keyword matching
- Multi-agent workflow recovery

### High Priority (15 gaps)

- Phase 2 GitHub PR enrichment tests
- Webhook retry logic
- LangSmith project routing validation
- Training job concurrent execution
- Evaluation dataset integration
- Approval timeout handling
- Risk assessor logic validation
- Cost attribution per task_id
- Agent state isolation tests
- Tool loading cache validation
- Training failure scenarios
- Deployment health check validation
- Multi-PR approval handling
- GitHub API failure graceful degradation
- Longitudinal tracking regression detection

### Medium Priority (13 gaps)

- Cost tracking dashboard integration
- Approval metrics accuracy
- Model version history queries
- Training TensorBoard accessibility
- Evaluation statistical significance
- Config backup restoration
- Agent initialization performance
- Tool discovery debugging
- Trace metadata completeness
- Project selection logic
- Experiment ID correlation
- Task ID uniqueness validation
- Database index performance

### Low Priority (5 gaps)

- Linear API rate limiting
- Trace sampling strategy
- Alert notification delivery
- Dashboard refresh latency
- Log rotation validation

**Next Steps**: Prioritize Critical gaps for Week 1-2 implementation. See [CODE_CHEF_VALIDATION_SCENARIOS.md](CODE_CHEF_VALIDATION_SCENARIOS.md) for comprehensive validation scenarios.

## Troubleshooting

### Hypothesis Flaky Tests

If property-based tests fail intermittently:

```powershell
# Run with seed to reproduce
pytest --hypothesis-seed=12345

# Show generated examples
pytest --hypothesis-show-statistics
```

### Database Connection Issues

If integration tests fail with database errors:

```powershell
# Check PostgreSQL running
docker ps | grep postgres

# Verify test database exists
psql -h localhost -U postgres -c "CREATE DATABASE test_devtools;"

# Set test database URL
$env:TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/test_devtools"
```

### Async Test Failures

If async tests hang or timeout:

```powershell
# Run with timeout
pytest --timeout=10

# Debug async issues
pytest -v -s --log-cli-level=DEBUG
```

## Code Coverage Goals

- **Reducer purity**: 100% coverage (critical path)
- **Event utilities**: 95% coverage (serialization, signatures)
- **WorkflowEngine integration**: 90% coverage (event emission)
- **API endpoints**: 85% coverage (happy path + error handling)

## Next Steps

After completing testing infrastructure:

1. **Run tests in CI**: Add to `.github/workflows/test.yml`
2. **Set coverage threshold**: Require 90% coverage for PRs
3. **Add performance benchmarks**: Track replay performance over time
4. **Document test patterns**: Share best practices with team

## References

- [Hypothesis documentation](https://hypothesis.readthedocs.io/)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [Property-based testing guide](https://increment.com/testing/in-praise-of-property-based-testing/)
