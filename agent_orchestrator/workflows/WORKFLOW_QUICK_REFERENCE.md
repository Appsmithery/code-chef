# Workflow Engine Quick Reference

## Overview

Declarative workflow engine with YAML templates, LLM decision gates, and HITL approvals.

**Location**: `agent_orchestrator/workflows/`

## Available Templates

### 1. **pr-deployment.workflow.yaml**

Full PR deployment pipeline with staging and production.

**Steps**: code_review → run_tests → deploy_staging → approval_gate → deploy_production → update_docs

**Use Case**: Standard pull request deployments

**Context Variables**:

```json
{
  "pr_number": 123,
  "repo_url": "github.com/org/repo",
  "branch": "feature/new-api",
  "previous_version": "v1.2.3"
}
```

---

### 2. **hotfix.workflow.yaml**

Fast-track emergency fixes (skips staging).

**Steps**: code_review (security only) → run_critical_tests → deploy_production → rollback_production (if needed)

**Use Case**: Production hotfixes, urgent security patches

**Context Variables**:

```json
{
  "pr_number": 456,
  "branch": "hotfix/security-patch",
  "previous_version": "v1.2.3"
}
```

---

### 3. **feature.workflow.yaml**

Standard feature development lifecycle.

**Steps**: analyze_requirements → implement_feature → code_review → run_tests → update_infrastructure (optional) → update_cicd (optional) → update_documentation → approval_gate → merge_feature

**Use Case**: New features, enhancements

**Context Variables**:

```json
{
  "task_description": "Add user authentication with JWT",
  "project_context": "Express.js REST API",
  "project_path": "/path/to/project",
  "language": "typescript",
  "branch": "feature/jwt-auth"
}
```

---

### 4. **docs-update.workflow.yaml**

Documentation-only changes (skips tests, staging).

**Steps**: validate_docs_only → review_documentation → check_approval_needed → merge_documentation

**Use Case**: README updates, API docs, typo fixes

**Context Variables**:

```json
{
  "files_changed": ["README.md", "docs/API.md"],
  "pr_number": 789,
  "branch": "docs/api-update"
}
```

---

### 5. **infrastructure.workflow.yaml**

IaC changes with plan, approval, apply, rollback.

**Steps**: analyze_changes → generate_plan → approval_gate → apply_changes → update_documentation → rollback_changes (on failure)

**Use Case**: Terraform, Pulumi, CloudFormation deployments

**Context Variables**:

```json
{
  "changes_description": "Add RDS PostgreSQL instance",
  "cloud_provider": "aws",
  "iac_tool": "terraform",
  "environment": "production"
}
```

---

## API Endpoints

### Execute Workflow

```bash
POST http://45.55.173.72:8001/workflow/execute
Content-Type: application/json

{
  "template_name": "feature.workflow.yaml",
  "context": {
    "task_description": "Add user authentication",
    "project_path": "/app/my-service",
    "language": "python",
    "branch": "feature/auth"
  }
}
```

**Response**:

```json
{
  "workflow_id": "abc-123-def-456",
  "status": "running",
  "current_step": "implement_feature",
  "step_statuses": {
    "analyze_requirements": "completed",
    "implement_feature": "running",
    "code_review": "pending"
  },
  "started_at": "2025-11-25T10:30:00Z"
}
```

---

### Get Workflow Status

```bash
GET http://45.55.173.72:8001/workflow/status/abc-123-def-456
```

**Response**:

```json
{
  "workflow_id": "abc-123-def-456",
  "status": "paused",
  "current_step": "approval_gate",
  "started_at": "2025-11-25T10:30:00Z",
  "step_statuses": {
    "analyze_requirements": "completed",
    "implement_feature": "completed",
    "code_review": "completed",
    "run_tests": "completed",
    "approval_gate": "running",
    "merge_feature": "pending"
  }
}
```

---

### Resume Workflow (HITL Approval)

```bash
POST http://45.55.173.72:8001/workflow/resume/abc-123-def-456
Content-Type: application/json

{
  "approval_decision": "approved"
}
```

**Response**:

```json
{
  "workflow_id": "abc-123-def-456",
  "status": "completed",
  "current_step": "merge_feature",
  "approval_decision": "approved",
  "completed_at": "2025-11-25T10:45:00Z"
}
```

---

### List Templates

```bash
GET http://45.55.173.72:8001/workflow/templates
```

**Response**:

```json
{
  "templates": [
    {
      "template_name": "pr-deployment.workflow.yaml",
      "name": "PR Deployment Workflow",
      "description": "Automated PR review, test, and deployment pipeline",
      "version": "1.0"
    },
    {
      "template_name": "hotfix.workflow.yaml",
      "name": "Hotfix Workflow",
      "description": "Fast-track emergency hotfix deployment",
      "version": "1.0"
    }
  ]
}
```

---

## Workflow Features

### LLM Decision Gates

**Purpose**: Dynamic routing based on LLM assessment of results.

**Example** (from `pr-deployment.workflow.yaml`):

```yaml
decision_gate:
  type: "llm_assessment"
  prompt: |
    Review results:
    - Security issues: {{ outputs.code_review.security_issues }}
    - Quality score: {{ outputs.code_review.quality_score }}

    Should we proceed to testing? Respond with:
    {"decision": "proceed" | "block", "reasoning": "..."}

  on_proceed: "run_tests"
  on_block: "notify_failure"
```

---

### HITL Approval Gates

**Purpose**: Human approval for high-risk operations.

**Example** (from `feature.workflow.yaml`):

```yaml
- id: "approval_gate"
  type: "hitl_approval"
  risk_assessment:
    type: "llm_assessment"
    prompt: |
      Feature development complete:
      - Quality score: {{ outputs.code_review.quality_score }}
      - Tests: {{ outputs.run_tests.passed }}/{{ outputs.run_tests.total }}

      Assess risk and determine if approval needed:
      - Low risk: Auto-approve if all tests pass
      - Medium risk: Require tech_lead approval
      - High risk: Require devops_engineer approval

  on_approved: "merge_feature"
  on_rejected: "notify_failure"
```

**Workflow Pauses**: When HITL approval is required, workflow status becomes `"paused"` and a Linear issue is created.

**Resume**: Once approved/rejected in Linear, call `POST /workflow/resume/{id}` to continue.

---

### Resource Locking

**Purpose**: Prevent concurrent operations on the same resource.

**Example** (from `infrastructure.workflow.yaml`):

```yaml
- id: "apply_changes"
  type: "agent_call"
  agent: "infrastructure"
  resource_lock: "infrastructure:production" # Prevents concurrent deploys
```

**Behavior**: If another workflow holds the lock, this step waits until released.

---

### Jinja2 Template Rendering

**Purpose**: Dynamic payloads with context variables.

**Example**:

```yaml
payload:
  pr_number: "{{ context.pr_number }}"
  quality_score: "{{ outputs.code_review.quality_score }}"
  test_results: "{{ outputs.run_tests.passed }}/{{ outputs.run_tests.total }}"
```

**Available Variables**:

- `context.*`: Initial context from `/workflow/execute` request
- `outputs.step_id.*`: Outputs from completed steps
- `workflow.*`: Workflow metadata (failed_step, error_message)

---

## Taskfile Commands

### Execute Workflow

```bash
task workflow:pr-deploy PR_NUMBER=123 BRANCH=feature/api
task workflow:hotfix PR_NUMBER=456 BRANCH=hotfix/security
```

### Get Status

```bash
task workflow:status WORKFLOW_ID=abc-123-def-456
```

### List Templates

```bash
task workflow:list-templates
```

### Resume Workflow

```bash
task workflow:resume WORKFLOW_ID=abc-123-def-456 DECISION=approved
```

---

## Architecture

### WorkflowEngine Class

**Location**: `agent_orchestrator/workflows/workflow_engine.py`

**Key Methods**:

- `load_workflow(template_name)`: Load YAML template
- `execute_workflow(template_name, context)`: Execute workflow from start
- `resume_workflow(workflow_id, approval_decision)`: Resume paused workflow
- `get_workflow_status(workflow_id)`: Get current status

**State Management**:

- PostgreSQL via `StateClient` (`shared/services/state/client.py`)
- LangGraph checkpointing for HITL approvals

---

## Example Usage

### 1. Deploy a PR

```bash
# Start deployment
curl -X POST http://45.55.173.72:8001/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "pr-deployment.workflow.yaml",
    "context": {
      "pr_number": 123,
      "repo_url": "github.com/org/repo",
      "branch": "feature/new-api"
    }
  }'

# Response: {"workflow_id": "abc-123", "status": "running"}

# Check status
curl http://45.55.173.72:8001/workflow/status/abc-123

# If paused for approval
curl -X POST http://45.55.173.72:8001/workflow/resume/abc-123 \
  -H "Content-Type: application/json" \
  -d '{"approval_decision": "approved"}'
```

---

### 2. Deploy Infrastructure

```bash
# Execute IaC workflow
curl -X POST http://45.55.173.72:8001/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "infrastructure.workflow.yaml",
    "context": {
      "changes_description": "Add RDS PostgreSQL",
      "cloud_provider": "aws",
      "iac_tool": "terraform",
      "environment": "production"
    }
  }'

# Workflow will:
# 1. Generate Terraform plan
# 2. Pause for approval (creates Linear issue)
# 3. Apply changes after approval
# 4. Rollback if health checks fail
```

---

### 3. Update Documentation

```bash
# Fast-track docs-only changes
curl -X POST http://45.55.173.72:8001/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "docs-update.workflow.yaml",
    "context": {
      "files_changed": ["README.md", "docs/API.md"],
      "pr_number": 789,
      "branch": "docs/api-update"
    }
  }'

# Auto-approved for low-risk typo fixes
# Requires tech_lead approval for architecture docs
```

---

## Next Steps (Week 3 - DEV-173)

- [ ] Integrate WorkflowEngine with actual agent execution (currently mocked)
- [ ] Connect to Linear API for approval issue creation
- [ ] Add LLM calls for decision gates (currently returning mock decisions)
- [ ] Test end-to-end workflow execution
- [ ] Add workflow metrics to Prometheus
- [ ] Add workflow traces to LangSmith

---

## Related Documentation

- **Architecture**: `support/docs/ARCHITECTURE.md`
- **12-Factor Agents**: `support/docs/_temp/12-Factor Agents-implementation-plan.md`
- **HITL Workflow**: `support/docs/DEPLOYMENT.md` (HITL section)
- **Linear Integration**: `config/linear/AGENT_QUICK_REFERENCE.md`
