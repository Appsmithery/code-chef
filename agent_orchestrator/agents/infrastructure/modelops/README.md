# ModelOps Training Module

> **📘 Complete Documentation**: See [LLM Operations Guide](../../../../support/docs/operations/LLM_OPERATIONS.md) for the canonical reference covering model selection, training, evaluation, deployment, and A/B testing.

Fine-tune code-chef agents using LangSmith evaluation data and HuggingFace AutoTrain.

## Overview

The ModelOps module enables continuous improvement of code-chef agents by:

1. Exporting high-quality examples from LangSmith evaluations
2. Submitting fine-tuning jobs to HuggingFace Space (AutoTrain)
3. Monitoring training progress with TensorBoard
4. Deploying fine-tuned models back to agents

## Architecture

```
┌─────────────────┐
│   LangSmith     │ ← Evaluation runs with feedback scores
│   Projects      │
└────────┬────────┘
         │ Export CSV (text/response columns)
         ▼
┌─────────────────┐
│  ModelOps       │ ← agent_orchestrator/agents/infrastructure/modelops/
│  Trainer        │   training.py
└────────┬────────┘
         │ REST API call (POST /train)
         ▼
┌─────────────────┐
│  HuggingFace    │ ← HuggingFace Space (Gradio + FastAPI)
│  Space          │   deploy/huggingface-spaces/modelops-trainer/
└────────┬────────┘
         │ AutoTrain (GPU: t4-small or a10g-large)
         ▼
┌─────────────────┐
│  Fine-tuned     │ ← Deployed to HuggingFace Hub
│  Model          │   alextorelli/codechef-{agent}-{timestamp}
└─────────────────┘
```

## Quick Start

### 1. Deploy HuggingFace Space

See `deploy/huggingface-spaces/modelops-trainer/MANUAL_DEPLOY.md` for deployment instructions.

### 2. Configure Environment

```bash
# config/env/.env
HUGGINGFACE_TOKEN=hf_xxxxxxxxxxxxx
MODELOPS_SPACE_URL=https://alextorelli-code-chef-modelops-trainer.hf.space
MODELOPS_DEMO_MODE=true  # Set to false for production
```

### 3. Train a Model

```python
from agent_orchestrator.agents.infrastructure.modelops import ModelOpsTrainer

trainer = ModelOpsTrainer()

# Export data from LangSmith and train model
job = trainer.train_model(
    agent_name="feature_dev",
    langsmith_project="code-chef-feature-dev",
    base_model_preset="codellama-7b",
    is_demo=False  # Production mode
)

# Monitor training
final_status = trainer.monitor_training(job["job_id"])
print(f"Model: {final_status['model_id']}")
```

## Configuration

### Model Presets (`config/modelops/training_defaults.yaml`)

| Preset        | Model ID                            | Parameters | Hardware   | Cost/hr | Use Case                        |
| ------------- | ----------------------------------- | ---------- | ---------- | ------- | ------------------------------- |
| phi-3-mini    | microsoft/Phi-3-mini-4k-instruct    | 3.8B       | t4-small   | $0.75   | Code review, docs, CI/CD        |
| codellama-7b  | codellama/CodeLlama-7b-Instruct-hf  | 7B         | a10g-large | $2.20   | Feature dev, infrastructure     |
| codellama-13b | codellama/CodeLlama-13b-Instruct-hf | 13B        | a10g-large | $2.20   | Supervisor, complex refactoring |

### Training Modes

**Demo Mode** (Quick validation):

- 1 epoch, 10 steps max
- ~5 minutes, ~$0.50 cost
- Use for testing dataset quality

**Production Mode** (Full training):

- 3 epochs, auto-configured steps
- ~90 minutes, $3.50-$15 cost
- Use for deploying to agents

## Usage Examples

### Export LangSmith Data Only

```python
trainer = ModelOpsTrainer()

df = trainer.export_langsmith_data(
    project_name="code-chef-feature-dev",
    filter_criteria={"feedback_score": {"gte": 0.7}},
    limit=1000
)

print(f"Exported {len(df)} examples")
df.to_csv("training_data.csv", index=False)
```

### Submit Training Job with Custom Parameters

```python
from agent_orchestrator.agents.infrastructure.modelops.training import ModelOpsTrainerClient

client = ModelOpsTrainerClient()

# Load custom CSV
with open("training_data.csv") as f:
    csv_data = f.read()

# Submit with overrides
job = client.submit_training_job(
    csv_data=csv_data,
    base_model="microsoft/Phi-3-mini-4k-instruct",
    project_name="custom-training",
    is_demo=False,
    learning_rate=1e-4,  # Override default
    num_epochs=5,        # Override default
    batch_size=4         # Override auto-configured batch size
)

print(f"Job ID: {job['job_id']}")
```

### Monitor Training with Custom Callback

```python
client = ModelOpsTrainerClient()

def progress_callback(status):
    print(f"Status: {status['status']}")
    if "progress" in status:
        print(f"  Progress: {status['progress']}%")
    if "tensorboard_url" in status:
        print(f"  TensorBoard: {status['tensorboard_url']}")

final_status = client.wait_for_completion(
    job_id="job_xxx",
    poll_interval=30,
    callback=progress_callback
)
```

## Testing

```bash
# Health check only
python support/tests/integration/test_modelops_integration.py --health-only

# Demo training with synthetic data
python support/tests/integration/test_modelops_integration.py --demo

# Full integration test with LangSmith
python support/tests/integration/test_modelops_integration.py --full
```

## Cost Estimates

| Model         | Mode       | Duration | Hardware   | Cost   |
| ------------- | ---------- | -------- | ---------- | ------ |
| phi-3-mini    | Demo       | 5 min    | t4-small   | $0.50  |
| phi-3-mini    | Production | 90 min   | t4-small   | $3.50  |
| codellama-7b  | Demo       | 8 min    | a10g-large | $0.80  |
| codellama-7b  | Production | 120 min  | a10g-large | $10.00 |
| codellama-13b | Production | 180 min  | a10g-large | $15.00 |

## Safety Limits

Configured in `config/modelops/training_defaults.yaml`:

- **Max Cost**: $50 per job (abort if exceeded)
- **Max Duration**: 6 hours (abort if exceeded)
- **HITL Approval**: Required for jobs > $15

## Troubleshooting

### Space Health Check Fails

```bash
# Check Space status
curl https://alextorelli-code-chef-modelops-trainer.hf.space/health

# Common issues:
# - Space not deployed yet (see MANUAL_DEPLOY.md)
# - Space building (wait 2-3 minutes)
# - HF_TOKEN secret not configured in Space settings
```

### Training Job Fails

1. Check Space logs in HuggingFace UI
2. Verify dataset format (CSV with text/response columns)
3. Check model ID is valid on HuggingFace Hub
4. Ensure sufficient GPU memory for model size

### LangSmith Export Fails

1. Verify `LANGCHAIN_API_KEY` is set
2. Check project name exists in LangSmith
3. Ensure project has evaluation runs with inputs/outputs

## References

- **Spec**: `support/docs/extend Infra agent ModelOps.md`
- **Space Deployment**: `deploy/huggingface-spaces/modelops-trainer/MANUAL_DEPLOY.md`
- **Configuration**: `config/modelops/training_defaults.yaml`
- **Linear Issues**: CHEF-210 (parent), CHEF-211-214 (sub-issues)
- **AutoTrain Docs**: https://github.com/huggingface/autotrain-advanced
- **HF Skills Training**: https://huggingface.co/blog/hf-skills-training
