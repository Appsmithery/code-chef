"""Infrastructure agent for Terraform, Kubernetes, and cloud operations."""

from pathlib import Path
from .._shared.base_agent import BaseAgent


class InfrastructureAgent(BaseAgent):
    """Infrastructure agent specialized in cloud and container orchestration.

    Uses llama-3.1-8b model for infrastructure operations.
    Has access to Terraform, Kubernetes, and Docker tools.
    """

    def __init__(self, config_path: str = None):
        """Initialize infrastructure agent.

        Args:
            config_path: Path to infrastructure config (defaults to tools/infrastructure_tools.yaml)
        """
        if config_path is None:
            config_path = Path(__file__).parent / "tools.yaml"

        super().__init__(str(config_path), agent_name="infrastructure")
