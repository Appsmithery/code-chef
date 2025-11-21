"""Code review agent for quality assurance and security analysis."""

from pathlib import Path
from .base_agent import BaseAgent


class CodeReviewAgent(BaseAgent):
    """Code review agent specialized in quality and security analysis.
    
    Uses llama-3.1-70b model for deep code analysis.
    Has access to GitHub, SonarQube, and git tools.
    """
    
    def __init__(self, config_path: str = None):
        """Initialize code-review agent.
        
        Args:
            config_path: Path to code-review config (defaults to tools/code_review_tools.yaml)
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "tools" / "code_review_tools.yaml"
        
        super().__init__(str(config_path), agent_name="code-review")
