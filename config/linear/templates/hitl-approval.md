# HITL Approval Request Template

**Template Type:** Workspace-scoped  
**Usage:** All agents posting approval requests to PR-68

---

## Template Configuration

**Name:** HITL Approval Request  
**Scope:** Workspace (available across all projects)  
**Icon:** 🔐

### Default Properties

- **Team:** Project Roadmaps (PR)
- **Project:** AI DevOps Agent Platform
- **Parent:** PR-68 (Approval Hub)
- **Priority:** Urgent
- **Assignee:** alextorelli28
- **Status:** Todo

### Template Variables

| Variable               | Type     | Required | Example                                                                     |
| ---------------------- | -------- | -------- | --------------------------------------------------------------------------- |
| `{{agent}}`            | Dropdown | Yes      | orchestrator, feature-dev, code-review, infrastructure, cicd, documentation |
| `{{task_id}}`          | Text     | Yes      | abc123-def456-ghi789                                                        |
| `{{priority}}`         | Dropdown | Yes      | critical, high, medium, low                                                 |
| `{{context}}`          | Markdown | Yes      | User requested JWT authentication for Express API                           |
| `{{proposed_changes}}` | Markdown | Yes      | - Add middleware/auth.js\n- Install jsonwebtoken package\n- Update routes   |
| `{{rationale}}`        | Markdown | Yes      | Secure API endpoints, prevent unauthorized access                           |
| `{{risks}}`            | Markdown | Yes      | Breaking change for existing clients without tokens                         |
| `{{deadline}}`         | Date     | No       | 2025-11-25                                                                  |

---

## Template Content

### Title

```
[HITL] {{agent}} - {{task_id}}
```

### Description

```markdown
# HITL Approval Request

**Agent:** {{agent}}  
**Task ID:** `{{task_id}}`  
**Priority:** {{priority}}

---

## Context

{{context}}

---

## Proposed Changes

{{proposed_changes}}

---

## Rationale

{{rationale}}

---

## Risks & Considerations

{{risks}}

---

## Required Action

- [ ] Review proposed changes
- [ ] Verify risks are acceptable
- [ ] Check implementation approach
- [ ] Approve or request modifications

{{#if deadline}}
**Deadline:** {{deadline}}
{{/if}}

**Approval Hub:** [PR-68](https://linear.app/project-roadmaps/issue/PR-68)
```

---

## Auto-Set Labels

Based on `{{agent}}` variable:

| Agent Value    | Applied Label                |
| -------------- | ---------------------------- |
| orchestrator   | minion-labels/orchestrator   |
| feature-dev    | minion-labels/feature-dev    |
| code-review    | minion-labels/code-review    |
| infrastructure | minion-labels/infrastructure |
| cicd           | minion-labels/cicd           |
| documentation  | minion-labels/documentation  |

---

## Usage Example

### Via API (Python):

```python
from shared.lib.linear_workspace_client import LinearWorkspaceClient

client = LinearWorkspaceClient()

approval_issue = await client.create_issue_from_template(
    template_id="hitl-approval-template-uuid",
    template_variables={
        "agent": "feature-dev",
        "task_id": "abc123-def456",
        "priority": "high",
        "context": "User requested JWT authentication for Express API endpoints",
        "proposed_changes": """
- Add `middleware/auth.js` with JWT verification
- Install `jsonwebtoken` package (v9.0.0)
- Update `/api/users` routes to require authentication
- Add login/logout endpoints
        """.strip(),
        "rationale": """
Current API has no authentication, exposing user data.
JWT tokens provide stateless auth suitable for microservices.
        """.strip(),
        "risks": """
- Breaking change for existing API clients
- Requires token refresh mechanism
- Must handle token expiration gracefully
        """.strip(),
        "deadline": "2025-11-25"
    },
    parent_id="PR-68"  # Link to approval hub
)

print(f"Created approval request: {approval_issue['identifier']}")
# Output: Created approval request: PR-123
```

### Via Linear UI:

1. Go to Linear → Create Issue
2. Select "HITL Approval Request" template
3. Fill in template variables
4. Click "Create"

---

## Webhook Integration

When approval request status changes:

**Event:** `Issue.update`  
**Trigger:** Status changes from "Todo" → "Approved" or "Rejected"  
**Action:** Webhook sends notification to orchestrator  
**Result:** Task execution resumes or cancels

---

## Related

- Template Spec: `config/linear/templates/hitl-approval.md` (this file)
- Implementation: `shared/lib/linear_workspace_client.py::create_issue_from_template()`
- Webhook Handler: `shared/gateway/main.py::/webhook/linear`
- Orchestrator Handler: `agent_orchestrator/main.py::handle_approval_decision()`
