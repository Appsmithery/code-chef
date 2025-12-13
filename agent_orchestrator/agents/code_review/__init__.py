"""Code review agent for quality assurance and security analysis."""

from pathlib import Path

from .._shared.base_agent import BaseAgent


class CodeReviewAgent(BaseAgent):
    """Code review agent specialized in quality and security analysis.

    Uses DeepSeek V3 (OpenRouter) for deep code analysis.
    Has access to GitHub, SonarQube, and git tools.
    """

    def __init__(self, config_path: str = None, project_context: dict = None):
        """Initialize code-review agent.

        Args:
            config_path: Path to code-review config (defaults to tools/code_review_tools.yaml)
            project_context: Project context dict with project_id, repository_url, workspace_name
        """
        if config_path is None:
            config_path = Path(__file__).parent / "tools.yaml"

        super().__init__(
            str(config_path), agent_name="code_review", project_context=project_context
        )
