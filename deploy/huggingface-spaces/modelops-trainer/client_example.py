"""
code-chef ModelOps Training Client

Usage from agent_orchestrator/agents/infrastructure/modelops/training.py
"""

import base64
import time
from typing import Any, Dict, Optional

import requests
from langsmith import traceable


class ModelOpsTrainerClient:
    """Client for code-chef ModelOps HuggingFace Space"""

    def __init__(self, space_url: str, hf_token: Optional[str] = None):
        """
        Initialize client.

        Args:
            space_url: HF Space URL (e.g., https://appsmithery-code-chef-modelops-trainer.hf.space)
            hf_token: Optional HF token for private spaces
        """
        self.space_url = space_url.rstrip("/")
        self.hf_token = hf_token
        self.headers = {"Content-Type": "application/json"}
        if hf_token:
            self.headers["Authorization"] = f"Bearer {hf_token}"

    @traceable(name="submit_training_job")
    def submit_training_job(
        self,
        agent_name: str,
        base_model: str,
        dataset_csv_path: str,
        training_method: str = "sft",
        demo_mode: bool = False,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        Submit a training job to the HF Space.

        Args:
            agent_name: Agent to train (feature_dev, code_review, etc.)
            base_model: HF model repo (e.g., Qwen/Qwen2.5-Coder-7B)
            dataset_csv_path: Path to CSV file with text/response columns
            training_method: sft, dpo, or reward
            demo_mode: If True, runs quick validation (100 examples, 1 epoch)
            config_overrides: Optional training config overrides

        Returns:
            Dict with job_id, status, message
        """
        # Read and encode CSV
        with open(dataset_csv_path, "rb") as f:
            csv_content = f.read()
        encoded_csv = base64.b64encode(csv_content).decode()

        # Submit job
        response = requests.post(
            f"{self.space_url}/train",
            headers=self.headers,
            json={
                "agent_name": agent_name,
                "base_model": base_model,
                "dataset_csv": encoded_csv,
                "training_method": training_method,
                "demo_mode": demo_mode,
                "config_overrides": config_overrides or {},
            },
        )
        response.raise_for_status()
        return response.json()

    @traceable(name="get_job_status")
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status of a training job.

        Args:
            job_id: Job ID returned from submit_training_job

        Returns:
            Dict with job status, progress, metrics
        """
        response = requests.get(
            f"{self.space_url}/status/{job_id}", headers=self.headers
        )
        response.raise_for_status()
        return response.json()

    @traceable(name="wait_for_completion")
    def wait_for_completion(
        self,
        job_id: str,
        poll_interval: int = 60,
        timeout: int = 7200,
        callback: Optional[callable] = None,
    ) -> Dict[str, Any]:
        """
        Wait for training job to complete.

        Args:
            job_id: Job ID to monitor
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait
            callback: Optional callback(status_dict) called on each poll

        Returns:
            Final job status dict

        Raises:
            TimeoutError: If job doesn't complete within timeout
            RuntimeError: If job fails
        """
        elapsed = 0
        while elapsed < timeout:
            status = self.get_job_status(job_id)

            if callback:
                callback(status)

            if status["status"] == "completed":
                return status
            elif status["status"] == "failed":
                raise RuntimeError(f"Training job failed: {status.get('error')}")

            time.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"Training job {job_id} did not complete within {timeout}s")

    def health_check(self) -> Dict[str, Any]:
        """
        Check if the Space is healthy.

        Returns:
            Dict with health status
        """
        response = requests.get(f"{self.space_url}/health", headers=self.headers)
        response.raise_for_status()
        return response.json()


# Example usage
if __name__ == "__main__":
    import os

    client = ModelOpsTrainerClient(
        space_url="https://appsmithery-code-chef-modelops-trainer.hf.space",
        hf_token=os.environ.get("HF_TOKEN"),
    )

    # Health check
    health = client.health_check()
    print(f"Health: {health}")

    # Submit demo job
    result = client.submit_training_job(
        agent_name="feature_dev",
        base_model="Qwen/Qwen2.5-Coder-7B",
        dataset_csv_path="/tmp/demo_dataset.csv",
        training_method="sft",
        demo_mode=True,
    )

    job_id = result["job_id"]
    print(f"Job submitted: {job_id}")

    # Monitor with callback
    def progress_callback(status):
        print(f"Status: {status['status']}, Progress: {status.get('progress_pct', 0)}%")

    final_status = client.wait_for_completion(
        job_id=job_id, poll_interval=30, callback=progress_callback
    )

    print(f"Training complete! Model: {final_status['hub_repo']}")
