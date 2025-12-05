# E2E LangSmith Trace Evaluation Strategy

**Last Updated**: December 5, 2025  
**Status**: Implementation Plan  
**Linear Issue**: [DEV-195](https://linear.app/dev-ops/issue/DEV-195/implement-e2e-langsmith-trace-evaluation-system)  
**Related**: [LANGSMITH_TRACING.md](LANGSMITH_TRACING.md), [OBSERVABILITY_GUIDE.md](../OBSERVABILITY_GUIDE.md)

---

## Overview

Implement a dual-project evaluation system for LangSmith traces using natural development workflows and CI/CD validation. This strategy leverages:

- **LangSmith Projects** for trace isolation (production vs. testing)
- **Existing E2E tests** in `support/tests/e2e/` for trace generation
- **RAG collections** for scenario seeding from Linear issues
- **GitHub Actions** for automated evaluation runs

---

## 1. Multi-Project Trace Isolation

Configure separate LangSmith projects to isolate production and evaluation traces.

### Environment Configuration

```bash
# config/env/.env (production)
LANGCHAIN_PROJECT=code-chef
LANGSMITH_TRACING=true
LANGCHAIN_TRACING_V2=true
LANGSMITH_WORKSPACE_ID=5029c640-3f73-480c-82f3-58e402ed4207

# config/env/.env.testing (evaluation)
LANGCHAIN_PROJECT=code-chef-testing
```

### Project Mapping

| Environment | LangSmith Project   | Retention | Purpose           |
| ----------- | ------------------- | --------- | ----------------- |
| Production  | `code-chef`         | 30 days   | Live agent traces |
| Testing     | `code-chef-testing` | 7 days    | E2E test traces   |
| Development | `code-chef-dev`     | 3 days    | Local development |

**Note**: All projects share the same workspace ID. Configure retention in LangSmith UI.

---

## 2. Evaluation Dataset Creation

Create datasets from real DevOps scenarios using RAG collections and Linear issues.

### Dataset Seeding Script

Create `support/tests/e2e/langsmith_datasets.py`:

```python
"""
LangSmith dataset creation for E2E evaluation.
Seeds datasets from RAG collections and Linear issues.
"""
from langsmith import Client
from typing import List, Dict
import httpx

# Initialize LangSmith client
client = Client()

# Seed from RAG issue_tracker collection
def get_scenarios_from_rag() -> List[Dict]:
    """Query RAG for real Linear issues to use as test scenarios."""
    response = httpx.post(
        "http://localhost:8007/query",
        json={
            "query": "feature implementation code review deployment",
            "collection": "issue_tracker",
            "limit": 15
        }
    )
    return response.json().get("results", [])

def create_evaluation_dataset():
    """Create or update the evaluation dataset."""
    dataset = client.create_dataset(
        dataset_name="devops-scenarios-v1",
        description="DevOps task scenarios for agent routing evaluation"
    )

    # Add scenarios (see table below)
    scenarios = get_scenarios_from_rag()
    for scenario in scenarios:
        client.create_example(
            dataset_id=dataset.id,
            inputs={"task": scenario["content"]},
            outputs={"expected_agents": scenario.get("metadata", {}).get("agents", [])}
        )

    return dataset
```

### Scenario Dataset

| #   | Scenario                                             | Expected Agents          | Risk Level |
| --- | ---------------------------------------------------- | ------------------------ | ---------- |
| 1   | Add JWT authentication to Express API                | feature_dev, code_review | medium     |
| 2   | Create GitHub Actions workflow for Docker deployment | cicd                     | high       |
| 3   | Write API documentation for /users endpoint          | documentation            | low        |
| 4   | Review PR for SQL injection vulnerabilities          | code_review              | high       |
| 5   | Add Terraform module for AWS RDS                     | infrastructure           | high       |
| 6   | Implement rate limiting middleware                   | feature_dev, code_review | medium     |
| 7   | Update README with installation steps                | documentation            | low        |
| 8   | Create Kubernetes deployment manifest                | infrastructure           | medium     |
| 9   | Add unit tests for auth module                       | feature_dev              | low        |
| 10  | Configure Prometheus alerting rules                  | infrastructure, cicd     | medium     |

---

## 3. Trace-Generating E2E Tests

Extend existing E2E tests to generate and validate LangSmith traces.

### Existing Test Coverage

The following tests already generate traces when `LANGSMITH_TRACING=true`:

```
support/tests/e2e/
├── test_feature_workflow.py    # Feature dev + HITL approval
├── test_review_workflow.py     # Code review flow
└── test_deploy_workflow.py     # Deployment workflow
```

### Add Trace Validation

Create `support/tests/e2e/test_langsmith_traces.py`:

```python
"""
LangSmith trace validation tests.
Verifies trace structure, agent routing, and token efficiency.
"""
import pytest
from langsmith import Client
from datetime import datetime, timedelta
import os

pytestmark = [pytest.mark.e2e, pytest.mark.trace]

client = Client()
PROJECT_NAME = os.getenv("LANGCHAIN_PROJECT", "code-chef-testing")


class TestLangSmithTraces:
    """Validate LangSmith trace structure and content."""

    @pytest.fixture
    def recent_traces(self):
        """Get traces from the last hour."""
        runs = client.list_runs(
            project_name=PROJECT_NAME,
            start_time=datetime.now() - timedelta(hours=1),
            run_type="chain"
        )
        return list(runs)

    def test_traces_have_agent_metadata(self, recent_traces):
        """Verify traces include agent routing metadata."""
        for trace in recent_traces[:5]:
            assert trace.extra is not None
            # Check for expected metadata fields
            if "metadata" in trace.extra:
                metadata = trace.extra["metadata"]
                assert "agent" in metadata or "workflow_id" in metadata

    def test_token_usage_tracked(self, recent_traces):
        """Verify token usage is captured in traces."""
        for trace in recent_traces[:5]:
            if trace.run_type == "llm":
                assert trace.total_tokens is not None or trace.prompt_tokens is not None

    def test_latency_within_threshold(self, recent_traces):
        """Verify P95 latency < 5 seconds."""
        latencies = [
            (trace.end_time - trace.start_time).total_seconds()
            for trace in recent_traces
            if trace.end_time and trace.start_time
        ]
        if latencies:
            p95 = sorted(latencies)[int(len(latencies) * 0.95)]
            assert p95 < 5.0, f"P95 latency {p95}s exceeds 5s threshold"
```

---

## 4. Custom Evaluator Functions

Implement evaluators for automated quality checks.

### Create Evaluators

Create `support/tests/evaluation/evaluators.py`:

```python
"""
Custom LangSmith evaluators for agent quality metrics.
"""
from langsmith.evaluation import EvaluationResult
from typing import Dict, Any


def agent_routing_accuracy(run, example) -> EvaluationResult:
    """
    Evaluate if the correct agent was routed to.
    Compares actual agent execution to expected agents.
    """
    expected_agents = set(example.outputs.get("expected_agents", []))
    actual_agents = set()

    # Extract agents from trace metadata
    if run.extra and "metadata" in run.extra:
        actual_agents.add(run.extra["metadata"].get("agent", ""))

    # Check child runs for agent nodes
    for child in run.child_runs or []:
        if child.name and "_node" in child.name:
            agent_name = child.name.replace("_node", "")
            actual_agents.add(agent_name)

    overlap = expected_agents & actual_agents
    score = len(overlap) / len(expected_agents) if expected_agents else 1.0

    return EvaluationResult(
        key="agent_routing_accuracy",
        score=score,
        comment=f"Expected: {expected_agents}, Actual: {actual_agents}"
    )


def token_efficiency(run, example) -> EvaluationResult:
    """
    Evaluate token usage efficiency.
    Target: < 2000 tokens per orchestrator call.
    """
    total_tokens = run.total_tokens or 0

    # Threshold based on agent type
    threshold = 4000 if "code_review" in str(run.name) else 2000
    score = min(1.0, threshold / max(total_tokens, 1))

    return EvaluationResult(
        key="token_efficiency",
        score=score,
        comment=f"Used {total_tokens} tokens (threshold: {threshold})"
    )


def latency_threshold(run, example) -> EvaluationResult:
    """
    Evaluate response latency.
    Target: P95 < 5 seconds.
    """
    if not run.end_time or not run.start_time:
        return EvaluationResult(key="latency", score=0.0, comment="Missing timestamps")

    latency = (run.end_time - run.start_time).total_seconds()
    threshold = 5.0
    score = min(1.0, threshold / max(latency, 0.1))

    return EvaluationResult(
        key="latency_threshold",
        score=score,
        comment=f"Latency: {latency:.2f}s (threshold: {threshold}s)"
    )


def workflow_completeness(run, example) -> EvaluationResult:
    """
    Evaluate if workflow completed all expected steps.
    """
    expected_steps = example.outputs.get("expected_steps", [])
    completed_steps = []

    for child in run.child_runs or []:
        if child.status == "success":
            completed_steps.append(child.name)

    if not expected_steps:
        return EvaluationResult(key="workflow_completeness", score=1.0)

    completion_rate = len(set(completed_steps) & set(expected_steps)) / len(expected_steps)

    return EvaluationResult(
        key="workflow_completeness",
        score=completion_rate,
        comment=f"Completed {len(completed_steps)}/{len(expected_steps)} steps"
    )
```

---

## 5. GitHub Actions Evaluation Workflow

Automate evaluation runs with CI/CD integration.

### Create Workflow

Create `.github/workflows/e2e-langsmith-eval.yml`:

```yaml
name: E2E LangSmith Evaluation

on:
  schedule:
    - cron: "0 6 * * *" # Daily at 6 AM UTC
  workflow_dispatch:
    inputs:
      dataset:
        description: "Dataset name to evaluate"
        default: "devops-scenarios-v1"
  push:
    branches: [main]
    paths:
      - "agent_orchestrator/**"
      - "shared/lib/**"

env:
  LANGCHAIN_PROJECT: code-chef-testing
  LANGSMITH_TRACING: true
  LANGCHAIN_TRACING_V2: true

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -r support/tests/requirements.txt
          pip install langsmith

      - name: Run E2E tests (generates traces)
        env:
          LANGCHAIN_API_KEY: ${{ secrets.LANGCHAIN_API_KEY }}
          LANGSMITH_API_KEY: ${{ secrets.LANGSMITH_API_KEY }}
          LANGSMITH_WORKSPACE_ID: ${{ secrets.LANGSMITH_WORKSPACE_ID }}
        run: |
          pytest support/tests/e2e/ -v -m "trace" --tb=short

      - name: Run evaluation
        env:
          LANGCHAIN_API_KEY: ${{ secrets.LANGCHAIN_API_KEY }}
        run: |
          python support/tests/evaluation/run_evaluation.py \
            --dataset ${{ github.event.inputs.dataset || 'devops-scenarios-v1' }} \
            --output results.json

      - name: Post results to Linear
        if: failure()
        env:
          LINEAR_API_KEY: ${{ secrets.LINEAR_API_KEY }}
        run: |
          python support/scripts/linear/create-eval-issue.py \
            --results results.json \
            --workflow-url ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
```

---

## 6. VS Code Integration

Configure VS Code workspace for natural trace generation during development.

### Workspace Settings

Add to `.vscode/settings.json`:

```json
{
  "python.envFile": "${workspaceFolder}/config/env/.env",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["support/tests", "-v"],
  "terminal.integrated.env.windows": {
    "LANGCHAIN_PROJECT": "code-chef-dev",
    "LANGSMITH_TRACING": "true"
  },
  "terminal.integrated.env.linux": {
    "LANGCHAIN_PROJECT": "code-chef-dev",
    "LANGSMITH_TRACING": "true"
  }
}
```

### Development Workflow

1. **Local development**: Traces go to `code-chef-dev` project
2. **Run E2E tests**: Traces go to `code-chef-testing` project
3. **Production**: Traces go to `code-chef` project

---

## Implementation Checklist

| Step | File                                                | Status                                                 |
| ---- | --------------------------------------------------- | ------------------------------------------------------ |
| 1    | Update `config/env/.env.template` with project vars | ⬜                                                     |
| 2    | Create `support/tests/e2e/langsmith_datasets.py`    | ⬜                                                     |
| 3    | Create `support/tests/e2e/test_langsmith_traces.py` | ⬜                                                     |
| 4    | Create `support/tests/evaluation/evaluators.py`     | ⬜                                                     |
| 5    | Create `support/tests/evaluation/run_evaluation.py` | ⬜                                                     |
| 6    | Create `.github/workflows/e2e-langsmith-eval.yml`   | ⬜                                                     |
| 7    | Update `.vscode/settings.json`                      | ⬜                                                     |
| 8    | Create Linear issue for tracking                    | ✅ [DEV-195](https://linear.app/dev-ops/issue/DEV-195) |

---

## References

- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [LangSmith Python SDK](https://python.langchain.com/docs/langsmith/)
- [LangSmith Evaluation](https://docs.smith.langchain.com/evaluation)
- [Existing LANGSMITH_TRACING.md](LANGSMITH_TRACING.md)
- [OBSERVABILITY_GUIDE.md](../OBSERVABILITY_GUIDE.md)
- [RAG Configuration](../../../config/rag/indexing.yaml)
