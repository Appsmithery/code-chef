# Implementation Prompt: ModelOps Extension for Infra Agent

> **Linear Issue**: [CHEF-210 - Phase 8: ModelOps Extension for Infrastructure Agent](https://linear.app/dev-ops/issue/CHEF-210/phase-8-modelops-extension-for-infrastructure-agent)
>
> Sub-issues:
>
> - [CHEF-211 - Phase 1: Registry + Training MVP](https://linear.app/dev-ops/issue/CHEF-211)
> - [CHEF-212 - Phase 2: Evaluation Integration](https://linear.app/dev-ops/issue/CHEF-212)
> - [CHEF-213 - Phase 3: Deployment Automation](https://linear.app/dev-ops/issue/CHEF-213)
> - [CHEF-214 - Phase 4: UX Polish](https://linear.app/dev-ops/issue/CHEF-214)

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
  - Training requires `huggingface_hub` SDK or AutoTrain API
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
    training.py            # HuggingFace Hub API training (direct API, not MCP)
    evaluation.py          # LangSmith eval integration (uses existing evaluators.py)
    deployment.py          # Model deployment/routing (update models.yaml)
    registry.py            # Model version tracking (JSON + SQLite)
```

### 2. Core Tools to Implement

> **MCP + SDK Hybrid Approach**: 
> - Use HuggingFace MCP tools for **discovery and validation** (model_search, dataset_search, hub_repo_details)
> - Use `huggingface_hub` Python SDK for **training operations** (AutoTrain API)
> - Use `HUGGINGFACE_TOKEN` GitHub secret for authentication

#### Tool: `train_subagent_model`

**Purpose**: Launch HuggingFace fine-tuning job for a specific subagent

**Inputs**:

- `agent_name` (str): Which subagent (`feature_dev`, `code_review`, `cicd`, `documentation`, `infrastructure`)
- `dataset_id` (str): LangSmith dataset ID with training examples
- `base_model` (str): HF model repo (e.g., `Qwen/Qwen2.5-Coder-7B`)
- `training_method` (str): `sft`, `dpo`, or `orpo`
- `training_config` (dict): Optional overrides (learning_rate, epochs, lora_rank, etc.)

**Implementation** (MCP for discovery, SDK for training):

1. **MCP**: Use `model_search` to validate base model exists on HF Hub
2. **MCP**: Use `hub_repo_details` to get model config (architecture, size, license)
3. Pull dataset from LangSmith using existing `Client()` pattern from `support/tests/evaluation/run_evaluation.py`
4. Convert to HuggingFace datasets format with train/test split
5. Estimate training cost via HF AutoTrain API
6. Create training job config:
   - Auto-select GPU based on model size (A10G for <13B, H100 for larger)
   - Configure LoRA (rank=16-32) for parameter efficiency
   - Set up checkpointing to HF Hub under `appsmithery/code-chef-{agent_name}-{timestamp}`
7. **SDK**: Submit job via `huggingface_hub.HfApi()` or AutoTrain API
8. Return job ID and tracking URL

**Output**: `{ job_id, hub_repo, estimated_cost, status_url }`

#### Tool: `monitor_training_job`

**Purpose**: Check status and retrieve metrics for a training job

**Inputs**:

- `job_id` (str): HuggingFace training job ID

**Implementation** (uses `huggingface_hub` SDK):

1. Poll HF training API via `HfApi().get_training_job(job_id)`
2. Parse logs for training loss, eval metrics, checkpoint progress
3. If complete, verify model uploaded to Hub and get final metrics

**Output**: `{ status, progress_pct, current_loss, eta_minutes, hub_repo }`

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

### 3. Model Registry Schema

Create `config/models/registry.json`:

```json
{
  "feature_dev": {
    "current": {
      "version": "v1-baseline",
      "model": "qwen/qwen-2.5-coder-32b-instruct",
      "endpoint": "openrouter",
      "deployed_at": "2025-12-01T00:00:00Z"
    },
    "history": [
      {
        "version": "v2-finetuned",
        "model": "appsmithery/code-chef-feature-dev-20251209",
        "base_model": "Qwen/Qwen2.5-Coder-7B",
        "training_method": "sft",
        "training_dataset": "ls://feature-dev-examples-001",
        "eval_dataset": "ls://feature-dev-eval-001",
        "eval_scores": {
          "accuracy": 0.87,
          "baseline_improvement": "+12%",
          "avg_latency_ms": 1200,
          "cost_per_1k": 0.003
        },
        "trained_at": "2025-12-09T22:00:00Z",
        "hub_repo": "appsmithery/code-chef-feature-dev-20251209",
        "deployment_status": "canary_20pct"
      }
    ]
  },
  "code_review": { "current": {...}, "history": [] },
  "infrastructure": { "current": {...}, "history": [] },
  "cicd": { "current": {...}, "history": [] },
  "documentation": { "current": {...}, "history": [] }
}
```

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

Integrates with existing evaluation infrastructure in `support/tests/evaluation/`:

- **Dataset Format**: Expect LangSmith datasets with structure:

```json
{
  "inputs": { "task": "Add JWT auth to Express API" },
  "outputs": { "code": "...", "tests": "..." },
  "metadata": { "agent": "feature_dev", "success": true }
}
```

- **Existing Evaluators** (from `evaluators.py`):

  - `agent_routing_accuracy` - Correct agent selection
  - `token_efficiency` - Token usage optimization
  - `latency_threshold` - Response time validation
  - `workflow_completeness` - Task completion quality
  - `mcp_integration_quality` - Tool usage patterns
  - `risk_assessment_accuracy` - HITL trigger accuracy

- **Evaluation Runs**: Tag experiments with:

  - `agent: {agent_name}`
  - `model_version: {version}`
  - `experiment_type: baseline_vs_candidate`

- **Tracing**: All ModelOps actions use `@traceable` decorator for LangSmith visibility

### 6. HuggingFace Integration

#### MCP Tools Available (Discovery & Inference)

The HuggingFace MCP server provides these tools for model discovery and validation:

| Tool | Purpose | Use in ModelOps |
|------|---------|-----------------|
| `model_search` | Search HF Hub for models | Find base models for fine-tuning |
| `dataset_search` | Search HF Hub for datasets | Discover training datasets |
| `hub_repo_details` | Get model/dataset metadata | Validate model exists, get config |
| `space_search` | Find Spaces | Discover AutoTrain or evaluation Spaces |
| `dynamic_space` | Invoke Spaces | Run inference tests on fine-tuned models |
| `paper_search` | Search ML papers | Find training methodology references |
| `hf_doc_search/fetch` | Access documentation | Reference AutoTrain, TRL, PEFT docs |

#### Training via SDK + AutoTrain

For actual fine-tuning, use `huggingface_hub` SDK with AutoTrain:

```python
from huggingface_hub import HfApi, create_repo, upload_file
import os

# Auth from GitHub secret
api = HfApi(token=os.environ.get("HUGGINGFACE_TOKEN"))

# Upload training dataset
api.upload_file(
    path_or_fileobj="training_data.jsonl",
    path_in_repo="data/train.jsonl",
    repo_id="appsmithery/code-chef-feature-dev-training",
    repo_type="dataset"
)

# Create model repo for checkpoints
create_repo(
    repo_id="appsmithery/code-chef-feature-dev-v2",
    repo_type="model",
    private=True
)

# For training jobs, use HuggingFace AutoTrain or Spaces:
# - AutoTrain API: https://huggingface.co/docs/autotrain
# - Spaces with GPU: Deploy training script as a Space
# - TRL for RLHF/DPO: https://huggingface.co/docs/trl
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
  small: # < 3B params
    gpu_type: "a10g"
    num_gpus: 1
  medium: # 3B-13B
    gpu_type: "a10g"
    num_gpus: 2
  large: # > 13B
    gpu_type: "h100"
    num_gpus: 1

cost_estimates:
  a10g_per_hour: 1.10
  h100_per_hour: 4.50
  avg_training_hours: 2
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

### Phase 1: Registry + Training (MVP)

**Scope**: Core infrastructure for model versioning and HuggingFace training

- [ ] Create `config/models/registry.json` schema
- [ ] Implement `modelops/registry.py` with CRUD operations
- [ ] Implement `modelops/training.py` with HuggingFace Hub SDK integration
- [ ] Add `train_subagent_model` tool
- [ ] Add `monitor_training_job` tool
- [ ] Create `config/modelops/training_defaults.yaml`
- [ ] Add HuggingFace tokens to `config/env/.env.template`
- [ ] Unit tests for registry and training

**Estimated effort**: 3-4 days

### Phase 2: Evaluation Integration

**Scope**: LangSmith integration for model comparison

- [ ] Implement `modelops/evaluation.py` using existing `support/tests/evaluation/evaluators.py`
- [ ] Add `evaluate_model_vs_baseline` tool
- [ ] Create evaluation comparison report format
- [ ] Add experiment tagging (agent, model_version, experiment_type)
- [ ] Unit tests for evaluation workflow

**Estimated effort**: 2-3 days

### Phase 3: Deployment Automation

**Scope**: Automated config updates and canary deployments

- [ ] Implement `modelops/deployment.py`
- [ ] Add `deploy_model_to_agent` tool
- [ ] Implement `config/agents/models.yaml` update logic
- [ ] Add canary traffic split configuration
- [ ] Implement rollback procedure
- [ ] Add `list_agent_models` tool
- [ ] Unit tests for deployment

**Estimated effort**: 2-3 days

### Phase 4: UX Polish

**Scope**: VS Code extension commands and notifications

- [ ] Add ModelOps commands to `extensions/vscode-codechef/package.json`
- [ ] Implement `src/commands/modelops.ts` handlers
- [ ] Add progress notifications for training jobs
- [ ] Add cost estimation display
- [ ] Add model comparison UI
- [ ] Integration tests

**Estimated effort**: 2-3 days

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
3. If yes (found 150 examples): "I can fine-tune Qwen2.5-Coder-7B on 150 examples. Estimated cost: $3.50, time: 1.5 hours. Proceed?"
4. User confirms → submit HuggingFace training job
5. Monitor progress: "Training 45% complete, current loss: 0.42..."
6. On completion: "Training done! Evaluating against baseline..."
7. Run eval: "New model: 87% accuracy (+12%), 20% faster. Deploy?"
8. User confirms → update config, canary rollout
9. "Deployed to 20% of feature_dev requests. Monitor for 24 hours, then full rollout."
```

---

## Files to Create/Modify

**New files**:

| File                                                               | Description                  |
| ------------------------------------------------------------------ | ---------------------------- |
| `agent_orchestrator/agents/infrastructure/modelops/__init__.py`    | Module init                  |
| `agent_orchestrator/agents/infrastructure/modelops/coordinator.py` | Main routing logic           |
| `agent_orchestrator/agents/infrastructure/modelops/training.py`    | HuggingFace Hub SDK training |
| `agent_orchestrator/agents/infrastructure/modelops/evaluation.py`  | LangSmith eval integration   |
| `agent_orchestrator/agents/infrastructure/modelops/deployment.py`  | Model deployment logic       |
| `agent_orchestrator/agents/infrastructure/modelops/registry.py`    | Model version tracking       |
| `config/modelops/training_defaults.yaml`                           | Training hyperparameters     |
| `config/models/registry.json`                                      | Model version registry       |
| `support/tests/agents/infrastructure/modelops/test_*.py`           | Unit tests                   |

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

- **HuggingFace MCP Limitation**: HF MCP provides only inference tools. Training requires `huggingface_hub` Python SDK directly
- **Error Handling**: Training can fail (OOM, timeout, dataset issues) - implement retry logic with ErrorRecoveryEngine
- **Cost Controls**: Add budget limits and require HITL approval for jobs > $10
- **Model Size**: Start with 7B models; larger requires H100 and higher cost
- **Dataset Quality**: Validate LangSmith datasets have consistent format before training
- **Versioning**: Use semantic versioning (v1.0.0, v1.1.0-beta) in registry
