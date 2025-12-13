"""CI/CD agent for build, test, and deployment pipelines."""

from pathlib import Path
from typing import Optional

from .._shared.base_agent import BaseAgent


class CICDAgent(BaseAgent):
    """CI/CD agent specialized in continuous integration and deployment.

    Uses Gemini 2.0 Flash (OpenRouter) for pipeline operations.
    Has access to Jenkins, GitHub Actions, and Docker tools.
    """

    def __init__(
        self, config_path: Optional[str] = None, project_context: Optional[dict] = None
    ):
        """Initialize cicd agent.

        Args:
            config_path: Path to cicd config (defaults to tools/cicd_tools.yaml)
            project_context: Project context dict with project_id, repository_url, workspace_name
        """
        if config_path is None:
            config_path = str(Path(__file__).parent / "tools.yaml")

        super().__init__(
            str(config_path), agent_name="cicd", project_context=project_context
        )
