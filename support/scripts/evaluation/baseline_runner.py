"""Baseline runner for A/B testing code-chef against untrained baseline LLM.

This script runs the same evaluation tasks through both:
1. Baseline LLM (without code-chef enhancements)
2. Code-chef extension (with trained models)

Results are traced to LangSmith with experiment_group metadata for comparison.

Usage:
    # Set experiment ID to correlate runs
    export EXPERIMENT_ID=exp-2025-01-001
    export TRACE_ENVIRONMENT=evaluation

    # Run baseline
    python support/scripts/evaluation/baseline_runner.py --mode baseline --tasks tasks.json

    # Run code-chef
    python support/scripts/evaluation/baseline_runner.py --mode code-chef --tasks tasks.json

    # Compare results in LangSmith:
    # Filter: experiment_id:"exp-2025-01-001"
    # Split by: experiment_group (baseline vs code-chef)
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from langsmith import Client as LangSmithClient
    from langsmith.utils import traceable

    LANGSMITH_AVAILABLE = True
except ImportError:
    print("ERROR: LangSmith not available. Install with: pip install langsmith")
    sys.exit(1)

from loguru import logger


def _get_baseline_trace_metadata(mode: str, task_id: str) -> Dict[str, str]:
    """Get metadata for baseline runner traces.

    Args:
        mode: "baseline" or "code-chef"
        task_id: Unique task identifier for correlation

    Returns:
        Metadata dict following tracing schema
    """
    return {
        "experiment_group": mode,  # "baseline" or "code-chef"
        "experiment_id": os.getenv(
            "EXPERIMENT_ID", f"exp-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        ),
        "task_id": task_id,
        "environment": "evaluation",
        "module": "evaluation",
        "extension_version": os.getenv("EXTENSION_VERSION", "1.0.0"),
        "model_version": os.getenv(
            "MODEL_VERSION", "baseline" if mode == "baseline" else "code-chef"
        ),
    }


def _get_langsmith_project() -> str:
    """Get LangSmith project for experiments."""
    return os.getenv("LANGSMITH_PROJECT_EXPERIMENTS", "code-chef-experiments")


class BaselineRunner:
    """Runs evaluation tasks through baseline or code-chef for comparison."""

    def __init__(self, mode: str = "baseline"):
        """Initialize baseline runner.

        Args:
            mode: "baseline" or "code-chef"
        """
        if mode not in ["baseline", "code-chef"]:
            raise ValueError(f"Invalid mode: {mode}. Must be 'baseline' or 'code-chef'")

        self.mode = mode
        self.langsmith_client = LangSmithClient()

        # Set environment variables for tracing
        os.environ["EXPERIMENT_GROUP"] = mode
        os.environ["TRACE_ENVIRONMENT"] = "evaluation"

        logger.info(f"Initialized {mode} runner")
        logger.info(f"Experiment ID: {os.getenv('EXPERIMENT_ID')}")

    @traceable(
        name="baseline_run_task",
        project_name=_get_langsmith_project(),
    )
    async def run_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single evaluation task.

        Args:
            task: Task definition with:
                - task_id: Unique identifier
                - prompt: Input prompt
                - expected_output: Optional expected result
                - metadata: Optional task metadata

        Returns:
            Result dict with output and metrics
        """
        task_id = task.get("task_id", str(uuid4()))
        prompt = task.get("prompt", "")

        # Add task-specific metadata to trace
        metadata = _get_baseline_trace_metadata(self.mode, task_id)
        metadata.update(task.get("metadata", {}))

        logger.info(f"Running task {task_id} in {self.mode} mode")

        if self.mode == "baseline":
            # Run through untrained baseline LLM
            result = await self._run_baseline_task(prompt, task_id, metadata)
        else:
            # Run through code-chef extension
            result = await self._run_codechef_task(prompt, task_id, metadata)

        return result

    @traceable(
        name="baseline_llm_invoke",
        project_name=_get_langsmith_project(),
    )
    async def _run_baseline_task(
        self, prompt: str, task_id: str, metadata: Dict[str, str]
    ) -> Dict[str, Any]:
        """Run task through baseline LLM without code-chef enhancements.

        This is the null hypothesis - what the LLM produces without fine-tuning.
        """
        start_time = datetime.now()

        # TODO: Implement actual baseline LLM invocation
        # For now, return mock result
        # In production, this would call:
        # - OpenRouter with base model (not fine-tuned)
        # - Or local model without code-chef training

        result = {
            "task_id": task_id,
            "mode": "baseline",
            "output": f"[BASELINE OUTPUT PLACEHOLDER for: {prompt[:50]}...]",
            "tokens_used": 500,
            "latency_ms": 1500,
            "cost_usd": 0.001,
            "metadata": metadata,
            "timestamp": start_time.isoformat(),
        }

        duration = (datetime.now() - start_time).total_seconds()
        result["duration_seconds"] = duration

        logger.info(f"Baseline task {task_id} completed in {duration:.2f}s")
        return result

    @traceable(
        name="codechef_agent_invoke",
        project_name=_get_langsmith_project(),
    )
    async def _run_codechef_task(
        self, prompt: str, task_id: str, metadata: Dict[str, str]
    ) -> Dict[str, Any]:
        """Run task through code-chef extension with trained models.

        This is the experimental condition - code-chef with fine-tuned models.
        """
        start_time = datetime.now()

        # TODO: Implement actual code-chef invocation
        # For now, return mock result
        # In production, this would call:
        # - Code-chef VS Code extension API
        # - Or agent orchestrator directly with trained models

        result = {
            "task_id": task_id,
            "mode": "code-chef",
            "output": f"[CODE-CHEF OUTPUT PLACEHOLDER for: {prompt[:50]}...]",
            "tokens_used": 450,  # Should be lower due to efficiency
            "latency_ms": 1200,  # Should be faster
            "cost_usd": 0.0008,  # Should be cheaper
            "metadata": metadata,
            "timestamp": start_time.isoformat(),
        }

        duration = (datetime.now() - start_time).total_seconds()
        result["duration_seconds"] = duration

        logger.info(f"Code-chef task {task_id} completed in {duration:.2f}s")
        return result

    async def run_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run multiple tasks.

        Args:
            tasks: List of task definitions

        Returns:
            List of results
        """
        results = []

        for task in tasks:
            try:
                result = await self.run_task(task)
                results.append(result)
            except Exception as e:
                logger.error(f"Task {task.get('task_id')} failed: {e}")
                results.append(
                    {
                        "task_id": task.get("task_id"),
                        "error": str(e),
                        "success": False,
                    }
                )

        return results

    def save_results(self, results: List[Dict[str, Any]], output_path: str):
        """Save results to JSON file.

        Args:
            results: List of result dicts
            output_path: Path to save results
        """
        with open(output_path, "w") as f:
            json.dump(
                {
                    "experiment_id": os.getenv("EXPERIMENT_ID"),
                    "mode": self.mode,
                    "timestamp": datetime.now().isoformat(),
                    "task_count": len(results),
                    "results": results,
                },
                f,
                indent=2,
            )

        logger.info(f"Results saved to {output_path}")


def load_tasks(tasks_file: str) -> List[Dict[str, Any]]:
    """Load tasks from JSON file.

    Args:
        tasks_file: Path to tasks JSON file

    Returns:
        List of task definitions
    """
    with open(tasks_file) as f:
        data = json.load(f)

    # Support both raw list and wrapped format
    if isinstance(data, list):
        return data
    elif "tasks" in data:
        return data["tasks"]
    else:
        raise ValueError(
            "Invalid tasks file format. Expected list or dict with 'tasks' key."
        )


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run A/B test comparison: baseline vs code-chef"
    )
    parser.add_argument(
        "--mode",
        choices=["baseline", "code-chef"],
        required=True,
        help="Run mode: baseline (untrained) or code-chef (trained)",
    )
    parser.add_argument(
        "--tasks",
        required=True,
        help="Path to tasks JSON file",
    )
    parser.add_argument(
        "--output",
        help="Output path for results (default: results-{mode}-{timestamp}.json)",
    )
    parser.add_argument(
        "--experiment-id",
        help="Experiment ID for correlation (default: auto-generated)",
    )

    args = parser.parse_args()

    # Set experiment ID
    if args.experiment_id:
        os.environ["EXPERIMENT_ID"] = args.experiment_id

    # Load tasks
    tasks = load_tasks(args.tasks)
    logger.info(f"Loaded {len(tasks)} tasks from {args.tasks}")

    # Initialize runner
    runner = BaselineRunner(mode=args.mode)

    # Run tasks
    results = await runner.run_tasks(tasks)

    # Save results
    output_path = (
        args.output
        or f"results-{args.mode}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    )
    runner.save_results(results, output_path)

    # Print summary
    success_count = sum(1 for r in results if r.get("success", True))
    logger.info(f"Completed: {success_count}/{len(results)} tasks successful")
    logger.info(f"View traces in LangSmith: {_get_langsmith_project()}")
    logger.info(
        f"Filter by: experiment_id:\"{os.getenv('EXPERIMENT_ID')}\" AND experiment_group:\"{args.mode}\""
    )


if __name__ == "__main__":
    asyncio.run(main())
