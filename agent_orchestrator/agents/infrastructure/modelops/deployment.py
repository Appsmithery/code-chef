"""Model deployment and lifecycle management for ModelOps.

Handles:
- Deploying fine-tuned models to agents (update models.yaml)
- Model rollback procedures
- Listing agent model versions
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from langsmith import traceable
from pydantic import BaseModel, Field

from .registry import ModelRegistry, ModelVersion


def _get_deployment_trace_metadata() -> Dict[str, str]:
    """Get standard metadata for deployment traces.

    Returns metadata following the schema in config/observability/tracing-schema.yaml
    """
    return {
        "experiment_group": os.getenv("EXPERIMENT_GROUP", "code-chef"),
        "environment": os.getenv("TRACE_ENVIRONMENT", "production"),
        "module": "deployment",
        "extension_version": os.getenv("EXTENSION_VERSION", "1.0.0"),
        "model_version": os.getenv("MODEL_VERSION", "unknown"),
        "agent": os.getenv("AGENT_NAME", "infrastructure"),
    }


def _get_langsmith_project() -> str:
    """Determine LangSmith project based on environment.

    Returns:
        Project name for deployment traces
    """
    environment = os.getenv("TRACE_ENVIRONMENT", "production")

    if environment == "production":
        return os.getenv("LANGSMITH_PROJECT_PRODUCTION", "code-chef-production")
    elif environment == "evaluation":
        return os.getenv("LANGSMITH_PROJECT_EVALUATION", "code-chef-evaluation")
    elif environment == "training":
        return os.getenv("LANGSMITH_PROJECT_TRAINING", "code-chef-training")
    else:
        return os.getenv("LANGSMITH_PROJECT", "code-chef-infrastructure")


class DeploymentConfig(BaseModel):
    """Configuration for model deployment."""

    agent_name: str = Field(..., description="Target agent for deployment")
    model_repo: str = Field(
        ...,
        description="HuggingFace model repo (e.g., alextorelli/codechef-feature-dev-v1)",
    )
    deployment_target: Literal["openrouter", "huggingface"] = Field(
        default="openrouter", description="Where to deploy the model"
    )
    version: Optional[str] = Field(None, description="Version tag for this deployment")


class DeploymentResult(BaseModel):
    """Result from model deployment operation."""

    deployed: bool
    agent_name: str
    model_repo: str
    version: str
    deployment_target: str
    endpoint_url: Optional[str] = None
    config_path: str
    deployed_at: str
    previous_model: Optional[str] = None
    rollback_available: bool


class ModelOpsDeployment:
    """Manages model deployment and rollbacks."""

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        models_config_path: Optional[str] = None,
    ):
        """Initialize deployment manager.

        Args:
            registry: ModelRegistry instance (creates new if None)
            models_config_path: Path to models.yaml (auto-detects if None)
        """
        self.registry = registry or ModelRegistry()

        # Auto-detect models.yaml path
        if models_config_path is None:
            # In Docker container, config is mounted at /app/config
            # In local dev, use relative path from repo root
            if Path("/app/config/agents/models.yaml").exists():
                models_config_path = "/app/config/agents/models.yaml"
            else:
                # deployment.py is at: agent_orchestrator/agents/infrastructure/modelops/deployment.py
                # Go up 4 levels to repo root: modelops -> infrastructure -> agents -> agent_orchestrator -> repo_root
                base_path = Path(__file__).parent.parent.parent.parent
                models_config_path = base_path / "config" / "agents" / "models.yaml"

        self.models_config_path = Path(models_config_path)

        if not self.models_config_path.exists():
            raise FileNotFoundError(
                f"Models config not found: {self.models_config_path}"
            )

    @traceable(
        name="deploy_model_to_agent",
        project_name=_get_langsmith_project(),
        metadata=_get_deployment_trace_metadata(),
    )
    async def deploy_model_to_agent(
        self,
        agent_name: str,
        model_repo: str,
        deployment_target: str = "openrouter",
        version: Optional[str] = None,
    ) -> DeploymentResult:
        """Deploy a fine-tuned model to an agent.

        Updates config/agents/models.yaml with the new model and records
        deployment in the model registry.

        Args:
            agent_name: Agent to deploy to (feature_dev, code_review, etc.)
            model_repo: HuggingFace model repo path
            deployment_target: "openrouter" or "huggingface"
            version: Optional version tag (auto-detected from registry if None)

        Returns:
            DeploymentResult with deployment details
        """
        # Load current models config
        with open(self.models_config_path, "r", encoding="utf-8") as f:
            models_config = yaml.safe_load(f)

        # Get current model for rollback
        current_model = None
        if deployment_target == "openrouter":
            current_model = (
                models_config.get("openrouter", {})
                .get("agent_models", {})
                .get(agent_name)
            )

        # Determine version from registry if not provided
        if version is None:
            agent_versions = self.registry.list_versions(agent_name)
            if agent_versions:
                # Find version matching this model_repo
                for v in agent_versions:
                    if v.hub_repo == model_repo:
                        version = v.version
                        break
                if version is None:
                    version = "v1.0.0"  # Default if not found
            else:
                version = "v1.0.0"

        # Update models.yaml based on deployment target
        if deployment_target == "openrouter":
            if "openrouter" not in models_config:
                models_config["openrouter"] = {}
            if "agent_models" not in models_config["openrouter"]:
                models_config["openrouter"]["agent_models"] = {}

            models_config["openrouter"]["agent_models"][agent_name] = model_repo
            endpoint_url = "https://openrouter.ai/api/v1"

        elif deployment_target == "huggingface":
            if "huggingface" not in models_config:
                models_config["huggingface"] = {"agent_models": {}}
            if "agent_models" not in models_config["huggingface"]:
                models_config["huggingface"]["agent_models"] = {}

            models_config["huggingface"]["agent_models"][agent_name] = model_repo
            endpoint_url = f"https://api-inference.huggingface.co/models/{model_repo}"

        else:
            raise ValueError(f"Unknown deployment target: {deployment_target}")

        # Create backup before modifying
        backup_path = self.models_config_path.with_suffix(".yaml.bak")
        shutil.copy(self.models_config_path, backup_path)

        # Write updated config
        with open(self.models_config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(models_config, f, default_flow_style=False, sort_keys=False)

        # Update registry with deployment info
        deployed_at = datetime.utcnow().isoformat() + "Z"

        # Get the version from registry to update deployment status
        versions = self.registry.list_versions(agent_name)
        version_found = None
        for v in versions:
            if v.hub_repo == model_repo or v.version == version:
                version_found = v
                break

        if version_found:
            # Set as current model in registry
            self.registry.set_current_model(agent_name, version_found.version)

        return DeploymentResult(
            deployed=True,
            agent_name=agent_name,
            model_repo=model_repo,
            version=version,
            deployment_target=deployment_target,
            endpoint_url=endpoint_url,
            config_path=str(self.models_config_path),
            deployed_at=deployed_at,
            previous_model=current_model,
            rollback_available=(current_model is not None),
        )

    @traceable(
        name="rollback_deployment",
        project_name=_get_langsmith_project(),
        metadata=_get_deployment_trace_metadata(),
    )
    async def rollback_deployment(
        self, agent_name: str, to_version: Optional[str] = None
    ) -> DeploymentResult:
        """Rollback to a previous model version.

        Args:
            agent_name: Agent to rollback
            to_version: Version to rollback to (uses previous if None)

        Returns:
            DeploymentResult with rollback info
        """
        # Get agent history
        versions = self.registry.list_versions(agent_name)
        if not versions:
            raise ValueError(f"No version history found for {agent_name}")

        # Find target version
        target_version = None
        if to_version:
            target_version = self.registry.get_version(agent_name, to_version)
            if not target_version:
                raise ValueError(f"Version {to_version} not found for {agent_name}")
        else:
            # Get current and find previous deployed version
            current = self.registry.get_current_model(agent_name)
            if not current:
                raise ValueError(f"No current version for {agent_name}")

            # Find most recent deployed version before current
            current_version = current.version
            for v in versions:
                if (
                    v.version != current_version
                    and v.deployment_status in ["deployed", "archived"]
                    and v.deployed_at
                ):
                    target_version = v
                    break

            if not target_version:
                raise ValueError(f"No previous version to rollback to for {agent_name}")

        # Deploy the target version
        return await self.deploy_model_to_agent(
            agent_name=agent_name,
            model_repo=target_version.hub_repo,
            deployment_target="openrouter",
            version=target_version.version,
        )

    @traceable(
        name="list_agent_models",
        project_name=_get_langsmith_project(),
        metadata=_get_deployment_trace_metadata(),
    )
    async def list_agent_models(
        self, agent_name: str, include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """List all model versions for an agent.

        Args:
            agent_name: Agent to list models for
            include_archived: Include archived versions

        Returns:
            List of model version dictionaries with metadata
        """
        versions = self.registry.list_versions(agent_name)

        # Filter archived if needed
        if not include_archived:
            versions = [v for v in versions if v.deployment_status != "archived"]

        # Convert to dicts with readable format
        result = []
        for v in versions:
            result.append(
                {
                    "version": v.version,
                    "model_id": v.model_id,
                    "hub_repo": v.hub_repo,
                    "base_model": v.training_config.base_model,
                    "training_method": v.training_config.training_method,
                    "trained_at": v.trained_at,
                    "trained_by": v.trained_by,
                    "deployment_status": v.deployment_status,
                    "deployed_at": v.deployed_at,
                    "eval_scores": (
                        v.eval_scores.model_dump() if v.eval_scores else None
                    ),
                    "job_id": v.job_id,
                }
            )

        return result

    @traceable(
        name="get_current_model",
        project_name=_get_langsmith_project(),
        metadata=_get_deployment_trace_metadata(),
    )
    async def get_current_model(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get currently deployed model for an agent.

        Args:
            agent_name: Agent to get current model for

        Returns:
            Current model info dict or None
        """
        current = self.registry.get_current_model(agent_name)
        if not current:
            return None

        return {
            "version": current.version,
            "model_id": current.model_id,
            "hub_repo": current.hub_repo,
            "deployment_status": current.deployment_status,
            "deployed_at": current.deployed_at,
            "eval_scores": (
                current.eval_scores.model_dump() if current.eval_scores else None
            ),
        }
