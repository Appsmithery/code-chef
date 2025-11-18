"""
Linear Roadmap Update Helper

Provides high-level functions for updating Linear project roadmap from agents.
Use these functions when you need to programmatically update Linear issues.
"""

import os
import httpx
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class LinearRoadmapUpdater:
    """Helper for updating Linear project roadmap via GraphQL API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize with Linear API key.
        
        Args:
            api_key: Linear OAuth token or Personal API key
        """
        self.api_key = api_key or os.getenv("LINEAR_API_KEY")
        self.graphql_endpoint = "https://api.linear.app/graphql"
        self.enabled = bool(self.api_key)
        
        if not self.enabled:
            logger.warning("Linear API key not configured - updates disabled")
    
    def is_enabled(self) -> bool:
        """Check if Linear integration is available."""
        return self.enabled
    
    async def update_issue_description(
        self, 
        issue_id: str, 
        description: str
    ) -> bool:
        """
        Update an issue's description.
        
        Args:
            issue_id: Linear issue ID
            description: New description (Markdown supported)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            logger.error("Cannot update issue - Linear not configured")
            return False
        
        mutation = """
        mutation IssueUpdate($id: String!, $description: String!) {
          issueUpdate(id: $id, input: { description: $description }) {
            success
            issue {
              id
              title
            }
          }
        }
        """
        
        variables = {
            "id": issue_id,
            "description": description
        }
        
        return await self._execute_mutation(mutation, variables)
    
    async def update_phase_completion(
        self,
        issue_id: str,
        phase_name: str,
        status: str = "COMPLETE",
        components: Optional[List[str]] = None,
        subtasks: Optional[List[Dict[str, str]]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        artifacts: Optional[Dict[str, str]] = None,
        tests: Optional[List[str]] = None,
        summary: Optional[str] = None,
        deployment_url: Optional[str] = None
    ) -> bool:
        """
        Update a phase issue with comprehensive completion information.
        
        Args:
            issue_id: Linear issue ID for the phase
            phase_name: Name of the phase (e.g., "Phase 2: HITL Integration")
            status: Status text (e.g., "COMPLETE", "IN PROGRESS")
            components: List of major components delivered
            subtasks: List of subtask dicts with 'title' and 'status'
            metrics: Dict of production metrics (e.g., {"requests": 4, "avg_time": "1.26s"})
            artifacts: Dict of code artifacts (path -> description)
            tests: List of test descriptions
            summary: Optional summary paragraph
            deployment_url: Optional deployment URL
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            logger.error("Cannot update phase - Linear not configured")
            return False
        
        # Build comprehensive description
        description_parts = [
            f"## {phase_name} - {status}",
            "",
        ]
        
        if summary:
            description_parts.extend([
                "### Implementation Summary",
                summary,
                "",
            ])
        
        if components:
            description_parts.extend([
                "### Components Delivered",
                *[f"{i+1}. **{comp}**" for i, comp in enumerate(components)],
                "",
            ])
        
        if subtasks:
            description_parts.extend([
                "### Subtasks Completed",
                *[f"- {'✅' if task.get('status') == 'complete' else '⏳'} {task['title']}" 
                  for task in subtasks],
                "",
            ])
        
        if metrics:
            description_parts.extend([
                f"### Production Metrics (as of {datetime.now().strftime('%Y-%m-%d')})",
                *[f"- {key.replace('_', ' ').title()}: {value}" 
                  for key, value in metrics.items()],
                "",
            ])
        
        if artifacts:
            description_parts.extend([
                "### Artifacts",
                *[f"- `{path}`: {desc}" for path, desc in artifacts.items()],
                "",
            ])
        
        if tests:
            description_parts.extend([
                "### Testing",
                *[f"✅ {test}" for test in tests],
                "",
            ])
        
        description_parts.extend([
            f"**Status**: {status}",
        ])
        
        if deployment_url:
            description_parts.append(f"**Deployment**: {deployment_url}")
        
        description = "\n".join(description_parts)
        
        success = await self.update_issue_description(issue_id, description)
        
        if success:
            logger.info(f"Updated Linear phase: {phase_name} - {status}")
        
        return success
    
    async def mark_issue_complete(
        self,
        issue_id: str,
        state_id: str
    ) -> bool:
        """
        Mark an issue as complete by updating its workflow state.
        
        Args:
            issue_id: Linear issue ID
            state_id: Workflow state ID for "completed" state
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            logger.error("Cannot mark complete - Linear not configured")
            return False
        
        mutation = """
        mutation IssueUpdate($id: String!, $stateId: String!) {
          issueUpdate(id: $id, input: { stateId: $stateId }) {
            success
            issue {
              id
              title
              state {
                name
              }
            }
          }
        }
        """
        
        variables = {
            "id": issue_id,
            "stateId": state_id
        }
        
        return await self._execute_mutation(mutation, variables)
    
    async def create_subtask(
        self,
        title: str,
        description: str,
        parent_id: str,
        project_id: str,
        team_id: str
    ) -> Optional[str]:
        """
        Create a new subtask under a parent issue.
        
        Args:
            title: Issue title
            description: Issue description (Markdown)
            parent_id: Parent issue ID
            project_id: Project ID
            team_id: Team ID
            
        Returns:
            Created issue ID if successful, None otherwise
        """
        if not self.is_enabled():
            logger.error("Cannot create subtask - Linear not configured")
            return None
        
        mutation = """
        mutation IssueCreate(
          $title: String!
          $description: String
          $projectId: String
          $parentId: String
          $teamId: String!
        ) {
          issueCreate(
            input: {
              title: $title
              description: $description
              projectId: $projectId
              parentId: $parentId
              teamId: $teamId
            }
          ) {
            success
            issue {
              id
              identifier
              url
            }
          }
        }
        """
        
        variables = {
            "title": title,
            "description": description,
            "projectId": project_id,
            "parentId": parent_id,
            "teamId": team_id
        }
        
        success = await self._execute_mutation(mutation, variables)
        
        if success:
            logger.info(f"Created Linear subtask: {title}")
            # Note: In production, parse response to get issue ID
            return "created"  # Placeholder
        
        return None
    
    async def _execute_mutation(
        self,
        mutation: str,
        variables: Dict[str, Any]
    ) -> bool:
        """
        Execute a GraphQL mutation.
        
        Args:
            mutation: GraphQL mutation string
            variables: Mutation variables
            
        Returns:
            True if successful, False otherwise
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if not self.api_key.startswith("Bearer ") else self.api_key
        }
        
        payload = {
            "query": mutation,
            "variables": variables
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.graphql_endpoint,
                    json=payload,
                    headers=headers
                )
                
                if response.status_code != 200:
                    logger.error(f"Linear API error: {response.status_code}")
                    return False
                
                result = response.json()
                
                if "errors" in result:
                    logger.error(f"Linear GraphQL errors: {result['errors']}")
                    return False
                
                # Check mutation success
                data = result.get("data", {})
                mutation_name = list(data.keys())[0] if data else None
                
                if mutation_name and data[mutation_name].get("success"):
                    return True
                
                logger.error(f"Linear mutation failed: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Linear API exception: {e}", exc_info=True)
            return False


# Singleton instance
_roadmap_updater: Optional[LinearRoadmapUpdater] = None


def get_roadmap_updater() -> LinearRoadmapUpdater:
    """Get or create Linear roadmap updater singleton."""
    global _roadmap_updater
    if _roadmap_updater is None:
        _roadmap_updater = LinearRoadmapUpdater()
    return _roadmap_updater


# Workspace constants (updated for workspace rename)
WORKSPACE_ID = "project-roadmaps"  # Workspace name
WORKSPACE_NAME = "Project Roadmaps"
TEAM_ID = "f5b610be-ac34-4983-918b-2c9d00aa9b7a"  # Project Roadmaps (PR) team

# Project constants
PROJECT_ID = "b21cbaa1-9f09-40f4-b62a-73e0f86dd501"  # AI DevOps Agent Platform
PROJECT_SHORT_ID = "78b3b839d36b"

# Workspace-level approval hub (created 2025-11-18)
APPROVAL_HUB_ISSUE_ID = "PR-68"  # Team-level issue for all approvals

# Multi-project registry
PROJECT_REGISTRY = {
    "dev-tools": {
        "id": "b21cbaa1-9f09-40f4-b62a-73e0f86dd501",
        "short_id": "78b3b839d36b",
        "name": "AI DevOps Agent Platform",
        "orchestrator_url": "http://45.55.173.72:8001"
    },
    "twkr": {
        "id": None,  # To be created by orchestrator
        "short_id": None,
        "name": "TWKR",
        "orchestrator_url": "http://45.55.173.72:8001"
    }
}

# Phase issue IDs
PHASE_ISSUES = {
    "phase_1": "ff224eef-378c-46f8-b1ed-32949dd7381e",  # Infrastructure Foundation
    "phase_2": "b3d90ca5-386e-48f4-8665-39deb258667c",  # HITL Integration
    "phase_3": "c52d1888-8722-4469-b52f-59a88975428f",  # Observability
    "phase_4": "7b57ecae-b675-4aef-af6c-52e9bee09f6b",  # Linear Integration
    "phase_5": "8927bac5-ca95-4ce9-a6ac-9bb79cc8aaa9",  # Copilot Integration
}

# Workflow state IDs (fetched from team f5b610be-ac34-4983-918b-2c9d00aa9b7a)
WORKFLOW_STATES = {
    "started": "96689f62-1d2c-4db0-8c7a-a2bcba1a61ef",
    "canceled": "4d5a61b0-c8a4-449c-91bf-571483a3626f",
    "completed": "d202b359-862b-4ce5-8b0a-972bf046250a",
    "unstarted": "9b9b5687-666b-4bcb-9ebd-ecf48304a26b",
    "backlog": "21046e8e-4fc7-4977-82b7-552e501b2f8a",
}
