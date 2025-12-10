# ModelOps HuggingFace Space Quick Start

## Space URL

https://appsmithery-code-chef-modelops-trainer.hf.space

## Deploy to HuggingFace

```bash
# 1. Create Space at https://huggingface.co/new-space
#    Name: code-chef-modelops-trainer
#    SDK: Gradio
#    Hardware: t4-small
#    Visibility: Private

# 2. Clone and push
git clone https://huggingface.co/spaces/appsmithery/code-chef-modelops-trainer
cd code-chef-modelops-trainer

# 3. Copy files from this directory
cp ../../../deploy/huggingface-spaces/modelops-trainer/app.py .
cp ../../../deploy/huggingface-spaces/modelops-trainer/requirements.txt .
cp ../../../deploy/huggingface-spaces/modelops-trainer/README.md .

# 4. Commit and push
git add .
git commit -m "Deploy ModelOps trainer"
git push

# 5. Configure secret in Space Settings
#    Add HF_TOKEN with write permissions
```

## Usage from Python

```python
import os
import requests
import base64

SPACE_URL = "https://appsmithery-code-chef-modelops-trainer.hf.space"

# Prepare dataset
csv_content = open("training_data.csv", "rb").read()
encoded_csv = base64.b64encode(csv_content).decode()

# Submit job
response = requests.post(
    f"{SPACE_URL}/train",
    json={
        "agent_name": "feature_dev",
        "base_model": "Qwen/Qwen2.5-Coder-7B",
        "dataset_csv": encoded_csv,
        "training_method": "sft",
        "demo_mode": True  # Start with demo
    }
)

job_id = response.json()["job_id"]
print(f"Job submitted: {job_id}")

# Monitor status
import time
while True:
    status = requests.get(f"{SPACE_URL}/status/{job_id}").json()
    print(f"Status: {status['status']}")

    if status["status"] in ["completed", "failed"]:
        break

    time.sleep(30)

if status["status"] == "completed":
    print(f"Model trained: {status['hub_repo']}")
    print(f"TensorBoard: {status['tensorboard_url']}")
```

## Usage from code-chef

Use the provided client:

```python
from deploy.huggingface_spaces.modelops_trainer.client_example import ModelOpsTrainerClient

client = ModelOpsTrainerClient(
    space_url=os.environ["MODELOPS_SPACE_URL"],
    hf_token=os.environ["MODELOPS_SPACE_TOKEN"]
)

# Submit job
result = client.submit_training_job(
    agent_name="feature_dev",
    base_model="Qwen/Qwen2.5-Coder-7B",
    dataset_csv_path="/tmp/training.csv",
    demo_mode=True
)

# Wait for completion with progress updates
final_status = client.wait_for_completion(
    job_id=result["job_id"],
    callback=lambda s: print(f"Progress: {s.get('progress_pct', 0)}%")
)

print(f"Model: {final_status['hub_repo']}")
```

## Endpoints

- `POST /train` - Submit training job
- `GET /status/{job_id}` - Get job status
- `GET /health` - Health check
- `GET /` - Gradio UI

## Dataset Format

CSV with two columns:

```csv
text,response
"Add JWT auth to Express API","<code implementation>"
"Fix memory leak in React","<debugging steps>"
```

## Cost

- **t4-small**: $0.75/hr (good for <3B models)
- **a10g-large**: $2.20/hr (for 3-7B models)
- **Demo run**: ~5 min, ~$0.50
- **Production run**: ~90 min, ~$3.50-$15

## Files

- `app.py` - Main application (FastAPI + Gradio)
- `requirements.txt` - Python dependencies
- `README.md` - Space documentation
- `client_example.py` - Python client for code-chef
- `DEPLOYMENT.md` - Detailed deployment guide
