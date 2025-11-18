# Phase 2: Human-in-the-Loop (HITL) Integration - Action Plan

**Sprint Duration**: 1-2 weeks  
**Start Date**: November 18, 2025  
**Project**: AI DevOps Agent Platform

---

## 🎯 SPRINT GOAL

Implement approval gates for high-risk autonomous operations using LangGraph interrupts and PostgreSQL checkpointing.

**Success Criteria**:

- ✅ Workflows can pause for human approval
- ✅ Orchestrator can resume workflows after approval
- ✅ Taskfile commands for approval management
- ✅ Risk assessment logic integrated in agents

---

## 📋 TASK BREAKDOWN

### Task 2.1: Interrupt Configuration (Week 1)

#### Day 1-2: Design & Architecture

**Objectives**:

1. Define interrupt trigger conditions
2. Design risk assessment schema
3. Plan PostgreSQL checkpoint schema extensions
4. Document approval workflow state machine

**Deliverables**:

```
config/hitl/
├── risk-assessment-rules.yaml      # Risk level definitions
├── interrupt-triggers.yaml          # When to interrupt
└── approval-policies.yaml           # Who can approve what

shared/lib/
├── risk_assessor.py                 # Risk assessment logic
└── hitl_manager.py                  # HITL workflow orchestration

shared/services/langgraph/src/
└── interrupt_nodes.py               # LangGraph interrupt node implementations
```

**Risk Assessment Schema**:

```yaml
risk_levels:
  low:
    auto_approve: true
    notify: false
  medium:
    auto_approve: false
    notify: true
    approvers: ["team_lead"]
  high:
    auto_approve: false
    notify: true
    approvers: ["team_lead", "tech_lead"]
    escalate_after: 30m
  critical:
    auto_approve: false
    notify: true
    approvers: ["tech_lead", "cto"]
    escalate_after: 15m
    require_justification: true

triggers:
  delete_production: "critical"
  deploy_production: "high"
  modify_infrastructure: "high"
  security_finding_critical: "critical"
  security_finding_high: "high"
  cost_above_threshold: "medium"
  data_export: "high"
```

**State Machine**:

```
[Task Submitted]
    → [Risk Assessment]
        → Low Risk → [Auto Execute]
        → Medium/High/Critical → [Interrupt for Approval]
            → [Pending Approval]
                → Approved → [Resume Execution]
                → Rejected → [Cancelled]
                → Timeout → [Escalate]
```

**Action Items**:

- [ ] Create config files in `config/hitl/`
- [ ] Design database schema for approvals table
- [ ] Document state transitions
- [ ] Review with team

---

#### Day 3-4: Implementation

**Part A: Risk Assessor Module**

File: `shared/lib/risk_assessor.py`

```python
"""
Risk assessment for autonomous operations.
Determines whether tasks require human approval.
"""
from typing import Dict, Literal
import yaml
import logging

logger = logging.getLogger(__name__)

RiskLevel = Literal["low", "medium", "high", "critical"]

class RiskAssessor:
    def __init__(self, config_path: str = "config/hitl/risk-assessment-rules.yaml"):
        with open(config_path) as f:
            self.rules = yaml.safe_load(f)

    def assess_task(self, task: Dict) -> RiskLevel:
        """
        Assess risk level of a task based on:
        - Operation type (delete, deploy, modify)
        - Target environment (production, staging, dev)
        - Resource type (database, infrastructure, code)
        - Security findings
        - Cost estimates
        """
        # Check explicit triggers
        operation = task.get("operation")
        environment = task.get("environment")

        # Critical triggers
        if operation == "delete" and environment == "production":
            return "critical"

        if operation == "deploy" and environment == "production":
            return "high"

        # Security findings
        security_findings = task.get("security_findings", [])
        if any(f["severity"] == "critical" for f in security_findings):
            return "critical"
        if any(f["severity"] == "high" for f in security_findings):
            return "high"

        # Cost threshold
        estimated_cost = task.get("estimated_cost", 0)
        if estimated_cost > 1000:
            return "high"
        if estimated_cost > 100:
            return "medium"

        # Default to low risk
        return "low"

    def requires_approval(self, risk_level: RiskLevel) -> bool:
        """Check if risk level requires approval"""
        return not self.rules["risk_levels"][risk_level]["auto_approve"]

    def get_approvers(self, risk_level: RiskLevel) -> list:
        """Get list of roles that can approve this risk level"""
        return self.rules["risk_levels"][risk_level].get("approvers", [])
```

**Action Items**:

- [ ] Implement `risk_assessor.py`
- [ ] Add unit tests in `support/tests/test_risk_assessor.py`
- [ ] Add to orchestrator imports

---

**Part B: HITL Manager Module**

File: `shared/lib/hitl_manager.py`

```python
"""
Human-in-the-Loop workflow management.
Handles approval requests, notifications, and workflow resumption.
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ApprovalRequest:
    workflow_id: str
    task_id: str
    risk_level: str
    description: str
    requested_by: str
    requested_at: datetime
    approvers: list
    timeout_minutes: int
    metadata: Dict

class HITLManager:
    def __init__(self, db_connection):
        self.db = db_connection

    async def request_approval(
        self,
        workflow_id: str,
        task_id: str,
        risk_level: str,
        description: str,
        approvers: list,
        timeout_minutes: int = 30,
        metadata: Optional[Dict] = None
    ) -> ApprovalRequest:
        """
        Create approval request and store in database.
        Sends notifications to required approvers.
        """
        request = ApprovalRequest(
            workflow_id=workflow_id,
            task_id=task_id,
            risk_level=risk_level,
            description=description,
            requested_by="orchestrator",
            requested_at=datetime.now(),
            approvers=approvers,
            timeout_minutes=timeout_minutes,
            metadata=metadata or {}
        )

        # Store in database
        await self._store_approval_request(request)

        # Send notifications (Linear, email, etc.)
        await self._notify_approvers(request)

        logger.info(f"Approval request created: {workflow_id} (risk: {risk_level})")
        return request

    async def approve_workflow(
        self,
        workflow_id: str,
        approved_by: str,
        justification: Optional[str] = None
    ) -> bool:
        """Approve workflow and trigger resumption"""
        # Update database
        await self._update_approval_status(workflow_id, "approved", approved_by, justification)

        # Resume workflow via LangGraph checkpointer
        # This will be handled by orchestrator endpoint

        logger.info(f"Workflow {workflow_id} approved by {approved_by}")
        return True

    async def reject_workflow(
        self,
        workflow_id: str,
        rejected_by: str,
        reason: str
    ) -> bool:
        """Reject workflow and cancel execution"""
        await self._update_approval_status(workflow_id, "rejected", rejected_by, reason)
        logger.info(f"Workflow {workflow_id} rejected by {rejected_by}")
        return True

    async def list_pending(self) -> list:
        """List all workflows awaiting approval"""
        query = """
            SELECT workflow_id, task_id, risk_level, description, requested_at, approvers
            FROM approval_requests
            WHERE status = 'pending'
            ORDER BY requested_at DESC
        """
        return await self.db.fetch(query)

    async def _store_approval_request(self, request: ApprovalRequest):
        """Store approval request in PostgreSQL"""
        query = """
            INSERT INTO approval_requests
            (workflow_id, task_id, risk_level, description, requested_by, requested_at, approvers, timeout_at, metadata, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'pending')
        """
        timeout_at = request.requested_at + timedelta(minutes=request.timeout_minutes)
        await self.db.execute(
            query,
            request.workflow_id,
            request.task_id,
            request.risk_level,
            request.description,
            request.requested_by,
            request.requested_at,
            request.approvers,
            timeout_at,
            request.metadata
        )

    async def _update_approval_status(self, workflow_id: str, status: str, actor: str, note: str):
        """Update approval status"""
        query = """
            UPDATE approval_requests
            SET status = $1, resolved_by = $2, resolved_at = $3, resolution_note = $4
            WHERE workflow_id = $5 AND status = 'pending'
        """
        await self.db.execute(query, status, actor, datetime.now(), note, workflow_id)

    async def _notify_approvers(self, request: ApprovalRequest):
        """Send notifications to approvers (Linear, Slack, email)"""
        # TODO: Implement notification logic
        # - Create Linear issue
        # - Send Slack message
        # - Send email
        pass
```

**Action Items**:

- [ ] Implement `hitl_manager.py`
- [ ] Create PostgreSQL schema: `config/state/approval_requests.sql`
- [ ] Add database migration script
- [ ] Integrate with orchestrator

---

**Part C: LangGraph Interrupt Nodes**

File: `shared/services/langgraph/src/interrupt_nodes.py`

```python
"""
LangGraph interrupt node implementations for HITL workflows.
"""
from langgraph.graph import StateGraph
from typing import TypedDict, Literal

class WorkflowState(TypedDict):
    task_id: str
    risk_level: Literal["low", "medium", "high", "critical"]
    requires_approval: bool
    approval_status: Literal["pending", "approved", "rejected"]
    execution_result: dict

def assess_risk_node(state: WorkflowState) -> WorkflowState:
    """Assess task risk and determine if approval needed"""
    from shared.lib.risk_assessor import RiskAssessor

    assessor = RiskAssessor()
    risk_level = assessor.assess_task(state)
    requires_approval = assessor.requires_approval(risk_level)

    return {
        **state,
        "risk_level": risk_level,
        "requires_approval": requires_approval,
        "approval_status": "pending" if requires_approval else "approved"
    }

def request_approval_node(state: WorkflowState) -> WorkflowState:
    """Request human approval and interrupt workflow"""
    from shared.lib.hitl_manager import HITLManager

    # This node will cause workflow to interrupt
    # Workflow will resume when approval is granted

    manager = HITLManager(db_connection)  # Get from context
    approval_request = await manager.request_approval(
        workflow_id=state["workflow_id"],
        task_id=state["task_id"],
        risk_level=state["risk_level"],
        description=state.get("description"),
        approvers=["team_lead", "tech_lead"]
    )

    return {
        **state,
        "approval_request_id": approval_request.workflow_id,
        "approval_status": "pending"
    }

def build_hitl_workflow():
    """Build LangGraph workflow with HITL interrupts"""
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("assess_risk", assess_risk_node)
    workflow.add_node("request_approval", request_approval_node)
    workflow.add_node("execute_task", execute_task_node)

    # Add edges with conditional routing
    workflow.add_conditional_edges(
        "assess_risk",
        lambda state: "request_approval" if state["requires_approval"] else "execute_task"
    )

    # Interrupt point - workflow pauses here until approval
    workflow.add_edge("request_approval", "__interrupt__")

    # After interrupt, check approval status
    workflow.add_conditional_edges(
        "__interrupt__",
        lambda state: "execute_task" if state["approval_status"] == "approved" else "__end__"
    )

    workflow.add_edge("execute_task", "__end__")

    workflow.set_entry_point("assess_risk")

    return workflow.compile()
```

**Action Items**:

- [ ] Implement interrupt nodes
- [ ] Test interrupt/resume cycle
- [ ] Document workflow configuration
- [ ] Add examples to `support/docs/`

---

#### Day 5: Testing & Integration

**Test Cases**:

1. **Low Risk Task** - Auto-executes without approval
2. **High Risk Task** - Interrupts and waits for approval
3. **Approval Flow** - Approve via API and verify resumption
4. **Rejection Flow** - Reject via API and verify cancellation
5. **Timeout Flow** - Wait for timeout and verify escalation

**Integration Points**:

- Orchestrator `/orchestrate` endpoint
- PostgreSQL checkpointer
- Risk assessor in task decomposition
- HITL manager in workflow execution

**Action Items**:

- [ ] Write integration tests in `support/tests/test_hitl_integration.py`
- [ ] Test with real workflow scenarios
- [ ] Document test results
- [ ] Fix bugs and edge cases

---

### Task 2.2: Taskfile Commands (Week 2)

#### Day 1-2: Taskfile Commands

**Add to `Taskfile.yml`**:

```yaml
#============================================================================
# HUMAN-IN-THE-LOOP WORKFLOWS
#============================================================================

workflow:list-pending:
  desc: List workflows awaiting approval
  summary: |
    Shows all workflows that are currently paused and awaiting human
    approval. Displays risk level, task description, and requester.
  cmds:
    - '{{if eq OS "windows"}}pwsh -File ./support/scripts/workflow/list-pending.ps1{{else}}bash ./support/scripts/workflow/list-pending.sh{{end}}'

workflow:approve:
  desc: Approve pending workflow
  summary: |
    Approves a workflow and allows it to continue execution.
    Usage: task workflow:approve WORKFLOW_ID=<id> [JUSTIFICATION="reason"]
  requires:
    vars: [WORKFLOW_ID]
  cmds:
    - '{{if eq OS "windows"}}pwsh -File ./support/scripts/workflow/approve.ps1 -WorkflowId {{.WORKFLOW_ID}} -Justification "{{.JUSTIFICATION}}"{{else}}bash ./support/scripts/workflow/approve.sh {{.WORKFLOW_ID}} "{{.JUSTIFICATION}}"{{end}}'

workflow:reject:
  desc: Reject pending workflow
  summary: |
    Rejects a workflow and cancels its execution.
    Usage: task workflow:reject WORKFLOW_ID=<id> REASON="explanation"
  requires:
    vars: [WORKFLOW_ID, REASON]
  cmds:
    - '{{if eq OS "windows"}}pwsh -File ./support/scripts/workflow/reject.ps1 -WorkflowId {{.WORKFLOW_ID}} -Reason "{{.REASON}}"{{else}}bash ./support/scripts/workflow/reject.sh {{.WORKFLOW_ID}} "{{.REASON}}"{{end}}'

workflow:status:
  desc: Get workflow status and approval details
  summary: |
    Shows detailed status of a workflow including approval state,
    risk level, and execution history.
    Usage: task workflow:status WORKFLOW_ID=<id>
  requires:
    vars: [WORKFLOW_ID]
  cmds:
    - '{{if eq OS "windows"}}pwsh -File ./support/scripts/workflow/status.ps1 -WorkflowId {{.WORKFLOW_ID}}{{else}}bash ./support/scripts/workflow/status.sh {{.WORKFLOW_ID}}{{end}}'
```

**Action Items**:

- [ ] Add commands to Taskfile.yml
- [ ] Test command syntax and validation
- [ ] Verify error handling

---

#### Day 3-4: PowerShell Scripts

**File: `support/scripts/workflow/list-pending.ps1`**

```powershell
# List workflows awaiting approval
param(
    [switch]$Remote
)

$orchestratorUrl = if ($Remote) { "http://45.55.173.72:8001" } else { "http://localhost:8001" }

Write-Host "`nFetching pending workflows..." -ForegroundColor Cyan

try {
    $workflows = Invoke-RestMethod -Uri "$orchestratorUrl/workflows/pending" -Method Get

    if ($workflows.Count -eq 0) {
        Write-Host "No workflows pending approval" -ForegroundColor Green
        exit 0
    }

    Write-Host "`nPending Workflows ($($workflows.Count)):`n" -ForegroundColor Yellow

    foreach ($workflow in $workflows) {
        $riskColor = switch ($workflow.risk_level) {
            "critical" { "Red" }
            "high" { "Yellow" }
            "medium" { "Blue" }
            default { "Gray" }
        }

        Write-Host "  ID: $($workflow.workflow_id)" -ForegroundColor White
        Write-Host "  Risk: $($workflow.risk_level)" -ForegroundColor $riskColor
        Write-Host "  Task: $($workflow.description)" -ForegroundColor Gray
        Write-Host "  Requested: $($workflow.requested_at)" -ForegroundColor Gray
        Write-Host "  Approvers: $($workflow.approvers -join ', ')" -ForegroundColor Gray
        Write-Host ""
    }

} catch {
    Write-Host "Error fetching workflows: $_" -ForegroundColor Red
    exit 1
}
```

**File: `support/scripts/workflow/approve.ps1`**

```powershell
# Approve workflow
param(
    [Parameter(Mandatory=$true)]
    [string]$WorkflowId,

    [string]$Justification = "",
    [switch]$Remote
)

$orchestratorUrl = if ($Remote) { "http://45.55.173.72:8001" } else { "http://localhost:8001" }

Write-Host "Approving workflow: $WorkflowId" -ForegroundColor Cyan

$body = @{
    approved_by = $env:USERNAME
    justification = $Justification
} | ConvertTo-Json

try {
    $result = Invoke-RestMethod -Uri "$orchestratorUrl/workflows/$WorkflowId/approve" -Method Post -Body $body -ContentType "application/json"

    Write-Host "✅ Workflow approved successfully" -ForegroundColor Green
    Write-Host "   Status: $($result.status)" -ForegroundColor Gray
    Write-Host "   Approved by: $($result.approved_by)" -ForegroundColor Gray

} catch {
    Write-Host "❌ Failed to approve workflow: $_" -ForegroundColor Red
    exit 1
}
```

**Action Items**:

- [ ] Create PowerShell scripts for all 4 commands
- [ ] Add error handling and validation
- [ ] Test on Windows and Linux (if applicable)
- [ ] Add help documentation

---

#### Day 5: API Endpoints & Testing

**Add to `agent_orchestrator/main.py`**:

```python
@app.get("/workflows/pending")
async def list_pending_workflows():
    """List all workflows awaiting approval"""
    try:
        pending = await hitl_manager.list_pending()
        return {
            "success": True,
            "workflows": pending
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/workflows/{workflow_id}/approve")
async def approve_workflow(workflow_id: str, request: Dict):
    """Approve workflow and resume execution"""
    approved_by = request.get("approved_by", "unknown")
    justification = request.get("justification")

    try:
        success = await hitl_manager.approve_workflow(
            workflow_id,
            approved_by,
            justification
        )

        # Resume workflow via LangGraph
        # ... implementation ...

        return {
            "success": success,
            "workflow_id": workflow_id,
            "status": "approved",
            "approved_by": approved_by
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/workflows/{workflow_id}/reject")
async def reject_workflow(workflow_id: str, request: Dict):
    """Reject workflow and cancel execution"""
    rejected_by = request.get("rejected_by", "unknown")
    reason = request.get("reason", "No reason provided")

    try:
        success = await hitl_manager.reject_workflow(
            workflow_id,
            rejected_by,
            reason
        )

        return {
            "success": success,
            "workflow_id": workflow_id,
            "status": "rejected",
            "rejected_by": rejected_by
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/workflows/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Get detailed workflow status"""
    try:
        status = await hitl_manager.get_workflow_status(workflow_id)
        return {
            "success": True,
            "workflow": status
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail="Workflow not found")
```

**Action Items**:

- [ ] Implement API endpoints in orchestrator
- [ ] Test endpoints with curl/Postman
- [ ] Write API documentation
- [ ] Integration test end-to-end flow

---

## 📦 DELIVERABLES CHECKLIST

### Code

- [ ] `shared/lib/risk_assessor.py` - Risk assessment module
- [ ] `shared/lib/hitl_manager.py` - HITL workflow manager
- [ ] `shared/services/langgraph/src/interrupt_nodes.py` - LangGraph interrupts
- [ ] `config/hitl/*.yaml` - Configuration files
- [ ] `config/state/approval_requests.sql` - Database schema
- [ ] `support/scripts/workflow/*.ps1` - Taskfile scripts (4 files)
- [ ] API endpoints in `agent_orchestrator/main.py`

### Configuration

- [ ] Update `Taskfile.yml` with workflow commands
- [ ] Database migration script
- [ ] Risk assessment rules
- [ ] Interrupt trigger configurations

### Documentation

- [ ] `support/docs/HITL_INTEGRATION.md` - User guide
- [ ] `support/docs/RISK_ASSESSMENT.md` - Risk levels and policies
- [ ] API documentation for approval endpoints
- [ ] Workflow state machine diagram

### Tests

- [ ] Unit tests for risk assessor
- [ ] Unit tests for HITL manager
- [ ] Integration tests for interrupt flow
- [ ] End-to-end approval workflow tests

---

## 🎬 GETTING STARTED

### Step 1: Create Directory Structure

```bash
mkdir -p config/hitl
mkdir -p support/scripts/workflow
mkdir -p shared/services/langgraph/src
mkdir -p support/tests/hitl
```

### Step 2: Set Up Database Schema

```bash
psql -h localhost -p 5432 -U devtools -d devtools -f config/state/approval_requests.sql
```

### Step 3: Install Dependencies

```bash
# Add to agent_orchestrator/requirements.txt
pyyaml>=6.0
```

### Step 4: Start Development

```bash
# Create feature branch
git checkout -b feature/phase2-hitl-integration

# Begin with Day 1 tasks (design)
```

---

## 🔍 TESTING STRATEGY

### Unit Tests

- Risk assessor with various task scenarios
- HITL manager database operations
- Interrupt node state transitions

### Integration Tests

- Full workflow from submission to approval
- Database persistence across restarts
- Notification delivery

### Manual Tests

- Taskfile commands on both Windows and Linux
- API endpoints via Postman
- Real workflow scenarios

---

## 📊 SUCCESS METRICS

- [ ] 100% of high-risk tasks interrupt for approval
- [ ] Average approval time < 5 minutes
- [ ] Zero production incidents from unauthorized operations
- [ ] All Taskfile commands work on local and remote
- [ ] API response time < 500ms
- [ ] PostgreSQL checkpoint recovery works after restart

---

## 🚨 RISKS & MITIGATION

| Risk                           | Probability | Impact | Mitigation                    |
| ------------------------------ | ----------- | ------ | ----------------------------- |
| PostgreSQL schema conflicts    | Medium      | High   | Test migrations on dev first  |
| LangGraph interrupt timing     | Medium      | Medium | Add timeout handling          |
| Notification delivery failures | Low         | Medium | Queue-based retry mechanism   |
| Approval timeout edge cases    | Medium      | Low    | Comprehensive timeout testing |

---

## 📞 SUPPORT & ESCALATION

**Questions?**

- Review: `.github/copilot-instructions.md`
- Docs: `support/docs/LANGGRAPH_QUICK_REF.md`
- Codebase: `shared/services/langgraph/`

**Blockers?**

- Check LangGraph version: `pip show langgraph`
- Verify PostgreSQL: `docker compose ps postgres`
- Review logs: `docker compose logs orchestrator`

---

## ✅ DEFINITION OF DONE

### Task 2.1 Complete When:

- [ ] Risk assessor passes all unit tests
- [ ] HITL manager integrated with orchestrator
- [ ] Interrupt nodes work in LangGraph workflow
- [ ] Database schema deployed
- [ ] Documentation updated

### Task 2.2 Complete When:

- [ ] All 4 Taskfile commands working
- [ ] PowerShell scripts tested on Windows
- [ ] API endpoints return correct responses
- [ ] End-to-end approval flow validated
- [ ] Linear integration updated (Issues 2.1 and 2.2 marked complete)

### Phase 2 Complete When:

- [ ] Both tasks done
- [ ] Integration tests passing
- [ ] Documentation complete
- [ ] Deployed to droplet
- [ ] Linear project updated to 80% progress
