# Linear Integration - Agent Quick Reference

## Your Agent Identity

| Agent             | Tag                     | GitHub Identifier          | Commit Author                          |
| ----------------- | ----------------------- | -------------------------- | -------------------------------------- |
| 🎯 Orchestrator   | `@orchestrator-agent`   | `code-chef`                | `code-chef <code-chef@appsmithery.co>` |
| 🚀 Feature-Dev    | `@feature-dev-agent`    | `code-chef/feature-dev`    | `code-chef feature-dev <...>`          |
| 🔍 Code-Review    | `@code-review-agent`    | `code-chef/code-review`    | `code-chef code-review <...>`          |
| 🏗️ Infrastructure | `@infrastructure-agent` | `code-chef/infrastructure` | `code-chef infrastructure <...>`       |
| ⚙️ CI/CD          | `@cicd-agent`           | `code-chef/cicd`           | `code-chef cicd <...>`                 |
| 📚 Documentation  | `@documentation-agent`  | `code-chef/documentation`  | `code-chef documentation <...>`        |

**GitHub Identifier** is used in:
- Commit messages
- PR titles and descriptions
- Linear issue linking via magic words

---

## 🔗 GitHub Integration

### Linking Commits to Linear Issues

Use **magic words** in commit messages to automatically link to Linear issues:

```bash
git commit -m "feat: add Redis caching

Implement Redis for API response caching.

Fixes DEV-123
Implemented by: code-chef/feature-dev
Coordinated by: code-chef"
```

**Magic Words**:
- **Close issue**: `Fixes`, `Closes`, `Resolves`
- **Reference issue**: `Refs`, `References`, `Part of`, `Related to`

### PR Format

When creating PRs, use this format:

```markdown
Title: [code-chef/feature-dev] Add Redis caching

## Summary
Implementation details

## Changes
- Change 1
- Change 2

## Linear Issues
Fixes DEV-123

## Agent Attribution
- **Agent**: 🚀 Feature Dev
- **Identifier**: code-chef/feature-dev
- **Coordinated by**: code-chef orchestrator
```

**Result**: Linear issue DEV-123 automatically updates with commit/PR references.

---

## Project IDs (REQUIRED for Sub-Agents)

| Project                      | UUID                                   | When to Use                     |
| ---------------------------- | -------------------------------------- | ------------------------------- |
| AI DevOps Agent Platform     | `b21cbaa1-9f09-40f4-b62a-73e0f86dd501` | DevOps automation features      |
| TWKR Agentic Resume Workflow | `86f8cc40-de06-4e3d-b7c8-ed95193737bc` | Resume/job application features |

---

## Quick Commands

### 📋 Create Issue (Sub-Agent)

```powershell
$env:LINEAR_API_KEY = "lin_oauth_..."

python support/scripts/linear/agent-linear-update.py create-issue `
    --project-id "b21cbaa1-9f09-40f4-b62a-73e0f86dd501" `  # REQUIRED
    --title "Your Issue Title" `
    --description "Your description here" `
    --agent-name "feature-dev" `  # YOUR agent name
    --status "in_progress" `
    --priority 2
```

**Result**: Issue created with automatic signature:

```markdown
Your description here

---

_Created by 🚀 Feature Dev [Feature-Dev Agent]_
_Agent Tag: @feature-dev-agent_
```

---

### 📋 Create Phase with Sub-Tasks (Orchestrator Only)

```powershell
python support/scripts/linear/agent-linear-update.py create-phase `
    --project-id "b21cbaa1-9f09-40f4-b62a-73e0f86dd501" `  # Optional for orchestrator
    --phase-number 7 `
    --title "Autonomous Operations" `
    --description "Phase 7 implementation details" `
    --subtasks "Task 1,Task 2,Task 3" `
    --agent-name "orchestrator" `
    --status "todo"
```

---

### 🔄 Update Issue Status (Any Agent)

```powershell
python support/scripts/linear/agent-linear-update.py update-status `
    --issue-id "PR-85" `
    --status "done"
```

_Note_: Status updates don't require `--agent-name` (status is factual, not attributed)

---

## 🚨 HITL Approvals (All Agents)

**DO NOT use `agent-linear-update.py` for approvals!**

Use orchestrator event bus instead:

```python
from shared.lib.event_bus import EventBus

event_bus = EventBus()
await event_bus.emit("approval_request", {
    "request_id": "deploy-prod-123",
    "agent_name": "feature-dev",  # YOUR agent name
    "action_type": "deploy_production",
    "risk_level": "high",
    "description": "Deploy v2.0.0 to production"
})
```

Orchestrator automatically posts to PR-68 with your agent tag.

---

## Access Control Rules

### ✅ Sub-Agents CAN:

- Create issues in their assigned project (with `--project-id`)
- Update issues in their assigned project
- Request approvals via event bus
- Use `--agent-name` for attribution

### ❌ Sub-Agents CANNOT:

- Update other projects (will be rejected)
- Post directly to PR-68 (use event bus)
- Omit `--project-id` parameter

### ✅ Orchestrator CAN:

- Create issues in ANY project
- Omit `--project-id` (defaults to AI DevOps Agent Platform)
- Post directly to PR-68 via event bus
- Create/manage phases across projects

---

## Common Patterns

### Pattern 1: Sub-Agent Creates Feature Issue

```powershell
# Feature-Dev creating a new feature
python support/scripts/linear/agent-linear-update.py create-issue `
    --project-id "b21cbaa1-9f09-40f4-b62a-73e0f86dd501" `
    --title "Add Redis caching layer" `
    --description "Implement Redis for API response caching to improve performance" `
    --agent-name "feature-dev" `
    --status "in_progress" `
    --priority 2
```

### Pattern 2: Sub-Agent Breaks Down Feature

```powershell
# Infrastructure creating infrastructure tasks
python support/scripts/linear/agent-linear-update.py create-issue `
    --project-id "b21cbaa1-9f09-40f4-b62a-73e0f86dd501" `
    --title "Task 1: Provision Redis cluster" `
    --parent-id "parent-issue-uuid" `
    --agent-name "infrastructure" `
    --status "todo"
```

### Pattern 3: Sub-Agent Marks Work Complete

```powershell
# Any agent marking their task done
python support/scripts/linear/agent-linear-update.py update-status `
    --issue-id "PR-XX" `
    --status "done"
```

### Pattern 4: Sub-Agent Requests Approval

```python
# Feature-Dev requesting deployment approval
await event_bus.emit("approval_request", {
    "request_id": f"deploy-{datetime.now().isoformat()}",
    "agent_name": "feature-dev",
    "action_type": "deploy_production",
    "risk_level": "high",
    "description": "Deploy caching feature to production",
    "issue_id": "PR-XX"  # Related issue
})
```

---

## Troubleshooting

### Error: "Permission denied"

- **Cause**: Sub-agent trying to update wrong project
- **Fix**: Verify `--project-id` matches your assigned project

### Error: "LINEAR_API_KEY not set"

- **Cause**: Missing environment variable
- **Fix**: `$env:LINEAR_API_KEY = "lin_oauth_..."`

### Issue created without signature

- **Cause**: Forgot `--agent-name` parameter
- **Fix**: Always include `--agent-name "your-agent"` for attribution

### Approval request not appearing in PR-68

- **Cause**: Using wrong script or bypassing event bus
- **Fix**: Use event bus, not `agent-linear-update.py` for approvals

---

## See Also

- [DEVELOPMENT.md#Linear & GitHub Integration](../../DEVELOPMENT.md#-linear--github-integration) - Multi-repo setup
- [config/linear/github-webhook-config.yaml](github-webhook-config.yaml) - GitHub webhook configuration
- [config/linear/agent-project-mapping.yaml](agent-project-mapping.yaml) - Agent identifiers and permissions
- `support/docs/LINEAR_USAGE_GUIDELINES.md` - Comprehensive documentation (if exists)

---

**Last Updated**: December 11, 2025  
**Projects**: AI DevOps Agent Platform (code-chef), TWKR Agentic Resume Workflow  
**Agents**: 6 (Orchestrator + 5 Sub-Agents)  
**GitHub Integration**: ✅ Enabled (bidirectional sync)
