# Implementation Prompt: ModelOps Extension for Infra Agent

## Context

You are extending the code-chef orchestrator's Infra agent to handle fine-tuning workflows for specialized subagents (FeatureDev, CodeReview, CICD, Docs). The system already has:

- LangGraph-based orchestrator with supervisor pattern
- ~150 MCP tools including HuggingFace integration
- LangSmith for tracing and evaluation
- OpenRouter for model routing
- Docker-based deployment infrastructure

## Objective

Add ModelOps capabilities to the Infra agent that allow it to:

1. Trigger fine-tuning jobs on HuggingFace
2. Monitor training progress and manage model artifacts
3. Evaluate fine-tuned models against baselines using LangSmith
4. Update agent configurations to use new models via OpenRouter/HF endpoints
5. Track model versions, performance metrics, and deployment status

## Architecture Requirements

### 1. Agent Extension Structure

```

agents/
infra/
__init__.py
agent.py              \# Existing Infra agent
modelops/             \# NEW: ModelOps extension
__init__.py
coordinator.py      \# Main ModelOps logic
training.py         \# HF training workflow
evaluation.py       \# LangSmith eval integration
deployment.py       \# Model deployment/routing
registry.py         \# Model version tracking

```

### 2. Core Tools to Implement

#### Tool: `train_subagent_model`

**Purpose**: Launch HF fine-tuning job for a specific subagent

**Inputs**:

- `agent_name` (str): Which subagent (e.g., "feature_dev", "code_review")
- `dataset_id` (str): LangSmith dataset ID with training examples
- `base_model` (str): HF model repo (e.g., "Qwen/Qwen2.5-Coder-7B")
- `training_method` (str): "sft", "dpo", or "orpo"
- `training_config` (dict): Optional overrides (learning_rate, epochs, lora_rank, etc.)

**Implementation Steps**:

1. Validate agent exists and has LangSmith dataset access
2. Pull dataset from LangSmith and convert to HF format (train/test split)
3. Estimate training cost via HF Jobs API
4. Create training job config:
   - Auto-select GPU based on model size (A10G for <13B, H100 for larger)
   - Configure LoRA (rank=16-32) for parameter efficiency
   - Set up checkpointing to HF Hub under `appsmithery/code-chef-{agent_name}-{timestamp}`
5. Submit job via HuggingFace MCP tools (`create_training_job` or equivalent)
6. Return job ID and tracking URL

**Output**: `{ job_id, hub_repo, estimated_cost, status_url }`

#### Tool: `monitor_training_job`

**Purpose**: Check status and retrieve metrics

**Inputs**:

- `job_id` (str): HF Jobs ID

**Implementation**:

1. Poll HF Jobs API via MCP tool (`get_job_status`)
2. Parse logs for training loss, eval metrics, checkpoint progress
3. If complete, verify model uploaded to Hub and get final metrics

**Output**: `{ status, progress_pct, current_loss, eta_minutes, hub_repo }`

#### Tool: `evaluate_model_vs_baseline`

**Purpose**: Compare fine-tuned model to current subagent baseline

**Inputs**:

- `agent_name` (str)
- `candidate_model` (str): HF repo path of fine-tuned model
- `eval_dataset_id` (str): LangSmith dataset (distinct from training)
- `metrics` (list[str]): e.g., ["accuracy", "latency", "cost_per_1k_tokens"]

**Implementation**:

1. Get current agent model config from registry
2. Set up LangSmith experiment with two runs:
   - Baseline: current model (via OpenRouter or HF inference endpoint)
   - Candidate: newly fine-tuned model (via HF inference endpoint)
3. Run both models on eval dataset, capture:
   - Task success rate
   - Output quality (via LLM-as-judge or deterministic metrics)
   - Latency (p50, p95)
   - Cost (tokens used \* model pricing)
4. Log full experiment to LangSmith with comparison tags

**Output**: `{ baseline_score, candidate_score, improvement_pct, recommendation, langsmith_experiment_url }`

#### Tool: `deploy_model_to_agent`

**Purpose**: Update agent config to use new model

**Inputs**:

- `agent_name` (str)
- `model_repo` (str): HF repo path
- `deployment_target` (str): "huggingface" or "openrouter"
- `rollout_strategy` (str): "immediate" or "canary_20pct"

**Implementation**:

1. If OpenRouter: Check if model is available via OpenRouter API, otherwise fallback to HF inference
2. Update agent model config (environment variable or config file):

```

agents:
feature_dev:
model: "appsmithery/code-chef-feature-dev-v2"
endpoint: "huggingface"  \# or "openrouter"
version: "v2-20251209"

```

3. If canary: Create traffic split config (80% old, 20% new) with LangSmith tagging
4. Trigger config reload (restart Docker service or hot-reload if supported)

**Output**: `{ deployed, endpoint_url, version, rollout_pct }`

#### Tool: `list_agent_models`

**Purpose**: Show model history and registry for a subagent

**Inputs**:

- `agent_name` (str)

**Implementation**:

1. Query model registry (SQLite DB or JSON file in `config/models/registry.json`)
2. Return list with: version, base_model, training_date, eval_scores, deployment_status

**Output**: List of model versions with metadata

### 3. Model Registry Schema

Create `config/models/registry.json`:

```

{
"feature_dev": {
"current": {
"version": "v1-baseline",
"model": "anthropic/claude-3.5-sonnet",
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
"code_review": { ... }
}

```

### 4. Infra Agent Integration

Extend `agents/infra/agent.py` to recognize ModelOps intents:

**New capabilities**:

- "Train a better model for [agent] using [dataset]"
- "Evaluate the new [agent] model"
- "Deploy the fine-tuned model to [agent]"
- "Show model history for [agent]"
- "Monitor training job [job_id]"

**Routing logic**:

```

if "train" in message and "model" in message:
delegate_to_modelops_coordinator()
elif "evaluate" in message and "model" in message:
delegate_to_evaluation()
elif "deploy" in message and "model" in message:
delegate_to_deployment()

```

### 5. LangSmith Integration Requirements

- **Dataset Format**: Expect LangSmith datasets with structure:

```

{
"inputs": { "task": "Add JWT auth to Express API" },
"outputs": { "code": "...", "tests": "..." },
"metadata": { "agent": "feature_dev", "success": true }
}

```

- **Evaluation Runs**: Tag experiments with:
- `agent: {agent_name}`
- `model_version: {version}`
- `experiment_type: baseline_vs_candidate`

- **Tracing**: Log all ModelOps actions (training start, eval runs, deployments) as LangSmith traces

### 6. HuggingFace MCP Tools to Use

Identify and use these MCP functions (adjust based on your actual HF MCP implementation):

- `hf_create_training_job(config)` - Submit training
- `hf_get_job_status(job_id)` - Poll progress
- `hf_upload_dataset(data, repo_id)` - Push training data
- `hf_create_inference_endpoint(model_repo)` - Deploy for eval
- `hf_get_model_info(repo_id)` - Check model metadata

### 7. Configuration Files

#### `config/modelops/training_defaults.yaml`

```

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
small: \# < 3B params
gpu_type: "a10g"
num_gpus: 1
medium: \# 3B-13B
gpu_type: "a10g"
num_gpus: 2
large: \# > 13B
gpu_type: "h100"
num_gpus: 1

cost_estimates:
a10g_per_hour: 1.10
h100_per_hour: 4.50
avg_training_hours: 2

```

#### `.env` additions

```


# ModelOps

HUGGINGFACE_HUB_TOKEN=hf_...
HUGGINGFACE_JOBS_ENABLED=true
MODELOPS_DEFAULT_BASE_MODEL=Qwen/Qwen2.5-Coder-7B
MODELOPS_HUB_ORG=appsmithery

```

### 8. User-Facing Commands (VS Code Extension)

Add commands to `extensions/vscode/package.json`:

```

{
"command": "code-chef.trainAgentModel",
"title": "Code Chef: Train Agent Model",
"category": "ModelOps"
},
{
"command": "code-chef.evaluateAgentModel",
"title": "Code Chef: Evaluate Agent Model"
},
{
"command": "code-chef.deployAgentModel",
"title": "Code Chef: Deploy Model to Agent"
}

```

Workflow example:

1. User runs "Train Agent Model"
2. Extension prompts:
   - Select agent: [FeatureDev, CodeReview, CICD, Docs]
   - Select LangSmith dataset (dropdown from user's datasets)
   - Confirm estimated cost
3. Extension calls orchestrator: `@chef Train feature_dev model using ls://dataset-123`
4. Infra agent delegates to ModelOps coordinator
5. Show progress notifications with HF Jobs URL
6. On completion, prompt: "Evaluate now?" → if yes, run eval tool
7. If eval shows improvement, prompt: "Deploy?" → if yes, run deploy tool

### 9. Testing Requirements

Create tests in `tests/agents/infra/modelops/`:

- `test_training_workflow.py`: Mock HF job submission and monitoring
- `test_evaluation.py`: Mock LangSmith dataset pull and comparison
- `test_deployment.py`: Verify config updates and rollback
- `test_registry.py`: Model version CRUD operations

### 10. Documentation to Add

Create `support/docs/MODELOPS.md`:

- When to fine-tune vs prompt engineering
- Step-by-step training workflow
- Cost estimation guide
- LangSmith dataset preparation
- Model evaluation best practices
- Rollback procedures

## Implementation Order

1. **Phase 1 (MVP)**: Registry + training tool

   - Set up model registry schema
   - Implement `train_subagent_model` with HF MCP
   - Add `monitor_training_job`

2. **Phase 2**: Evaluation integration

   - Implement `evaluate_model_vs_baseline` with LangSmith
   - Add experiment tracking and comparison

3. **Phase 3**: Deployment automation

   - Implement `deploy_model_to_agent`
   - Add config hot-reload
   - Support canary deployments

4. **Phase 4**: UX polish
   - VS Code extension commands
   - Progress notifications
   - Cost tracking dashboard

## Success Criteria

- Can train a 7B model for an agent in < 2 hours with < $5 cost
- Evaluation automatically compares quality, latency, cost
- Deployment updates agent config with zero manual file editing
- Full audit trail in LangSmith and model registry
- Rollback to previous model in < 60 seconds

## Example User Flow

```

User: "@chef The FeatureDev agent keeps missing error handling. Train it better."

Orchestrator → Infra Agent → ModelOps Coordinator:

1. Check if LangSmith dataset exists for FeatureDev error-handling examples
2. If not, prompt user: "I need training examples. Run '@chef collect feature-dev failures' first?"
3. If yes (found 150 examples): "I can fine-tune Qwen2.5-Coder-7B on 150 examples. Estimated cost: \$3.50, time: 1.5 hours. Proceed?"
4. User confirms → submit HF training job
5. Monitor progress: "Training 45% complete, current loss: 0.42..."
6. On completion: "Training done! Evaluating against baseline..."
7. Run eval: "New model: 87% accuracy (+12%), 20% faster. Deploy?"
8. User confirms → update config, canary rollout
9. "Deployed to 20% of FeatureDev requests. Monitor for 24 hours, then full rollout."
```

## Files to Create/Modify

**New files**:

- `agents/infra/modelops/coordinator.py`
- `agents/infra/modelops/training.py`
- `agents/infra/modelops/evaluation.py`
- `agents/infra/modelops/deployment.py`
- `agents/infra/modelops/registry.py`
- `config/modelops/training_defaults.yaml`
- `config/models/registry.json`
- `support/docs/MODELOPS.md`
- `tests/agents/infra/modelops/test_*.py`

**Modified files**:

- `agents/infra/agent.py` - Add ModelOps routing
- `config/env/.env.template` - Add HF tokens
- `extensions/vscode/package.json` - Add commands
- `extensions/vscode/src/commands/modelops.ts` - New command handlers
- `deploy/docker-compose.yml` - Mount model registry volume

## Notes for Implementation

- **HF MCP Discovery**: First task is to list available HF MCP tools with `mcp list huggingface` or equivalent and map to the functions above
- **Error Handling**: Training can fail (OOM, timeout, dataset issues) - implement retry logic and clear error messages
- **Cost Controls**: Add budget limits and require explicit approval for jobs > $10
- **Model Size**: Start with 7B models; larger requires H100 and higher cost
- **Dataset Quality**: Bad training data = bad model. Validate LangSmith datasets have consistent format and quality
- **Versioning**: Use semantic versioning for models (v1.0.0, v1.1.0-beta)

```

```
