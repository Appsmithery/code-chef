# Linear Integration - Usage Guidelines

## Overview

This project uses Linear for **two completely separate workflows**:

### 1. **📋 PROJECT ROADMAP MANAGEMENT** (Project-Specific)

**Purpose**: Track project phases, milestones, and feature delivery  
**Access**: Sub-agents update their assigned project; Orchestrator can update any project  
**Update Pattern**: Manual/agent-initiated via `agent-linear-update.py`

**Projects in Project Roadmaps Workspace:**

- **AI DevOps Agent Platform**

  - **URL**: https://linear.app/project-roadmaps/project/ai-devops-agent-platform-78b3b839d36b
  - **Project UUID**: `b21cbaa1-9f09-40f4-b62a-73e0f86dd501`
  - **Project ID (Slug)**: `78b3b839d36b`
  - **Team**: Project Roadmaps (PR)
  - **Team ID**: `f5b610be-ac34-4983-918b-2c9d00aa9b7a`

- **TWKR Agentic Resume Workflow**
  - **URL**: https://linear.app/project-roadmaps/project/twkr-agentic-resume-workflow-30f6ea5be0a6
  - **Project UUID**: `86f8cc40-de06-4e3d-b7c8-ed95193737bc`
  - **Project ID (Slug)**: `30f6ea5be0a6`
  - **Team**: Project Roadmaps (PR)
  - **Team ID**: `f5b610be-ac34-4983-918b-2c9d00aa9b7a`

**Use Cases:**

- Phase completion reports
- Milestone tracking
- Feature documentation
- Sprint planning
- Technical debt tracking

**Primary Script:**

- `support/scripts/agent-linear-update.py` - **PROJECT ROADMAP UPDATES**
  - Accepts `--project-id` and `--team-id` parameters
  - Sub-agents: Must pass their project UUID
  - Orchestrator: Can update any project (defaults to AI DevOps Agent Platform)

**Legacy Scripts:**

- `support/scripts/update-linear-phase6.py` - Phase 6 specific (deprecated)
- `support/scripts/update-linear-graphql.py` - Generic updates (use agent-linear-update.py instead)
- `support/scripts/create-hitl-subtasks.py` - Create subtasks (use agent-linear-update.py instead)

---

### 2. **🚨 HITL APPROVAL NOTIFICATIONS** (Workspace-Level)

**Purpose**: Real-time approval notifications for human-in-the-loop workflows  
**Access**: ALL agents can post to PR-68 via orchestrator event bus  
**Update Pattern**: Automatic via event bus (orchestrator mediates)

- **Issue**: PR-68 (Agent Approvals Hub)
- **URL**: https://linear.app/project-roadmaps/issue/PR-68/agent-approvals-hub
- **Issue ID**: `PR-68`
- **Scope**: Workspace-wide (not project-specific)

**Use Cases:**

- HITL approval requests
- Critical action notifications
- High-risk operation alerts
- Deployment approvals
- Configuration change approvals

**Integration Method:**

- **Orchestrator Event Bus**: `shared/lib/event_bus.py` + `linear_workspace_client.py`
- **Sub-agents**: Emit approval events → Orchestrator posts to PR-68
- **Direct Script**: `support/scripts/update-linear-pr68.py` (manual use only)

**⚠️ CRITICAL: DO NOT confuse these two workflows!**

- **Roadmap updates** → Use `agent-linear-update.py` with `--project-id`
- **Approval requests** → Use orchestrator event bus (automatic) or `update-linear-pr68.py` (manual)

---

## Agent Identification & Traceability

Each agent has a unique workspace identifier for tracking comments and edits:

| Agent          | Workspace Tag           | Display Name      | Signature              |
| -------------- | ----------------------- | ----------------- | ---------------------- |
| Orchestrator   | `@orchestrator-agent`   | 🎯 Orchestrator   | [Orchestrator Agent]   |
| Feature-Dev    | `@feature-dev-agent`    | 🚀 Feature Dev    | [Feature-Dev Agent]    |
| Code-Review    | `@code-review-agent`    | 🔍 Code Review    | [Code-Review Agent]    |
| Infrastructure | `@infrastructure-agent` | 🏗️ Infrastructure | [Infrastructure Agent] |
| CI/CD          | `@cicd-agent`           | ⚙️ CI/CD          | [CI/CD Agent]          |
| Documentation  | `@documentation-agent`  | 📚 Documentation  | [Documentation Agent]  |

**Automatic Tagging:**

When creating issues with `--agent-name`, the script automatically appends:

```markdown
---

_Created by 🚀 Feature Dev [Feature-Dev Agent]_
_Agent Tag: @feature-dev-agent_
```

**Usage:**

```powershell
# Sub-agent creating an issue with traceability
python support/scripts/agent-linear-update.py create-issue `
    --project-id "b21cbaa1-9f09-40f4-b62a-73e0f86dd501" `
    --title "Implement caching layer" `
    --description "Add Redis caching for API responses" `
    --agent-name "feature-dev"  # Adds signature to description
```

---

## When to Use Which

### 📋 Use `agent-linear-update.py` (Roadmap Management) When:

**Agent Type: Sub-Agent (Feature-Dev, Code-Review, Infrastructure, CI/CD, Documentation)**

- ✅ Creating issues/tasks for your assigned project
- ✅ Updating status of issues in your project
- ✅ Breaking down features into sub-tasks
- ✅ Marking tasks complete after implementation
- ⚠️ **MUST** pass `--project-id` for your assigned project

**Agent Type: Orchestrator**

- ✅ Creating phase completion reports
- ✅ Adding features to any project roadmap
- ✅ Documenting major milestones
- ✅ Coordinating cross-project initiatives
- ✅ Can update any project (defaults to AI DevOps Agent Platform)

**Example (Sub-Agent - Feature-Dev):**

```powershell
$env:LINEAR_API_KEY = "lin_oauth_..."

# Feature-dev agent creating a feature with sub-tasks
python support/scripts/agent-linear-update.py create-issue `
    --project-id "b21cbaa1-9f09-40f4-b62a-73e0f86dd501" `
    --title "Implement Auto-Scaling Logic" `
    --description "Add dynamic scaling based on load metrics" `
    --status "in_progress"

# Breaking down complex feature
python support/scripts/agent-linear-update.py create-phase `
    --project-id "b21cbaa1-9f09-40f4-b62a-73e0f86dd501" `
    --phase-number 7 `
    --title "Autonomous Operations" `
    --subtasks "Decision Engine,Learning Module,Self-Healing"
```

**Example (Orchestrator):**

```powershell
$env:LINEAR_API_KEY = "lin_oauth_..."

# Orchestrator creating phase completion (uses default project)
python support/scripts/agent-linear-update.py create-issue `
    --title "Phase 6 Complete: Multi-Agent Collaboration" `
    --description "All Phase 6 features deployed and validated" `
    --status "done" `
    --priority 1
```

---

### 🚨 Use Orchestrator Event Bus (HITL Approvals) When:

**Agent Type: ANY (All agents have access)**

- ✅ Requesting HITL approval for high-risk actions
- ✅ Notifying humans of critical decisions
- ✅ Requiring human confirmation before deployment
- ✅ Escalating blocked workflows

**Integration Method (Automatic):**

```python
# In any agent (orchestrator mediates)
from shared.lib.event_bus import EventBus

event_bus = EventBus()
await event_bus.emit("approval_request", {
    "request_id": "approve-deploy-prod-123",
    "agent_name": "feature-dev",
    "action_type": "deploy_production",
    "risk_level": "high",
    "description": "Deploy v2.0.0 to production",
    "approval_hub_issue": "PR-68"
})

# Orchestrator automatically posts to PR-68
```

**Manual Method (Orchestrator Only):**

```powershell
$env:LINEAR_API_KEY = "lin_oauth_..."
python support/scripts/update-linear-pr68.py
```

---

## Configuration

### Environment Variables

In `config/env/.env`:

```bash
# Linear OAuth Token (for GraphQL API access)
LINEAR_API_KEY=lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571

# Linear Project Configuration
LINEAR_PROJECT_ID=78b3b839d36b
LINEAR_TEAM_ID=f5b610be-ac34-4983-918b-2c9d00aa9b7a

# Linear Approval Hub
LINEAR_APPROVAL_HUB_ISSUE_ID=PR-68

# Linear OAuth Configuration
LINEAR_OAUTH_CLIENT_ID=22a84e6bd5a10c0207d255773ce91ec6
LINEAR_OAUTH_CLIENT_SECRET=b7bc7b0c6f39b36e7455c1e6a0e5f31c
LINEAR_OAUTH_REDIRECT_URI=http://localhost:8000/oauth/linear/callback
```

---

## Project Structure in Linear

```
Project Roadmaps (PR) Team
├── AI DevOps Agent Platform (Project: 78b3b839d36b)
│   ├── Phase 1: Foundation ✅
│   ├── Phase 2: HITL Integration ✅
│   ├── Phase 3: Progressive MCP Disclosure ✅
│   ├── Phase 4: LLM Integration ✅
│   ├── Phase 5: Copilot Integration ✅
│   ├── Phase 6: Multi-Agent Collaboration ✅ (current)
│   └── Phase 7: Autonomous Operations (planned)
│
└── PR-68: Agent Approvals Hub (Workspace-level issue)
    └── Purpose: Approval notification hub for all HITL requests
```

---

## Best Practices

### For Phase Completions:

1. Run the phase-specific update script: `update-linear-phase6.py`
2. Include completion metrics and validation results
3. Link to relevant documentation in GitHub
4. Mark issue state as "Done" or "Complete"

### For Approval Notifications:

1. Let the event bus handle automatic posting to PR-68
2. Include approval request ID for traceability
3. Add risk level and action type labels
4. @mention relevant team members

### For General Updates:

1. Use the generic GraphQL script: `update-linear-graphql.py`
2. Target specific issue IDs or titles
3. Append to existing descriptions (don't overwrite)
4. Include timestamps and status indicators

---

## Common Mistakes to Avoid

### ❌ Workflow Confusion

| Mistake                                       | Correct Approach                                        |
| --------------------------------------------- | ------------------------------------------------------- |
| ❌ Post phase completions to PR-68            | ✅ Use `agent-linear-update.py` with project ID         |
| ❌ Use `agent-linear-update.py` for approvals | ✅ Use orchestrator event bus → PR-68                   |
| ❌ Sub-agent updates orchestrator's project   | ✅ Sub-agent passes `--project-id` for their project    |
| ❌ Direct PR-68 updates from sub-agents       | ✅ Sub-agents emit events → Orchestrator posts to PR-68 |

### ❌ Access Control Violations

| Agent Type   | ✅ Allowed                                                 | ❌ Forbidden                                |
| ------------ | ---------------------------------------------------------- | ------------------------------------------- |
| Sub-Agents   | Update their assigned project via `agent-linear-update.py` | Update other projects; Direct PR-68 updates |
| Orchestrator | Update any project; Post to PR-68 via event bus            | Bypass HITL approval process                |

### ❌ Data Management

| Mistake                                  | Correct Approach                    |
| ---------------------------------------- | ----------------------------------- |
| ❌ Overwrite existing issue descriptions | ✅ Append updates with timestamps   |
| ❌ Create duplicate phase issues         | ✅ Search for existing issues first |
| ❌ Forget `--project-id` as sub-agent    | ✅ Always pass project UUID         |
| ❌ Mix roadmap and HITL in same script   | ✅ Keep workflows separate          |

---

## Verification

After running any Linear update script:

1. **Check the Linear URL** provided in the output
2. **Verify the update** appears in the correct location
3. **Confirm timestamps** match the deployment date
4. **Review formatting** (Markdown should render correctly)

---

## Troubleshooting

### "Issue not found" error:

- Verify the issue ID or project ID is correct
- Check your LINEAR_API_KEY has access to the workspace
- Try searching by title first

### "Permission denied" error:

- Ensure LINEAR*API_KEY is an OAuth token (starts with `lin_oauth*`)
- Personal API keys (`lin_api_`) may have limited permissions
- Verify team membership in Linear

### Updates not appearing:

- Check if description was appended (not overwritten)
- Verify GraphQL mutation succeeded in script output
- Check Linear UI for rate limiting messages

---

## Related Documentation

- `LINEAR_SETUP.md` - Initial setup and configuration
- `HITL_IMPLEMENTATION_PHASE2.md` - HITL approval workflow
- `PHASE_6_MONITORING_GUIDE.md` - Monitoring and observability
- `.github/copilot-instructions.md` - Overall architecture context

---

## Status Management

**IMPORTANT**: Always set appropriate status when creating or updating issues.

### Workflow States

| State         | When to Use                    | Example                                          |
| ------------- | ------------------------------ | ------------------------------------------------ |
| `backlog`     | Future work without commitment | "Phase 8 ideas we might tackle later"            |
| `todo`        | Committed work not yet started | "Phase 7 planned for next sprint"                |
| `in_progress` | Currently being worked on      | "Implementing Phase 6 multi-agent collaboration" |
| `done`        | Completed work                 | "Phase 6 deployed and validated"                 |
| `cancelled`   | Abandoned or deprioritized     | "Feature X no longer needed"                     |

### Retrospective Updates

When creating issues for **already-completed work**, always set status to `done`:

```powershell
# PR-85 was created retrospectively to document Phase 6 completion
# It should have been marked as "done" immediately
python support/scripts/agent-linear-update.py update-status `
    --issue-id "PR-85" `
    --status "done"
```

---

## Sub-Issue Best Practices

**Break down complex features into 3-5 sub-tasks** for better context and tracking.

### When to Create Sub-Issues

✅ **DO create sub-issues for:**

- Phase implementations (3-5 sub-tasks per phase)
- Complex features requiring multiple PRs
- Work spanning multiple agents or services
- Long-running initiatives (>1 week)

❌ **DON'T create sub-issues for:**

- Simple bug fixes
- Documentation updates
- Single-file changes
- Quick configuration tweaks

### Example: Phase 7 with Sub-Tasks

```powershell
$env:LINEAR_API_KEY = "lin_oauth_..."

python support/scripts/agent-linear-update.py create-phase `
    --phase-number 7 `
    --title "Autonomous Operations" `
    --description "Implement autonomous decision-making and learning capabilities" `
    --subtasks "Autonomous Decision Making,Learning from Outcomes,Predictive Task Routing,Self-Optimization Engine,Advanced Failure Recovery" `
    --status "todo"
```

**Result Structure:**

```
Phase 7: Autonomous Operations (Priority 1, Status: Todo)
├── Task 7.1: Autonomous Decision Making (Priority 2, Status: Todo)
├── Task 7.2: Learning from Outcomes (Priority 2, Status: Todo)
├── Task 7.3: Predictive Task Routing (Priority 2, Status: Todo)
├── Task 7.4: Self-Optimization Engine (Priority 2, Status: Todo)
└── Task 7.5: Advanced Failure Recovery (Priority 2, Status: Todo)
```

### Sub-Issue Workflow

**1. Planning Phase:**

```powershell
# Create parent issue with sub-tasks
python support/scripts/agent-linear-update.py create-phase `
    --phase-number 8 `
    --title "Advanced Monitoring" `
    --description "Comprehensive observability and alerting" `
    --subtasks "Distributed Tracing,Custom Metrics,Alerting Rules" `
    --status "todo"
```

**2. During Implementation:**

```powershell
# Mark parent as in-progress when starting work
python support/scripts/agent-linear-update.py update-status `
    --issue-id "PR-XX" `
    --status "in_progress"

# Update sub-tasks as you complete them
python support/scripts/agent-linear-update.py update-status `
    --issue-id "PR-XX" `  # Sub-task ID
    --status "done"
```

**3. After Completion:**

```powershell
# Mark parent as done after all sub-tasks complete
python support/scripts/agent-linear-update.py update-status `
    --issue-id "PR-XX" `  # Parent ID
    --status "done"
```

---

## Script Reference

### 📋 Roadmap Management Scripts

| Script                     | Purpose                                | Access Control                                               | Supports Sub-Issues | Supports Status | Project-Agnostic |
| -------------------------- | -------------------------------------- | ------------------------------------------------------------ | ------------------- | --------------- | ---------------- |
| `agent-linear-update.py`   | **PRIMARY SCRIPT** for roadmap updates | Sub-agents (with `--project-id`), Orchestrator (any project) | ✅ Yes              | ✅ Yes          | ✅ Yes           |
| `update-linear-phase6.py`  | Phase 6 specific (DEPRECATED)          | Orchestrator only                                            | ❌ No               | ❌ No           | ❌ No            |
| `update-linear-graphql.py` | Generic updates (DEPRECATED)           | Orchestrator only                                            | ❌ No               | ❌ No           | ❌ No            |
| `create-hitl-subtasks.py`  | Create subtasks (DEPRECATED)           | Orchestrator only                                            | ✅ Yes              | ❌ No           | ❌ No            |
| `mark-hitl-complete.py`    | Mark tasks done (DEPRECATED)           | Orchestrator only                                            | ❌ No               | ✅ Limited      | ❌ No            |

### 🚨 HITL Approval Scripts

| Script                  | Purpose                 | Access Control          | Integration Method         |
| ----------------------- | ----------------------- | ----------------------- | -------------------------- |
| `update-linear-pr68.py` | Manual PR-68 updates    | Orchestrator only       | Direct GraphQL             |
| Orchestrator Event Bus  | Automatic PR-68 updates | All agents (via events) | Event-driven (recommended) |

### agent-linear-update.py Commands

**Project-Agnostic Commands (works with any project):**

```powershell
$env:LINEAR_API_KEY = "lin_oauth_..."

# Get workflow state IDs for a team
python support/scripts/agent-linear-update.py get-states `
    --team-id "f5b610be-ac34-4983-918b-2c9d00aa9b7a"

# Create standalone issue (sub-agent MUST pass --project-id)
python support/scripts/agent-linear-update.py create-issue `
    --project-id "b21cbaa1-9f09-40f4-b62a-73e0f86dd501" `
    --title "Add Prometheus dashboard" `
    --description "Create Grafana dashboard for agent metrics" `
    --status "todo" `
    --priority 2

# Create phase with sub-tasks (orchestrator can omit --project-id for default)
python support/scripts/agent-linear-update.py create-phase `
    --project-id "b21cbaa1-9f09-40f4-b62a-73e0f86dd501" `
    --phase-number 7 `
    --title "Autonomous Operations" `
    --description "Self-learning and adaptive agent behaviors" `
    --subtasks "Decision Engine,Learning Module,Self-Healing" `
    --status "todo"

# Update issue status (works across all projects)
python support/scripts/agent-linear-update.py update-status `
    --issue-id "PR-85" `
    --status "done"
```

**Access Control Examples:**

```powershell
# ✅ SUB-AGENT (Feature-Dev): Must specify project
python support/scripts/agent-linear-update.py create-issue `
    --project-id "b21cbaa1-9f09-40f4-b62a-73e0f86dd501" `
    --title "Feature X" `
    --description "..." `
    --status "in_progress"

# ✅ ORCHESTRATOR: Can use default project or specify any project
python support/scripts/agent-linear-update.py create-issue `
    --title "Phase 6 Complete" `
    --description "..." `
    --status "done"  # Uses DEFAULT_PROJECT_UUID

# ❌ SUB-AGENT: DO NOT use for HITL approvals
# Use orchestrator event bus instead!
```

---

**Last Updated**: November 19, 2025 (Added sub-issue and status management guidelines)  
**Project Status**: Phase 6 Complete ✅  
**Next Phase**: Phase 7 - Autonomous Operations
