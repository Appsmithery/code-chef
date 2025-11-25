# Workflow CLI Guide

Complete guide to using declarative workflows via Taskfile commands.

## Quick Start

```bash
# List available workflows
task workflow:list-templates

# Execute PR deployment
task workflow:pr-deploy PR_NUMBER=123 BRANCH=feature/test

# Check status
task workflow:status WORKFLOW_ID=abc-123

# Resume after approval
task workflow:resume WORKFLOW_ID=abc-123 DECISION=approved
```

## Available Workflows

### 1. PR Deployment (`workflow:pr-deploy`)

**Purpose**: Full PR review and deployment to production

**Usage**:

```bash
task workflow:pr-deploy PR_NUMBER=123 BRANCH=feature/api-updates
```

**Parameters**:

- `PR_NUMBER` (default: 123) - Pull request number
- `BRANCH` (default: feature/test) - Feature branch name

**Steps**:

1. Code review by code-review agent
2. Run unit+integration tests
3. Deploy to staging environment
4. **PAUSE for approval** (creates Linear issue)
5. Deploy to production (after approval)
6. Update documentation

**Example Output**:

```
✓ Workflow started: pr-deployment-abc123
Monitor: http://localhost:8001/workflow/status/pr-deployment-abc123
```

### 2. Hotfix (`workflow:hotfix`)

**Purpose**: Emergency production fix with fast-track deployment

**Usage**:

```bash
task workflow:hotfix PR_NUMBER=456 BRANCH=hotfix/critical-security-fix
```

**Parameters**:

- `PR_NUMBER` (default: 456) - Hotfix PR number
- `BRANCH` (default: hotfix/critical) - Hotfix branch name

**Steps**:

1. Validate hotfix criteria
2. Emergency security review
3. Deploy directly to production (skips staging)
4. Post-deploy smoke tests

**Fast-Track**: No staging deployment, minimal approval gates for urgent fixes

### 3. Feature Development (`workflow:feature`)

**Purpose**: Full feature implementation lifecycle with dynamic routing

**Usage**:

```bash
task workflow:feature TASK="Add API authentication" LANGUAGE=python
```

**Parameters**:

- `TASK` (default: "Add test feature") - Feature description
- `LANGUAGE` (default: python) - Programming language (python/javascript/typescript/go/java)

**Steps**:

1. Supervisor analyzes requirements → determines path (code_only/full_stack/docs_only)
2. Feature-dev implements code
3. Code-review checks quality/security
4. CI/CD runs tests
5. **Conditional**: Update infrastructure (if IaC changes detected)
6. **Conditional**: Update CI/CD pipelines (if pipeline changes needed)
7. Documentation updates
8. **PAUSE for approval** based on risk assessment

**Dynamic Routing**: LLM decision gate after analyze_requirements determines workflow path

### 4. Infrastructure Deployment (`workflow:infrastructure`)

**Purpose**: Safe IaC deployment with plan, approval, apply, rollback

**Usage**:

```bash
task workflow:infrastructure CHANGES="Add PostgreSQL database" ENV=staging
```

**Parameters**:

- `CHANGES` (default: "Add test resource") - Infrastructure changes description
- `ENV` (default: staging) - Target environment (staging/production)

**Steps**:

1. Infrastructure agent analyzes IaC changes
2. Generate plan (like `terraform plan`)
3. **PAUSE for approval** with risk assessment
4. **Escalate approval** if critical (requires 2 approvals)
5. Apply changes (like `terraform apply`)
6. Update infrastructure documentation
7. **Automatic rollback** if health checks fail

**Resource Locking**: Prevents concurrent deployments to same environment

### 5. Documentation Update (No Task Command - Use API)

**Purpose**: Fast-track documentation-only changes

**API Usage**:

```bash
curl -X POST http://localhost:8001/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "docs-update.workflow.yaml",
    "context": {
      "files_changed": ["README.md", "QUICKSTART.md"],
      "pr_number": 789,
      "change_type": "typo_fix",
      "author": "contributor"
    }
  }'
```

**Steps**:

1. Validate docs-only (rejects if code files changed)
2. Review documentation (clarity, completeness, broken links)
3. Check if approval needed (low-risk auto-approved)
4. Merge directly to main (skips tests/staging)

## Workflow Management

### Check Status

```bash
task workflow:status WORKFLOW_ID=abc-123
```

**Output**:

```json
{
  "workflow_id": "abc-123",
  "status": "running",
  "current_step": "code_review",
  "started_at": "2025-11-25T10:30:00Z",
  "step_statuses": {
    "code_review": "running",
    "run_tests": "pending",
    "deploy_staging": "pending"
  }
}
```

**Possible Statuses**:

- `pending` - Workflow queued, not started
- `running` - Currently executing
- `paused` - Waiting for HITL approval
- `completed` - Successfully finished
- `failed` - Error occurred
- `rolled_back` - Rolled back due to failure

### Resume Paused Workflow

When workflow pauses for approval (creates Linear issue), resume with:

```bash
# Approve and continue
task workflow:resume WORKFLOW_ID=abc-123 DECISION=approved

# Reject and terminate
task workflow:resume WORKFLOW_ID=abc-123 DECISION=rejected
```

**Approval Flow**:

1. Workflow pauses at `approval_gate` step
2. Linear issue created with workflow context, risk assessment, approval details
3. Issue assigned to appropriate role (tech_lead, devops_engineer)
4. Approver reviews in Linear
5. Run `task workflow:resume` to continue or abort

**Example**: PR deployment paused at approval_gate

```bash
# Check status first
task workflow:status WORKFLOW_ID=pr-deployment-abc123
# Output: "status": "paused", "current_step": "approval_gate"

# Approve to deploy to production
task workflow:resume WORKFLOW_ID=pr-deployment-abc123 DECISION=approved

# Workflow continues: deploy_production → update_docs → completed
```

### Cancel/Abort Workflow

**Current Status**: Not yet implemented (planned for Week 4 - DEV-174)

**Workaround**: For paused workflows, reject approval

```bash
task workflow:resume WORKFLOW_ID=abc-123 DECISION=rejected
```

**Future Enhancement** (Week 4):

```bash
task workflow:cancel WORKFLOW_ID=abc-123
```

Will add:

- Immediate cancellation of running workflows
- Cleanup of in-progress steps
- Rollback of partial changes (if configured)
- Audit log entry

### List Available Templates

```bash
task workflow:list-templates
```

**Output**:

```
pr-deployment.workflow.yaml - Pull Request Deployment with Approval
hotfix.workflow.yaml - Emergency Hotfix Workflow (Fast-Track)
feature.workflow.yaml - Feature Development Lifecycle
docs-update.workflow.yaml - Documentation-Only Updates
infrastructure.workflow.yaml - Infrastructure as Code Deployment
```

## Advanced Usage

### Custom Context Variables

All workflows accept custom context via JSON. For complex scenarios, use direct API:

```bash
curl -X POST http://localhost:8001/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "feature.workflow.yaml",
    "context": {
      "task_description": "Add OAuth2 authentication",
      "project_path": "/opt/Dev-Tools",
      "language": "python",
      "framework": "FastAPI",
      "requires_infrastructure": true,
      "requires_cicd": true,
      "target_coverage": 90,
      "custom_labels": ["security", "api"]
    }
  }'
```

### Workflow State Inspection

```bash
# Get full workflow state
curl -s http://localhost:8001/workflow/status/abc-123 | jq .

# Extract specific step output
curl -s http://localhost:8001/workflow/status/abc-123 | jq '.outputs.code_review'

# Check all step statuses
curl -s http://localhost:8001/workflow/status/abc-123 | jq '.step_statuses'

# Get error message if failed
curl -s http://localhost:8001/workflow/status/abc-123 | jq '.error_message'
```

### Monitoring Multiple Workflows

```bash
# List all running workflows (requires state persistence API)
curl -s http://localhost:8008/workflows | jq '.[] | select(.status=="running") | {workflow_id, current_step}'

# Monitor workflow in real-time (poll every 5s)
watch -n 5 'curl -s http://localhost:8001/workflow/status/abc-123 | jq ".status, .current_step"'
```

## Prompt Validation

Before executing workflows, validate that all agent prompts are under 8K token budget:

```bash
task prompts:validate
```

**Expected Output**:

```
Validating supervisor prompt... ✓ 2,345 tokens (29% of 8K budget)
Validating feature-dev prompt... ✓ 3,567 tokens (45% of 8K budget)
Validating code-review prompt... ✓ 4,123 tokens (52% of 8K budget)
Validating infrastructure prompt... ✓ 2,890 tokens (36% of 8K budget)
Validating cicd prompt... ✓ 2,456 tokens (31% of 8K budget)
Validating documentation prompt... ✓ 2,012 tokens (25% of 8K budget)

All prompts valid ✓
```

**Token Budget**: 8K per agent (system prompt + tool guides + workflow context)

## Integration with Linear

All workflows integrate with Linear for HITL approvals:

**Approval Issue Structure**:

```
Title: [WORKFLOW] Approval Required: PR Deployment

Workflow: pr-deployment.workflow.yaml
Workflow ID: pr-deployment-abc123
Step: approval_gate
Risk Level: medium

Risk Assessment
- Code changes: 145 lines (8 files)
- Security review: PASSED
- Test coverage: 92% (target: 85%)
- Approver required: tech_lead

Approval Details
- Deployment Target: production
- Estimated Downtime: 0 minutes
- Rollback Plan: automated via CI/CD

Actions
- Approve: Resume workflow with approved decision
- Reject: Terminate workflow

Resume Endpoint: POST http://45.55.173.72:8001/workflow/resume/pr-deployment-abc123
```

**Parent Issue**: All approval requests created as sub-issues of DEV-68 (HITL Hub)

## Observability

### LangSmith Tracing

All workflow executions traced in LangSmith:

- **Project**: `agents-workflows`
- **Dashboard**: https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207

**What's Traced**:

- Workflow start/completion
- Agent invocations with payloads
- LLM decision gate calls
- Approval issue creation
- Resource lock acquisition/release

### Grafana Metrics

Workflow metrics available in Grafana:

- **Workflow Execution Count**: Counter per template
- **Workflow Duration**: Histogram by status
- **Step Execution Time**: Per step type
- **Approval Wait Time**: Time from pause to resume
- **Resource Lock Contention**: Lock acquisition failures

**Dashboard**: https://appsmithery.grafana.net/d/workflows

### PostgreSQL State

All workflow state persisted in PostgreSQL (`state-persistence` service):

- Workflow definitions
- Step statuses
- Agent outputs
- Decision gate results
- Resource locks

**Query Workflow History**:

```sql
SELECT workflow_id, status, started_at, completed_at
FROM workflow_state
WHERE template_name = 'pr-deployment.workflow.yaml'
ORDER BY started_at DESC
LIMIT 10;
```

## Troubleshooting

### Workflow Never Starts

**Symptom**: `task workflow:pr-deploy` returns immediately, no workflow_id

**Causes**:

- Orchestrator not running
- Template file not found
- Invalid JSON in context

**Fix**:

```bash
# Check orchestrator health
curl http://localhost:8001/health

# Verify template exists
task workflow:list-templates

# Test with minimal context
curl -X POST http://localhost:8001/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{"template_name": "pr-deployment.workflow.yaml", "context": {"pr_number": 1, "branch": "test"}}'
```

### Workflow Stuck on Step

**Symptom**: Status shows same step for >5 minutes

**Causes**:

- Agent execution error (not caught)
- LLM call timeout
- PostgreSQL state save failure

**Fix**:

```bash
# Check orchestrator logs
docker compose logs orchestrator | grep abc-123

# Check LangSmith traces for errors
# Dashboard → Filter by workflow_id

# Check PostgreSQL state
curl -s http://localhost:8008/workflow/abc-123 | jq .
```

### Approval Issue Not Created

**Symptom**: Workflow paused but no Linear issue

**Causes**:

- `LINEAR_API_KEY` missing or invalid
- Linear API rate limit exceeded
- LinearWorkspaceClient not available

**Fix**:

```bash
# Verify Linear API key
curl -H "Authorization: $LINEAR_API_KEY" https://api.linear.app/graphql \
  -d '{"query": "{viewer{id name}}"}'

# Check orchestrator environment
docker compose exec orchestrator env | grep LINEAR

# Check logs for Linear API errors
docker compose logs orchestrator | grep -i linear
```

### Resource Lock Deadlock

**Symptom**: Multiple infrastructure workflows stuck on lock acquisition

**Causes**:

- Previous workflow failed without releasing lock
- PostgreSQL advisory lock orphaned

**Fix**:

```bash
# List all active locks
docker compose exec postgres psql -U postgres -d workflow_state \
  -c "SELECT * FROM pg_locks WHERE locktype = 'advisory';"

# Force release all advisory locks
docker compose exec postgres psql -U postgres -d workflow_state \
  -c "SELECT pg_advisory_unlock_all();"

# Resume workflows
task workflow:status WORKFLOW_ID=infra-abc123
```

## Best Practices

### 1. Use Descriptive Context

Bad:

```bash
task workflow:feature TASK="fix bug"
```

Good:

```bash
task workflow:feature TASK="Fix authentication timeout in API gateway (issue #456)"
```

### 2. Validate Before Production Workflows

Always test workflows on staging first:

```bash
# Staging deployment
task workflow:infrastructure CHANGES="Add Redis cache" ENV=staging

# Wait for completion and verify
task workflow:status WORKFLOW_ID=infra-staging-123

# Then production
task workflow:infrastructure CHANGES="Add Redis cache" ENV=production
```

### 3. Monitor Approval Wait Times

Long approval wait times indicate bottlenecks:

```bash
# Check all paused workflows
curl -s http://localhost:8008/workflows | jq '.[] | select(.status=="paused") | {workflow_id, current_step, started_at}'
```

Consider:

- Auto-approval for low-risk changes
- Delegating approval to team leads
- Configuring approval timeouts

### 4. Review Failed Workflows

Always investigate failures:

```bash
# Get error details
task workflow:status WORKFLOW_ID=failed-abc123 | jq '.error_message, .failed_step'

# Check LangSmith trace
# Navigate to: https://smith.langchain.com → Search workflow_id

# Review agent outputs
task workflow:status WORKFLOW_ID=failed-abc123 | jq '.outputs'
```

### 5. Clean Up Old Workflows

PostgreSQL state grows over time. Archive completed workflows:

```sql
-- Archive workflows older than 30 days
DELETE FROM workflow_state
WHERE status = 'completed'
  AND completed_at < NOW() - INTERVAL '30 days';
```

## Event Sourcing Commands (New in Week 4)

### View Event Log

Show complete event history for a workflow:

```bash
# View all events
curl http://localhost:8001/workflow/abc-123/events

# View with pagination
curl "http://localhost:8001/workflow/abc-123/events?limit=50&offset=0"

# Filter by action type
curl "http://localhost:8001/workflow/abc-123/events?action=COMPLETE_STEP"
```

**Taskfile Command**:

```bash
task workflow:events WORKFLOW_ID=abc-123
```

### Export Audit Report

Generate compliance audit report:

```bash
# Export to PDF
curl "http://localhost:8001/workflow/abc-123/events/export?format=pdf" > audit_report.pdf

# Export to JSON
curl "http://localhost:8001/workflow/abc-123/events/export?format=json" > events.json

# Export to CSV
curl "http://localhost:8001/workflow/abc-123/events/export?format=csv" > events.csv
```

**Taskfile Command**:

```bash
task workflow:export-audit WORKFLOW_ID=abc-123 FORMAT=pdf
```

PDF audit report includes:

- Workflow timeline (Gantt chart)
- Approval history with approver roles
- Resource lock acquisition/release
- Error events and retry attempts
- Event signature verification status

### Replay Workflow

Test state reconstruction from events:

```bash
# Replay all events to reconstruct state
curl -X POST http://localhost:8001/workflow/abc-123/replay
```

**Taskfile Command**:

```bash
task workflow:replay WORKFLOW_ID=abc-123
```

**Use Cases**:

- Debugging state mismatches
- Verifying event sourcing implementation
- Testing reducer correctness

### Time-Travel Debugging

Reconstruct state at specific timestamp:

```bash
# Get state at 10:15 AM on Jan 15, 2024
curl http://localhost:8001/workflow/abc-123/state-at/2024-01-15T10:15:00Z
```

**Taskfile Command**:

```bash
task workflow:time-travel WORKFLOW_ID=abc-123 TIMESTAMP=2024-01-15T10:15:00Z
```

**Use Cases**:

- Incident investigation: "What was the state when the failure occurred?"
- Compliance audits: "Show me the approval history at deployment time"
- Regression testing: "Reproduce the bug by replaying events"

### View Snapshots

List performance snapshots (created every 10 events):

```bash
curl http://localhost:8001/workflow/abc-123/snapshots
```

**Taskfile Command**:

```bash
task workflow:snapshots WORKFLOW_ID=abc-123
```

**Response**:

```json
[
  {
    "snapshot_id": "uuid-123",
    "workflow_id": "abc-123",
    "event_count": 10,
    "created_at": "2024-01-15T10:00:00Z"
  },
  {
    "snapshot_id": "uuid-456",
    "workflow_id": "abc-123",
    "event_count": 20,
    "created_at": "2024-01-15T10:05:00Z"
  }
]
```

### Annotate Event

Add operator comment to event (for incident tracking):

```bash
curl -X POST http://localhost:8001/workflow/abc-123/annotate \
  -H "Content-Type: application/json" \
  -d '{
    "operator": "alice@example.com",
    "comment": "Manually approved due to urgent customer escalation",
    "event_id": "event-uuid-789"
  }'
```

**Taskfile Command**:

```bash
task workflow:annotate WORKFLOW_ID=abc-123 \
  OPERATOR="alice@example.com" \
  COMMENT="Manually approved due to emergency"
```

### Cancel Workflow (Updated)

Cancel workflow with comprehensive cleanup:

```bash
curl -X DELETE "http://localhost:8001/workflow/abc-123?reason=Emergency%20fix%20deployed&cancelled_by=ops@example.com"
```

**Taskfile Command**:

```bash
task workflow:cancel \
  WORKFLOW_ID=abc-123 \
  REASON="Emergency fix deployed" \
  CANCELLED_BY="ops@example.com"
```

**Cleanup Actions**:

- Release PostgreSQL advisory locks
- Mark Linear approval issues as cancelled
- Notify participating agents
- Cancel child workflows

### Retry Failed Workflow (Updated)

Retry failed workflow with exponential backoff:

```bash
curl -X POST "http://localhost:8001/workflow/abc-123/retry-from/deploy?max_retries=3"
```

**Taskfile Command**:

```bash
task workflow:retry WORKFLOW_ID=abc-123 STEP_ID=deploy MAX_RETRIES=3
```

**Response**:

```json
{
  "workflow_id": "abc-123",
  "step_id": "deploy",
  "retry_attempt": 2,
  "max_retries": 3,
  "backoff_delay": 4.0,
  "status": "retrying"
}
```

## Automated Audit Reports

Generate audit reports automatically via cron job:

```bash
# Generate reports for all workflows completed in last 7 days
python support/scripts/generate_audit_reports.py

# Generate reports for last 30 days
python support/scripts/generate_audit_reports.py --days 30

# Generate report for specific workflow
python support/scripts/generate_audit_reports.py --workflow-id abc-123

# Archive old events (90+ days)
python support/scripts/generate_audit_reports.py --archive

# Compress archived events to gzip
python support/scripts/generate_audit_reports.py --compress
```

**Cron Schedule** (Weekly on Sundays at 2 AM):

```bash
0 2 * * 0 /usr/bin/python3 /opt/Dev-Tools/support/scripts/generate_audit_reports.py --archive --compress
```

## See Also

- **Event Sourcing Guide**: `support/docs/guides/EVENT_SOURCING.md` - Complete architecture documentation
- **Workflow Quick Reference**: `agent_orchestrator/workflows/WORKFLOW_QUICK_REFERENCE.md`
- **Workflow Testing**: `support/docs/WORKFLOW_TESTING.md`
- **Architecture Overview**: `support/docs/ARCHITECTURE.md`
- **Linear Integration**: `config/linear/AGENT_QUICK_REFERENCE.md`
- **Deployment Guide**: `support/docs/DEPLOYMENT.md`
