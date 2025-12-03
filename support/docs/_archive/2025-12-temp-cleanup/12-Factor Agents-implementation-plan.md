# **12-Factor Agents Implementation Plan**

## **Phase 1: Prompt Engineering & Context Management**

### Factor 2 & 3: Own Your Prompts + Context Windows

**Current State**: System prompts scattered in YAML files, no version control visibility.

**Recommendation**: Create `.prompt.md` files in agent-centric directories ✅ **COMPLETED**

```
agent_orchestrator/agents/
├── _shared/
│   ├── base_agent.py
│   └── tool_guides/               # Cross-cutting tool documentation
├── supervisor/
│   ├── __init__.py                # Agent implementation
│   ├── system.prompt.md           # Task routing & decomposition
│   ├── tools.yaml                 # Tool access configuration
│   └── workflows/                 # Agent-specific workflows
├── feature_dev/
│   ├── __init__.py
│   ├── system.prompt.md           # Code generation
│   ├── tools.yaml
│   └── workflows/
├── code_review/
│   ├── __init__.py
│   ├── system.prompt.md           # Security/quality analysis
│   ├── tools.yaml
│   └── workflows/
├── infrastructure/
│   ├── __init__.py
│   ├── system.prompt.md           # IaC generation
│   ├── tools.yaml
│   └── workflows/
├── cicd/
│   ├── __init__.py
│   ├── system.prompt.md           # Pipeline automation
│   ├── tools.yaml
│   └── workflows/
└── documentation/
    ├── __init__.py
    ├── system.prompt.md           # Docs generation
    ├── tools.yaml
    └── workflows/
```

**Example: `supervisor.prompt.md`**

````markdown
# Supervisor Agent System Prompt (v1.2)

## Role

You route development tasks to specialized agents using MECE decomposition.

## Context Window Budget: 8K tokens

- Task description: 2K tokens
- Tool descriptions: 3K tokens (progressive disclosure)
- Agent profiles: 1K tokens
- Response: 2K tokens

## Available Agents

- `feature-dev`: Code implementation (Python focus)
- `code-review`: Security/quality analysis
- `infrastructure`: Docker/K8s/Terraform
- `cicd`: GitHub Actions/Jenkins pipelines
- `documentation`: Technical writing

## Routing Rules

1. **Feature requests** → feature-dev (if code changes)
2. **Security concerns** → code-review (always)
3. **Infrastructure changes** → infrastructure (if IaC/containers)
4. **Pipeline updates** → cicd (if CI/CD config)
5. **Documentation needs** → documentation (if docs update)

## Output Format

```json
{
  "next_agent": "feature-dev",
  "requires_approval": false,
  "reasoning": "New feature requires code implementation"
}
```

## Context Compression Rules

- Summarize completed subtasks to <100 words each
- Only include last 3 agent handoffs in context
- Truncate file contents to 500 lines max
````

**Implementation**: ✅ **COMPLETED**

```python
# Updated BaseAgent class (agent_orchestrator/agents/_shared/base_agent.py)

def get_system_prompt(self) -> str:
    """Load system prompt from system.prompt.md in agent directory"""
    # Path structure: agents/{agent_name}/system.prompt.md
    prompt_file = Path(__file__).parent.parent / self.agent_name / "system.prompt.md"

    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")

    # Fallback to YAML config for backward compatibility
    return self.config["agent"].get("system_prompt", "You are a helpful AI assistant.")
```

---

## **Phase 2: Progressive Tool Disclosure with Prompt Files**

### Factor 1 & 4: Natural Language → Tool Calls + Structured Outputs

**Current State**: Progressive disclosure implemented, but tool selection is code-based.

**Recommendation**: Create tool prompt files in shared directory ✅ **COMPLETED**

```
agent_orchestrator/agents/_shared/tool_guides/
├── filesystem-tools.prompt.md     # File operations
├── git-tools.prompt.md            # Version control
├── docker-tools.prompt.md         # Container management
├── linear-tools.prompt.md         # Issue tracking (with project UUIDs)
└── notion-tools.prompt.md         # Documentation
```

**Example: `git-tools.prompt.md`**

````markdown
# Git Tools Usage Guide

## When to Use

- Creating feature branches
- Committing code changes
- Opening pull requests
- Checking repository status

## Available Tools (gitmcp server)

### `create_branch`

```json
{
  "branch_name": "feature/new-feature",
  "base_branch": "main"
}
```

### `commit_changes`

```json
{
  "message": "feat: add authentication endpoint",
  "files": ["src/auth.py", "tests/test_auth.py"]
}
```

### `create_pull_request`

```json
{
  "title": "Add authentication endpoint",
  "description": "Implements JWT-based authentication",
  "base": "main",
  "head": "feature/new-feature"
}
```

## Common Patterns

**Pattern 1: New Feature Workflow**

1. `create_branch` → feature branch
2. Write code (filesystem tools)
3. `commit_changes` → commit
4. `create_pull_request` → open PR

**Pattern 2: Bug Fix Workflow**

1. `create_branch` → bugfix branch
2. Fix code
3. `commit_changes` → commit with "fix:" prefix
4. `create_pull_request` → link to issue
````

**Update Progressive Loader**: ✅ **COMPLETED**

```python
# Updated ProgressiveMCPLoader class (shared/lib/progressive_mcp_loader.py)

def format_tools_with_prompts(self, toolsets: List[ToolSet]) -> str:
    """Format toolsets with usage examples from prompt files"""
    from pathlib import Path

    lines = ["## Available MCP Tools\n"]

    # Map MCP server names to prompt file names
    server_to_prompt = {
        "gitmcp": "git-tools",
        "rust-mcp-filesystem": "filesystem-tools",
        "dockerhub": "docker-tools",
        "linear": "linear-tools",
        "notion": "notion-tools",
    }

    for toolset in toolsets:
        prompt_name = server_to_prompt.get(toolset.server)

        if prompt_name:
            # Load tool usage guide from _shared/tool_guides
            prompt_file = (
                Path(__file__).parent.parent.parent
                / "agent_orchestrator"
                / "agents"
                / "_shared"
                / "tool_guides"
                / f"{prompt_name}.prompt.md"
            )

            if prompt_file.exists():
                lines.append(f"### Server: `{toolset.server}` ({toolset.priority} priority)\n")
                lines.append(prompt_file.read_text(encoding="utf-8"))
                lines.append("")  # Separator
                continue

        # Fallback to basic listing
        lines.append(f"### Server: `{toolset.server}` ({toolset.priority} priority)")
        lines.append(f"**Purpose:** {toolset.rationale}\n")
        lines.append("**Tools:**")
        for tool in toolset.tools:
            lines.append(f"- `{tool}`")
        lines.append("")

    return "\n".join(lines)
```

---

## **Phase 3: Pre-Defined Workflow Templates**

### Factor 8 & 10: Own Your Control Flow + Small Focused Agents

**Current State**: Workflows in workflows are code-heavy.

**Recommendation**: Create declarative workflow templates with LLM decision gates

```
agent_orchestrator/workflows/templates/
├── pr-deployment.workflow.yaml    # Code review → Tests → Deploy
├── hotfix.workflow.yaml           # Fast-track emergency fixes
├── feature.workflow.yaml          # Standard feature development
├── docs-update.workflow.yaml      # Documentation changes
└── infrastructure.workflow.yaml   # IaC changes
```

**Example: `pr-deployment.workflow.yaml`**

```yaml
name: "PR Deployment Workflow"
version: "1.0"
description: "Automated PR review, test, and deployment pipeline"

# Deterministic steps with LLM decision gates at strategic points
steps:
  - id: "code_review"
    type: "agent_call"
    agent: "code-review"
    deterministic: true
    payload:
      pr_number: "{{ context.pr_number }}"
      repo_url: "{{ context.repo_url }}"

    # LLM decision gate: Should we proceed?
    decision_gate:
      type: "llm_assessment"
      prompt: |
        Review results:
        - Security issues: {{ outputs.code_review.security_issues }}
        - Quality score: {{ outputs.code_review.quality_score }}
        - Critical blockers: {{ outputs.code_review.blockers }}

        Should we proceed to testing? Respond with:
        {"decision": "proceed" | "block", "reasoning": "..."}

      on_proceed: "run_tests"
      on_block: "notify_failure"

  - id: "run_tests"
    type: "agent_call"
    agent: "cicd"
    deterministic: true
    payload:
      branch: "{{ context.branch }}"
      test_suites: ["unit", "integration", "e2e"]

    decision_gate:
      type: "deterministic_check"
      condition: "outputs.run_tests.passed >= outputs.run_tests.total * 0.95"
      on_success: "deploy_staging"
      on_failure: "notify_failure"

  - id: "deploy_staging"
    type: "agent_call"
    agent: "infrastructure"
    deterministic: true
    resource_lock: "deployment:staging" # Prevent concurrent deploys
    payload:
      environment: "staging"
      branch: "{{ context.branch }}"

    # No LLM decision - always proceed if successful
    on_success: "approval_gate"

  - id: "approval_gate"
    type: "hitl_approval"
    deterministic: true
    risk_assessment:
      type: "llm_assessment"
      prompt: |
        Deployment ready for production:
        - Review score: {{ outputs.code_review.quality_score }}
        - Tests passed: {{ outputs.run_tests.passed }}/{{ outputs.run_tests.total }}
        - Staging URL: {{ outputs.deploy_staging.url }}

        Assess risk level (low/medium/high) and required approver role.

        Response format:
        {"risk_level": "medium", "approver_role": "tech_lead", "reasoning": "..."}

    # Pause workflow, await approval
    on_approved: "deploy_production"
    on_rejected: "notify_failure"

  - id: "deploy_production"
    type: "agent_call"
    agent: "infrastructure"
    deterministic: true
    resource_lock: "deployment:production"
    payload:
      environment: "production"
      branch: "{{ context.branch }}"

    # LLM health assessment after deploy
    decision_gate:
      type: "llm_assessment"
      prompt: |
        Production deployment metrics:
        - Health check: {{ outputs.deploy_production.health_check }}
        - Error rate: {{ outputs.deploy_production.error_rate }}
        - Response time: {{ outputs.deploy_production.response_time_p95 }}

        Should we rollback? Respond with:
        {"decision": "keep" | "rollback", "reasoning": "..."}

      on_keep: "update_docs"
      on_rollback: "rollback_production"

  - id: "update_docs"
    type: "agent_call"
    agent: "documentation"
    deterministic: true
    payload:
      pr_number: "{{ context.pr_number }}"
      deployment_id: "{{ outputs.deploy_production.deployment_id }}"

    on_success: "workflow_complete"

  - id: "rollback_production"
    type: "agent_call"
    agent: "infrastructure"
    deterministic: true
    payload:
      action: "rollback"
      environment: "production"
      to_version: "{{ context.previous_version }}"

    on_success: "notify_rollback"

# Error handling
error_handling:
  - step: "code_review"
    on_error: "notify_failure"

  - step: "run_tests"
    on_error: "notify_failure"

  - step: "deploy_staging"
    on_error: "notify_failure"

  - step: "deploy_production"
    on_error: "rollback_production"

# Notifications
notifications:
  - trigger: "workflow_complete"
    channels: ["linear", "email"]
    template: "deployment_success"

  - trigger: "notify_failure"
    channels: ["linear", "email", "slack"]
    template: "deployment_failed"

  - trigger: "notify_rollback"
    channels: ["linear", "email", "slack"]
    template: "deployment_rollback"
```

**Workflow Engine Implementation**:

```python
"""Declarative workflow engine with LLM decision gates"""

import yaml
from pathlib import Path
from typing import Dict, Any
from shared.lib.workflow_state import WorkflowStateManager
from shared.lib.resource_lock_manager import ResourceLockManager
from shared.lib.gradient_client import get_gradient_client

class WorkflowEngine:
    """Execute declarative workflows with LLM decision gates"""

    def __init__(self, db_conn_string: str):
        self.state_mgr = WorkflowStateManager(db_conn_string)
        self.lock_mgr = ResourceLockManager(db_conn_string)
        self.llm = get_gradient_client("orchestrator")

    async def load_workflow(self, template_path: str) -> Dict[str, Any]:
        """Load workflow template from YAML"""
        with open(template_path) as f:
            return yaml.safe_load(f)

    async def execute_workflow(
        self,
        workflow_id: str,
        template: Dict[str, Any],
        context: Dict[str, Any]
    ):
        """Execute workflow with LLM decision gates"""

        # Create workflow state
        await self.state_mgr.create_workflow(
            workflow_id=workflow_id,
            workflow_type=template["name"],
            initial_state={"context": context, "outputs": {}},
            participating_agents=self._extract_agents(template)
        )

        # Execute steps
        current_step = template["steps"][0]

        while current_step:
            step_id = current_step["id"]
            step_type = current_step["type"]

            print(f"Executing step: {step_id} ({step_type})")

            # Execute step based on type
            if step_type == "agent_call":
                result = await self._execute_agent_call(
                    workflow_id,
                    current_step,
                    context
                )
            elif step_type == "hitl_approval":
                result = await self._execute_approval_gate(
                    workflow_id,
                    current_step,
                    context
                )
            else:
                raise ValueError(f"Unknown step type: {step_type}")

            # Store outputs
            outputs = await self.state_mgr.get_workflow(workflow_id)
            outputs.state_data["outputs"][step_id] = result

            # Evaluate decision gate (if present)
            if "decision_gate" in current_step:
                next_step_id = await self._evaluate_decision_gate(
                    current_step["decision_gate"],
                    context,
                    outputs.state_data["outputs"]
                )
            else:
                # Deterministic next step
                next_step_id = current_step.get("on_success")

            # Checkpoint
            await self.state_mgr.checkpoint(
                workflow_id,
                step_name=step_id,
                agent_id="workflow-engine",
                data={"result": result, "next_step": next_step_id}
            )

            # Find next step
            if next_step_id == "workflow_complete":
                await self.state_mgr.complete_workflow(workflow_id)
                break

            current_step = self._find_step(template, next_step_id)

    async def _evaluate_decision_gate(
        self,
        gate: Dict[str, Any],
        context: Dict[str, Any],
        outputs: Dict[str, Any]
    ) -> str:
        """Use LLM to make strategic routing decisions"""

        if gate["type"] == "llm_assessment":
            # Render prompt with context and outputs
            prompt = self._render_template(
                gate["prompt"],
                {"context": context, "outputs": outputs}
            )

            # Call LLM for decision
            response = await self.llm.complete_structured(
                prompt=prompt,
                system_prompt="You are a workflow decision engine. Respond only with JSON.",
                temperature=0.3
            )

            decision = response["content"]["decision"]

            # Route based on decision
            if decision == "proceed":
                return gate["on_proceed"]
            elif decision == "block":
                return gate["on_block"]
            elif decision == "keep":
                return gate["on_keep"]
            elif decision == "rollback":
                return gate["on_rollback"]

        elif gate["type"] == "deterministic_check":
            # Evaluate condition (no LLM)
            condition = self._render_template(
                gate["condition"],
                {"context": context, "outputs": outputs}
            )

            if eval(condition):  # Safe in controlled environment
                return gate["on_success"]
            else:
                return gate["on_failure"]

        raise ValueError(f"Unknown decision gate type: {gate['type']}")

    async def _execute_agent_call(
        self,
        workflow_id: str,
        step: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute agent call step"""
        agent = step["agent"]
        payload = self._render_template(step["payload"], {"context": context})

        # Acquire resource lock if needed
        resource_lock = step.get("resource_lock")
        if resource_lock:
            async with self.lock_mgr.lock(
                resource_id=resource_lock,
                agent_id="workflow-engine",
                timeout_seconds=600
            ):
                # Call agent (via orchestrator /execute endpoint)
                result = await self._call_agent(agent, payload)
        else:
            result = await self._call_agent(agent, payload)

        return result

    def _render_template(self, template: Any, vars: Dict[str, Any]) -> Any:
        """Render Jinja2-style template"""
        if isinstance(template, str):
            # Simple variable substitution
            for key, value in vars.items():
                template = template.replace(f"{{{{ {key} }}}}", str(value))
            return template
        elif isinstance(template, dict):
            return {k: self._render_template(v, vars) for k, v in template.items()}
        elif isinstance(template, list):
            return [self._render_template(item, vars) for item in template]
        return template
```

---

## **Phase 4: Task-Based Automation Scripts**

### Factor 11: Trigger from Anywhere

**Current State**: Taskfile.yml exists but lacks workflow orchestration.

**Recommendation**: Enhance Taskfile with workflow triggers

```yaml
# Add these tasks to existing file

  #============================================================================
  # WORKFLOW EXECUTION (12-Factor Agents)
  #============================================================================

  workflow:pr-deploy:
    desc: Execute PR deployment workflow
    summary: |
      Run full PR deployment workflow: review → test → deploy → approve

      Usage:
        task workflow:pr-deploy PR_NUMBER=123 BRANCH=feature/auth
    vars:
      PR_NUMBER: '{{.PR_NUMBER}}'
      BRANCH: '{{.BRANCH}}'
      WORKFLOW_ID: 'pr-deploy-{{.PR_NUMBER}}-{{now | date "20060102-150405"}}'
    cmds:
      - |
        curl -X POST http://localhost:8001/workflow/execute \
          -H "Content-Type: application/json" \
          -d '{
            "workflow_id": "{{.WORKFLOW_ID}}",
            "template": "pr-deployment.workflow.yaml",
            "context": {
              "pr_number": {{.PR_NUMBER}},
              "branch": "{{.BRANCH}}",
              "repo_url": "git@github.com:appsmithery/dev-tools.git"
            }
          }'
      - echo "Workflow started: {{.WORKFLOW_ID}}"
      - echo "Monitor: http://localhost:8001/workflow/status/{{.WORKFLOW_ID}}"

  workflow:hotfix:
    desc: Execute emergency hotfix workflow (fast-track)
    vars:
      BRANCH: '{{.BRANCH}}'
      ISSUE_ID: '{{.ISSUE_ID}}'
    cmds:
      - |
        curl -X POST http://localhost:8001/workflow/execute \
          -H "Content-Type: application/json" \
          -d '{
            "workflow_id": "hotfix-{{.ISSUE_ID}}-{{now | date "20060102-150405"}}",
            "template": "hotfix.workflow.yaml",
            "context": {
              "branch": "{{.BRANCH}}",
              "issue_id": "{{.ISSUE_ID}}",
              "priority": "urgent"
            }
          }'

  workflow:status:
    desc: Check workflow status
    vars:
      WORKFLOW_ID: '{{.WORKFLOW_ID}}'
    cmds:
      - curl -s http://localhost:8001/workflow/status/{{.WORKFLOW_ID}} | jq .

  workflow:list-templates:
    desc: List available workflow templates
    cmds:
      - ls -1 agent_orchestrator/workflows/templates/*.workflow.yaml | xargs -n1 basename

  #============================================================================
  # AGENT PROMPT MANAGEMENT
  #============================================================================

  prompts:validate:
    desc: Validate all agent prompt files
    cmds:
      - |
        for prompt in agent_orchestrator/prompts/*.prompt.md; do
          echo "Validating: $prompt"
          # Check for required sections
          grep -q "## Role" "$prompt" || echo "  ❌ Missing Role section"
          grep -q "## Context Window Budget" "$prompt" || echo "  ❌ Missing Context Budget"
          grep -q "## Output Format" "$prompt" || echo "  ✅ Valid"
        done

  prompts:token-count:
    desc: Estimate token count for agent prompts
    cmds:
      - |
        for prompt in agent_orchestrator/prompts/*.prompt.md; do
          words=$(wc -w < "$prompt")
          tokens=$((words * 4 / 3))  # Rough estimate: 1.33 tokens per word
          echo "$(basename $prompt): ~$tokens tokens"
        done
```

---

## **Phase 5: Stateless Reducers & State Serialization**

### Factor 5 & 6 & 12: Unified State + Pause/Resume + Stateless Reducers

**Current State**: Workflow state in PostgreSQL, but no pure reducer functions.

**Recommendation**: Create stateless workflow reducer functions

```python
"""Stateless workflow reducers for reproducible execution"""

from typing import Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum

class WorkflowAction(str, Enum):
    """Deterministic workflow actions"""
    START_WORKFLOW = "start_workflow"
    COMPLETE_STEP = "complete_step"
    FAIL_STEP = "fail_step"
    APPROVE_GATE = "approve_gate"
    REJECT_GATE = "reject_gate"
    PAUSE_WORKFLOW = "pause_workflow"
    RESUME_WORKFLOW = "resume_workflow"
    ROLLBACK_STEP = "rollback_step"

@dataclass
class WorkflowEvent:
    """Immutable workflow event"""
    action: WorkflowAction
    step_id: str
    data: Dict[str, Any]
    timestamp: str

def workflow_reducer(
    state: Dict[str, Any],
    event: WorkflowEvent
) -> Dict[str, Any]:
    """Pure function: (state, event) → new_state

    This is the SINGLE SOURCE OF TRUTH for workflow state transitions.
    All state changes must go through this reducer for reproducibility.
    """

    # Create new state (never mutate input)
    new_state = {
        **state,
        "events": [*state.get("events", []), event]
    }

    if event.action == WorkflowAction.START_WORKFLOW:
        new_state.update({
            "status": "running",
            "current_step": event.step_id,
            "steps_completed": [],
            "outputs": {}
        })

    elif event.action == WorkflowAction.COMPLETE_STEP:
        new_state.update({
            "steps_completed": [*new_state["steps_completed"], event.step_id],
            "outputs": {
                **new_state["outputs"],
                event.step_id: event.data
            }
        })
        # Update current_step based on workflow template routing
        next_step = event.data.get("next_step")
        if next_step:
            new_state["current_step"] = next_step

    elif event.action == WorkflowAction.FAIL_STEP:
        new_state.update({
            "status": "failed",
            "error": event.data.get("error"),
            "failed_step": event.step_id
        })

    elif event.action == WorkflowAction.APPROVE_GATE:
        new_state.update({
            "approvals": {
                **new_state.get("approvals", {}),
                event.step_id: {
                    "approved": True,
                    "approver": event.data.get("approver"),
                    "timestamp": event.timestamp
                }
            }
        })

    elif event.action == WorkflowAction.REJECT_GATE:
        new_state.update({
            "status": "rejected",
            "rejections": {
                **new_state.get("rejections", {}),
                event.step_id: {
                    "reason": event.data.get("reason"),
                    "rejector": event.data.get("rejector"),
                    "timestamp": event.timestamp
                }
            }
        })

    elif event.action == WorkflowAction.PAUSE_WORKFLOW:
        new_state.update({
            "status": "paused",
            "paused_at": event.timestamp,
            "paused_step": event.step_id
        })

    elif event.action == WorkflowAction.RESUME_WORKFLOW:
        new_state.update({
            "status": "running",
            "resumed_at": event.timestamp
        })

    elif event.action == WorkflowAction.ROLLBACK_STEP:
        # Revert outputs for rolled-back step
        new_outputs = {**new_state["outputs"]}
        new_outputs.pop(event.step_id, None)

        new_state.update({
            "outputs": new_outputs,
            "steps_completed": [
                s for s in new_state["steps_completed"] if s != event.step_id
            ],
            "rollbacks": [
                *new_state.get("rollbacks", []),
                {"step": event.step_id, "reason": event.data.get("reason")}
            ]
        })

    return new_state

def replay_workflow(events: list[WorkflowEvent]) -> Dict[str, Any]:
    """Replay all events to reconstruct workflow state

    This enables:
    - Time-travel debugging
    - Audit logs
    - State recovery after crashes
    """
    state = {"status": "initialized"}

    for event in events:
        state = workflow_reducer(state, event)

    return state
```

**Integration with WorkflowEngine**:

```python
# Update WorkflowEngine class

class WorkflowEngine:
    """Execute workflows with pure reducers"""

    async def execute_workflow(self, workflow_id: str, template: Dict, context: Dict):
        """Execute workflow using pure reducer functions"""

        # Initialize state with reducer
        state = workflow_reducer(
            {},
            WorkflowEvent(
                action=WorkflowAction.START_WORKFLOW,
                step_id=template["steps"][0]["id"],
                data={"context": context},
                timestamp=datetime.utcnow().isoformat()
            )
        )

        # Persist initial state
        await self.state_mgr.create_workflow(
            workflow_id=workflow_id,
            workflow_type=template["name"],
            initial_state=state,
            participating_agents=[]
        )

        # Execute workflow
        while state["status"] == "running":
            current_step = self._find_step(template, state["current_step"])

            # Execute step
            try:
                result = await self._execute_step(workflow_id, current_step, state)

                # Apply COMPLETE_STEP event via reducer
                state = workflow_reducer(
                    state,
                    WorkflowEvent(
                        action=WorkflowAction.COMPLETE_STEP,
                        step_id=current_step["id"],
                        data=result,
                        timestamp=datetime.utcnow().isoformat()
                    )
                )

            except Exception as e:
                # Apply FAIL_STEP event via reducer
                state = workflow_reducer(
                    state,
                    WorkflowEvent(
                        action=WorkflowAction.FAIL_STEP,
                        step_id=current_step["id"],
                        data={"error": str(e)},
                        timestamp=datetime.utcnow().isoformat()
                    )
                )
                break

            # Persist state after every event
            await self.state_mgr.update_state(
                workflow_id,
                updates=state,
                agent_id="workflow-engine"
            )

            # Check if workflow complete
            if state["current_step"] == "workflow_complete":
                break

        return state
```

---

## **Implementation Roadmap**

### Week 1: Prompt Files & Context Management ✅ **COMPLETED** (DEV-171)

- [x] Create agent-centric directory structure `agent_orchestrator/agents/{agent_name}/`
- [x] Create `system.prompt.md` for all 6 agents (supervisor, feature_dev, code_review, infrastructure, cicd, documentation)
- [x] Create `agent_orchestrator/agents/_shared/tool_guides/*.prompt.md` for top 5 tool servers
- [x] Update `BaseAgent.get_system_prompt()` to load from `system.prompt.md` in agent directories
- [x] Update `ProgressiveMCPLoader.format_tools_with_prompts()` to include usage examples from `_shared/tool_guides/`
- [x] Move tool configs to `{agent_name}/tools.yaml` (agent-centric organization)
- [x] Move `base_agent.py` to `agents/_shared/base_agent.py`
- [x] Update all agent imports to use `_shared.base_agent`
- [x] Verified: SupervisorAgent imports successfully

### Week 2: Workflow Templates ✅ **COMPLETED** (DEV-172)

- [x] Create `agent_orchestrator/workflows/templates/pr-deployment.workflow.yaml`
- [x] Create `agent_orchestrator/workflows/templates/hotfix.workflow.yaml`
- [x] Create `agent_orchestrator/workflows/templates/feature.workflow.yaml`
- [x] Create `agent_orchestrator/workflows/templates/docs-update.workflow.yaml`
- [x] Create `agent_orchestrator/workflows/templates/infrastructure.workflow.yaml`
- [x] Implement `WorkflowEngine` with LLM decision gates
- [x] Add workflow execution endpoint: `POST /workflow/execute`
- [x] Add workflow status endpoint: `GET /workflow/status/{id}`
- [x] Add workflow resume endpoint: `POST /workflow/resume/{id}`
- [x] Add workflow templates endpoint: `GET /workflow/templates`

### Week 3: Task Automation ✅ **COMPLETED** (DEV-173)

- [x] Add workflow tasks to Taskfile.yml
- [x] Create `task workflow:pr-deploy`, `task workflow:hotfix`, `task workflow:feature`, `task workflow:infrastructure`
- [x] Add `task workflow:status`, `task workflow:resume`, `task workflow:cancel` (placeholder)
- [x] Add prompt validation: `task prompts:validate`
- [x] Create comprehensive testing script: `support/scripts/workflow/test-workflows.py`
- [x] Create testing documentation: `support/docs/WORKFLOW_TESTING.md`
- [x] Create CLI guide: `support/docs/guides/WORKFLOW_CLI.md`
- [x] Integrate real agent execution via LangGraph
- [x] Implement LLM decision gates with GradientClient
- [x] Connect Linear API for HITL approvals
- [x] Add distributed resource locking with PostgreSQL advisory locks

### Week 4: Stateless Reducers & Event Replay (DEV-174)

**Core Tasks:**

- [ ] Create `shared/lib/workflow_reducer.py` with pure reducer function
- [ ] Create `shared/lib/workflow_events.py` for event types and utilities
- [ ] Create `config/state/workflow_events.sql` for event sourcing schema
- [ ] Update `WorkflowEngine` to use reducer for all state changes
- [ ] Add replay functionality: `replay_workflow(events)`
- [ ] Add audit log endpoint: `GET /workflow/{id}/events`
- [ ] Add time-travel debugging: `GET /workflow/{id}/state-at/{timestamp}`

**Enhanced Tasks (Based on Week 1-3 Progress):**

1. **Event Sourcing Foundation**

   - [ ] Event versioning schema (v1, v2) for backward compatibility
   - [ ] Event serialization/deserialization with JSON schema validation
   - [ ] Event encryption utilities for sensitive approval data

2. **Incremental State Snapshots** (Performance)

   - [ ] Create periodic snapshots every 10 events
   - [ ] Add `GET /workflow/{id}/snapshots` endpoint
   - [ ] Implement snapshot compaction (remove old snapshots after 30 days)
   - [ ] Add `snapshot_frequency` config to workflow YAML templates

3. **Workflow Cancellation** (Complete Week 3 TODO)

   - [ ] Add `WorkflowAction.CANCEL_WORKFLOW` to reducer
   - [ ] Implement cleanup: release locks, mark Linear sub-issues complete, notify agents
   - [ ] Add `DELETE /workflow/{id}` endpoint (soft delete with reason)
   - [ ] Handle cascading cancellation for child workflows
   - [ ] Update `task workflow:cancel` to call DELETE endpoint

4. **Error Recovery & Retry Logic**

   - [ ] Implement `POST /workflow/{id}/retry-from/{step_id}` endpoint
   - [ ] Add automatic retry with exponential backoff
   - [ ] Create error classification: `retriable`, `terminal`, `requires_manual_intervention`
   - [ ] Add `WorkflowAction.RETRY_STEP` with max retry counter (default: 3)
   - [ ] Update `_execute_agent_call()` to use retry logic

5. **Workflow Composition** (Multi-Workflow Orchestration)

   - [ ] Add `CALL_SUBWORKFLOW` step type to YAML schema
   - [ ] Implement parent-child workflow relationships
   - [ ] Add `GET /workflow/{id}/children` endpoint
   - [ ] Support `wait_for_children: true` in workflow templates

6. **Enhanced Observability**

   - [ ] Stream workflow events to LangSmith as separate trace spans
   - [ ] Create Grafana dashboard for event replay metrics
   - [ ] Implement `POST /workflow/{id}/annotate` for operator comments
   - [ ] Create event-based alerting (alert on 3+ consecutive failures)

7. **Workflow Template Versioning**

   - [ ] Embed workflow template version in initial state
   - [ ] Add template compatibility checking on resume
   - [ ] Implement migration functions for template version upgrades
   - [ ] Add `GET /workflow/templates/{name}/versions` endpoint

8. **Testing Infrastructure**

   - [ ] Create `support/tests/unit/test_workflow_reducer.py` with property-based tests
   - [ ] Use `hypothesis` library for random event sequences
   - [ ] Verify reducer idempotency and purity
   - [ ] Add snapshot tests for complex event sequences

9. **Compliance & Audit**

   - [ ] Add tamper-proof event signatures (HMAC-SHA256)
   - [ ] Implement event export: `GET /workflow/{id}/events/export?format=json|csv|pdf`
   - [ ] Add event retention policies (archive events >90 days to S3)
   - [ ] Create audit report template (PDF generation)

10. **Migration Strategy**
    - [ ] Create `support/scripts/migrate_workflow_state_to_events.py`
    - [ ] Implement dual-write mode (old state + new events)
    - [ ] Add shadow read validation
    - [ ] Add feature flag: `USE_EVENT_SOURCING=true`
    - [ ] Gradual rollout: new workflows → paused workflows → full cutover

---

## **Benefits Summary**

| 12-Factor Principle               | Implementation                        | Benefit                                          |
| --------------------------------- | ------------------------------------- | ------------------------------------------------ |
| **Factor 2: Own Your Prompts**    | `.prompt.md` files in version control | Prompt evolution tracked, easy rollback          |
| **Factor 3: Own Context Window**  | Token budgets in prompt files         | No LLM context overflows                         |
| **Factor 4: Tools = JSON**        | Tool prompt files with examples       | Agents learn proper tool usage                   |
| **Factor 8: Own Control Flow**    | Workflow YAML templates               | Deterministic pipelines with strategic LLM gates |
| **Factor 10: Small Agents**       | 6 specialized agents vs 1 giant       | Clear responsibilities, easier debugging         |
| **Factor 12: Stateless Reducers** | Pure `workflow_reducer()` function    | Reproducible execution, time-travel debugging    |

**Key Wins**:

1. **90% deterministic workflows** with LLM decision gates only where flexibility adds value
2. **Version-controlled prompts** make prompt engineering a first-class engineering discipline
3. **Pause/Resume workflows** with serialized state enable human approval gates
4. **Audit logs via event replay** provide full execution history for debugging
5. **Task-based automation** meets devs where they work (CLI, not APIs)
