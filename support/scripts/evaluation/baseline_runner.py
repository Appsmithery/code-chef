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
    from langsmith import traceable

    LANGSMITH_AVAILABLE = True
except ImportError:
    print("WARNING: LangSmith not available. Tracing will be disabled.")

    # Fallback no-op decorator
    def traceable(name=None, project_name=None):
        def decorator(func):
            return func

        return decorator

    LANGSMITH_AVAILABLE = False

import httpx
from loguru import logger

# Import longitudinal tracker for database persistence
sys.path.insert(0, str(project_root / "shared"))
from lib.longitudinal_tracker import longitudinal_tracker


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
        self.langsmith_client = LangSmithClient() if LANGSMITH_AVAILABLE else None

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
        Uses OpenRouter API with untrained base model.
        """
        start_time = datetime.now()

        # Use OpenRouter for baseline (untrained model)
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            logger.warning("OPENROUTER_API_KEY not set, using mock response")
            return self._mock_baseline_response(prompt, task_id, metadata, start_time)

        # Choose baseline model (untrained, general purpose)
        baseline_model = os.getenv("BASELINE_MODEL", "anthropic/claude-3.5-haiku")

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openrouter_api_key}",
                        "HTTP-Referer": "https://github.com/Appsmithery/Dev-Tools",
                        "X-Title": "code-chef-baseline-evaluation",
                    },
                    json={
                        "model": baseline_model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 2000,
                        "temperature": 0.7,
                    },
                )
                response.raise_for_status()
                data = response.json()

            # Extract metrics from response
            output = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            tokens_used = usage.get("total_tokens", 0)
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)

            # Calculate latency and cost
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Cost calculation (OpenRouter pricing varies by model)
            # Claude 3.5 Haiku: ~$1.00/1M input, ~$5.00/1M output tokens
            cost_per_input_token = 1.00 / 1_000_000
            cost_per_output_token = 5.00 / 1_000_000
            cost_usd = (prompt_tokens * cost_per_input_token) + (
                completion_tokens * cost_per_output_token
            )

            result = {
                "task_id": task_id,
                "mode": "baseline",
                "output": output,
                "tokens_used": tokens_used,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "latency_ms": latency_ms,
                "cost_usd": cost_usd,
                "model": baseline_model,
                "metadata": metadata,
                "timestamp": start_time.isoformat(),
                "success": True,
            }

            logger.info(
                f"✓ Baseline task {task_id[:8]}... completed: {tokens_used} tokens, "
                f"{latency_ms:.0f}ms, ${cost_usd:.6f}"
            )
            return result

        except Exception as e:
            logger.error(f"✗ Baseline task {task_id[:8]}... failed: {e}")
            return {
                "task_id": task_id,
                "mode": "baseline",
                "error": str(e),
                "success": False,
                "metadata": metadata,
                "timestamp": start_time.isoformat(),
            }

    def _mock_baseline_response(
        self, prompt: str, task_id: str, metadata: Dict[str, str], start_time: datetime
    ) -> Dict[str, Any]:
        """Return mock baseline response when OpenRouter API is unavailable."""
        latency_ms = (datetime.now() - start_time).total_seconds() * 1000

        return {
            "task_id": task_id,
            "mode": "baseline",
            "output": f"[MOCK BASELINE: API key not configured. Prompt: {prompt[:50]}...]",
            "tokens_used": 500,
            "prompt_tokens": 350,
            "completion_tokens": 150,
            "latency_ms": latency_ms,
            "cost_usd": 0.001,
            "model": "mock-baseline",
            "metadata": metadata,
            "timestamp": start_time.isoformat(),
            "success": False,
            "mock": True,
        }

    @traceable(
        name="codechef_agent_invoke",
        project_name=_get_langsmith_project(),
    )
    async def _run_codechef_task(
        self, prompt: str, task_id: str, metadata: Dict[str, str]
    ) -> Dict[str, Any]:
        """Run task through code-chef extension with trained models.

        This is the experimental condition - code-chef with fine-tuned models.
        Calls the orchestrator API endpoint.
        """
        start_time = datetime.now()

        # Call code-chef orchestrator
        orchestrator_url = os.getenv("ORCHESTRATOR_URL", "http://localhost:8001")

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{orchestrator_url}/execute",
                    json={
                        "message": prompt,
                        "metadata": {
                            "experiment_id": metadata.get("experiment_id"),
                            "task_id": task_id,
                            "experiment_group": "code-chef",
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()

            # Extract metrics from orchestrator response
            output = data.get("result", {}).get("output", "")
            tokens_used = data.get("metrics", {}).get("total_tokens", 0)
            prompt_tokens = data.get("metrics", {}).get("prompt_tokens", 0)
            completion_tokens = data.get("metrics", {}).get("completion_tokens", 0)
            cost_usd = data.get("metrics", {}).get("total_cost", 0)
            agents_used = data.get("agents_used", [])

            # Calculate latency
            latency_ms = (datetime.now() - start_time).total_seconds() * 1000

            result = {
                "task_id": task_id,
                "mode": "code-chef",
                "output": output,
                "tokens_used": tokens_used,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "latency_ms": latency_ms,
                "cost_usd": cost_usd,
                "agents_used": agents_used,
                "metadata": metadata,
                "timestamp": start_time.isoformat(),
                "success": True,
            }

            logger.info(
                f"✓ Code-chef task {task_id[:8]}... completed: {tokens_used} tokens, "
                f"{latency_ms:.0f}ms, ${cost_usd:.6f}, agents={agents_used}"
            )
            return result

        except Exception as e:
            logger.error(f"✗ Code-chef task {task_id[:8]}... failed: {e}")
            return {
                "task_id": task_id,
                "mode": "code-chef",
                "error": str(e),
                "success": False,
                "metadata": metadata,
                "timestamp": start_time.isoformat(),
            }

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

                # Store in longitudinal tracker if available
                if longitudinal_tracker._initialized and result.get("success"):
                    await self._store_result(result)

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

    async def _store_result(self, result: Dict[str, Any]):
        """Store result in longitudinal tracker.

        Args:
            result: Task result with metrics
        """
        try:
            metadata = result.get("metadata", {})
            experiment_id = metadata.get(
                "experiment_id", os.getenv("EXPERIMENT_ID", "unknown")
            )

            # For now, store basic metrics only
            # Evaluation scores (accuracy, completeness, etc.) will come from evaluators
            await longitudinal_tracker.record_result(
                experiment_id=experiment_id,
                task_id=result["task_id"],
                experiment_group=result["mode"],
                extension_version=metadata.get("extension_version", "1.0.0"),
                model_version=result.get("model", "unknown"),
                agent_name=metadata.get("agent_name"),
                scores={},  # Will be filled by evaluators
                metrics={
                    "latency_ms": result.get("latency_ms", 0),
                    "tokens_used": result.get("tokens_used", 0),
                    "cost_usd": result.get("cost_usd", 0),
                },
                success=result.get("success", True),
                error_message=result.get("error"),
                metadata=metadata,
            )
            logger.debug(
                f"Stored result for task {result['task_id'][:8]}... in database"
            )
        except Exception as e:
            logger.warning(f"Failed to store result in database: {e}")

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

    # Initialize longitudinal tracker for database persistence
    try:
        await longitudinal_tracker.initialize()
        logger.info("✓ Longitudinal tracker initialized")
    except Exception as e:
        logger.warning(f"✗ Longitudinal tracker unavailable: {e}")

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
