"""LangGraph agent nodes for multi-agent workflows."""

from typing import Optional

from ._shared.base_agent import BaseAgent
from .cicd import CICDAgent
from .code_review import CodeReviewAgent
from .documentation import DocumentationAgent
from .feature_dev import FeatureDevAgent
from .infrastructure import InfrastructureAgent
from .supervisor import SupervisorAgent

# Agent registry (lazy loaded)
_agents = {}


def get_agent(agent_name: str, project_context: Optional[dict] = None):
    """Get or create agent instance.

    Args:
        agent_name: Name of agent (supervisor, feature-dev, code-review, etc.)
        project_context: Project context dict with project_id, repository_url, workspace_name

    Returns:
        Agent instance
    """
    # Create cache key including project context for isolation
    cache_key = agent_name
    if project_context:
        project_id = project_context.get("project_id", "")
        cache_key = f"{agent_name}:{project_id}"

    if cache_key not in _agents:
        agent_classes = {
            "supervisor": SupervisorAgent,
            "feature-dev": FeatureDevAgent,
            "code-review": CodeReviewAgent,
            "infrastructure": InfrastructureAgent,
            "cicd": CICDAgent,
            "documentation": DocumentationAgent,
        }
        _agents[cache_key] = agent_classes[agent_name](project_context=project_context)

    return _agents[cache_key]


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
