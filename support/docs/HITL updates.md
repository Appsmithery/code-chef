## 🎯 Linear/GitHub Webhook Integration Strategy for HITL & Multi-Agent Workflows

Based on the code-chef architecture, here's how to **properly integrate** the Linear/GitHub webhook system into your HITL and multi-agent workflows:

---

## 🏗️ Current Architecture (What's Built)

### 1. **HITL Approval Flow** (Already Working)

- **Trigger**: High/Critical risk operations detected by [RiskAssessor](d:\APPS\code-chef\shared\lib\risk_assessor.py)
- **Checkpoint**: LangGraph `interrupt()` saves state via graph.py
- **Storage**: `approval_requests` table in PostgreSQL
- **Resume**: Webhook → `resume_workflow_from_approval()` → workflow continues

### 2. **Webhook Infrastructure** (Partially Implemented)

- ✅ **Endpoint**: main.py
- ✅ **Signature Verification**: HMAC-SHA256 validation
- ✅ **Processor**: [LinearWebhookProcessor](d:\APPS\code-chef\shared\lib\linear_webhook_processor.py) handles emoji reactions
- ⚠️ **GitHub Integration**: Only creates linkback comments (not full bidirectional sync)

---

## 🔗 Integration Points Needed

### **A. Enhance HITLManager → Linear Integration**

**Current Gap**: HITLManager creates approval requests but doesn't automatically create Linear issues.

**Solution**: Modify hitl_manager.py to create Linear issues:

```python
# In HITLManager.create_approval_request() after DB insert:

async def create_approval_request(...) -> str:
    # ... existing code ...

    # NEW: Create Linear issue for tracking
    linear_client = get_linear_client()
    issue = await linear_client.create_issue(
        title=f"[HITL] {task.get('operation', 'Approval Required')}",
        description=self._format_approval_description(request_id, task, risk_level),
        priority=2 if risk_level in ["high", "critical"] else 3,
        labels=["HITL", f"risk-{risk_level}"],
        parent_id=os.getenv("APPROVAL_HUB_ID"),  # DEV-68 or equivalent
    )

    # Store Linear issue ID with approval request
    await cursor.execute(
        "UPDATE approval_requests SET linear_issue_id = %s WHERE id = %s",
        (issue["id"], request_id)
    )

    return request_id
```

---

### **B. Connect Webhook to Approval Resume**

**Current Gap**: Webhook processes events but doesn't trigger workflow resume.

**Solution**: Wire webhook to existing resume logic in main.py:

```python
@app.post("/webhooks/linear")
async def linear_webhook(request: Request):
    # ... existing signature verification ...

    result = await webhook_processor.process_webhook(event)

    if result["action"] == "resume_workflow":
        metadata = result["metadata"]

        # NEW: Look up approval request by Linear issue ID
        async with await hitl_manager._get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT id FROM approval_requests WHERE linear_issue_id = %s AND status = 'pending'",
                    (metadata["issue_id"],)
                )
                row = await cursor.fetchone()

                if row:
                    approval_request_id = row[0]

                    # Resume workflow
                    resume_result = await resume_workflow_from_approval(
                        approval_request_id,
                        action="approved"
                    )

                    return {
                        "status": "workflow_resumed",
                        "approval_request_id": approval_request_id,
                        **resume_result
                    }

    # ... handle other actions ...
```

---

### **C. Add GitHub PR Comment on Approval**

**Enhancement**: When approval happens, post status to GitHub PR.

**Solution**: Extend main.py:

```python
async def resume_workflow_from_approval(approval_request_id: str, action: str = "approved"):
    # ... existing resume logic ...

    # NEW: Post GitHub PR comment if workflow involves a PR
    if "pr_number" in task_context:
        github_client = get_github_client()
        await github_client.create_comment(
            owner="Appsmithery",
            repo="code-chef",
            pr_number=task_context["pr_number"],
            body=f"""✅ **HITL Approval Granted**

Workflow resumed after human approval.
- **Approval ID**: `{approval_request_id}`
- **Risk Level**: {risk_level}
- **Approved by**: {approver_email}

Linear tracking: [{linear_issue_id}]({linear_url})
"""
        )

    return result
```

---

### **D. Multi-Agent Workflow Integration**

**Pattern**: Each agent node can trigger HITL at decision points.

**Example**: In [feature_dev agent](d:\APPS\code-chef\agent_orchestrator\agents\feature_dev\):

```python
# In feature_dev agent execute method:

async def execute(self, state: WorkflowState) -> WorkflowState:
    # ... existing code generation ...

    # Risk assessment for code changes
    risk_context = {
        "operation": "code_modification",
        "files_changed": len(modified_files),
        "lines_added": total_lines_added,
        "environment": "production",
        "agent_name": "feature_dev"
    }

    risk_level = risk_assessor.assess_task(risk_context)

    if risk_assessor.requires_approval(risk_level):
        # Set HITL flag - graph.py approval_node will handle
        return {
            "messages": [AIMessage(content=f"Generated code (risk={risk_level})")],
            "task_result": {"code": generated_code},
            "requires_approval": True,  # Triggers approval_node
            "pending_operation": f"Deploy {len(modified_files)} file changes to production",
            "next_agent": "approval"  # Routes to approval_node
        }

    # Low risk - proceed directly
    return {...}
```

---

### **E. Workflow Engine Integration**

**For declarative YAML workflows** (e.g., pr-deployment.workflow.yaml):

Already implemented! See workflow_engine.py:

```yaml
# In workflow template:
steps:
  - id: review_changes
    type: agent
    agent: code_review

  - id: approval_gate
    type: approval
    requires_approval: true
    on_approved: deploy_production
    on_rejected: notify_failure
    risk_assessment:
      factors:
        - environment: production
        - resource_type: deployment
```

The engine automatically:

1. Creates Linear issue via `_create_approval_issue()`
2. Pauses workflow execution
3. Waits for webhook callback
4. Resumes via main.py

---

## 📋 Implementation Checklist

### **Phase 1: Core Integration** (1-2 days)

- [ ] Add `linear_issue_id` column to `approval_requests` table
- [ ] Update `HITLManager.create_approval_request()` to create Linear issues
- [ ] Wire webhook processor to `resume_workflow_from_approval()`
- [ ] Test end-to-end with sample high-risk operation

### **Phase 2: GitHub Enrichment** (1 day)

- [ ] Add GitHub PR comment posting in resume flow
- [ ] Store `pr_number` in approval request context
- [ ] Test with actual PR deployment workflow

### **Phase 3: Agent Integration** (2-3 days)

- [ ] Add risk assessment to each agent node
- [ ] Implement `requires_approval` flag in agent responses
- [ ] Test routing to approval_node from each agent
- [ ] Validate memory persistence across HITL pause

### **Phase 4: Observability** (1 day)

- [ ] Add LangSmith traces for webhook events
- [ ] Prometheus metrics for approval latency
- [ ] Grafana dashboard for HITL stats
- [ ] Alert on stuck approval requests (>24h pending)

---

## 🧪 Testing Strategy

### **1. Unit Tests**

```python
# test_hitl_linear_integration.py
async def test_approval_creates_linear_issue():
    """Verify approval request creates Linear issue."""
    hitl = HITLManager()
    request_id = await hitl.create_approval_request(...)

    # Check Linear issue created
    linear = get_linear_client()
    issues = await linear.search_issues(f"HITL approval {request_id}")
    assert len(issues) == 1
    assert "HITL" in issues[0].labels

async def test_webhook_resumes_workflow():
    """Verify webhook triggers workflow resume."""
    # Create approval request
    request_id = await hitl.create_approval_request(...)

    # Simulate Linear webhook (emoji reaction)
    webhook_event = {
        "type": "Reaction",
        "action": "create",
        "data": {
            "emoji": "👍",
            "comment": {"body": f"REQUEST_ID={request_id}"}
        }
    }

    result = await linear_webhook(webhook_event)
    assert result["status"] == "workflow_resumed"
```

### **2. Integration Tests**

```bash
# Start orchestrator with test database
docker compose up -d orchestrator

# Trigger high-risk operation
curl -X POST http://localhost:8001/execute \
  -d '{"message": "Deploy to production", "environment": "production"}'

# Should create Linear issue and pause
# Manually approve in Linear UI
# Verify workflow resumes automatically
```

### **3. E2E Test Workflow**

Use the test issue you created (CHEF-270) as template:

1. Trigger operation requiring HITL
2. Verify Linear issue created with proper labels
3. Add 👍 emoji reaction
4. Verify webhook received and processed
5. Check workflow resumed successfully
6. Validate GitHub PR comment added

---

## 🎛️ Configuration Updates

### **Environment Variables**

Add to [.env](d:\APPS\code-chef\config\env\):

```bash
# Linear Webhook Integration
LINEAR_WEBHOOK_SIGNING_SECRET=your_webhook_secret_here
APPROVAL_HUB_ID=your_approval_hub_issue_id  # e.g., CHEF-270

# GitHub Integration
GITHUB_TOKEN=your_github_token
GITHUB_WEBHOOK_SECRET=your_github_webhook_secret
```

### **Webhook Handlers Config**

Update webhook-handlers.yaml to include approval request ID extraction:

```yaml
webhooks:
  - name: hitl_emoji_approval
    event: Reaction
    action: create
    filters:
      - field: emoji
        in: ["👍", "👎"]
      - field: comment.body
        contains: "HITL Approval Required"

    handlers:
      - when:
          emoji: "👍"
        actions:
          - type: extract_approval_id
            pattern: "REQUEST_ID=([a-f0-9-]+)"
          - type: resume_workflow
            endpoint: /webhooks/linear
```

---

## 📊 Metrics to Track

1. **Approval Latency**: Time from request creation to approval
2. **Webhook Success Rate**: % of webhooks processed without error
3. **Resume Time**: Time from webhook to workflow continuation
4. **Approval Backlog**: Number of pending approval requests
5. **Timeout Rate**: % of approval requests that expire

Add to prometheus.yml:

```yaml
# HITL Metrics
- job_name: "hitl_approvals"
  metrics_path: "/metrics"
  static_configs:
    - targets: ["orchestrator:8001"]
  metric_relabel_configs:
    - source_labels: [__name__]
      regex: "(hitl_.*|approval_.*|webhook_.*)"
      action: keep
```

---

## 🚀 Next Steps

1. **Choose integration phase** (recommend starting with Phase 1)
2. **Create Linear issue** for implementation tracking
3. **Branch strategy**: `feature/hitl-linear-webhook-integration`
4. **PR validation**: Use CHEF-270 as test case

Would you like me to:

1. **Implement Phase 1** changes now?
2. **Create the database migration** for `linear_issue_id` column?
3. **Generate comprehensive test suite** for the integration?
4. **Draft the implementation Linear issue** with full technical spec?
