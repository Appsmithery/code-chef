# Linear Integration Implementation Plan

**Status:** In Progress  
**Started:** November 20, 2025  
**Target Completion:** November 27, 2025

## Overview

Enhance Linear integration with VS Code extension, issue templates, GitHub permalinks, sub-issue automation, and webhook support for real-time approval notifications.

---

## Implementation Phases

### ✅ Phase 0: Prerequisites (Complete)

- [x] Linear OAuth app configured (`.minions`)
- [x] Webhook enabled: `https://theshop.appsmithery.co/webhook`
- [x] Agent-specific labels created (`minion-labels` group)
- [x] Approval hub issue: PR-68
- [x] Environment variables in `.env`

### 🔄 Phase 1: VS Code Extension Setup (In Progress)

**Timeline:** Day 1 (Today)  
**Effort:** 30 minutes

#### Tasks:

1. [x] Install Linear Connect extension (correct ID: `linear.linear-connect`)
2. [ ] Configure workspace settings
3. [ ] Test OAuth flow with existing Linear app
4. [ ] Document usage for team

**Files Modified:**

- `.vscode/settings.json` (create/update)
- `extensions/vscode-devtools-copilot/package.json` (add dependency)

---

### 📋 Phase 2: Issue Templates (Planned)

**Timeline:** Day 1-2  
**Effort:** 2 hours

#### Template 1: HITL Approval Request

**Scope:** Workspace-wide  
**Usage:** All agents posting to PR-68

**Fields:**

- Agent name (dropdown: orchestrator, feature-dev, code-review, infrastructure, cicd, documentation)
- Task ID (text)
- Priority (dropdown: critical, high, medium, low)
- Context (markdown)
- Proposed changes (markdown)
- Rationale (markdown)
- Risks & considerations (markdown)
- Deadline (date)

**Default Properties:**

- Team: Project Roadmaps (PR)
- Project: AI DevOps Agent Platform
- Parent: PR-68
- Priority: Urgent
- Assignee: alextorelli28
- Labels: Auto-set based on agent field

#### Template 2-7: Agent-Specific Sub-Issue Templates

**Scope:** Project-scoped (AI DevOps Agent Platform)

**Per Agent:**

1. **Orchestrator Task** - Task decomposition tracking
2. **Feature-Dev Task** - Feature development sub-issue
3. **Code-Review Task** - Code review checklist
4. **Infrastructure Task** - Infrastructure change tracking
5. **CI/CD Task** - Pipeline/deployment tracking
6. **Documentation Task** - Docs generation/update

**Common Fields:**

- Parent task ID
- Estimated complexity (simple/moderate/complex)
- Requirements (markdown)
- Acceptance criteria (checklist)
- Technical approach (markdown)
- Dependencies (text)
- Files/modules affected (text)

**Agent-Specific Fields:**

- **Feature-Dev**: Code generation strategy, test coverage target
- **Code-Review**: Security checklist, performance impact
- **Infrastructure**: Cost estimate, rollback plan, environment
- **CI/CD**: Pipeline stages, deployment strategy
- **Documentation**: Target audience, format (API/guide/tutorial)

**Files Created:**

- `config/linear/templates/hitl-approval.md` (template spec)
- `config/linear/templates/agent-tasks/*.md` (6 agent templates)

---

### 🔗 Phase 3: GitHub Permalinks (Planned)

**Timeline:** Day 2-3  
**Effort:** 2 hours

#### Enhancements to `linear_workspace_client.py`:

**New Methods:**

```python
def generate_github_permalink(
    repo: str,
    file_path: str,
    line_start: int,
    line_end: Optional[int] = None,
    commit_sha: Optional[str] = None
) -> str
```

**Integration Points:**

- Orchestrator: Include permalinks in approval requests
- Agents: Reference code in sub-issue descriptions
- Code-Review: Link to files requiring review

**Files Modified:**

- `shared/lib/linear_workspace_client.py`
- `agent_orchestrator/main.py` (update approval formatting)
- `agent_*/service.py` (update sub-issue creation)

---

### 📄 Phase 4: Issue Documents Support (Planned)

**Timeline:** Day 3  
**Effort:** 1 hour

#### New Method in `linear_workspace_client.py`:

```python
async def create_issue_with_document(
    self,
    title: str,
    description: str,
    document_markdown: str,  # NEW
    project_id: str,
    labels: List[str],
    parent_id: Optional[str] = None
) -> Dict[str, Any]
```

**Use Cases:**

- Attach detailed task decomposition analysis to HITL approvals
- Include LangSmith trace summaries
- Post-mortem documentation for failed tasks
- Architecture decision records (ADRs)

**Files Modified:**

- `shared/lib/linear_workspace_client.py`

---

### 🤖 Phase 5: Agent Sub-Issue Auto-Creation (Planned)

**Timeline:** Day 4-5  
**Effort:** 4 hours

#### Architecture:

```
Orchestrator → Event Bus → Agent Queue → Agent Creates Linear Sub-Issue
```

#### Changes Per Agent:

**New Endpoint:**

```python
@app.post("/tasks/accept")
async def accept_task(task: TaskAssignment):
    # 1. Create Linear sub-issue from template
    # 2. Link to parent via parentId
    # 3. Store task_id → linear_issue_id mapping
    # 4. Update issue status as task progresses
    # 5. Post result comment on completion
```

**State Management:**

- Store mapping in PostgreSQL: `task_linear_mappings` table
- Schema: `(task_id, linear_issue_id, agent_name, created_at, updated_at, status)`

**Files Modified:**

- `agent_*/main.py` (6 agents)
- `shared/services/state/schema.sql` (new table)
- `shared/lib/linear_workspace_client.py` (template-based creation)

---

### 🔔 Phase 6: Webhook Handler (Planned)

**Timeline:** Day 5-6  
**Effort:** 3 hours

#### Webhook Configuration (Already in `.env`):

```bash
LINEAR_WEBHOOK_URI=https://theshop.appsmithery.co/webhook
LINEAR_WEBHOOK_SIGNING_SECRET=7e17cf4ac3fbabd348663521bd089461b24f322eee3dadf353d60867262bd37c
```

#### Implementation:

**Gateway MCP Enhancement:**

```python
# shared/gateway/main.py

@app.post("/webhook/linear")
async def linear_webhook(
    request: Request,
    x_linear_signature: str = Header(None)
):
    # 1. Verify HMAC signature
    # 2. Parse webhook payload
    # 3. Filter for approval hub (PR-68) updates
    # 4. Extract approval decision from status change
    # 5. Emit event to orchestrator via event bus
    # 6. Return 200 OK
```

**Orchestrator Event Handler:**

```python
# agent_orchestrator/main.py

async def handle_approval_decision(event: Dict[str, Any]):
    # 1. Extract task_id from Linear issue description
    # 2. Check decision: approved/rejected
    # 3. Resume or cancel task execution
    # 4. Update task state in PostgreSQL
    # 5. Notify user via VS Code extension
```

**Webhook Events to Handle:**

- `Issue.update` - Status changes (todo → approved/rejected)
- `Comment.create` - Approval comments with specific format
- `Issue.close` - Manual closure = rejection

**Files Modified:**

- `shared/gateway/main.py` (webhook endpoint)
- `agent_orchestrator/main.py` (event handler)
- `shared/lib/event_bus.py` (new event types)

---

## Configuration Summary

### VS Code Settings (`.vscode/settings.json`)

```json
{
  "linear.apiKey": "${LINEAR_API_KEY}",
  "linear.workspaceId": "5029c640-3f73-480c-82f3-58e402ed4207",
  "linear.teamId": "f5b610be-ac34-4983-918b-2c9d00aa9b7a",
  "linear.defaultProject": "AI DevOps Agent Platform"
}
```

### Environment Variables (Already in `.env`)

```bash
# Linear OAuth App
LINEAR_OAUTH_CLIENT_ID=22a84e6bd5a10c0207d255773ce91ec6
LINEAR_OAUTH_CLIENT_SECRET=b7bc7b0c6f39b36e7455c1e6a0e5f31c
LINEAR_API_KEY=lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571

# Webhook
LINEAR_WEBHOOK_URI=https://theshop.appsmithery.co/webhook
LINEAR_WEBHOOK_SIGNING_SECRET=7e17cf4ac3fbabd348663521bd089461b24f322eee3dadf353d60867262bd37c

# Workspace
LINEAR_TEAM_ID=f5b610be-ac34-4983-918b-2c9d00aa9b7a
LINEAR_APPROVAL_HUB_ISSUE_ID=PR-68
```

---

## Testing Strategy

### Phase 1 (Extension):

- [ ] Install extension successfully
- [ ] Authenticate with Linear OAuth
- [ ] Create test issue from VS Code
- [ ] View issues in Linear sidebar

### Phase 2 (Templates):

- [ ] Create HITL approval from template
- [ ] Create agent sub-issue from template
- [ ] Verify default properties auto-fill
- [ ] Test template variables

### Phase 3 (Permalinks):

- [ ] Generate permalink for single line
- [ ] Generate permalink for line range
- [ ] Generate permalink with commit SHA
- [ ] Click permalink from Linear → jumps to GitHub

### Phase 4 (Documents):

- [ ] Create issue with attached document
- [ ] View document in Linear issue
- [ ] Update document content
- [ ] Test markdown rendering

### Phase 5 (Auto-Creation):

- [ ] Orchestrator decomposes task
- [ ] Agent receives task via event bus
- [ ] Agent creates Linear sub-issue
- [ ] Sub-issue linked to parent
- [ ] Agent updates status as work progresses
- [ ] Agent posts completion comment

### Phase 6 (Webhooks):

- [ ] Linear sends webhook on issue update
- [ ] Gateway receives and verifies signature
- [ ] Event published to orchestrator
- [ ] Orchestrator resumes/cancels task
- [ ] User notified of approval decision

---

## Success Metrics

### Developer Experience:

- **Issue Creation Time:** <30 seconds (from VS Code)
- **Context Switching:** 0 (no need to open Linear)
- **Template Usage:** 100% of HITL approvals use standard template

### Automation:

- **Manual Sub-Issue Creation:** 0% (agents auto-create)
- **Approval Notification Latency:** <5 seconds (webhook-driven)
- **State Sync Errors:** <1% (webhook reliability)

### Observability:

- **HITL Approval Requests:** Tracked in Linear with consistent format
- **Agent Task Status:** Visible in Linear sub-issues
- **GitHub Code References:** Included in 90%+ of approvals

---

## Rollback Plan

### Phase 1-4 (No Breaking Changes):

- Simply don't use new features
- Existing workflows unchanged

### Phase 5 (Agent Auto-Creation):

- **Rollback:** Disable agent `/tasks/accept` endpoint
- **Fallback:** Manual sub-issue creation by orchestrator

### Phase 6 (Webhooks):

- **Rollback:** Disable webhook in Linear app settings
- **Fallback:** Polling-based approval checking (existing)

---

## Dependencies

### External:

- Linear GraphQL API (https://api.linear.app/graphql)
- Linear Connect VS Code Extension (linear.linear-connect)
- GitHub API (for permalink validation)

### Internal:

- Event Bus (shared/lib/event_bus.py)
- State Service (shared/services/state/)
- MCP Gateway (shared/gateway/)
- PostgreSQL (task state, mappings)

---

## Documentation Updates

### User-Facing:

- [ ] Update README with Linear integration features
- [ ] Create HITL workflow guide
- [ ] Add VS Code extension setup instructions
- [ ] Document issue template usage

### Developer-Facing:

- [ ] Update `linear_workspace_client.py` docstrings
- [ ] Document webhook payload structure
- [ ] Add agent sub-issue creation examples
- [ ] Update architecture diagrams

---

## Timeline Summary

| Phase                  | Timeline | Effort | Status         |
| ---------------------- | -------- | ------ | -------------- |
| 0. Prerequisites       | Complete | -      | ✅ Done        |
| 1. VS Code Extension   | Day 1    | 30m    | 🔄 In Progress |
| 2. Issue Templates     | Day 1-2  | 2h     | 📋 Planned     |
| 3. GitHub Permalinks   | Day 2-3  | 2h     | 📋 Planned     |
| 4. Issue Documents     | Day 3    | 1h     | 📋 Planned     |
| 5. Agent Auto-Creation | Day 4-5  | 4h     | 📋 Planned     |
| 6. Webhook Handler     | Day 5-6  | 3h     | 📋 Planned     |

**Total Effort:** ~12.5 hours  
**Target Completion:** November 27, 2025
