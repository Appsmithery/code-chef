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
        """Handle ModelOps-related requests from VS Code or chat.

        This method routes model training, evaluation, and deployment requests
        to the ModelOps coordinator. It parses natural language intents and
        extracts structured context for the coordinator.

        Args:
            message: User message/intent (e.g., "Train feature_dev model using dataset X")
            context: Additional context (agent_name, model_id, langsmith_project, etc.)

        Returns:
            Structured result dictionary with job IDs, status, or error messages

        Example:
            >>> agent = InfrastructureAgent()
            >>> result = await agent.handle_modelops_request(
            ...     "Train feature_dev model",
            ...     {"agent_name": "feature_dev", "langsmith_project": "code-chef-feature-dev"}
            ... )
            >>> print(result["job_id"])  # "job_abc123"
        """
        context = context or {}

        # Enhanced intent detection for VS Code commands
        message_lower = message.lower()

        # Extract agent name if not in context
        if "agent_name" not in context:
            agent_names = [
                "feature_dev",
                "code_review",
                "infrastructure",
                "cicd",
                "documentation",
            ]
            for agent in agent_names:
                if agent in message_lower:
                    context["agent_name"] = agent
                    break

        # Extract model repo from message if present
        if "model_repo" not in context:
            # Look for HuggingFace repo pattern (username/model-name)
            import re

            repo_match = re.search(r"([a-zA-Z0-9_-]+)/([a-zA-Z0-9_-]+)", message)
            if repo_match:
                context["model_repo"] = repo_match.group(0)

        # Extract job ID for monitoring
        if "job_id" not in context:
            import re

            job_match = re.search(r"job[_\s]?([a-zA-Z0-9-]+)", message_lower)
            if job_match:
                context["job_id"] = job_match.group(1)

        # Route to coordinator
        try:
            result = await self.modelops.route_request(message, context)

            # Ensure response is JSON-serializable for VS Code
            if "error" not in result:
                result["success"] = True

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": message,
                "context": context,
            }
