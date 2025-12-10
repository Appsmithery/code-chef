"""Model deployment and lifecycle management for ModelOps.

Handles:
- Deploying fine-tuned models to agents (update models.yaml)
- Canary deployments with traffic splitting
- Model rollback procedures
- Listing agent model versions
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from langsmith import traceable
from pydantic import BaseModel, Field

from .registry import ModelRegistry, ModelVersion


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
    rollout_strategy: Literal["immediate", "canary_20pct", "canary_50pct"] = Field(
        default="immediate", description="Deployment rollout strategy"
    )
    version: Optional[str] = Field(None, description="Version tag for this deployment")


class DeploymentResult(BaseModel):
    """Result from model deployment operation."""

    deployed: bool
    agent_name: str
    model_repo: str
    version: str
    deployment_target: str
    rollout_pct: int = Field(..., description="Percentage of traffic to new model")
    endpoint_url: Optional[str] = None
    config_path: str
    deployed_at: str
    previous_model: Optional[str] = None
    rollback_available: bool


class ModelOpsDeployment:
    """Manages model deployment, canary rollouts, and rollbacks."""

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
            base_path = Path(__file__).parent.parent.parent.parent.parent
            models_config_path = base_path / "config" / "agents" / "models.yaml"

        self.models_config_path = Path(models_config_path)

        if not self.models_config_path.exists():
            raise FileNotFoundError(
                f"Models config not found: {self.models_config_path}"
            )

    @traceable(name="deploy_model_to_agent")
    async def deploy_model_to_agent(
        self,
        agent_name: str,
        model_repo: str,
        deployment_target: str = "openrouter",
        rollout_strategy: str = "immediate",
        version: Optional[str] = None,
    ) -> DeploymentResult:
        """Deploy a fine-tuned model to an agent.

        Updates config/agents/models.yaml with the new model and records
        deployment in the model registry.

        Args:
            agent_name: Agent to deploy to (feature_dev, code_review, etc.)
            model_repo: HuggingFace model repo path
            deployment_target: "openrouter" or "huggingface"
            rollout_strategy: "immediate", "canary_20pct", or "canary_50pct"
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

        # Determine rollout percentage
        rollout_pct_map = {"immediate": 100, "canary_20pct": 20, "canary_50pct": 50}
        rollout_pct = rollout_pct_map.get(rollout_strategy, 100)

        # Map rollout strategy to deployment status
        status_map = {
            "immediate": "deployed",
            "canary_20pct": "canary_20pct",
            "canary_50pct": "canary_50pct",
        }
        deployment_status = status_map.get(rollout_strategy, "deployed")

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
            # Update existing version in history
            # The registry API doesn't have update_version, so we'll update via set_current or set_canary

            # If immediate deployment, set as current
            if rollout_strategy == "immediate":
                self.registry.set_current_model(agent_name, version_found.version)
            # If canary, set as canary
            elif "canary" in rollout_strategy:
                canary_pct = 20 if "20" in rollout_strategy else 50
                self.registry.set_canary_model(
                    agent_name, version_found.version, canary_pct
                )

        return DeploymentResult(
            deployed=True,
            agent_name=agent_name,
            model_repo=model_repo,
            version=version,
            deployment_target=deployment_target,
            rollout_pct=rollout_pct,
            endpoint_url=endpoint_url,
            config_path=str(self.models_config_path),
            deployed_at=deployed_at,
            previous_model=current_model,
            rollback_available=(current_model is not None),
        )

    @traceable(name="promote_canary")
    async def promote_canary(
        self, agent_name: str, to_percentage: int = 100
    ) -> DeploymentResult:
        """Promote canary deployment to higher traffic percentage.

        Args:
            agent_name: Agent with canary deployment
            to_percentage: Target traffic percentage (50 or 100)

        Returns:
            DeploymentResult with updated rollout info
        """
        # Get canary version from registry
        canary_version = self.registry.get_canary_model(agent_name)
        if not canary_version:
            raise ValueError(f"No canary deployment found for {agent_name}")

        # Map percentage to strategy and status
        if to_percentage == 50:
            # Update to 50% canary
            self.registry.set_canary_model(agent_name, canary_version.version, 50)
        elif to_percentage == 100:
            # Promote to current
            self.registry.promote_canary_to_current(agent_name)
        else:
            raise ValueError(f"Invalid percentage: {to_percentage}. Use 50 or 100.")

        # Get updated current model
        current = self.registry.get_current_model(agent_name)

        return DeploymentResult(
            deployed=True,
            agent_name=agent_name,
            model_repo=canary_version.hub_repo,
            version=canary_version.version,
            deployment_target="openrouter",  # Assuming OpenRouter for now
            rollout_pct=to_percentage,
            endpoint_url="https://openrouter.ai/api/v1",
            config_path=str(self.models_config_path),
            deployed_at=datetime.utcnow().isoformat() + "Z",
            previous_model=(
                current.model_id if current and to_percentage == 100 else None
            ),
            rollback_available=True,
        )

    @traceable(name="rollback_deployment")
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
            rollout_strategy="immediate",
            version=target_version.version,
        )

    @traceable(name="list_agent_models")
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

    @traceable(name="get_current_model")
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
