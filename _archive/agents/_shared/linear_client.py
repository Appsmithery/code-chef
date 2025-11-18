"""
Direct Linear API access using Python SDK.
Only import this in agents that need Linear integration (orchestrator, documentation).
"""

import os
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class LinearIntegration:
    """
    Direct Linear API access without gateway.

    Requires LINEAR_API_KEY environment variable (Personal API token).
    """

    def __init__(self):
        self.api_key = os.getenv("LINEAR_API_KEY")
        self.enabled = bool(self.api_key)

        if self.enabled:
            # Use linear-sdk Python package (install via pip)
            try:
                from linear_sdk import LinearClient
                self.client = LinearClient(api_key=self.api_key)
                logger.info("[Linear] Client initialized with API key")
            except ImportError:
                logger.error("[Linear] linear-sdk package not installed")
                self.enabled = False
                self.client = None
        else:
            logger.warning("[Linear] No LINEAR_API_KEY found - Linear integration disabled")
            self.client = None

    def is_enabled(self) -> bool:
        """Check if Linear integration is available."""
        return self.enabled and self.client is not None

    async def fetch_issues(self, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Fetch issues from Linear workspace.

        Args:
            filters: Optional filters (e.g., {"state": "in_progress"})

        Returns:
            List of issue dictionaries
        """
        if not self.is_enabled():
            logger.warning("[Linear] Cannot fetch issues - integration disabled")
            return []

        try:
            issues = await self.client.issues(filter=filters or {}, first=50)

            return [
                {
                    "id": issue.id,
                    "title": issue.title,
                    "state": issue.state.name if issue.state else None,
                    "priority": issue.priority,
                    "assignee": issue.assignee.name if issue.assignee else None,
                    "url": issue.url,
                    "description": issue.description,
                    "created_at": issue.created_at.isoformat() if issue.created_at else None
                }
                for issue in issues.nodes
            ]

        except Exception as e:
            logger.error(f"[Linear] Failed to fetch issues: {e}", exc_info=True)
            return []

    async def create_issue(
        self,
        title: str,
        description: str,
        team_id: Optional[str] = None,
        priority: int = 0
    ) -> Optional[Dict]:
        """
        Create a new Linear issue.

        Args:
            title: Issue title
            description: Issue description
            team_id: Optional team ID (defaults to personal workspace)
            priority: Priority (0=None, 1=Urgent, 2=High, 3=Normal, 4=Low)

        Returns:
            Created issue data or None if failed
        """
        if not self.is_enabled():
            logger.warning("[Linear] Cannot create issue - integration disabled")
            return None

        try:
            issue = await self.client.create_issue(
                title=title,
                description=description,
                team_id=team_id,
                priority=priority
            )

            logger.info(f"[Linear] Created issue: {issue.id} - {title}")

            return {
                "id": issue.id,
                "title": issue.title,
                "url": issue.url,
                "identifier": issue.identifier
            }

        except Exception as e:
            logger.error(f"[Linear] Failed to create issue: {e}", exc_info=True)
            return None

    async def update_issue(
        self,
        issue_id: str,
        **updates
    ) -> bool:
        """
        Update an existing Linear issue.

        Args:
            issue_id: Linear issue ID
            **updates: Fields to update (title, description, state_id, priority, etc.)

        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            logger.warning("[Linear] Cannot update issue - integration disabled")
            return False

        try:
            await self.client.update_issue(issue_id, **updates)
            logger.info(f"[Linear] Updated issue: {issue_id}")
            return True

        except Exception as e:
            logger.error(f"[Linear] Failed to update issue {issue_id}: {e}", exc_info=True)
            return False

    async def fetch_project_roadmap(self, project_id: str) -> Dict[str, Any]:
        """
        Fetch project roadmap with associated issues.

        Args:
            project_id: Linear project ID

        Returns:
            Project data with issues
        """
        if not self.is_enabled():
            logger.warning("[Linear] Cannot fetch project - integration disabled")
            return {}

        try:
            project = await self.client.project(project_id)
            issues = await project.issues()

            return {
                "project": {
                    "id": project.id,
                    "name": project.name,
                    "state": project.state,
                    "progress": project.progress,
                    "description": project.description
                },
                "issues": [
                    {
                        "id": issue.id,
                        "title": issue.title,
                        "state": issue.state.name if issue.state else None,
                        "priority": issue.priority,
                        "url": issue.url
                    }
                    for issue in issues.nodes
                ]
            }

        except Exception as e:
            logger.error(f"[Linear] Failed to fetch project {project_id}: {e}", exc_info=True)
            return {}


# Singleton instance
_linear_instance: Optional[LinearIntegration] = None


def get_linear_client() -> LinearIntegration:
    """Get or create Linear client singleton."""
    global _linear_instance
    if _linear_instance is None:
        _linear_instance = LinearIntegration()
    return _linear_instance
