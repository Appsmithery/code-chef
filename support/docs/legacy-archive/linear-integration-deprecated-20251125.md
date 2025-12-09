# Linear Integration Guide

**Complete guide for Linear workspace integration, HITL approvals, and project management.**

See [QUICKSTART.md](../QUICKSTART.md) | [ARCHITECTURE.md](../ARCHITECTURE.md)

---

## Overview

Linear integration provides:

- **Issue Management**: Auto-create Linear issues from agent workflows
- **HITL Approvals**: High-risk operations require human approval in Linear  
- **Progress Tracking**: Real-time status updates in Linear project board
- **Workspace Awareness**: Each Git repository maps to a Linear project

---

## Setup

### 1. Create Linear OAuth Token

1. Visit https://linear.app/settings/api
2. Create Personal API Key or OAuth application
3. Copy token (starts with `lin_oauth_`)

### 2. Configure Environment

Edit `config/env/.env`:

```bash
# Linear Team ID (from URL: linear.app/team/<key>/...)
LINEAR_TEAM_ID=f5b610be-ac34-4983-918b-2c9d00aa9b7a

# OAuth Token  
LINEAR_API_KEY=lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571

# Approval Hub (workspace-level issue for HITL notifications)
LINEAR_APPROVAL_HUB_ISSUE_ID=DEV-68

# Webhook Secret (for Linear  Dev-Tools webhooks)
LINEAR_WEBHOOK_SIGNING_SECRET=<generate-random-secret>
```

### 3. Create Linear Project

```python
from shared.lib.linear_workspace_client import LinearWorkspaceClient

client = LinearWorkspaceClient()

# Create project for repository
project = await client.create_project(
    team_id="f5b610be-ac34-4983-918b-2c9d00aa9b7a",
    name="Dev-Tools Platform",
    description="AI agent orchestration platform"
)

print(f"Project ID: {project['id']}")
```

### 4. Configure Templates

Linear templates define custom fields for HITL approvals:

```bash
# In config/env/.env
HITL_ORCHESTRATOR_TEMPLATE_UUID=aa632a46-ea22-4dd0-9403-90b0d1f05aa0
TASK_ORCHESTRATOR_TEMPLATE_UUID=<task-template-uuid>
```

**Template Custom Fields:**

- **Request Status** (dropdown): Approved, Denied, More information required
- **Required Action** (checkboxes): Review changes, Verify risks, Check implementation

---

## Usage

### Create Issues from Agent Workflows

```python
from shared.lib.linear_workspace_client import LinearWorkspaceClient

client = LinearWorkspaceClient()

# Create feature issue
issue = await client.create_issue(
    title="Implement authentication module",
    description="Add JWT-based authentication with refresh tokens",
    project_id="b21cbaa1-9f09-40f4-b62a-73e0f86dd501",
    state="todo",
    priority=2  # High
)
```

### HITL Approval Workflow

**Automatic for high-risk operations:**

```
1. Agent detects high-risk operation (prod deploy, secret change)
2. Orchestrator creates approval request in PostgreSQL
3. LangGraph workflow interrupts at approval_gate node
4. Linear sub-issue created in DEV-68 with approval form
5. User reviews in Linear, sets Request Status = Approved
6. Webhook updates PostgreSQL
7. Workflow resumes from checkpoint
```

**Trigger manually:**

```python
from shared.lib.hitl_manager import get_hitl_manager
from shared.lib.risk_assessor import get_risk_assessor

risk_assessor = get_risk_assessor()
hitl_manager = get_hitl_manager()

# Assess risk
risk_level = risk_assessor.assess_task({
    "operation": "deploy",
    "environment": "production",
    "impact": "high"
})

# Create approval request if needed
if risk_assessor.requires_approval(risk_level):
    approval_id = await hitl_manager.create_approval_request(
        workflow_id="task-123",
        thread_id="thread-123",
        checkpoint_id="checkpoint-123",
        task={"operation": "deploy"},
        agent_name="orchestrator"
    )
```

### Update Issue Status

```python
# Mark issue complete
await client.update_issue(
    issue_id="PR-85",
    state="done",
    description_append="\n\n## Completion Notes\n- All tests passing\n- Deployed to production"
)
```

### Query Issues

```python
# Get project issues
issues = await client.get_project_issues(
    project_id="b21cbaa1-9f09-40f4-b62a-73e0f86dd501",
    state="in_progress"
)

for issue in issues:
    print(f"{issue['identifier']}: {issue['title']}")
```

---

## Configuration

### Linear Config (`config/linear/linear-config.yaml`)

```yaml
team:
  id: f5b610be-ac34-4983-918b-2c9d00aa9b7a
  key: PR

projects:
  ai_devops_platform:
    id: b21cbaa1-9f09-40f4-b62a-73e0f86dd501
    slug: 78b3b839d36b

templates:
  hitl_approval:
    id: aa632a46-ea22-4dd0-9403-90b0d1f05aa0
    custom_fields:
      request_status:
        id: <field-uuid>
        type: dropdown
        options:
          - Approved
          - Denied
          - More information required
      required_action:
        id: <field-uuid>
        type: checkboxes
        options:
          - Review changes
          - Verify risks
          - Check implementation

approval_hub:
  issue_id: DEV-68
  issue_uuid: <uuid>
```

### Risk Assessment Rules (`config/hitl/risk-assessment-rules.yaml`)

```yaml
risk_levels:
  critical:
    operations:
      - delete_production_data
      - rotate_secrets
      - modify_iam_policies
    requires_approval: true
    required_role: devops_engineer

  high:
    operations:
      - deploy_production
      - modify_infrastructure
      - database_migration
    requires_approval: true
    required_role: tech_lead

  medium:
    operations:
      - deploy_staging
      - update_dependencies
      - modify_ci_pipeline
    requires_approval: true
    required_role: developer

  low:
    operations:
      - read_logs
      - query_metrics
      - update_documentation
    requires_approval: false
```

---

## Webhooks

### Configure Linear Webhook

1. Linear Settings  API  Webhooks
2. Create webhook with URL: `https://your-domain.com/webhooks/linear`
3. Copy signing secret to `.env` as `LINEAR_WEBHOOK_SIGNING_SECRET`
4. Enable events: Issue updated, Comment created

### Webhook Handler (`shared/gateway/webhooks/linear.ts`)

```typescript
app.post('/webhooks/linear', async (req, res) => {
  // Verify signature
  const signature = req.headers['linear-signature'];
  const isValid = verifyLinearWebhook(req.body, signature);
  
  if (!isValid) {
    return res.status(401).json({ error: 'Invalid signature' });
  }

  // Process issue update
  if (req.body.action === 'update' && req.body.data.state) {
    const issueId = req.body.data.id;
    const requestStatus = req.body.data.customFields.request_status;
    
    if (requestStatus === 'Approved') {
      // Update PostgreSQL approval_requests table
      await approveRequest(issueId);
      
      // Emit resume event via event bus
      await eventBus.emit('approval:approved', { issueId });
    }
  }

  res.json({ received: true });
});
```

---

## Troubleshooting

### "Linear API key invalid"

```bash
# Verify token
curl https://api.linear.app/graphql \
  -H "Authorization: Bearer lin_oauth_***" \
  -d '{"query": "{ viewer { id name email } }"}'

# Should return user data, not 401
```

### "Template not found"

```bash
# List available templates
curl https://api.linear.app/graphql \
  -H "Authorization: Bearer lin_oauth_***" \
  -d '{"query": "{ issueTemplates { nodes { id name } } }"}'

# Update HITL_ORCHESTRATOR_TEMPLATE_UUID in .env
```

### "Approval webhook not triggering"

```bash
# Check webhook delivery in Linear Settings  API  Webhooks
# View failed deliveries and error messages

# Verify signature validation in logs
docker compose logs gateway-mcp | grep "linear-webhook"
```

---

## Related Documentation

- **[LINEAR_HITL_WORKFLOW.md](../LINEAR_HITL_WORKFLOW.md)** - Complete HITL approval flow
- **[ARCHITECTURE.md](../ARCHITECTURE.md)** - System architecture with HITL integration
- **[operations/SECRETS_MANAGEMENT.md](../operations/SECRETS_MANAGEMENT.md)** - Managing Linear tokens
