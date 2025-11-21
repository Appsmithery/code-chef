# Feature-Dev Task Template

**Template Type:** Project-scoped (AI DevOps Agent Platform)  
**Usage:** Feature development sub-issues created by feature-dev agent

---

## Template Configuration

**Name:** Feature-Dev Task  
**Scope:** Project (AI DevOps Agent Platform)  
**Icon:** 💻

### Default Properties

- **Team:** Project Roadmaps (PR)
- **Project:** AI DevOps Agent Platform
- **Priority:** Medium
- **Status:** Todo
- **Labels:** minion-labels/feature-dev

### Template Variables

| Variable                       | Type      | Required | Example                                                     |
| ------------------------------ | --------- | -------- | ----------------------------------------------------------- |
| `{{parent_task_id}}`           | Text      | Yes      | task_abc123                                                 |
| `{{complexity}}`               | Dropdown  | Yes      | simple, moderate, complex                                   |
| `{{requirements}}`             | Markdown  | Yes      | Add JWT middleware with RS256 signing                       |
| `{{acceptance_criteria}}`      | Checklist | Yes      | - [ ] Middleware validates tokens\n- [ ] Tests pass         |
| `{{technical_approach}}`       | Markdown  | Yes      | Use jsonwebtoken library, extract from Authorization header |
| `{{dependencies}}`             | Text      | No       | jsonwebtoken@9.0.0, crypto module                           |
| `{{files_affected}}`           | Text      | No       | middleware/auth.js, routes/users.js                         |
| `{{test_coverage_target}}`     | Number    | No       | 85                                                          |
| `{{code_generation_strategy}}` | Dropdown  | No       | llm_first, template_based, hybrid                           |

---

## Template Content

### Title

```
[Feature-Dev] {{parent_task_id}}
```

### Description

```markdown
# Feature Development Task

**Parent Task:** `{{parent_task_id}}`  
**Estimated Complexity:** {{complexity}}

---

## Requirements

{{requirements}}

---

## Acceptance Criteria

{{acceptance_criteria}}

---

## Technical Approach

{{technical_approach}}

## {{#if dependencies}}

## Dependencies

{{dependencies}}
{{/if}}

## {{#if files_affected}}

## Files/Modules Affected

{{files_affected}}
{{/if}}

## {{#if test_coverage_target}}

## Test Coverage Target

{{test_coverage_target}}%
{{/if}}

## {{#if code_generation_strategy}}

## Code Generation Strategy

{{code_generation_strategy}}
{{/if}}

---

## Status Updates

Agent will update this issue as work progresses.
```

---

## Auto-Link to Parent

Template automatically sets `parentId` when agent provides parent issue ID.

---

## Usage Example

### Via Agent Auto-Creation:

```python
# In agent_feature-dev/main.py

@app.post("/tasks/accept")
async def accept_task(task: TaskAssignment):
    """Agent accepts task and creates Linear sub-issue"""

    # Create Linear sub-issue from template
    linear_issue = await linear_client.create_issue_from_template(
        template_id="feature-dev-task-template-uuid",
        template_variables={
            "parent_task_id": task.task_id,
            "complexity": task.estimated_complexity,  # from orchestrator
            "requirements": task.requirements,
            "acceptance_criteria": "\n".join([f"- [ ] {c}" for c in task.criteria]),
            "technical_approach": task.technical_notes or "To be determined",
            "dependencies": ", ".join(task.dependencies) if task.dependencies else None,
            "files_affected": ", ".join(task.files) if task.files else None,
            "test_coverage_target": 85,
            "code_generation_strategy": "llm_first"
        },
        parent_id=task.orchestrator_issue_id  # Link to parent approval/task
    )

    # Store mapping for status updates
    await state_client.store_task_mapping(
        task_id=task.task_id,
        linear_issue_id=linear_issue["id"],
        linear_identifier=linear_issue["identifier"]
    )

    return {"linear_issue": linear_issue["identifier"]}
```

---

## Status Update Lifecycle

1. **Created** (Todo): Agent received task from orchestrator
2. **In Progress**: Agent started code generation
3. **In Review**: Code generated, running tests
4. **Done**: Tests passed, code committed

Agent updates Linear issue status programmatically:

```python
# Update status after code generation
await linear_client.update_issue_status(
    issue_id=linear_issue_id,
    status="in_progress"
)

# Add comment with progress
await linear_client.add_comment(
    issue_id=linear_issue_id,
    body=f"Generated 3 files, running tests..."
)

# Mark complete
await linear_client.update_issue_status(
    issue_id=linear_issue_id,
    status="done"
)
```

---

## Related Templates

- **orchestrator-task.md** - Orchestrator task decomposition
- **code-review-task.md** - Code review checklist
- **infrastructure-task.md** - Infrastructure change tracking
- **cicd-task.md** - Pipeline/deployment tracking
- **documentation-task.md** - Docs generation/update

---

## Related

- Template Spec: `config/linear/templates/agent-tasks/feature-dev-task.md` (this file)
- Implementation: `agent_feature-dev/main.py::/tasks/accept`
- State Management: `shared/services/state/schema.sql::task_linear_mappings`
