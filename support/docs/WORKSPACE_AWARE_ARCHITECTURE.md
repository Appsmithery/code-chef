# Workspace-Aware Architecture Strategy

## Problem Statement

Current implementation has hardcoded assumptions:

- GitHub repo URL in `.env` → Not portable across projects
- Linear project ID in `.env` → Not portable across organizations
- Permalink generator initialized at orchestrator startup → Only works for Dev-Tools repo
- Extension expects orchestrator to know user's project context → Breaks multi-project workflow

**User's Goal**: Package agents + extension for use across any software project, with orchestrator dynamically adapting to the workspace context provided by the VS Code extension.

---

## Recommended Strategy: Workspace-Driven Context Injection

### Core Principle

**The VS Code extension is the source of truth for workspace context.**  
The orchestrator should be **stateless** and **workspace-agnostic**, receiving all project-specific context in each request.

### Three-Layer Architecture

#### Layer 1: VS Code Extension (Context Provider)

**Responsibility**: Extract and enrich workspace metadata before sending to orchestrator

**Already Captured** (in `contextExtractor.ts`):

- ✅ Workspace name, path
- ✅ Git branch, remote URL
- ✅ Open files, active editor
- ✅ Project type (node, python, etc.)
- ✅ Languages used

**Needs to Add**:

- 🔧 **GitHub repo URL** (parsed from git remote)
- 🔧 **Linear project ID** (from workspace settings or `.vscode/settings.json`)
- 🔧 **Linear team ID** (from workspace settings)
- 🔧 **Current commit SHA** (for permalinks)

**Implementation**:

```typescript
// extensions/vscode-devtools-copilot/src/contextExtractor.ts

interface WorkspaceContext {
  // Existing fields
  workspace_name: string;
  workspace_path: string;
  git_branch: string;
  git_remote: string; // Already have this!

  // NEW: Parsed GitHub context
  github_repo_url?: string; // e.g., "https://github.com/owner/repo"
  github_commit_sha?: string; // Current HEAD commit

  // NEW: Linear context (from workspace settings)
  linear_project_id?: string; // From .vscode/settings.json
  linear_team_id?: string; // From .vscode/settings.json

  // Existing fields
  open_files: string[];
  project_type: string;
  active_editor: any;
}
```

**Workspace Settings** (`.vscode/settings.json` in user's project):

```json
{
  "devtools.orchestratorUrl": "http://45.55.173.72:8001",
  "devtools.linear.projectId": "b21cbaa1-9f09-40f4-b62a-73e0f86dd501",
  "devtools.linear.teamId": "f5b610be-ac34-4983-918b-2c9d00aa9b7a",
  "devtools.github.enabled": true
}
```

**Benefits**:

- User configures Linear project/team once per workspace
- Extension automatically detects GitHub repo from git remote
- No hardcoded values in orchestrator `.env`
- Works across unlimited projects/repos

---

#### Layer 2: Orchestrator (Context Consumer)

**Responsibility**: Accept workspace context in request payload, initialize services dynamically

**Current `/orchestrate` Endpoint** (BEFORE):

```python
@app.post("/orchestrate")
async def orchestrate(request: OrchestrationRequest):
    # ❌ Uses global repo_url from .env
    # ❌ Uses global project_id from .env
    description = enrich_description_with_permalinks(request.description)
    ...
```

**New `/orchestrate` Endpoint** (AFTER):

```python
@app.post("/orchestrate")
async def orchestrate(request: OrchestrationRequest):
    # ✅ Extract workspace context from request
    github_repo_url = request.project_context.get("github_repo_url")
    commit_sha = request.project_context.get("github_commit_sha")
    linear_project_id = request.project_context.get("linear_project_id")
    linear_team_id = request.project_context.get("linear_team_id")

    # ✅ Initialize permalink generator per-request (if GitHub repo available)
    if github_repo_url:
        from lib.github_permalink_generator import GitHubPermalinkGenerator
        permalink_gen = GitHubPermalinkGenerator(
            repo_url=github_repo_url,
            repo_path="/tmp/workspace"  # Won't use local git in production
        )
        enriched_description = permalink_gen.enrich_markdown_with_permalinks(
            request.description,
            commit_sha=commit_sha
        )
    else:
        enriched_description = request.description
        logger.warning("No GitHub repo URL provided, skipping permalink enrichment")

    # ✅ Store workspace context in task state for use by /execute
    task = {
        "task_id": task_id,
        "description": enriched_description,
        "workspace_context": {
            "github_repo_url": github_repo_url,
            "github_commit_sha": commit_sha,
            "linear_project_id": linear_project_id,
            "linear_team_id": linear_team_id,
        },
        ...
    }
    ...
```

**New `/execute` Endpoint** (AFTER):

```python
@app.post("/execute/{task_id}")
async def execute(task_id: str):
    # ✅ Retrieve task with workspace context
    task = await state_client.get_task(task_id)
    workspace_context = task.get("workspace_context", {})

    # ✅ Initialize Linear updater with workspace context
    linear_client = get_linear_client()
    updater = IncrementalLinearUpdater(linear_client)

    parent_issue_id = await updater.create_task_structure(
        task_id=task_id,
        task_description=task["description"],  # Already enriched with permalinks
        subtasks=task["subtasks"],
        project_id=workspace_context.get("linear_project_id"),
        team_id=workspace_context.get("linear_team_id")
    )

    # ✅ Execute workflow with subtask updates
    for subtask in task["subtasks"]:
        await updater.update_subtask_start(subtask["id"])
        result = await execute_subtask(subtask, workspace_context)

        # Enrich result with permalinks if GitHub context available
        if workspace_context.get("github_repo_url"):
            result_with_links = enrich_result_with_permalinks(
                result,
                workspace_context
            )
        else:
            result_with_links = result

        await updater.update_subtask_complete(
            subtask["id"],
            result=result_with_links,
            artifacts=result.get("artifacts")
        )
    ...
```

**Benefits**:

- Orchestrator remains stateless (no global state)
- Each request is self-contained with full workspace context
- Supports concurrent requests from different projects
- No `.env` changes needed when switching projects

---

#### Layer 3: Permalink Generator (Context-Aware Utility)

**Responsibility**: Generate permalinks for any repository, given repo URL and commit SHA

**Current Implementation** (BEFORE):

```python
# ❌ Global singleton initialized at startup
_generator: Optional[GitHubPermalinkGenerator] = None

def init_permalink_generator(repo_url: str):
    global _generator
    _generator = GitHubPermalinkGenerator(repo_url)

def generate_permalink(file_path: str, line_start: int, line_end: int):
    # ❌ Uses global _generator (assumes single repo)
    return _generator.generate_permalink(file_path, line_start, line_end)
```

**New Implementation** (AFTER):

```python
# ✅ No global state - always pass repo context explicitly

def generate_permalink(
    repo_url: str,
    file_path: str,
    line_start: Optional[int] = None,
    line_end: Optional[int] = None,
    commit_sha: Optional[str] = None
) -> str:
    """
    Generate GitHub permalink for any repository.

    Args:
        repo_url: GitHub repository URL (e.g., "https://github.com/owner/repo")
        file_path: Relative path from repo root
        line_start: Starting line number (optional)
        line_end: Ending line number (optional)
        commit_sha: Specific commit SHA (required for production, avoids git operations)

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
    # ✅ Build URL directly without git operations (production mode)
    if commit_sha:
        url = f"{repo_url.rstrip('/')}/blob/{commit_sha}/{file_path}"
        if line_start:
            url += f"#L{line_start}"
            if line_end and line_end != line_start:
                url += f"-L{line_end}"
        return url

    # ✅ Fallback to git operations (development mode)
    else:
        logger.warning("No commit SHA provided, falling back to git operations")
        generator = GitHubPermalinkGenerator(repo_url)
        return generator.generate_permalink(file_path, line_start, line_end)


def enrich_markdown_with_permalinks(
    markdown_text: str,
    repo_url: str,
    commit_sha: str
) -> str:
    """
    Enrich markdown with permalinks for any repository.

    Args:
        markdown_text: Text containing file references
        repo_url: GitHub repository URL
        commit_sha: Commit SHA to link to

    Returns:
        Markdown text with file references converted to links

    Example:
        >>> enrich_markdown_with_permalinks(
        ...     "Review src/main.py lines 45-67",
        ...     "https://github.com/user/project",
        ...     "abc123def456"
        ... )
        'Review [src/main.py (L45-L67)](https://github.com/user/project/blob/abc123def456/src/main.py#L45-L67)'
    """
    # ✅ Create temporary generator for this repo
    generator = GitHubPermalinkGenerator(repo_url, repo_path="/tmp")
    return generator.enrich_markdown_with_permalinks(markdown_text, commit_sha)
```

**Benefits**:

- No global state or singletons
- Works with any repository passed at call time
- Commit SHA from extension eliminates git operations
- Simpler, more predictable behavior

---

## Implementation Plan

### Phase 1: Enhance VS Code Extension Context Extraction

**File**: `extensions/vscode-devtools-copilot/src/contextExtractor.ts`

**Changes**:

1. Parse GitHub repo URL from `git_remote` field:

   ```typescript
   private parseGitHubUrl(gitRemote: string): string | null {
       // Handle SSH: git@github.com:owner/repo.git
       // Handle HTTPS: https://github.com/owner/repo.git
       const sshMatch = gitRemote.match(/git@github\.com:(.+?)\.git/);
       if (sshMatch) {
           return `https://github.com/${sshMatch[1]}`;
       }
       const httpsMatch = gitRemote.match(/https:\/\/github\.com\/(.+?)\.git/);
       if (httpsMatch) {
           return `https://github.com/${httpsMatch[1]}`;
       }
       return null;
   }
   ```

2. Get current commit SHA:

   ```typescript
   private async getCommitSha(workspacePath: string): Promise<string | null> {
       try {
           const gitHeadPath = path.join(workspacePath, '.git', 'refs', 'heads');
           const branch = await this.getGitBranch(workspacePath);
           if (!branch) return null;

           const shaPath = path.join(gitHeadPath, branch);
           const sha = await fs.readFile(shaPath, 'utf-8');
           return sha.trim();
       } catch {
           return null;
       }
   }
   ```

3. Read Linear config from workspace settings:

   ```typescript
   private getLinearConfig(): { projectId?: string; teamId?: string } {
       const config = vscode.workspace.getConfiguration('devtools.linear');
       return {
           projectId: config.get('projectId'),
           teamId: config.get('teamId')
       };
   }
   ```

4. Update `extract()` method to include new fields.

**Estimated Time**: 2 hours

---

### Phase 2: Rewrite Permalink Generator (Stateless)

**File**: `shared/lib/github_permalink_generator.py`

**Changes**:

1. Keep `GitHubPermalinkGenerator` class for encapsulation, but remove singleton pattern
2. Add new standalone functions that take repo_url + commit_sha as parameters
3. Remove `init_permalink_generator()` global function
4. Remove `_generator` global variable
5. Update `generate_permalink()` to accept repo_url parameter
6. Update `enrich_markdown_with_permalinks()` to accept repo_url + commit_sha

**Key Signature Changes**:

```python
# OLD (stateful)
init_permalink_generator(repo_url)
generate_permalink(file_path, line_start, line_end)

# NEW (stateless)
generate_permalink(repo_url, file_path, line_start, line_end, commit_sha)
enrich_markdown_with_permalinks(markdown_text, repo_url, commit_sha)
```

**Estimated Time**: 3 hours

---

### Phase 3: Update Orchestrator to Use Workspace Context

**File**: `agent_orchestrator/main.py`

**Changes**:

1. Update `OrchestrationRequest` model to expect workspace context:

   ```python
   class OrchestrationRequest(BaseModel):
       description: str
       priority: str = "medium"
       project_context: Optional[Dict[str, Any]] = None  # NEW: From extension
       session_id: Optional[str] = None
   ```

2. Update `/orchestrate` endpoint:

   - Extract `github_repo_url`, `github_commit_sha` from `project_context`
   - Extract `linear_project_id`, `linear_team_id` from `project_context`
   - Call `enrich_markdown_with_permalinks()` with repo context (if available)
   - Store workspace context in task state for use by `/execute`

3. Remove global permalink generator initialization from startup
4. Remove `GITHUB_REPO_URL` from `.env` requirements

**Estimated Time**: 2 hours

---

### Phase 4: Update Incremental Linear Updater

**File**: `shared/lib/incremental_linear_updater.py`

**Changes**:

1. Add `workspace_context` parameter to `create_task_structure()`:

   ```python
   async def create_task_structure(
       self,
       task_id: str,
       task_description: str,  # Already enriched with permalinks
       subtasks: List[Dict],
       workspace_context: Dict[str, Any],  # NEW: Contains repo_url, commit_sha
       project_id: Optional[str] = None,
       team_id: Optional[str] = None,
   ) -> str:
       ...
   ```

2. Update `update_subtask_complete()` to optionally enrich result with permalinks:
   ```python
   async def update_subtask_complete(
       self,
       subtask_id: str,
       result: Dict,
       workspace_context: Optional[Dict[str, Any]] = None,  # NEW
       artifacts: Optional[Dict[str, str]] = None,
       permalinks: Optional[List[str]] = None,
   ):
       # If workspace_context has GitHub info, enrich result
       if workspace_context and workspace_context.get("github_repo_url"):
           enriched_result = self._enrich_result_with_permalinks(
               result, workspace_context
           )
       else:
           enriched_result = result
       ...
   ```

**Estimated Time**: 2 hours

---

### Phase 5: Rewrite `/execute` Endpoint

**File**: `agent_orchestrator/main.py`

**Changes**:

1. Retrieve task with workspace context from state
2. Initialize `IncrementalLinearUpdater` with workspace context
3. Create Linear issue structure with `project_id` and `team_id` from context
4. Pass workspace context to subtask execution
5. Enrich results with permalinks before updating Linear issues

**Example**:

```python
@app.post("/execute/{task_id}")
async def execute(task_id: str):
    # Retrieve task with workspace context
    task = await state_client.get_task(task_id)
    workspace_ctx = task.get("workspace_context", {})

    # Initialize Linear updater
    linear_client = get_linear_client()
    updater = IncrementalLinearUpdater(linear_client)

    # Create issue structure
    parent_issue_id = await updater.create_task_structure(
        task_id=task_id,
        task_description=task["description"],
        subtasks=task["subtasks"],
        workspace_context=workspace_ctx,
        project_id=workspace_ctx.get("linear_project_id"),
        team_id=workspace_ctx.get("linear_team_id")
    )

    # Execute workflow with incremental updates
    for subtask in task["subtasks"]:
        await updater.update_subtask_start(subtask["id"])

        # Execute subtask (pass workspace context for agent to use)
        result = await execute_subtask(subtask, workspace_ctx)

        # Update Linear with result
        await updater.update_subtask_complete(
            subtask["id"],
            result=result,
            workspace_context=workspace_ctx,  # For permalink enrichment
            artifacts=result.get("artifacts")
        )

    # Mark parent as complete
    await updater.mark_complete()

    return {"status": "completed", "parent_issue_id": parent_issue_id}
```

**Estimated Time**: 4 hours

---

### Phase 6: Update `.env` and Documentation

**Files**:

- `config/env/.env.template`
- `support/docs/DEPLOYMENT_GUIDE.md`
- `extensions/vscode-devtools-copilot/README.md`

**Changes**:

1. Remove `GITHUB_REPO_URL` from `.env.template` (no longer needed)
2. Remove `LINEAR_PROJECT_ID` from `.env.template` (no longer needed)
3. Add documentation for workspace settings in extension README:

   ````markdown
   ## Workspace Configuration

   Create `.vscode/settings.json` in your project:

   ```json
   {
     "devtools.orchestratorUrl": "http://45.55.173.72:8001",
     "devtools.linear.projectId": "your-linear-project-id",
     "devtools.linear.teamId": "your-linear-team-id",
     "devtools.github.enabled": true
   }
   ```
   ````

   **Finding Linear IDs**:

   - Project ID: Open project in Linear → URL has `.../<team-key>/project/<project-id>`
   - Team ID: Use Linear GraphQL API or check team settings

   ```

   ```

4. Update deployment guide to clarify `.env` is for stack-level secrets only

**Estimated Time**: 1 hour

---

## Secrets Management Strategy

### `.env` Scope (Stack-Level Secrets)

**Keep in `.env`** (infrastructure secrets):

- ✅ `LINEAR_API_KEY` (OAuth token for orchestrator)
- ✅ `GRADIENT_API_KEY` (Gradient AI access)
- ✅ `LANGSMITH_API_KEY` (LangSmith tracing)
- ✅ `DB_PASSWORD` (PostgreSQL)
- ✅ `SMTP_USER`, `SMTP_PASS` (Email notifications)
- ✅ `LINEAR_WEBHOOK_SIGNING_SECRET` (Webhook validation)

**Remove from `.env`** (workspace-specific context):

- ❌ `GITHUB_REPO_URL` → Get from workspace git remote
- ❌ `LINEAR_PROJECT_ID` → Get from workspace settings
- ❌ `LINEAR_TEAM_ID` → Get from workspace settings

### Workspace Settings Scope (User-Level Config)

**Add to `.vscode/settings.json` in user's project**:

- ✅ `devtools.linear.projectId`
- ✅ `devtools.linear.teamId`
- ✅ `devtools.github.enabled` (opt-in for permalink features)
- ✅ `devtools.orchestratorUrl` (allows local dev vs production)

### Benefits of This Split

- **Portability**: Dev-Tools agents work across any project
- **Security**: Sensitive tokens stay in orchestrator `.env`, never in user's workspace
- **Flexibility**: Each workspace can target different Linear projects/teams
- **Multi-Project**: User can work on 5 different repos, each with own Linear project
- **Team Collaboration**: Workspace settings can be committed to project repo (project IDs are not secrets)

---

## Testing Strategy

### Unit Tests

1. Test permalink generator with different repo URLs
2. Test context extraction with/without GitHub remote
3. Test Linear updater with/without workspace context

### Integration Tests

1. Submit task from extension for non-Dev-Tools repo
2. Verify permalinks generated for correct repo
3. Verify Linear issues created in correct project
4. Test with missing workspace context (graceful degradation)

### End-to-End Test Scenarios

1. **Scenario A: Full context available**

   - Workspace with GitHub remote + Linear config
   - Verify permalinks in Linear issues
   - Verify issues in correct project

2. **Scenario B: Partial context (GitHub only)**

   - Workspace with GitHub remote, no Linear config
   - Verify permalinks work
   - Verify Linear issues in default project (from `.env` fallback)

3. **Scenario C: No context (non-git workspace)**
   - Workspace without git remote
   - Verify task executes without permalinks
   - Verify Linear issues created (no permalinks)

---

## Migration Path (Backward Compatibility)

To avoid breaking existing deployments:

1. **Phase 1: Add workspace context support** (non-breaking)

   - Extension sends new fields in `project_context`
   - Orchestrator accepts new fields but falls back to `.env` if missing
   - Permalink generator checks for repo_url in request first, then `.env`

2. **Phase 2: Deprecate `.env` fields** (warning)

   - Log warnings when using `GITHUB_REPO_URL` from `.env`
   - Documentation encourages workspace settings

3. **Phase 3: Remove `.env` fields** (breaking, future release)
   - Remove fallback logic
   - Require workspace context in requests

---

## Example Workflow (After Implementation)

### User Perspective

1. Install Dev-Tools extension in VS Code
2. Open any project (not Dev-Tools repo)
3. Create `.vscode/settings.json`:
   ```json
   {
     "devtools.linear.projectId": "my-project-123",
     "devtools.linear.teamId": "my-team-456"
   }
   ```
4. Type in Copilot Chat: `@devtools Implement JWT authentication`
5. Extension extracts workspace context (repo URL from git, commit SHA)
6. Orchestrator receives context, generates permalinks for user's repo
7. Linear issues created in user's Linear project with permalinks

### Orchestrator Perspective

1. Receive request with workspace context
2. Extract `github_repo_url`, `commit_sha`, `linear_project_id`
3. Enrich description with permalinks for user's repo
4. Execute workflow, create Linear issues in user's project
5. Update issues incrementally with results + permalinks

---

## Success Criteria

- ✅ Extension works with any GitHub repository (not just Dev-Tools)
- ✅ Orchestrator has no hardcoded repo URLs
- ✅ Linear issues created in workspace-specified project
- ✅ Permalinks point to correct repository and commit
- ✅ `.env` contains only stack-level secrets
- ✅ User can work on multiple projects without reconfiguring orchestrator
- ✅ Graceful degradation when workspace context unavailable

---

## Open Questions

1. **Fallback behavior**: Should orchestrator reject requests without workspace context, or fall back to `.env` values?

   - **Recommendation**: Log warning and use `.env` fallback for migration period, then require context in future release

2. **Multi-repo projects**: What if workspace has multiple git remotes?

   - **Recommendation**: Use `origin` remote, allow override in workspace settings (`devtools.github.repoUrl`)

3. **Linear project discovery**: Should extension auto-detect Linear project from workspace?

   - **Recommendation**: No, require explicit config. Auto-detection too fragile (API calls, rate limits, ambiguity)

4. **Commit SHA staleness**: What if user's local commit is not pushed to GitHub yet?

   - **Recommendation**: Permalinks still work (404 until pushed). Add warning in Linear issue if commit not found.

5. **Non-GitHub repos**: Support GitLab, Bitbucket, etc.?
   - **Recommendation**: Future enhancement. Start with GitHub only, design for extensibility.

---

## Next Steps

Would you like me to:

1. **Start with Phase 1** (enhance extension context extraction)?
2. **Generate all code changes** in parallel (multi-file refactor)?
3. **Create a migration guide** for existing deployments?
4. **Update test suite** to validate workspace-aware behavior?

Let me know which approach you prefer, and I'll proceed with implementation.
