# Linear Integration Setup

## Quick Setup for AI DevOps Agent Platform Project

### Step 1: Get Your Linear API Key

1. Navigate to: https://linear.app/vibecoding-roadmap/settings/api
2. Click **"Create new Personal API Key"**
3. Give it a name like "Dev-Tools Agent Platform"
4. Copy the generated key (starts with `lin_api_`)

### Step 2: Configure Environment

Add the API key to `config/env/.env`:

```bash
# Linear Personal API Token (for direct SDK access)
LINEAR_API_KEY=lin_api_your_key_here
```

### Step 3: Restart Services

If running locally:

```powershell
cd deploy
docker compose restart orchestrator
```

If running on droplet:

```powershell
ssh root@45.55.173.72 "cd /opt/Dev-Tools/deploy && docker compose restart orchestrator"
```

### Step 4: Test Connection

Run the connection script:

```powershell
.\support\scripts\connect-linear-project.ps1
```

Or for remote:

```powershell
.\support\scripts\connect-linear-project.ps1 -Remote
```

## Project Information

- **Workspace**: vibecoding-roadmap
- **Project**: AI DevOps Agent Platform
- **Project ID**: 78b3b839d36b
- **URL**: https://linear.app/vibecoding-roadmap/project/ai-devops-agent-platform-78b3b839d36b

## Available Endpoints

Once configured, you can use these endpoints via the orchestrator:

### Fetch Project Roadmap

```bash
GET http://localhost:8001/linear/project/78b3b839d36b
```

### List All Issues

```bash
GET http://localhost:8001/linear/issues
```

### Create New Issue

```bash
POST http://localhost:8001/linear/issues
Content-Type: application/json

{
  "title": "Issue title",
  "description": "Issue description",
  "priority": 2
}
```

### Update Issue Description

```bash
PATCH http://localhost:8001/linear/issues/{issue_id}
Content-Type: application/json

{
  "description": "Updated description with completion details"
}
```

### Update Phase Completion

```bash
POST http://localhost:8001/linear/roadmap/update-phase
Content-Type: application/json

{
  "issue_id": "b3d90ca5-386e-48f4-8665-39deb258667c",
  "phase_name": "Phase 2: HITL Integration",
  "status": "COMPLETE",
  "summary": "Complete HITL approval system deployed and verified in production.",
  "components": [
    "Risk Assessment Engine",
    "Approval Workflow",
    "REST API (5 endpoints)"
  ],
  "subtasks": [
    {"title": "Task 2.1: Interrupt Configuration", "status": "complete"},
    {"title": "Task 2.2: Taskfile Commands", "status": "complete"}
  ],
  "metrics": {
    "total_requests": 4,
    "avg_approval_time": "1.26 seconds",
    "risk_distribution": "2 critical, 1 high, 1 medium"
  },
  "artifacts": {
    "agent_orchestrator/main.py": "HITL API endpoints (lines 705-901)",
    "shared/lib/hitl_manager.py": "Approval lifecycle manager"
  },
  "tests": [
    "End-to-end approval flow verified",
    "Rejection workflow tested",
    "Database persistence validated"
  ],
  "deployment_url": "https://agent.appsmithery.co"
}
```

## Programmatic Updates via Python Scripts

For automated roadmap updates, use the GraphQL helper scripts:

### Update Issue Description

```powershell
$env:LINEAR_API_KEY="lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571"
python support/scripts/update-linear-graphql.py
```

### Create Subtasks

```powershell
$env:LINEAR_API_KEY="lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571"
python support/scripts/create-hitl-subtasks.py
```

### Mark Tasks Complete

```powershell
$env:LINEAR_API_KEY="lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571"
python support/scripts/mark-hitl-complete.py
```

## Using the Linear Roadmap Helper (Agents)

Agents can use the `linear_roadmap` module for programmatic updates:

```python
from lib.linear_roadmap import (
    get_roadmap_updater,
    PHASE_ISSUES,
    WORKFLOW_STATES,
    PROJECT_ID,
    TEAM_ID
)

# Initialize
updater = get_roadmap_updater()

# Update a phase with completion details
await updater.update_phase_completion(
    issue_id=PHASE_ISSUES["phase_2"],
    phase_name="Phase 2: HITL Integration",
    status="COMPLETE",
    components=["Risk Assessment", "Approval Workflow", "REST API"],
    metrics={"total_requests": 4, "avg_time": "1.26s"},
    tests=["End-to-end flow verified"]
)

# Mark issue as complete
await updater.mark_issue_complete(
    issue_id="task_id_here",
    state_id=WORKFLOW_STATES["completed"]
)

# Create a subtask
await updater.create_subtask(
    title="Task 2.3: API Endpoints",
    description="Complete REST API implementation",
    parent_id=PHASE_ISSUES["phase_2"],
    project_id=PROJECT_ID,
    team_id=TEAM_ID
)
```

## Integration Architecture

```
┌─────────────────────────────────────────────────────┐
│                Linear Workspace                      │
│         vibecoding-roadmap                           │
│                                                      │
│  ┌────────────────────────────────────────────┐    │
│  │  Project: AI DevOps Agent Platform         │    │
│  │  ID: 78b3b839d36b                          │    │
│  │                                             │    │
│  │  - Issues (roadmap items)                  │    │
│  │  - Project milestones                      │    │
│  │  - Team assignments                        │    │
│  └────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
                      ▲
                      │ LINEAR_API_KEY
                      │ (Personal API Token)
                      │
┌─────────────────────────────────────────────────────┐
│         agent_orchestrator:8001                      │
│                                                      │
│  shared/lib/linear_client.py                        │
│  - LinearIntegration class                          │
│  - fetch_project_roadmap(project_id)                │
│  - fetch_issues(filters)                            │
│  - create_issue()                                   │
│  - update_issue()                                   │
└─────────────────────────────────────────────────────┘
                      ▲
                      │ HTTP REST API
                      │
┌─────────────────────────────────────────────────────┐
│         Your Application / Scripts                   │
│  - PowerShell scripts                               │
│  - Python clients                                   │
│  - Web dashboards                                   │
└─────────────────────────────────────────────────────┘
```

## Troubleshooting

### "Linear integration not configured"

- Ensure LINEAR_API_KEY is set in `config/env/.env`
- Restart orchestrator after adding the key
- Check logs: `docker compose logs orchestrator`

### "403 Forbidden"

- Verify API key is correct and hasn't been revoked
- Check you have access to the workspace

### "404 Not Found" for project

- Verify project ID is correct: `78b3b839d36b`
- Ensure you have access to the project in Linear

## Security Notes

- **Never commit** LINEAR_API_KEY to version control
- The `.env` file is gitignored
- API keys are Personal Access Tokens - keep them secure
- Rotate keys periodically
- Use different keys for dev/staging/prod environments
