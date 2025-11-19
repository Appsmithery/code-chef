"""
Linear Client Factory - Security-Scoped Client Creation

Creates Linear clients with appropriate permission scoping:
- Orchestrator: Workspace-level (can post to approval hub)
- Subagents: Project-level (can only access assigned project)

Usage:
    from shared.lib.linear_client_factory import get_linear_client
    
    # Orchestrator gets workspace client
    client = get_linear_client(agent_name="orchestrator")
    await client.post_to_approval_hub(...)
    
    # Subagent gets project-scoped client
    client = get_linear_client(agent_name="feature-dev", project_name="phase-5-chat")
    await client.create_issue(...)
"""

import os
import logging
from typing import Optional, Union
import yaml

from .linear_workspace_client import LinearWorkspaceClient
from .linear_project_client import LinearProjectClient

logger = logging.getLogger(__name__)

# Project registry cache
_project_registry = None


def _load_project_registry() -> dict:
    """
    Load project registry from config file.
    
    Returns:
        Dict mapping project_name -> project_id
    """
    global _project_registry
    
    if _project_registry is not None:
        return _project_registry
    
    registry_path = os.path.join(
        os.path.dirname(__file__),
        "..", "..",
        "config", "linear", "project-registry.yaml"
    )
    
    if not os.path.exists(registry_path):
        logger.warning(f"Project registry not found: {registry_path}")
        _project_registry = {}
        return _project_registry
    
    with open(registry_path, "r") as f:
        _project_registry = yaml.safe_load(f)
    
    logger.info(f"Loaded {len(_project_registry)} projects from registry")
    return _project_registry


def get_linear_client(
    agent_name: str,
    project_name: Optional[str] = None,
    api_key: Optional[str] = None
) -> Union[LinearWorkspaceClient, LinearProjectClient]:
    """
    Get Linear client with security-appropriate scoping.
    
    Security Rules:
    - Orchestrator: Workspace-level client (can access approval hub)
    - Subagents: Project-level client (can only access assigned project)
    
    Args:
        agent_name: Name of agent requesting client (orchestrator, feature-dev, etc.)
        project_name: Name of project to scope to (required for subagents)
        api_key: Linear OAuth token (uses LINEAR_API_KEY env if not provided)
    
    Returns:
        LinearWorkspaceClient for orchestrator, LinearProjectClient for subagents
    
    Raises:
        ValueError: If subagent doesn't provide project_name
        ValueError: If project_name not in registry
    """
    # Orchestrator gets workspace-level access
    if agent_name == "orchestrator":
        logger.info("Creating workspace-level Linear client for orchestrator")
        return LinearWorkspaceClient(api_key=api_key)
    
    # Subagents MUST provide project_name
    if not project_name:
        raise ValueError(
            f"Agent '{agent_name}' requires project_name for Linear access. "
            "Security policy: subagents cannot access workspace-level resources."
        )
    
    # Look up project ID from registry
    registry = _load_project_registry()
    
    if project_name not in registry:
        available_projects = ", ".join(registry.keys())
        raise ValueError(
            f"Project '{project_name}' not found in registry. "
            f"Available: {available_projects}"
        )
    
    project_id = registry[project_name]["project_id"]
    
    logger.info(
        f"Creating project-scoped Linear client for {agent_name} "
        f"(project: {project_name}, id: {project_id})"
    )
    
    return LinearProjectClient(
        project_id=project_id,
        api_key=api_key
    )


def refresh_project_registry() -> None:
    """
    Force reload of project registry from disk.
    
    Call this after updating project-registry.yaml.
    """
    global _project_registry
    _project_registry = None
    _load_project_registry()
    logger.info("Project registry refreshed")


# For testing/debugging
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test orchestrator client
    try:
        orchestrator_client = get_linear_client(agent_name="orchestrator")
        print(f"✅ Orchestrator client: {type(orchestrator_client).__name__}")
    except Exception as e:
        print(f"❌ Orchestrator client failed: {e}")
    
    # Test subagent without project_name (should fail)
    try:
        subagent_client = get_linear_client(agent_name="feature-dev")
        print(f"❌ Subagent without project_name should have failed!")
    except ValueError as e:
        print(f"✅ Subagent security check: {e}")
    
    # Test subagent with project_name (requires registry file)
    try:
        subagent_client = get_linear_client(
            agent_name="feature-dev",
            project_name="phase-5-chat"
        )
        print(f"✅ Subagent client: {type(subagent_client).__name__}")
    except Exception as e:
        print(f"⚠️  Subagent with project failed (registry may not exist): {e}")
