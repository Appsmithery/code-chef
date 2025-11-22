# GitHub Copilot Custom Agent Integration Guide

**Status**: Implementation Guide  
**Last Updated**: November 22, 2025  
**Related**: LINEAR_INTEGRATION_GUIDE.md, DEPLOYMENT_GUIDE.md

---

## Overview

This guide covers integrating GitHub Copilot's custom agent functionality with the Dev-Tools orchestrator to enable:

1. **GitHub Permalinks** - Reference specific lines/files in issues
2. **Document Attachments** - Attach files/context to Linear issues
3. **Custom Agent Configuration** - Configure Dev-Tools as a GitHub Copilot Agent

---

## GitHub Copilot Permissions

Based on your Linear integration, GitHub Copilot has these active permissions:

- ✅ **Assign issues and projects** to the app in teams it can access
- ✅ **Mention app in issues, projects, and documents** it can access
- ✅ **Read access** to your workspace
- ✅ **Receive realtime updates** about your workspace
- ✅ **Write access** to your workspace

These permissions enable bi-directional sync between GitHub and Linear.

---

## Part 1: GitHub Permalinks in Linear

### What are GitHub Permalinks?

GitHub permalinks are permanent URLs to specific lines/files at a specific commit:

```
https://github.com/Appsmithery/Dev-Tools/blob/<commit-sha>/path/to/file.py#L123-L145
```

**Benefits**:

- References stay valid even if file is moved/renamed
- Shows exact code context at time of issue creation
- Links to specific line ranges for precision

### Implementation Strategy

#### Option 1: Automatic Permalink Generation (Recommended)

When creating Linear issues via orchestrator, automatically generate GitHub permalinks for relevant files:

**Workflow**:

1. User mentions file in task description
2. Orchestrator detects file reference via NLP
3. Orchestrator queries git for current commit SHA
4. Generate permalink: `https://github.com/{owner}/{repo}/blob/{sha}/{file}#L{start}-L{end}`
5. Add permalink to Linear issue description

**Implementation** (`shared/lib/github_permalink_generator.py`):

```python
import subprocess
from typing import Optional, List
from pydantic import BaseModel

class FileReference(BaseModel):
    file_path: str
    start_line: Optional[int] = None
    end_line: Optional[int] = None

class GitHubPermalink(BaseModel):
    url: str
    file_path: str
    commit_sha: str
    line_range: Optional[str] = None

def get_current_commit_sha(repo_path: str = ".") -> str:
    """Get current git commit SHA"""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout.strip()

def get_repo_url_from_remote(repo_path: str = ".") -> str:
    """Extract GitHub repo URL from git remote"""
    result = subprocess.run(
        ["git", "config", "--get", "remote.origin.url"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True
    )
    url = result.stdout.strip()

    # Convert SSH to HTTPS
    if url.startswith("git@github.com:"):
        url = url.replace("git@github.com:", "https://github.com/")

    # Remove .git suffix
    if url.endswith(".git"):
        url = url[:-4]

    return url

def generate_permalink(
    file_ref: FileReference,
    repo_path: str = ".",
    commit_sha: Optional[str] = None
) -> GitHubPermalink:
    """Generate GitHub permalink for file reference"""
    if not commit_sha:
        commit_sha = get_current_commit_sha(repo_path)

    repo_url = get_repo_url_from_remote(repo_path)

    # Build permalink
    url = f"{repo_url}/blob/{commit_sha}/{file_ref.file_path}"

    # Add line range if specified
    line_range = None
    if file_ref.start_line:
        if file_ref.end_line and file_ref.end_line != file_ref.start_line:
            url += f"#L{file_ref.start_line}-L{file_ref.end_line}"
            line_range = f"L{file_ref.start_line}-L{file_ref.end_line}"
        else:
            url += f"#L{file_ref.start_line}"
            line_range = f"L{file_ref.start_line}"

    return GitHubPermalink(
        url=url,
        file_path=file_ref.file_path,
        commit_sha=commit_sha,
        line_range=line_range
    )

def extract_file_references_from_text(text: str) -> List[FileReference]:
    """Extract file paths from task description using heuristics"""
    import re

    # Pattern 1: Explicit file paths (e.g., "in file.py" or "src/main.py")
    file_pattern = r'\b(?:in\s+)?([a-zA-Z0-9_\-/]+\.(?:py|ts|js|md|yaml|json|sh))\b'

    # Pattern 2: Line references (e.g., "line 123" or "lines 45-67")
    line_pattern = r'lines?\s+(\d+)(?:-(\d+))?'

    file_matches = re.findall(file_pattern, text, re.IGNORECASE)
    line_matches = re.findall(line_pattern, text, re.IGNORECASE)

    refs = []
    for file_path in file_matches:
        # Check if there's a line reference nearby
        start_line = None
        end_line = None

        if line_matches:
            # Assume first line match applies to this file
            start_line = int(line_matches[0][0])
            if line_matches[0][1]:
                end_line = int(line_matches[0][1])

        refs.append(FileReference(
            file_path=file_path,
            start_line=start_line,
            end_line=end_line
        ))

    return refs

# Usage in orchestrator
async def enrich_linear_issue_with_permalinks(
    task_description: str,
    project_context: dict
) -> str:
    """Enrich Linear issue description with GitHub permalinks"""
    repo_path = project_context.get("workspace_path", ".")

    # Extract file references
    file_refs = extract_file_references_from_text(task_description)

    if not file_refs:
        return task_description

    # Generate permalinks
    enriched_description = task_description + "\n\n**Referenced Files:**\n"

    for ref in file_refs:
        try:
            permalink = generate_permalink(ref, repo_path)
            enriched_description += f"- [{ref.file_path}]({permalink.url})"
            if permalink.line_range:
                enriched_description += f" ({permalink.line_range})"
            enriched_description += f" @ `{permalink.commit_sha[:7]}`\n"
        except Exception as e:
            logger.warning(f"Failed to generate permalink for {ref.file_path}: {e}")

    return enriched_description
```

**Orchestrator Integration** (`agent_orchestrator/main.py`):

```python
# In /orchestrate endpoint, before creating Linear issue
if linear_client and task_requires_linear_issue(request):
    enriched_description = await enrich_linear_issue_with_permalinks(
        task_description=request.description,
        project_context=request.project_context or {}
    )

    linear_issue = await linear_client.create_issue(
        title=generate_issue_title(request.description),
        description=enriched_description,  # Use enriched version
        team_id=os.getenv("LINEAR_TEAM_ID"),
        project_id=request.project_context.get("linear_project_id")
    )
```

#### Option 2: Manual Permalink Insertion

Allow users to manually insert GitHub permalinks in task descriptions:

**VS Code Extension Enhancement**:

1. Add context menu action: "Copy GitHub Permalink"
2. When user right-clicks in editor, copy permalink to clipboard
3. User pastes into `@devtools` chat prompt

**Implementation** (`extensions/vscode-devtools-copilot/src/extension.ts`):

```typescript
// Register command
context.subscriptions.push(
  vscode.commands.registerCommand("devtools.copyGithubPermalink", async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showErrorMessage("No active editor");
      return;
    }

    const selection = editor.selection;
    const filePath = vscode.workspace.asRelativePath(editor.document.uri);

    // Get current git commit
    const gitExtension = vscode.extensions.getExtension("vscode.git")?.exports;
    const git = gitExtension?.getAPI(1);
    const repo = git?.repositories[0];

    if (!repo) {
      vscode.window.showErrorMessage("Not a git repository");
      return;
    }

    const commitSha = repo.state.HEAD?.commit;
    const remoteUrl = repo.state.remotes[0]?.fetchUrl || "";

    // Convert SSH to HTTPS
    let githubUrl = remoteUrl
      .replace("git@github.com:", "https://github.com/")
      .replace(".git", "");

    // Build permalink
    const lineRange = selection.isEmpty
      ? `#L${selection.start.line + 1}`
      : `#L${selection.start.line + 1}-L${selection.end.line + 1}`;

    const permalink = `${githubUrl}/blob/${commitSha}/${filePath}${lineRange}`;

    await vscode.env.clipboard.writeText(permalink);
    vscode.window.showInformationMessage(
      "GitHub permalink copied to clipboard!"
    );
  })
);
```

---

## Part 2: Document Attachments in Linear

### What are Document Attachments?

Document attachments allow you to attach files, images, logs, or other artifacts to Linear issues for context.

### Implementation Strategy

#### Option 1: Upload Files to GitHub Gist + Link in Linear

**Workflow**:

1. User attaches file in task submission
2. Orchestrator uploads to GitHub Gist (private)
3. Embed Gist URL in Linear issue description
4. Linear renders Gist preview inline

**Implementation** (`shared/lib/github_gist_uploader.py`):

```python
import httpx
from typing import Dict, List
from pydantic import BaseModel

class GistFile(BaseModel):
    filename: str
    content: str

class GistUploadResponse(BaseModel):
    gist_url: str
    gist_id: str
    files: Dict[str, str]  # filename -> raw_url

async def upload_to_gist(
    files: List[GistFile],
    description: str,
    public: bool = False,
    github_token: str = None
) -> GistUploadResponse:
    """Upload files to GitHub Gist"""
    if not github_token:
        github_token = os.getenv("GITHUB_PAT")

    # Build Gist API payload
    gist_files = {
        file.filename: {"content": file.content}
        for file in files
    }

    payload = {
        "description": description,
        "public": public,
        "files": gist_files
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.github.com/gists",
            json=payload,
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28"
            }
        )
        response.raise_for_status()

        data = response.json()

        return GistUploadResponse(
            gist_url=data["html_url"],
            gist_id=data["id"],
            files={
                name: file_data["raw_url"]
                for name, file_data in data["files"].items()
            }
        )

# Usage in orchestrator
async def attach_files_to_linear_issue(
    issue_id: str,
    attachments: List[Dict[str, str]],  # [{"filename": "...", "content": "..."}]
    github_token: str
) -> str:
    """Attach files via GitHub Gist and update Linear issue"""

    # Upload to Gist
    gist_files = [GistFile(**attach) for attach in attachments]
    gist_response = await upload_to_gist(
        files=gist_files,
        description=f"Attachments for Linear issue {issue_id}",
        public=False,
        github_token=github_token
    )

    # Update Linear issue description
    attachment_section = "\n\n**Attachments:**\n"
    for filename, raw_url in gist_response.files.items():
        attachment_section += f"- [{filename}]({raw_url})\n"

    attachment_section += f"\n[View all attachments]({gist_response.gist_url})"

    return attachment_section
```

#### Option 2: Use Linear's Native Attachment API

**Note**: Linear GraphQL API supports file uploads via multipart/form-data.

**Implementation** (`shared/lib/linear_client.py`):

```python
async def upload_attachment_to_linear(
    issue_id: str,
    file_path: str,
    linear_api_key: str
) -> str:
    """Upload file attachment directly to Linear"""
    import aiofiles

    async with aiofiles.open(file_path, 'rb') as f:
        file_content = await f.read()

    # Step 1: Request upload URL
    query = """
    mutation FileUpload($contentType: String!, $filename: String!, $size: Int!) {
      fileUpload(contentType: $contentType, filename: $filename, size: $size) {
        uploadUrl
        assetUrl
      }
    }
    """

    import os
    import mimetypes

    filename = os.path.basename(file_path)
    content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
    file_size = len(file_content)

    async with httpx.AsyncClient() as client:
        # Get upload URL
        response = await client.post(
            "https://api.linear.app/graphql",
            json={
                "query": query,
                "variables": {
                    "contentType": content_type,
                    "filename": filename,
                    "size": file_size
                }
            },
            headers={
                "Authorization": linear_api_key,
                "Content-Type": "application/json"
            }
        )
        response.raise_for_status()

        data = response.json()["data"]["fileUpload"]
        upload_url = data["uploadUrl"]
        asset_url = data["assetUrl"]

        # Step 2: Upload file to S3
        await client.put(
            upload_url,
            content=file_content,
            headers={"Content-Type": content_type}
        )

        # Step 3: Attach to issue
        attach_query = """
        mutation AttachmentCreate($issueId: String!, $url: String!, $title: String!) {
          attachmentCreate(input: {
            issueId: $issueId
            url: $url
            title: $title
          }) {
            attachment {
              id
              url
            }
          }
        }
        """

        attach_response = await client.post(
            "https://api.linear.app/graphql",
            json={
                "query": attach_query,
                "variables": {
                    "issueId": issue_id,
                    "url": asset_url,
                    "title": filename
                }
            },
            headers={
                "Authorization": linear_api_key,
                "Content-Type": "application/json"
            }
        )
        attach_response.raise_for_status()

        return asset_url
```

---

## Part 3: GitHub Copilot Custom Agent Configuration

### Custom Agent Definition File

Based on your screenshot, GitHub Copilot expects a `.github/copilot-agent.json` configuration:

**Create** (`.github/copilot-agent.json`):

```json
{
  "name": "Dev-Tools Orchestrator",
  "description": "Central orchestration layer for Dev-Tools agent fleet - decomposes tasks, routes to specialist agents, coordinates workflows across 6 FastAPI services",
  "version": "1.0.0",
  "visibility": "workspace",
  "agents": [
    {
      "id": "orchestrator",
      "name": "Orchestrator",
      "description": "Multi-agent orchestration with LangGraph workflow engine and progressive tool disclosure",
      "icon": "🎯",
      "endpoints": {
        "chat": "http://45.55.173.72:8001/chat",
        "status": "http://45.55.173.72:8001/tasks/{taskId}"
      },
      "capabilities": [
        "task-decomposition",
        "agent-routing",
        "workflow-coordination",
        "hitl-approvals",
        "progressive-tool-disclosure"
      ],
      "tools": [
        "memory",
        "context7",
        "gitmcp",
        "rust-mcp-filesystem",
        "dockerhub",
        "playwright",
        "notion"
      ],
      "model": "llama-3.1-70b-instruct",
      "provider": "digitalocean-gradient"
    }
  ],
  "integrations": {
    "linear": {
      "enabled": true,
      "workspace": "dev-ops",
      "approvalHub": "DEV-68"
    },
    "github": {
      "enabled": true,
      "permalinks": true,
      "attachments": {
        "provider": "gist",
        "visibility": "private"
      }
    },
    "langsmith": {
      "enabled": true,
      "project": "dev-tools-agents"
    }
  }
}
```

### VS Code Custom Agent Registration

**Update** (`extensions/vscode-devtools-copilot/package.json`):

```json
{
  "contributes": {
    "chatParticipants": [
      {
        "id": "devtools",
        "name": "devtools-orchestrator",
        "description": "LangGraph orchestrator with LangChain function calling...",
        "isSticky": true,
        "customAgent": {
          "configFile": ".github/copilot-agent.json",
          "mode": "agent"
        }
      }
    ]
  }
}
```

### Chat Participant Modes

GitHub Copilot Chat Participants support two modes:

1. **Ask Mode** (Default) - Query-only, no execution

   - User: `@devtools how do I deploy?`
   - Agent: Returns answer, no actions taken

2. **Agent Mode** - Full execution capabilities
   - User: `@devtools deploy to staging`
   - Agent: Actually executes deployment workflow

**Detecting Mode** (`src/chatParticipant.ts`):

```typescript
async handleChatRequest(
    request: vscode.ChatRequest,
    context: vscode.ChatContext,
    stream: vscode.ChatResponseStream,
    token: vscode.CancellationToken
): Promise<vscode.ChatResult> {
    // Check if in Agent mode (execution allowed)
    const isAgentMode = request.variables?.some(v => v.name === 'agent');

    if (isAgentMode) {
        // Execute workflow
        const response = await this.client.orchestrate({...});
        await this.client.execute(response.task_id);
    } else {
        // Ask mode - return plan only
        const response = await this.client.orchestrate({...});
        // Don't call execute()
    }
}
```

---

## Part 4: Complete Integration Workflow

### End-to-End Example

**Scenario**: User submits task with file references

```
@devtools Implement JWT authentication in src/auth.py lines 45-67, review security,
and deploy to staging. See config/auth.yaml for current setup.
```

**Workflow**:

1. **VS Code Extension** (`chatParticipant.ts`)

   - Detect Agent mode
   - Extract workspace context
   - Submit to orchestrator

2. **Orchestrator** (`/orchestrate`)

   - Parse file references: `src/auth.py:45-67`, `config/auth.yaml`
   - Generate GitHub permalinks
   - Decompose into subtasks
   - Create Linear issue with permalinks
   - Check risk level → requires approval

3. **HITL Approval** (`/webhooks/linear`)

   - User approves in Linear DEV-68 sub-issue
   - Webhook triggers workflow resumption

4. **Execution** (`/execute/{task_id}`)

   - Route to feature-dev agent
   - Attach logs/diffs to Linear via Gist
   - Route to code-review agent
   - Update Linear with security findings
   - Route to cicd agent
   - Attach deployment logs

5. **VS Code Extension** (`/status`)
   - Poll for completion
   - Render results with GitHub permalink references
   - Display attached artifacts (logs, diffs)

---

## Configuration Checklist

- [ ] Set `GITHUB_PAT` environment variable (for Gist uploads)
- [ ] Add `github_permalink_generator.py` to `shared/lib/`
- [ ] Add `github_gist_uploader.py` to `shared/lib/`
- [ ] Update `linear_client.py` with file attachment methods
- [ ] Create `.github/copilot-agent.json` configuration
- [ ] Update VS Code extension `package.json` with custom agent config
- [ ] Update `chatParticipant.ts` to handle Agent vs Ask mode
- [ ] Add `execute()` method to `orchestratorClient.ts` ✅
- [ ] Update `/orchestrate` endpoint to enrich descriptions with permalinks
- [ ] Test with: `@devtools Implement feature in src/main.py lines 100-150`

---

## Testing

### Test GitHub Permalinks

```bash
# Test permalink generation
curl -X POST http://45.55.173.72:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Fix bug in src/auth.py lines 45-67",
    "priority": "high",
    "project_context": {
      "workspace_path": "/opt/Dev-Tools",
      "git_branch": "main"
    }
  }'

# Expected: Linear issue contains permalink to src/auth.py#L45-L67 at current commit
```

### Test Document Attachments

```bash
# Test Gist upload
python - << 'EOF'
import asyncio
from shared.lib.github_gist_uploader import upload_to_gist, GistFile

async def test():
    files = [
        GistFile(filename="error.log", content="Error trace here..."),
        GistFile(filename="config.yaml", content="config: value")
    ]
    response = await upload_to_gist(
        files=files,
        description="Test attachments",
        public=False
    )
    print(f"Gist URL: {response.gist_url}")

asyncio.run(test())
EOF
```

### Test Agent Mode

In VS Code:

1. Open Copilot Chat
2. Click Agent mode (icon in top-right)
3. Submit: `@devtools deploy to staging`
4. Verify workflow executes automatically

---

## Troubleshooting

### Permalinks Not Generating

**Issue**: No permalinks in Linear issue  
**Fix**: Check git repository access

```bash
cd /opt/Dev-Tools
git rev-parse HEAD  # Should return commit SHA
git config --get remote.origin.url  # Should return GitHub URL
```

### Gist Upload Fails

**Issue**: HTTP 401 from Gist API  
**Fix**: Verify GitHub PAT has `gist` scope

```bash
curl -H "Authorization: Bearer $GITHUB_PAT" https://api.github.com/gists
# Should return 200, not 401
```

### Agent Mode Not Working

**Issue**: Tasks planned but not executed  
**Fix**: Check Agent mode indicator in VS Code

- Look for "🤖 Agent" icon in chat header
- If in Ask mode, tasks won't execute automatically

---

## Next Steps

1. ✅ Fixed `/tasks/{taskId}` endpoint bug
2. ✅ Added `execute()` method to orchestrator client
3. ✅ Updated chat participant to call execute automatically in Agent mode
4. 📝 Implement `github_permalink_generator.py`
5. 📝 Implement `github_gist_uploader.py`
6. 📝 Create `.github/copilot-agent.json` configuration
7. 📝 Test end-to-end workflow with file references

---

**References**:

- GitHub Gist API: https://docs.github.com/en/rest/gists
- Linear Attachments API: https://developers.linear.app/docs/graphql/working-with-the-graphql-api#uploading-files
- GitHub Copilot Custom Agents: https://code.visualstudio.com/docs/copilot/copilot-extensibility-overview
