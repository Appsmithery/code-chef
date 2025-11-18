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
