"""Feature development agent for implementing new features."""

from pathlib import Path

from .._shared.base_agent import BaseAgent


class FeatureDevAgent(BaseAgent):
    """Feature development agent specialized in code implementation.

    Uses codellama-13b model optimized for code generation.
    Has access to GitHub, filesystem, git, and docker tools.
    """

    def __init__(self, config_path: str = None, project_context: dict = None):
        """Initialize feature-dev agent.

        Args:
            config_path: Path to feature-dev config (defaults to tools/feature_dev_tools.yaml)
            project_context: Project context dict with project_id, repository_url, workspace_name
        """
        if config_path is None:
            config_path = Path(__file__).parent / "tools.yaml"

        super().__init__(
            str(config_path), agent_name="feature_dev", project_context=project_context
        )
