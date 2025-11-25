"""Feature development agent for implementing new features."""

from pathlib import Path
from .._shared.base_agent import BaseAgent


class FeatureDevAgent(BaseAgent):
    """Feature development agent specialized in code implementation.

    Uses codellama-13b model optimized for code generation.
    Has access to GitHub, filesystem, git, and docker tools.
    """

    def __init__(self, config_path: str = None):
        """Initialize feature-dev agent.

        Args:
            config_path: Path to feature-dev config (defaults to tools/feature_dev_tools.yaml)
        """
        if config_path is None:
            config_path = Path(__file__).parent / "tools.yaml"

        super().__init__(str(config_path), agent_name="feature_dev")
