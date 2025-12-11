# LangSmith Project Restructuring Guide

## Purpose

Transition from per-agent projects to purpose-driven projects that better support:

- Longitudinal tracking (measuring improvement over time)
- A/B testing (comparing code-chef vs baseline)
- Environment isolation (separating production from training/evaluation/testing)

## Date

December 10, 2025

---

## Old Structure (Agent-Based)

**Problems:**

- Mixed production, training, and evaluation traces
- Difficult to compare baseline vs code-chef
- No clean way to track improvement over time
- Test traces contaminating production metrics

**Projects:**

- `code-chef-feature-dev`
- `code-chef-code-review`
- `code-chef-infrastructure`
- `code-chef-cicd`
- `code-chef-documentation`
- `code-chef-supervisor`

**Status:** These projects should be archived or deleted after trace cleanup.

---

## New Structure (Purpose-Based)

### 1. code-chef-production

**Purpose:** All live extension usage  
**Trace Filter:** `environment:"production"`  
**Description:**

```
Production traces from the code-chef VS Code extension.
Established: December 10, 2025
Contains: Live user interactions with all agents
Excludes: Training, evaluation, and test runs
```

**Use Cases:**

- Monitor production performance
- Track user experience metrics
- Identify production issues
- Measure real-world accuracy

**Key Metadata:**

- `environment: production`
- `module: {agent_name}`
- `extension_version: {version}`
- `experiment_group: code-chef`

---

### 2. code-chef-experiments

**Purpose:** A/B test comparisons (baseline vs code-chef)  
**Trace Filter:** `experiment_id IS NOT NULL`  
**Description:**

```
A/B testing traces comparing code-chef against baseline.
Established: December 10, 2025
Contains: Paired baseline and code-chef runs on identical tasks
Purpose: Measure improvement over baseline LLM
```

**Use Cases:**

- Compare code-chef vs baseline performance
- Measure improvement from enhancements
- Validate training effectiveness
- Support hypothesis testing

**Key Metadata:**

- `experiment_id: exp-YYYY-MM-NNN`
- `task_id: task-{uuid}` (same for baseline and code-chef)
- `experiment_group: baseline | code-chef`
- `environment: evaluation`

**Workflow:**

1. Run baseline version of task → traces to this project with `experiment_group: baseline`
2. Run code-chef version of same task → traces to this project with `experiment_group: code-chef`
3. Correlate using `task_id`
4. Compare metrics side-by-side

---

### 3. code-chef-training

**Purpose:** Model training operations  
**Trace Filter:** `module:"training"`  
**Description:**

```
Model training traces from ModelOps workflows.
Established: December 10, 2025
Contains: AutoTrain jobs, training monitoring, cost tracking
Excludes: Evaluation and deployment operations
```

**Use Cases:**

- Monitor training job progress
- Track training costs
- Debug training failures
- Optimize training parameters

**Key Metadata:**

- `environment: training`
- `module: training`
- `model_version: {model-name}-{version}`
- `cost: {USD}`

**Typical Traces:**

- `modelops_train_model` - Main training invocation
- `modelops_validate_training_config` - Pre-flight validation
- `modelops_estimate_cost` - Cost estimation
- `modelops_submit_job` - Job submission to HuggingFace
- `modelops_get_training_status` - Status polling
- `modelops_health_check` - Space health checks

---

### 4. code-chef-evaluation

**Purpose:** Model evaluation and comparison runs  
**Trace Filter:** `module:"evaluation"`  
**Description:**

```
Model evaluation traces from ModelOps workflows.
Established: December 10, 2025
Contains: LangSmith evaluations, model comparisons, recommendation generation
Excludes: Production usage and training operations
```

**Use Cases:**

- Compare models before deployment
- Generate deployment recommendations
- Track evaluation metrics over time
- Debug evaluation failures

**Key Metadata:**

- `environment: evaluation`
- `module: evaluation`
- `model_version: {model-name}-{version}`
- `experiment_group: code-chef` (or `baseline` if applicable)

**Typical Traces:**

- `modelops_evaluate_models` - Main evaluation invocation
- `modelops_compare_models` - Side-by-side comparison
- `modelops_run_evaluation_suite` - Full test suite
- `modelops_generate_comparison_report` - Report generation

---

## Migration Steps

### Phase 1: Create New Projects (Manual in LangSmith UI)

1. Navigate to https://smith.langchain.com
2. Create each new project:
   - `code-chef-production`
   - `code-chef-experiments`
   - `code-chef-training`
   - `code-chef-evaluation`
3. Set project descriptions as documented above
4. Set appropriate access controls

### Phase 2: Update Code (Automated)

Update all `@traceable` decorators to include new metadata:

- See Steps 3-6 of Phase 5 implementation plan
- Update training.py, evaluation.py, deployment.py, registry.py, coordinator.py
- Add environment, module, experiment_group tags

### Phase 3: Update Configuration

Update environment variables:

```bash
# In .env file
LANGSMITH_PROJECT_PRODUCTION=code-chef-production
LANGSMITH_PROJECT_EXPERIMENTS=code-chef-experiments
LANGSMITH_PROJECT_TRAINING=code-chef-training
LANGSMITH_PROJECT_EVALUATION=code-chef-evaluation
```

### Phase 4: Archive Old Projects (Manual)

After verifying new structure works:

1. Archive old agent-based projects
2. Keep for historical reference (30 days)
3. Update documentation to reference new structure

---

## Project Selection Logic

### In Code (Python)

```python
import os
from langsmith import traceable

def get_langsmith_project() -> str:
    """Determine which LangSmith project to use based on context."""
    environment = os.getenv("TRACE_ENVIRONMENT", "production")

    if environment == "training":
        return os.getenv("LANGSMITH_PROJECT_TRAINING", "code-chef-training")
    elif environment == "evaluation":
        # Check if this is an experiment
        if os.getenv("EXPERIMENT_ID"):
            return os.getenv("LANGSMITH_PROJECT_EXPERIMENTS", "code-chef-experiments")
        return os.getenv("LANGSMITH_PROJECT_EVALUATION", "code-chef-evaluation")
    elif environment == "test":
        return os.getenv("LANGSMITH_PROJECT", "code-chef-test")
    else:  # production
        return os.getenv("LANGSMITH_PROJECT_PRODUCTION", "code-chef-production")

# Usage
@traceable(
    project_name=get_langsmith_project(),
    metadata={
        "environment": os.getenv("TRACE_ENVIRONMENT", "production"),
        "module": "training",
        "experiment_group": "code-chef",
    }
)
def train_model(...):
    pass
```

### In Configuration

Set via environment variables before running operations:

```bash
# Training operation
export TRACE_ENVIRONMENT=training
python -m agent_orchestrator.agents.infrastructure.modelops.training

# Evaluation operation
export TRACE_ENVIRONMENT=evaluation
python -m agent_orchestrator.agents.infrastructure.modelops.evaluation

# A/B test
export TRACE_ENVIRONMENT=evaluation
export EXPERIMENT_ID=exp-2025-01-001
python support/scripts/evaluation/baseline_runner.py
```

---

## Verification Checklist

After migration:

- [ ] All 4 new projects created in LangSmith
- [ ] Project descriptions updated with establishment date
- [ ] Environment variables configured
- [ ] Code updated with new metadata
- [ ] First production trace appears in `code-chef-production`
- [ ] First training trace appears in `code-chef-training`
- [ ] First evaluation trace appears in `code-chef-evaluation`
- [ ] A/B test traces appear in `code-chef-experiments`
- [ ] Old projects archived or scheduled for deletion

---

## Benefits

### Before (Agent-Based)

- ❌ Mixed environments in same project
- ❌ Hard to track improvement over time
- ❌ No baseline comparison capability
- ❌ Test contamination of production metrics

### After (Purpose-Based)

- ✅ Clean environment isolation
- ✅ Longitudinal tracking via production project
- ✅ A/B testing via experiments project
- ✅ Separate training/evaluation/test traces
- ✅ Clear project selection logic
- ✅ Better cost attribution
