# Linear Tools Usage Guide

## When to Use

- Creating and updating issues
- Managing project roadmaps
- Tracking HITL approval requests
- Linking work to Linear issues

## Available Tools (linear MCP server)

### `create_issue`

```json
{
  "title": "Implement authentication endpoint",
  "description": "Add JWT-based authentication with refresh tokens",
  "team_id": "f5b610be-ac34-4983-918b-2c9d00aa9b7a",
  "project_id": "b21cbaa1-9f09-40f4-b62a-73e0f86dd501",
  "status": "todo",
  "priority": 2,
  "labels": ["feature", "backend"]
}
```

**Use when**: Creating new work items or tracking agent tasks.

### `update_issue`

```json
{
  "issue_id": "DEV-123",
  "status": "in_progress",
  "assignee_id": "user-uuid",
  "comment": "Started implementation, ETA 2 days"
}
```

**Use when**: Updating progress or marking work complete.

### `create_comment`

```json
{
  "issue_id": "DEV-123",
  "body": "Deployment completed successfully to staging.\n\nURL: https://staging.example.com\nVersion: v1.2.3"
}
```

**Use when**: Adding context, deployment notes, or status updates.

### `list_issues`

```json
{
  "team_id": "f5b610be-ac34-4983-918b-2c9d00aa9b7a",
  "project_id": "b21cbaa1-9f09-40f4-b62a-73e0f86dd501",
  "status": ["todo", "in_progress"]
}
```

**Use when**: Checking pending work or roadmap status.

### `create_sub_issue`

```json
{
  "parent_id": "DEV-123",
  "title": "Add input validation",
  "description": "Validate request payload before processing",
  "status": "todo"
}
```

**Use when**: Breaking down complex features into subtasks.

## Common Patterns

**Pattern 1: Feature Tracking**

1. `create_issue` → main feature issue
2. `create_sub_issue` → break into 3-5 subtasks
3. `update_issue` → mark subtasks complete as work progresses
4. `create_comment` → add deployment/completion notes

**Pattern 2: HITL Approval**

1. `create_issue` → approval request in DEV-68 hub
2. Set custom fields: Request Status, Required Action
3. Wait for human approval
4. `update_issue` → mark as approved/rejected
5. Resume workflow based on status

**Pattern 3: Roadmap Updates**

1. `list_issues` → get project issues
2. `update_issue` → mark completed work as "done"
3. `create_comment` → add retrospective notes
4. Update project descriptions with progress

## Key Details

- **AI DevOps Project**: `b21cbaa1-9f09-40f4-b62a-73e0f86dd501`
- **Team ID**: Project Roadmaps (PR) = `f5b610be-ac34-4983-918b-2c9d00aa9b7a`
- **HITL Hub**: DEV-68 (workspace-wide approval notifications)
- **Status Values**: todo, in_progress, done, canceled
- **Priority**: 0 (none), 1 (urgent), 2 (high), 3 (normal), 4 (low)

## Safety Rules

- Always set `project_id` when creating roadmap issues
- Mark completed work as "done" not "canceled"
- Use sub-issues (3-5 tasks) for complex features
- Add deployment notes via comments, not descriptions
