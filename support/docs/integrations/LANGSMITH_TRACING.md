# LangSmith Tracing Integration

> **📘 Complete LLM Operations Guide**: For model selection, training, evaluation, and deployment, see [LLM Operations Guide](../operations/llm-operations.md). This document focuses on tracing configuration and metadata standards.

**Last Updated**: December 24, 2025  
**Schema Version**: 1.0.0  
**Clean Start Date**: December 10, 2025 (all historical traces deleted)  
**Annotation Workflow**: Active (Phase 0 - collect before code changes)

## Overview

All Dev-Tools agents are instrumented with **LangSmith** for comprehensive observability supporting:

- 📊 **Longitudinal Tracking** - Measure improvement over time
- 🧪 **A/B Testing** - Compare code-chef vs baseline
- 🏷️ **Environment Isolation** - Separate production/training/evaluation/test traces
- ⏱️ **Performance Metrics** - Latency, token usage, cost tracking
- 🔍 **Full Visibility** - Prompts, completions, errors
- 🔄 **Workflow Graphs** - LangGraph execution visualization

## Dashboard Access

**Production**: https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207

---

## New Project Structure (December 10, 2025)

We transitioned from per-agent projects to **purpose-based projects**:

### Projects

| Project                    | Purpose                             | Filter                      |
| -------------------------- | ----------------------------------- | --------------------------- |
| `code-chef-production`     | Live extension usage                | `environment:"production"`  |
| `code-chef-experiments`    | A/B test comparisons                | `experiment_id IS NOT NULL` |
| `code-chef-training`       | Model training operations           | `module:"training"`         |
| `code-chef-evaluation`     | Model evaluation runs               | `module:"evaluation"`       |
| `code-chef-test` (optional | Test suite runs (if tracing enabled | `environment:"test"`        |

### Old Projects (Deprecated)

These were deleted December 10, 2025:

- ~~`code-chef-feature-dev`~~
- ~~`code-chef-code-review`~~
- ~~`code-chef-infrastructure`~~
- ~~`code-chef-cicd`~~
- ~~`code-chef-documentation`~~
- ~~`code-chef-supervisor`~~

**Reason for change**: Purpose-based organization better supports longitudinal tracking and A/B testing.

---

## Metadata Schema

All traces now include standardized metadata (see `config/observability/tracing-schema.yaml`):

### Core Fields

```yaml
experiment_group: code-chef | baseline # For A/B testing
environment: production | training | evaluation | test
module: training | evaluation | deployment | registry | coordinator | {agent_name}
extension_version: "1.2.3" # Semver
model_version: "codellama-13b-v2" # Model identifier
```

### Optional Fields

```yaml
experiment_id: "exp-2025-01-001" # Correlate A/B runs
task_id: "task-{uuid}" # Correlate same task across groups
config_hash: "sha256:a1b2c3d4" # Config fingerprint
agent: "infrastructure" # Agent name
```

### Example Metadata

**Production trace**:

```python
{
    "experiment_group": "code-chef",
    "environment": "production",
    "module": "feature_dev",
    "extension_version": "1.2.3",
    "model_version": "codellama-13b-v2",
    "config_hash": "sha256:a1b2c3d4"
}
```

**Training operation**:

```python
{
    "experiment_group": "code-chef",
    "environment": "training",
    "module": "training",
    "extension_version": "1.2.3",
    "model_version": "codellama-13b-v3",
    "agent": "infrastructure"
}
```

**A/B test comparison**:

```python
{
    "experiment_id": "exp-2025-01-001",
    "task_id": "task-550e8400-...",
    "experiment_group": "baseline",  # or "code-chef"
    "environment": "evaluation",
    "module": "evaluation",
    "extension_version": "1.2.3"
}
```

---

## Configuration

### Environment Variables

Set in `config/env/.env`:

```bash
# Enable LangSmith tracing
LANGSMITH_TRACING=true
LANGCHAIN_TRACING_V2=true

# LangSmith connection
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=lsv2_sk_***
LANGSMITH_API_KEY=lsv2_sk_***
LANGSMITH_WORKSPACE_ID=5029c640-3f73-480c-82f3-58e402ed4207

# Project selection (auto-selected by code based on environment)
LANGSMITH_PROJECT_PRODUCTION=code-chef-production
LANGSMITH_PROJECT_EXPERIMENTS=code-chef-experiments
LANGSMITH_PROJECT_TRAINING=code-chef-training
LANGSMITH_PROJECT_EVALUATION=code-chef-evaluation

# Metadata for traces
TRACE_ENVIRONMENT=production             # production | training | evaluation | test
EXPERIMENT_GROUP=code-chef               # code-chef | baseline
EXTENSION_VERSION=1.2.3                  # Current extension version
MODEL_VERSION=codellama-13b-v2           # Current model version
EXPERIMENT_ID=                           # Set when running A/B tests
TASK_ID=                                 # Set when correlating tasks
AGENT_NAME=infrastructure                # Current agent name
```

### Key Types

| Key Type       | Format      | Use Case                      |
| -------------- | ----------- | ----------------------------- |
| Service Key    | `lsv2_sk_*` | Production (org-level access) |
| Personal Token | `lsv2_pt_*` | Development (user-level)      |

**Note**: Service keys require `LANGSMITH_WORKSPACE_ID`.

---

## Annotation-First Testing Workflow

**Philosophy**: Collect data → annotate → evaluate → tune models → **then** fix code

### Phase 0: Data Collection (2-4 weeks)

**Goal**: Accumulate 100+ annotated traces covering common failure modes

**Process**:

1. **Run test prompts** from [`support/tests/chat-participant-test-prompts.md`](../../tests/chat-participant-test-prompts.md)
2. **Review traces** in LangSmith (code-chef-production project)
3. **Annotate incorrect responses**:
   - **Correctness score**: 0.0 (incorrect) to 1.0 (perfect)
   - **Note field**: Explain what went wrong and what was expected
4. **Add to datasets**: Create `code-chef-gold-standard-v1` dataset in LangSmith
5. **Categorize failures**:
   - MCP awareness (doesn't recognize "mcp" acronym)
   - Tool discovery (can't list available MCP servers)
   - Agent routing (wrong agent selected)
   - Code generation (incorrect syntax/logic)
   - Context understanding (misses file references)

### Example Annotation

**Trace**: https://smith.langchain.com/public/fb55af3a-821a-4a01-9245-fe18f3610142/r

**User Query**: "which mcp servers do you have access to?"

**Annotation**:

- **Correctness**: 0.00 (completely incorrect)
- **Note**: "Model didn't recognize 'mcp' acronym. Should list 15+ MCP servers from Docker MCP Toolkit: memory, github, rust-mcp-filesystem, mcp_huggingface, mcp_copilot_conta, brave-search, fetch, mcp_docs_by_langc, sequential-thinking, etc. Expected response: 'I have access to 178+ tools from 15+ MCP servers including...'"

**Category**: MCP awareness

### Evaluation Before Code Changes

Before tweaking prompts or code:

```bash
# Run baseline evaluation on annotated dataset
python support/scripts/evaluation/baseline_runner.py \
  --mode baseline \
  --dataset code-chef-gold-standard-v1 \
  --output baseline-results.json

# Review metrics
cat baseline-results.json | jq '.metrics'
# Example: {"accuracy": 0.72, "mcp_awareness": 0.35, "tool_discovery": 0.50}
```

If MCP awareness is <0.70, prioritize model training or prompt engineering for that category.

### Building Evaluation Datasets

**LangSmith UI**:

1. Go to project: `code-chef-production`
2. Filter annotated traces: `correctness <= 0.5` (failures)
3. Click "Add to Dataset" → Create `code-chef-gold-standard-v1`
4. Include both failures and successes (balanced dataset)

**Programmatic**:

```python
from langsmith import Client

client = Client()

# Create dataset
dataset = client.create_dataset(
    dataset_name="code-chef-gold-standard-v1",
    description="Annotated traces for model evaluation"
)

# Add examples
for trace in annotated_traces:
    client.create_example(
        dataset_id=dataset.id,
        inputs={"messages": trace.inputs},
        outputs={"response": trace.outputs},
        metadata={
            "correctness": trace.feedback["correctness"],
            "category": trace.metadata["category"],
            "note": trace.feedback["note"]
        }
    )
```

### Model Improvement Thresholds

| Improvement | Action        | Rationale                                 |
| ----------- | ------------- | ----------------------------------------- |
| >15%        | Deploy        | Significant improvement, safe to deploy   |
| 5-15%       | Manual review | Moderate improvement, validate edge cases |
| <5%         | Reject        | Insufficient improvement or regression    |

**DO NOT** make code changes until:

- ✅ 100+ traces annotated
- ✅ Evaluation dataset created
- ✅ Baseline metrics captured
- ✅ Failure patterns identified
- ✅ Model improvement path planned

---

## Usage Patterns

### Longitudinal Tracking

**Goal**: Measure how code-chef improves over time

```python
# LangSmith query
module:"feature_dev" AND environment:"production"
# Group by: extension_version
# Chart: Accuracy over time
```

**Example**: Compare accuracy from v1.0.0 → v1.2.3

### A/B Testing

**Goal**: Compare code-chef vs baseline on same tasks

**Step 1**: Run baseline

```bash
export EXPERIMENT_ID=exp-2025-01-001
export TRACE_ENVIRONMENT=evaluation
export EXPERIMENT_GROUP=baseline

python support/scripts/evaluation/baseline_runner.py \
    --mode baseline \
    --tasks support/scripts/evaluation/sample_tasks.json
```

**Step 2**: Run code-chef

```bash
export EXPERIMENT_GROUP=code-chef

python support/scripts/evaluation/baseline_runner.py \
    --mode code-chef \
    --tasks support/scripts/evaluation/sample_tasks.json
```

**Step 3**: Analyze in LangSmith

```python
# Query
experiment_id:"exp-2025-01-001"
# Split by: experiment_group
# Compare: accuracy, latency, cost
```

### Environment Isolation

**Production traces only**:

```python
environment:"production"
```

**Exclude test/training from production metrics**:

```python
environment:"production" NOT (environment:"test" OR environment:"training")
```

**Training operations**:

```python
module:"training" AND environment:"training"
```

---

## Implementation Details

### Decorator Pattern

All ModelOps functions use enhanced `@traceable` decorators:

```python
from langsmith import traceable

@traceable(
    name="modelops_train_model",
    project_name=_get_langsmith_project(),  # Auto-selects based on environment
    metadata=_get_training_trace_metadata(),  # Includes all schema fields
)
def train_model(...):
    pass
```

### Project Selection Logic

```python
def _get_langsmith_project() -> str:
    """Auto-select project based on TRACE_ENVIRONMENT."""
    environment = os.getenv("TRACE_ENVIRONMENT", "production")

    if environment == "training":
        return "code-chef-training"
    elif environment == "evaluation":
        if os.getenv("EXPERIMENT_ID"):
            return "code-chef-experiments"
        return "code-chef-evaluation"
    elif environment == "test":
        return "code-chef-test"
    else:  # production
        return "code-chef-production"
```

### Metadata Helpers

```python
def _get_trace_metadata() -> Dict[str, str]:
    """Generate metadata following schema."""
    return {
        "experiment_group": os.getenv("EXPERIMENT_GROUP", "code-chef"),
        "environment": os.getenv("TRACE_ENVIRONMENT", "production"),
        "module": "training",  # Or evaluation, deployment, etc.
        "extension_version": os.getenv("EXTENSION_VERSION", "1.0.0"),
        "model_version": os.getenv("MODEL_VERSION", "unknown"),
        "config_hash": _get_config_hash(),
        "experiment_id": os.getenv("EXPERIMENT_ID"),
        "task_id": os.getenv("TASK_ID"),
    }
```

---

## Architecture

```
┌──────────────────┐     Metadata      ┌──────────────────────┐
│  ModelOps        │────────────────────▶ LangSmith Projects   │
│  Training        │     + environment  │ • code-chef-training │
│  Evaluation      │     + module       │ • code-chef-eval     │
│  Deployment      │     + exp_group    │ • code-chef-prod     │
└──────────────────┘                    │ • code-chef-exp      │
                                        └──────────────────────┘
         │
         ▼
┌──────────────────┐
│  Tests           │     environment:   ┌──────────────────────┐
│  conftest.py     │────────────────────▶ code-chef-test       │
│  Sets env vars   │     "test"         │ (optional)           │
└──────────────────┘                    └──────────────────────┘
```

---

## Troubleshooting

### Traces not appearing

1. Check environment variables set: `LANGCHAIN_TRACING_V2=true`
2. Verify API key: `echo $LANGCHAIN_API_KEY`
3. Check project exists in LangSmith UI
4. Look for errors in logs: `grep "langsmith" <log-file>`

### Traces in wrong project

1. Check `TRACE_ENVIRONMENT` matches expected value
2. Verify project selection logic in `_get_langsmith_project()`
3. Ensure environment variables set before code execution

### Missing metadata

1. Verify metadata helper function called
2. Check environment variables for metadata fields
3. Look for None values in trace metadata

---

## Migration from Old Structure

**Date**: December 10, 2025  
**Actions taken**:

1. ✅ Deleted all traces from old agent-based projects
2. ✅ Created new purpose-based projects
3. ✅ Updated all `@traceable` decorators with metadata
4. ✅ Added helper functions for project selection
5. ✅ Updated conftest.py for test environment

**Benefits**:

- Clean slate for longitudinal tracking
- A/B testing infrastructure ready
- Environment isolation prevents contamination
- Cost tracking by environment
- Better query/filter capabilities

---

## Best Practices

1. **Always set TRACE_ENVIRONMENT** before operations
2. **Use experiment_id** for all A/B tests
3. **Include task_id** for multi-run correlations
4. **Update extension_version** on releases
5. **Set model_version** when training/deploying
6. **Use baseline_runner.py** for proper A/B testing
7. **Keep metadata schema current** (`config/observability/tracing-schema.yaml`)
8. **Annotate failures immediately** (correctness + note fields)
9. **Build datasets progressively** (aim for 100+ examples per category)
10. **Evaluate before changing code** (data-driven improvements)
11. **Test MCP awareness** (acronym recognition, tool listing)
12. **Validate Docker MCP Toolkit integration** (178+ tools accessible)

---

## References

- Schema: [`config/observability/tracing-schema.yaml`](../../config/observability/tracing-schema.yaml)
- Project Restructure: [`support/docs/procedures/langsmith-project-restructure.md`](../procedures/langsmith-project-restructure.md)
- Baseline Runner: [`support/scripts/evaluation/baseline_runner.py`](../../scripts/evaluation/baseline_runner.py)
- LangSmith Docs: https://docs.smith.langchain.com/

## @traceable Decorator Coverage

The following modules have explicit `@traceable` instrumentation for fine-grained observability:

### Core Modules

| Module                      | Decorators | Tags                         |
| --------------------------- | ---------- | ---------------------------- |
| `hitl_manager.py`           | 7          | `hitl`, `approval`, `linear` |
| `progressive_mcp_loader.py` | 5          | `mcp`, `tools`, `loading`    |
| `agent_memory.py`           | 5          | `memory`, `rag`, `insights`  |

### Workflow Files

| Module               | Decorators | Tags                                         |
| -------------------- | ---------- | -------------------------------------------- |
| `parallel_docs.py`   | 4          | `workflow`, `documentation`, `parallel`      |
| `pr_deployment.py`   | 4          | `workflow`, `pr`, `code-review`, `hitl`      |
| `self_healing.py`    | 4          | `workflow`, `self-healing`, `infrastructure` |
| `workflow_engine.py` | 5+         | `workflow`, `hitl`, `approval`               |

### Adding Custom Traces

```python
from langsmith import traceable

@traceable(name="my_custom_operation", tags=["custom", "agent"])
async def my_operation(input: str) -> str:
    # Your code here
    return result
```

## Debugging

### Check if tracing is enabled

```bash
# On droplet
docker exec deploy-orchestrator-1 printenv | grep -E "LANG(CHAIN|SMITH)"
```

### View traces

1. Open https://smith.langchain.com
2. Select project "agents"
3. Filter by timeframe or metadata

### Enable debug mode

```bash
export LANGCHAIN_VERBOSE=true
```

## Disabling Tracing

Temporarily disable without code changes:

```bash
export LANGCHAIN_TRACING_V2=false
```

## Deployment Notes

After changing tracing configuration:

```bash
# Must recreate containers (restart won't reload .env)
docker compose down && docker compose up -d
```

## Related Documentation

- [LangSmith Official Docs](https://docs.smith.langchain.com/)
- [LangGraph Tracing](https://docs.smith.langchain.com/old/tracing/faq/logging_and_viewing#logging-traces-from-langgraph)
- [Copilot Instructions - LangSmith Section](../../.github/copilot-instructions.md#langsmith-llm-tracing)
