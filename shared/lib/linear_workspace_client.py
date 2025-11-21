"""
Linear Workspace Client - Workspace-Level Operations

Handles workspace-level operations like:
- Posting to approval hub (workspace-wide issue)
- Creating new projects
- Reading all projects for routing
- GitHub permalink generation
- Issue documents (rich markdown attachments)
- Template-based issue creation

Security: Only orchestrator should use this client.
"""

import os
import logging
from typing import Optional, Dict, Any, List
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from urllib.parse import quote

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
        hub_issue_id = os.getenv("LINEAR_APPROVAL_HUB_ISSUE_ID", "DEV-68")
        
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

@alextorelli28 - Your approval is needed:

{task_description}

**Actions**:
- ✅ Approve: Change issue status to "Approved" or "Done"
- ❌ Reject: Change issue status to "Rejected" or "Canceled"
- Or comment: `approve REQUEST_ID={approval_id}` or `reject REQUEST_ID={approval_id} REASON="<reason>"`

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
    
    # ========================================
    # Phase 3: GitHub Permalinks
    # ========================================
    
    @staticmethod
    def generate_github_permalink(
        repo: str,
        file_path: str,
        line_start: int,
        line_end: Optional[int] = None,
        commit_sha: Optional[str] = None
    ) -> str:
        """
        Generate GitHub permalink for code reference.
        
        Args:
            repo: Repository in format "owner/repo" (e.g., "Appsmithery/Dev-Tools")
            file_path: Path to file relative to repo root (e.g., "agent_orchestrator/main.py")
            line_start: Starting line number (1-indexed)
            line_end: Ending line number (optional, for ranges)
            commit_sha: Specific commit SHA (optional, defaults to "main")
        
        Returns:
            Full GitHub permalink URL
        
        Example:
            >>> LinearWorkspaceClient.generate_github_permalink(
            ...     "Appsmithery/Dev-Tools",
            ...     "agent_orchestrator/main.py",
            ...     150,
            ...     175
            ... )
            'https://github.com/Appsmithery/Dev-Tools/blob/main/agent_orchestrator/main.py#L150-L175'
        """
        # Ensure file_path doesn't start with /
        file_path = file_path.lstrip("/")
        
        # Default to main branch if no commit specified
        ref = commit_sha or "main"
        
        # Build base URL
        base_url = f"https://github.com/{repo}/blob/{ref}/{file_path}"
        
        # Add line anchors
        if line_end and line_end != line_start:
            line_fragment = f"#L{line_start}-L{line_end}"
        else:
            line_fragment = f"#L{line_start}"
        
        permalink = f"{base_url}{line_fragment}"
        logger.debug(f"Generated GitHub permalink: {permalink}")
        
        return permalink
    
    # ========================================
    # Phase 4: Issue Documents
    # ========================================
    
    async def create_issue_with_document(
        self,
        title: str,
        description: str,
        document_markdown: str,
        project_id: str,
        labels: Optional[List[str]] = None,
        parent_id: Optional[str] = None,
        priority: Optional[int] = None,
        assignee_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create Linear issue with attached rich markdown document.
        
        Args:
            title: Issue title
            description: Brief description (shown in issue list)
            document_markdown: Full markdown content for attached document
            project_id: Project UUID
            labels: List of label IDs
            parent_id: Parent issue ID (for sub-issues)
            priority: Priority level (0=None, 1=Urgent, 2=High, 3=Medium, 4=Low)
            assignee_id: User UUID to assign
        
        Returns:
            Created issue with id, identifier, url, and document
        
        Use Cases:
            - HITL approvals with detailed context
            - Task decomposition analysis
            - Post-mortem documentation
            - Architecture decision records (ADRs)
        """
        mutation = gql("""
            mutation CreateIssueWithDoc($input: IssueCreateInput!) {
                issueCreate(input: $input) {
                    success
                    issue {
                        id
                        identifier
                        url
                        title
                        description
                    }
                }
            }
        """)
        
        input_data = {
            "title": title,
            "description": description,
            "projectId": project_id,
            "document": {
                "content": document_markdown
            }
        }
        
        if labels:
            input_data["labelIds"] = labels
        
        if parent_id:
            input_data["parentId"] = parent_id
        
        if priority is not None:
            input_data["priority"] = priority
        
        if assignee_id:
            input_data["assigneeId"] = assignee_id
        
        try:
            result = self.client.execute(
                mutation,
                variable_values={"input": input_data}
            )
            
            issue = result["issueCreate"]["issue"]
            logger.info(f"Created issue with document: {issue['identifier']} - {issue['title']}")
            
            return issue
            
        except Exception as e:
            logger.error(f"Failed to create issue with document: {e}")
            raise
    
    # ========================================
    # Phase 2: Template-Based Issue Creation
    # ========================================
    
    async def create_issue_from_template(
        self,
        template_id: str,
        template_variables: Optional[Dict[str, str]] = None,
        title_override: Optional[str] = None,
        project_id: Optional[str] = None,
        parent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create issue from Linear template with variable substitution.
        
        Args:
            template_id: Linear template UUID
            template_variables: Dict of template variables to substitute
            title_override: Override template title
            project_id: Override template project
            parent_id: Set parent issue (for sub-issues)
        
        Returns:
            Created issue with id, identifier, url
        
        Example:
            >>> await client.create_issue_from_template(
            ...     template_id="hitl-approval-template-uuid",
            ...     template_variables={
            ...         "agent": "feature-dev",
            ...         "task_id": "abc123",
            ...         "priority": "high",
            ...         "context": "User requested JWT authentication"
            ...     }
            ... )
        """
        mutation = gql("""
            mutation CreateIssueFromTemplate($input: IssueCreateInput!, $templateId: String!) {
                issueCreate(input: $input, templateId: $templateId) {
                    success
                    issue {
                        id
                        identifier
                        url
                        title
                    }
                }
            }
        """)
        
        input_data = {}
        
        if title_override:
            input_data["title"] = title_override
        
        if project_id:
            input_data["projectId"] = project_id
        
        if parent_id:
            input_data["parentId"] = parent_id
        
        # Template variables are passed in description
        if template_variables:
            input_data["templateVariables"] = template_variables
        
        try:
            result = self.client.execute(
                mutation,
                variable_values={
                    "input": input_data,
                    "templateId": template_id
                }
            )
            
            issue = result["issueCreate"]["issue"]
            logger.info(f"Created issue from template: {issue['identifier']} - {issue['title']}")
            
            return issue
            
        except Exception as e:
            logger.error(f"Failed to create issue from template: {e}")
            raise
    
    # ========================================
    # Phase 5: Issue Updates (Status & Comments)
    # ========================================
    
    async def update_issue_status(
        self,
        issue_id: str,
        status: str
    ) -> Dict[str, Any]:
        """
        Update Linear issue status.
        
        Args:
            issue_id: Issue UUID
            status: Status name (e.g., "todo", "in_progress", "done", "approved", "rejected")
        
        Returns:
            Updated issue with id, identifier, state
        
        Usage:
            >>> await client.update_issue_status(
            ...     issue_id="issue-uuid",
            ...     status="done"
            ... )
        """
        # First, get the workflow state ID for this status
        query = gql("""
            query GetWorkflowStates($teamId: String!) {
                team(id: $teamId) {
                    states {
                        nodes {
                            id
                            name
                            type
                        }
                    }
                }
            }
        """)
        
        try:
            # Get team ID
            team_id = os.getenv("LINEAR_TEAM_ID")
            if not team_id:
                raise ValueError("LINEAR_TEAM_ID not configured")
            
            # Fetch workflow states
            result = self.client.execute(query, variable_values={"teamId": team_id})
            states = result["team"]["states"]["nodes"]
            
            # Find matching state (case-insensitive)
            state_id = None
            status_lower = status.lower().replace("_", " ")
            
            for state in states:
                if state["name"].lower() == status_lower:
                    state_id = state["id"]
                    break
            
            if not state_id:
                # Try partial match
                for state in states:
                    if status_lower in state["name"].lower():
                        state_id = state["id"]
                        break
            
            if not state_id:
                logger.error(f"Status '{status}' not found in workflow states")
                raise ValueError(f"Invalid status: {status}")
            
            # Update issue
            mutation = gql("""
                mutation UpdateIssue($issueId: String!, $stateId: String!) {
                    issueUpdate(id: $issueId, input: {stateId: $stateId}) {
                        success
                        issue {
                            id
                            identifier
                            state {
                                name
                            }
                        }
                    }
                }
            """)
            
            result = self.client.execute(
                mutation,
                variable_values={
                    "issueId": issue_id,
                    "stateId": state_id
                }
            )
            
            issue = result["issueUpdate"]["issue"]
            logger.info(f"Updated issue {issue['identifier']} to status: {issue['state']['name']}")
            
            return issue
            
        except Exception as e:
            logger.error(f"Failed to update issue status: {e}")
            raise
    
    async def add_comment(
        self,
        issue_id: str,
        body: str
    ) -> Dict[str, Any]:
        """
        Add comment to Linear issue.
        
        Args:
            issue_id: Issue UUID
            body: Comment markdown content
        
        Returns:
            Created comment with id, createdAt
        
        Usage:
            >>> await client.add_comment(
            ...     issue_id="issue-uuid",
            ...     body="Code generation complete. 3 files created, all tests passing."
            ... )
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
                        body
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
            
            comment = result["commentCreate"]["comment"]
            logger.info(f"Added comment to issue: {comment['id']}")
            
            return comment
            
        except Exception as e:
            logger.error(f"Failed to add comment: {e}")
            raise
    
    async def get_issue_by_identifier(
        self,
        identifier: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get issue by identifier (e.g., "PR-68").
        
        Args:
            identifier: Issue identifier (team prefix + number)
        
        Returns:
            Issue with id, identifier, title, description, state, parent
        
        Usage:
            >>> issue = await client.get_issue_by_identifier("PR-68")
            >>> print(issue['id'])  # Use for parentId in sub-issues
        """
        query = gql("""
            query GetIssue($identifier: String!) {
                issue(id: $identifier) {
                    id
                    identifier
                    title
                    description
                    url
                    state {
                        name
                    }
                    parent {
                        id
                        identifier
                    }
                }
            }
        """)
        
        try:
            result = self.client.execute(
                query,
                variable_values={"identifier": identifier}
            )
            
            issue = result.get("issue")
            if issue:
                logger.info(f"Found issue: {issue['identifier']} - {issue['title']}")
            else:
                logger.warning(f"Issue not found: {identifier}")
            
            return issue
            
        except Exception as e:
            logger.error(f"Failed to get issue: {e}")
            return None
