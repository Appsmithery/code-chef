"""ModelOps training implementation using HuggingFace Space API.

This module provides model fine-tuning capabilities for code-chef agents by:
1. Exporting LangSmith evaluation results to CSV format
2. Submitting training jobs to HuggingFace Space (AutoTrain)
3. Monitoring training progress and retrieving trained models
4. Managing training configurations and hardware requirements

Architecture:
- Uses HuggingFace Space REST API for training isolation
- Leverages AutoTrain Advanced for automatic configuration
- Integrates with LangSmith for evaluation data export
- Supports demo (quick test) and production modes

GitHub Reference: https://github.com/Appsmithery/Dev-Tools/blob/main/support/docs/extend%20Infra%20agent%20ModelOps.md
"""

import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

# HTTP client
import httpx
import pandas as pd
import yaml

# LangSmith imports
try:
    from langsmith import Client as LangSmithClient
    from langsmith.utils import traceable

    LANGSMITH_AVAILABLE = True
except ImportError:
    # Fallback for environments without LangSmith
    LANGSMITH_AVAILABLE = False

    def traceable(name=None, **kwargs):
        """No-op decorator when LangSmith not available"""

        def decorator(func):
            return func

        return decorator if name else lambda f: f

    LangSmithClient = None

# Logging
from loguru import logger


def _get_training_trace_metadata() -> Dict[str, Any]:
    """Get standard metadata for training traces.

    Returns metadata following the schema in config/observability/tracing-schema.yaml
    """
    return {
        "experiment_group": os.getenv("EXPERIMENT_GROUP", "code-chef"),
        "environment": os.getenv("TRACE_ENVIRONMENT", "training"),
        "module": "training",
        "extension_version": os.getenv("EXTENSION_VERSION", "1.0.0"),
        "model_version": os.getenv("MODEL_VERSION", "unknown"),
        "experiment_id": os.getenv("EXPERIMENT_ID"),
        "agent": os.getenv("AGENT_NAME", "infrastructure"),
    }


def _get_langsmith_project() -> str:
    """Determine LangSmith project based on environment.

    Returns:
        Project name for training traces
    """
    environment = os.getenv("TRACE_ENVIRONMENT", "training")

    if environment == "training":
        return os.getenv("LANGSMITH_PROJECT_TRAINING", "code-chef-training")
    elif environment == "evaluation" and os.getenv("EXPERIMENT_ID"):
        return os.getenv("LANGSMITH_PROJECT_EXPERIMENTS", "code-chef-experiments")
    else:
        return os.getenv("LANGSMITH_PROJECT", "code-chef-infrastructure")


@dataclass
class TrainingConfig:
    """Configuration for model training job."""

    base_model: str
    project_name: str
    dataset_csv: str  # CSV content or path
    is_demo: bool = False
    learning_rate: Optional[float] = None
    num_epochs: Optional[int] = None
    batch_size: Optional[int] = None
    target_hardware: Optional[Literal["t4-small", "a10g-large"]] = None
    text_column: str = "text"
    response_column: str = "response"


class ModelOpsTrainerClient:
    """Client for HuggingFace Space ModelOps Trainer API.

    Provides REST API interface to the AutoTrain-based training service.
    """

    def __init__(
        self,
        space_url: Optional[str] = None,
        hf_token: Optional[str] = None,
        timeout: int = 300,
    ):
        """Initialize ModelOps trainer client.

        Args:
            space_url: HuggingFace Space URL (default: from env MODELOPS_SPACE_URL)
            hf_token: HuggingFace token (default: from env HUGGINGFACE_TOKEN)
            timeout: HTTP timeout in seconds
        """
        self.space_url = space_url or os.getenv(
            "MODELOPS_SPACE_URL",
            "https://alextorelli-code-chef-modelops-trainer.hf.space",
        )
        self.hf_token = hf_token or os.getenv("HUGGINGFACE_TOKEN")
        self.timeout = timeout

        if not self.hf_token:
            logger.warning("No HuggingFace token found. Space API calls may fail.")

        self.client = httpx.Client(timeout=timeout)

    @traceable(
        name="modelops_health_check",
        project_name=_get_langsmith_project(),
        metadata=_get_training_trace_metadata(),
    )
    def health_check(self) -> Dict:
        """Check if Space is healthy and responsive.

        Returns:
            Dict with status and Space information
        """
        try:
            response = self.client.get(f"{self.space_url}/health")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    @traceable(
        name="modelops_submit_training",
        project_name=_get_langsmith_project(),
        metadata=_get_training_trace_metadata(),
    )
    def submit_training_job(
        self,
        csv_data: str,
        base_model: str,
        project_name: str,
        is_demo: bool = False,
        learning_rate: Optional[float] = None,
        num_epochs: Optional[int] = None,
        batch_size: Optional[int] = None,
        text_column: str = "text",
        response_column: str = "response",
    ) -> Dict:
        """Submit a training job to the Space.

        Args:
            csv_data: CSV content as string with text/response columns
            base_model: HuggingFace model ID (e.g., "microsoft/Phi-3-mini-4k-instruct")
            project_name: Name for the training project
            is_demo: If True, runs quick test (5-10 min, cheap)
            learning_rate: Override learning rate (optional, AutoTrain auto-configures)
            num_epochs: Override number of epochs (optional)
            batch_size: Override batch size (optional)
            text_column: Name of input text column in CSV
            response_column: Name of target response column in CSV

        Returns:
            Dict with job_id and status
        """
        import base64

        payload = {
            "dataset": base64.b64encode(csv_data.encode()).decode(),
            "base_model": base_model,
            "project_name": project_name,
            "is_demo": is_demo,
            "text_column": text_column,
            "response_column": response_column,
        }

        if learning_rate:
            payload["learning_rate"] = learning_rate
        if num_epochs:
            payload["num_epochs"] = num_epochs
        if batch_size:
            payload["batch_size"] = batch_size

        try:
            response = self.client.post(
                f"{self.space_url}/train",
                json=payload,
                headers=(
                    {"Authorization": f"Bearer {self.hf_token}"}
                    if self.hf_token
                    else {}
                ),
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Training job submitted: {result.get('job_id')}")
            return result
        except Exception as e:
            logger.error(f"Failed to submit training job: {e}")
            raise

    @traceable(
        name="modelops_get_job_status",
        project_name=_get_langsmith_project(),
        metadata=_get_training_trace_metadata(),
    )
    def get_job_status(self, job_id: str) -> Dict:
        """Get status of a training job.

        Args:
            job_id: Job identifier from submit_training_job

        Returns:
            Dict with status, model_id (if complete), and logs
        """
        try:
            response = self.client.get(f"{self.space_url}/status/{job_id}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            raise

    @traceable(
        name="modelops_wait_for_completion",
        project_name=_get_langsmith_project(),
        metadata=_get_training_trace_metadata(),
    )
    def wait_for_completion(
        self,
        job_id: str,
        poll_interval: int = 30,
        max_wait: int = 7200,  # 2 hours max
        callback: Optional[callable] = None,
    ) -> Dict:
        """Wait for training job to complete.

        Args:
            job_id: Job identifier
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait
            callback: Optional function called with status dict on each poll

        Returns:
            Final job status dict
        """
        start_time = time.time()

        while (time.time() - start_time) < max_wait:
            status = self.get_job_status(job_id)

            if callback:
                callback(status)

            if status["status"] in ["completed", "failed"]:
                return status

            logger.info(
                f"Job {job_id} status: {status['status']} - waiting {poll_interval}s..."
            )
            time.sleep(poll_interval)

        raise TimeoutError(f"Training job {job_id} did not complete within {max_wait}s")

    def __del__(self):
        """Close HTTP client."""
        self.client.close()


class ModelOpsTrainer:
    """High-level ModelOps training orchestrator.

    Handles end-to-end workflow:
    1. Export evaluation results from LangSmith
    2. Format as CSV for training
    3. Submit to HuggingFace Space
    4. Monitor and retrieve trained model
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize ModelOps trainer.

        Args:
            config_path: Path to training_defaults.yaml (optional)
        """
        self.config_path = config_path or str(
            Path(__file__).parent.parent.parent.parent.parent
            / "config"
            / "modelops"
            / "training_defaults.yaml"
        )

        self.config = self._load_config()
        self.langsmith_client = LangSmithClient() if LANGSMITH_AVAILABLE else None
        self.trainer_client = ModelOpsTrainerClient()

        logger.info(f"ModelOpsTrainer initialized (LangSmith: {LANGSMITH_AVAILABLE})")

    def _load_config(self) -> Dict:
        """Load training configuration from YAML."""
        config_path = Path(self.config_path)

        if not config_path.exists():
            logger.warning(f"Config not found: {config_path}. Using defaults.")
            return self._default_config()

        with open(config_path) as f:
            return yaml.safe_load(f)

    def _default_config(self) -> Dict:
        """Default configuration if YAML not found."""
        return {
            "model_presets": {
                "phi-3-mini": {
                    "model_id": "microsoft/Phi-3-mini-4k-instruct",
                    "hardware": "t4-small",
                    "parameters": "3.8B",
                },
                "codellama-7b": {
                    "model_id": "codellama/CodeLlama-7b-Instruct-hf",
                    "hardware": "a10g-large",
                    "parameters": "7B",
                },
            },
            "training_defaults": {
                "demo": {"num_epochs": 1, "batch_size": 1, "max_steps": 10},
                "production": {"num_epochs": 3, "learning_rate": 2e-4},
            },
        }

    @traceable(
        name="modelops_export_langsmith_data",
        project_name=_get_langsmith_project(),
        metadata=_get_training_trace_metadata(),
    )
    def export_langsmith_data(
        self,
        project_name: str,
        filter_criteria: Optional[Dict] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """Export evaluation results from LangSmith project.

        Args:
            project_name: LangSmith project name (e.g., "code-chef-feature-dev")
            filter_criteria: Optional filters for runs
            limit: Maximum number of runs to export

        Returns:
            DataFrame with text/response columns
        """
        if not LANGSMITH_AVAILABLE or not self.langsmith_client:
            raise RuntimeError(
                "LangSmith not available. Install: pip install langsmith"
            )

        logger.info(f"Exporting data from LangSmith project: {project_name}")

        try:
            runs = self.langsmith_client.list_runs(
                project_name=project_name, filter=filter_criteria, limit=limit
            )

            data = []
            for run in runs:
                # Extract input/output from run
                if run.inputs and run.outputs:
                    text = self._extract_text(run.inputs)
                    response = self._extract_text(run.outputs)

                    if text and response:
                        data.append(
                            {
                                "text": text,
                                "response": response,
                                "run_id": str(run.id),
                                "feedback_score": (
                                    run.feedback_stats.get("score", 0)
                                    if run.feedback_stats
                                    else 0
                                ),
                            }
                        )

            df = pd.DataFrame(data)
            logger.info(f"Exported {len(df)} training examples from LangSmith")

            return df

        except Exception as e:
            logger.error(f"Failed to export LangSmith data: {e}")
            raise

    def _extract_text(self, data: Dict) -> str:
        """Extract text from LangSmith run input/output."""
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            # Try common keys
            for key in ["input", "text", "prompt", "question", "output", "response"]:
                if key in data:
                    return str(data[key])
            # Fallback: return first string value
            for value in data.values():
                if isinstance(value, str):
                    return value
        return ""

    @traceable(
        name="modelops_train_model",
        project_name=_get_langsmith_project(),
        metadata=_get_training_trace_metadata(),
    )
    def train_model(
        self,
        agent_name: str,
        langsmith_project: str,
        base_model_preset: str = "phi-3-mini",
        is_demo: bool = False,
        filter_criteria: Optional[Dict] = None,
        export_limit: int = 1000,
    ) -> Dict:
        """Train a model for a specific agent.

        Args:
            agent_name: Agent name (e.g., "feature_dev", "code_review")
            langsmith_project: LangSmith project to export data from
            base_model_preset: Preset from config (e.g., "phi-3-mini", "codellama-7b")
            is_demo: If True, runs quick demo mode
            filter_criteria: Optional filters for LangSmith data
            export_limit: Max examples to export from LangSmith

        Returns:
            Dict with training job info and model_id (when complete)
        """
        logger.info(f"Starting ModelOps training for {agent_name}")

        # 1. Export data from LangSmith
        df = self.export_langsmith_data(
            project_name=langsmith_project,
            filter_criteria=filter_criteria,
            limit=export_limit,
        )

        if len(df) < 10:
            raise ValueError(
                f"Insufficient training data: {len(df)} examples (need at least 10)"
            )

        # 2. Get model preset
        preset = self.config["model_presets"].get(base_model_preset)
        if not preset:
            raise ValueError(f"Unknown model preset: {base_model_preset}")

        # 3. Prepare CSV
        csv_data = df[["text", "response"]].to_csv(index=False)

        # 4. Submit training job
        project_name = f"codechef-{agent_name}-{int(time.time())}"

        job = self.trainer_client.submit_training_job(
            csv_data=csv_data,
            base_model=preset["model_id"],
            project_name=project_name,
            is_demo=is_demo,
        )

        logger.info(f"Training job submitted: {job['job_id']}")
        logger.info(f"Expected cost: ${job.get('estimated_cost', 'unknown')}")
        logger.info(f"Hardware: {preset['hardware']}")

        # Build Trackio URL
        trackio_url = f"https://huggingface.co/spaces/alextorelli/code-chef-modelops-trainer?job_id={job['job_id']}"

        return {
            "job_id": job["job_id"],
            "project_name": project_name,
            "base_model": preset["model_id"],
            "hub_repo": f"alextorelli/{project_name}",
            "training_examples": len(df),
            "is_demo": is_demo,
            "hardware": preset["hardware"],
            "status": "submitted",
            "estimated_duration_minutes": 5 if is_demo else 90,
            "estimated_cost": 0.50 if is_demo else 3.50,
            "trackio_url": trackio_url,
            "tensorboard_url": None,  # Available after job starts
        }

    async def get_training_status(self, job_id: str) -> Dict[str, Any]:
        """Get current status of a training job (async for VS Code polling).

        Args:
            job_id: Training job identifier

        Returns:
            Dict with current status, progress, metrics, and URLs
        """
        try:
            status = self.trainer_client.get_job_status(job_id)

            return {
                "job_id": job_id,
                "status": status.get("status", "unknown"),
                "progress": status.get("progress", 0),
                "current_step": status.get("current_step", 0),
                "total_steps": status.get("total_steps", 1000),
                "current_loss": status.get("current_loss"),
                "learning_rate": status.get("learning_rate"),
                "eta_minutes": status.get("eta_minutes"),
                "hub_repo": status.get("hub_repo"),
                "tensorboard_url": status.get("tensorboard_url"),
                "trackio_url": f"https://huggingface.co/spaces/alextorelli/code-chef-modelops-trainer?job_id={job_id}",
            }
        except Exception as e:
            logger.error(f"Failed to get training status: {e}")
            return {
                "job_id": job_id,
                "status": "error",
                "error": str(e),
            }

    @traceable(
        name="modelops_monitor_training",
        project_name=_get_langsmith_project(),
        metadata=_get_training_trace_metadata(),
    )
    def monitor_training(self, job_id: str, poll_interval: int = 30) -> Dict:
        """Monitor training job until completion.

        Args:
            job_id: Job identifier from train_model()
            poll_interval: Seconds between status checks

        Returns:
            Final job status with model_id
        """

        def log_progress(status: Dict):
            logger.info(f"Training progress: {status['status']}")
            if "progress" in status:
                logger.info(f"  Progress: {status['progress']}%")
            if "tensorboard_url" in status:
                logger.info(f"  TensorBoard: {status['tensorboard_url']}")

        final_status = self.trainer_client.wait_for_completion(
            job_id=job_id, poll_interval=poll_interval, callback=log_progress
        )

        if final_status["status"] == "completed":
            logger.success(f"Training completed! Model: {final_status['model_id']}")
        else:
            logger.error(
                f"Training failed: {final_status.get('error', 'Unknown error')}"
            )

        return final_status
