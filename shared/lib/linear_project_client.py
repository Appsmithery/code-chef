"""
Linear Project Client - Project-Scoped Operations

Handles project-scoped operations like:
- Creating issues within a specific project
- Updating issue status
- Adding comments to project issues

Security: Subagents use this with project_id scoping.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

logger = logging.getLogger(__name__)


class LinearProjectClient:
    """
    Linear client with project-level permissions.
    
    Use cases:
    - Creating issues within assigned project
    - Updating issue status
    - Adding comments to project issues
    
    Security: Each subagent gets a client scoped to their project_id.
    """
    
    def __init__(self, project_id: str, api_key: Optional[str] = None):
        """
        Initialize project-scoped Linear client.
        
        Args:
            project_id: Linear project UUID (enforces scoping)
            api_key: Linear OAuth token
        """
        self.project_id = project_id
        self.api_key = api_key or os.getenv("LINEAR_API_KEY")
        
        if not self.api_key:
            raise ValueError("LINEAR_API_KEY not configured")
        
        if not self.project_id:
            raise ValueError("project_id required for project client")
        
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
        
        logger.info(f"Linear project client initialized (project: {project_id})")
    
    async def create_issue(
        self,
        title: str,
        description: str,
        team_id: str,
        priority: int = 0,
        labels: Optional[List[str]] = None,
        assignee_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create issue within this project.
        
        Args:
            title: Issue title
            description: Issue description (Markdown)
            team_id: Team UUID
            priority: 0 (none), 1 (urgent), 2 (high), 3 (medium), 4 (low)
            labels: List of label names
            assignee_id: User UUID to assign
        
        Returns:
            Issue object with id, title, url
        """
        mutation = gql("""
            mutation CreateIssue($input: IssueCreateInput!) {
                issueCreate(input: $input) {
                    success
                    issue {
                        id
                        title
                        url
                        identifier
                    }
                }
            }
        """)
        
        issue_input = {
            "title": title,
            "description": description,
            "teamId": team_id,
            "projectId": self.project_id,  # Enforce project scoping
            "priority": priority
        }
        
        if assignee_id:
            issue_input["assigneeId"] = assignee_id
        
        if labels:
            issue_input["labelIds"] = labels
        
        try:
            result = self.client.execute(
                mutation,
                variable_values={"input": issue_input}
            )
            
            issue = result["issueCreate"]["issue"]
            logger.info(f"Created issue in project {self.project_id}: {issue['identifier']}")
            
            return issue
            
        except Exception as e:
            logger.error(f"Failed to create issue: {e}")
            raise
    
    async def update_issue_status(
        self,
        issue_id: str,
        state_id: str
    ) -> bool:
        """
        Update issue workflow state.
        
        Args:
            issue_id: Issue UUID
            state_id: Workflow state UUID
        
        Returns:
            True if successful
        """
        mutation = gql("""
            mutation UpdateIssue($issueId: String!, $stateId: String!) {
                issueUpdate(
                    id: $issueId
                    input: { stateId: $stateId }
                ) {
                    success
                }
            }
        """)
        
        try:
            result = self.client.execute(
                mutation,
                variable_values={
                    "issueId": issue_id,
                    "stateId": state_id
                }
            )
            
            success = result["issueUpdate"]["success"]
            logger.info(f"Updated issue {issue_id} state to {state_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update issue: {e}")
            raise
    
    async def add_comment(
        self,
        issue_id: str,
        body: str
    ) -> str:
        """
        Add comment to issue within this project.
        
        Args:
            issue_id: Issue UUID
            body: Comment body (Markdown)
        
        Returns:
            Comment ID
        """
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
                    "issueId": issue_id,
                    "body": body
                }
            )
            
            comment_id = result["commentCreate"]["comment"]["id"]
            logger.info(f"Added comment to issue {issue_id}: {comment_id}")
            
            return comment_id
            
        except Exception as e:
            logger.error(f"Failed to add comment: {e}")
            raise
    
    async def list_issues(
        self,
        state_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List issues within this project.
        
        Args:
            state_filter: Filter by state name (e.g., "Backlog", "In Progress")
        
        Returns:
            List of issues with id, title, state, assignee
        """
        query = gql("""
            query ListIssues($projectId: ID!, $stateFilter: String) {
                project(id: $projectId) {
                    issues(
                        filter: { state: { name: { eq: $stateFilter } } }
                    ) {
                        nodes {
                            id
                            title
                            identifier
                            state {
                                name
                            }
                            assignee {
                                name
                                email
                            }
                        }
                    }
                }
            }
        """)
        
        try:
            result = self.client.execute(
                query,
                variable_values={
                    "projectId": self.project_id,
                    "stateFilter": state_filter
                }
            )
            
            issues = result["project"]["issues"]["nodes"]
            logger.info(f"Listed {len(issues)} issues in project {self.project_id}")
            
            return issues
            
        except Exception as e:
            logger.error(f"Failed to list issues: {e}")
            raise
