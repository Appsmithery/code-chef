# VS Code Python Testing Setup Guide

## Overview

This guide explains how to use VS Code's native Python testing features with the Dev-Tools test suite.

## Prerequisites

1. **Install VS Code Extensions** (recommended extensions are in `.vscode/extensions.json`):

   - `ms-python.python` - Python language support
   - `ms-python.vscode-pylance` - Python IntelliSense
   - `ms-python.black-formatter` - Python code formatter
   - `littlefoxteam.vscode-python-test-adapter` - Enhanced test UI

   **Quick Install**: Press `Ctrl+Shift+P`, type "Extensions: Show Recommended Extensions", and install all.

2. **Install Test Dependencies**:

   ```bash
   pip install -r support/tests/requirements.txt
   ```

   Or use VS Code Task: `Ctrl+Shift+P` → "Tasks: Run Task" → "Install Test Dependencies"

## Test Explorer

### Open Test Explorer

1. Click the **Testing** icon in the Activity Bar (left sidebar) - looks like a beaker/flask
2. Or press `Ctrl+Shift+P` → "Testing: Focus on Test Explorer View"

### Discover Tests

Tests should be auto-discovered on save. If not:

1. Click the **Refresh** icon in Test Explorer
2. Or run: `Ctrl+Shift+P` → "Testing: Refresh Tests"

### Test Structure in Explorer

```
Dev-Tools/
├── support/tests/
│   ├── e2e/
│   │   ├── TestFeatureDevelopmentWorkflow
│   │   │   ├── test_high_risk_approval_flow
│   │   │   ├── test_workflow_resume_after_approval
│   │   │   └── ...
│   │   ├── TestCodeReviewWorkflow
│   │   └── TestDeploymentWorkflow
│   ├── integration/
│   │   ├── TestPostgresCheckpointing
│   │   └── TestMCPGatewayDiscovery
│   └── workflows/
│       └── TestAgentHandoff
```

## Running Tests

### Via Test Explorer

1. **Run All Tests**: Click the ▶️ icon at the top of Test Explorer
2. **Run Single Test File**: Click ▶️ next to the file name
3. **Run Single Test Class**: Click ▶️ next to the class name
4. **Run Single Test Method**: Click ▶️ next to the test method name

### Via Command Palette

- `Ctrl+Shift+P` → "Testing: Run All Tests"
- `Ctrl+Shift+P` → "Testing: Run Failed Tests"
- `Ctrl+Shift+P` → "Testing: Run Last Run"

### Via Tasks

Press `Ctrl+Shift+P` → "Tasks: Run Task" → Select task:

- **Run All Tests** - All tests with verbose output
- **Run E2E Tests** - End-to-end workflow tests
- **Run Integration Tests** - Integration tests (requires services)
- **Run Unit Tests** - Fast unit tests only
- **Run Performance Tests** - Performance and load tests
- **Run Tests with Coverage** - Generate coverage report

### Via Keyboard Shortcuts

Default shortcuts (can be customized):

- Run tests in current file: No default (customize in Keyboard Shortcuts)
- Debug current test: Right-click test → "Debug Test"

## Debugging Tests

### Debug Single Test

1. **Via Test Explorer**:

   - Right-click test → "Debug Test"
   - Or click the debug icon next to test name

2. **Via Launch Configuration**:
   - Set breakpoint in test file
   - Press `F5` → Select "Python: Debug Tests"

### Debug Configurations Available

Access via Debug panel (`Ctrl+Shift+D`) or `F5`:

- **Python: Debug Tests** - Debug current test file
- **Python: Debug Current Test** - Debug selected test (select test name first)
- **Python: All Tests** - Debug all tests
- **Python: E2E Tests** - Debug E2E tests
- **Python: Integration Tests** - Debug integration tests
- **Python: Performance Tests** - Debug performance tests
- **Python: Tests with Coverage** - Debug with coverage

### Set Breakpoints

1. Click in the gutter (left of line numbers)
2. Or press `F9` on the line
3. Breakpoint appears as red dot

### Debug Controls

- `F5` - Continue
- `F10` - Step Over
- `F11` - Step Into
- `Shift+F11` - Step Out
- `Ctrl+Shift+F5` - Restart
- `Shift+F5` - Stop

## Test Markers

Filter tests using pytest markers:

### Via Command Line

```bash
# Run only unit tests (fast, mocked)
pytest support/tests -m unit

# Run only integration tests
pytest support/tests -m integration

# Run only E2E tests
pytest support/tests -m e2e

# Run only performance tests
pytest support/tests -m performance
```

### Via VS Code Settings

Edit `.vscode/settings.json`:

```json
"python.testing.pytestArgs": [
  "support/tests",
  "-v",
  "-m",
  "unit"  // Change to filter by marker
]
```

## Coverage Reports

### Generate Coverage

1. **Via Task**: `Ctrl+Shift+P` → "Tasks: Run Task" → "Run Tests with Coverage"
2. **Via Command Line**:
   ```bash
   pytest support/tests --cov=agent_orchestrator --cov=shared --cov-report=html
   ```

### View Coverage

1. **Via Task**: `Ctrl+Shift+P` → "Tasks: Run Task" → "Open Coverage Report"
2. **Manually**: Open `htmlcov/index.html` in browser

### Coverage in Editor

Install `Coverage Gutters` extension for inline coverage:

1. Install: `ryanluker.vscode-coverage-gutters`
2. Run tests with coverage
3. Click "Watch" in status bar

## Configuration Files

### `.vscode/settings.json`

```jsonc
{
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.testing.pytestArgs": [
    "support/tests",
    "-v",
    "--tb=short",
    "--strict-markers"
  ],
  "python.testing.cwd": "${workspaceFolder}",
  "python.testing.autoTestDiscoverOnSaveEnabled": true,
  "python.envFile": "${workspaceFolder}/config/env/.env"
}
```

Key settings:

- `pytestEnabled: true` - Use pytest framework
- `pytestArgs` - Default pytest arguments
- `autoTestDiscoverOnSaveEnabled` - Auto-discover tests on save
- `envFile` - Load environment variables from .env

### `support/tests/pytest.ini`

Main pytest configuration:

- Test discovery patterns
- Custom markers
- Timeout settings
- Log configuration
- Coverage options

### `support/tests/conftest.py`

Shared fixtures for all tests:

- Mock clients (Gradient AI, MCP, Linear)
- Database fixtures
- HTTP clients
- Test data
- Cleanup utilities

## Environment Variables

Tests load environment from `config/env/.env`:

```bash
# Required for integration tests
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/devtools
MCP_GATEWAY_URL=http://localhost:8000
ORCHESTRATOR_URL=http://localhost:8001

# Required for real API tests
GRADIENT_API_KEY=your-key
LINEAR_API_KEY=lin_api_...  # Personal API Key from https://linear.app/dev-ops/settings/api
LANGSMITH_API_KEY=lsv2_sk_...
```

## Test Output

### In Test Explorer

- ✅ Green checkmark = Passed
- ❌ Red X = Failed
- ⏭️ Blue arrow = Skipped
- ⏱️ Clock = Running

Click test to see output in "Test Results" panel.

### In Terminal

Tests run in integrated terminal with:

- Colored output
- Test names and status
- Error tracebacks
- Timing information

## Troubleshooting

### Tests Not Discovered

1. Check Python interpreter: Bottom-left status bar
2. Refresh tests: Test Explorer → Refresh icon
3. Check pytest installation: `pip show pytest`
4. Verify pytest.ini path: Should be `support/tests/pytest.ini`

### Import Errors

1. Check Python path in settings.json
2. Verify shared modules in sys.path
3. Run from repo root: `cd D:\INFRA\Dev-Tools\Dev-Tools`

### Database Connection Errors

1. Start PostgreSQL: `docker compose up -d postgres`
2. Check connection: `psql postgresql://postgres:postgres@localhost:5432/devtools`
3. Create test database: `createdb test_devtools`

### Service Unavailable

Integration tests require services:

```bash
cd deploy
docker compose up -d
```

Check health:

```bash
curl http://localhost:8000/health  # MCP Gateway
curl http://localhost:8001/health  # Orchestrator
```

### Slow Test Discovery

1. Reduce test scope in settings.json:

   ```json
   "python.testing.pytestArgs": [
     "support/tests/e2e",  // Only E2E tests
     "-v"
   ]
   ```

2. Or disable auto-discovery:
   ```json
   "python.testing.autoTestDiscoverOnSaveEnabled": false
   ```

## Advanced Features

### Parameterized Tests

Tests with multiple inputs appear as multiple test cases in Test Explorer.

### Async Tests

Async tests (using `pytest-asyncio`) work seamlessly with VS Code testing.

### Test Fixtures

Shared fixtures from `conftest.py` are automatically available in all tests.

### Test Markers

Filter tests by marker in Test Explorer using search: `@marker:unit`

## Best Practices

1. **Run Unit Tests Frequently**: Fast feedback during development
2. **Run Integration Tests Before Commit**: Validate with real services
3. **Use Debugging Liberally**: Set breakpoints to understand failures
4. **Check Coverage Regularly**: Aim for >80% coverage
5. **Keep Tests Green**: Fix failing tests immediately

## Quick Reference

| Action             | Shortcut                   | Command                                 |
| ------------------ | -------------------------- | --------------------------------------- |
| Run all tests      | Test Explorer ▶️           | `Ctrl+Shift+P` → Testing: Run All Tests |
| Run current file   | Test Explorer ▶️           | Right-click → Run Tests                 |
| Debug test         | Right-click → Debug        | `F5` → Debug Tests                      |
| Refresh tests      | Test Explorer 🔄           | `Ctrl+Shift+P` → Testing: Refresh Tests |
| Open Test Explorer | `Ctrl+Shift+T` (custom)    | View → Testing                          |
| Run task           | `Ctrl+Shift+P`             | Tasks: Run Task                         |
| View output        | Test Explorer → Click test | Output panel                            |

## Additional Resources

- [VS Code Python Testing Docs](https://code.visualstudio.com/docs/python/testing)
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Dev-Tools Test Suite README](./README.md)

---

**Need Help?** Check `support/tests/README.md` for detailed test documentation.
