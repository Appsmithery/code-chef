# Linear Integration Guide

**Version:** v0.3.1  
**Status:** ✅ Production Ready  
**Last Updated:** November 25, 2025

**Recent Updates:**

- ✅ GitHub permalink configuration added to `linear-config.yaml`
- ✅ Documentation consolidated (archived duplicate `guides/LINEAR_INTEGRATION.md`)
- ✅ DEV-180 tracking permalink integration status

---

## Quick Reference

### Configuration Files

- **Structural Config**: `config/linear/linear-config.yaml` (version controlled)
- **Secrets**: `config/env/.env` (gitignored)
- **Config Loader**: `shared/lib/linear_config.py`
- **Client**: `shared/lib/linear_workspace_client.py`

### Key Environment Variables

```bash
# Authentication
LINEAR_API_KEY=lin_oauth_***
LINEAR_OAUTH_CLIENT_ID=22a84e6bd5a10c0207d255773ce91ec6
LINEAR_OAUTH_CLIENT_SECRET=b7bc7b0c6f39b36e7455c1e6a0e5f31c

# Workspace
LINEAR_TEAM_ID=f5b610be-ac34-4983-918b-2c9d00aa9b7a
LINEAR_APPROVAL_HUB_ISSUE_ID=DEV-68

# Templates
HITL_ORCHESTRATOR_TEMPLATE_UUID=aa632a46-ea22-4dd0-9403-90b0d1f05aa0
LINEAR_ORCHESTRATOR_TEMPLATE_ID=<project_task_template_uuid>

# Webhooks
LINEAR_WEBHOOK_URI=https://theshop.appsmithery.co/webhook
LINEAR_WEBHOOK_SIGNING_SECRET=<webhook_secret>
```

### Quick Setup

```bash
# 1. Copy template
cp config/env/.env.template config/env/.env

# 2. Add Linear secrets (see above)

# 3. Validate configuration
npm run secrets:validate:discover

# 4. Deploy
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config
```

---

## Architecture Overview

### Multi-Layer Configuration (v0.3)

**Layer 1: Structural Config (YAML)**

- File: `config/linear/linear-config.yaml`
- Contains: Workspace settings, template UUIDs, custom field IDs, label IDs, assignee IDs
- Version controlled, self-documenting

**Layer 2: Secrets (.env)**

- File: `config/env/.env`
- Contains: API keys, OAuth tokens, webhook secrets
- Gitignored, environment-specific

**Layer 3: Config Loader**

- File: `shared/lib/linear_config.py`
- Provides: Type-safe access, Pydantic validation, YAML + .env merging
- Singleton pattern for performance

**Layer 4: Client Integration**

- File: `shared/lib/linear_workspace_client.py`
- Uses config loader for all Linear operations
- Template fallback, policy-based approvals

### Benefits

- ✅ 50% reduction in `.env` size
- ✅ Version-controlled structural config
- ✅ Type-safe access with IDE autocomplete
- ✅ Multi-environment ready
- ✅ Self-documenting configuration

---

## Configuration Setup

### Step 1: Extract Custom Field IDs

Linear custom fields must be extracted manually from browser DevTools or API:

**Method A: Browser DevTools**

1. Open test issue in Linear
2. Open DevTools (F12) → Network tab
3. Filter by "graphql"
4. Modify a custom field value
5. Inspect GraphQL request/response for field IDs

**Method B: API Script**

```bash
export LINEAR_API_KEY="lin_oauth_***"
export LINEAR_TEAM_ID="f5b610be-ac34-4983-918b-2c9d00aa9b7a"
python support/scripts/linear/get-custom-fields.py
```

**Expected Output:**

```
Field: Request Status
  ID: <field_uuid>
  Type: dropdown
  Options:
    - Approved (id: <option_uuid>)
    - Denied (id: <option_uuid>)
    - More information required (id: <option_uuid>)

Field: Required Action
  ID: <field_uuid>
  Type: checkboxes
  Options:
    - Review proposed changes (id: <option_uuid>)
    - Verify risks are acceptable (id: <option_uuid>)
    - Check implementation approach (id: <option_uuid>)
    - Request modifications (id: <option_uuid>)
```

### Step 2: Update YAML Configuration

Edit `config/linear/linear-config.yaml`:

```yaml
workspace:
  slug: "dev-ops"
  team_id: "f5b610be-ac34-4983-918b-2c9d00aa9b7a"
  approval_hub_issue_id: "DEV-68"

templates:
  hitl:
    orchestrator: "aa632a46-ea22-4dd0-9403-90b0d1f05aa0"
  tasks:
    orchestrator: "<task_template_uuid>"
    feature_dev: "<task_template_uuid>"
    code_review: "<task_template_uuid>"
    infrastructure: "<task_template_uuid>"
    cicd: "<task_template_uuid>"
    documentation: "<task_template_uuid>"

custom_fields:
  request_status:
    id: "<field_uuid>"
    options:
      approved: "<option_uuid>"
      denied: "<option_uuid>"
      more_info: "<option_uuid>"
  required_action:
    id: "<field_uuid>"
    options:
      review_changes: "<option_uuid>"
      verify_risks: "<option_uuid>"
      check_implementation: "<option_uuid>"
      request_modifications: "<option_uuid>"
```

### Step 3: Configure Environment Secrets

Edit `config/env/.env`:

```bash
# Linear Authentication
LINEAR_API_KEY=lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571
LINEAR_OAUTH_CLIENT_ID=22a84e6bd5a10c0207d255773ce91ec6
LINEAR_OAUTH_CLIENT_SECRET=b7bc7b0c6f39b36e7455c1e6a0e5f31c
LINEAR_OAUTH_DEV_TOKEN=lin_oauth_***

# Webhook Configuration
LINEAR_WEBHOOK_URI=https://theshop.appsmithery.co/webhook
LINEAR_WEBHOOK_SIGNING_SECRET=7e17cf4ac3fbabd348663521bd089461b24f322eee3dadf353d60867262bd37c

# Template Overrides (optional - defaults to orchestrator templates)
HITL_ORCHESTRATOR_TEMPLATE_UUID=aa632a46-ea22-4dd0-9403-90b0d1f05aa0
LINEAR_ORCHESTRATOR_TEMPLATE_ID=<task_template_uuid>
```

### Step 4: Setup Webhook

1. Go to Linear Settings → API → Webhooks
2. Click "Create webhook"
3. Configure:
   - **URL**: `https://theshop.appsmithery.co/webhooks/linear`
   - **Events**: `Issue updated`, `Comment created`
   - **Secret**: Use value from `LINEAR_WEBHOOK_SIGNING_SECRET`
4. Save webhook

### Step 5: Validate Configuration

```bash
# Test config loading
python support/scripts/linear/test-linear-config.py

# Expected output:
# ✅ Config Loading - YAML parsing successful
# ✅ Structural Config - All YAML values loaded
# ✅ Secrets Loading - .env values merged
# ✅ Config Methods - Helper methods working
# ✅ Environment Overrides - Agent-specific overrides working
```

### Step 6: Configure GitHub Permalinks (Optional - v0.3.1)

Add GitHub repository configuration to `config/linear/linear-config.yaml`:

```yaml
github:
  repository:
    owner: "Appsmithery"
    name: "Dev-Tools"
    url: "https://github.com/Appsmithery/Dev-Tools"

  permalink_generation:
    enabled: true # Generate permalinks for code references in Linear issues
    default_branch: "main"
    include_commit_sha: true # Use commit SHA for stable references

  auto_permalink_agents:
    - "feature-dev"
    - "code-review"
    - "infrastructure"
    - "cicd"
```

**Status:** Implementation complete (DEV-180), integration with issue creation pending.

**Available Now:**

```python
from shared.lib.github_permalink_generator import init_permalink_generator, generate_permalink

# Initialize at startup
init_permalink_generator("https://github.com/Appsmithery/Dev-Tools")

# Generate permalink
url = generate_permalink("agent_orchestrator/main.py", line_start=45, line_end=67)
# Result: https://github.com/Appsmithery/Dev-Tools/blob/abc123/agent_orchestrator/main.py#L45-L67
```

### Step 7: Deploy

```powershell
# Deploy configuration
.\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config

# Verify deployment
ssh do-codechef-droplet "curl -s http://localhost:8001/health | jq"
```

---

## Usage Patterns

### Basic Configuration Access

```python
from shared.lib.linear_config import get_linear_config

config = get_linear_config()
api_key = config.api_key
team_id = config.workspace.team_id
approval_hub_id = config.workspace.approval_hub_issue_id
```

### Template Selection with Fallback

```python
# Get template UUID (falls back to orchestrator if agent-specific not found)
template_uuid = config.get_template_uuid("feature-dev", scope="workspace")

# Create issue from template
issue = await linear_client.create_issue_from_template(
    template_id=template_uuid,
    title="New Feature Task",
    team_id=config.workspace.team_id
)
```

### Custom Field Operations

```python
# Get custom field IDs
request_status_id = config.get_custom_field_id("request_status")
required_action_id = config.get_custom_field_id("required_action")

# Get option UUIDs
approved_option = config.get_custom_field_option("request_status", "approved")
denied_option = config.get_custom_field_option("request_status", "denied")

# Create issue with custom fields
issue = await linear_client.create_issue(
    title="HITL Approval Request",
    description="Task requires approval",
    team_id=config.workspace.team_id,
    custom_fields={
        request_status_id: approved_option,  # Pre-select "Approved"
        required_action_id: [
            config.get_custom_field_option("required_action", "review_changes"),
            config.get_custom_field_option("required_action", "verify_risks")
        ]
    }
)
```

### Risk-Based Approval Policies

```python
# Get approval policy for risk level
policy = config.get_approval_policy("high")

priority = policy.priority  # 1 (Urgent)
required_actions = policy.required_actions
# ["Review proposed changes", "Verify risks are acceptable", "Check implementation approach"]

# Apply policy to issue
await linear_client.update_issue(
    issue_id=issue_id,
    priority=priority,
    custom_fields={
        required_action_id: [
            config.get_custom_field_option("required_action", action)
            for action in policy.required_action_keys
        ]
    }
)
```

---

## State Management

### PostgreSQL Schema

```sql
CREATE TABLE task_linear_mappings (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) NOT NULL UNIQUE,
    linear_issue_id VARCHAR(255) NOT NULL,
    linear_identifier VARCHAR(50) NOT NULL,  -- e.g., "PR-123"
    agent_name VARCHAR(50) NOT NULL,
    parent_issue_id VARCHAR(255),
    parent_identifier VARCHAR(50),
    status VARCHAR(50) DEFAULT 'todo',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

### State Client Usage

```python
from shared.lib.state_client import get_state_client

state_client = get_state_client()

# Store mapping
await state_client.store_task_mapping(
    task_id="abc123-def456",
    linear_issue_id="550e8400-e29b-41d4-a716-446655440000",
    linear_identifier="PR-123",
    agent_name="feature-dev",
    parent_issue_id="parent-uuid",
    parent_identifier="DEV-68",
    status="todo"
)

# Get mapping
mapping = await state_client.get_task_mapping("abc123-def456")

# Update status
await state_client.update_task_status("abc123-def456", "in_progress")
await state_client.update_task_status("abc123-def456", "done", mark_completed=True)

# Query operations
tasks = await state_client.get_agent_tasks("feature-dev")
stats = await state_client.get_completion_stats("feature-dev")
```

---

## Agent Integration Pattern

All agents should follow this pattern:

```python
from shared.lib.linear_workspace_client import get_linear_workspace_client
from shared.lib.linear_config import get_linear_config
from shared.lib.state_client import get_state_client

linear_client = get_linear_workspace_client()
config = get_linear_config()
state_client = get_state_client()

@app.post("/tasks/accept")
async def accept_task(task: TaskAssignment):
    # 1. Get template UUID with fallback
    template_uuid = config.get_template_uuid("feature-dev", scope="project")

    # 2. Create Linear sub-issue from template
    linear_issue = await linear_client.create_issue_from_template(
        template_id=template_uuid,
        title=task.title,
        description=task.description,
        parent_id=task.parent_issue_id
    )

    # 3. Store mapping in state service
    await state_client.store_task_mapping(
        task_id=task.task_id,
        linear_issue_id=linear_issue["id"],
        linear_identifier=linear_issue["identifier"],
        agent_name="feature-dev",
        parent_issue_id=task.parent_issue_id,
        parent_identifier=task.parent_identifier,
        status="todo"
    )

    # 4. Execute task with status updates
    await linear_client.update_issue_status(linear_issue["id"], "in_progress")
    await state_client.update_task_status(task.task_id, "in_progress")

    # ... perform work ...

    # 5. Mark complete
    await linear_client.update_issue_status(linear_issue["id"], "done")
    await state_client.update_task_status(task.task_id, "done", mark_completed=True)

    # 6. Add completion comment
    await linear_client.add_comment(
        linear_issue["id"],
        f"Task completed ✅\n\nDuration: {duration}s"
    )

    return TaskResult(status="completed", linear_issue_id=linear_issue["id"])
```

---

## Monitoring & Observability

### Health Checks

```bash
# Check webhook endpoint
curl https://codechef.appsmithery.co/webhooks/linear/health

# Check orchestrator
curl https://codechef.appsmithery.co/api/health
```

### Dashboard Queries

```sql
-- Active tasks by agent
SELECT agent_name, COUNT(*) as active_tasks
FROM task_linear_mappings
WHERE status = 'in_progress'
GROUP BY agent_name;

-- Completion rate by agent
SELECT
    agent_name,
    COUNT(*) as total,
    SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) as completed,
    ROUND(100.0 * SUM(CASE WHEN status = 'done' THEN 1 ELSE 0 END) / COUNT(*), 2) as rate
FROM task_linear_mappings
GROUP BY agent_name;

-- Average completion time
SELECT
    agent_name,
    ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - created_at)) / 60), 2) as avg_minutes
FROM task_linear_mappings
WHERE status = 'done' AND completed_at IS NOT NULL
GROUP BY agent_name;
```

### LangSmith Traces

Webhook handlers traced in project `webhooks-linear`:  
https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects

---

## Troubleshooting

### Custom Fields Not Showing

**Problem:** Created issues don't have custom fields populated

**Solution:**

1. Verify field IDs in `linear-config.yaml` match your workspace
2. Run extraction script: `python support/scripts/linear/get-custom-fields.py`
3. Check field is enabled for team in Linear settings

### Webhook Not Triggering

**Problem:** Approval status changes don't trigger workflow resume

**Solution:**

1. Verify `LINEAR_WEBHOOK_SIGNING_SECRET` in `.env`
2. Check webhook logs in Linear Settings → API → Webhooks
3. Test webhook with Linear's test feature
4. Check orchestrator logs: `docker logs deploy-orchestrator-1 | grep -i webhook`

### Template Not Found

**Problem:** `Template UUID not found` error when creating issues

**Solution:**

1. Verify template UUID in `linear-config.yaml`
2. Check template exists in Linear Settings → Templates
3. Confirm template scope matches (workspace vs project)
4. Use fallback: `config.get_template_uuid("agent", scope="workspace")`

### State Mapping Missing

**Problem:** Task mapping not found in PostgreSQL

**Solution:**

```python
# Verify mapping creation
mapping = await state_client.get_task_mapping("task-id")
if not mapping:
    logger.error(f"No mapping found for task {task_id}")
    # Check store_task_mapping was called
    # Verify PostgreSQL connection
```

---

## Migration from Legacy Config

### Before (Legacy .env-only)

```bash
# 50+ environment variables
LINEAR_TEAM_ID=...
LINEAR_APPROVAL_HUB_ISSUE_ID=...
LINEAR_FIELD_REQUEST_STATUS_ID=...
LINEAR_REQUEST_STATUS_APPROVED=...
LINEAR_REQUEST_STATUS_DENIED=...
# ... 45+ more variables
```

### After (Multi-layer v0.3)

**YAML Config (version controlled):**

```yaml
workspace:
  team_id: "..."
  approval_hub_issue_id: "DEV-68"
custom_fields:
  request_status:
    id: "..."
    options:
      approved: "..."
```

**.env (secrets only):**

```bash
LINEAR_API_KEY=lin_oauth_***
LINEAR_WEBHOOK_SIGNING_SECRET=***
```

**Benefits:**

- ✅ 50% smaller `.env` file
- ✅ Structural config in version control
- ✅ Type-safe access
- ✅ Self-documenting

---

## VS Code Extension Setup

### Install Linear Connect

1. Install extension: `linear.linear-connect`
2. Open Command Palette (Ctrl+Shift+P)
3. Run: "Linear: Authenticate"
4. Use OAuth token from `.env`

### Workspace Settings

Create `.vscode/settings.json`:

```json
{
  "linear.apiKey": "${LINEAR_API_KEY}",
  "linear.teamId": "f5b610be-ac34-4983-918b-2c9d00aa9b7a",
  "linear.defaultProject": "AI DevOps Agent Platform"
}
```

### Usage

- Create issues from VS Code
- View issues in sidebar
- Link commits to issues
- Update issue status

---

## Related Documentation

- **HITL Workflow**: `support/docs/LINEAR_HITL_WORKFLOW.md`
- **Deployment Guide**: `support/docs/DEPLOYMENT.md`
- **Secrets Management**: `support/docs/operations/SECRETS_MANAGEMENT.md`
- **GitHub Permalink Generator**: `shared/lib/github_permalink_generator.py`
- **Config Loader**: `shared/lib/linear_config.py`
- **Linear Client**: `shared/lib/linear_workspace_client.py`
- **State Client**: `shared/lib/state_client.py`

---

**Document Version:** 1.1.0  
**Architecture:** LangGraph v0.3  
**Configuration:** Multi-layer (YAML + .env)  
**Last Updated:** November 25, 2025  
**Changes:** Added GitHub permalink configuration, consolidated documentation
