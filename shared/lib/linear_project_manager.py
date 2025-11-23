"""
Linear Project Manager

Handles automatic Linear project creation for new workspaces.
Projects are auto-created based on workspace name and GitHub repo URL.
"""

from typing import Optional, Dict, List
import logging
from lib.linear_workspace_client import get_linear_client

logger = logging.getLogger(__name__)


class LinearProjectManager:
    """Manages Linear project lifecycle for workspaces."""

    def __init__(self, linear_client, default_team_id: str):
        """
        Initialize with Linear client and default team.

        Args:
            linear_client: LinearWorkspaceClient instance
            default_team_id: Team ID from .env (e.g., "f5b610be-ac34-4983-918b-2c9d00aa9b7a")
        """
        self.linear = linear_client
        self.default_team_id = default_team_id
        logger.info(f"Initialized LinearProjectManager with team: {default_team_id}")

    async def get_or_create_project(
        self,
        workspace_name: str,
        github_repo_url: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Get existing project or create new one for workspace.

        Args:
            workspace_name: Name of workspace (e.g., "my-app")
            github_repo_url: GitHub repo URL (optional, for description)
            project_id: Existing project ID from workspace settings (optional)

        Returns:
            Dict with keys: id, identifier, name, url

        Example:
            >>> manager = LinearProjectManager(linear_client, "team-123")
            >>> project = await manager.get_or_create_project(
            ...     "my-app",
            ...     "https://github.com/user/my-app"
            ... )
            >>> project["id"]
            "proj-abc123"
        """
        # If project ID provided, verify it exists
        if project_id:
            try:
                project = await self.linear.get_project(project_id)
                logger.info(
                    f"Using existing Linear project: {project.get('name')} ({project_id})"
                )
                return {
                    "id": project["id"],
                    "identifier": project.get("identifier", ""),
                    "name": project.get("name", workspace_name),
                    "url": project.get("url", ""),
                }
            except Exception as e:
                logger.warning(
                    f"Project ID {project_id} not found, will create new: {e}"
                )

        # Search for project by name (in case it exists but not cached)
        try:
            projects = await self._search_projects_by_name(workspace_name)
            if projects:
                project = projects[0]
                logger.info(f"Found existing project by name: {project.get('name')}")
                return {
                    "id": project["id"],
                    "identifier": project.get("identifier", ""),
                    "name": project.get("name", workspace_name),
                    "url": project.get("url", ""),
                }
        except Exception as e:
            logger.warning(f"Failed to search for existing project: {e}")

        # Create new project
        logger.info(f"Creating new Linear project for workspace: {workspace_name}")

        description = f"**Workspace**: {workspace_name}\n\n"
        if github_repo_url:
            description += f"**Repository**: {github_repo_url}\n\n"
        description += "Managed by Dev-Tools AI agent system."

        try:
            project = await self.linear.create_project(
                name=workspace_name,
                team_id=self.default_team_id,
                description=description,
                state="planned",  # Start in "Planned" state
            )

            logger.info(
                f"✅ Created Linear project: {project.get('name')} ({project['id']})"
            )
            return {
                "id": project["id"],
                "identifier": project.get("identifier", ""),
                "name": project.get("name", workspace_name),
                "url": project.get("url", ""),
            }
        except Exception as e:
            logger.error(f"Failed to create Linear project: {e}", exc_info=True)
            # Return minimal info to allow task to proceed
            return {"id": "", "identifier": "", "name": workspace_name, "url": ""}

    async def _search_projects_by_name(self, workspace_name: str) -> List[Dict]:
        """
        Search for projects by name in the default team.

        Args:
            workspace_name: Workspace name to search for

        Returns:
            List of matching projects
        """
        try:
            # Use Linear GraphQL to list projects
            # Filter by team and search name
            projects = await self.linear.list_projects(
                team_id=self.default_team_id, query=workspace_name
            )

            # Exact match filter
            matching = [
                p
                for p in projects
                if p.get("name", "").lower() == workspace_name.lower()
            ]

            return matching
        except Exception as e:
            logger.error(f"Error searching projects: {e}")
            return []


# Global singleton
_project_manager: Optional[LinearProjectManager] = None


def get_project_manager() -> LinearProjectManager:
    """Get global LinearProjectManager instance."""
    global _project_manager
    if _project_manager is None:
        import os

        linear_client = get_linear_client()
        team_id = os.getenv("LINEAR_TEAM_ID", "f5b610be-ac34-4983-918b-2c9d00aa9b7a")
        _project_manager = LinearProjectManager(linear_client, team_id)
    return _project_manager
