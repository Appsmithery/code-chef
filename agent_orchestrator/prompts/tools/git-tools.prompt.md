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
