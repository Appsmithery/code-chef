"""CI/CD agent for build, test, and deployment pipelines."""

from pathlib import Path
from .base_agent import BaseAgent


class CICDAgent(BaseAgent):
    """CI/CD agent specialized in continuous integration and deployment.
    
    Uses llama-3.1-8b model for pipeline operations.
    Has access to Jenkins, GitHub Actions, and Docker tools.
    """
    
    def __init__(self, config_path: str = None):
        """Initialize cicd agent.
        
        Args:
            config_path: Path to cicd config (defaults to tools/cicd_tools.yaml)
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "tools" / "cicd_tools.yaml"
        
        super().__init__(str(config_path), agent_name="cicd")
