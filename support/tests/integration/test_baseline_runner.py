"""
Integration tests for Baseline Runner with real/mocked LLM calls.

Part of Phase 2: Complete Baseline Runner Implementation (CHEF-240)
"""

import asyncio
import json
import os

# Add project root to path
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).parents[3]))

from support.scripts.evaluation.baseline_runner import BaselineRunner, load_tasks

pytestmark = pytest.mark.asyncio


class TestBaselineRunnerIntegration:
    """Integration tests for BaselineRunner."""

    @pytest.fixture
    def sample_tasks(self):
        """Load sample evaluation tasks."""
        tasks_file = (
            Path(__file__).parent.parent.parent
            / "scripts"
            / "evaluation"
            / "sample_tasks.json"
        )
        if tasks_file.exists():
            return load_tasks(str(tasks_file))

        # Fallback to minimal test tasks
        return [
            {
                "task_id": "test-task-001",
                "prompt": "Create a hello world function in Python",
                "metadata": {"category": "code_generation", "difficulty": "easy"},
            }
        ]

    async def test_baseline_runner_initialization(self):
        """Test baseline runner initializes correctly."""
        runner = BaselineRunner(mode="baseline")
        assert runner.mode == "baseline"
        assert runner.langsmith_client is not None

    async def test_codechef_runner_initialization(self):
        """Test code-chef runner initializes correctly."""
        runner = BaselineRunner(mode="code-chef")
        assert runner.mode == "code-chef"

    async def test_invalid_mode_raises_error(self):
        """Test that invalid mode raises ValueError."""
        with pytest.raises(ValueError, match="Invalid mode"):
            BaselineRunner(mode="invalid")

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": ""})
    async def test_baseline_task_without_api_key(self, sample_tasks):
        """Test baseline runner handles missing API key gracefully."""
        runner = BaselineRunner(mode="baseline")
        task = sample_tasks[0]

        result = await runner.run_task(task)

        assert result["mode"] == "baseline"
        assert result["success"] is False
        assert result.get("mock") is True
        assert "MOCK BASELINE" in result["output"]

    @patch("httpx.AsyncClient")
    async def test_baseline_task_with_mocked_api(self, mock_httpx, sample_tasks):
        """Test baseline runner with mocked OpenRouter API."""
        # Setup mock response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "def hello_world():\n    return 'Hello, World!'"
                    }
                }
            ],
            "usage": {
                "total_tokens": 450,
                "prompt_tokens": 300,
                "completion_tokens": 150,
            },
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_httpx.return_value = mock_client

        # Run with API key set
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            runner = BaselineRunner(mode="baseline")
            task = sample_tasks[0]

            result = await runner.run_task(task)

        assert result["mode"] == "baseline"
        assert result["success"] is True
        assert result["tokens_used"] == 450
        assert result["prompt_tokens"] == 300
        assert result["completion_tokens"] == 150
        assert result["latency_ms"] > 0
        assert result["cost_usd"] > 0
        assert "def hello_world" in result["output"]

    @patch("httpx.AsyncClient")
    async def test_codechef_task_with_mocked_orchestrator(
        self, mock_httpx, sample_tasks
    ):
        """Test code-chef runner with mocked orchestrator API."""
        # Setup mock orchestrator response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "output": "def hello_world():\n    '''Returns a greeting.'''\n    return 'Hello, World!'"
            },
            "metrics": {
                "total_tokens": 380,
                "prompt_tokens": 250,
                "completion_tokens": 130,
                "total_cost": 0.0015,
            },
            "agents_used": ["feature_dev"],
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_httpx.return_value = mock_client

        runner = BaselineRunner(mode="code-chef")
        task = sample_tasks[0]

        result = await runner.run_task(task)

        assert result["mode"] == "code-chef"
        assert result["success"] is True
        assert result["tokens_used"] == 380
        assert result["cost_usd"] == 0.0015
        assert result["agents_used"] == ["feature_dev"]
        assert "def hello_world" in result["output"]

    @patch("httpx.AsyncClient")
    async def test_baseline_api_error_handling(self, mock_httpx, sample_tasks):
        """Test baseline runner handles API errors gracefully."""
        # Setup mock error response
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("API Error")

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_httpx.return_value = mock_client

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            runner = BaselineRunner(mode="baseline")
            task = sample_tasks[0]

            result = await runner.run_task(task)

        assert result["success"] is False
        assert "error" in result
        assert "API Error" in result["error"]

    async def test_run_multiple_tasks(self, sample_tasks):
        """Test running multiple tasks in sequence."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            runner = BaselineRunner(mode="baseline")

            # Take first 2 tasks
            tasks = sample_tasks[:2]
            results = await runner.run_tasks(tasks)

            assert len(results) == len(tasks)
            assert all("task_id" in r for r in results)
            assert all(r["mode"] == "baseline" for r in results)

    async def test_load_tasks_from_file(self, tmp_path):
        """Test loading tasks from JSON file."""
        # Create temp tasks file
        tasks_data = [
            {"task_id": "test-1", "prompt": "Test prompt 1"},
            {"task_id": "test-2", "prompt": "Test prompt 2"},
        ]

        tasks_file = tmp_path / "tasks.json"
        with open(tasks_file, "w") as f:
            json.dump(tasks_data, f)

        loaded_tasks = load_tasks(str(tasks_file))

        assert len(loaded_tasks) == 2
        assert loaded_tasks[0]["task_id"] == "test-1"
        assert loaded_tasks[1]["prompt"] == "Test prompt 2"

    async def test_load_tasks_wrapped_format(self, tmp_path):
        """Test loading tasks from wrapped JSON format."""
        tasks_data = {
            "experiment_name": "Test Experiment",
            "tasks": [
                {"task_id": "test-1", "prompt": "Test prompt 1"},
            ],
        }

        tasks_file = tmp_path / "tasks.json"
        with open(tasks_file, "w") as f:
            json.dump(tasks_data, f)

        loaded_tasks = load_tasks(str(tasks_file))

        assert len(loaded_tasks) == 1
        assert loaded_tasks[0]["task_id"] == "test-1"

    async def test_save_results(self, tmp_path, sample_tasks):
        """Test saving results to JSON file."""
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": ""}):
            runner = BaselineRunner(mode="baseline")

            results = await runner.run_tasks([sample_tasks[0]])

            output_file = tmp_path / "results.json"
            runner.save_results(results, str(output_file))

            assert output_file.exists()

            with open(output_file) as f:
                saved_data = json.load(f)

            assert "experiment_id" in saved_data
            assert "mode" in saved_data
            assert saved_data["mode"] == "baseline"
            assert "results" in saved_data
            assert len(saved_data["results"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
