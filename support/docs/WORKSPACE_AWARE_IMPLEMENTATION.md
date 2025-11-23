# Workspace-Aware Implementation Plan (Updated)

## Revised Requirements (November 22, 2025)

### Configuration Scope

- ✅ **Team ID** → `.env` (same team for all projects)
- ✅ **Project ID** → Dynamic (auto-create or from workspace settings)
- ✅ **Repo URL** → Git remote (user creates repo first)

### User Workflow

1. Create GitHub repo: `gh repo create my-app`
2. Clone locally: `git clone git@github.com:user/my-app.git && cd my-app`
3. Open VS Code: `code .`
4. Chat: `@devtools Initialize React app with TypeScript`
5. **Auto-magic**: Linear project created, settings cached, workflow executes

---

## Phase 1: Extension Context Extraction (Enhanced)

### File: `extensions/vscode-devtools-copilot/src/contextExtractor.ts`

#### New Methods to Add

```typescript
/**
 * Parse GitHub URL from git remote
 * Handles both SSH and HTTPS formats
 */
private parseGitHubUrl(gitRemote: string | null): string | null {
    if (!gitRemote) return null;

    // SSH: git@github.com:owner/repo.git
    const sshMatch = gitRemote.match(/git@github\.com:([^\/]+\/[^\.]+)\.git/);
    if (sshMatch) {
        return `https://github.com/${sshMatch[1]}`;
    }

    // HTTPS: https://github.com/owner/repo.git
    const httpsMatch = gitRemote.match(/https:\/\/github\.com\/([^\/]+\/[^\.]+)\.git/);
    if (httpsMatch) {
        return `https://github.com/${httpsMatch[1]}`;
    }

    // Already clean HTTPS URL
    const cleanMatch = gitRemote.match(/https:\/\/github\.com\/([^\/]+\/[^\/]+)/);
    if (cleanMatch) {
        return `https://github.com/${cleanMatch[1]}`;
    }

    return null;
}

/**
 * Get current commit SHA from git
 * Reads directly from .git/refs/heads/<branch>
 */
private async getCommitSha(workspacePath: string, branch: string | null): Promise<string | null> {
    if (!branch) return null;

    try {
        const refPath = path.join(workspacePath, '.git', 'refs', 'heads', branch);
        const sha = await fs.readFile(refPath, 'utf-8');
        return sha.trim();
    } catch {
        // Try packed-refs fallback
        try {
            const packedRefsPath = path.join(workspacePath, '.git', 'packed-refs');
            const content = await fs.readFile(packedRefsPath, 'utf-8');
            const match = content.match(new RegExp(`^([a-f0-9]{40}) refs/heads/${branch}$`, 'm'));
            return match ? match[1] : null;
        } catch {
            return null;
        }
    }
}

/**
 * Get Linear project ID from workspace settings (if exists)
 */
private getLinearProjectId(): string | null {
    const config = vscode.workspace.getConfiguration('devtools.linear');
    return config.get('projectId') || null;
}

/**
 * Save Linear project ID to workspace settings
 * Called after orchestrator creates new project
 */
async saveLinearProjectId(projectId: string): Promise<void> {
    const config = vscode.workspace.getConfiguration('devtools.linear');
    await config.update('projectId', projectId, vscode.ConfigurationTarget.Workspace);
}
```

#### Updated `extract()` Method

```typescript
async extract(): Promise<Record<string, any>> {
    const workspace = vscode.workspace.workspaceFolders?.[0];
    if (!workspace) {
        return {
            workspace_name: 'unknown',
            workspace_path: null,
            git_branch: null,
            github_repo_url: null,
            github_commit_sha: null,
            linear_project_id: null,
            open_files: [],
            project_type: 'unknown',
            active_editor: null
        };
    }

    const workspacePath = workspace.uri.fsPath;
    const gitBranch = await this.getGitBranch(workspacePath);
    const gitRemote = await this.getGitRemote(workspacePath);
    const githubRepoUrl = this.parseGitHubUrl(gitRemote);
    const commitSha = await this.getCommitSha(workspacePath, gitBranch);
    const linearProjectId = this.getLinearProjectId();

    return {
        workspace_name: workspace.name,
        workspace_path: workspacePath,
        git_branch: gitBranch,
        git_remote: gitRemote,

        // NEW: GitHub context
        github_repo_url: githubRepoUrl,
        github_commit_sha: commitSha,

        // NEW: Linear context (may be null for new projects)
        linear_project_id: linearProjectId,

        // Existing fields
        open_files: this.getOpenFiles(),
        project_type: await this.detectProjectType(workspacePath),
        active_editor: this.getActiveEditorContext(),
        languages: this.getWorkspaceLanguages()
    };
}
```

---

## Phase 2: Orchestrator Auto-Create Project Logic

### File: `shared/lib/linear_project_manager.py` (NEW)

```python
"""
Linear Project Manager

Handles automatic Linear project creation for new workspaces.
"""

from typing import Optional, Dict
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

    async def get_or_create_project(
        self,
        workspace_name: str,
        github_repo_url: Optional[str] = None,
        project_id: Optional[str] = None
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
                logger.info(f"Using existing Linear project: {project['name']} ({project_id})")
                return {
                    "id": project["id"],
                    "identifier": project.get("identifier", ""),
                    "name": project["name"],
                    "url": project.get("url", "")
                }
            except Exception as e:
                logger.warning(f"Project ID {project_id} not found, creating new: {e}")

        # Search for project by name (in case it exists but not cached)
        try:
            projects = await self.linear.list_projects(team_id=self.default_team_id)
            for project in projects:
                if project["name"].lower() == workspace_name.lower():
                    logger.info(f"Found existing project by name: {project['name']}")
                    return {
                        "id": project["id"],
                        "identifier": project.get("identifier", ""),
                        "name": project["name"],
                        "url": project.get("url", "")
                    }
        except Exception as e:
            logger.warning(f"Failed to search for existing project: {e}")

        # Create new project
        logger.info(f"Creating new Linear project for workspace: {workspace_name}")

        description = f"**Workspace**: {workspace_name}\n\n"
        if github_repo_url:
            description += f"**Repository**: {github_repo_url}\n\n"
        description += "Managed by Dev-Tools AI agent system."

        project = await self.linear.create_project(
            name=workspace_name,
            team_id=self.default_team_id,
            description=description,
            state="planned"  # Start in "Planned" state
        )

        logger.info(f"Created Linear project: {project['name']} ({project['id']})")
        return {
            "id": project["id"],
            "identifier": project.get("identifier", ""),
            "name": project["name"],
            "url": project.get("url", "")
        }


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
```

---

## Phase 3: Update Orchestrator `/orchestrate` Endpoint

### File: `agent_orchestrator/main.py`

#### Import New Manager

```python
from lib.linear_project_manager import get_project_manager
```

#### Update `/orchestrate` Endpoint

```python
@app.post("/orchestrate")
async def orchestrate(request: OrchestrationRequest):
    """
    Orchestrate a development task.

    Enhanced with workspace-aware context:
    - Auto-creates Linear project for new repos
    - Enriches descriptions with GitHub permalinks
    - Returns project ID for extension to cache
    """
    try:
        task_id = str(uuid.uuid4())
        logger.info(f"Orchestrating task {task_id}: {request.description[:50]}...")

        # Extract workspace context from request
        workspace_ctx = request.project_context or {}
        workspace_name = workspace_ctx.get("workspace_name", "unknown")
        github_repo_url = workspace_ctx.get("github_repo_url")
        commit_sha = workspace_ctx.get("github_commit_sha")
        linear_project_id = workspace_ctx.get("linear_project_id")

        # Get or create Linear project
        project_manager = get_project_manager()
        project = await project_manager.get_or_create_project(
            workspace_name=workspace_name,
            github_repo_url=github_repo_url,
            project_id=linear_project_id
        )

        # Update workspace context with resolved project ID
        workspace_ctx["linear_project_id"] = project["id"]
        workspace_ctx["linear_project_name"] = project["name"]

        logger.info(
            f"Using Linear project: {project['name']} ({project['id']}) "
            f"for workspace: {workspace_name}"
        )

        # Enrich description with permalinks (if GitHub context available)
        if github_repo_url and commit_sha:
            from lib.github_permalink_generator import enrich_markdown_with_permalinks
            enriched_description = enrich_markdown_with_permalinks(
                request.description,
                repo_url=github_repo_url,
                commit_sha=commit_sha
            )
            logger.info(f"Enriched description with GitHub permalinks for {github_repo_url}")
        else:
            enriched_description = request.description
            logger.info("No GitHub context available, skipping permalink enrichment")

        # ... rest of orchestration logic (decompose, assess risk, etc.)

        # Store task with workspace context
        task = {
            "task_id": task_id,
            "description": enriched_description,
            "original_description": request.description,
            "priority": request.priority,
            "workspace_context": workspace_ctx,  # Include resolved project ID
            "subtasks": subtasks,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
        }

        await state_client.save_task(task)

        return {
            "task_id": task_id,
            "status": "planned",
            "subtasks": subtasks,
            "workspace_context": workspace_ctx,  # Return to extension for caching
            "linear_project": {
                "id": project["id"],
                "name": project["name"],
                "url": project.get("url")
            }
        }

    except Exception as e:
        logger.error(f"Orchestration failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Phase 4: Update Extension to Cache Project ID

### File: `extensions/vscode-devtools-copilot/src/chatParticipant.ts`

#### Update `handleChatRequest()` Method

```typescript
async handleChatRequest(
    request: vscode.ChatRequest,
    context: vscode.ChatContext,
    stream: vscode.ChatResponseStream,
    token: vscode.CancellationToken
): Promise<vscode.ChatResult> {
    const userMessage = request.prompt;

    // Handle commands
    if (request.command) {
        return await this.handleCommand(request.command, userMessage, stream, token);
    }

    stream.progress('Analyzing workspace context...');

    try {
        // Extract workspace context
        const workspaceContext = await this.contextExtractor.extract();

        // Get or create session
        const sessionId = this.sessionManager.getOrCreateSession(context);

        stream.progress('Submitting to Dev-Tools orchestrator...');

        // Submit to orchestrator
        const response = await this.client.orchestrate({
            description: userMessage,
            priority: 'medium',
            project_context: workspaceContext,
            session_id: sessionId
        });

        this.lastTaskId = response.task_id;

        // NEW: Cache Linear project ID if returned (for new projects)
        if (response.linear_project?.id && !workspaceContext.linear_project_id) {
            await this.contextExtractor.saveLinearProjectId(response.linear_project.id);
            stream.markdown(`\n✨ Created Linear project: **${response.linear_project.name}**\n`);
            stream.markdown(`📋 [View in Linear](${response.linear_project.url})\n\n`);
        }

        // Check if approval is required
        if (response.status === 'approval_pending' || response.approval_request_id) {
            // ... existing approval logic
        }

        // Execute the workflow automatically (Agent mode)
        stream.progress('Executing workflow...');
        try {
            await this.client.execute(response.task_id);
            stream.markdown('\n✅ **Workflow execution started!**\n\n');
            stream.markdown(`Monitor progress: \`@devtools /status ${response.task_id}\`\n\n`);
        } catch (executeError: any) {
            stream.markdown('\n⚠️ **Task planned but execution failed to start**\n\n');
            stream.markdown(`Error: ${executeError.message}\n\n`);
        }

        // Stream response
        return await this.renderTaskResponse(response, stream);

    } catch (error: any) {
        stream.markdown(`\n\n❌ **Error**: ${error.message}\n\n`);
        return { errorDetails: { message: error.message } };
    }
}
```

---

## Phase 5: Update Permalink Generator (Stateless)

### File: `shared/lib/github_permalink_generator.py`

#### New Standalone Functions

```python
def generate_permalink(
    repo_url: str,
    file_path: str,
    line_start: Optional[int] = None,
    line_end: Optional[int] = None,
    commit_sha: Optional[str] = None
) -> str:
    """
    Generate GitHub permalink for any repository (stateless).

    Args:
        repo_url: GitHub repository URL (e.g., "https://github.com/owner/repo")
        file_path: Relative path from repo root
        line_start: Starting line number (optional)
        line_end: Ending line number (optional)
        commit_sha: Specific commit SHA (REQUIRED for production)

    Returns:
        GitHub permalink URL

    Example:
        >>> generate_permalink(
        ...     "https://github.com/user/project",
        ...     "src/main.py",
        ...     45,
        ...     67,
        ...     "abc123def456"
        ... )
        'https://github.com/user/project/blob/abc123def456/src/main.py#L45-L67'
    """
    if not commit_sha:
        raise ValueError("commit_sha is required for permalink generation")

    # Clean repo URL
    base_url = repo_url.rstrip(".git").rstrip("/")

    # Build permalink
    url = f"{base_url}/blob/{commit_sha}/{file_path}"

    # Add line numbers
    if line_start:
        url += f"#L{line_start}"
        if line_end and line_end != line_start:
            url += f"-L{line_end}"

    return url


def enrich_markdown_with_permalinks(
    markdown_text: str,
    repo_url: str,
    commit_sha: str
) -> str:
    """
    Enrich markdown with permalinks for any repository (stateless).

    Args:
        markdown_text: Text containing file references
        repo_url: GitHub repository URL
        commit_sha: Commit SHA to link to

    Returns:
        Markdown text with file references converted to links
    """
    # Use existing GitHubPermalinkGenerator class internally
    generator = GitHubPermalinkGenerator(repo_url, repo_path="/tmp")
    return generator.enrich_markdown_with_permalinks(markdown_text, commit_sha)
```

---

## Phase 6: Update `.env.template`

### File: `config/env/.env.template`

#### Add Linear Team ID, Remove Project-Specific Config

```bash
# ============================================================================
# LINEAR INTEGRATION - UPDATED (November 2025)
# ============================================================================
# Team-Level Configuration (same team for all projects)
LINEAR_TEAM_ID=f5b610be-ac34-4983-918b-2c9d00aa9b7a  # Project Roadmaps team

# Linear API Key (OAuth token for GraphQL API access)
LINEAR_API_KEY=

# OAuth Configuration (Secrets)
LINEAR_OAUTH_CLIENT_ID=
LINEAR_OAUTH_CLIENT_SECRET=
LINEAR_OAUTH_DEV_TOKEN=

# Webhook Security (Secrets)
LINEAR_ORCHESTRATOR_WEBHOOK_SECRET=
LINEAR_WEBHOOK_SIGNING_SECRET=

# NOTE: Project IDs are now dynamic - auto-created per workspace
# No need to configure LINEAR_PROJECT_ID in .env
# Projects are created automatically based on workspace name + GitHub repo
```

---

## Testing Checklist

### Scenario 1: New Project (Auto-Create)

- [ ] Create new GitHub repo: `gh repo create test-app`
- [ ] Clone: `git clone git@github.com:user/test-app.git && cd test-app`
- [ ] Open VS Code: `code .`
- [ ] Chat: `@devtools Initialize Node.js project`
- [ ] Verify: Linear project "test-app" created
- [ ] Verify: `.vscode/settings.json` contains `devtools.linear.projectId`
- [ ] Verify: Issues created in new project
- [ ] Verify: Permalinks point to `github.com/user/test-app`

### Scenario 2: Existing Project (Cached ID)

- [ ] Open existing workspace with `.vscode/settings.json`
- [ ] Chat: `@devtools Add authentication`
- [ ] Verify: Uses existing Linear project ID
- [ ] Verify: No new project created
- [ ] Verify: Issues in correct project

### Scenario 3: No Git Remote (Graceful Degradation)

- [ ] Create local folder without git
- [ ] Open VS Code: `code .`
- [ ] Chat: `@devtools Create README`
- [ ] Verify: Task executes without permalinks
- [ ] Verify: Linear project created with generic name
- [ ] Verify: No errors

### Scenario 4: Multi-Project Workflow

- [ ] Open project A (`github.com/user/project-a`)
- [ ] Chat: `@devtools Fix bug`
- [ ] Verify: Issues in project-a Linear project
- [ ] Open project B (`github.com/user/project-b`)
- [ ] Chat: `@devtools Add feature`
- [ ] Verify: Issues in project-b Linear project
- [ ] Verify: No cross-contamination

---

## Estimated Time: 12 Hours

- Phase 1: Extension context extraction → **2 hours**
- Phase 2: Linear project manager → **2 hours**
- Phase 3: Orchestrator `/orchestrate` update → **2 hours**
- Phase 4: Extension caching logic → **1 hour**
- Phase 5: Permalink generator refactor → **2 hours**
- Phase 6: `.env` + documentation → **1 hour**
- Testing & validation → **2 hours**

---

## Next Steps

1. **Start Phase 1**: Update extension context extraction
2. **Create project manager**: Implement auto-create logic
3. **Wire orchestrator**: Update `/orchestrate` endpoint
4. **Test end-to-end**: Verify auto-create workflow
5. **Deploy to droplet**: Update production stack

Ready to start Phase 1?
