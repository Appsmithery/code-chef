"""Infrastructure agent for Terraform, Kubernetes, and cloud operations."""

from pathlib import Path
from typing import Any, Dict, Optional

from .._shared.base_agent import BaseAgent
from .modelops.coordinator import ModelOpsCoordinator


class InfrastructureAgent(BaseAgent):
    """Infrastructure agent specialized in cloud and container orchestration.

    Uses llama-3.1-8b model for infrastructure operations.
    Has access to Terraform, Kubernetes, Docker, and ModelOps tools.
    """

    def __init__(self, config_path: str = None):
        """Initialize infrastructure agent.

        Args:
            config_path: Path to infrastructure config (defaults to tools/infrastructure_tools.yaml)
        """
        if config_path is None:
            config_path = Path(__file__).parent / "tools.yaml"

        super().__init__(str(config_path), agent_name="infrastructure")

        # Initialize ModelOps coordinator for model training/deployment
        self.modelops = ModelOpsCoordinator()

    async def handle_modelops_request(
        self, message: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle ModelOps-related requests.

        This method routes model training, evaluation, and deployment requests
        to the ModelOps coordinator.

        Args:
            message: User message/intent
            context: Additional context (agent_name, model_id, etc.)

        Returns:
            Result dictionary from ModelOps operation

        Example:
            >>> agent = InfrastructureAgent()
            >>> result = await agent.handle_modelops_request(
            ...     "Train feature_dev model",
            ...     {"agent_name": "feature_dev", "langsmith_project": "code-chef-feature-dev"}
            ... )
        """
        context = context or {}
        return await self.modelops.route_request(message, context)
