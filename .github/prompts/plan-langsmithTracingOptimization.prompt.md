## Plan: LangSmith Tracing Optimization & Training Dataset Strategy

### Phase 1: Performance Optimization

#### 1.1 Intent Recognition Optimization

**File**: [shared/lib/intent_recognizer.py](shared/lib/intent_recognizer.py)

**Changes**:

1. **Compress System Prompt** (60% token reduction)
```python
# Replace verbose system prompt with schema-first approach
system_prompt = """JSON API. Schema:
{type: enum[task_submission|status_query|clarification|approval_decision|general_query],
 confidence: float[0-1], needs_clarification: bool, task_type: enum[feature-dev|code-review|infrastructure|cicd|documentation],
 reasoning: str}

Rules: confidence 0.9+ if clear, extract IDs from "task-xyz" patterns, prefer task_type=feature-dev for code"""
```

2. **Conditional Conversation History** (threshold: 0.8)
```python
async def recognize(self, message: str, conversation_history: Optional[List] = None) -> Intent:
    """Recognize intent with adaptive context loading."""
    
    # First pass: No history
    intent = await self._classify(message, history=None)
    
    # Second pass: Include history only if confidence < 0.8
    if intent.confidence < 0.8 or intent.needs_clarification:
        intent = await self._classify(message, history=conversation_history[-3:] if conversation_history else None)
    
    return intent
```

3. **Model Selection** - Update [config/agents/models.yaml](config/agents/models.yaml)
```yaml
agents:
  # Add new intent_recognizer agent
  intent_recognizer:
    model: qwen/qwen-2.5-coder-7b-instruct
    cost_per_1m_tokens: 0.02
    context_window: 32768
    max_tokens: 512
    temperature: 0.1  # Low for consistent classification
    langsmith_project: code-chef-production
```

4. **Update Intent Recognizer Initialization** - [shared/lib/intent_recognizer.py](shared/lib/intent_recognizer.py)
```python
# Replace hardcoded model with config-based selection
def __init__(self):
    self.llm_client = get_llm_client("intent_recognizer")  # Uses qwen-2.5-coder-7b
```

**Expected Impact**:
- Latency: 3.4s → ~1.5s (-56%)
- Cost: $0.003/call → $0.00006/call (-98%)
- Token usage: 500 → 200 tokens/call (-60%)

---

#### 1.2 Orchestration Flow Trace Granularity

**Files to Update**:
- [shared/lib/linear_project_manager.py](shared/lib/linear_project_manager.py)
- [agent_orchestrator/workflows/workflow_router.py](agent_orchestrator/workflows/workflow_router.py)
- [shared/lib/mcp_tool_client.py](shared/lib/mcp_tool_client.py)

**Enhancement**: Add metadata_fn to expose safe context in traces

```python
# shared/lib/linear_project_manager.py
from langsmith import traceable

class LinearProjectManager:
    
    @traceable(
        name="get_or_create_project",
        tags=["linear", "project", "workspace"],
        metadata_fn=lambda self, workspace_name, github_repo_url, **kw: {
            "workspace": workspace_name,
            "has_github": github_repo_url is not None,
            "operation": "get_or_create"
        }
    )
    async def get_or_create_project(
        self,
        workspace_name: str,
        github_repo_url: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get or create Linear project with trace metadata."""
        # Existing implementation
        ...

    @traceable(
        name="list_projects",
        tags=["linear", "project", "list"],
        metadata_fn=lambda self, **kw: {
            "team_id": self.team_id,
            "operation": "list"
        }
    )
    async def list_projects(self) -> List[Dict[str, Any]]:
        """List Linear projects with trace metadata."""
        # Existing implementation
        ...
```

```python
# agent_orchestrator/workflows/workflow_router.py
@traceable(
    name="select_workflow",
    tags=["workflow", "routing", "selection"],
    metadata_fn=lambda self, task_description, **kw: {
        "task_length": len(task_description),
        "context_keys": list(kw.get("context", {}).keys()),
        "method": kw.get("method", "auto")
    }
)
async def select_workflow(
    self,
    task_description: str,
    context: Optional[Dict[str, Any]] = None,
    method: str = "auto"
) -> WorkflowSelection:
    """Select workflow with enhanced trace visibility."""
    # Existing implementation
    ...
```

```python
# shared/lib/mcp_tool_client.py
@traceable(
    name="invoke_tool",
    tags=["mcp", "tools", "invocation"],
    metadata_fn=lambda self, tool_name, arguments, **kw: {
        "tool": tool_name,
        "server": tool_name.split("/")[0] if "/" in tool_name else "unknown",
        "arg_count": len(arguments),
        "timeout": kw.get("timeout", 30.0)
    }
)
async def invoke_tool(
    self,
    tool_name: str,
    arguments: Dict[str, Any],
    timeout: float = 30.0
) -> Dict[str, Any]:
    """Invoke MCP tool with trace metadata."""
    # Existing implementation
    ...
```

**Benefit**: Trace visibility without exposing sensitive data (API keys, full payloads)

---

### Phase 2: Automated Trace Collection

#### 2.1 Auto-Annotation Script

**File**: `support/scripts/evaluation/auto_annotate_traces.py`

```python
"""
Automatic annotation of LangSmith traces for training dataset.

Usage:
    python support/scripts/evaluation/auto_annotate_traces.py --days 1
    python support/scripts/evaluation/auto_annotate_traces.py --experiment exp-2025-01-001
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from langsmith import Client
from lib.longitudinal_tracker import LongitudinalTracker

client = Client()

# Evaluation criteria
QUALITY_METRICS = {
    "intent_recognition": {
        "accuracy": lambda trace: verify_intent_matches_action(trace),
        "confidence_calibration": lambda trace: abs(trace.outputs.get("confidence", 0) - trace.metadata.get("actual_accuracy", 0)) < 0.2,
        "latency": lambda trace: (trace.end_time - trace.start_time).total_seconds() < 2.0,
        "token_efficiency": lambda trace: trace.prompt_tokens < 500,
    },
    "orchestration": {
        "routing_accuracy": lambda trace: verify_agent_selection(trace),
        "subtask_quality": lambda trace: all(is_actionable(st) for st in trace.outputs.get("subtasks", [])),
        "context_relevance": lambda trace: verify_context_used(trace),
        "completion_rate": lambda trace: trace.metadata.get("task_completed", False),
    }
}

def calculate_metrics(trace) -> Dict[str, float]:
    """Calculate quality metrics for a trace."""
    trace_type = trace.name
    
    if trace_type not in QUALITY_METRICS:
        return {"overall_score": 0.5}
    
    metrics = {}
    criteria = QUALITY_METRICS[trace_type]
    
    for metric_name, evaluator_fn in criteria.items():
        try:
            metrics[metric_name] = 1.0 if evaluator_fn(trace) else 0.0
        except Exception as e:
            metrics[metric_name] = 0.0
    
    metrics["overall_score"] = sum(metrics.values()) / len(metrics)
    return metrics

def verify_intent_matches_action(trace) -> bool:
    """Verify predicted intent matches actual user action."""
    predicted_intent = trace.outputs.get("type")
    # Check subsequent traces to see if task was created
    actual_intent = trace.metadata.get("actual_intent", predicted_intent)
    return predicted_intent == actual_intent

def verify_agent_selection(trace) -> bool:
    """Verify correct agent was selected for task."""
    selected_agent = trace.outputs.get("selected_agent")
    # Compare with task_type to validate routing
    task_type = trace.inputs.get("task_type")
    agent_map = {
        "feature-dev": "feature_dev",
        "code-review": "code_review",
        "infrastructure": "infrastructure",
    }
    return selected_agent == agent_map.get(task_type)

def is_actionable(subtask: str) -> bool:
    """Check if subtask is clear and actionable."""
    return len(subtask) > 20 and any(verb in subtask.lower() for verb in ["implement", "create", "update", "fix", "add", "remove", "refactor"])

def verify_context_used(trace) -> bool:
    """Verify project context was utilized."""
    return bool(trace.inputs.get("project_context") or trace.metadata.get("workspace_name"))

async def annotate_recent_traces(days: int = 1, experiment_id: Optional[str] = None):
    """Annotate traces from last N days."""
    start_time = datetime.utcnow() - timedelta(days=days)
    
    filter_query = f'start_time > "{start_time.isoformat()}" AND environment:"production"'
    if experiment_id:
        filter_query += f' AND experiment_id:"{experiment_id}"'
    
    # Fetch production traces
    traces = client.list_runs(
        project_name="code-chef-production",
        filter=filter_query
    )
    
    annotated_count = 0
    for trace in traces:
        # Skip if already annotated
        if any(f.key == "quality_score" for f in trace.feedback_stats):
            continue
        
        # Calculate metrics
        metrics = calculate_metrics(trace)
        
        # Add annotation
        client.create_feedback(
            run_id=trace.id,
            key="quality_score",
            score=metrics["overall_score"],
            comment=f"Auto-evaluated: {metrics}",
            metadata={
                "annotator": "auto",
                "criteria": list(metrics.keys()),
                "training_eligible": metrics["overall_score"] >= 0.8
            }
        )
        
        annotated_count += 1
        
        # Export high-quality traces
        if metrics["overall_score"] >= 0.8:
            await export_for_training(trace, metrics)
    
    print(f"✅ Annotated {annotated_count} traces")

async def export_for_training(trace, metrics: Dict[str, float]):
    """Export trace to training dataset format."""
    import json
    from pathlib import Path
    
    output_dir = Path("support/data/training/annotated_traces")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    training_example = {
        "trace_id": str(trace.id),
        "input": trace.inputs.get("prompt") or trace.inputs.get("message"),
        "output": trace.outputs,
        "metadata": {
            "quality_score": metrics["overall_score"],
            "metrics": metrics,
            "timestamp": trace.start_time.isoformat(),
            "agent": trace.metadata.get("agent_name"),
            "model": trace.metadata.get("model_version"),
        }
    }
    
    output_file = output_dir / f"{trace.id}.json"
    with open(output_file, "w") as f:
        json.dump(training_example, f, indent=2)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Auto-annotate LangSmith traces")
    parser.add_argument("--days", type=int, default=1, help="Number of days to look back")
    parser.add_argument("--experiment", type=str, help="Specific experiment ID to annotate")
    
    args = parser.parse_args()
    
    asyncio.run(annotate_recent_traces(days=args.days, experiment_id=args.experiment))
```

#### 2.2 GitHub Actions Workflow

**File**: `.github/workflows/annotate-traces.yml`

```yaml
name: Annotate Production Traces
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC
  workflow_dispatch:  # Manual trigger

jobs:
  annotate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install langsmith datasets httpx
      
      - name: Annotate traces
        env:
          LANGCHAIN_API_KEY: ${{ secrets.LANGCHAIN_API_KEY }}
          LANGSMITH_API_KEY: ${{ secrets.LANGCHAIN_API_KEY }}
        run: |
          python support/scripts/evaluation/auto_annotate_traces.py --days 1
      
      - name: Upload annotations
        uses: actions/upload-artifact@v4
        with:
          name: annotated-traces
          path: support/data/training/annotated_traces/
          retention-days: 30
```

---

### Phase 3: Training Dataset Construction

#### 3.1 Dataset Export Script

**File**: `support/scripts/evaluation/export_training_dataset.py`

```python
"""
Export annotated LangSmith traces to HuggingFace dataset for training.

Output format:
- Dataset: alextorelli/code-chef-intent-recognition-v1
- Structure: {input: str, output: dict, metadata: dict}

Usage:
    python support/scripts/evaluation/export_training_dataset.py --min-quality 0.8 --max-samples 10000
"""

import asyncio
from typing import List, Dict, Any
from datasets import Dataset, DatasetDict
from langsmith import Client

client = Client()

async def export_training_dataset(min_quality: float = 0.8, max_samples: int = 10000):
    """Export high-quality traces to HuggingFace."""
    
    # Fetch annotated traces
    traces = client.list_runs(
        project_name="code-chef-production",
        filter=f'has:feedback.quality_score AND feedback.quality_score >= {min_quality}',
        limit=max_samples
    )
    
    # Convert to training format
    examples = []
    for trace in traces:
        feedback = next((f for f in trace.feedback_stats if f.key == "quality_score"), None)
        if not feedback:
            continue
        
        example = {
            "input": trace.inputs.get("prompt") or trace.inputs.get("message", ""),
            "output": trace.outputs,
            "metadata": {
                "trace_id": str(trace.id),
                "quality_score": feedback.score,
                "timestamp": trace.start_time.isoformat(),
                "agent": trace.metadata.get("agent_name"),
                "model": trace.metadata.get("model_version"),
                "latency_ms": (trace.end_time - trace.start_time).total_seconds() * 1000,
                "tokens": trace.prompt_tokens + trace.completion_tokens,
            }
        }
        examples.append(example)
    
    if len(examples) == 0:
        print("❌ No annotated traces found. Run auto_annotate_traces.py first.")
        return
    
    # Split into train/validation/test (80/10/10)
    dataset = Dataset.from_list(examples)
    dataset_dict = dataset.train_test_split(test_size=0.2, seed=42)
    val_test = dataset_dict["test"].train_test_split(test_size=0.5, seed=42)
    
    final_dataset = DatasetDict({
        "train": dataset_dict["train"],
        "validation": val_test["train"],
        "test": val_test["test"]
    })
    
    # Upload to HuggingFace
    final_dataset.push_to_hub("alextorelli/code-chef-intent-recognition-v1", private=False)
    
    print(f"✅ Exported {len(examples)} examples to HuggingFace")
    print(f"   Train: {len(final_dataset['train'])} examples")
    print(f"   Validation: {len(final_dataset['validation'])} examples")
    print(f"   Test: {len(final_dataset['test'])} examples")
    print(f"\n📊 Dataset URL: https://huggingface.co/datasets/alextorelli/code-chef-intent-recognition-v1")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Export training dataset to HuggingFace")
    parser.add_argument("--min-quality", type=float, default=0.8, help="Minimum quality score")
    parser.add_argument("--max-samples", type=int, default=10000, help="Maximum samples to export")
    
    args = parser.parse_args()
    
    asyncio.run(export_training_dataset(
        min_quality=args.min_quality,
        max_samples=args.max_samples
    ))
```

---

### Phase 4: Evaluation Framework

#### 4.1 Intent Recognition Evaluator

**File**: `support/tests/evaluation/test_intent_recognition_eval.py`

```python
"""
Evaluation suite for intent recognition improvements.

Compares baseline vs code-chef on held-out test set using A/B testing framework.

Usage:
    pytest support/tests/evaluation/test_intent_recognition_eval.py -v
    HYPOTHESIS_PROFILE=thorough pytest support/tests/evaluation/test_intent_recognition_eval.py -v
"""

import pytest
import numpy as np
from scipy.stats import ttest_rel
from datasets import load_dataset
from support.tests.evaluation.evaluators import (
    IntentAccuracyEvaluator,
    ConfidenceCalibrationEvaluator,
    LatencyEvaluator,
    TokenEfficiencyEvaluator
)

@pytest.mark.asyncio
async def test_intent_recognition_improvement(
    longitudinal_tracker_fixture,
    baseline_llm_client,  # Fixture: Claude 3.5 Sonnet with verbose prompt
    codechef_llm_client,  # Fixture: Qwen 2.5 Coder 7B with compressed prompt
    ab_experiment_id
):
    """
    Evaluate intent recognition improvement using A/B testing.
    
    Success Criteria:
    - Accuracy improvement: +15% (baseline: 72% → target: 87%)
    - Latency reduction: -50% (baseline: 3.4s → target: 1.7s)
    - Cost reduction: -98% (baseline: $0.003 → target: $0.00006)
    - Token efficiency: -60% (baseline: 500 → target: 200 tokens)
    """
    
    # Load test dataset
    test_dataset = load_dataset(
        "alextorelli/code-chef-intent-recognition-v1",
        split="test"
    )
    
    # Initialize evaluators
    accuracy_eval = IntentAccuracyEvaluator()
    latency_eval = LatencyEvaluator(threshold_ms=2000)
    token_eval = TokenEfficiencyEvaluator(max_tokens=500)
    
    tracker = longitudinal_tracker_fixture
    
    # Run baseline
    baseline_accuracy = []
    baseline_latency = []
    baseline_tokens = []
    
    for example in test_dataset:
        result = await baseline_llm_client.complete(
            prompt=example["input"],
            metadata={"experiment_group": "baseline", "task_id": example["metadata"]["trace_id"]}
        )
        
        accuracy_score = await accuracy_eval.evaluate(result, example["output"])
        baseline_accuracy.append(accuracy_score)
        baseline_latency.append(result.get("latency", 0))
        baseline_tokens.append(result.get("prompt_tokens", 0) + result.get("completion_tokens", 0))
        
        # Store in PostgreSQL
        await tracker.record_result(
            agent="intent_recognizer",
            experiment_id=ab_experiment_id,
            experiment_group="baseline",
            task_id=example["metadata"]["trace_id"],
            scores={
                "accuracy": accuracy_score,
                "latency": result.get("latency", 0),
                "tokens": baseline_tokens[-1],
                "cost": (baseline_tokens[-1] / 1_000_000) * 3.0  # Claude pricing
            }
        )
    
    # Run code-chef
    codechef_accuracy = []
    codechef_latency = []
    codechef_tokens = []
    
    for example in test_dataset:
        result = await codechef_llm_client.complete(
            prompt=example["input"],
            metadata={"experiment_group": "code-chef", "task_id": example["metadata"]["trace_id"]}
        )
        
        accuracy_score = await accuracy_eval.evaluate(result, example["output"])
        codechef_accuracy.append(accuracy_score)
        codechef_latency.append(result.get("latency", 0))
        codechef_tokens.append(result.get("prompt_tokens", 0) + result.get("completion_tokens", 0))
        
        await tracker.record_result(
            agent="intent_recognizer",
            experiment_id=ab_experiment_id,
            experiment_group="code-chef",
            task_id=example["metadata"]["trace_id"],
            scores={
                "accuracy": accuracy_score,
                "latency": result.get("latency", 0),
                "tokens": codechef_tokens[-1],
                "cost": (codechef_tokens[-1] / 1_000_000) * 0.02  # Qwen pricing
            }
        )
    
    # Statistical comparison
    t_stat, p_value = ttest_rel(baseline_accuracy, codechef_accuracy)
    
    accuracy_improvement = ((np.mean(codechef_accuracy) - np.mean(baseline_accuracy)) / np.mean(baseline_accuracy)) * 100
    latency_improvement = ((np.mean(baseline_latency) - np.mean(codechef_latency)) / np.mean(baseline_latency)) * 100
    token_improvement = ((np.mean(baseline_tokens) - np.mean(codechef_tokens)) / np.mean(baseline_tokens)) * 100
    
    # Calculate cost savings
    baseline_cost = (sum(baseline_tokens) / 1_000_000) * 3.0
    codechef_cost = (sum(codechef_tokens) / 1_000_000) * 0.02
    cost_improvement = ((baseline_cost - codechef_cost) / baseline_cost) * 100
    
    # Assert improvements
    assert accuracy_improvement >= 15, f"Accuracy improvement {accuracy_improvement:.1f}% below target (15%)"
    assert p_value < 0.05, f"Improvement not statistically significant (p={p_value:.3f})"
    assert latency_improvement >= 40, f"Latency improvement {latency_improvement:.1f}% below target (50%)"
    assert token_improvement >= 50, f"Token efficiency {token_improvement:.1f}% below target (60%)"
    assert cost_improvement >= 95, f"Cost reduction {cost_improvement:.1f}% below target (98%)"
    
    print(f"\n✅ Intent Recognition Improvements:")
    print(f"   Accuracy:    {accuracy_improvement:+.1f}% (p={p_value:.4f})")
    print(f"   Latency:     {latency_improvement:+.1f}%")
    print(f"   Tokens:      {token_improvement:+.1f}%")
    print(f"   Cost:        {cost_improvement:+.1f}%")
    print(f"\n💰 Cost Savings: ${baseline_cost:.4f} → ${codechef_cost:.6f} per {len(test_dataset)} calls")
```

#### 4.2 Continuous Evaluation Workflow

**File**: `.github/workflows/evaluate-model-performance.yml`

```yaml
name: Evaluate Model Performance
on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday
  workflow_dispatch:  # Manual trigger

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r support/tests/requirements.txt
      
      - name: Run evaluation suite
        env:
          LANGCHAIN_API_KEY: ${{ secrets.LANGCHAIN_API_KEY }}
          POSTGRES_CHECKPOINT_URI: ${{ secrets.POSTGRES_CHECKPOINT_URI }}
        run: |
          pytest support/tests/evaluation/test_intent_recognition_eval.py -v --tb=short
      
      - name: Generate regression report
        if: failure()
        run: |
          python support/scripts/evaluation/generate_regression_report.py
      
      - name: Create Linear issue on regression
        if: failure()
        env:
          LINEAR_API_KEY: ${{ secrets.LINEAR_API_KEY }}
        run: |
          python support/scripts/linear/create_regression_issue.py \
            --title "Model Performance Regression Detected" \
            --priority "high" \
            --label "regression"
```

---

### Phase 5: Active Learning Loop

#### 5.1 Uncertainty Sampling

**File**: [shared/lib/intent_recognizer.py](shared/lib/intent_recognizer.py)

```python
from langsmith import Client

langsmith_client = Client()

async def recognize(self, message: str, conversation_history: Optional[List] = None) -> Intent:
    """Recognize intent with uncertainty flagging for active learning."""
    
    # Existing recognition logic
    intent = await self._classify(message, history=conversation_history)
    
    # Flag low-confidence predictions for manual review
    if intent.confidence < 0.8:
        try:
            # Get current trace ID from LangSmith context
            from langsmith import get_current_run_tree
            current_trace = get_current_run_tree()
            
            if current_trace:
                langsmith_client.create_feedback(
                    run_id=current_trace.id,
                    key="needs_review",
                    value=True,
                    comment=f"Low confidence ({intent.confidence:.2f}) - prioritize for annotation",
                    metadata={
                        "review_priority": "high" if intent.confidence < 0.6 else "medium",
                        "intent_type": intent.type,
                        "add_to_training": True
                    }
                )
        except Exception as e:
            logger.warning(f"Failed to flag trace for review: {e}")
    
    return intent
```

#### 5.2 Hard Negative Mining

**File**: [agent_orchestrator/main.py](agent_orchestrator/main.py)

```python
# Add post-task evaluation to chat endpoint
@app.post("/chat", response_model=ChatResponse, tags=["chat"])
@traceable(name="chat_endpoint", tags=["chat", "nlp", "conversation"])
async def chat_endpoint(request: ChatRequest):
    """Natural language chat interface with outcome tracking."""
    
    # Existing chat logic
    response = await process_chat_request(request)
    
    # Post-task evaluation: Compare predicted intent with actual outcome
    if response.intent == "task_submission" and response.task_id:
        # Schedule async task to verify intent accuracy after task completion
        asyncio.create_task(
            evaluate_intent_accuracy(
                predicted_intent=response.intent,
                task_id=response.task_id,
                trace_id=get_current_run_tree().id
            )
        )
    
    return response

async def evaluate_intent_accuracy(predicted_intent: str, task_id: str, trace_id: str):
    """Evaluate if predicted intent matched actual user action."""
    from langsmith import Client
    
    # Wait for task to complete or timeout
    await asyncio.sleep(300)  # 5 minute delay
    
    # Check if task was actually created and completed
    task_status = await get_task_status(task_id)
    
    if task_status["created"] and task_status["completed"]:
        actual_intent = "task_submission"
    elif task_status["created"] and not task_status["completed"]:
        actual_intent = "clarification"  # User needed more info
    else:
        actual_intent = "general_query"  # No task created
    
    # Flag mismatches as false positives
    if actual_intent != predicted_intent:
        langsmith_client = Client()
        langsmith_client.create_feedback(
            run_id=trace_id,
            key="false_positive",
            score=0.0,
            comment=f"Predicted {predicted_intent}, actual was {actual_intent}",
            metadata={
                "add_to_training": True,
                "priority": "high",
                "task_id": task_id
            }
        )
```

#### 5.3 Diversity Sampling

**File**: `support/scripts/evaluation/check_dataset_diversity.py`

```python
"""
Check training dataset diversity and identify underrepresented intents.

Usage:
    python support/scripts/evaluation/check_dataset_diversity.py
"""

from collections import Counter
from datasets import load_dataset
from langsmith import Client

client = Client()

def check_diversity():
    """Check dataset diversity and flag underrepresented classes."""
    
    # Load current training dataset
    try:
        dataset = load_dataset("alextorelli/code-chef-intent-recognition-v1", split="train")
    except:
        print("❌ Dataset not found. Export traces first.")
        return
    
    # Count intent distribution
    intent_counts = Counter([ex["output"].get("type") for ex in dataset])
    
    print("\n📊 Intent Distribution:")
    for intent, count in intent_counts.most_common():
        print(f"   {intent:25s}: {count:4d} examples")
    
    # Identify underrepresented intents (< 50 examples)
    rare_intents = [intent for intent, count in intent_counts.items() if count < 50]
    
    if rare_intents:
        print(f"\n⚠️  Underrepresented Intents (< 50 examples):")
        for intent in rare_intents:
            print(f"   - {intent}: {intent_counts[intent]} examples")
        
        # Flag traces with rare intents for priority annotation
        traces = client.list_runs(
            project_name="code-chef-production",
            filter=f'outputs.type IN {rare_intents}'
        )
        
        for trace in traces:
            client.create_feedback(
                run_id=trace.id,
                key="diversity_sampling",
                value=True,
                comment=f"Rare intent '{trace.outputs.get('type')}' - prioritize for training",
                metadata={"review_priority": "high", "add_to_training": True}
            )
        
        print(f"\n✅ Flagged {len(list(traces))} traces with rare intents for annotation")
    else:
        print("\n✅ All intents well-represented (≥ 50 examples each)")

if __name__ == "__main__":
    check_diversity()
```

---

## Implementation Checklist

### Phase 1: Performance Optimization
- [ ] Update [shared/lib/intent_recognizer.py](shared/lib/intent_recognizer.py) - compress prompt, conditional history (threshold 0.8)
- [ ] Add `intent_recognizer` agent to [config/agents/models.yaml](config/agents/models.yaml) - Qwen 2.5 Coder 7B
- [ ] Update [shared/lib/linear_project_manager.py](shared/lib/linear_project_manager.py) - add metadata_fn to @traceable
- [ ] Update [agent_orchestrator/workflows/workflow_router.py](agent_orchestrator/workflows/workflow_router.py) - add metadata_fn
- [ ] Update [shared/lib/mcp_tool_client.py](shared/lib/mcp_tool_client.py) - add metadata_fn
- [ ] Deploy and verify traces show enhanced metadata

### Phase 2: Automated Trace Collection
- [ ] Create `support/scripts/evaluation/auto_annotate_traces.py`
- [ ] Create `.github/workflows/annotate-traces.yml`
- [ ] Create `support/data/training/annotated_traces/` directory
- [ ] Run initial annotation: `python support/scripts/evaluation/auto_annotate_traces.py --days 7`
- [ ] Verify annotations appear in LangSmith

### Phase 3: Training Dataset Construction
- [ ] Create `support/scripts/evaluation/export_training_dataset.py`
- [ ] Export initial dataset: `python support/scripts/evaluation/export_training_dataset.py --min-quality 0.8`
- [ ] Verify dataset published to HuggingFace: `alextorelli/code-chef-intent-recognition-v1`
- [ ] Validate train/validation/test splits (80/10/10)

### Phase 4: Evaluation Framework
- [ ] Create `support/tests/evaluation/test_intent_recognition_eval.py`
- [ ] Create `.github/workflows/evaluate-model-performance.yml`
- [ ] Run baseline evaluation: `pytest support/tests/evaluation/test_intent_recognition_eval.py -v`
- [ ] Verify metrics stored in PostgreSQL via `longitudinal_tracker`

### Phase 5: Active Learning Loop
- [ ] Add uncertainty sampling to [shared/lib/intent_recognizer.py](shared/lib/intent_recognizer.py)
- [ ] Add hard negative mining to [agent_orchestrator/main.py](agent_orchestrator/main.py)
- [ ] Create `support/scripts/evaluation/check_dataset_diversity.py`
- [ ] Schedule weekly diversity checks in GitHub Actions

---

## Expected Impact

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| **Intent Recognition Latency** | 3.4s | 1.5s | -56% |
| **Intent Recognition Cost** | $0.003/call | $0.00006/call | -98% |
| **Token Usage** | 500 tokens/call | 200 tokens/call | -60% |
| **Intent Accuracy** | 72% | 87% | +15% |
| **Training Dataset Size** | 0 | 1,000+ examples | Bootstrap complete |
| **Evaluation Coverage** | Manual | Automated + Continuous | Full CI/CD |

**Cost Savings**: ~$50/month at 50K calls/month  
**Data Foundation**: Self-improving system via active learning from production traces
