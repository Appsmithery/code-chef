### 1.2 Configure Online Evaluators in LangSmith

**Navigate to**: LangSmith → `code-chef-production` project → **Evaluators** tab → **New Evaluator**

#### Evaluator 1: MCP Tool Awareness (Reference-Free)

**Type**: LLM-as-Judge  
**Model**: `openrouter/openai/o3-mini` (fast, cost-effective)  
**Trigger**: Run-level (evaluate each agent response)  
**Sampling**: 20% during UAT (reduce cost)

**Prompt**:

```python
# Create in LangSmith UI
EVALUATOR_NAME = "mcp-tool-awareness"
PROMPT = """
You are evaluating an AI coding agent's response for MCP (Model Context Protocol) tool awareness.

Agent Response: {output}
User Request: {input}

Scoring Criteria (0.0 - 1.0):
- 1.0: Agent correctly identifies and uses MCP tools when appropriate
- 0.7: Agent mentions MCP but doesn't use tools optimally
- 0.4: Agent shows vague awareness of tools
- 0.0: Agent ignores available MCP tools

Output JSON: {{"score": <float>, "reasoning": "<string>"}}
"""
```

#### Evaluator 2: Output Format Validation (Custom Code)

**Type**: Custom Code Evaluator  
**Language**: Python  
**Trigger**: Run-level

**Code**:

```python
import json

def evaluate(run, example=None):
    """Validate agent output matches expected format."""
    output = run.outputs.get("output", "")

    # Check for required structure
    issues = []

    # Must not include internal thoughts
    if "@@THINK@@" in output or "@@SCRATCHPAD@@" in output:
        issues.append("Exposed internal thinking")

    # Should have markdown formatting for file refs
    if "file:" in output.lower() and "[" not in output:
        issues.append("Missing markdown file links")

    # Check for incomplete JSON responses
    if "{" in output and "}" in output:
        try:
            json.loads(output)
        except:
            issues.append("Malformed JSON in response")

    score = 1.0 if not issues else max(0.0, 1.0 - (len(issues) * 0.3))

    return {
        "key": "format_validation",
        "score": score,
        "comment": ", ".join(issues) if issues else "All checks passed"
    }
```

#### Evaluator 3: Agent Routing Quality (Thread-Level)

**Type**: Custom Code Evaluator  
**Language**: Python  
**Trigger**: Thread-level (when conversation completes)  
**Idle Time**: 5 minutes (time to wait after last message before evaluation)

**Code**:

```python
def evaluate(thread_run, example=None):
    """Evaluate multi-turn conversation quality."""
    runs = thread_run.child_runs

    # Check for agent handoffs
    agents_used = set()
    for run in runs:
        metadata = run.extra.get("metadata", {})
        if "module" in metadata:
            agents_used.add(metadata["module"])

    # Check for unnecessary supervisor calls
    supervisor_calls = sum(1 for r in runs if r.extra.get("metadata", {}).get("module") == "supervisor")

    # Score based on routing efficiency
    if len(agents_used) == 1 and supervisor_calls == 0:
        score = 1.0  # Direct routing, no unnecessary hops
    elif len(agents_used) <= 3 and supervisor_calls <= 2:
        score = 0.8  # Efficient multi-agent coordination
    elif supervisor_calls > 4:
        score = 0.4  # Too many supervisor redirects
    else:
        score = 0.6  # Mediocre routing

    return {
        "key": "routing_efficiency",
        "score": score,
        "comment": f"Used {len(agents_used)} agents, {supervisor_calls} supervisor calls"
    }
```

#### Evaluator 4: Trajectory Match (AgentEvals - for regression testing)

Create `support/scripts/evaluation/setup_trajectory_evaluators.py`:

```python
from langsmith import Client
from agentevals import create_trajectory_match_evaluator
from langsmith.evaluation import evaluate

client = Client()

# Define expected tool call sequences for regression tests
EXPECTED_TRAJECTORIES = {
    "feature_implementation": [
        ("semantic_search", {"query": "*"}),  # Search for similar code
        ("read_file", {"filePath": "*"}),     # Read existing files
        ("replace_string_in_file", {"filePath": "*"})  # Implement change
    ],
    "bug_investigation": [
        ("grep_search", {"query": "*", "isRegexp": False}),  # Search for error
        ("get_errors", {}),  # Check linter errors
        ("read_file", {"filePath": "*"})  # Read problematic file
    ]
}

# Create evaluators
for scenario, trajectory in EXPECTED_TRAJECTORIES.items():
    evaluator = create_trajectory_match_evaluator(
        expected_trajectory=trajectory,
        mode="subset",  # Allow extra tools, but must include expected
        name=f"trajectory_{scenario}"
    )

    # Apply to existing dataset
    results = evaluate(
        lambda inputs: client.get_run(inputs["run_id"]),
        data=f"error-cases-regression-suite",
        evaluators=[evaluator],
        experiment_prefix=f"regression_{scenario}"
    )
    print(f"Evaluated {scenario}: {results}")
```

### 1.3 Activate Annotation Queue

**Create Queue via LangSmith SDK**:

Create `support/scripts/evaluation/create_annotation_queue.py`:

```python
from langsmith import Client
import os

client = Client(api_key=os.getenv("LANGCHAIN_API_KEY"))

# Create UAT review queue
queue_info = client.create_annotation_queue(
    name="uat-review-queue",
    description="UAT testing - review traces with low confidence, errors, or edge cases",
    default_dataset="code-chef-gold-standard-v1"  # Auto-add to this dataset
)

print(f"Created annotation queue: {queue_info.id}")
print(f"URL: https://smith.langchain.com/o/<org-id>/datasets/queues/{queue_info.id}")

# Add rules to auto-populate queue
# Note: Rules API may require manual configuration in LangSmith UI
print("\nManual setup required in LangSmith UI:")
print("1. Go to Annotation Queues → uat-review-queue → Rules")
print("2. Add filters:")
print("   - metadata.intent_confidence < 0.75")
print("   - errors IS NOT NULL")
print("   - latency_ms > 5000")
print("3. Set sampling rate: 20%")
```

---

## Phase 2: Automation Workflows (Week 2)

### 2.1 Activate Auto-Annotation for Uncertainty Sampling

**Update** auto_annotate_traces.py:

Add logic to:

1. Query recent traces with low confidence
2. Add to annotation queue automatically
3. Flag for human review

```python
# Add to existing script
from langsmith import Client

def auto_populate_annotation_queue():
    """Add uncertain traces to review queue."""
    client = Client()

    # Query traces from last 24 hours
    traces = client.list_runs(
        project_name="code-chef-production",
        filter='gt(created_at, "2025-01-05T00:00:00Z") and lt(metadata.intent_confidence, 0.75)',
        limit=50
    )

    # Add to annotation queue
    queue = client.get_annotation_queue("uat-review-queue")
    for trace in traces:
        queue.add_run(trace.id)

    print(f"Added {len(list(traces))} traces to uat-review-queue")

if __name__ == "__main__":
    auto_populate_annotation_queue()
```

**Schedule**: Run daily via GitHub Actions or cron

### 2.2 Sync Annotations to Datasets

**Update** sync_dataset_from_annotations.py:

Ensure it syncs from `uat-review-queue` to `code-chef-gold-standard-v1` dataset:

```python
from langsmith import Client

def sync_reviewed_traces():
    """Move reviewed traces from queue to dataset."""
    client = Client()

    # Get completed annotations from queue
    queue = client.get_annotation_queue("uat-review-queue")
    reviewed_runs = queue.get_runs(status="completed")

    # Add to gold standard dataset
    dataset = client.read_dataset(dataset_name="code-chef-gold-standard-v1")

    for run in reviewed_runs:
        # Get human annotation
        annotation = queue.get_run_annotation(run.id)

        # Create dataset example with reference output
        client.create_example(
            dataset_id=dataset.id,
            inputs=run.inputs,
            outputs=run.outputs,
            metadata={
                "human_score": annotation.score,
                "reviewer_notes": annotation.comment,
                "original_run_id": run.id
            }
        )

    print(f"Synced {len(list(reviewed_runs))} examples to dataset")

if __name__ == "__main__":
    sync_reviewed_traces()
```

### 2.3 Baseline Comparison Before Deployments

**Update CI/CD workflow** (`.github/workflows/pre-deploy-evaluation.yml`):

```yaml
name: Pre-Deployment Evaluation

on:
  pull_request:
    types: [labeled]
    # Trigger when PR labeled "ready-to-deploy"

jobs:
  evaluate:
    runs-on: ubuntu-latest
    if: contains(github.event.pull_request.labels.*.name, 'ready-to-deploy')

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run baseline evaluation
        env:
          LANGCHAIN_API_KEY: ${{ secrets.LANGCHAIN_API_KEY }}
          TRACE_ENVIRONMENT: evaluation
        run: |
          python support/scripts/evaluation/baseline_runner.py \
            --mode code-chef \
            --tasks support/scripts/evaluation/sample_tasks.json \
            --dataset ib-agent-scenarios-v1 \
            --output evaluation-results.json

      - name: Check for regressions
        run: |
          python support/scripts/evaluation/detect_regression.py \
            --results evaluation-results.json \
            --threshold 0.05  # Fail if >5% regression

      - name: Comment results on PR
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const results = JSON.parse(fs.readFileSync('evaluation-results.json'));

            const comment = `## Evaluation Results\n\n` +
              `**Accuracy**: ${results.accuracy.toFixed(2)}\n` +
              `**MCP Awareness**: ${results.mcp_awareness.toFixed(2)}\n` +
              `**Routing Efficiency**: ${results.routing_efficiency.toFixed(2)}\n\n` +
              `${results.recommendation === 'deploy' ? '✅ Safe to deploy' : '⚠️ Manual review required'}`;

            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
```

---

## Phase 3: UAT-Specific Monitoring (Week 3)

### 3.1 Create UAT Dashboard

**LangSmith Monitoring Dashboard**:

Navigate to **code-chef-production** → **Monitoring** → Create charts:

1. **Intent Classification Confidence**

   - Metric: `metadata.intent_confidence`
   - Aggregation: P50, P95
   - Alert: < 0.70

2. **Agent Routing Distribution**

   - Group by: `metadata.module`
   - Chart type: Pie chart
   - Track: Which agents are most/least used

3. **Error Rate by Agent**

   - Filter: `error IS NOT NULL`
   - Group by: `metadata.module`
   - Alert: > 5% error rate

4. **Online Evaluator Scores**
   - Metrics: `feedback.mcp-tool-awareness.score`, `feedback.format_validation.score`
   - Aggregation: Average
   - Alert: < 0.75

### 3.2 Daily Review Workflow

**Daily UAT Checklist**:

```bash
#!/bin/bash
# support/scripts/evaluation/daily_uat_review.sh

# 1. Check online evaluator scores
echo "=== Online Evaluator Scores (Last 24h) ==="
python -c "
from langsmith import Client
import datetime

client = Client()
end = datetime.datetime.now()
start = end - datetime.timedelta(days=1)

runs = client.list_runs(
    project_name='code-chef-production',
    start_time=start,
    end_time=end
)

scores = {'mcp-tool-awareness': [], 'format_validation': []}
for run in runs:
    feedback = run.feedback_stats
    for key in scores:
        if key in feedback:
            scores[key].append(feedback[key]['avg'])

for key, vals in scores.items():
    if vals:
        print(f'{key}: {sum(vals)/len(vals):.2f}')
"

# 2. Check annotation queue status
echo -e "\n=== Annotation Queue Status ==="
python support/scripts/evaluation/check_queue_status.py

# 3. Review regressions
echo -e "\n=== Regression Checks ==="
python support/scripts/evaluation/detect_regression.py \
  --agent feature_dev \
  --metric accuracy \
  --limit 7  # Last 7 days

# 4. Export new training data
echo -e "\n=== Training Data Exports ==="
python support/scripts/evaluation/export_training_dataset.py \
  --dataset code-chef-gold-standard-v1 \
  --min-score 0.8 \
  --output training-$(date +%Y%m%d).jsonl
```

**Run daily** during UAT: `./support/scripts/evaluation/daily_uat_review.sh`

### 3.3 Weekly Model Evaluation

**Weekly Workflow**:

1. **Sync Datasets** (every Sunday):

   ```bash
   python support/scripts/evaluation/sync_dataset_from_annotations.py
   ```

2. **Check Dataset Diversity**:

   ```bash
   python support/scripts/evaluation/check_dataset_diversity.py \
     --dataset code-chef-gold-standard-v1
   ```

3. **Run Baseline Comparison**:

   ```bash
   python support/scripts/evaluation/baseline_runner.py \
     --mode baseline \
     --dataset code-chef-gold-standard-v1 \
     --output baseline-week$(date +%U).json

   python support/scripts/evaluation/baseline_runner.py \
     --mode code-chef \
     --dataset code-chef-gold-standard-v1 \
     --output codechef-week$(date +%U).json
   ```

4. **Decide on Model Training**:
   - If code-chef >> baseline: Current model working well
   - If baseline ≈ code-chef: Consider fine-tuning
   - If baseline > code-chef: Investigate model degradation

---

## Phase 4: Integration with Existing Evaluators (Ongoing)

### 4.1 Integrate AgentEvals Graph Trajectory

For LangGraph agent evaluation (supervisor routing quality):

Create `support/tests/evaluation/test_graph_trajectory.py`:

```python
from agentevals import (
    extract_langgraph_trajectory_from_thread,
    create_graph_trajectory_llm_as_judge
)
from langsmith import Client

def test_supervisor_routing_quality():
    """Evaluate supervisor agent routing decisions."""
    client = Client()

    # Get recent threads from supervisor
    threads = client.list_runs(
        project_name="code-chef-production",
        filter='eq(metadata.module, "supervisor")',
        limit=20
    )

    # Extract graph trajectories
    for thread in threads:
        trajectory = extract_langgraph_trajectory_from_thread(thread)

        # Evaluate with LLM-as-judge
        evaluator = create_graph_trajectory_llm_as_judge(
            graph_schema={
                "nodes": ["supervisor", "feature_dev", "code_review", "infrastructure"],
                "edges": [
                    ("supervisor", "feature_dev"),
                    ("supervisor", "code_review"),
                    ("supervisor", "infrastructure"),
                    ("feature_dev", "END"),
                    ("code_review", "END"),
                    ("infrastructure", "END")
                ]
            },
            criteria="Agent routing should be efficient (no unnecessary hops) and correct (task matched to appropriate specialist agent)"
        )

        result = evaluator(thread)
        print(f"Thread {thread.id}: {result['score']:.2f} - {result['reasoning']}")
```

### 4.2 Property-Based Evaluation Tests

Expand test_property_based.py with more properties:

```python
from hypothesis import given, strategies as st
import pytest

@given(
    user_input=st.text(min_size=10, max_size=500),
    agent=st.sampled_from(["feature_dev", "code_review", "infrastructure"])
)
def test_agent_always_returns_valid_output(user_input, agent):
    """Property: All agent responses must be valid JSON or markdown."""
    from agent_orchestrator.graph import run_agent

    response = run_agent(agent, user_input)

    # Must not expose internal state
    assert "@@THINK@@" not in response
    assert "@@SCRATCHPAD@@" not in response

    # Must have structured output
    assert len(response) > 0
    assert response.strip() != ""

@given(
    intent=st.sampled_from([
        "implement feature",
        "review code",
        "deploy infrastructure",
        "write documentation"
    ])
)
def test_intent_classification_is_deterministic(intent):
    """Property: Same input should always route to same agent."""
    from agent_orchestrator.workflows.workflow_router import route_task

    # Run classification multiple times
    results = [route_task(intent) for _ in range(3)]

    # Should be consistent
    assert len(set([r.workflow_id for r in results])) == 1
```

---

## Cost Management During UAT

### Expected Costs

**Tracing** (Extended Retention):

- Baseline: ~$5/month for normal traces
- With online evaluators: ~$15/month (3x higher due to extended retention)

**Online Evaluation**:

- 20% sampling × 1000 traces/day × $0.001/evaluation = $6/day = $180/month
- Reduce sampling to 10% if needed: $90/month

**LLM-as-Judge**:

- o3-mini via OpenRouter: $0.0001/token
- Avg 500 tokens/evaluation × 200 evals/day = $10/day = $300/month

**Total UAT Cost**: ~$500/month (acceptable for quality assurance)

### Cost Optimization

1. **Sampling**: Start at 20%, reduce to 10% after Week 1
2. **Idle Time**: Set thread evaluators to 10 minutes (reduce unnecessary evaluations)
3. **Model Selection**: Use `o3-mini` instead of `gpt-4` for evaluators (10x cheaper)
4. **Conditional Evaluation**: Only evaluate runs with `metadata.environment == "production"`

---

## Success Metrics

### Week 1 Goals

- [ ] Online evaluators configured and running
- [ ] Annotation queue created with 20+ traces
- [ ] AgentEvals library installed and tested
- [ ] Daily review workflow established

### Week 2 Goals

- [ ] 50+ traces annotated in queue
- [ ] Gold standard dataset has 30+ examples
- [ ] Baseline comparison shows <5% regression
- [ ] Automated sync working (queue → dataset)

### Week 3 Goals

- [ ] Online evaluator scores > 0.80 average
- [ ] Error rate < 3%
- [ ] Intent classification confidence > 0.75 P95
- [ ] Trajectory evaluators passing on regression tests

### End of UAT

- [ ] 100+ annotated traces in gold standard dataset
- [ ] Regression test suite covers all critical bugs
- [ ] Model training decision made (based on baseline comparison)
- [ ] Documentation updated with evaluation procedures

---

## Quick Reference Commands

```bash
# Check online evaluator status
curl "https://api.smith.langchain.com/projects/code-chef-production/stats" \
  -H "x-api-key: $LANGCHAIN_API_KEY" | jq '.feedback_stats'

# Add trace to annotation queue manually
python -c "
from langsmith import Client
client = Client()
client.add_run_to_annotation_queue('uat-review-queue', '<run-id>')
"

# Export training data
python support/scripts/evaluation/export_training_dataset.py \
  --dataset code-chef-gold-standard-v1 \
  --output training-$(date +%Y%m%d).jsonl

# Run baseline evaluation
python support/scripts/evaluation/baseline_runner.py \
  --mode baseline \
  --dataset ib-agent-scenarios-v1

# Check for regressions
python support/scripts/evaluation/detect_regression.py \
  --agent feature_dev \
  --metric accuracy \
  --threshold 0.05

# Sync annotations to dataset
python support/scripts/evaluation/sync_dataset_from_annotations.py
```

---

## Next Steps

1. **Immediate** (Today):

   - Install `agentevals` and `openevals`
   - Create annotation queue `uat-review-queue`
   - Configure first online evaluator (MCP tool awareness)

2. **This Week**:

   - Set up all 4 online evaluators
   - Add auto-annotation script to cron/GitHub Actions
   - Start daily review workflow

3. **Next Week**:

   - Integrate trajectory evaluators for regression testing
   - Activate baseline comparison in CI/CD
   - Begin collecting gold standard dataset

4. **Week 3+**:
   - Weekly model evaluation
   - Decide on model fine-tuning based on baseline comparison
   - Expand regression test suite

---

**Questions or Issues?** Create Linear issue with label `langsmith-uat`.
