#!/usr/bin/env python3
"""
Update Linear Phase 5 Copilot Integration issue with comprehensive implementation plan.
"""

import asyncio
import json
import os
import sys
import aiohttp


async def update_linear_issue(issue_id: str, description: str, api_key: str):
    """Update Linear issue using GraphQL mutation."""
    
    mutation = """
    mutation IssueUpdate($id: String!, $description: String!) {
      issueUpdate(id: $id, input: { description: $description }) {
        success
        issue {
          id
          title
          url
        }
      }
    }
    """
    
    variables = {
        "id": issue_id,
        "description": description
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}" if not api_key.startswith("Bearer ") else api_key
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.linear.app/graphql",
            json={"query": mutation, "variables": variables},
            headers=headers
        ) as response:
            result = await response.json()
            
            if response.status != 200:
                print(f"❌ API error: {response.status}")
                print(json.dumps(result, indent=2))
                return False
            
            if "errors" in result:
                print(f"❌ GraphQL errors:")
                print(json.dumps(result["errors"], indent=2))
                return False
            
            if result.get("data", {}).get("issueUpdate", {}).get("success"):
                issue = result["data"]["issueUpdate"]["issue"]
                print(f"✅ Successfully updated: {issue['title']}")
                print(f"   URL: {issue['url']}")
                return True
            else:
                print("❌ Update failed")
                print(json.dumps(result, indent=2))
                return False


async def main():
    """Update Phase 5 Copilot Integration issue with multi-project scoping architecture."""
    
    # Get API key from environment
    api_key = os.getenv("LINEAR_API_KEY")
    if not api_key:
        print("❌ LINEAR_API_KEY environment variable not set")
        print("   Get your API key from: https://linear.app/project-roadmaps/settings/api")
        return 1
    
    # Phase 5 Copilot Integration issue ID
    issue_id = "8927bac5-ca95-4ce9-a6ac-9bb79cc8aaa9"
    
    description = """## Phase 5: Copilot Integration Layer - REVISED PLAN

**Status**: Planning  
**Target Duration**: 7 days  
**Dependencies**: Phase 2 HITL Complete ✅, Phase 3 Observability Complete ✅

---

### Executive Summary

Phase 5 transforms Dev-Tools into a conversational AI assistant with **workspace-level notification management** for multi-project support. This phase replaces Slack-based notifications with Linear's native workspace hub, enabling centralized approval visibility across all projects (dev-tools, twkr, future).

**Key Revisions from Original Plan**:
- ❌ Slack Integration → ✅ Linear Workspace Hub (native notifications)
- ❌ Project-level notifications → ✅ Workspace-level approval hub
- ❌ Flat agent architecture → ✅ Multi-project scoping with security guardrails

---

### Task 5.1: Conversational Chat Interface

**Endpoint**: `POST /chat`  
**Duration**: Day 1-2

Natural language task submission with intent recognition and multi-turn clarification.

**Implementation**:
```python
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # 1. Load session context (HybridMemory)
    # 2. Intent recognition (Gradient LLM)
    # 3. Clarification loop (if needed)
    # 4. Task decomposition → /orchestrate
    # 5. Streaming response
```

**Key Features**:
- Multi-turn conversations (3+ turns)
- Session persistence (PostgreSQL + hybrid memory)
- Intent recognition (90%+ accuracy target)
- Streaming responses via Server-Sent Events

**Artifacts**:
- `agent_orchestrator/chat_endpoint.py`
- `shared/lib/intent_recognizer.py`
- `shared/lib/session_manager.py`

---

### Task 5.2: Workspace-Level Notification System (REVISED)

**Architecture**: Multi-project workspace hub with scoping enforcement  
**Duration**: Day 3-5

**Multi-Project Architecture**:
```
┌──────────────────────────────────────────────────────────┐
│             Linear Workspace: "project-roadmaps"         │
│              Team ID: f5b610be-ac34-4983-918b-2c9d00aa9b7a │
└──────────────────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │ dev-tools│   │   twkr   │   │  future  │
   │ Project  │   │ Project  │   │ Projects │
   └──────────┘   └──────────┘   └──────────┘
         │               │               │
         └───────────────┴───────────────┘
                         │
                         ▼
           ┌────────────────────────────┐
           │  🤖 Agent Approvals Hub    │ ← Workspace-level issue
           │  (Team Issue, not Project) │
           │                            │
           │  All approval requests     │
           │  from all projects posted  │
           │  here as comments          │
           └────────────────────────────┘
                         │
                         ▼
              User sees via Linear:
              • Desktop notifications
              • Email notifications
              • Mobile notifications
              • @mention alerts
```

**Scoping Rules**:
- **Orchestrator**: Workspace-level access (LinearWorkspaceClient)
  - Can post to workspace approval hub
  - Can create new projects
  - Can read all projects
  - CANNOT modify project-specific issues

- **Subagents**: Project-scoped access (LinearProjectClient)
  - Can only comment on issues in assigned project
  - CANNOT access approval hub
  - CANNOT access other projects
  - Client factory enforces scope via agent_name check

**Implementation Steps**:

1. **Linear Client Factory** (Day 3)
```python
# shared/lib/linear_client_factory.py
def get_linear_client(agent_name: str, project_name: str):
    if agent_name == "orchestrator":
        return LinearWorkspaceClient(workspace_id="project-roadmaps")
    else:
        return LinearProjectClient(
            project_id=get_project_id(project_name),
            allowed_agent=agent_name
        )
```

2. **Event Bus** (Day 3)
```python
# shared/lib/event_bus.py
class EventBus:
    def publish(self, event: WorkflowEvent):
        # Route to appropriate notifiers
        if event.type == "approval_required":
            workspace_notifier.notify(event)  # → Workspace hub
        elif event.type == "task_progress":
            project_notifier.notify(event)     # → Project issue
```

3. **LinearWorkspaceClient** (Day 4)
```python
# shared/lib/linear_workspace_client.py
class LinearWorkspaceClient:
    async def post_approval_request(self, approval_id: str, details: dict):
        # Post to workspace-level approval hub
        comment = (
            f"## Approval Required: {approval_id}\\n"
            f"**Project**: {details['project_name']}\\n"
            f"**Agent**: {details['agent_name']}\\n"
            f"**Risk**: {details['risk_level']}\\n\\n"
            f"[View Details]({details['approval_url']})\\n\\n"
            f"@{details['requester']} - Your approval is needed."
        )
        await self._create_comment(APPROVAL_HUB_ISSUE_ID, comment)
```

4. **LinearProjectClient** (Day 4)
```python
# shared/lib/linear_project_client.py
class LinearProjectClient:
    async def post_progress_update(self, issue_id: str, message: str):
        # Verify issue belongs to this project
        await self._verify_issue_in_project(issue_id)
        
        # Post project-scoped comment
        await self._create_comment(issue_id, f"🤖 {message}")
```

5. **Event Wiring** (Day 5)
```python
# Orchestrator workflow
event_bus.subscribe("approval_required", workspace_notifier.notify)
event_bus.subscribe("approval_completed", workspace_notifier.notify)

# Subagent workflows
event_bus.subscribe("task_progress", project_notifier.notify)
event_bus.subscribe("task_completed", project_notifier.notify)
```

6. **Configuration** (Day 5)
```yaml
# config/hitl/notification-config.yaml
workspace:
  id: "project-roadmaps"
  team_id: "f5b610be-ac34-4983-918b-2c9d00aa9b7a"
  approval_hub_issue_id: "PR-XXX"  # To be created manually

projects:
  dev-tools:
    id: "b21cbaa1-9f09-40f4-b62a-73e0f86dd501"
    short_id: "78b3b839d36b"
  twkr:
    id: null  # Created by orchestrator on-demand

channels:
  linear:
    workspace_notifications: true
    project_updates: true
  email:
    enabled: true
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    from_address: "agent@appsmithery.co"
    critical_only: true  # Only for high/critical approvals

routing:
  approval_required: ["linear_workspace", "email_critical"]
  approval_completed: ["linear_workspace"]
  task_progress: ["linear_project"]
  task_completed: ["linear_project"]
  error: ["linear_workspace", "email_critical"]

# config/linear/project-registry.yaml
agent_permissions:
  orchestrator:
    scope: "workspace"
    projects: ["*"]
    can_create_projects: true
    can_post_to_hub: true
  
  feature-dev:
    scope: "project"
    projects: ["${PROJECT_NAME}"]  # From env
    can_post_to_hub: false
  
  code-review:
    scope: "project"
    projects: ["${PROJECT_NAME}"]
    can_post_to_hub: false
```

**Artifacts**:
- `shared/lib/linear_workspace_client.py`
- `shared/lib/linear_project_client.py`
- `shared/lib/linear_client_factory.py`
- `shared/lib/notifiers/linear_workspace_notifier.py`
- `shared/lib/notifiers/linear_project_notifier.py`
- `shared/lib/notifiers/email_notifier.py`
- `config/hitl/notification-config.yaml`
- `config/linear/project-registry.yaml`

**Acceptance Criteria**:
✅ Workspace hub receives all approval requests from all projects  
✅ Subagents can only comment on their assigned project  
✅ Email fallback works for critical/high risk approvals  
✅ Linear native notifications deliver within 5 seconds  
✅ Security: Subagents cannot access approval hub or other projects  
✅ Security: Client factory enforces scoping based on agent_name  
✅ Multi-project: Works with dev-tools and twkr simultaneously  

---

### 7-Day Implementation Timeline

**Day 1-2**: Chat Endpoint + Intent Recognition
- ✅ `/chat` endpoint with SSE streaming
- ✅ Session management (PostgreSQL)
- ✅ Intent recognizer (Gradient LLM)
- ✅ Multi-turn clarification loop

**Day 3**: Client Factory + Scoping Architecture
- ✅ `LinearClientFactory` with orchestrator/subagent routing
- ✅ `LinearWorkspaceClient` (workspace-level permissions)
- ✅ `LinearProjectClient` (project-scoped permissions)
- ✅ Security tests (subagent access restrictions)

**Day 4**: Workspace/Project Notifiers
- ✅ `LinearWorkspaceNotifier` (approval hub posting)
- ✅ `LinearProjectNotifier` (project-scoped updates)
- ✅ `EmailNotifier` (critical fallback)
- ✅ Event bus wiring

**Day 5**: Multi-Project Wiring
- ✅ Update orchestrator to inject PROJECT_NAME env
- ✅ Project registry configuration
- ✅ Agent permission matrix
- ✅ Cross-project isolation tests

**Day 6**: Integration Testing
- ✅ End-to-end approval flow (dev-tools project)
- ✅ End-to-end approval flow (twkr project)
- ✅ Verify notifications in Linear Inbox
- ✅ Email delivery tests
- ✅ Security: Subagent cannot post to approval hub
- ✅ Security: Subagent cannot access other project's issues

**Day 7**: Documentation + Deployment
- ✅ Operator guide for workspace hub setup
- ✅ Agent configuration documentation
- ✅ Deploy to droplet (45.55.173.72)
- ✅ Smoke tests in production

---

### Environment Configuration

Add to `config/env/.env`:
```bash
# Linear Workspace Configuration
LINEAR_WORKSPACE_ID="project-roadmaps"
LINEAR_TEAM_ID="f5b610be-ac34-4983-918b-2c9d00aa9b7a"
LINEAR_APPROVAL_HUB_ISSUE_ID="PR-XXX"  # Create manually first

# Project Scoping
PROJECT_NAME="dev-tools"  # Or "twkr", set per-agent in compose

# Email Fallback (Critical Approvals Only)
SMTP_HOST="smtp.gmail.com"
SMTP_PORT="587"
SMTP_USER="agent@appsmithery.co"
SMTP_PASSWORD="${SMTP_APP_PASSWORD}"
SMTP_FROM="agent@appsmithery.co"

# Existing Linear Config (keep)
LINEAR_API_KEY="lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571"
LINEAR_PROJECT_ID="b21cbaa1-9f09-40f4-b62a-73e0f86dd501"
```

---

### Prerequisites (Manual Setup Required)

1. **Create Workspace Approval Hub in Linear**:
   - Go to Linear → Project Roadmaps (PR) team
   - Create new issue: "🤖 Agent Approvals Hub"
   - Assign to yourself
   - Copy issue ID (e.g., PR-99) → Update `LINEAR_APPROVAL_HUB_ISSUE_ID` in `.env`
   - Add label: `hitl`, `approvals`, `workspace-level`

2. **Update `shared/lib/linear_roadmap.py`**:
   ```python
   APPROVAL_HUB_ISSUE_ID = "PR-99"  # From step 1
   ```

3. **Verify Linear OAuth Token** (already configured):
   - Token: `lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571`
   - Workspace: `project-roadmaps` (formerly `vibecoding-roadmap`)

---

### Security Model

**Orchestrator (Workspace-Level)**:
- ✅ Create projects
- ✅ Post to approval hub
- ✅ Read all projects
- ❌ Modify project issues directly

**Subagents (Project-Scoped)**:
- ✅ Comment on issues in assigned project
- ✅ Update status in assigned project
- ❌ Access approval hub
- ❌ Access other projects
- ❌ Create projects

**Enforcement**: `LinearClientFactory` checks `agent_name` parameter and returns appropriate client type. All subagent calls include `_verify_issue_in_project()` check before API calls.

---

### Success Metrics

- ✅ 90%+ intent recognition accuracy on dev task descriptions
- ✅ Multi-turn conversations (3+ turns average)
- ✅ Workspace hub notifications within 5 seconds
- ✅ Email delivery <10 seconds for critical approvals
- ✅ Zero cross-project access violations in security tests
- ✅ Session persistence across agent restarts

---

### Next Steps After Phase 5

**Phase 6**: VS Code Extension (Optional)
- Copilot panel for embedded chat
- Right-click context menu integration
- Inline suggestions for agent tasks

**Phase 7**: Advanced RAG (Optional)
- Multi-project context indexing
- Cross-project knowledge sharing
- Intelligent issue linking

---

**Artifact**: Full implementation plan in `support/docs/PHASE_5_PLAN.md` (800+ lines)
"""
    
    print(f"📝 Updating Linear Phase 5 issue {issue_id}...")
    
    success = await update_linear_issue(issue_id, description, api_key)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
