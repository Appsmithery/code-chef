#!/usr/bin/env python3
"""
HuggingFace Space: code-chef ModelOps Training Service
Provides REST API endpoint for AutoTrain-based model fine-tuning
"""

import asyncio
import base64
import json
import os
import yaml
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

    dataset: str  # Base64 encoded CSV
    base_model: str
    project_name: str
    is_demo: bool = False
    text_column: str = "text"
    response_column: str = "response"
    learning_rate: Optional[float] = None
    num_epochs: Optional[int] = None
    batch_size: Optional[int] = None


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
    project_name: str,
    base_model: str,
    dataset_path: str,
    is_demo: bool,
    text_column: str = "text",
    response_column: str = "response",
    learning_rate: Optional[float] = None,
    num_epochs: Optional[int] = None,
    batch_size: Optional[int] = None,
):
    """Execute AutoTrain job asynchronously using config file"""
    try:
        # Update job status
        metadata = load_job_metadata(job_id)
        if metadata:
            metadata["status"] = "running"
            metadata["started_at"] = datetime.utcnow().isoformat()
            save_job_metadata(job_id, metadata)

        # Configure output directory
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        repo_id = f"alextorelli/codechef-{project_name}-{timestamp}"
        output_dir = JOBS_DIR / f"{job_id}_output"
        output_dir.mkdir(exist_ok=True)

        # Create AutoTrain config file (more reliable than CLI args)
        config = {
            "task": "lm_training",
            "backend": "local",  # Required by AutoTrain
            "base_model": base_model,
            "project_name": f"codechef-{project_name}",
            "data_path": str(dataset_path),
            "train_split": "train",
            "valid_split": None,
            "text_column": text_column,
            "rejected_text_column": response_column,
            "add_eos_token": True,
            "block_size": 512 if is_demo else 2048,
            "model_max_length": 2048,
            "epochs": num_epochs if num_epochs else (1 if is_demo else 3),
            "batch_size": batch_size if batch_size else (1 if is_demo else 2),
            "lr": learning_rate if learning_rate else 2e-4,
            "peft": True,
            "quantization": "int4",
            "target_modules": "all-linear",
            "lora_r": 16,
            "lora_alpha": 32,
            "lora_dropout": 0.05,
            "weight_decay": 0.01,
            "gradient_accumulation": 4,
            "mixed_precision": "bf16",
            "push_to_hub": True,
            "repo_id": repo_id,
            "token": HF_TOKEN,
            "logging_steps": 10,
            "save_total_limit": 1,
        }
        
        config_file = output_dir / "config.yml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        # Run AutoTrain with config file
        process = await asyncio.create_subprocess_exec(
            "autotrain",
            "--config",
            str(config_file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(output_dir),
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise RuntimeError(
                f"Training failed with code {process.returncode}: {stderr.decode()[-500:]}"
            )

        # Update final status
        metadata = load_job_metadata(job_id)
        if metadata:
            metadata["status"] = "completed"
            metadata["completed_at"] = datetime.utcnow().isoformat()
            metadata["hub_repo"] = repo_id
            metadata["model_id"] = repo_id
            metadata["tensorboard_url"] = (
                f"https://huggingface.co/{repo_id}/tensorboard"
            )
            save_job_metadata(job_id, metadata)

    except Exception as e:
        # Update error status
        metadata = load_job_metadata(job_id)
        if metadata:
            metadata["status"] = "failed"
            metadata["error"] = str(e)
            metadata["failed_at"] = datetime.utcnow().isoformat()
            save_job_metadata(job_id, metadata)
        raise


@app.post("/train", response_model=Dict[str, str])
async def submit_training_job(request: TrainingRequest):
    """Submit a new training job"""
    # Generate job ID
    job_id = f"job_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{request.project_name}"

    # Save dataset
    dataset_path = JOBS_DIR / f"{job_id}_dataset.csv"

    # Base64 encoded CSV content
    import base64

    csv_content = base64.b64decode(request.dataset)
    dataset_path.write_bytes(csv_content)

    # Create job metadata
    metadata = {
        "job_id": job_id,
        "project_name": request.project_name,
        "base_model": request.base_model,
        "is_demo": request.is_demo,
        "text_column": request.text_column,
        "response_column": request.response_column,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "dataset_path": str(dataset_path),
    }
    save_job_metadata(job_id, metadata)

    # Start training in background
    asyncio.create_task(
        run_training_job(
            job_id=job_id,
            project_name=request.project_name,
            base_model=request.base_model,
            dataset_path=str(dataset_path),
            is_demo=request.is_demo,
            text_column=request.text_column,
            response_column=request.response_column,
            learning_rate=request.learning_rate,
            num_epochs=request.num_epochs,
            batch_size=request.batch_size,
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


# Gradio UI for API documentation
with gr.Blocks(title="code-chef ModelOps Trainer") as demo:
    gr.Markdown(
        """
    # 🏗️ code-chef ModelOps Training Service
    
    AutoTrain-powered fine-tuning for code-chef agents.
    
    ## API Status
    ✅ Service is running
    
    ## Quick Test
    ```bash
    curl https://alextorelli-code-chef-modelops-trainer.hf.space/health
    ```
    
    ## REST API Endpoints
    
    ### POST /train
    Submit a new training job
    
    ```bash
    curl -X POST https://alextorelli-code-chef-modelops-trainer.hf.space/train \\
      -H "Content-Type: application/json" \\
      -d '{
        "dataset": "<base64-encoded-csv>",
        "base_model": "microsoft/Phi-3-mini-4k-instruct",
        "project_name": "codechef-feature-dev",
        "is_demo": true,
        "text_column": "text",
        "response_column": "response"
      }'
    ```
    
    ### GET /status/{job_id}
    Get training job status
    
    ```bash
    curl https://alextorelli-code-chef-modelops-trainer.hf.space/status/job_xxx
    ```
    
    ### GET /health
    Health check endpoint
    
    Returns service status and configuration.
    
    ## Python Client
    
    ```python
    from agent_orchestrator.agents.infrastructure.modelops.training import ModelOpsTrainerClient
    
    client = ModelOpsTrainerClient()
    
    # Submit job
    job = client.submit_training_job(
        csv_data="text,response\\ncode,output",
        base_model="microsoft/Phi-3-mini-4k-instruct",
        project_name="test-training",
        is_demo=True
    )
    
    # Check status
    status = client.get_job_status(job["job_id"])
    ```
    
    ## Model Presets
    - **phi-3-mini**: 3.8B params, t4-small GPU ($0.75/hr)
    - **codellama-7b**: 7B params, a10g-large GPU ($2.20/hr)
    - **codellama-13b**: 13B params, a10g-large GPU ($2.20/hr)
    
    ## Training Modes
    - **Demo**: 1 epoch, ~5 min, ~$0.50
    - **Production**: 3 epochs, ~90 min, $3.50-$15
    """
    )

# Mount Gradio interface to FastAPI app at root path
# HuggingFace Spaces will auto-detect and run the FastAPI app
app = gr.mount_gradio_app(app, demo, path="/")
