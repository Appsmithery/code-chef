"""Unit tests for ModelOps registry module.

Tests CRUD operations, validation, backup/restore, and version tracking.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from agent_orchestrator.agents.infrastructure.modelops.registry import (
    AgentModelRegistry,
    EvaluationScores,
    ModelRegistry,
    ModelVersion,
    TrainingConfig,
)


@pytest.fixture
def temp_registry():
    """Create temporary registry for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry_path = Path(tmpdir) / "test_registry.json"
        registry = ModelRegistry(registry_path=str(registry_path))
        yield registry


@pytest.fixture
def sample_training_config():
    """Sample training configuration."""
    return {
        "base_model": "microsoft/Phi-3-mini-4k-instruct",
        "training_method": "sft",
        "training_dataset": "ls://feature-dev-train-001",
        "eval_dataset": "ls://feature-dev-eval-001",
        "learning_rate": 2e-4,
        "num_epochs": 3,
        "is_demo": False,
    }


@pytest.fixture
def sample_eval_scores():
    """Sample evaluation scores."""
    return {
        "accuracy": 0.87,
        "baseline_improvement_pct": 12.0,
        "avg_latency_ms": 1200.0,
        "cost_per_1k_tokens": 0.003,
        "token_efficiency": 0.82,
        "workflow_completeness": 0.91,
    }


class TestModelRegistry:
    """Test ModelRegistry class."""

    def test_registry_initialization(self, temp_registry):
        """Test registry file creation."""
        assert temp_registry.registry_path.exists()

        data = temp_registry._read_registry()
        assert "agents" in data
        assert "feature_dev" in data["agents"]
        assert "created_at" in data

    def test_get_agent_registry(self, temp_registry):
        """Test retrieving agent registry."""
        registry = temp_registry.get_agent_registry("feature_dev")

        assert isinstance(registry, AgentModelRegistry)
        assert registry.agent_name == "feature_dev"
        assert registry.current is None
        assert registry.canary is None
        assert len(registry.history) == 0

    def test_invalid_agent_name(self, temp_registry):
        """Test error on invalid agent name."""
        with pytest.raises(ValueError, match="Unknown agent"):
            temp_registry.get_agent_registry("invalid_agent")

    def test_add_model_version(self, temp_registry, sample_training_config):
        """Test adding a new model version."""
        version = temp_registry.add_model_version(
            agent_name="feature_dev",
            version="v1.0.0",
            model_id="alextorelli/codechef-feature-dev-v1",
            training_config=sample_training_config,
            job_id="job_12345",
            hub_repo="alextorelli/codechef-feature-dev-v1",
        )

        assert isinstance(version, ModelVersion)
        assert version.version == "v1.0.0"
        assert version.model_id == "alextorelli/codechef-feature-dev-v1"
        assert version.job_id == "job_12345"
        assert version.deployment_status == "not_deployed"

        # Verify it's in registry
        registry = temp_registry.get_agent_registry("feature_dev")
        assert len(registry.history) == 1
        assert registry.history[0].version == "v1.0.0"

    def test_update_evaluation_scores(
        self, temp_registry, sample_training_config, sample_eval_scores
    ):
        """Test updating evaluation scores."""
        # Add version first
        temp_registry.add_model_version(
            agent_name="feature_dev",
            version="v1.0.0",
            model_id="test/model",
            training_config=sample_training_config,
        )

        # Update scores
        success = temp_registry.update_evaluation_scores(
            agent_name="feature_dev", version="v1.0.0", eval_scores=sample_eval_scores
        )

        assert success is True

        # Verify scores stored
        version = temp_registry.get_version("feature_dev", "v1.0.0")
        assert version.eval_scores is not None
        assert version.eval_scores.accuracy == 0.87
        assert version.eval_scores.baseline_improvement_pct == 12.0

    def test_set_current_model(self, temp_registry, sample_training_config):
        """Test setting current model."""
        # Add version
        temp_registry.add_model_version(
            agent_name="feature_dev",
            version="v1.0.0",
            model_id="test/model",
            training_config=sample_training_config,
        )

        # Set as current
        success = temp_registry.set_current_model("feature_dev", "v1.0.0")
        assert success is True

        # Verify current model
        registry = temp_registry.get_agent_registry("feature_dev")
        assert registry.current is not None
        assert registry.current.version == "v1.0.0"
        assert registry.current.deployment_status == "deployed"
        assert registry.current.deployed_at is not None

    def test_set_canary_model(self, temp_registry, sample_training_config):
        """Test setting canary model."""
        # Add version
        temp_registry.add_model_version(
            agent_name="feature_dev",
            version="v1.0.0",
            model_id="test/model",
            training_config=sample_training_config,
        )

        # Set as 20% canary
        success = temp_registry.set_canary_model("feature_dev", "v1.0.0", canary_pct=20)
        assert success is True

        # Verify canary
        registry = temp_registry.get_agent_registry("feature_dev")
        assert registry.canary is not None
        assert registry.canary.version == "v1.0.0"
        assert registry.canary.deployment_status == "canary_20pct"

    def test_promote_canary_to_current(self, temp_registry, sample_training_config):
        """Test promoting canary to current."""
        # Add two versions
        temp_registry.add_model_version(
            agent_name="feature_dev",
            version="v1.0.0",
            model_id="test/model-v1",
            training_config=sample_training_config,
        )
        temp_registry.add_model_version(
            agent_name="feature_dev",
            version="v2.0.0",
            model_id="test/model-v2",
            training_config=sample_training_config,
        )

        # Set v1 as current
        temp_registry.set_current_model("feature_dev", "v1.0.0")

        # Set v2 as canary
        temp_registry.set_canary_model("feature_dev", "v2.0.0", canary_pct=20)

        # Promote canary
        success = temp_registry.promote_canary_to_current("feature_dev")
        assert success is True

        # Verify promotion
        registry = temp_registry.get_agent_registry("feature_dev")
        assert registry.current.version == "v2.0.0"
        assert registry.current.deployment_status == "deployed"
        assert registry.canary is None

        # Old version should be archived
        v1 = temp_registry.get_version("feature_dev", "v1.0.0")
        assert v1.deployment_status == "archived"

    def test_rollback_to_version(self, temp_registry, sample_training_config):
        """Test rollback to previous version."""
        # Add two versions
        temp_registry.add_model_version(
            agent_name="feature_dev",
            version="v1.0.0",
            model_id="test/model-v1",
            training_config=sample_training_config,
        )
        temp_registry.add_model_version(
            agent_name="feature_dev",
            version="v2.0.0",
            model_id="test/model-v2",
            training_config=sample_training_config,
        )

        # Set v2 as current
        temp_registry.set_current_model("feature_dev", "v2.0.0")

        # Rollback to v1
        success = temp_registry.rollback_to_version("feature_dev", "v1.0.0")
        assert success is True

        # Verify rollback
        registry = temp_registry.get_agent_registry("feature_dev")
        assert registry.current.version == "v1.0.0"

    def test_list_versions(self, temp_registry, sample_training_config):
        """Test listing model versions."""
        # Add multiple versions
        for i in range(5):
            temp_registry.add_model_version(
                agent_name="feature_dev",
                version=f"v1.{i}.0",
                model_id=f"test/model-v{i}",
                training_config=sample_training_config,
            )

        # List versions
        versions = temp_registry.list_versions("feature_dev", limit=3)

        assert len(versions) == 3
        # Should be newest first
        assert versions[0].version == "v1.4.0"
        assert versions[1].version == "v1.3.0"
        assert versions[2].version == "v1.2.0"

    def test_backup_creation(self, temp_registry, sample_training_config):
        """Test automatic backup creation."""
        # Add version (triggers backup on write)
        temp_registry.add_model_version(
            agent_name="feature_dev",
            version="v1.0.0",
            model_id="test/model",
            training_config=sample_training_config,
        )

        # Check backup directory
        backup_dir = temp_registry.registry_path.parent / "backups"
        assert backup_dir.exists()

        backups = list(backup_dir.glob("registry_*.json"))
        assert len(backups) > 0

    def test_validation_errors(self, temp_registry):
        """Test Pydantic validation."""
        # Invalid training method
        with pytest.raises(Exception):  # Pydantic validation error
            temp_registry.add_model_version(
                agent_name="feature_dev",
                version="v1.0.0",
                model_id="test/model",
                training_config={
                    "base_model": "test/model",
                    "training_method": "invalid_method",  # Invalid
                    "training_dataset": "test",
                },
            )

        # Invalid evaluation score (out of range)
        temp_registry.add_model_version(
            agent_name="feature_dev",
            version="v1.0.0",
            model_id="test/model",
            training_config={
                "base_model": "test/model",
                "training_method": "sft",
                "training_dataset": "test",
            },
        )

        with pytest.raises(Exception):  # Pydantic validation error
            temp_registry.update_evaluation_scores(
                agent_name="feature_dev",
                version="v1.0.0",
                eval_scores={"accuracy": 1.5},  # Out of range (must be 0-1)
            )


class TestPydanticModels:
    """Test Pydantic model validation."""

    def test_evaluation_scores_validation(self):
        """Test EvaluationScores validation."""
        # Valid scores
        scores = EvaluationScores(
            accuracy=0.85, avg_latency_ms=1200.0, cost_per_1k_tokens=0.003
        )
        assert scores.accuracy == 0.85

        # Out of range accuracy
        with pytest.raises(Exception):
            EvaluationScores(accuracy=1.5)

        # Negative latency
        with pytest.raises(Exception):
            EvaluationScores(avg_latency_ms=-100)

    def test_training_config_validation(self):
        """Test TrainingConfig validation."""
        # Valid config
        config = TrainingConfig(
            base_model="test/model",
            training_method="sft",
            training_dataset="ls://dataset",
        )
        assert config.training_method == "sft"

        # Invalid training method
        with pytest.raises(Exception):
            TrainingConfig(
                base_model="test/model",
                training_method="invalid",
                training_dataset="ls://dataset",
            )

    def test_agent_name_validation(self):
        """Test agent name validation."""
        # Valid agent
        registry = AgentModelRegistry(agent_name="feature_dev", history=[])
        assert registry.agent_name == "feature_dev"

        # Invalid agent
        with pytest.raises(Exception):
            AgentModelRegistry(agent_name="invalid_agent", history=[])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
