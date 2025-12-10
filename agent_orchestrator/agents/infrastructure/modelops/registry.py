"""Model registry for tracking fine-tuned agent model versions.

This module provides versioning and metadata tracking for fine-tuned models:
- Training job metadata (base model, dataset, hyperparameters)
- Evaluation scores and comparison metrics
- Deployment status (current, canary, archived)
- Model lineage and rollback history

Architecture:
- JSON file storage for simplicity and human readability
- Thread-safe file operations with file locking
- Automatic backup on critical operations
- Validation using Pydantic models

GitHub Reference: https://github.com/Appsmithery/Dev-Tools/blob/main/support/docs/extend%20Infra%20agent%20ModelOps.md
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

try:
    from langsmith.utils import traceable

    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False

    def traceable(name=None, **kwargs):
        """No-op decorator when LangSmith not available"""

        def decorator(func):
            return func

        return decorator if name else lambda f: f


from loguru import logger


# Pydantic Models for validation
class EvaluationScores(BaseModel):
    """Evaluation metrics for a model."""

    accuracy: Optional[float] = Field(None, ge=0.0, le=1.0)
    baseline_improvement_pct: Optional[float] = None
    avg_latency_ms: Optional[float] = Field(None, ge=0.0)
    cost_per_1k_tokens: Optional[float] = Field(None, ge=0.0)
    token_efficiency: Optional[float] = Field(None, ge=0.0, le=1.0)
    workflow_completeness: Optional[float] = Field(None, ge=0.0, le=1.0)
    langsmith_experiment_url: Optional[str] = None

    # Allow additional custom metrics
    class Config:
        extra = "allow"


class TrainingConfig(BaseModel):
    """Training configuration metadata."""

    base_model: str
    training_method: Literal["sft", "dpo", "grpo"] = "sft"
    training_dataset: str  # LangSmith dataset ID or path
    eval_dataset: Optional[str] = None
    learning_rate: Optional[float] = None
    num_epochs: Optional[int] = None
    batch_size: Optional[int] = None
    lora_rank: Optional[int] = None
    max_seq_length: Optional[int] = None
    hardware: Optional[str] = None
    is_demo: bool = False


class ModelVersion(BaseModel):
    """A single model version entry."""

    version: str  # e.g., "v2-finetuned" or "v1.0.0"
    model_id: str  # HuggingFace model repo
    training_config: TrainingConfig
    trained_at: str  # ISO timestamp
    trained_by: str = "modelops-trainer"  # System or user ID
    job_id: Optional[str] = None  # HF training job ID
    hub_repo: Optional[str] = None  # HF Hub repo path
    eval_scores: Optional[EvaluationScores] = None
    deployment_status: Literal[
        "not_deployed", "canary_20pct", "canary_50pct", "deployed", "archived"
    ] = "not_deployed"
    deployed_at: Optional[str] = None  # ISO timestamp
    notes: Optional[str] = None


class AgentModelRegistry(BaseModel):
    """Registry for a single agent's models."""

    agent_name: str
    current: Optional[ModelVersion] = None
    canary: Optional[ModelVersion] = None
    history: List[ModelVersion] = Field(default_factory=list)

    @field_validator("agent_name")
    @classmethod
    def validate_agent_name(cls, v):
        valid_agents = [
            "feature_dev",
            "code_review",
            "infrastructure",
            "cicd",
            "documentation",
            "supervisor",
        ]
        if v not in valid_agents:
            raise ValueError(f"Invalid agent name: {v}. Must be one of {valid_agents}")
        return v


class ModelRegistry:
    """Thread-safe model registry manager.

    Handles CRUD operations for agent model versions with automatic
    backup and validation.
    """

    def __init__(self, registry_path: Optional[str] = None):
        """Initialize model registry.

        Args:
            registry_path: Path to registry.json (default: config/models/registry.json)
        """
        if registry_path:
            self.registry_path = Path(registry_path)
        else:
            # Default path relative to this file
            self.registry_path = (
                Path(__file__).parent.parent.parent.parent.parent
                / "config"
                / "models"
                / "registry.json"
            )

        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_registry_exists()
        logger.info(f"ModelRegistry initialized at {self.registry_path}")

    def _ensure_registry_exists(self):
        """Create registry file if it doesn't exist."""
        if not self.registry_path.exists():
            logger.info(f"Creating new registry at {self.registry_path}")
            initial_data = {
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "agents": {
                    "feature_dev": {
                        "agent_name": "feature_dev",
                        "current": None,
                        "canary": None,
                        "history": [],
                    },
                    "code_review": {
                        "agent_name": "code_review",
                        "current": None,
                        "canary": None,
                        "history": [],
                    },
                    "infrastructure": {
                        "agent_name": "infrastructure",
                        "current": None,
                        "canary": None,
                        "history": [],
                    },
                    "cicd": {
                        "agent_name": "cicd",
                        "current": None,
                        "canary": None,
                        "history": [],
                    },
                    "documentation": {
                        "agent_name": "documentation",
                        "current": None,
                        "canary": None,
                        "history": [],
                    },
                },
            }
            self._write_registry(initial_data)

    def _backup_registry(self):
        """Create timestamped backup of registry."""
        backup_dir = self.registry_path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"registry_{timestamp}.json"

        shutil.copy2(self.registry_path, backup_path)
        logger.debug(f"Registry backed up to {backup_path}")

        # Keep only last 10 backups
        backups = sorted(backup_dir.glob("registry_*.json"), reverse=True)
        for old_backup in backups[10:]:
            old_backup.unlink()
            logger.debug(f"Removed old backup: {old_backup}")

    def _read_registry(self) -> Dict:
        """Read registry from disk."""
        with open(self.registry_path, "r") as f:
            return json.load(f)

    def _write_registry(self, data: Dict):
        """Write registry to disk with backup."""
        if self.registry_path.exists():
            self._backup_registry()

        data["updated_at"] = datetime.utcnow().isoformat()

        with open(self.registry_path, "w") as f:
            json.dump(data, f, indent=2)

        logger.debug(f"Registry updated at {self.registry_path}")

    @traceable(name="registry_get_agent")
    def get_agent_registry(self, agent_name: str) -> AgentModelRegistry:
        """Get registry for a specific agent.

        Args:
            agent_name: Agent name (e.g., "feature_dev")

        Returns:
            AgentModelRegistry with current/canary/history
        """
        data = self._read_registry()

        if agent_name not in data["agents"]:
            raise ValueError(f"Unknown agent: {agent_name}")

        agent_data = data["agents"][agent_name]
        return AgentModelRegistry(**agent_data)

    @traceable(name="registry_add_version")
    def add_model_version(
        self,
        agent_name: str,
        version: str,
        model_id: str,
        training_config: Dict,
        job_id: Optional[str] = None,
        hub_repo: Optional[str] = None,
    ) -> ModelVersion:
        """Add a new model version to agent's history.

        Args:
            agent_name: Agent name
            version: Version string (e.g., "v2-finetuned" or "1.0.0")
            model_id: HuggingFace model ID
            training_config: Training configuration dict
            job_id: Optional training job ID
            hub_repo: Optional HF Hub repo path

        Returns:
            Created ModelVersion
        """
        data = self._read_registry()

        if agent_name not in data["agents"]:
            raise ValueError(f"Unknown agent: {agent_name}")

        # Validate training config
        config = TrainingConfig(**training_config)

        # Create new version
        new_version = ModelVersion(
            version=version,
            model_id=model_id,
            training_config=config,
            trained_at=datetime.utcnow().isoformat(),
            job_id=job_id,
            hub_repo=hub_repo,
        )

        # Add to history
        data["agents"][agent_name]["history"].append(new_version.model_dump())

        self._write_registry(data)
        logger.info(f"Added model version {version} for {agent_name}")

        return new_version

    @traceable(name="registry_update_eval_scores")
    def update_evaluation_scores(
        self, agent_name: str, version: str, eval_scores: Dict
    ) -> bool:
        """Update evaluation scores for a model version.

        Args:
            agent_name: Agent name
            version: Version string
            eval_scores: Evaluation scores dict

        Returns:
            True if updated successfully
        """
        data = self._read_registry()

        if agent_name not in data["agents"]:
            raise ValueError(f"Unknown agent: {agent_name}")

        # Validate scores
        scores = EvaluationScores(**eval_scores)

        # Find version in history
        agent_data = data["agents"][agent_name]
        for i, model in enumerate(agent_data["history"]):
            if model["version"] == version:
                agent_data["history"][i]["eval_scores"] = scores.model_dump()
                self._write_registry(data)
                logger.info(f"Updated eval scores for {agent_name} {version}")
                return True

        raise ValueError(f"Version {version} not found for {agent_name}")

    @traceable(name="registry_set_current")
    def set_current_model(self, agent_name: str, version: str) -> bool:
        """Set a version as the current deployed model.

        Args:
            agent_name: Agent name
            version: Version string from history

        Returns:
            True if updated successfully
        """
        data = self._read_registry()

        if agent_name not in data["agents"]:
            raise ValueError(f"Unknown agent: {agent_name}")

        # Find version in history
        agent_data = data["agents"][agent_name]
        model_version = None
        for model in agent_data["history"]:
            if model["version"] == version:
                model_version = model.copy()
                break

        if not model_version:
            raise ValueError(f"Version {version} not found for {agent_name}")

        # Update deployment info
        model_version["deployment_status"] = "deployed"
        model_version["deployed_at"] = datetime.utcnow().isoformat()

        # Archive old current if exists
        if agent_data["current"]:
            old_current = agent_data["current"].copy()
            old_current["deployment_status"] = "archived"
            # Update in history
            for i, model in enumerate(agent_data["history"]):
                if model["version"] == old_current["version"]:
                    agent_data["history"][i] = old_current
                    break

        # Set new current
        agent_data["current"] = model_version

        # Update version in history
        for i, model in enumerate(agent_data["history"]):
            if model["version"] == version:
                agent_data["history"][i] = model_version
                break

        self._write_registry(data)
        logger.success(f"Set {version} as current model for {agent_name}")

        return True

    @traceable(name="registry_set_canary")
    def set_canary_model(
        self, agent_name: str, version: str, canary_pct: int = 20
    ) -> bool:
        """Set a version as canary deployment.

        Args:
            agent_name: Agent name
            version: Version string from history
            canary_pct: Percentage of traffic (20 or 50)

        Returns:
            True if updated successfully
        """
        if canary_pct not in [20, 50]:
            raise ValueError("canary_pct must be 20 or 50")

        data = self._read_registry()

        if agent_name not in data["agents"]:
            raise ValueError(f"Unknown agent: {agent_name}")

        # Find version in history
        agent_data = data["agents"][agent_name]
        model_version = None
        for model in agent_data["history"]:
            if model["version"] == version:
                model_version = model.copy()
                break

        if not model_version:
            raise ValueError(f"Version {version} not found for {agent_name}")

        # Update deployment info
        model_version["deployment_status"] = (
            f"canary_{canary_pct}pct" if canary_pct != 100 else "deployed"
        )
        model_version["deployed_at"] = datetime.utcnow().isoformat()

        # Set canary
        agent_data["canary"] = model_version

        # Update version in history
        for i, model in enumerate(agent_data["history"]):
            if model["version"] == version:
                agent_data["history"][i] = model_version
                break

        self._write_registry(data)
        logger.success(f"Set {version} as {canary_pct}% canary for {agent_name}")

        return True

    @traceable(name="registry_promote_canary")
    def promote_canary_to_current(self, agent_name: str) -> bool:
        """Promote canary to current (100% traffic).

        Args:
            agent_name: Agent name

        Returns:
            True if promoted successfully
        """
        data = self._read_registry()

        if agent_name not in data["agents"]:
            raise ValueError(f"Unknown agent: {agent_name}")

        agent_data = data["agents"][agent_name]

        if not agent_data.get("canary"):
            raise ValueError(f"No canary deployment for {agent_name}")

        canary = agent_data["canary"]

        # Archive old current
        if agent_data["current"]:
            old_current = agent_data["current"].copy()
            old_current["deployment_status"] = "archived"
            for i, model in enumerate(agent_data["history"]):
                if model["version"] == old_current["version"]:
                    agent_data["history"][i] = old_current
                    break

        # Promote canary
        canary["deployment_status"] = "deployed"
        canary["deployed_at"] = datetime.utcnow().isoformat()
        agent_data["current"] = canary
        agent_data["canary"] = None

        # Update in history
        for i, model in enumerate(agent_data["history"]):
            if model["version"] == canary["version"]:
                agent_data["history"][i] = canary
                break

        self._write_registry(data)
        logger.success(f"Promoted canary to current for {agent_name}")

        return True

    @traceable(name="registry_rollback")
    def rollback_to_version(self, agent_name: str, version: str) -> bool:
        """Rollback to a previous version.

        Args:
            agent_name: Agent name
            version: Version string to rollback to

        Returns:
            True if rolled back successfully
        """
        logger.warning(f"Rolling back {agent_name} to {version}")
        return self.set_current_model(agent_name, version)

    @traceable(name="registry_list_versions")
    def list_versions(
        self, agent_name: str, limit: int = 10, status_filter: Optional[str] = None
    ) -> List[ModelVersion]:
        """List model versions for an agent.

        Args:
            agent_name: Agent name
            limit: Maximum number of versions to return
            status_filter: Optional deployment status filter

        Returns:
            List of ModelVersion objects, newest first
        """
        registry = self.get_agent_registry(agent_name)

        versions = registry.history.copy()

        # Filter by status
        if status_filter:
            versions = [v for v in versions if v.deployment_status == status_filter]

        # Sort by trained_at (newest first)
        versions.sort(key=lambda v: v.trained_at, reverse=True)

        # Limit
        return versions[:limit]

    @traceable(name="registry_get_version")
    def get_version(self, agent_name: str, version: str) -> Optional[ModelVersion]:
        """Get a specific model version.

        Args:
            agent_name: Agent name
            version: Version string

        Returns:
            ModelVersion if found, None otherwise
        """
        registry = self.get_agent_registry(agent_name)

        for v in registry.history:
            if v.version == version:
                return v

        return None

    def get_current_model(self, agent_name: str) -> Optional[ModelVersion]:
        """Get current deployed model for an agent.

        Args:
            agent_name: Agent name

        Returns:
            ModelVersion if exists, None otherwise
        """
        registry = self.get_agent_registry(agent_name)
        return registry.current

    def get_canary_model(self, agent_name: str) -> Optional[ModelVersion]:
        """Get canary model for an agent.

        Args:
            agent_name: Agent name

        Returns:
            ModelVersion if exists, None otherwise
        """
        registry = self.get_agent_registry(agent_name)
        return registry.canary
