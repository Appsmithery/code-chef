# Implementation Prompt: ModelOps Extension for Infra Agent

> **Linear Issue**: [CHEF-210 - Phase 8: ModelOps Extension for Infrastructure Agent](https://linear.app/dev-ops/issue/CHEF-210/phase-8-modelops-extension-for-infrastructure-agent)
>
> Sub-issues:
>
> - [CHEF-211 - Phase 1: Registry + Training MVP](https://linear.app/dev-ops/issue/CHEF-211) ✅ **DONE**
> - [CHEF-212 - Phase 2: Evaluation Integration](https://linear.app/dev-ops/issue/CHEF-212) ✅ **DONE**
> - [CHEF-213 - Phase 3: Deployment Automation](https://linear.app/dev-ops/issue/CHEF-213) 🚧 **READY**
> - [CHEF-214 - Phase 4: UX Polish](https://linear.app/dev-ops/issue/CHEF-214) ⏳ **BLOCKED**

## Context

Extending the code-chef orchestrator's Infrastructure agent to handle fine-tuning workflows for specialized subagents (feature_dev, code_review, cicd, documentation). The system has:

- **LangGraph StateGraph** with supervisor pattern (`agent_orchestrator/graph.py`)
- **BaseAgent class** with progressive tool loading (`agents/_shared/base_agent.py`)
- **~178 MCP tools** across 20 servers (see `config/mcp-agent-tool-mapping.yaml`)
- **HuggingFace MCP** - Discovery and inference tools:
  - `model_search` - Find models on HF Hub
  - `dataset_search` - Find datasets on HF Hub
  - `hub_repo_details` - Get model/dataset metadata
  - `space_search` / `dynamic_space` - Search and invoke Spaces
  - `paper_search` - Search ML papers
  - `hf_doc_search` / `hf_doc_fetch` - Documentation access
  - Training uses **AutoTrain Advanced** for simplified fine-tuning
- **GitHub Secrets**: `HUGGINGFACE_TOKEN` configured for authentication
- **LangSmith evaluation** infrastructure (`support/tests/evaluation/`)
- **OpenRouter model routing** (`config/agents/models.yaml`)
- **Docker-based deployment** (`deploy/docker-compose.yml`)

## Current Agent Architecture Reference

```
agents/infrastructure/
  __init__.py          # InfrastructureAgent(BaseAgent)
  tools.yaml           # Progressive loading config, error recovery
  system.prompt.md     # Multi-cloud IaC, deployment rules
  workflows/           # (empty, for future workflow modules)
```

## Objective

Add ModelOps capabilities to the Infrastructure agent that allow it to:

1. **Trigger fine-tuning jobs** via HuggingFace Hub API (not MCP - no training MCP exists)
2. **Monitor training progress** and manage model artifacts on HuggingFace Hub
3. **Evaluate fine-tuned models** against baselines using existing LangSmith evaluation infrastructure
4. **Update agent configurations** to use new models via OpenRouter/HuggingFace endpoints
5. **Track model versions**, performance metrics, and deployment status in a registry

## Architecture Requirements

### 1. Agent Extension Structure

```
agent_orchestrator/agents/infrastructure/
  __init__.py              # Existing InfrastructureAgent class
  tools.yaml               # Add modelops tools config
  system.prompt.md         # Add ModelOps section
  modelops/                # NEW: ModelOps extension module
    __init__.py
    coordinator.py         # Main ModelOps orchestration logic
    training.py            # AutoTrain Advanced integration (simplified training)
    evaluation.py          # LangSmith eval integration (uses existing evaluators.py)
    deployment.py          # Model deployment/routing (update models.yaml)
    registry.py            # Model version tracking (JSON + SQLite)
```

### 2. Core Tools to Implement

> **MCP + AutoTrain Hybrid Approach**:
>
> - Use HuggingFace MCP tools for **discovery and validation** (model_search, dataset_search, hub_repo_details)
> - Use **AutoTrain Advanced** for **training operations** (auto-configured, simplified)
> - Use `HUGGINGFACE_TOKEN` GitHub secret for authentication

#### Tool: `train_subagent_model`

**Purpose**: Launch HuggingFace fine-tuning job for a specific subagent

**Inputs**:

- `agent_name` (str): Which subagent (`feature_dev`, `code_review`, `cicd`, `documentation`, `infrastructure`)
- `dataset_id` (str): LangSmith dataset ID with training examples
- `base_model` (str): HF model repo (e.g., `Qwen/Qwen2.5-Coder-7B`)
- `training_method` (str): `sft` (supervised fine-tuning), `dpo` (direct preference optimization), or `grpo` (group relative policy optimization for reasoning tasks)
- `training_config` (dict): Optional overrides (learning_rate, epochs, lora_rank, etc.)

**Implementation** (MCP for discovery, AutoTrain for training):

1. **MCP**: Use `model_search` to validate base model exists on HF Hub
2. **MCP**: Use `hub_repo_details` to get model config (architecture, size, license)
3. Pull dataset from LangSmith using existing `Client()` pattern from `support/tests/evaluation/run_evaluation.py`
4. Export to CSV format (AutoTrain auto-converts to required format):
   ```csv
   text,response
   "Add JWT auth to Express API","<code implementation>"
   "Fix memory leak in React","<debugging steps>"
   ```
5. **AutoTrain**: Submit training job with simplified config:

   ```python
   from autotrain.trainers.clm import train

   job = await train(
       project_name=f"code-chef-{agent_name}-{timestamp}",
       model=base_model,
       data_path=f"/tmp/{agent_name}_train.csv",
       text_column="text",
       target_column="response",
       push_to_hub=True,
       repo_id=f"appsmithery/code-chef-{agent_name}-v2",
       token=HF_TOKEN,
       auto_find_batch_size=True,  # Auto GPU/batch optimization
       use_peft=True,              # Auto LoRA for >3B models
       quantization="int4"         # Optional 4-bit training
   )
   ```

6. AutoTrain automatically:
   - Validates dataset format and suggests fixes
   - Selects optimal GPU (t4-small for <1B, a10g-large for 3-7B)
   - Configures LoRA/QLoRA for models >3B
   - Sets up TensorBoard monitoring
   - Handles checkpointing to HF Hub
7. Return job ID, Hub repo, TensorBoard URL, estimated cost/time

**Output**: `{ job_id, hub_repo, estimated_cost, status_url }`

#### Tool: `monitor_training_job`

**Purpose**: Check status and retrieve metrics for a training job

**Inputs**:

- `job_id` (str): HuggingFace training job ID

**Implementation** (uses AutoTrain API):

1. Query AutoTrain job status via `autotrain.job.status(job_id)`
2. Fetch TensorBoard metrics for real-time training loss, learning rate, validation
3. Parse job status: `pending`, `running`, `completed`, `failed`
4. Calculate progress from logs (AutoTrain provides step/total info)
5. If complete, verify model uploaded to Hub and get final metrics
6. If failed, extract AutoTrain error logs with built-in diagnostics

**Output**: `{ status, progress_pct, current_step, total_steps, current_loss, learning_rate, eta_minutes, hub_repo, tensorboard_url }`

#### Tool: `evaluate_model_vs_baseline`

**Purpose**: Compare fine-tuned model to current subagent baseline

**Inputs**:

- `agent_name` (str)
- `candidate_model` (str): HF repo path of fine-tuned model
- `eval_dataset_id` (str): LangSmith dataset ID (distinct from training)
- `metrics` (list[str]): e.g., `["accuracy", "latency", "cost_per_1k_tokens"]`

**Implementation** (integrates with existing `support/tests/evaluation/`):

1. Get current agent model config from `config/agents/models.yaml`
2. Set up LangSmith experiment using existing `evaluate()` pattern from `run_evaluation.py`
3. Run both models on eval dataset using existing evaluators:
   - `agent_routing_accuracy` - Task success rate
   - `token_efficiency` - Cost metrics
   - `latency_threshold` - Performance (p50, p95)
   - `workflow_completeness` - Output quality
4. Log full experiment to LangSmith with comparison tags (`model_version`, `experiment_type`)

**Output**: `{ baseline_score, candidate_score, improvement_pct, recommendation, langsmith_experiment_url }`

#### Tool: `deploy_model_to_agent`

**Purpose**: Update agent config to use new model

**Inputs**:

- `agent_name` (str)
- `model_repo` (str): HF repo path
- `deployment_target` (str): `huggingface` or `openrouter`
- `rollout_strategy` (str): `immediate` or `canary_20pct`

**Implementation**:

1. If OpenRouter: Check if model is available via OpenRouter API models list
2. Update `config/agents/models.yaml` under `openrouter.agent_models`:

```yaml
openrouter:
  agent_models:
    feature_dev: appsmithery/code-chef-feature-dev-v2 # Updated by ModelOps
```

3. Update model registry (`config/models/registry.json`) with deployment record
4. If canary: Create traffic split config (80% old, 20% new) with LangSmith tagging
5. Trigger container restart via `docker compose restart orchestrator` or hot-reload

**Output**: `{ deployed, endpoint_url, version, rollout_pct }`

#### Tool: `list_agent_models`

**Purpose**: Show model history and registry for a subagent

**Inputs**:

- `agent_name` (str)

**Implementation**:

1. Query model registry (`config/models/registry.json`)
2. Return list with: version, base_model, training_date, eval_scores, deployment_status

**Output**: List of model versions with metadata

#### Tool: `convert_model_to_gguf`

**Purpose**: Convert fine-tuned model to GGUF format for local deployment

**Inputs**:

- `model_repo` (str): HuggingFace repo path of fine-tuned model
- `quantization` (str): `Q4_K_M` (default), `Q5_K_M`, `Q8_0`, etc.
- `output_repo` (str): Target HF repo for GGUF model (e.g., `appsmithery/code-chef-feature-dev-gguf`)

**Implementation**:

1. Submit HF Jobs API conversion job:
   - Merge LoRA adapters if applicable
   - Convert to GGUF format using llama.cpp
   - Apply quantization (Q4_K_M = 4-bit, good balance of size/quality)
2. Push GGUF files to target repo on Hub
3. Generate usage instructions for llama.cpp, Ollama, LM Studio

**Output**: `{ job_id, output_repo, quantization, estimated_size_gb, usage_command }`

### 3. Model Registry Schema

✅ **IMPLEMENTED** - See `config/models/registry.json` and `agent_orchestrator/agents/infrastructure/modelops/registry.py`

**Registry Structure** (JSON with Pydantic validation):

```json
{
  "created_at": "2025-12-10T00:00:00Z",
  "updated_at": "2025-12-10T14:53:00Z",
  "version": "1.0.0",
  "agents": {
    "feature_dev": {
      "agent_name": "feature_dev",
      "current": {
        "version": "v1.0.0",
        "model_id": "microsoft/Phi-3-mini-4k-instruct",
        "training_config": {
          "base_model": "microsoft/Phi-3-mini-4k-instruct",
          "training_method": "sft",
          "training_dataset": "ls://feature-dev-train",
          "eval_dataset": "ls://feature-dev-eval",
          "learning_rate": 2e-4,
          "num_epochs": 3
        },
        "trained_at": "2025-12-09T22:00:00Z",
        "trained_by": "modelops-trainer",
        "job_id": "job_abc123",
        "hub_repo": "alextorelli/codechef-feature-dev-v1",
        "eval_scores": {
          "accuracy": 0.87,
          "baseline_improvement_pct": 12.0,
          "avg_latency_ms": 1200.0,
          "cost_per_1k_tokens": 0.003,
          "token_efficiency": 0.82,
          "workflow_completeness": 0.91,
          "langsmith_experiment_url": "https://smith.langchain.com/..."
        },
        "deployment_status": "deployed",
        "deployed_at": "2025-12-10T00:00:00Z"
      },
      "canary": null,
      "history": [...]
    }
  }
}
```

**Version Tracking Features** (Phase 2 Complete):

- ✅ Semantic versioning support (`v{major}.{minor}.{patch}-{suffix}`)
- ✅ Deployment lifecycle: `not_deployed` → `canary_20pct` → `canary_50pct` → `deployed` → `archived`
- ✅ Automatic backups (last 10 versions in `config/models/backups/`)
- ✅ Thread-safe operations with file locking
- ✅ Pydantic validation for all data structures
- ✅ Full CRUD operations (add, update, promote, rollback)

**Phase 3 Enhancements** (Planned):

- Auto-increment version generator
- Model ID naming convention validator
- Parent version tracking (lineage)
- Tag system for branches (production/experimental/security)
- Changelog field for release notes

### 4. Infrastructure Agent Integration

Extend `agent_orchestrator/agents/infrastructure/__init__.py` to delegate ModelOps intents:

**New capabilities** (add to `system.prompt.md`):

- "Train a better model for [agent] using [dataset]"
- "Evaluate the new [agent] model"
- "Deploy the fine-tuned model to [agent]"
- "Show model history for [agent]"
- "Monitor training job [job_id]"

**Delegation pattern** (in `modelops/coordinator.py`):

```python
from langsmith import traceable

@traceable(name="modelops_route")
async def route_modelops_request(message: str, context: dict) -> dict:
    """Route ModelOps requests to appropriate handler."""
    message_lower = message.lower()

    if "train" in message_lower and "model" in message_lower:
        return await training.train_subagent_model(context)
    elif "evaluate" in message_lower and "model" in message_lower:
        return await evaluation.evaluate_model_vs_baseline(context)
    elif "deploy" in message_lower and "model" in message_lower:
        return await deployment.deploy_model_to_agent(context)
    elif "list" in message_lower and "model" in message_lower:
        return await registry.list_agent_models(context)
    elif "monitor" in message_lower and "job" in message_lower:
        return await training.monitor_training_job(context)
    else:
        return {"error": "Unknown ModelOps intent", "message": message}
```

### 5. LangSmith Integration Requirements

✅ **IMPLEMENTED** - See `agent_orchestrator/agents/infrastructure/modelops/evaluation.py`

Integrates with existing evaluation infrastructure in `support/tests/evaluation/`:

- **Dataset Format**: Expect LangSmith datasets with structure:

```json
{
  "inputs": { "task": "Add JWT auth to Express API" },
  "outputs": { "code": "...", "tests": "..." },
  "metadata": { "agent": "feature_dev", "success": true }
}
```

- **Existing Evaluators** (from `evaluators.py`, integrated in Phase 2):

  - `agent_routing_accuracy` - Correct agent selection
  - `token_efficiency` - Token usage optimization
  - `latency_threshold` - Response time validation
  - `workflow_completeness` - Task completion quality
  - `mcp_integration_quality` - Tool usage patterns
  - `risk_assessment_accuracy` - HITL trigger accuracy

- **Weighted Scoring** (Phase 2 Implementation):

  - 30% accuracy
  - 25% workflow_completeness
  - 20% token_efficiency
  - 15% latency_threshold
  - 10% mcp_integration_quality

- **Recommendation Engine** (Phase 2):

  - **Deploy**: >15% improvement, no critical degradations
  - **Deploy Canary**: 5-15% improvement, needs validation
  - **Needs Review**: ±5% marginal change
  - **Reject**: <-5% regression OR >20% degradation OR quality <0.5

- **Evaluation Runs**: Tag experiments with:

  - `agent: {agent_name}`
  - `model_version: {version}`
  - `experiment_type: baseline_vs_candidate`

- **Tracing**: All ModelOps actions use `@traceable` decorator for LangSmith visibility

**Dataset Evolution Strategy**:

1. **Phase 1 (Current)**: Bootstrap with public HuggingFace datasets

   - `bigcode/the-stack-dedup` for code generation
   - Generic ML datasets for initial training
   - Establishes baseline performance

2. **Phase 2 (3-6 months)**: Hybrid approach

   - 80% public datasets + 20% LangSmith traces
   - Filter for: `success=True`, `feedback_score>=4.0`, `hitl_approved=True`
   - Capture workflow patterns, tool usage, multi-agent handoffs

3. **Phase 3 (6-12 months)**: Proprietary LangSmith datasets
   - 100% real code-chef workflow traces
   - 10,000+ examples per agent
   - Production-validated, domain-specific examples
   - Expected: +40-60% improvement over generic models

### 6. HuggingFace Integration

#### MCP Tools Available (Discovery & Inference)

The HuggingFace MCP server provides these tools for model discovery and validation:

| Tool                  | Purpose                    | Use in ModelOps                          |
| --------------------- | -------------------------- | ---------------------------------------- |
| `model_search`        | Search HF Hub for models   | Find base models for fine-tuning         |
| `dataset_search`      | Search HF Hub for datasets | Discover training datasets               |
| `hub_repo_details`    | Get model/dataset metadata | Validate model exists, get config        |
| `space_search`        | Find Spaces                | Discover AutoTrain or evaluation Spaces  |
| `dynamic_space`       | Invoke Spaces              | Run inference tests on fine-tuned models |
| `paper_search`        | Search ML papers           | Find training methodology references     |
| `hf_doc_search/fetch` | Access documentation       | Reference AutoTrain, TRL, PEFT docs      |

#### Training via SDK + AutoTrain

#### Training Methods Supported

1. **Supervised Fine-Tuning (SFT)**: Train on input-output demonstration pairs. Use when you have high-quality examples of desired behavior.

   - Dataset format: `messages` column with conversation format, or `prompt`/`completion` columns
   - Use case: Domain adaptation, style matching, instruction following

2. **Direct Preference Optimization (DPO)**: Train on preference pairs (chosen vs rejected). Use after SFT to align with human preferences.

   - Dataset format: `chosen` and `rejected` columns with preference pairs
   - Use case: Safety alignment, output quality improvement, tone/style preferences
   - Note: Sensitive to dataset format - must use exact column names

3. **Group Relative Policy Optimization (GRPO)**: Reinforcement learning for verifiable tasks. Model generates responses and receives rewards based on correctness.
   - Dataset format: `problem` and `solution` columns with programmatic success criteria
   - Use case: Math reasoning, code generation, any task with objective correctness metrics
   - Note: More complex than SFT/DPO, requires reward function implementation

#### Training via Jobs API

For actual fine-tuning, use HuggingFace Jobs API with TRL (Transformer Reinforcement Learning):

```python
from autotrain.trainers.clm import train as train_sft
from autotrain.trainers.dpo import train as train_dpo
from autotrain import AutoTrainConfig
import os

# Auth from GitHub secret
HF_TOKEN = os.environ.get("HUGGINGFACE_TOKEN")

# Export LangSmith dataset to CSV
dataset.to_csv("/tmp/training_data.csv", columns=["text", "response"])

# Configure AutoTrain (much simpler than Jobs API)
config = AutoTrainConfig(
    project_name="code-chef-feature-dev-v2",
    model="Qwen/Qwen2.5-Coder-7B",
    data_path="/tmp/training_data.csv",
    text_column="text",
    target_column="response",

    # AutoTrain handles these automatically:
    auto_find_batch_size=True,    # Optimal batch size for GPU
    use_peft=True,                 # LoRA auto-enabled for >3B
    quantization="int4",           # Optional 4-bit training

    # Output configuration
    push_to_hub=True,
    repo_id="appsmithery/code-chef-feature-dev-v2",
    token=HF_TOKEN,

    # Optional overrides (AutoTrain has smart defaults)
    learning_rate=2e-5,
    num_train_epochs=3,
    warmup_ratio=0.1
)

# Submit training (works locally OR on HF Spaces)
job = await train_sft(config)

# Monitor progress
status = job.status()
tensorboard_url = job.tensorboard_url

# Reference:
# - AutoTrain Advanced: https://github.com/huggingface/autotrain-advanced
# - AutoTrain Docs: https://huggingface.co/docs/autotrain
```

#### Using MCP Tools for Model Validation

After training, use HF MCP tools to validate the fine-tuned model:

```python
# Use model_search to find our fine-tuned model
model_info = await mcp_huggingface_hub_repo_details(
    repo_ids=["appsmithery/code-chef-feature-dev-v2"]
)

# Use dynamic_space to run inference tests
# (deploy model to a testing Space or use existing inference endpoints)
```

### 7. Configuration Files

#### `config/modelops/training_defaults.yaml`

```yaml
default_training_config:
  learning_rate: 2e-5
  num_epochs: 3
  batch_size: 4
  gradient_accumulation_steps: 4
  warmup_ratio: 0.1
  lora_rank: 32
  lora_alpha: 64
  target_modules: ["q_proj", "v_proj", "k_proj", "o_proj"]
  max_seq_length: 8192

gpu_selection:
  tiny: # < 1B params
    gpu_type: "t4-small"
    cost_per_hour: 0.75
    use_case: "Educational/experimental runs"
  small: # 1-3B params
    gpu_type: "t4-medium"
    cost_per_hour: 1.00
    use_case: "Small production models"
  medium: # 3-7B params
    gpu_type: "a10g-large"
    cost_per_hour: 2.20
    use_lora: true
    use_case: "Production with LoRA"
  large: # 7B+ params
    gpu_type: "not_supported"
    message: "Models >7B not suitable for HF Jobs API - use external training infrastructure"

training_estimates:
  demo_run: # 100 examples for testing
    time_minutes: 5
    cost_usd: 0.50
  production_run: # Full dataset, 3 epochs
    time_minutes: 90
    cost_usd: 15.00

validation_costs:
  dataset_validation_cpu: 0.02 # Pre-training format check
```

#### Environment Configuration

**GitHub Secrets** (already configured):

- `HUGGINGFACE_TOKEN` - HuggingFace Hub authentication

**Local environment** (`config/env/.env.template`):

```bash
# ModelOps - HuggingFace Training
HUGGINGFACE_HUB_TOKEN=hf_...
HUGGINGFACE_JOBS_ENABLED=true
MODELOPS_DEFAULT_BASE_MODEL=Qwen/Qwen2.5-Coder-7B
MODELOPS_HUB_ORG=appsmithery

# ModelOps - HuggingFace Space (Production)
MODELOPS_SPACE_URL=https://appsmithery-code-chef-modelops-trainer.hf.space
MODELOPS_SPACE_TOKEN=hf_...  # HF token with write permissions
MODELOPS_USE_SPACE=true  # Use Space API instead of local AutoTrain
```

### 8. User-Facing Commands (VS Code Extension)

Add commands to `extensions/vscode-codechef/package.json`:

```json
{
  "command": "codechef.trainAgentModel",
  "title": "Train Agent Model",
  "category": "code/chef ModelOps"
},
{
  "command": "codechef.evaluateAgentModel",
  "title": "Evaluate Agent Model",
  "category": "code/chef ModelOps"
},
{
  "command": "codechef.deployAgentModel",
  "title": "Deploy Model to Agent",
  "category": "code/chef ModelOps"
},
{
  "command": "codechef.listAgentModels",
  "title": "List Agent Models",
  "category": "code/chef ModelOps"
}
```

**Workflow example** (via @chef chat participant):

1. User: `@chef Train feature_dev model using recent production traces`
2. Infrastructure agent → ModelOps coordinator:
   - Validates LangSmith dataset exists for feature_dev
   - Estimates cost: "$3.50, ~1.5 hours on A10G"
   - Requests HITL approval if cost > $10
3. User confirms → submit HuggingFace training job
4. Progress notifications: "Training 45% complete, loss: 0.42..."
5. On completion: "Training done! Evaluating against baseline..."
6. Run evaluation: "New model: 87% accuracy (+12%), 20% faster"
7. Prompt: "Deploy to 20% canary?" → User confirms
8. Update `config/agents/models.yaml` + registry, restart orchestrator

### 9. Testing Requirements

Create tests in `support/tests/agents/infrastructure/modelops/`:

- `test_training_workflow.py`: Mock HuggingFace Hub API job submission and monitoring
- `test_evaluation.py`: Mock LangSmith dataset pull and comparison using existing evaluators
- `test_deployment.py`: Verify config updates and rollback
- `test_registry.py`: Model version CRUD operations

### 10. Documentation

Add ModelOps section to existing `support/docs/ARCHITECTURE.md` or create `support/docs/MODELOPS.md`:

- When to fine-tune vs prompt engineering
- Step-by-step training workflow
- Cost estimation guide
- LangSmith dataset preparation
- Model evaluation best practices
- Rollback procedures

---

## Implementation Phases (Linear Issues)

### Phase 1: Registry + Training (MVP) ✅ **COMPLETE**

**Status**: Done - 2025-12-10

**Delivered**:

- ✅ Created `config/models/registry.json` schema ([link](https://github.com/Appsmithery/Dev-Tools/blob/main/config/models/registry.json))
- ✅ Implemented `modelops/registry.py` with CRUD operations ([link](https://github.com/Appsmithery/Dev-Tools/blob/main/agent_orchestrator/agents/infrastructure/modelops/registry.py))
  - ModelRegistry class with thread-safe operations
  - Pydantic validation (TrainingConfig, EvaluationScores, ModelVersion)
  - Automatic backups (10-version history)
  - Version tracking: current, canary, archived states
  - Rollback and promotion operations
- ✅ Implemented `modelops/training.py` with AutoTrain integration ([link](https://github.com/Appsmithery/Dev-Tools/blob/main/agent_orchestrator/agents/infrastructure/modelops/training.py))
  - ModelOpsTrainerClient for Space API
  - ModelOpsTrainer for end-to-end orchestration
  - LangSmith to CSV export
  - Demo vs Production modes
- ✅ Created `config/modelops/training_defaults.yaml` ([link](https://github.com/Appsmithery/Dev-Tools/blob/main/config/modelops/training_defaults.yaml))
  - Model presets (phi-3-mini, codellama-7b, codellama-13b)
  - Training mode defaults
  - GPU/cost estimates
- ✅ HuggingFace Space deployed at `alextorelli/code-chef-modelops-trainer`
  - REST API: `/health`, `/train`, `/status/:job_id`
  - Healthy and responsive
  - AutoTrain integration working
- ✅ Integration tests created ([link](https://github.com/Appsmithery/Dev-Tools/blob/main/support/tests/integration/test_modelops_integration.py))
  - Health check, demo training, full integration tests
- ✅ Comprehensive README documentation ([link](https://github.com/Appsmithery/Dev-Tools/blob/main/agent_orchestrator/agents/infrastructure/modelops/README.md))

**Items Deferred to Phase 2**: Registry and agent integration (better designed with evaluation context)

**Actual effort**: 2 days

### Phase 2: Evaluation Integration ✅ **COMPLETE**

**Status**: Done - 2025-12-10

**Delivered**:

- ✅ Implemented `modelops/evaluation.py` ([link](https://github.com/Appsmithery/Dev-Tools/blob/main/agent_orchestrator/agents/infrastructure/modelops/evaluation.py))
  - ModelEvaluator class integrating with existing evaluators
  - `compare_models()` for baseline vs candidate comparison
  - Weighted improvement calculation (30% accuracy, 25% completeness, 20% efficiency, 15% latency, 10% integration)
  - Automatic recommendation generation (deploy, deploy_canary, reject, needs_review)
  - Markdown comparison report generation
  - LangSmith experiment tracking
- ✅ Registry implementation from Phase 1 moved here
  - Better designed with evaluation context
  - Full version history tracking
  - Deployment status management
- ✅ Unit tests for registry ([link](https://github.com/Appsmithery/Dev-Tools/blob/main/support/tests/agents/infrastructure/modelops/test_registry.py))
  - 15 tests covering CRUD operations, validation, backup
  - All passing ✅
- ✅ Unit tests for evaluation ([link](https://github.com/Appsmithery/Dev-Tools/blob/main/support/tests/agents/infrastructure/modelops/test_evaluation.py))
  - 12 tests covering comparison, recommendation, reports
  - All passing ✅
- ✅ Updated `modelops/__init__.py` to export new classes

**Test Results**: 27/27 tests passing

**Key Features**:

- Weighted scoring with configurable thresholds
- Smart recommendation engine based on improvement percentage
- Cached evaluation scores to avoid redundant runs
- Full comparison reports in markdown format

**Actual effort**: 2 days

### Phase 3: Deployment Automation 🚧 **IN PROGRESS**

**Status**: Ready to start - Dependencies satisfied

**Dependencies**:

- ✅ Phase 1: Training infrastructure (DONE)
- ✅ Phase 2: Registry + Evaluation (DONE)

**Updated Scope** (includes items deferred from Phase 1):

**Infrastructure Agent Integration:**

- [ ] Update `agents/infrastructure/__init__.py` to route ModelOps intents
- [ ] Add ModelOps tools to `agents/infrastructure/tools.yaml`
- [ ] Update `agents/infrastructure/system.prompt.md` with ModelOps capabilities

**Deployment Module:**

- [ ] Create `modelops/deployment.py`
- [ ] Implement `deploy_model_to_agent` tool with registry integration
- [ ] Implement `config/agents/models.yaml` update logic
- [ ] Add canary traffic split configuration (20% → 50% → 100%)
- [ ] Implement rollback procedure (<60 seconds)
- [ ] Add `list_agent_models` tool
- [ ] Add version auto-increment generator
- [ ] Add model ID naming convention validator

**Testing:**

- [ ] Unit tests for deployment operations
- [ ] Integration tests for end-to-end workflow (train → evaluate → deploy → rollback)

**Deployment Targets**:

1. OpenRouter - Check model availability via API
2. HuggingFace Inference Endpoints - Direct model hosting
3. Self-hosted endpoints - Custom deployments

**Canary Strategy**:

1. Deploy candidate to 20% of traffic
2. Monitor for 24-48 hours
3. Compare metrics vs baseline in production
4. Promote to 50%, then 100% if successful
5. Rollback immediately if degradation detected

**Success Criteria**:

- Infrastructure agent routes ModelOps requests
- Models deployed via single command
- Canary deployments functional with traffic split
- Rollback works in <60 seconds
- Full integration tests passing

**Estimated effort**: 3-4 days (increased from 2-3 days due to agent integration)

### Phase 4: UX Polish + GGUF Support

**Scope**: VS Code extension commands, notifications, and local deployment

- [ ] Add ModelOps commands to `extensions/vscode-codechef/package.json`
- [ ] Implement `src/commands/modelops.ts` handlers
- [ ] Add progress notifications for training jobs with Trackio links
- [ ] Add cost estimation display (demo vs production)
- [ ] Add model comparison UI with evaluation results
- [ ] Implement `convert_model_to_gguf` tool for local deployment
- [ ] Add usage instructions for llama.cpp, Ollama, LM Studio
- [ ] Integration tests

**Estimated effort**: 3-4 days

---

## Success Criteria

- Can train a 7B model for an agent in < 2 hours with < $5 cost
- Evaluation automatically compares quality, latency, cost using existing evaluators
- Deployment updates `config/agents/models.yaml` with zero manual file editing
- Full audit trail in LangSmith and model registry
- Rollback to previous model in < 60 seconds

## Example User Flow

```
User: "@chef The feature_dev agent keeps missing error handling. Train it better."

Orchestrator → Infrastructure Agent → ModelOps Coordinator:

1. Check if LangSmith dataset exists for feature_dev error-handling examples
2. If not, prompt user: "I need training examples. Run '@chef collect feature-dev failures' first?"
3. If yes (found 150 examples): Export to CSV format (text, response columns)
4. AutoTrain validates: "✓ Dataset ready. 150 examples, CSV format valid."
5. Estimate costs: "Demo run (100 examples): $0.50, 5 minutes | Production: $3.50, 90 minutes"
6. Recommend: "Should I run a demo first to verify the pipeline?"
7. User confirms demo → AutoTrain submits demo job (auto-selects t4-small, configures LoRA)
8. Demo completes: "Demo successful! Loss: 2.41 → 1.23. Ready for production?"
9. User confirms production → AutoTrain submits full training (auto-optimizes everything)
10. Monitor via TensorBoard: "Training 45% complete (step 850/1200), loss: 1.23, ETA: 20 min"
11. On completion: "Training done! Model pushed to appsmithery/code-chef-feature-dev-v2. Evaluating..."
12. Run eval: "New model: 87% accuracy (+12%), 20% faster, $0.003/1k tokens. Deploy?"
13. User confirms → update config, canary rollout
14. "Deployed to 20% of feature_dev requests. Monitor for 24h, then full rollout?"
```

---

## Files to Create/Modify

**New files**:

| File                                                               | Description                    |
| ------------------------------------------------------------------ | ------------------------------ |
| `agent_orchestrator/agents/infrastructure/modelops/__init__.py`    | Module init                    |
| `agent_orchestrator/agents/infrastructure/modelops/coordinator.py` | Main routing logic             |
| `agent_orchestrator/agents/infrastructure/modelops/training.py`    | AutoTrain Advanced integration |
| `agent_orchestrator/agents/infrastructure/modelops/evaluation.py`  | LangSmith eval integration     |
| `agent_orchestrator/agents/infrastructure/modelops/deployment.py`  | Model deployment logic         |
| `agent_orchestrator/agents/infrastructure/modelops/registry.py`    | Model version tracking         |
| `config/modelops/training_defaults.yaml`                           | Training hyperparameters       |
| `config/models/registry.json`                                      | Model version registry         |
| `support/tests/agents/infrastructure/modelops/test_*.py`           | Unit tests                     |

**Modified files**:

| File                                                        | Changes                      |
| ----------------------------------------------------------- | ---------------------------- |
| `agent_orchestrator/agents/infrastructure/__init__.py`      | Add ModelOps intent routing  |
| `agent_orchestrator/agents/infrastructure/tools.yaml`       | Add ModelOps allowed servers |
| `agent_orchestrator/agents/infrastructure/system.prompt.md` | Add ModelOps capabilities    |
| `config/env/.env.template`                                  | Add HuggingFace tokens       |
| `extensions/vscode-codechef/package.json`                   | Add ModelOps commands        |
| `deploy/docker-compose.yml`                                 | Mount model registry volume  |

---

## Implementation Notes

- **AutoTrain Advantages**: Simplified API, auto dataset validation, auto GPU selection, auto LoRA config, built-in monitoring
- **HuggingFace MCP**: Use only for model discovery and validation - AutoTrain handles all training
- **Dataset Format**: AutoTrain accepts CSV with `text`/`response` columns - simpler than HF datasets format
- **Error Handling**: AutoTrain provides built-in retry logic and diagnostic errors - less custom code needed
- **Local Development**: Can run AutoTrain locally for testing, then deploy to HF Spaces for production
- **Cost Controls**: Add budget limits and require HITL approval for jobs > $10
- **Model Size**: AutoTrain supports <1B to 70B models (auto-selects appropriate GPU)
- **Versioning**: Use semantic versioning (v1.0.0, v1.1.0-beta) in registry
