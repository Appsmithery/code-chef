#!/usr/bin/env python3
"""
HuggingFace Space: code-chef ModelOps Training Service
Provides REST API endpoint for AutoTrain-based model fine-tuning
"""

import asyncio
import base64
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import gradio as gr
from fastapi import FastAPI, HTTPException
from huggingface_hub import HfApi
from pydantic import BaseModel

# Environment setup
HF_TOKEN = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
if not HF_TOKEN:
    raise ValueError("HF_TOKEN environment variable required")

api = HfApi(token=HF_TOKEN)

# Job tracking
JOBS_DIR = Path("/tmp/modelops_jobs")
JOBS_DIR.mkdir(exist_ok=True)


class TrainingRequest(BaseModel):
    """Training job request schema"""

    agent_name: str
    base_model: str
    dataset_csv: str  # Base64 encoded CSV or HF dataset ID
    training_method: str = "sft"  # sft, dpo, reward
    demo_mode: bool = False
    config_overrides: Optional[Dict[str, Any]] = None


class JobStatus(BaseModel):
    """Training job status response"""

    job_id: str
    status: str  # pending, running, completed, failed
    progress_pct: Optional[float] = None
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    current_loss: Optional[float] = None
    hub_repo: Optional[str] = None
    tensorboard_url: Optional[str] = None
    error: Optional[str] = None


# FastAPI app
app = FastAPI(title="code-chef ModelOps Trainer")


def save_job_metadata(job_id: str, metadata: dict):
    """Save job metadata to disk"""
    job_file = JOBS_DIR / f"{job_id}.json"
    with open(job_file, "w") as f:
        json.dump(metadata, f, indent=2)


def load_job_metadata(job_id: str) -> Optional[dict]:
    """Load job metadata from disk"""
    job_file = JOBS_DIR / f"{job_id}.json"
    if not job_file.exists():
        return None
    with open(job_file) as f:
        return json.load(f)


async def run_training_job(
    job_id: str,
    agent_name: str,
    base_model: str,
    dataset_path: str,
    training_method: str,
    demo_mode: bool,
    config_overrides: Optional[Dict] = None,
):
    """Execute AutoTrain job asynchronously using CLI"""
    try:
        # Update job status
        metadata = load_job_metadata(job_id)
        metadata["status"] = "running"
        metadata["started_at"] = datetime.utcnow().isoformat()
        save_job_metadata(job_id, metadata)

        # Configure output directory
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        repo_id = f"alextorelli/codechef-{agent_name}-{timestamp}"
        output_dir = JOBS_DIR / f"{job_id}_output"
        output_dir.mkdir(exist_ok=True)

        # Build autotrain-advanced CLI command
        cmd = [
            "autotrain",
            "llm",
            "--train",
            "--model",
            base_model,
            "--data-path",
            dataset_path,
            "--text-column",
            "text",
            "--prompt-text-column",
            "response",
            "--project-name",
            f"codechef-{agent_name}",
            "--push-to-hub",
            "--repo-id",
            repo_id,
            "--token",
            HF_TOKEN,
            # Auto-configuration
            "--auto-find-batch-size",
            "--use-peft",
            "--quantization",
            "int4",
        ]

        # Demo mode: reduce training
        if demo_mode:
            cmd.extend(["--num-train-epochs", "1", "--max-seq-length", "512"])
        else:
            cmd.extend(["--num-train-epochs", "3", "--max-seq-length", "2048"])

        # Apply overrides
        if config_overrides:
            for key, value in config_overrides.items():
                cmd.extend([f"--{key.replace('_', '-')}", str(value)])

        # Execute training subprocess
        log_file = output_dir / "training.log"
        with open(log_file, "w") as log:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                cwd=str(output_dir),
            )
            returncode = await process.wait()

        if returncode != 0:
            with open(log_file) as f:
                error_log = f.read()
            raise RuntimeError(
                f"Training failed with code {returncode}: {error_log[-500:]}"
            )

        # Update final status
        metadata["status"] = "completed"
        metadata["completed_at"] = datetime.utcnow().isoformat()
        metadata["hub_repo"] = repo_id
        metadata["model_id"] = repo_id
        metadata["tensorboard_url"] = f"https://huggingface.co/{repo_id}/tensorboard"
        save_job_metadata(job_id, metadata)

    except Exception as e:
        # Update error status
        metadata = load_job_metadata(job_id)
        metadata["status"] = "failed"
        metadata["error"] = str(e)
        metadata["failed_at"] = datetime.utcnow().isoformat()
        save_job_metadata(job_id, metadata)
        raise


@app.post("/train", response_model=Dict[str, str])
async def submit_training_job(request: TrainingRequest):
    """Submit a new training job"""
    # Generate job ID
    job_id = f"job_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{request.agent_name}"

    # Save dataset
    dataset_path = JOBS_DIR / f"{job_id}_dataset.csv"

    # Handle dataset input (CSV content or HF dataset ID)
    if request.dataset_csv.startswith("hf://"):
        # HuggingFace dataset ID
        dataset_id = request.dataset_csv.replace("hf://", "")
        # Download and convert to CSV
        from datasets import load_dataset

        ds = load_dataset(dataset_id, split="train")
        ds.to_csv(dataset_path)
    else:
        # Base64 encoded CSV content
        import base64

        csv_content = base64.b64decode(request.dataset_csv)
        dataset_path.write_bytes(csv_content)

    # Create job metadata
    metadata = {
        "job_id": job_id,
        "agent_name": request.agent_name,
        "base_model": request.base_model,
        "training_method": request.training_method,
        "demo_mode": request.demo_mode,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "dataset_path": str(dataset_path),
    }
    save_job_metadata(job_id, metadata)

    # Start training in background
    asyncio.create_task(
        run_training_job(
            job_id=job_id,
            agent_name=request.agent_name,
            base_model=request.base_model,
            dataset_path=str(dataset_path),
            training_method=request.training_method,
            demo_mode=request.demo_mode,
            config_overrides=request.config_overrides,
        )
    )

    return {
        "job_id": job_id,
        "status": "pending",
        "message": f"Training job {job_id} submitted successfully",
    }


@app.get("/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get training job status"""
    metadata = load_job_metadata(job_id)
    if not metadata:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JobStatus(
        job_id=metadata["job_id"],
        status=metadata["status"],
        model_id=metadata.get("model_id"),
        hub_repo=metadata.get("hub_repo"),
        tensorboard_url=metadata.get("tensorboard_url"),
        error=metadata.get("error"),
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "code-chef-modelops-trainer",
        "autotrain_available": True,
        "hf_token_configured": bool(HF_TOKEN),
    }


# Gradio UI for manual testing
with gr.Blocks(title="code-chef ModelOps Trainer") as demo:
    gr.Markdown(
        """
    # 🏗️ code-chef ModelOps Training Service
    
    AutoTrain-powered fine-tuning for code-chef agents.
    Use the API endpoints below for programmatic access.
    """
    )

    with gr.Tab("Submit Training"):
        agent_name = gr.Textbox(label="Agent Name", placeholder="feature_dev")
        base_model = gr.Textbox(label="Base Model", value="Qwen/Qwen2.5-Coder-7B")
        dataset_file = gr.File(label="Training Dataset (CSV)", file_types=[".csv"])
        training_method = gr.Dropdown(
            label="Training Method", choices=["sft", "dpo", "reward"], value="sft"
        )
        demo_mode = gr.Checkbox(label="Demo Mode (100 examples, 1 epoch)", value=False)

        submit_btn = gr.Button("Submit Training Job", variant="primary")
        output_status = gr.JSON(label="Job Submission Result")

    with gr.Tab("Check Status"):
        job_id_input = gr.Textbox(
            label="Job ID", placeholder="job_20251210_123456_feature_dev"
        )
        check_btn = gr.Button("Check Status")
        status_output = gr.JSON(label="Job Status")

    with gr.Tab("API Documentation"):
        gr.Markdown(
            """
        ## REST API Endpoints
        
        ### POST /train
        Submit a new training job
        
        ```bash
        curl -X POST https://YOUR-SPACE.hf.space/train \\
          -H "Content-Type: application/json" \\
          -d '{
            "agent_name": "feature_dev",
            "base_model": "Qwen/Qwen2.5-Coder-7B",
            "dataset_csv": "<base64-encoded-csv>",
            "training_method": "sft",
            "demo_mode": false
          }'
        ```
        
        ### GET /status/{job_id}
        Get training job status
        
        ```bash
        curl https://YOUR-SPACE.hf.space/status/job_20251210_123456_feature_dev
        ```
        
        ### GET /health
        Health check
        
        ```bash
        curl https://YOUR-SPACE.hf.space/health
        ```
        """
        )

    # Event handlers
    def submit_job(agent, model, dataset, method, demo):
        if not dataset:
            return {"error": "Dataset file required"}

        # Read CSV and encode
        import base64

        csv_content = dataset.read()
        encoded_csv = base64.b64encode(csv_content).decode()

        request = TrainingRequest(
            agent_name=agent,
            base_model=model,
            dataset_csv=encoded_csv,
            training_method=method,
            demo_mode=demo,
        )

        # Submit via API
        import requests

        response = requests.post("http://localhost:7860/train", json=request.dict())
        return response.json()

    def check_status(job_id):
        import requests

        response = requests.get(f"http://localhost:7860/status/{job_id}")
        return response.json()

    submit_btn.click(
        fn=submit_job,
        inputs=[agent_name, base_model, dataset_file, training_method, demo_mode],
        outputs=output_status,
    )

    check_btn.click(fn=check_status, inputs=[job_id_input], outputs=status_output)

# Mount Gradio app to FastAPI
app = gr.mount_gradio_app(app, demo, path="/")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)
