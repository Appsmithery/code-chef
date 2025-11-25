"""Supervisor agent for task routing and workflow orchestration."""

from pathlib import Path
from typing import Optional
from .._shared.base_agent import BaseAgent


class SupervisorAgent(BaseAgent):
    """Supervisor agent that routes tasks to specialized agents.

    Uses llama-3.1-70b model for complex routing decisions.
    Analyzes tasks and determines which specialized agent should handle them.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize supervisor agent.

        Args:
            config_path: Path to supervisor config (defaults to tools.yaml in agent directory)
        """
        if config_path is None:
            config_path = str(Path(__file__).parent / "tools.yaml")

        super().__init__(str(config_path), agent_name="supervisor")
