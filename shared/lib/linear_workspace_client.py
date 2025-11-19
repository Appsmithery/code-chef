"""
Linear Workspace Client - Workspace-Level Operations

Handles workspace-level operations like:
- Posting to approval hub (workspace-wide issue)
- Creating new projects
- Reading all projects for routing

Security: Only orchestrator should use this client.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

logger = logging.getLogger(__name__)


class LinearWorkspaceClient:
    """
    Linear client with workspace-level permissions.
    
    Use cases:
    - Posting approval requests to workspace hub
    - Creating new projects
    - Listing all projects for routing
    
    Security: Only the orchestrator should instantiate this.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize workspace-level Linear client.
        
        Args:
            api_key: Linear OAuth token with workspace scope
        """
        self.api_key = api_key or os.getenv("LINEAR_API_KEY")
        
        if not self.api_key:
            raise ValueError("LINEAR_API_KEY not configured")
        
        # Initialize GraphQL client
        transport = RequestsHTTPTransport(
            url="https://api.linear.app/graphql",
            headers={"Authorization": self.api_key},
            use_json=True
        )
        
        self.client = Client(
            transport=transport,
            fetch_schema_from_transport=True
        )
        
        logger.info("Linear workspace client initialized")
    
    async def post_to_approval_hub(
        self,
        approval_id: str,
        task_description: str,
        risk_level: str,
        project_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Post approval request to workspace-level approval hub.
        
        Args:
            approval_id: UUID of approval request
            task_description: Human-readable task description
            risk_level: critical, high, medium, low
            project_name: Which project this approval is for
            approver_mention: Linear @mention for approver (e.g., "@ops-lead")
            metadata: Additional context (risk factors, action details)
        
        Returns:
            Comment ID if successful
        """
        # Get approval hub issue ID from config
        hub_issue_id = os.getenv("LINEAR_APPROVAL_HUB_ISSUE_ID")
        
        if not hub_issue_id:
            logger.error("LINEAR_APPROVAL_HUB_ISSUE_ID not configured")
            raise ValueError("Approval hub not configured")
        
        # Format comment body
        risk_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢"
        }
        
        body = f"""
{risk_emoji.get(risk_level, "⚪")} **{risk_level.upper()} Approval Required**

**Project**: `{project_name}`
**Approval ID**: `{approval_id}`

@lead-minion - Your approval is needed:

{task_description}

**Actions**:
- ✅ Approve: `task workflow:approve REQUEST_ID={approval_id}`
- ❌ Reject: `task workflow:reject REQUEST_ID={approval_id} REASON="<reason>"`

**Details**: [View in dashboard](http://45.55.173.72:8001/approvals/{approval_id})
"""
        
        if metadata:
            body += f"\n**Metadata**: ```json\n{metadata}\n```"
        
        # Create comment via GraphQL
        mutation = gql("""
            mutation CreateComment($issueId: String!, $body: String!) {
                commentCreate(input: {
                    issueId: $issueId
                    body: $body
                }) {
                    success
                    comment {
                        id
                        createdAt
                    }
                }
            }
        """)
        
        try:
            result = self.client.execute(
                mutation,
                variable_values={
                    "issueId": hub_issue_id,
                    "body": body
                }
            )
            
            comment_id = result["commentCreate"]["comment"]["id"]
            logger.info(f"Posted approval {approval_id} to workspace hub: {comment_id}")
            
            return comment_id
            
        except Exception as e:
            logger.error(f"Failed to post to approval hub: {e}")
            raise
    
    async def list_projects(self) -> List[Dict[str, Any]]:
        """
        List all projects in workspace for routing decisions.
        
        Returns:
            List of projects with id, name, slug
        """
        query = gql("""
            query ListProjects {
                projects {
                    nodes {
                        id
                        name
                        slugId
                        state
                    }
                }
            }
        """)
        
        try:
            result = self.client.execute(query)
            projects = result["projects"]["nodes"]
            
            logger.info(f"Listed {len(projects)} projects in workspace")
            return projects
            
        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            raise
    
    async def create_project(
        self,
        name: str,
        team_id: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create new project in workspace.
        
        Args:
            name: Project name
            team_id: Team UUID
            description: Optional project description
        
        Returns:
            Project object with id, name, url
        """
        mutation = gql("""
            mutation CreateProject($input: ProjectCreateInput!) {
                projectCreate(input: $input) {
                    success
                    project {
                        id
                        name
                        url
                    }
                }
            }
        """)
        
        try:
            result = self.client.execute(
                mutation,
                variable_values={
                    "input": {
                        "name": name,
                        "teamIds": [team_id],
                        "description": description or ""
                    }
                }
            )
            
            project = result["projectCreate"]["project"]
            logger.info(f"Created project: {project['name']} ({project['id']})")
            
            return project
            
        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            raise
