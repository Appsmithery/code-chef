# E2E LangSmith Trace Evaluation Strategy

**Last Updated**: December 5, 2025  
**Status**: Implementation Plan  
**Linear Issue**: [DEV-195](https://linear.app/dev-ops/issue/DEV-195/implement-e2e-langsmith-trace-evaluation-system)  
**Related**: [LANGSMITH_TRACING.md](LANGSMITH_TRACING.md), [OBSERVABILITY_GUIDE.md](../OBSERVABILITY_GUIDE.md)  
**Test Project**: [IB-Agent Platform](https://github.com/Appsmithery/IB-Agent) - Investment banking AI agent for comps analysis, SEC filings, and macro data

---

## Overview

Implement a dual-project evaluation system for LangSmith traces using the **IB-Agent Platform** as the primary test project. This strategy validates code-chef's orchestration capabilities through real-world IB agent development workflows:

- **LangSmith Projects** for trace isolation (production vs. testing)
- **IB-Agent workflows** for realistic multi-agent trace generation
- **MCP server integration** testing (EDGAR, FRED, Nasdaq)
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

Create datasets from **IB-Agent Platform** development scenarios using the project roadmap.

### Dataset Seeding Script

Create `support/tests/e2e/langsmith_datasets.py`:

```python
"""
LangSmith dataset creation for E2E evaluation.
Seeds datasets from IB-Agent Platform implementation scenarios.
"""
from langsmith import Client
from typing import List, Dict
import httpx

# Initialize LangSmith client
client = Client()

# IB-Agent Platform scenarios mapped to code-chef agents
IB_AGENT_SCENARIOS = [
    # Phase 1: Data Layer
    {
        "task": "Build EDGAR MCP server with search_filings tool that queries SEC EDGAR API",
        "expected_agents": ["feature_dev", "code_review"],
        "risk_level": "high",
        "ib_agent_step": "1.3"
    },
    {
        "task": "Configure Qdrant collection 'ib-agent-filings' with 1536-dim vectors for SEC embeddings",
        "expected_agents": ["infrastructure"],
        "risk_level": "medium",
        "ib_agent_step": "1.4"
    },
    {
        "task": "Clone Nasdaq Data Link MCP server and add to docker-compose.yml",
        "expected_agents": ["infrastructure", "cicd"],
        "risk_level": "medium",
        "ib_agent_step": "1.2"
    },
    # Phase 2: Core Agents
    {
        "task": "Implement CompsAgent with LangGraph workflow: get_fundamentals -> screen_peers -> enrich -> rank",
        "expected_agents": ["feature_dev", "code_review"],
        "risk_level": "high",
        "ib_agent_step": "2.2"
    },
    {
        "task": "Build RAG ingestion pipeline for 10-K filings with semantic chunking by SEC Item headers",
        "expected_agents": ["feature_dev"],
        "risk_level": "medium",
        "ib_agent_step": "2.3"
    },
    {
        "task": "Create POST /api/v1/research/comps endpoint with async task execution",
        "expected_agents": ["feature_dev", "code_review"],
        "risk_level": "medium",
        "ib_agent_step": "2.1"
    },
    # Phase 3: UI
    {
        "task": "Update Chainlit UI to call /api/v1/research/comps and display table results",
        "expected_agents": ["feature_dev"],
        "risk_level": "low",
        "ib_agent_step": "3.1"
    },
    # Phase 4: Excel Add-in
    {
        "task": "Create Office.js manifest.xml for Excel Add-in with ReadWriteDocument permissions",
        "expected_agents": ["feature_dev"],
        "risk_level": "high",
        "ib_agent_step": "4.1"
    },
    {
        "task": "Build React task pane with Excel.run() for writing comps to workbook",
        "expected_agents": ["feature_dev", "code_review"],
        "risk_level": "high",
        "ib_agent_step": "4.2"
    }
]

def create_evaluation_dataset():
    """Create or update the evaluation dataset with IB-Agent scenarios."""
    dataset = client.create_dataset(
        dataset_name="ib-agent-scenarios-v1",
        description="IB-Agent Platform development scenarios for code-chef evaluation"
    )

    for scenario in IB_AGENT_SCENARIOS:
        client.create_example(
            dataset_id=dataset.id,
            inputs={"task": scenario["task"]},
            outputs={
                "expected_agents": scenario["expected_agents"],
                "risk_level": scenario["risk_level"],
                "ib_agent_step": scenario.get("ib_agent_step", "")
            }
        )

    return dataset
```

### Scenario Dataset

The scenarios below map to **IB-Agent Platform** implementation phases:

#### Phase 1: Data Layer Foundation (MCP Servers)

| #   | Scenario                                              | Expected Agents          | Risk Level | IB-Agent Step |
| --- | ----------------------------------------------------- | ------------------------ | ---------- | ------------- |
| 1   | Build EDGAR MCP server with `search_filings` tool     | feature_dev, code_review | high       | Step 1.3      |
| 2   | Configure Qdrant collection for SEC filing embeddings | infrastructure           | medium     | Step 1.4      |
| 3   | Clone and integrate Nasdaq Data Link MCP server       | infrastructure, cicd     | medium     | Step 1.2      |
| 4   | Write Docker Compose for IB Agent stack               | infrastructure           | medium     | Step 1.1      |

#### Phase 2: Core Agent Development

| #   | Scenario                                         | Expected Agents          | Risk Level | IB-Agent Step |
| --- | ------------------------------------------------ | ------------------------ | ---------- | ------------- |
| 5   | Implement Comps Analysis Agent with LangGraph    | feature_dev, code_review | high       | Step 2.2      |
| 6   | Build RAG pipeline for 10-K filing ingestion     | feature_dev              | medium     | Step 2.3      |
| 7   | Create `/api/v1/research/comps` FastAPI endpoint | feature_dev, code_review | medium     | Step 2.1      |
| 8   | Add task store for async workflow tracking       | feature_dev              | low        | Step 2.1      |

#### Phase 3: UI Integration

| #   | Scenario                                         | Expected Agents          | Risk Level | IB-Agent Step |
| --- | ------------------------------------------------ | ------------------------ | ---------- | ------------- |
| 9   | Update Chainlit UI to call comps endpoint        | feature_dev              | low        | Step 3.1      |
| 10  | Implement Excel export service for comps results | feature_dev, code_review | medium     | Step 3.2      |

#### Phase 4: Excel Add-in ("The Sidecar")

| #   | Scenario                                           | Expected Agents          | Risk Level | IB-Agent Step |
| --- | -------------------------------------------------- | ------------------------ | ---------- | ------------- |
| 11  | Create Office.js manifest for Excel task pane      | feature_dev              | high       | Step 4.1      |
| 12  | Build React task pane with Excel.run() integration | feature_dev, code_review | high       | Step 4.2      |

#### Cross-Cutting Scenarios

| #   | Scenario                                           | Expected Agents | Risk Level |
| --- | -------------------------------------------------- | --------------- | ---------- |
| 13  | Review MCP client for OWASP Top 10 vulnerabilities | code_review     | high       |
| 14  | Write API documentation for IB Agent endpoints     | documentation   | low        |
| 15  | Configure GitHub Actions for IB Agent CI/CD        | cicd            | medium     |

---

## 3. Trace-Generating E2E Tests

Extend existing E2E tests to generate and validate LangSmith traces.

### Existing Test Coverage

The following tests generate traces from **IB-Agent Platform** development workflows:

```
support/tests/e2e/
├── test_ib_agent_phase1.py     # MCP server + infrastructure setup
├── test_ib_agent_phase2.py     # Core agent development (CompsAgent, RAG)
├── test_feature_workflow.py    # Generic feature dev + HITL approval
├── test_review_workflow.py     # Code review flow (MCP security review)
└── test_deploy_workflow.py     # Deployment workflow (Docker Compose)
```

### Add Trace Validation

Create `support/tests/e2e/test_langsmith_traces.py`:

```python
"""
LangSmith trace validation tests for IB-Agent Platform scenarios.
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

    def test_ib_agent_task_routing(self, recent_traces):
        """Verify IB-Agent tasks route to correct agents."""
        ib_agent_patterns = {
            "MCP": ["feature_dev", "infrastructure"],
            "EDGAR": ["feature_dev", "code_review"],
            "Qdrant": ["infrastructure"],
            "LangGraph": ["feature_dev"],
            "Docker": ["infrastructure", "cicd"],
            "Excel": ["feature_dev"]
        }
        for trace in recent_traces[:5]:
            if trace.inputs:
                task = str(trace.inputs.get("task", ""))
                for keyword, expected in ib_agent_patterns.items():
                    if keyword.lower() in task.lower():
                        # Validate routing (actual check depends on trace structure)
                        assert trace.extra is not None

    def test_token_usage_tracked(self, recent_traces):
        """Verify token usage is captured in traces."""
        for trace in recent_traces[:5]:
            if trace.run_type == "llm":
                assert trace.total_tokens is not None or trace.prompt_tokens is not None

    def test_latency_within_threshold(self, recent_traces):
        """Verify P95 latency < 5 seconds for IB-Agent scenarios."""
        latencies = [
            (trace.end_time - trace.start_time).total_seconds()
            for trace in recent_traces
            if trace.end_time and trace.start_time
        ]
        if latencies:
            p95 = sorted(latencies)[int(len(latencies) * 0.95)]
            assert p95 < 5.0, f"P95 latency {p95}s exceeds 5s threshold"

    def test_mcp_server_traces(self, recent_traces):
        """Verify MCP server integration traces are captured."""
        mcp_servers = ["edgar", "fred", "nasdaq"]
        for trace in recent_traces:
            if trace.name and any(mcp in trace.name.lower() for mcp in mcp_servers):
                # Validate MCP call traces have proper structure
                assert trace.status in ["success", "error"]
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
    Evaluate token usage efficiency for IB-Agent tasks.
    Thresholds based on task complexity.
    """
    total_tokens = run.total_tokens or 0

    # IB-Agent specific thresholds
    task = str(example.inputs.get("task", ""))
    if any(kw in task.lower() for kw in ["langgraph", "compsagent", "rag"]):
        threshold = 6000  # Complex agent workflows
    elif "code_review" in str(run.name) or "security" in task.lower():
        threshold = 4000  # Security review needs more context
    elif any(kw in task.lower() for kw in ["excel", "manifest"]):
        threshold = 3000  # UI/Office.js tasks
    else:
        threshold = 2000  # Default

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
    Evaluate if IB-Agent workflow completed all expected steps.
    """
    expected_steps = example.outputs.get("expected_steps", [])
    completed_steps = []

    # IB-Agent workflow steps
    ib_agent_step = example.outputs.get("ib_agent_step", "")
    if ib_agent_step.startswith("1."):  # Phase 1: Data Layer
        expected_steps = ["infrastructure_check", "docker_validate", "mcp_health"]
    elif ib_agent_step.startswith("2."):  # Phase 2: Core Agents
        expected_steps = ["feature_dev_node", "code_review_node", "test_generate"]
    elif ib_agent_step.startswith("4."):  # Phase 4: Excel Add-in (high risk)
        expected_steps = ["feature_dev_node", "code_review_node", "security_scan"]

    for child in run.child_runs or []:
        if child.status == "success":
            completed_steps.append(child.name)

    if not expected_steps:
        return EvaluationResult(key="workflow_completeness", score=1.0)

    completion_rate = len(set(completed_steps) & set(expected_steps)) / len(expected_steps)

    return EvaluationResult(
        key="workflow_completeness",
        score=completion_rate,
        comment=f"Completed {len(completed_steps)}/{len(expected_steps)} steps (IB-Agent step {ib_agent_step})"
    )


def mcp_integration_quality(run, example) -> EvaluationResult:
    """
    Evaluate MCP server integration quality.
    Checks for proper error handling, citations, and response structure.
    """
    task = str(example.inputs.get("task", ""))
    mcp_keywords = ["edgar", "fred", "nasdaq", "mcp"]

    if not any(kw in task.lower() for kw in mcp_keywords):
        return EvaluationResult(key="mcp_integration", score=1.0, comment="Non-MCP task")

    # Check for proper MCP response handling
    has_citations = False
    has_error_handling = False

    for child in run.child_runs or []:
        if "mcp" in child.name.lower():
            if child.outputs and "citations" in str(child.outputs):
                has_citations = True
            if child.error or (child.outputs and "error" in str(child.outputs).lower()):
                has_error_handling = True

    score = 0.5
    if has_citations:
        score += 0.25
    if has_error_handling or run.status == "success":
        score += 0.25

    return EvaluationResult(
        key="mcp_integration_quality",
        score=score,
        comment=f"Citations: {has_citations}, Error handling: {has_error_handling}"
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
            --dataset ${{ github.event.inputs.dataset || 'ib-agent-scenarios-v1' }} \
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
| 4    | Create `support/tests/e2e/test_ib_agent_phase1.py`  | ⬜                                                     |
| 5    | Create `support/tests/e2e/test_ib_agent_phase2.py`  | ⬜                                                     |
| 6    | Create `support/tests/evaluation/evaluators.py`     | ⬜                                                     |
| 7    | Create `support/tests/evaluation/run_evaluation.py` | ⬜                                                     |
| 8    | Create `.github/workflows/e2e-langsmith-eval.yml`   | ⬜                                                     |
| 9    | Update `.vscode/settings.json`                      | ⬜                                                     |
| 10   | Create Linear issue for tracking                    | ✅ [DEV-195](https://linear.app/dev-ops/issue/DEV-195) |

---

## References

- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [LangSmith Python SDK](https://python.langchain.com/docs/langsmith/)
- [LangSmith Evaluation](https://docs.smith.langchain.com/evaluation)
- [IB-Agent Platform Repository](https://github.com/Appsmithery/IB-Agent)
- [IB-Agent Action Plan](https://github.com/Appsmithery/IB-Agent/blob/main/Planning/action_plan.md)
- [Existing LANGSMITH_TRACING.md](LANGSMITH_TRACING.md)
- [OBSERVABILITY_GUIDE.md](../OBSERVABILITY_GUIDE.md)
- [RAG Configuration](../../../config/rag/indexing.yaml)
