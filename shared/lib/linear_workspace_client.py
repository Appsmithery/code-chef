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
from langsmith import traceable

from lib.linear_config import get_linear_config, LinearConfig

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

    def __init__(
        self, api_key: Optional[str] = None, config: Optional[LinearConfig] = None
    ):
        """
        Initialize workspace-level Linear client.

        Args:
            api_key: Linear OAuth token with workspace scope (optional, loaded from config)
            config: LinearConfig instance (optional, auto-loaded if not provided)
        """
        # Load configuration
        self.config = config or get_linear_config()

        # Use provided API key or load from config
        self.api_key = api_key or self.config.api_key

        if not self.api_key:
            raise ValueError("LINEAR_API_KEY not configured in .env")

        # Initialize GraphQL client
        transport = RequestsHTTPTransport(
            url="https://api.linear.app/graphql",
            headers={"Authorization": self.api_key},
            use_json=True,
        )

        self.client = Client(transport=transport, fetch_schema_from_transport=True)

        logger.info("Linear workspace client initialized")

    async def _execute_query(
        self, query_string: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute raw GraphQL query (for testing/debugging).

        Args:
            query_string: GraphQL query string
            variables: Optional query variables

        Returns:
            Query result
        """
        query = gql(query_string)
        return self.client.execute(query, variable_values=variables or {})

    @traceable(name="post_to_approval_hub", tags=["linear", "hitl", "graphql"])
    async def post_to_approval_hub(
        self,
        approval_id: str,
        task_description: str,
        risk_level: str,
        project_name: str,
        metadata: Optional[Dict[str, Any]] = None,
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
        # Get approval hub issue identifier from config
        hub_issue_identifier = self.config.approval_hub.issue_id

        if not hub_issue_identifier:
            logger.error("approval_hub.issue_id not configured")
            raise ValueError("Approval hub not configured")

        # Resolve identifier to UUID
        hub_issue = await self.get_issue_by_identifier(hub_issue_identifier)
        if not hub_issue:
            logger.error(f"Approval hub issue {hub_issue_identifier} not found")
            raise ValueError(f"Approval hub issue {hub_issue_identifier} not found")

        hub_issue_id = hub_issue["id"]

        # Format comment body
        risk_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}

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
        mutation = gql(
            """
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
        """
        )

        try:
            result = self.client.execute(
                mutation, variable_values={"issueId": hub_issue_id, "body": body}
            )

            comment_id = result["commentCreate"]["comment"]["id"]
            logger.info(f"Posted approval {approval_id} to workspace hub: {comment_id}")

            return comment_id

        except Exception as e:
            logger.error(f"Failed to post to approval hub: {e}")
            raise

    @traceable(name="list_projects", tags=["linear", "graphql"])
    async def list_projects(self) -> List[Dict[str, Any]]:
        """
        List all projects in workspace for routing decisions.

        Returns:
            List of projects with id, name, slug
        """
        query = gql(
            """
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
        """
        )

        try:
            result = self.client.execute(query)
            projects = result["projects"]["nodes"]

            logger.info(f"Listed {len(projects)} projects in workspace")
            return projects

        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            raise

    @traceable(name="create_project", tags=["linear", "graphql", "mutation"])
    async def create_project(
        self, name: str, team_id: str, description: Optional[str] = None
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
        mutation = gql(
            """
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
        """
        )

        try:
            result = self.client.execute(
                mutation,
                variable_values={
                    "input": {
                        "name": name,
                        "teamIds": [team_id],
                        "description": description or "",
                    }
                },
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
        commit_sha: Optional[str] = None,
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
        assignee_id: Optional[str] = None,
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
        mutation = gql(
            """
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
        """
        )

        input_data = {
            "title": title,
            "description": description,
            "projectId": project_id,
            "document": {"content": document_markdown},
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
                mutation, variable_values={"input": input_data}
            )

            issue = result["issueCreate"]["issue"]
            logger.info(
                f"Created issue with document: {issue['identifier']} - {issue['title']}"
            )

            return issue

        except Exception as e:
            logger.error(f"Failed to create issue with document: {e}")
            raise

    # ========================================
    # Phase 2: Template-Based Issue Creation
    # ========================================

    async def create_approval_subissue(
        self,
        approval_id: str,
        task_description: str,
        risk_level: str,
        project_name: str,
        agent_name: str = "orchestrator",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create HITL approval sub-issue using agent-specific template.

        Args:
            approval_id: UUID of approval request
            task_description: Task description requiring approval
            risk_level: critical, high, medium, low
            project_name: Project name for context
            agent_name: Agent requesting approval (for template selection)
            metadata: Additional context (task_id, priority, timestamp, etc.)

        Returns:
            Created sub-issue with id, identifier, url
        """
        # Get parent approval hub issue
        hub_identifier = self.config.approval_hub.issue_id

        # Resolve parent issue ID from identifier
        parent_issue = await self.get_issue_by_identifier(hub_identifier)
        if not parent_issue:
            raise ValueError(f"Approval hub issue {hub_identifier} not found")

        parent_id = parent_issue["id"]

        # Select HITL template based on agent (with fallback to orchestrator)
        template_id = self.config.get_template_uuid(agent_name, scope="workspace")

        # Prepare template variables
        template_vars = {
            "agent": agent_name,
            "task_id": approval_id,
            "context_description": task_description,
            "changes_summary": task_description,
            "reasoning": f"Risk level: {risk_level}",
            "risks": metadata.get("risk_factors", []) if metadata else [],
            "deadline": "30 minutes",
            "estimated_tokens": (
                metadata.get("estimated_cost", 150) if metadata else 150
            ),
        }

        # Add metadata as JSON
        if metadata:
            template_vars["metadata"] = str(metadata)

        # Generate title with risk emoji
        risk_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
        title = f"{risk_emoji.get(risk_level, '⚪')} [{risk_level.upper()}] HITL Approval: {task_description[:50]}"

        # Get approval policy for risk level (includes priority and required actions)
        policy = self.config.get_approval_policy(risk_level)

        # Get label IDs for HITL and agent
        label_ids = [
            self.config.labels.hitl,
            self.config.labels.orchestrator,
        ]

        # Create sub-issue from template (inherit parent's team)
        team_id = parent_issue.get("team", {}).get("id")
        assignee_id = self.config.default_assignee.id

        # Prepare custom fields for approval template
        # Request Status: Leave empty (user input required)
        # Required Action: Pre-check actions based on risk level from policy
        custom_fields = {}

        # Request Status dropdown field - leave empty for user to fill
        # (no default value for high-stakes decisions)

        # Required Action checkboxes field - use policy's required actions
        required_action_field_id = self.config.get_custom_field_id("required_action")
        custom_fields[required_action_field_id] = policy.required_actions

        return await self.create_issue_from_template(
            template_id=template_id,
            template_variables=template_vars,
            title_override=title,
            parent_id=parent_id,
            team_id=team_id,
            assignee_id=assignee_id,
            label_ids=label_ids,
            priority=policy.priority,
            custom_fields=custom_fields,
        )

    @traceable(
        name="create_issue_from_template",
        tags=["linear", "graphql", "mutation", "template"],
    )
    async def create_issue_from_template(
        self,
        template_id: str,
        template_variables: Optional[Dict[str, str]] = None,
        title_override: Optional[str] = None,
        project_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        team_id: Optional[str] = None,
        assignee_id: Optional[str] = None,
        label_ids: Optional[List[str]] = None,
        priority: Optional[int] = None,
        state_id: Optional[str] = None,
        custom_fields: Optional[Dict[str, Any]] = None,
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
        # Note: Linear doesn't support templateId in issueCreate.
        # Templates in Linear SDK work via template.instantiate() which requires
        # SDK access, not pure GraphQL. For now, create issue with template structure.
        mutation = gql(
            """
            mutation CreateIssue($input: IssueCreateInput!) {
                issueCreate(input: $input) {
                    success
                    issue {
                        id
                        identifier
                        url
                        title
                    }
                }
            }
        """
        )

        input_data = {}

        if title_override:
            input_data["title"] = title_override

        if project_id:
            input_data["projectId"] = project_id

        if parent_id:
            input_data["parentId"] = parent_id

        if team_id:
            input_data["teamId"] = team_id

        if assignee_id:
            input_data["assigneeId"] = assignee_id

        if label_ids:
            input_data["labelIds"] = label_ids

        if priority:
            input_data["priority"] = priority

        if state_id:
            input_data["stateId"] = state_id

        # Note: Linear API doesn't support setting customFields during issue creation
        # Custom fields must be set after creation via issueUpdate mutation
        # Store for potential future use, but don't send to API
        if custom_fields:
            # Log that custom fields were requested but can't be set during creation
            logger.warning(
                f"Custom fields requested but not supported during creation: {list(custom_fields.keys())}"
            )

        # Build description from template variables (manual template expansion)
        if template_variables:
            description_parts = []
            for key, value in template_variables.items():
                if isinstance(value, list):
                    value = "\n".join([f"- {item}" for item in value])
                description_parts.append(
                    f"**{key.replace('_', ' ').title()}:** {value}"
                )

            input_data["description"] = "\n\n".join(description_parts)

        try:
            result = self.client.execute(
                mutation, variable_values={"input": input_data}
            )

            issue = result["issueCreate"]["issue"]
            logger.info(f"Created issue: {issue['identifier']} - {issue['title']}")

            return issue

        except Exception as e:
            logger.error(f"Failed to create issue: {e}")
            raise

    # ========================================
    # Phase 5: Issue Updates (Status & Comments)
    # ========================================

    async def update_issue_status(self, issue_id: str, status: str) -> Dict[str, Any]:
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
        query = gql(
            """
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
        """
        )

        try:
            # Get team ID from config
            team_id = self.config.workspace.team_id
            if not team_id:
                raise ValueError("workspace.team_id not configured")

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
            mutation = gql(
                """
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
            """
            )

            result = self.client.execute(
                mutation, variable_values={"issueId": issue_id, "stateId": state_id}
            )

            issue = result["issueUpdate"]["issue"]
            logger.info(
                f"Updated issue {issue['identifier']} to status: {issue['state']['name']}"
            )

            return issue

        except Exception as e:
            logger.error(f"Failed to update issue status: {e}")
            raise

    async def add_comment(self, issue_id: str, body: str) -> Dict[str, Any]:
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
        mutation = gql(
            """
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
        """
        )

        try:
            result = self.client.execute(
                mutation, variable_values={"issueId": issue_id, "body": body}
            )

            comment = result["commentCreate"]["comment"]
            logger.info(f"Added comment to issue: {comment['id']}")

            return comment

        except Exception as e:
            logger.error(f"Failed to add comment: {e}")
            raise

    async def create_approval_comment(
        self,
        agent_name: str,
        task_description: str,
        risk_level: str,
        approval_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create HITL approval request as a comment with emoji reaction instructions.

        This replaces sub-issue creation with a simpler comment-based approval flow:
        - User reacts with 👍 to approve
        - User reacts with 👎 to deny
        - User replies with comment to request more info

        Args:
            agent_name: Name of agent requesting approval
            task_description: Description of task requiring approval
            risk_level: Risk level (low, medium, high, critical)
            approval_id: Optional unique ID for tracking
            metadata: Optional metadata (risk factors, estimated cost, etc.)

        Returns:
            {
                "comment_id": "comment-uuid",
                "url": "https://linear.app/...",
                "issue_id": "DEV-68"
            }

        Usage:
            >>> comment_data = await client.create_approval_comment(
            ...     agent_name="feature-dev",
            ...     task_description="Deploy multi-layer config to production",
            ...     risk_level="high",
            ...     metadata={"risk_factors": ["Configuration change", "Production deployment"]}
            ... )
        """
        # Get approval hub from config
        hub_identifier = self.config.approval_hub.issue_id

        # Resolve to UUID
        hub_issue = await self.get_issue_by_identifier(hub_identifier)
        if not hub_issue:
            raise ValueError(f"Approval hub issue {hub_identifier} not found")

        hub_issue_id = hub_issue["id"]

        # Get approval policy for risk level
        policy = self.config.get_approval_policy(risk_level)

        # Format risk emoji
        risk_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
        emoji = risk_emoji.get(risk_level, "⚪")

        # Format required actions
        actions_text = "\n".join(f"- {action}" for action in policy.required_actions)

        # Format risk factors if provided
        risk_factors_text = ""
        if metadata and "risk_factors" in metadata:
            risk_factors_text = "\n\n**Risk Factors:**\n" + "\n".join(
                f"- {factor}" for factor in metadata["risk_factors"]
            )

        # Build approval comment body
        approval_body = f"""## {emoji} HITL Approval Required

**Agent:** `{agent_name}`
**Risk Level:** {risk_level.upper()}
**Priority:** {"Urgent" if policy.priority == 0 else "High" if policy.priority == 1 else "Medium" if policy.priority == 2 else "Low"}

### Task
{task_description}

### Required Actions
{actions_text}{risk_factors_text}

---

### ✅ How to Approve/Deny

**React to this comment with:**
- 👍 **Approve** - Resume workflow and execute actions
- 👎 **Deny** - Cancel workflow, no actions taken
- 💬 **Reply** - Request more information (workflow pauses)

The workflow will automatically resume or cancel based on your reaction.
"""

        if approval_id:
            approval_body += f"\n*Approval ID: `{approval_id}`*"

        # Create comment
        mutation = gql(
            """
            mutation CreateComment($issueId: String!, $body: String!) {
                commentCreate(input: {
                    issueId: $issueId
                    body: $body
                }) {
                    success
                    comment {
                        id
                        url
                        createdAt
                    }
                }
            }
        """
        )

        try:
            result = self.client.execute(
                mutation,
                variable_values={"issueId": hub_issue_id, "body": approval_body},
            )

            if not result["commentCreate"]["success"]:
                raise Exception("Failed to create approval comment")

            comment = result["commentCreate"]["comment"]
            logger.info(f"Created approval comment for {agent_name}: {comment['url']}")

            return {
                "comment_id": comment["id"],
                "url": comment["url"],
                "issue_id": hub_identifier,
                "approval_id": approval_id,
            }

        except Exception as e:
            logger.error(f"Failed to create approval comment: {e}")
            raise

    async def get_issue_by_identifier(
        self, identifier: str
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
        # Split identifier into team key and number (e.g., "DEV-68" -> "DEV", 68)
        parts = identifier.split("-")
        if len(parts) != 2:
            logger.error(f"Invalid identifier format: {identifier}")
            return None

        team_key = parts[0]
        try:
            issue_number = int(parts[1])
        except ValueError:
            logger.error(f"Invalid issue number in identifier: {identifier}")
            return None

        query = gql(
            """
            query GetIssueByIdentifier($teamKey: String!, $number: Float!) {
                issues(filter: {team: {key: {eq: $teamKey}}, number: {eq: $number}}, first: 1) {
                    nodes {
                        id
                        identifier
                        title
                        description
                        url
                        team {
                            id
                            key
                            name
                        }
                        state {
                            name
                        }
                        parent {
                            id
                            identifier
                        }
                    }
                }
            }
        """
        )

        try:
            result = self.client.execute(
                query, variable_values={"teamKey": team_key, "number": issue_number}
            )

            nodes = result.get("issues", {}).get("nodes", [])
            issue = nodes[0] if nodes else None

            if issue:
                logger.info(f"Found issue: {issue['identifier']} - `{issue['title']}`")
            else:
                logger.warning(f"Issue not found: {identifier}")

            return issue

        except Exception as e:
            logger.error(f"Failed to get issue: {e}")
            return None
