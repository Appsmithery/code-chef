# Linear Integration - Usage Guidelines

## Overview

This project uses Linear for two distinct purposes:

### 1. **AI DevOps Agent Platform Project** (Primary)

- **URL**: https://linear.app/project-roadmaps/project/ai-devops-agent-platform-78b3b839d36b
- **Project ID**: `78b3b839d36b`
- **Team**: Project Roadmaps (PR)
- **Purpose**: Track project phases, milestones, and feature delivery
- **Update Frequency**: After each phase completion

**Use Cases:**

- Phase completion reports
- Milestone tracking
- Feature documentation
- Roadmap updates

**Scripts:**

- `support/scripts/update-linear-phase6.py` - Update Phase 6 completion
- `support/scripts/update-linear-graphql.py` - Generic issue updates
- `support/scripts/create-hitl-subtasks.py` - Create subtasks for phases

---

### 2. **PR-68: Agent Approvals Hub** (Specific Use Case)

- **URL**: https://linear.app/project-roadmaps/issue/PR-68/agent-approvals-hub
- **Issue ID**: `PR-68`
- **Purpose**: Workspace-level approval notification hub for HITL workflows
- **Update Frequency**: Real-time (when approval requests are created)

**Use Cases:**

- HITL approval notifications
- Agent coordination alerts
- Workflow approval tracking
- Critical action notifications

**Scripts:**

- `support/scripts/update-linear-pr68.py` - Update PR-68 with approval notifications
- Orchestrator event bus integration (automatic)

---

## When to Use Which

### Update the Project (78b3b839d36b) When:

- ✅ Completing a phase (Phase 6, Phase 7, etc.)
- ✅ Adding new features to the roadmap
- ✅ Documenting major milestones
- ✅ Recording deployment status
- ✅ Updating architecture documentation

**Example:**

```powershell
$env:LINEAR_API_KEY="your_key_here"
python support/scripts/update-linear-phase6.py
```

---

### Update PR-68 When:

- ✅ Agent requests HITL approval
- ✅ Critical action needs human review
- ✅ Workflow requires approval gate
- ✅ Posting approval notifications

**Example:**

```powershell
$env:LINEAR_API_KEY="your_key_here"
python support/scripts/update-linear-pr68.py
```

**Automatic Integration:**

```python
# In orchestrator event bus
await linear_workspace_client.post_approval_notification(
    issue_id="PR-68",
    request_id=approval_request_id,
    risk_level="high",
    action_type="deploy_production"
)
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

❌ **DON'T** post phase completions to PR-68  
✅ **DO** post phase completions to the project (78b3b839d36b)

❌ **DON'T** post approval requests to the project  
✅ **DO** post approval requests to PR-68

❌ **DON'T** overwrite existing issue descriptions  
✅ **DO** append updates with timestamps

❌ **DON'T** create duplicate issues for phases  
✅ **DO** search for existing phase issues first

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

| Script                     | Purpose                       | Target                 | Supports Sub-Issues | Supports Status |
| -------------------------- | ----------------------------- | ---------------------- | ------------------- | --------------- |
| `agent-linear-update.py`   | **PRIMARY SCRIPT** for agents | Project/Any issue      | ✅ Yes              | ✅ Yes          |
| `update-linear-phase6.py`  | Phase 6 completion            | Project (78b3b839d36b) | ❌ No               | ❌ No           |
| `update-linear-pr68.py`    | Approval hub updates          | PR-68                  | ❌ No               | ❌ No           |
| `update-linear-graphql.py` | Generic updates               | Any issue              | ❌ No               | ❌ No           |
| `create-hitl-subtasks.py`  | Create subtasks               | Any parent issue       | ✅ Yes              | ❌ No           |
| `mark-hitl-complete.py`    | Mark tasks done               | Any issue              | ❌ No               | ✅ Limited      |

### agent-linear-update.py Commands

```powershell
# Get workflow state IDs (run once to populate script)
python support/scripts/agent-linear-update.py get-states

# Create standalone issue
python support/scripts/agent-linear-update.py create-issue `
    --title "Add Prometheus dashboard" `
    --description "Create Grafana dashboard for agent metrics" `
    --status "todo" `
    --priority 2

# Create phase with sub-tasks (RECOMMENDED for complex features)
python support/scripts/agent-linear-update.py create-phase `
    --phase-number 7 `
    --title "Autonomous Operations" `
    --description "Self-learning and adaptive agent behaviors" `
    --subtasks "Decision Engine,Learning Module,Self-Healing" `
    --status "todo"

# Update issue status
python support/scripts/agent-linear-update.py update-status `
    --issue-id "PR-85" `
    --status "done"
```

---

**Last Updated**: November 19, 2025 (Added sub-issue and status management guidelines)  
**Project Status**: Phase 6 Complete ✅  
**Next Phase**: Phase 7 - Autonomous Operations
