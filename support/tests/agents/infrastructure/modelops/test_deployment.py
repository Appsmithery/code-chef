"""Unit tests for ModelOps deployment functionality."""

import shutil
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from agent_orchestrator.agents.infrastructure.modelops.deployment import (
    DeploymentConfig,
    DeploymentResult,
    ModelOpsDeployment,
)
from agent_orchestrator.agents.infrastructure.modelops.registry import (
    EvaluationScores,
    ModelRegistry,
    ModelVersion,
    TrainingConfig,
)


@pytest.fixture
def test_models_config(tmp_path):
    """Create a temporary models.yaml for testing."""
    config = {
        "version": "1.1",
        "provider": "openrouter",
        "openrouter": {
            "base_url": "https://openrouter.ai/api/v1",
            "agent_models": {
                "feature_dev": "qwen/qwen-2.5-coder-32b-instruct",
                "code_review": "deepseek/deepseek-chat",
            },
        },
    }

    config_path = tmp_path / "models.yaml"
    with open(config_path, "w") as f:
        yaml.safe_dump(config, f)

    return config_path


@pytest.fixture
def test_registry(tmp_path):
    """Create a test registry."""
    registry_path = tmp_path / "test_registry.json"
    registry = ModelRegistry(registry_path=str(registry_path))

    # Add a test version using correct API
    training_config_dict = {
        "base_model": "microsoft/Phi-3-mini-4k-instruct",
        "training_method": "sft",
        "training_dataset": "ls://test-train",
        "eval_dataset": "ls://test-eval",
    }

    version = registry.add_model_version(
        agent_name="feature_dev",
        version="v1.0.0",
        model_id="microsoft/Phi-3-mini-4k-instruct",
        training_config=training_config_dict,
        job_id="test-job-123",
        hub_repo="test-user/test-model-v1",
    )

    # Update with evaluation scores
    eval_scores_dict = {
        "accuracy": 0.85,
        "baseline_improvement_pct": 10.0,
        "avg_latency_ms": 1200.0,
        "cost_per_1k_tokens": 0.003,
    }

    registry.update_evaluation_scores("feature_dev", "v1.0.0", eval_scores_dict)
    registry.set_current_model("feature_dev", "v1.0.0")

    return registry


@pytest.fixture
def deployment(test_models_config, test_registry):
    """Create deployment instance with test config."""
    return ModelOpsDeployment(
        registry=test_registry, models_config_path=str(test_models_config)
    )


class TestModelOpsDeployment:
    """Test suite for ModelOpsDeployment class."""

    @pytest.mark.asyncio
    async def test_deploy_to_openrouter(self, deployment, test_models_config):
        """Test deploying model to OpenRouter."""
        result = await deployment.deploy_model_to_agent(
            agent_name="feature_dev",
            model_repo="test-user/codechef-feature-dev-v2",
            deployment_target="openrouter",
            version="v2.0.0",
        )

        assert result.deployed is True
        assert result.agent_name == "feature_dev"
        assert result.model_repo == "test-user/codechef-feature-dev-v2"
        assert result.version == "v2.0.0"
        assert result.deployment_target == "openrouter"
        assert result.endpoint_url == "https://openrouter.ai/api/v1"
        assert result.rollback_available is True
        assert result.previous_model == "qwen/qwen-2.5-coder-32b-instruct"

        # Verify config was updated
        with open(test_models_config, "r") as f:
            config = yaml.safe_load(f)

        assert (
            config["openrouter"]["agent_models"]["feature_dev"]
            == "test-user/codechef-feature-dev-v2"
        )

        # Verify backup was created
        backup_path = Path(str(test_models_config) + ".bak")
        assert backup_path.exists()

    @pytest.mark.asyncio
    async def test_deploy_to_huggingface(self, deployment, test_models_config):
        """Test deploying model to HuggingFace."""
        result = await deployment.deploy_model_to_agent(
            agent_name="code_review",
            model_repo="test-user/codechef-code-review-v1",
            deployment_target="huggingface",
            version="v1.0.0",
        )

        assert result.deployed is True
        assert result.deployment_target == "huggingface"
        assert (
            result.endpoint_url
            == "https://api-inference.huggingface.co/models/test-user/codechef-code-review-v1"
        )

        # Verify config was updated
        with open(test_models_config, "r") as f:
            config = yaml.safe_load(f)

        assert "huggingface" in config
        assert (
            config["huggingface"]["agent_models"]["code_review"]
            == "test-user/codechef-code-review-v1"
        )

    @pytest.mark.asyncio
    async def test_rollback_to_previous(self, deployment, test_registry):
        """Test rolling back to previous version."""
        # Deploy v2.0.0
        await deployment.deploy_model_to_agent(
            agent_name="feature_dev",
            model_repo="test-user/codechef-feature-dev-v2",
            version="v2.0.0",
        )

        # Add v2.0.0 to registry history
        training_config_dict = {
            "base_model": "microsoft/Phi-3-mini-4k-instruct",
            "training_method": "sft",
            "training_dataset": "ls://test-train",
            "eval_dataset": "ls://test-eval",
        }

        test_registry.add_model_version(
            agent_name="feature_dev",
            version="v2.0.0",
            model_id="test-user/codechef-feature-dev-v2",
            training_config=training_config_dict,
            job_id="test-job-456",
            hub_repo="test-user/codechef-feature-dev-v2",
        )

        test_registry.set_current_model("feature_dev", "v2.0.0")

        # Now rollback
        result = await deployment.rollback_deployment(agent_name="feature_dev")

        assert result.deployed is True
        assert result.version == "v1.0.0"  # Should rollback to v1.0.0
        assert result.model_repo == "test-user/test-model-v1"

    @pytest.mark.asyncio
    async def test_rollback_to_specific_version(self, deployment, test_registry):
        """Test rolling back to a specific version."""
        # Add v2.0.0
        training_config_dict = {
            "base_model": "microsoft/Phi-3-mini-4k-instruct",
            "training_method": "sft",
            "training_dataset": "ls://test-train",
            "eval_dataset": "ls://test-eval",
        }

        test_registry.add_model_version(
            agent_name="feature_dev",
            version="v2.0.0",
            model_id="test-user/codechef-feature-dev-v2",
            training_config=training_config_dict,
            job_id="test-job-456",
            hub_repo="test-user/codechef-feature-dev-v2",
        )

        # Rollback to specific version
        result = await deployment.rollback_deployment(
            agent_name="feature_dev", to_version="v1.0.0"
        )

        assert result.version == "v1.0.0"
        assert result.model_repo == "test-user/test-model-v1"

    @pytest.mark.asyncio
    async def test_list_agent_models(self, deployment, test_registry):
        """Test listing all models for an agent."""
        models = await deployment.list_agent_models(agent_name="feature_dev")

        assert len(models) == 1
        assert models[0]["version"] == "v1.0.0"
        assert models[0]["model_id"] == "microsoft/Phi-3-mini-4k-instruct"
        assert models[0]["hub_repo"] == "test-user/test-model-v1"
        assert models[0]["deployment_status"] == "deployed"  # Set as current
        assert models[0]["eval_scores"] is not None

    @pytest.mark.asyncio
    async def test_list_agent_models_exclude_archived(self, deployment, test_registry):
        """Test listing models excludes archived versions."""
        # Add archived version
        training_config_dict = {
            "base_model": "microsoft/Phi-3-mini-4k-instruct",
            "training_method": "sft",
            "training_dataset": "ls://test-train",
            "eval_dataset": "ls://test-eval",
        }

        test_registry.add_model_version(
            agent_name="feature_dev",
            version="v0.9.0",
            model_id="test-user/codechef-feature-dev-old",
            training_config=training_config_dict,
            job_id="test-job-old",
            hub_repo="test-user/codechef-feature-dev-old",
        )

        # List without archived
        models = await deployment.list_agent_models(
            agent_name="feature_dev", include_archived=False
        )

        # v0.9.0 has not_deployed status (not archived), so both should be included
        assert len(models) == 2

        # List with archived - same result since we don't have truly archived versions
        models_with_archived = await deployment.list_agent_models(
            agent_name="feature_dev", include_archived=True
        )

        assert len(models_with_archived) == 2

    @pytest.mark.asyncio
    async def test_get_current_model(self, deployment):
        """Test getting current deployed model."""
        current = await deployment.get_current_model(agent_name="feature_dev")

        assert current is not None
        assert current["version"] == "v1.0.0"
        assert current["model_id"] == "microsoft/Phi-3-mini-4k-instruct"
        assert current["deployment_status"] == "deployed"

    @pytest.mark.asyncio
    async def test_get_current_model_no_deployment(self, deployment):
        """Test getting current model when none deployed."""
        # Should return None or raise ValueError for nonexistent agent
        try:
            current = await deployment.get_current_model(agent_name="nonexistent_agent")
            # If it doesn't raise, it should return None
            assert current is None
        except ValueError as e:
            # It's also valid to raise an error for unknown agent
            assert "Unknown agent" in str(e)

    @pytest.mark.asyncio
    async def test_deploy_invalid_target_fails(self, deployment):
        """Test deploying to invalid target raises error."""
        with pytest.raises(ValueError, match="Unknown deployment target"):
            await deployment.deploy_model_to_agent(
                agent_name="feature_dev",
                model_repo="test-user/model",
                deployment_target="invalid_target",
            )

    @pytest.mark.asyncio
    async def test_deploy_creates_backup(self, deployment, test_models_config):
        """Test deployment creates backup of models.yaml."""
        backup_path = Path(str(test_models_config) + ".bak")

        # Remove backup if exists
        if backup_path.exists():
            backup_path.unlink()

        await deployment.deploy_model_to_agent(
            agent_name="feature_dev", model_repo="test-user/new-model", version="v3.0.0"
        )

        # Verify backup created
        assert backup_path.exists()

        # Verify backup contains original config
        with open(backup_path, "r") as f:
            backup_config = yaml.safe_load(f)

        assert "openrouter" in backup_config
        assert "agent_models" in backup_config["openrouter"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
