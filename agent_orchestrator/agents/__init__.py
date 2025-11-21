"""LangGraph agent nodes for multi-agent workflows."""

from .base_agent import BaseAgent
from .supervisor import SupervisorAgent
from .feature_dev import FeatureDevAgent
from .code_review import CodeReviewAgent
from .infrastructure import InfrastructureAgent
from .cicd import CICDAgent
from .documentation import DocumentationAgent

# Agent registry (lazy loaded)
_agents = {}

def get_agent(agent_name: str):
    """Get or create agent instance.
    
    Args:
        agent_name: Name of agent (supervisor, feature-dev, code-review, etc.)
    
    Returns:
        Agent instance
    """
    if agent_name not in _agents:
        agent_classes = {
            "supervisor": SupervisorAgent,
            "feature-dev": FeatureDevAgent,
            "code-review": CodeReviewAgent,
            "infrastructure": InfrastructureAgent,
            "cicd": CICDAgent,
            "documentation": DocumentationAgent,
        }
        _agents[agent_name] = agent_classes[agent_name]()
    
    return _agents[agent_name]

__all__ = [
    "BaseAgent",
    "SupervisorAgent",
    "FeatureDevAgent",
    "CodeReviewAgent",
    "InfrastructureAgent",
    "CICDAgent",
    "DocumentationAgent",
    "get_agent",
]
