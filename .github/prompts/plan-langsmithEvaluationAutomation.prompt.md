# LangSmith Evaluation Automation Plan

Based on the LangChain documentation and your existing evaluation infrastructure, here's a comprehensive plan to complete LangSmith eval automation:

## Current State Assessment

You already have excellent groundwork:

- ✅ Custom evaluators ([evaluators.py](d:/APPS/code-chef/support/tests/evaluation/evaluators.py))
- ✅ Baseline runner for A/B testing
- ✅ Annotation protocol and dataset building
- ✅ Longitudinal tracking infrastructure
- ⚠️ **Missing**: Direct LangSmith SDK `evaluate()` integration

## Recommended Automation Strategy

### 1. **Use LangSmith's `evaluate()` API** (Primary Method)

The LangSmith SDK provides a powerful `evaluate()` function that automatically:

- Runs your target system against a dataset
- Applies evaluators in parallel
- Stores results with full trace lineage
- Compares across experiments

**Implementation** (update [run_evaluation.py](d:/APPS/code-chef/support/tests/evaluation/run_evaluation.py)):

```python
from langsmith import Client
from langsmith.evaluation import evaluate, LangChainStringEvaluator
from langsmith.schemas import Run, Example

# Your existing custom evaluators
from support.tests.evaluation.evaluators import (
    agent_routing_accuracy,
    token_efficiency,
    latency_threshold,
    workflow_completeness,
    mcp_integration_quality
)

client = Client()

# Target function - your actual system
async def code_chef_target(inputs: dict) -> dict:
    """Invoke code-chef orchestrator with user message."""
    response = await orchestrator_client.post(
        "https://codechef.appsmithery.co/api/execute",
        json={
            "message": inputs["query"],
            "user_id": inputs.get("user_id", "eval-user"),
            "mode": inputs.get("mode", "auto")
        }
    )
    return {
        "output": response.json()["response"],
        "agent": response.json().get("agent_used"),
        "tokens": response.json().get("token_usage")
    }

# Wrap custom evaluators for LangSmith
def wrap_evaluator(evaluator_fn):
    """Convert your evaluator to LangSmith format."""
    def wrapped(run: Run, example: Example) -> dict:
        result = evaluator_fn(run, example)
        return {
            "key": result.key,
            "score": result.score,
            "comment": result.comment
        }
    return wrapped

# Run evaluation
results = evaluate(
    code_chef_target,
    data="code-chef-gold-standard-v1",  # Your annotated dataset
    evaluators=[
        wrap_evaluator(agent_routing_accuracy),
        wrap_evaluator(token_efficiency),
        wrap_evaluator(latency_threshold),
        wrap_evaluator(workflow_completeness),
        wrap_evaluator(mcp_integration_quality)
    ],
    experiment_prefix="code-chef-eval",
    metadata={
        "experiment_group": "code-chef",
        "environment": "evaluation",
        "extension_version": os.getenv("EXTENSION_VERSION", "1.0.0")
    },
    max_concurrency=5  # Parallel evaluation
)

# Results automatically stored in LangSmith with full traces
print(f"Evaluation complete: {results['project_url']}")
```

### 2. **Add LangSmith Prebuilt Evaluators** (Supplement Custom Ones)

LangSmith provides battle-tested evaluators you can combine with yours:

```python
from langsmith.evaluation import LangChainStringEvaluator

# Prebuilt evaluators (no LLM needed)
prebuilt_evaluators = [
    # String similarity
    LangChainStringEvaluator("embedding_distance", config={
        "embeddings": OpenAIEmbeddings(),
        "distance_metric": "cosine"
    }),

    # Exact match for structured outputs
    LangChainStringEvaluator("exact_match"),

    # Regex patterns for expected formats
    LangChainStringEvaluator("regex_match", config={
        "patterns": [r"MCP server", r"tool"]  # For MCP awareness
    })
]

# LLM-as-judge evaluators (for semantic correctness)
llm_evaluators = [
    # Criteria-based (uses your LLM)
    LangChainStringEvaluator("criteria", config={
        "criteria": {
            "helpfulness": "Is the response helpful and actionable?",
            "accuracy": "Is the response factually correct?",
            "completeness": "Does it address all parts of the question?"
        },
        "llm": ChatOpenAI(model="gpt-4")
    }),

    # Labeled criteria (with rubric)
    LangChainStringEvaluator("labeled_criteria", config={
        "criteria": {
            "mcp_awareness": {
                "0": "Doesn't mention MCP or tools",
                "1": "Mentions MCP but incorrectly",
                "2": "Correctly identifies MCP servers and tool count"
            }
        }
    })
]

# Combine in evaluation
results = evaluate(
    code_chef_target,
    data="code-chef-gold-standard-v1",
    evaluators=[
        *[wrap_evaluator(e) for e in ALL_EVALUATORS],  # Your custom ones
        *prebuilt_evaluators,  # LangSmith prebuilt
        *llm_evaluators  # LLM-as-judge
    ]
)
```

### 3. **Automated Comparison Experiments**

Use LangSmith's experiment comparison to automate A/B testing:

```python
# Baseline experiment
baseline_results = evaluate(
    baseline_target,  # Untrained model
    data="code-chef-gold-standard-v1",
    evaluators=all_evaluators,
    experiment_prefix="baseline",
    metadata={"experiment_group": "baseline"}
)

# Code-chef experiment
codechef_results = evaluate(
    code_chef_target,  # Your trained model
    data="code-chef-gold-standard-v1",
    evaluators=all_evaluators,
    experiment_prefix="code-chef",
    metadata={"experiment_group": "code-chef"}
)

# LangSmith automatically links these for comparison
# View in UI: Experiments tab → Compare baseline vs code-chef
```

### 4. **Continuous Evaluation Automation**

Create a GitHub Actions workflow that runs on every commit:

```yaml
# .github/workflows/continuous-evaluation.yml
name: Continuous Evaluation

on:
  push:
    branches: [main]
  schedule:
    - cron: "0 0 * * 0" # Weekly Sunday midnight

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run LangSmith Evaluation
        env:
          LANGCHAIN_API_KEY: ${{ secrets.LANGCHAIN_API_KEY }}
          ORCHESTRATOR_URL: https://codechef.appsmithery.co
        run: |
          python support/tests/evaluation/run_langsmith_evaluation.py \
            --dataset code-chef-gold-standard-v1 \
            --experiment-prefix "ci-$(date +%Y%m%d)" \
            --compare-to-baseline

      - name: Check for Regression
        run: |
          python support/scripts/evaluation/detect_regression.py \
            --threshold 0.05 \
            --create-linear-issue
```

### 5. **Dataset Management Automation**

Automate dataset updates from annotated traces:

```python
# support/scripts/evaluation/sync_dataset_from_annotations.py
from langsmith import Client

client = Client()

# Query annotated traces from last week
annotated_traces = client.list_runs(
    project_name="code-chef-production",
    filter='has(feedback) and feedback_scores["correctness"] < 0.7',
    start_time=datetime.now() - timedelta(days=7)
)

# Add to evaluation dataset
dataset = client.read_dataset(dataset_name="code-chef-gold-standard-v1")

for trace in annotated_traces:
    client.create_example(
        inputs={"query": trace.inputs["message"]},
        outputs={"expected": trace.reference_example.outputs},
        dataset_id=dataset.id,
        metadata={
            "source": "production_annotation",
            "correctness": trace.feedback_scores["correctness"],
            "failure_category": trace.feedback_tags[0] if trace.feedback_tags else None
        }
    )
```

## Recommended Implementation Order

### Week 1: Core Integration

1. ✅ Update [run_evaluation.py](d:/APPS/code-chef/support/tests/evaluation/run_evaluation.py) to use `evaluate()` API
2. ✅ Wrap existing custom evaluators for LangSmith format
3. ✅ Test on small dataset (10 examples)

### Week 2: Enhance Evaluators

4. ✅ Add LangSmith prebuilt evaluators (embedding_distance, criteria)
5. ✅ Create LLM-as-judge evaluators for MCP awareness, tool discovery
6. ✅ Validate evaluator outputs match expectations

### Week 3: Automation

7. ✅ Create continuous evaluation GitHub Action
8. ✅ Implement dataset sync from annotations
9. ✅ Set up regression detection with Linear issue creation

### Week 4: Refinement

10. ✅ Compare baseline vs code-chef experiments
11. ✅ Calculate improvement metrics (>15% threshold)
12. ✅ Document findings and iteration plan

## Key Benefits of This Approach

| Benefit                     | How It Helps                                       |
| --------------------------- | -------------------------------------------------- |
| **Automatic trace lineage** | Every eval run creates full traces you can inspect |
| **Parallel execution**      | Evaluators run concurrently (5-10x faster)         |
| **Built-in comparison**     | LangSmith UI automatically compares experiments    |
| **Regression detection**    | Statistical significance testing built-in          |
| **Dataset versioning**      | Track dataset changes over time                    |
| **Cost tracking**           | Automatic LLM cost calculation per evaluation      |

## Example: Complete Evaluation Script

Create `support/tests/evaluation/run_langsmith_evaluation.py`:

```python
"""Complete LangSmith evaluation automation."""

import asyncio
from datetime import datetime
from langsmith import Client
from langsmith.evaluation import evaluate, LangChainStringEvaluator
from support.tests.evaluation.evaluators import ALL_EVALUATORS

async def main():
    client = Client()

    # Target system
    async def code_chef_target(inputs: dict) -> dict:
        response = await orchestrator_client.post(
            "https://codechef.appsmithery.co/api/execute",
            json={
                "message": inputs["query"],
                "user_id": inputs.get("user_id", "eval-user"),
                "mode": inputs.get("mode", "auto")
            }
        )
        return {
            "output": response.json()["response"],
            "agent": response.json().get("agent_used"),
            "tokens": response.json().get("token_usage")
        }

    # Wrap evaluators
    def wrap_evaluator(evaluator_fn):
        def wrapped(run: Run, example: Example) -> dict:
            result = evaluator_fn(run, example)
            return {
                "key": result.key,
                "score": result.score,
                "comment": result.comment
            }
        return wrapped

    # Run evaluation
    results = await evaluate(
        code_chef_target,
        data="code-chef-gold-standard-v1",
        evaluators=[
            *[wrap_evaluator(e) for e in ALL_EVALUATORS],
            LangChainStringEvaluator("embedding_distance"),
            LangChainStringEvaluator("criteria", config={
                "criteria": {
                    "mcp_awareness": "Does response correctly identify MCP servers?"
                }
            })
        ],
        experiment_prefix=f"eval-{datetime.now().strftime('%Y%m%d')}",
        metadata={
            "experiment_group": "code-chef",
            "environment": "evaluation"
        },
        max_concurrency=5
    )

    # Check for regression
    if results["aggregate_metrics"]["accuracy"] < 0.85:
        create_linear_issue(
            title="Evaluation Regression Detected",
            description=f"Accuracy dropped to {results['aggregate_metrics']['accuracy']}"
        )

    return results

if __name__ == "__main__":
    asyncio.run(main())
```

## Next Steps

This approach completes your eval automation while leveraging LangSmith's powerful features. The key is integrating `evaluate()` API with your existing custom evaluators, then layering on automation via GitHub Actions.

**Priority Actions:**

1. Implement the core `evaluate()` integration in run_evaluation.py
2. Test with a small dataset to validate the wrapper functions
3. Add prebuilt evaluators for quick wins (embedding_distance, exact_match)
4. Set up continuous evaluation in GitHub Actions
5. Create dataset sync automation for annotation feedback loop
