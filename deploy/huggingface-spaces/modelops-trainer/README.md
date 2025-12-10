---
title: code-chef ModelOps Trainer
emoji: 🏗️
colorFrom: blue
colorTo: purple
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: apache-2.0
duplicated_from: appsmithery/code-chef-modelops-trainer
hardware: t4-small
---

# code-chef ModelOps Trainer

AutoTrain-powered fine-tuning service for code-chef agents.

## Features

- **AutoTrain Integration**: Simplified model training with auto-configuration
- **REST API**: Submit and monitor training jobs programmatically
- **Web UI**: Gradio interface for manual testing
- **Multi-Method Support**: SFT, DPO, and Reward Modeling
- **Demo Mode**: Quick validation runs (100 examples, 1 epoch)
- **Production Mode**: Full training runs with optimal settings

## API Endpoints

### POST /train

Submit a new training job

**Request Body**:

```json
{
  "agent_name": "feature_dev",
  "base_model": "Qwen/Qwen2.5-Coder-7B",
  "dataset_csv": "<base64-encoded-csv-or-hf-dataset-id>",
  "training_method": "sft",
  "demo_mode": false,
  "config_overrides": {
    "learning_rate": 2e-5,
    "num_train_epochs": 3
  }
}
```

**Response**:

```json
{
  "job_id": "job_20251210_123456_feature_dev",
  "status": "pending",
  "message": "Training job submitted successfully"
}
```

### GET /status/{job_id}

Get training job status

**Response**:

```json
{
  "job_id": "job_20251210_123456_feature_dev",
  "status": "running",
  "progress_pct": 45.0,
  "current_step": 850,
  "total_steps": 1200,
  "current_loss": 1.23,
  "hub_repo": "appsmithery/code-chef-feature-dev-20251210-123456",
  "tensorboard_url": "https://tensorboard.dev/experiment/xyz"
}
```

### GET /health

Health check

**Response**:

```json
{
  "status": "healthy",
  "service": "code-chef-modelops-trainer",
  "autotrain_available": true,
  "hf_token_configured": true
}
```

## Environment Variables

Set these in Space Settings > Variables and secrets:

- `HF_TOKEN` or `HUGGINGFACE_TOKEN`: HuggingFace write access token (required)

## Dataset Format

CSV with two columns:

- `text`: Input prompt/instruction
- `response`: Expected output

Example:

```csv
text,response
"Add JWT auth to Express API","const jwt = require('jsonwebtoken');\n..."
"Fix memory leak in React","Use useEffect cleanup function:\n..."
```

## Usage from code-chef

```python
import requests
import base64

# Prepare dataset
csv_content = dataset.to_csv(index=False).encode()
encoded_csv = base64.b64encode(csv_content).decode()

# Submit training job
response = requests.post(
    "https://appsmithery-code-chef-modelops-trainer.hf.space/train",
    json={
        "agent_name": "feature_dev",
        "base_model": "Qwen/Qwen2.5-Coder-7B",
        "dataset_csv": encoded_csv,
        "training_method": "sft",
        "demo_mode": False
    }
)

job_id = response.json()["job_id"]

# Monitor status
status_response = requests.get(
    f"https://appsmithery-code-chef-modelops-trainer.hf.space/status/{job_id}"
)
print(status_response.json())
```

## Hardware

Default: `t4-small` GPU (good for models up to 3B)

Upgrade to `a10g-large` for 3-7B models via Space Settings.

## Cost Estimates

- **Demo run**: 100 examples, 1 epoch, ~5 minutes, ~$0.50
- **Production run**: Full dataset, 3 epochs, ~90 minutes, ~$3.50-$15

## License

Apache 2.0

## Related

- [code-chef GitHub](https://github.com/Appsmithery/Dev-Tools)
- [AutoTrain Advanced](https://github.com/huggingface/autotrain-advanced)
- [Linear Roadmap](https://linear.app/dev-ops/project/chef-210)
