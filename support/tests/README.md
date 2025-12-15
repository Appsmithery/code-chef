# Dev-Tools Test Suite

Comprehensive testing infrastructure for the Dev-Tools multi-agent platform.

## Test Structure

```
support/tests/
├── conftest.py              # Shared fixtures and configuration
├── pytest.ini               # pytest configuration
├── requirements.txt         # Test dependencies
├── e2e/                     # End-to-end workflow tests
│   ├── test_feature_workflow.py
│   ├── test_review_workflow.py
│   └── test_deploy_workflow.py
├── integration/             # Integration tests (DB, MCP)
│   └── test_postgres_checkpointing.py
├── workflows/               # Multi-agent workflow tests
│   └── test_agent_handoff.py
├── hitl/                    # HITL approval tests
│   └── test_linear_integration.py
└── performance/             # Performance and load tests
    └── test_concurrent_workflows.py
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r support/tests/requirements.txt
```

### 2. Run All Tests

```bash
# From repo root
pytest support/tests/ -v

# With coverage
pytest support/tests/ --cov=agent_orchestrator --cov=shared --cov-report=html
```

### 3. Run Specific Test Suites

```bash
# Unit tests only (fast, mocked)
pytest support/tests/ -m unit

# E2E tests
pytest support/tests/e2e/ -v

# Integration tests (requires services)
pytest support/tests/integration/ -v

# Performance tests
pytest support/tests/performance/ -v -s

# HITL tests
pytest support/tests/hitl/ -v
```

### 4. Run Single Test File

```bash
pytest support/tests/e2e/test_feature_workflow.py -v -s
```

## Test Markers

Use markers to filter tests:

- `@pytest.mark.unit` - Fast unit tests with mocks
- `@pytest.mark.integration` - Tests requiring real services
- `@pytest.mark.e2e` - End-to-end workflow tests
- `@pytest.mark.performance` - Performance and load tests
- `@pytest.mark.hitl` - HITL approval workflow tests
- `@pytest.mark.slow` - Tests taking >10 seconds

## Environment Setup

### Local Testing (Mocked)

No configuration needed. Tests use mocked clients by default.

```bash
pytest support/tests/e2e/ -v
```

### Integration Testing (Real Services)

1. Start Docker stack:

```bash
cd deploy
docker-compose up -d
```

2. Set environment variables:

```bash
# .env or shell
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/devtools"
export ORCHESTRATOR_URL="http://localhost:8001"
```

3. Run integration tests:

```bash
pytest support/tests/integration/ -v
```

### Production Testing (Real APIs)

1. Set API keys:

```bash
export GRADIENT_API_KEY="your-gradient-key"
export LINEAR_API_KEY="lin_api_..."  # Personal API Key from https://linear.app/dev-ops/settings/api
export LANGSMITH_API_KEY="lsv2_sk_..."
```

2. Run full test suite:

```bash
pytest support/tests/ -v --run-integration
```

## Shared Fixtures

Available in `conftest.py`:

### Mock Clients

- `mock_llm_client` - Mock LLM LLM client
- `mock_mcp_client` - Mock MCP gateway client
- `mock_linear_client` - Mock Linear GraphQL client

### Database

- `db_pool` - AsyncPG connection pool
- `clean_db` - Clean database before/after test

### HTTP

- `gateway_url` - MCP gateway URL
- `orchestrator_url` - Orchestrator URL

### Test Data

- `sample_task_request` - Sample task payload
- `sample_approval_request` - Sample approval payload
- `sample_workflow_state` - Sample LangGraph state

## Test Examples

### Unit Test (Mocked)

```python
import pytest

pytestmark = pytest.mark.unit

async def test_feature_workflow(mock_llm_client, mock_mcp_client):
    # Test with mocked clients
    result = await run_workflow()
    assert result["status"] == "success"
```

### Integration Test (Real Services)

```python
import pytest

pytestmark = pytest.mark.integration

@pytest.mark.skipif(
    not os.getenv("DATABASE_URL"),
    reason="Requires DATABASE_URL"
)
async def test_postgres_checkpoint(db_pool):
    # Test with real PostgreSQL
    async with db_pool.acquire() as conn:
        await conn.execute("INSERT INTO ...")
```

### E2E Test (Full Workflow)

```python
import pytest

pytestmark = pytest.mark.e2e

async def test_complete_feature_workflow():
    # Test complete workflow: supervisor → agent → approval → completion
    state = await orchestrator.process_task({
        "task": "Implement JWT auth"
    })

    assert state["status"] == "awaiting_approval"
    assert state["linear_issue_id"].startswith("DEV-")
```

## Performance Testing

### Concurrent Workflows

```bash
pytest support/tests/performance/test_concurrent_workflows.py::TestConcurrentWorkflowExecution::test_10_concurrent_workflows -v -s
```

Expected output:

```
✅ Concurrent workflow execution test passed
   - Total duration: 15.23s
   - Average workflow duration: 12.45s
   - Throughput: 0.66 workflows/sec
   - Workflows completed: 10
```

### Database Contention

```bash
pytest support/tests/performance/test_concurrent_workflows.py::TestConcurrentWorkflowExecution::test_checkpoint_database_contention -v -s
```

Expected output:

```
✅ Database contention test passed
   - Total duration: 2.34s
   - Average write duration: 45.2ms
   - Writes per second: 21.4
   - Total writes: 50
```

## Debugging Tests

### Verbose Output

```bash
pytest support/tests/e2e/test_feature_workflow.py -v -s
```

### Single Test Method

```bash
pytest support/tests/e2e/test_feature_workflow.py::TestFeatureDevelopmentWorkflow::test_high_risk_approval_flow -v -s
```

### Debug with breakpoints

```python
import pytest

async def test_debug():
    result = await some_function()
    pytest.set_trace()  # Breakpoint
    assert result == expected
```

### Show print statements

```bash
pytest support/tests/e2e/ -v -s  # -s shows print()
```

## Coverage Reports

Generate HTML coverage report:

```bash
pytest support/tests/ --cov=agent_orchestrator --cov=shared --cov-report=html

# Open report
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

## CI/CD Integration

### GitHub Actions (Planned)

```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - run: pip install -r support/tests/requirements.txt
      - run: pytest support/tests/ --cov --cov-report=xml

      - uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## Test Data Management

### Cleanup

Tests automatically clean up after themselves:

- Database: `TRUNCATE TABLE langgraph_checkpoints CASCADE`
- Docker: Container removal (if using testcontainers)
- Files: Temporary test artifacts deleted

### Isolation

Each test runs in isolation:

- Unique `thread_id` for workflows
- Separate database transactions
- Fresh mock instances

## Troubleshooting

### Database Connection Errors

```bash
# Ensure PostgreSQL is running
docker ps | grep postgres

# Check connection
psql postgresql://postgres:postgres@localhost:5432/test_devtools
```

### Orchestrator Unavailable

```bash
# Check orchestrator health
curl http://localhost:8001/health

# Restart orchestrator
cd deploy && docker-compose restart orchestrator
```

### Import Errors

```bash
# Verify Python path
pytest --collect-only support/tests/e2e/test_feature_workflow.py

# Install in development mode
pip install -e .
```

### Async Test Failures

Ensure `pytest-asyncio` is installed:

```bash
pip install pytest-asyncio>=0.23.0
```

## Contributing

When adding new tests:

1. Choose appropriate directory (`e2e/`, `integration/`, etc.)
2. Add pytest markers (`@pytest.mark.unit`, etc.)
3. Use shared fixtures from `conftest.py`
4. Include cleanup logic
5. Document expected behavior
6. Update this README

## Next Steps

- [ ] Add Qdrant vector memory tests
- [ ] Add hybrid memory system tests
- [ ] Create test workflow in GitHub Actions
- [ ] Set up coverage reporting (Codecov)
- [ ] Add test status badges to main README
- [ ] Create test documentation in `support/docs/TESTING.md`
- [ ] Add pre-commit hooks for test execution
