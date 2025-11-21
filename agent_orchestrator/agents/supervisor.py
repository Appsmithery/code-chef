"""Supervisor agent for task routing and workflow orchestration."""

from pathlib import Path
from .base_agent import BaseAgent


class SupervisorAgent(BaseAgent):
    """Supervisor agent that routes tasks to specialized agents.
    
    Uses llama-3.1-70b model for complex routing decisions.
    Analyzes tasks and determines which specialized agent should handle them.
    """
    
    def __init__(self, config_path: str = None):
        """Initialize supervisor agent.
        
        Args:
            config_path: Path to supervisor config (defaults to tools/supervisor_tools.yaml)
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "tools" / "supervisor_tools.yaml"
        
        super().__init__(str(config_path), agent_name="supervisor")
