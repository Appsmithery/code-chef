# Phase 3 Implementation Summary: Agent Integration

**Completed**: December 12, 2025  
**Status**: ✅ All Phase 3 tasks complete

---

## Overview

Phase 3 completes the HITL approval integration by enabling individual agent nodes to assess operation risk and automatically route to the approval node when high-risk operations are detected. This provides defense-in-depth: agents can trigger approvals directly without waiting for supervisor routing.

---

## Changes Made

### 1. BaseAgent Risk Assessment Helper

**File**: `agent_orchestrator/agents/_shared/base_agent.py`

**Added Method**: `_assess_operation_risk(operation, context)`

```python
async def _assess_operation_risk(
    self,
    operation: str,
    context: Dict[str, Any],
) -> tuple[str, bool, Optional[Dict[str, Any]]]:
    """Assess risk level of an operation and determine if HITL approval needed.

    Returns:
        Tuple of (risk_level, requires_approval, pr_context)
    """
```

**Features**:

- Integrates with existing `RiskAssessor` from Phase 1
- Returns risk level ("low", "medium", "high", "critical")
- Returns boolean flag for approval requirement
- Extracts PR context if available in operation context
- Fail-safe: treats assessment failures as high-risk
- Detailed logging for debugging

**Usage Example**:

```python
risk_level, needs_approval, pr_ctx = await self._assess_operation_risk(
    operation="deploy",
    context={
        "environment": "production",
        "service": "orchestrator",
        "pr_number": 42,
        "pr_url": "https://github.com/owner/repo/pull/42",
        "github_repo": "owner/repo"
    }
)
```

---

### 2. Feature Dev Node Enhancement

**File**: `agent_orchestrator/graph.py` - `feature_dev_node()`

**Risk Assessment Logic**:

```python
# Assess risk for code changes
risk_context = {
    "operation": "code_modification",
    "environment": state.get("environment", "production"),
    "description": state.get("pending_operation", "Code implementation"),
    "files_changed": state.get("files_changed", 0),
    "agent_name": "feature-dev"
}

risk_level = risk_assessor.assess_task(risk_context)
requires_approval = risk_assessor.requires_approval(risk_level)
```

**Conditional Routing**:

- **High Risk** → Routes to `approval` node with `requires_approval: True`
- **Low Risk** → Routes to `supervisor` node with `requires_approval: False`

**State Updates**:

- Sets `next_agent: "approval"` for high-risk operations
- Preserves `pr_context` in state for downstream nodes
- Includes `risk_level` in `task_result` for observability

---

### 3. Infrastructure Node Enhancement

**File**: `agent_orchestrator/graph.py` - `infrastructure_node()`

**Risk Assessment Logic**:

```python
# Assess risk for infrastructure changes
risk_context = {
    "operation": "infrastructure_modification",
    "environment": state.get("environment", "production"),
    "description": state.get("pending_operation", "Infrastructure change"),
    "resource_type": "infrastructure",
    "agent_name": "infrastructure"
}
```

**Triggers Approval For**:

- Production infrastructure deployments
- Terraform/IaC changes to critical resources
- Docker Compose configuration updates
- Cloud resource modifications

---

### 4. CI/CD Node Enhancement

**File**: `agent_orchestrator/graph.py` - `cicd_node()`

**Risk Assessment Logic**:

```python
# Assess risk for deployments
risk_context = {
    "operation": "deploy",
    "environment": state.get("environment", "production"),
    "description": state.get("pending_operation", "Deployment"),
    "resource_type": "deployment",
    "agent_name": "cicd"
}
```

**Triggers Approval For**:

- Production deployments
- Pipeline modifications affecting production
- GitHub Actions workflow changes
- Critical service deployments

**PR Context Extraction**:

- CI/CD node is the primary handler for PR deployments
- Extracts `pr_number`, `pr_url`, `github_repo` from state
- Passes PR context to approval node for GitHub comment integration

---

### 5. Approval Node PR Context Support

**File**: `agent_orchestrator/graph.py` - `approval_node()`

**Enhanced to Accept PR Context**:

```python
# Extract PR context if available (Phase 3 enhancement)
pr_context = state.get("pr_context", {})
pr_number = pr_context.get("pr_number")
pr_url = pr_context.get("pr_url")
github_repo = pr_context.get("github_repo")

request_id = await hitl_manager.create_approval_request(
    workflow_id=state.get("workflow_id", str(uuid.uuid4())),
    thread_id=state.get("thread_id", ""),
    checkpoint_id=f"checkpoint-{uuid.uuid4()}",
    task=risk_context,
    agent_name=state.get("current_agent", "orchestrator"),
    pr_number=pr_number,      # Phase 3
    pr_url=pr_url,            # Phase 3
    github_repo=github_repo,  # Phase 3
)
```

**Benefits**:

- Approval requests automatically include PR details
- GitHub PR receives confirmation comment on approval (Phase 2)
- Linear issue includes link to PR for context

---

### 6. Conditional Routing Logic

**File**: `agent_orchestrator/graph.py` - `create_workflow()`

**Added Conditional Edges**:

```python
def route_from_agent(state: WorkflowState) -> str:
    """Route from agent node based on requires_approval flag."""
    if state.get("requires_approval", False):
        return "approval"
    return "supervisor"

# Conditional routing for agents that can trigger approval
workflow.add_conditional_edges(
    "feature-dev",
    route_from_agent,
    {"approval": "approval", "supervisor": "supervisor"},
)
workflow.add_conditional_edges(
    "infrastructure",
    route_from_agent,
    {"approval": "approval", "supervisor": "supervisor"},
)
workflow.add_conditional_edges(
    "cicd",
    route_from_agent,
    {"approval": "approval", "supervisor": "supervisor"},
)
```

**Previous Behavior**: All agents had fixed edges back to supervisor

**New Behavior**: Agents can dynamically route to approval or supervisor based on risk

---

### 7. Workflow Template Update

**File**: `agent_orchestrator/workflows/templates/pr-deployment.workflow.yaml`

**Enhanced Approval Gate**:

```yaml
- id: "approval_gate"
  type: "hitl_approval"
  deterministic: true
  # Phase 3: Include PR context for GitHub comment integration
  pr_context:
    pr_number: "{{ context.pr_number }}"
    pr_url: "{{ context.pr_url }}"
    github_repo: "{{ context.github_repo }}"
  risk_assessment:
    type: "llm_assessment"
    prompt: |
      Deployment ready for production:
      - Review score: {{ outputs.code_review.quality_score }}
      - Tests passed: {{ outputs.run_tests.passed }}/{{ outputs.run_tests.total }}
      - Staging URL: {{ outputs.deploy_staging.url }}
      - PR: {{ context.pr_url }}

  on_approved: "deploy_production"
  on_rejected: "notify_failure"
```

**Template Variables**:

- `context.pr_number` - GitHub PR number
- `context.pr_url` - Full URL to PR
- `context.github_repo` - Repository in `owner/repo` format

---

### 8. Test Infrastructure

**File**: `support/tests/integration/test_phase3_agent_hitl.py`

**Test Coverage**:

1. **Feature Dev Risk Assessment** - Validates high-risk code changes trigger approval
2. **Infrastructure Risk Assessment** - Validates production IaC changes trigger approval
3. **CI/CD Risk Assessment** - Validates production deployments trigger approval
4. **Approval Node PR Context** - Validates PR context is passed to HITLManager
5. **Low-Risk Bypass** - Validates development changes skip approval

**Test Execution**:

```bash
cd support/tests/integration
python test_phase3_agent_hitl.py
```

**Expected Output**:

```
====================
TEST SUMMARY: 5 passed, 0 failed
✅ All Phase 3 agent HITL integration tests passed!
```

---

## Architecture Changes

### Workflow Flow (Before Phase 3)

```
User Request → Supervisor → Agent Node → Supervisor → ...
                   ↓
             approval (if supervisor detects high-risk)
```

### Workflow Flow (After Phase 3)

```
User Request → Supervisor → Agent Node
                               ↓
                         [Risk Assessment]
                         /              \
                    High Risk       Low Risk
                        ↓               ↓
                   approval         supervisor
                        ↓
                  [HITL Approval]
                        ↓
                  [Linear Issue]
                        ↓
                 [Human Approval]
                        ↓
                 [Linear Webhook]
                        ↓
              [GitHub PR Comment]
                        ↓
             [Workflow Resumes] → supervisor
```

**Key Improvements**:

- **Defense in Depth**: Agents assess risk independently of supervisor
- **Faster Routing**: No round-trip to supervisor for obvious high-risk ops
- **Better Context**: Agents provide operation-specific risk context
- **PR Integration**: PR context flows automatically from agent to approval

---

## Integration Points

### Example: PR Deployment Flow

```python
# 1. GitHub webhook triggers workflow with PR context
workflow_state = {
    "messages": [HumanMessage(content="Deploy PR #123")],
    "pr_context": {
        "pr_number": 123,
        "pr_url": "https://github.com/owner/repo/pull/123",
        "github_repo": "owner/repo"
    },
    "environment": "production"
}

# 2. Supervisor routes to CI/CD agent
# 3. CI/CD agent performs deployment preparation
# 4. CI/CD agent assesses risk (production deployment = high risk)
# 5. CI/CD agent routes to approval node with PR context
# 6. Approval node creates Linear issue with PR link
# 7. Human approves in Linear (👍 reaction)
# 8. Linear webhook fires
# 9. GitHub PR receives approval comment
# 10. Workflow resumes and completes deployment
```

### Example: Low-Risk Development Change

```python
# 1. Developer requests code change
workflow_state = {
    "messages": [HumanMessage(content="Add logging to utils")],
    "environment": "development",
    "files_changed": 1
}

# 2. Supervisor routes to Feature Dev agent
# 3. Feature Dev agent implements changes
# 4. Feature Dev agent assesses risk (dev + small change = low risk)
# 5. Feature Dev agent routes directly to supervisor (no approval)
# 6. Workflow continues without human intervention
```

---

## Risk Assessment Criteria

### High-Risk Operations (Trigger Approval)

**Feature Dev**:

- Production code changes
- Authentication/security modifications
- Database schema changes
- > 10 files modified

**Infrastructure**:

- Production infrastructure deployments
- VPC/network configuration changes
- Database infrastructure changes
- Terraform state modifications

**CI/CD**:

- Production deployments
- Pipeline changes affecting production
- Critical service deployments (orchestrator, database)

### Low-Risk Operations (Bypass Approval)

- Development environment changes
- Documentation updates
- Code comments/formatting
- Staging deployments
- Single-file minor changes

---

## Configuration

### Environment Variables

No new environment variables required - Phase 3 uses existing configuration from Phase 1 & 2.

### Risk Assessment Rules

**File**: `config/hitl/risk-assessment-rules.yaml`

Already configured in Phase 1:

```yaml
high_risk:
  operations:
    - deploy
    - delete
    - modify_infrastructure
  environments:
    - production
  resources:
    - database
    - authentication
    - payment_processing
```

---

## Observability

### Metrics

**New Metrics** (added to Prometheus):

- `agent_risk_assessment_total{agent, risk_level}` - Risk assessments by agent
- `agent_approval_triggers_total{agent}` - Approvals triggered by each agent
- `agent_approval_bypasses_total{agent}` - Low-risk operations that bypassed approval

### Logging

**New Log Entries**:

```
[feature-dev] Risk assessment: code_modification in production = high (approval=required)
[feature-dev] High-risk code changes detected (high), routing to approval
[feature-dev] Risk factors: production_environment, security_related
```

### LangSmith Traces

**Trace Metadata**:

- `risk_level` - Assessed risk level for operation
- `requires_approval` - Whether approval was triggered
- `pr_number` - PR number if applicable
- `approval_request_id` - UUID of approval request created

---

## Testing

### Unit Tests

All agent risk assessment logic is unit-testable:

```python
async def test_feature_dev_high_risk():
    """Test that feature_dev triggers approval for production changes."""
    state = {
        "messages": [...],
        "environment": "production",
        "files_changed": 5
    }

    result = await feature_dev_node(state)

    assert result["next_agent"] == "approval"
    assert result["requires_approval"] is True
```

### Integration Tests

End-to-end workflow tests with actual database:

```bash
# Run Phase 3 integration tests
python support/tests/integration/test_phase3_agent_hitl.py
```

### Manual Testing

```bash
# 1. Start orchestrator
docker compose up -d orchestrator

# 2. Trigger high-risk operation
curl -X POST http://localhost:8001/execute \
  -d '{
    "message": "Deploy to production",
    "environment": "production",
    "pr_number": 123
  }'

# 3. Verify Linear issue created
# 4. Approve in Linear (👍 reaction)
# 5. Verify GitHub PR comment posted
# 6. Verify workflow resumes
```

---

## Rollback Plan

If issues arise:

### Code Rollback

```bash
# Revert graph.py changes
git checkout HEAD~6 agent_orchestrator/graph.py

# Revert base_agent.py changes
git checkout HEAD~7 agent_orchestrator/agents/_shared/base_agent.py
```

### Feature Toggle

Set environment variable to disable agent risk assessment:

```bash
export DISABLE_AGENT_RISK_ASSESSMENT=true
```

Then modify agent nodes to check this flag before performing assessment.

### Workflow Fallback

Update workflow templates to remove `pr_context` fields if GitHub integration causes issues.

---

## Success Metrics

Phase 3 successfully delivers:

- ✅ Risk assessment helper in BaseAgent (reusable across agents)
- ✅ Feature Dev agent routes to approval for high-risk code changes
- ✅ Infrastructure agent routes to approval for production deployments
- ✅ CI/CD agent routes to approval for production pipelines
- ✅ Approval node accepts PR context from agent state
- ✅ Conditional routing enables dynamic approval flow
- ✅ Workflow templates updated with PR context fields
- ✅ Comprehensive test suite validates all scenarios

**All acceptance criteria met. Phase 3 complete.**

---

## Next Steps: Phase 4 (Observability)

Phase 4 will add comprehensive observability for HITL approvals:

1. **Prometheus Metrics**:

   - Approval latency by risk level
   - Approval backlog dashboard
   - Agent-specific approval rates
   - Timeout/expiration tracking

2. **LangSmith Integration**:

   - Dedicated traces for approval events
   - Risk assessment decision logging
   - Approval outcome correlation

3. **Grafana Dashboards**:

   - Real-time approval queue
   - Historical approval trends
   - Risk distribution by agent
   - SLA compliance tracking

4. **Alerting**:
   - Stuck approvals (>24h pending)
   - High approval backlog (>10 pending)
   - Critical operations pending approval
   - Approval webhook failures

**Estimated Effort**: 1 day

---

## Documentation Links

- [Phase 1 Implementation](HITL-IMPLEMENTATION-COMPLETE.md) - Core integration
- [Phase 2 Implementation](PHASE-2-IMPLEMENTATION-SUMMARY.md) - GitHub PR integration
- [Risk Assessor](../../shared/lib/risk_assessor.py) - Risk assessment logic
- [LangGraph Workflow](../../agent_orchestrator/graph.py) - Workflow definition
- [Test Suite](../../support/tests/integration/test_phase3_agent_hitl.py) - Phase 3 tests

---

**Questions?** File an issue in [Linear](https://linear.app/dev-ops/project/codechef-78b3b839d36b) with label `hitl-phase3`.
