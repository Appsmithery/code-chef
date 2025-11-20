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

## Script Reference

| Script                     | Purpose              | Target                 | Frequency      |
| -------------------------- | -------------------- | ---------------------- | -------------- |
| `update-linear-phase6.py`  | Phase 6 completion   | Project (78b3b839d36b) | Once per phase |
| `update-linear-pr68.py`    | Approval hub updates | PR-68                  | Real-time      |
| `update-linear-graphql.py` | Generic updates      | Any issue              | As needed      |
| `create-hitl-subtasks.py`  | Create subtasks      | Any parent issue       | As needed      |
| `mark-hitl-complete.py`    | Mark tasks done      | Any issue              | As needed      |

---

**Last Updated**: November 19, 2025  
**Project Status**: Phase 6 Complete ✅
