"""Documentation agent for technical writing and knowledge management."""

from pathlib import Path

from .._shared.base_agent import BaseAgent


class DocumentationAgent(BaseAgent):
    """Documentation agent specialized in technical writing.

    Uses mistral-7b model optimized for documentation.
    Has access to Confluence, Markdown, and filesystem tools.
    """

    def __init__(self, config_path: str = None, project_context: dict = None):
        """Initialize documentation agent.

        Args:
            config_path: Path to documentation config (defaults to tools/documentation_tools.yaml)
            project_context: Project context dict with project_id, repository_url, workspace_name
        """
        if config_path is None:
            config_path = Path(__file__).parent / "tools.yaml"

        super().__init__(
            str(config_path),
            agent_name="documentation",
            project_context=project_context,
        )
