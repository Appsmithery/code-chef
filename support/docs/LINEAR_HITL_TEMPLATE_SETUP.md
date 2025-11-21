# Linear HITL Approval Template Configuration Guide

## Overview

This guide configures the Linear approval template (ID: `8881211a-7b9c-42ab-a178-608ddf1f6665`) with custom fields for Human-in-the-Loop (HITL) approval workflow.

## Template Structure

### Custom Fields

1. **Request Status** (Dropdown, _NOT_ Required) // ---> this field tracks the approval decision, and is the human's input, so should _not_ be pre-filled by the orchestrator.

   - Approved (Default)
   - Denied
   - More information required

2. **Required Action** (Checkboxes, Required) // ---> this field indicates the actions the reviewer must take, and is pre-filled by the orchestrator based on risk level and should be moved up in the order.
   - Review proposed changes
   - Verify risks are acceptable
   - Check implementation approach
   - Request modifications

## Setup Steps

### Step 1: Retrieve Custom Field IDs

Run the inspection script to get field IDs from your Linear workspace:

```bash
# Set your Linear API key
export LINEAR_API_KEY="lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571"

# Optional: Set team ID (script will auto-detect if omitted)
export LINEAR_TEAM_ID="f5b610be-ac34-4983-918b-2c9d00aa9b7a"  # Project Roadmaps (PR)

# Run the script
python support/scripts/linear/get-custom-fields.py
```

**Output Example:**

```
Custom Fields for Team: Project Roadmaps (PR)
================================================================================

Field: Request Status
  ID: abc123...
  Type: dropdown
  Enabled: true
  Options:
    - Approved (id: opt1, color: green)
    - Denied (id: opt2, color: red)
    - More information required (id: opt3, color: yellow)

Field: Required Action
  ID: def456...
  Type: checkboxes
  Enabled: true
  Options:
    - Review proposed changes (id: opt4, color: blue)
    - Verify risks are acceptable (id: opt5, color: orange)
    - Check implementation approach (id: opt6, color: purple)
    - Request modifications (id: opt7, color: gray)

Environment Variable Configuration
================================================================================
LINEAR_FIELD_REQUEST_STATUS_ID=abc123...
LINEAR_FIELD_REQUIRED_ACTION_ID=def456...
LINEAR_REQUEST_STATUS_APPROVED=opt1
LINEAR_REQUEST_STATUS_DENIED=opt2
LINEAR_REQUEST_STATUS_MORE_INFORMATION_REQUIRED=opt3
```

### Step 2: Update Environment Configuration

Add the retrieved IDs to `config/env/.env`:

```bash
# Linear Custom Field IDs (from get-custom-fields.py output)
LINEAR_FIELD_REQUEST_STATUS_ID=abc123...
LINEAR_FIELD_REQUIRED_ACTION_ID=def456...
LINEAR_REQUEST_STATUS_APPROVED=opt1
LINEAR_REQUEST_STATUS_DENIED=opt2
LINEAR_REQUEST_STATUS_MORE_INFO=opt3
```

### Step 3: Deploy Configuration

Deploy the updated configuration to the droplet:

```powershell
# Copy updated .env to droplet
scp config/env/.env root@45.55.173.72:/opt/Dev-Tools/config/env/.env

# Restart orchestrator to load new configuration
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose down orchestrator && docker compose up -d orchestrator"
```

### Step 4: Configure Webhook

Set up Linear webhook to handle approval status changes:

1. Go to Linear Settings → API → Webhooks
2. Click "Create webhook"
3. Configure:

   - **URL**: `https://theshop.appsmithery.co/webhooks/linear`
   - **Events**: `Issue updated`, `Comment created`
   - **Secret**: Generate and save to `.env` as `LINEAR_WEBHOOK_SIGNING_SECRET`

4. Save the webhook

### Step 5: Test Approval Flow

Send a high-risk request to trigger HITL approval:

```powershell
$json = @'
{
  "message": "DROP TABLE production.users CASCADE"
}
'@

Invoke-RestMethod -Uri "http://45.55.173.72:8001/chat" -Method POST -Body $json -ContentType "application/json"
```

**Expected Behavior:**

1. Orchestrator detects high-risk action
2. Creates sub-issue in DEV-68 (approval hub)
3. Issue has:

   - **Request Status**: Empty (awaiting your input)
   - **Required Action**: Pre-checked based on risk level
   - **Assignee**: alex@appsmithery.co
   - **Labels**: HITL, orchestrator
   - **Priority**: Urgent (for high/critical risk)

4. You fill out the form:

   - Select "Approved" or "Denied" from Request Status
   - Check any additional Required Actions
   - Add comments if needed

5. Webhook triggers workflow resume/cancel based on your selection

## Approval Workflow States

### Approved Flow

```
[Create Issue] → [User sets Request Status = Approved] → [Webhook triggers]
  → [Resume LangGraph workflow] → [Execute approved actions]
  → [Update issue to "In Progress"] → [Complete]
```

### Denied Flow

```
[Create Issue] → [User sets Request Status = Denied] → [Webhook triggers]
  → [Cancel LangGraph workflow] → [No actions taken]
  → [Update issue to "Canceled"] → [Complete]
```

### More Info Required Flow

```
[Create Issue] → [User sets Request Status = More info] → [Webhook triggers]
  → [Keep workflow paused] → [User adds comments with clarification]
  → [User changes to "Approved"] → [Resume workflow]
```

## Custom Field Auto-Configuration

The orchestrator automatically configures custom fields based on risk level:

### Low/Medium Risk

- **Request Status**: Empty (user decides approval)
- **Required Action**: `["review_proposed_changes"]` (pre-checked)

### High/Critical Risk

- **Request Status**: Empty (user decides approval)
- **Required Action**: `["review_proposed_changes", "verify_risks_are_acceptable", "check_implementation_approach"]` (pre-checked)

## Comment Commands

Use slash commands in issue comments for quick actions:

- `/approve` - Sets Request Status to "Approved"
- `/deny` - Sets Request Status to "Denied"
- `/request-info` - Sets Request Status to "More information required"

## Webhook Handler Configuration

See `config/linear/webhook-handlers.yaml` for complete webhook event handling logic.

Key handlers:

- `hitl_approval_status_change` - Triggers on Request Status updates
- `hitl_required_actions_updated` - Tracks checklist completion
- `hitl_comment_commands` - Processes slash commands

## Monitoring & Observability

### LangSmith Traces

- Webhook handlers are traced in LangSmith project `webhooks-linear`
- View at: https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects

### Health Checks

```bash
# Check webhook endpoint
curl https://theshop.appsmithery.co/webhooks/linear/health

# Check orchestrator status
curl http://45.55.173.72:8001/health
```

### Logs

```bash
# View orchestrator logs
ssh root@45.55.173.72 "docker logs deploy-orchestrator-1 --tail 100 -f"

# Filter for HITL-related logs
ssh root@45.55.173.72 "docker logs deploy-orchestrator-1 --tail 500 | grep -i hitl"
```

## Troubleshooting

### Issue: Custom fields not showing in created issues

**Solution**: Verify field IDs are correct and fields are enabled for the team

```bash
python support/scripts/linear/get-custom-fields.py
```

### Issue: Webhook not triggering

**Solution**: Check webhook signature and event filters

1. Verify `LINEAR_WEBHOOK_SIGNING_SECRET` in `.env`
2. Check webhook logs in Linear Settings → API → Webhooks
3. Test webhook with Linear's test feature

### Issue: Workflow not resuming after approval

**Solution**: Check LangGraph checkpoint and workflow state

```bash
# Check workflow state in PostgreSQL
ssh root@45.55.173.72 'docker exec deploy-postgres-1 psql -U devtools -d devtools -c "SELECT * FROM workflow_state WHERE status = '\''paused'\'';"'
```

## References

- Linear Templates: https://linear.app/dev-ops/settings/templates
- Linear API: https://developers.linear.app/docs/graphql/api
- Webhooks: https://developers.linear.app/docs/graphql/webhooks
- LangGraph Checkpointing: https://langchain-ai.github.io/langgraph/how-tos/persistence/
