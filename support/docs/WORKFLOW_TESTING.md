# Workflow Testing Guide

## Overview

This guide covers end-to-end testing of the declarative workflow system, including all 5 workflow templates, agent execution integration, LLM decision gates, Linear API approvals, and distributed resource locking.

## Quick Start

```bash
# Test all workflows
python support/scripts/workflow/test-workflows.py

# Test specific workflow
python support/scripts/workflow/test-workflows.py pr-deployment
python support/scripts/workflow/test-workflows.py feature
python support/scripts/workflow/test-workflows.py infrastructure

# Set custom orchestrator URL
ORCHESTRATOR_URL=http://45.55.173.72:8001 python support/scripts/workflow/test-workflows.py
```

## Test Coverage

### 1. PR Deployment Workflow (`pr-deployment.workflow.yaml`)

**Test Scenario**: Full PR review and deployment to production

**Context**:

```json
{
  "pr_number": 123,
  "repo_url": "https://github.com/Appsmithery/Dev-Tools",
  "branch": "feature/test-workflow",
  "base_branch": "main",
  "author": "test-user",
  "title": "Test PR Deployment Workflow"
}
```

**Expected Steps**:

1. `code_review` - Code-review agent analyzes PR
2. `run_tests` - CI/CD agent runs unit+integration tests
3. `deploy_staging` - CI/CD agent deploys to staging environment
4. `approval_gate` - HITL approval (pauses workflow)
5. `deploy_production` - CI/CD agent deploys to production (after approval)
6. `update_docs` - Documentation agent updates deployment docs

**Validation**:

- ✓ Workflow executes all steps in correct order
- ✓ Workflow pauses at approval_gate
- ✓ Linear issue created for approval request
- ✓ Workflow resumes after approval
- ✓ All step outputs stored correctly

### 2. Hotfix Workflow (`hotfix.workflow.yaml`)

**Test Scenario**: Emergency production fix with fast-track deployment

**Context**:

```json
{
  "pr_number": 456,
  "repo_url": "https://github.com/Appsmithery/Dev-Tools",
  "branch": "hotfix/critical-fix",
  "base_branch": "main",
  "author": "devops-user",
  "title": "Critical Production Fix",
  "severity": "critical"
}
```

**Expected Steps**:

1. `validate_hotfix` - Supervisor validates hotfix criteria
2. `emergency_review` - Code-review agent performs rapid security check
3. `deploy_production` - CI/CD agent deploys directly to production (skips staging)
4. `post_deploy_verification` - CI/CD agent runs smoke tests

**Validation**:

- ✓ Fast-track path executed (no staging deploy)
- ✓ Emergency review completes quickly
- ✓ Production deployment successful
- ✓ Post-deploy verification runs

### 3. Feature Development Workflow (`feature.workflow.yaml`)

**Test Scenario**: Full feature implementation lifecycle with dynamic routing

**Context**:

```json
{
  "task_description": "Add test feature for workflow validation",
  "project_path": "/opt/Dev-Tools/agent_orchestrator",
  "language": "python",
  "framework": "FastAPI",
  "requires_infrastructure": false,
  "requires_cicd": false
}
```

**Expected Steps**:

1. `analyze_requirements` - Supervisor analyzes task, determines path
2. `implement_feature` - Feature-dev agent implements code
3. `code_review` - Code-review agent checks quality/security
4. `run_tests` - CI/CD agent runs unit+integration tests
5. `update_documentation` - Documentation agent updates docs
6. `approval_gate` - HITL approval based on risk assessment

**Conditional Steps** (skipped when `requires_*=false`):

- `update_infrastructure` - Infrastructure agent updates IaC (if `requires_infrastructure=true`)
- `update_cicd` - CI/CD agent updates pipelines (if `requires_cicd=true`)

**Validation**:

- ✓ Dynamic routing works (code_only path when no infra/cicd)
- ✓ Conditional steps skipped correctly
- ✓ LLM decision gate determines correct path
- ✓ Risk assessment accurate

### 4. Documentation Update Workflow (`docs-update.workflow.yaml`)

**Test Scenario**: Fast-track documentation-only changes

**Context**:

```json
{
  "files_changed": ["README.md", "support/docs/QUICKSTART.md"],
  "pr_number": 789,
  "change_type": "typo_fix",
  "author": "contributor"
}
```

**Expected Steps**:

1. `validate_docs_only` - Verify no code files changed
2. `review_documentation` - Check clarity, completeness, broken links
3. `check_approval_needed` - LLM risk assessment
4. `merge_documentation` - Merge directly to main (skips tests/staging)

**Validation**:

- ✓ Validates docs-only (rejects if code files changed)
- ✓ Low-risk changes auto-approved
- ✓ Skips testing and staging environments
- ✓ Fast merge to production

### 5. Infrastructure Deployment Workflow (`infrastructure.workflow.yaml`)

**Test Scenario**: Safe IaC deployment with plan, approval, apply, rollback

**Context**:

```json
{
  "changes_description": "Add test PostgreSQL resource",
  "cloud_provider": "digitalocean",
  "environment": "staging",
  "iac_tool": "terraform",
  "resources": ["droplet", "managed_database"]
}
```

**Expected Steps**:

1. `analyze_changes` - Infrastructure agent analyzes IaC changes
2. `generate_plan` - Infrastructure agent creates plan (like `terraform plan`)
3. `approval_gate` - HITL approval with risk assessment
4. `apply_changes` - Infrastructure agent applies changes (like `terraform apply`)
5. `update_documentation` - Documentation agent updates infra docs

**Optional Steps**:

- `escalate_approval` - Critical changes require 2 approvals (if risk=critical)
- `rollback_changes` - Automatic rollback on health check failure

**Validation**:

- ✓ Plan generation works correctly
- ✓ Risk assessment accurate (low/medium/high/critical)
- ✓ Resource locking prevents concurrent deployments to same environment
- ✓ Rollback triggers on health check failure

## Integration Testing

### Agent Execution Integration

**Test**: Verify WorkflowEngine calls actual agents via graph.py

**Method**:

1. Execute workflow with real agent payload
2. Verify agent invocation via LangGraph workflow
3. Check agent response stored in workflow state
4. Validate agent execution errors handled correctly

**Expected Behavior**:

- `_execute_agent_call()` calls appropriate agent node based on `step.agent`
- Agent receives rendered payload with Jinja2 template variables
- Agent response stored in `state.outputs[step_id]`
- Errors trigger retry logic or fail workflow based on `error_handling` config

### LLM Decision Gates

**Test**: Verify real LLM calls for dynamic routing

**Method**:

1. Execute workflow with LLM decision gate
2. Verify GradientClient called with correct prompt
3. Check decision parsed from LLM JSON response
4. Validate routing based on LLM decision

**Expected Behavior**:

- `_call_llm_decision()` calls GradientClient with rendered prompt
- LLM returns structured JSON: `{"decision": "proceed|block", "reasoning": "...", "risk_level": "low|medium|high"}`
- Decision determines next step via `on_proceed`, `on_block` routing
- Errors fallback to safe default (usually "block")

### Linear API Integration

**Test**: Verify HITL approval issues created in Linear

**Method**:

1. Execute workflow that requires approval
2. Verify workflow pauses at HITL step
3. Check Linear issue created with correct details
4. Resume workflow with approval decision
5. Verify workflow continues from correct next step

**Expected Behavior**:

- `_create_approval_issue()` creates Linear issue via GraphQL API
- Issue contains: workflow context, risk assessment, approval payload, resume endpoint
- Issue assigned based on `approver_role` (tech_lead, devops_engineer)
- Issue created as sub-issue of DEV-68 (HITL hub)
- Resume endpoint accepts "approved" or "rejected" decision

### Resource Locking

**Test**: Verify distributed resource locking prevents concurrent operations

**Method**:

1. Execute 2 infrastructure workflows with same environment
2. Verify first workflow acquires lock
3. Verify second workflow waits for first to complete
4. Check lock released after workflow completion or failure

**Expected Behavior**:

- `_acquire_lock()` uses PostgreSQL advisory locks
- Lock name: `infrastructure:{{ context.environment }}`
- Second workflow blocks until first releases lock
- Locks released automatically on workflow completion or failure
- Orphaned locks cleaned up after timeout (30s default)

## Test Execution

### Prerequisites

1. **Orchestrator Running**: Ensure orchestrator service running on localhost:8001 or droplet
2. **Environment Variables**:
   ```bash
   LINEAR_API_KEY=lin_oauth_...
   LANGSMITH_API_KEY=lsv2_sk_...
   GRADIENT_API_KEY=do_pat_...
   ```
3. **Database**: PostgreSQL state persistence service running on localhost:8008
4. **MCP Gateway**: Gateway service running on localhost:8000 with all 17 MCP servers

### Running Tests

```bash
# Local testing (orchestrator on localhost)
docker compose up -d
python support/scripts/workflow/test-workflows.py

# Remote testing (orchestrator on droplet)
ORCHESTRATOR_URL=http://45.55.173.72:8001 python support/scripts/workflow/test-workflows.py

# Test specific workflow with verbose output
python support/scripts/workflow/test-workflows.py infrastructure
```

### Interpreting Results

**Test Output**:

```
================================================================================
Testing Infrastructure Deployment Workflow
================================================================================

1. Executing workflow: infrastructure.workflow.yaml
   Context: {
     "changes_description": "Add test PostgreSQL resource",
     "cloud_provider": "digitalocean",
     "environment": "staging",
     "iac_tool": "terraform",
     "resources": ["droplet", "managed_database"]
   }
   ✓ Workflow started: abc-123

2. Monitoring workflow execution...
   Status: running | Step: analyze_changes
   Status: running | Step: generate_plan
   Status: paused | Step: approval_gate

4. Workflow paused for approval...
   Linear issue: Check Linear for approval request
   Resume: POST http://localhost:8001/workflow/resume/abc-123
   Auto-approving for test...
   ✓ Workflow resumed

   Status: running | Step: apply_changes
   Status: running | Step: update_documentation
   Status: completed | Step: update_documentation

5. Final validation...
   ✓ Workflow completed successfully
```

**Test Summary**:

```
================================================================================
TEST SUMMARY
================================================================================

Total: 5 | Passed: 5 | Failed: 0 | Errors: 0

✓ pr-deployment.workflow.yaml - PASSED
✓ hotfix.workflow.yaml - PASSED
✓ feature.workflow.yaml - PASSED
✓ docs-update.workflow.yaml - PASSED
✓ infrastructure.workflow.yaml - PASSED

Results saved to: support/reports/workflow-test-results-20250119-120000.json
```

### Common Issues

**Issue**: Workflow never starts

- **Cause**: Orchestrator not running or unreachable
- **Fix**: Check `docker compose ps`, verify orchestrator health at `/health` endpoint

**Issue**: Workflow fails at agent execution

- **Cause**: Agent node not available in LangGraph workflow
- **Fix**: Check `agent_orchestrator/graph.py` has agent node defined

**Issue**: LLM decision gate returns error

- **Cause**: GradientClient not initialized or API key missing
- **Fix**: Verify `GRADIENT_API_KEY` set, check LangSmith traces for LLM errors

**Issue**: Linear issue not created

- **Cause**: Linear API key invalid or LinearWorkspaceClient not available
- **Fix**: Verify `LINEAR_API_KEY` set, test Linear GraphQL API directly

**Issue**: Resource lock not working

- **Cause**: StateClient not connected to PostgreSQL
- **Fix**: Verify state-persistence service running, check database connection

## Manual Testing

For manual workflow testing without the test script:

```bash
# 1. Execute workflow
curl -X POST http://localhost:8001/workflow/execute \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "feature.workflow.yaml",
    "context": {
      "task_description": "Add manual test feature",
      "project_path": "/opt/Dev-Tools",
      "language": "python"
    }
  }'

# Response: {"workflow_id": "abc-123", "status": "running", ...}

# 2. Check status
curl http://localhost:8001/workflow/status/abc-123

# 3. Resume after approval
curl -X POST http://localhost:8001/workflow/resume/abc-123 \
  -H "Content-Type: application/json" \
  -d '{"approval_decision": "approved"}'

# 4. List available templates
curl http://localhost:8001/workflow/templates
```

## Performance Benchmarks

### Expected Execution Times

| Workflow       | Steps | Avg Time | Max Time |
| -------------- | ----- | -------- | -------- |
| pr-deployment  | 6     | 45s      | 120s     |
| hotfix         | 4     | 30s      | 60s      |
| feature        | 5-7   | 60s      | 180s     |
| docs-update    | 4     | 20s      | 45s      |
| infrastructure | 5-6   | 90s      | 240s     |

**Notes**:

- Times exclude HITL approval wait time (manual step)
- Times include LLM decision gates (~2-5s per gate)
- Times include agent execution (~10-30s per agent call)
- Infrastructure workflow slower due to plan generation and apply steps

### Performance Optimization

**Parallel Execution**: Future enhancement to execute independent steps in parallel

- Currently: Sequential execution (step-by-step)
- Future: Parallel execution for steps without dependencies
- Estimated speedup: 30-50% for workflows with parallel-eligible steps

**Caching**: Future enhancement to cache LLM decision gate results

- Currently: Every decision gate calls LLM
- Future: Cache decisions for identical contexts
- Estimated speedup: 10-20% for repeated decisions

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Workflow Tests

on:
  push:
    branches: [main]
    paths:
      - "agent_orchestrator/workflows/**"
      - "support/scripts/workflow/**"
  pull_request:
    paths:
      - "agent_orchestrator/workflows/**"

jobs:
  test-workflows:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: workflow_state
          POSTGRES_PASSWORD: postgres

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -r agent_orchestrator/requirements.txt
          pip install httpx pytest pytest-asyncio

      - name: Start services
        run: docker compose up -d orchestrator gateway state-persistence

      - name: Wait for services
        run: sleep 30

      - name: Run workflow tests
        env:
          LINEAR_API_KEY: ${{ secrets.LINEAR_API_KEY }}
          GRADIENT_API_KEY: ${{ secrets.GRADIENT_API_KEY }}
          ORCHESTRATOR_URL: http://localhost:8001
        run: python support/scripts/workflow/test-workflows.py

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: workflow-test-results
          path: support/reports/workflow-test-results-*.json
```

## See Also

- **Workflow Quick Reference**: `agent_orchestrator/workflows/WORKFLOW_QUICK_REFERENCE.md`
- **Architecture Overview**: `support/docs/ARCHITECTURE.md`
- **Deployment Guide**: `support/docs/DEPLOYMENT.md`
- **Linear Integration**: `config/linear/AGENT_QUICK_REFERENCE.md`
