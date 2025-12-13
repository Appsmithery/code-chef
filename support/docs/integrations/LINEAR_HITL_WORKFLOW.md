# Linear HITL Approval Workflow

**Version:** v0.3  
**Status:** ✅ Production Ready  
**Last Updated:** November 22, 2025

---

## Quick Reference

### Risk Levels

| Risk Level   | Auto-Approve | Approver Role             | Timeout | Examples                     |
| ------------ | ------------ | ------------------------- | ------- | ---------------------------- |
| **Low**      | ✅ Yes       | N/A                       | N/A     | Dev reads, config queries    |
| **Medium**   | ❌ No        | developer/tech_lead       | 30 min  | Staging deploys, data import |
| **High**     | ❌ No        | tech_lead/devops_engineer | 60 min  | Production deploys, infra    |
| **Critical** | ❌ No        | devops_engineer           | 120 min | Production deletes, secrets  |

### Custom Fields

**Request Status** (Dropdown - User Input):

- Approved
- Denied
- More information required

**Required Action** (Checkboxes - Pre-filled by Orchestrator):

- Review proposed changes
- Verify risks are acceptable
- Check implementation approach
- Request modifications

### Taskfile Commands

```bash
task workflow:init-db              # Initialize approval_requests table
task workflow:list-pending         # List pending approvals
task workflow:approve REQUEST_ID=<uuid>   # Approve request
task workflow:reject REQUEST_ID=<uuid> REASON="..."  # Reject request
task workflow:status WORKFLOW_ID=<id>     # Show workflow status
task workflow:clean-expired        # Clean up expired requests
```

---

## Architecture Overview

### HITL Approval Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Orchestrator │────▶│ Risk         │────▶│ HITL         │
│              │     │ Assessor     │     │ Manager      │
└──────────────┘     └──────────────┘     └──────────────┘
                            │                      │
                            │                      │
                     ┌──────▼──────┐       ┌───────▼──────┐
                     │ Risk Level  │       │ Approval     │
                     │ (L/M/H/C)   │       │ Request      │
                     └─────────────┘       │ (PostgreSQL) │
                                           └───────┬──────┘
                                                   │
                     ┌─────────────────────────────▼─────────────────────────┐
                     │                LangGraph Workflow                      │
                     │  ┌──────────┐    ┌──────────┐    ┌──────────────┐    │
                     │  │ approval │───▶│ User     │───▶│ conditional  │    │
                     │  │ _gate    │    │ Decision │    │ _router      │    │
                     │  └──────────┘    │ (Linear) │    └──────────────┘    │
                     │                  └──────────┘                         │
                     └──────────────────────────────────────────────────────┘
                                                   │
                     ┌─────────────────────────────┴─────────────────────────┐
                     │                                                        │
              ┌──────▼──────┐                                      ┌─────────▼────────┐
              │ Execute     │                                      │ Handle           │
              │ Operation   │                                      │ Rejection        │
              └─────────────┘                                      └──────────────────┘
```

### Core Components

**Risk Assessor** (`shared/lib/risk_assessor.py`):

- Evaluates task risk based on operation type, environment, impact
- Configuration: `config/hitl/risk-assessment-rules.yaml`
- Returns: `low` | `medium` | `high` | `critical`

**HITL Manager** (`shared/lib/hitl_manager.py`):

- Creates approval requests in PostgreSQL
- Manages lifecycle (pending → approved/denied → completed)
- Enforces role-based policies from `config/hitl/approval-policies.yaml`

**LangGraph Interrupt Nodes** (`shared/services/langgraph/src/interrupt_nodes.py`):

- `approval_gate` - Interrupts workflow if approval required
- `conditional_approval_router` - Routes based on approval status

**Linear Workspace Client** (`shared/lib/linear_workspace_client.py`):

- Creates sub-issues in DEV-68 (approval hub)
- Pre-fills custom fields based on risk level
- Posts approval forms with Request Status dropdown

---

## Workflow Pattern

### Step-by-Step Flow

1. **Task Submission**

   ```python
   # User submits high-risk task
   POST /orchestrate
   {
     "description": "Deploy authentication service to production",
     "priority": "high"
   }
   ```

2. **Risk Assessment**

   ```python
   from shared.lib.risk_assessor import get_risk_assessor

   risk_assessor = get_risk_assessor()
   risk_level = risk_assessor.assess_task({
       "operation": "deploy",
       "environment": "production",
       "service": "authentication"
   })
   # Returns: "high"
   ```

3. **Approval Request Creation**

   ```python
   if risk_assessor.requires_approval(risk_level):
       from shared.lib.hitl_manager import get_hitl_manager

       hitl_manager = get_hitl_manager()
       approval_request_id = await hitl_manager.create_approval_request(
           workflow_id=task_id,
           thread_id=f"thread-{task_id}",
           checkpoint_id=f"checkpoint-{task_id}",
           task=task_dict,
           agent_name="orchestrator"
       )
   ```

4. **LangGraph Workflow Interrupt**

   ```python
   from shared.services.langgraph.src.interrupt_nodes import approval_gate

   workflow = StateGraph(WorkflowState)
   workflow.add_node("approval_gate", approval_gate)
   compiled = workflow.compile(
       checkpointer=checkpointer,
       interrupt_before=["approval_gate"]
   )

   # Workflow pauses at approval_gate node
   ```

5. **Linear Sub-Issue Creation**

   ```python
   # Orchestrator creates sub-issue in DEV-68
   linear_issue = await linear_client.create_issue(
       title=f"🟠 [HIGH] HITL Approval: {task_description}",
       description=f"**Task ID**: {task_id}\n**Risk Level**: High\n...",
       parent_id="DEV-68",
       team_id=config.workspace.team_id,
       template_id=config.get_template_uuid("orchestrator", scope="workspace"),
       custom_fields={
           required_action_id: [
               "review_changes",
               "verify_risks",
               "check_implementation"
           ]
       }
   )
   ```

6. **User Decision (Linear UI)**

   - User opens DEV-68, sees new sub-issue
   - Reviews task details, risks, proposed changes
   - Sets **Request Status**: Approved / Denied / More info
   - Checks additional **Required Actions** if needed
   - Adds comments with justification

7. **Webhook Processing**

   ```python
   # Linear webhook triggers on status change
   POST /webhooks/linear
   {
     "action": "update",
     "data": {
       "id": "issue-uuid",
       "customFields": {
         "request_status": "approved"
       }
     }
   }

   # Webhook handler updates PostgreSQL
   await hitl_manager.update_approval_status(
       approval_request_id,
       status="approved",
       approved_by="alex@appsmithery.co"
   )

   # Emit resume event
   await event_bus.emit("approval_decision", {
       "task_id": task_id,
       "status": "approved",
       "approval_request_id": approval_request_id
   })
   ```

8. **Workflow Resumption**

   ```python
   # LangGraph workflow resumes from checkpoint
   result = compiled.invoke(
       state,
       config={"configurable": {"thread_id": thread_id}}
   )

   # Conditional router checks approval status
   if state["approval_status"] == "approved":
       return "execute_operation"
   else:
       return "handle_rejection"
   ```

---

## Configuration

### Risk Assessment Rules

**File**: `config/hitl/risk-assessment-rules.yaml`

```yaml
risk_levels:
  critical:
    operations:
      - delete_production
      - modify_secrets
      - drop_database
    environments:
      - production
    auto_approve: false
    requires_justification: true

  high:
    operations:
      - deploy_production
      - modify_infrastructure
      - database_migration
    environments:
      - production
    auto_approve: false

  medium:
    operations:
      - deploy_staging
      - import_data
      - config_update
    environments:
      - staging
    auto_approve: false

  low:
    operations:
      - read_config
      - list_resources
      - dev_deploy
    environments:
      - development
    auto_approve: true
```

### Approval Policies

**File**: `config/hitl/approval-policies.yaml`

```yaml
policies:
  critical:
    approver_roles:
      - devops_engineer
    priority: 0 # No priority (requires manual review)
    timeout_minutes: 120
    required_actions:
      - review_proposed_changes
      - verify_risks_are_acceptable
      - check_implementation_approach
      - request_modifications

  high:
    approver_roles:
      - tech_lead
      - devops_engineer
    priority: 1 # Urgent
    timeout_minutes: 60
    required_actions:
      - review_proposed_changes
      - verify_risks_are_acceptable
      - check_implementation_approach

  medium:
    approver_roles:
      - developer
      - tech_lead
    priority: 2 # High
    timeout_minutes: 30
    required_actions:
      - review_proposed_changes
```

### Environment Variables

```bash
# Linear Approval Configuration
LINEAR_APPROVAL_HUB_ISSUE_ID=DEV-68
HITL_ORCHESTRATOR_TEMPLATE_UUID=aa632a46-ea22-4dd0-9403-90b0d1f05aa0

# Linear Custom Fields
LINEAR_FIELD_REQUEST_STATUS_ID=<field_uuid>
LINEAR_FIELD_REQUIRED_ACTION_ID=<field_uuid>
LINEAR_REQUEST_STATUS_APPROVED=<option_uuid>
LINEAR_REQUEST_STATUS_DENIED=<option_uuid>
LINEAR_REQUEST_STATUS_MORE_INFO=<option_uuid>

# Linear Webhook
LINEAR_WEBHOOK_SIGNING_SECRET=<webhook_secret>
```

---

## Database Schema

### Approval Requests Table

**File**: `config/state/approval_requests.sql`

```sql
CREATE TABLE approval_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id VARCHAR(255) NOT NULL,
    thread_id VARCHAR(255) NOT NULL,
    checkpoint_id VARCHAR(255) NOT NULL,
    task_description TEXT NOT NULL,
    risk_level VARCHAR(50) NOT NULL,
    agent_name VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by VARCHAR(255),
    rejection_reason TEXT,
    linear_issue_id VARCHAR(255),
    linear_issue_url TEXT,
    expires_at TIMESTAMP
);

CREATE INDEX idx_approval_requests_status ON approval_requests(status);
CREATE INDEX idx_approval_requests_workflow ON approval_requests(workflow_id);
```

### Initialize Schema

```bash
# SSH to droplet
ssh do-codechef-droplet

# Apply schema
cd /opt/Dev-Tools
task workflow:init-db

# Verify
task workflow:list-pending
```

---

## Template Setup

### HITL Approval Template

**Template ID**: `aa632a46-ea22-4dd0-9403-90b0d1f05aa0`  
**Scope**: Workspace-wide (all agents use same template)

**Structure**:

1. **Title Pattern**: `🟠 [${RISK_LEVEL}] HITL Approval: ${TASK_DESCRIPTION}`

2. **Description Template**:

   ```markdown
   ## Task Information

   **Task ID**: ${TASK_ID}
   **Risk Level**: ${RISK_LEVEL}
   **Agent**: ${AGENT_NAME}
   **Submitted**: ${TIMESTAMP}

   ## Proposed Changes

   ${PROPOSED_CHANGES}

   ## Risks & Considerations

   ${RISKS}

   ## Approval Decision

   Please review the task details and set the **Request Status** field:

   - **Approved**: Task will proceed immediately
   - **Denied**: Task will be canceled
   - **More information required**: Task will remain paused for clarification

   Check all applicable **Required Actions** below.
   ```

3. **Custom Fields**:

   - **Request Status**: Empty (user decides)
   - **Required Action**: Pre-checked based on risk level

4. **Default Properties**:
   - Parent: DEV-68
   - Priority: Based on risk level (Urgent for high/critical)
   - Assignee: alex@appsmithery.co
   - Labels: HITL, orchestrator

---

## Testing

### Test Low-Risk Task (Auto-Approve)

```bash
curl -X POST https://codechef.appsmithery.co/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Read configuration from dev environment",
    "priority": "low"
  }'

# Expected: Immediate orchestration, no approval request
```

### Test High-Risk Task (HITL Approval)

```bash
curl -X POST https://codechef.appsmithery.co/api/orchestrate \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Deploy authentication service to production",
    "priority": "high"
  }'

# Expected: approval_pending status, Linear sub-issue in DEV-68
```

### Approve Request

**Method 1: Linear UI**

1. Open DEV-68 in Linear
2. Find new sub-issue
3. Set Request Status → Approved
4. Webhook triggers workflow resume

**Method 2: Taskfile Command**

```bash
task workflow:list-pending
# Copy REQUEST_ID from output

task workflow:approve REQUEST_ID=<uuid>
```

### Reject Request

**Method 1: Linear UI**

1. Open sub-issue
2. Set Request Status → Denied
3. Add comment with reason

**Method 2: Taskfile Command**

```bash
task workflow:reject REQUEST_ID=<uuid> REASON="Security concerns - requires additional review"
```

---

## Monitoring

### Check Pending Approvals

```bash
task workflow:list-pending

# Output:
# Pending Approval Requests
# ================================================================================
# Request ID: 1d35addc-35b5-488f-89f3-2bfb0c963293
#   Task: Deploy authentication service to production
#   Risk Level: high
#   Agent: orchestrator
#   Created: 2025-11-22 14:30:00
#   Linear Issue: https://linear.app/dev-ops/issue/DEV-142
```

### Check Workflow Status

```bash
task workflow:status WORKFLOW_ID=32467165-c04f-49fa-9e41-8b4bbb775253

# Output:
# Workflow Status
# ================================================================================
# Workflow ID: 32467165-c04f-49fa-9e41-8b4bbb775253
# Status: paused
# Approval Request: 1d35addc-35b5-488f-89f3-2bfb0c963293
# Risk Level: high
# Awaiting: User decision in Linear (DEV-142)
```

### View Orchestrator Logs

```bash
ssh do-codechef-droplet "docker logs deploy-orchestrator-1 --tail 100 | grep -i 'HITL\|approval'"

# Look for:
# - "HITL approval required for high-risk task"
# - "Created Linear approval issue: DEV-142"
# - "Approval status changed to: approved"
# - "Resuming workflow from checkpoint"
```

---

## Troubleshooting

### Workflow Not Resuming After Approval

**Problem**: User approved in Linear but workflow still paused

**Solution**:

1. Check webhook processed successfully:
   ```bash
   ssh do-codechef-droplet "docker logs deploy-orchestrator-1 | grep 'webhook\|approval'"
   ```
2. Verify approval status in PostgreSQL:
   ```sql
   SELECT * FROM approval_requests WHERE id = '<request_id>';
   ```
3. Manually trigger resume:
   ```bash
   task workflow:approve REQUEST_ID=<uuid>
   ```

### Custom Fields Not Pre-filled

**Problem**: Linear issue created without Required Actions checked

**Solution**:

1. Verify custom field IDs in `linear-config.yaml`
2. Run: `python support/scripts/linear/get-custom-fields.py`
3. Update environment variables and redeploy:
   ```powershell
   .\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config
   ```

### Webhook Signature Validation Failed

**Problem**: `403 Forbidden` when Linear sends webhook

**Solution**:

1. Verify `LINEAR_WEBHOOK_SIGNING_SECRET` in `.env`
2. Check webhook secret in Linear Settings → Webhooks matches `.env`
3. Regenerate secret if needed and redeploy

### Expired Approval Requests

**Problem**: Old approval requests cluttering database

**Solution**:

```bash
# Clean up expired requests (older than timeout)
task workflow:clean-expired

# Manual cleanup
ssh do-codechef-droplet 'docker exec deploy-postgres-1 psql -U devtools -d devtools -c "DELETE FROM approval_requests WHERE status = '\''pending'\'' AND expires_at < NOW();"'
```

---

## Best Practices

### ✅ Do's

- **Use risk assessor consistently**: All tasks should be risk-assessed before execution
- **Pre-fill required actions**: Let orchestrator determine actions based on risk level
- **Add context to approval requests**: Include links to code, architecture docs, runbooks
- **Set realistic timeouts**: 30min for medium, 60min for high, 120min for critical
- **Monitor pending approvals**: Check `task workflow:list-pending` regularly
- **Clean up expired requests**: Run `task workflow:clean-expired` weekly

### ❌ Don'ts

- **Don't bypass risk assessment**: Even "trivial" operations should be assessed
- **Don't pre-fill Request Status**: Let user decide approval/denial
- **Don't use polling**: Webhooks provide sub-second notification latency
- **Don't skip justification**: Always explain why task requires approval
- **Don't ignore timeouts**: Expired approvals should be re-submitted

---

## Related Documentation

- **Linear Integration**: `support/docs/integrations/LINEAR_INTEGRATION.md`
- **Deployment Guide**: `support/docs/getting-started/DEPLOYMENT.md`
- **Risk Assessment Rules**: `config/hitl/risk-assessment-rules.yaml`
- **Approval Policies**: `config/hitl/approval-policies.yaml`
- **Database Schema**: `config/state/approval_requests.sql`

---

**Document Version:** 1.0.0  
**Architecture:** LangGraph v0.3 with HITL  
**Approval Hub**: DEV-68  
**Last Updated:** November 22, 2025
