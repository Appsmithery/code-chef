# Agent Endpoints

Complete API reference for all Dev-Tools agents.

## MCP Gateway

**Base URL:** `http://gateway-mcp:8000`

### Endpoints

- `GET /health` — Service heartbeat.
- `GET /oauth/linear/install` — Redirects workspace admins to Linear OAuth (actor=`app`).
- `GET /oauth/linear/callback` — Handles Linear OAuth return, stores workspace token.
- `GET /oauth/linear/status` — Returns current token status (workspace, expiry, fallback info).
- `GET /api/linear-issues` — Fetches roadmap issues (default filters: started, unstarted, backlog).
- `GET /api/linear-project/:projectId` — Fetches a specific project with roadmap issues.

---

## Orchestrator Agent

**Base URL:** `http://orchestrator:8001`

### Endpoints

- `POST /task` - Submit new task for routing

  - Body: `{"type": "string", "description": "string", "context": {}}`
  - Returns: `{"task_id": "string", "status": "string"}`

- `GET /task/{id}` - Get task status

  - Returns: `{"task_id": "string", "status": "string", "result": {}}`

- `POST /route` - Manually route to agent
  - Body: `{"task_id": "string", "agent": "string"}`

---

## Feature Development Agent

**Base URL:** `http://feature-dev:8002`

### Endpoints

- `POST /feature` - Create new feature

  - Body: `{"name": "string", "description": "string", "requirements": []}`

- `POST /code` - Generate code

  - Body: `{"prompt": "string", "language": "string", "context": {}}`

- `GET /status/{id}` - Check feature development status

---

## Code Review Agent

**Base URL:** `http://code-review:8003`

### Endpoints

- `POST /review` - Submit code for review

  - Body: `{"code": "string", "language": "string", "checks": []}`
  - Returns: `{"review_id": "string", "issues": [], "score": number}`

- `GET /results/{id}` - Get review results

---

## Infrastructure Agent

**Base URL:** `http://infrastructure:8004`

### Endpoints

- `POST /infrastructure` - Generate IaC

  - Body: `{"type": "terraform|docker|k8s", "spec": {}}`

- `POST /deploy` - Deploy infrastructure

  - Body: `{"config_id": "string", "environment": "string"}`

- `GET /status/{id}` - Check deployment status

---

## CI/CD Agent

**Base URL:** `http://cicd:8005`

### Endpoints

- `POST /pipeline` - Generate CI/CD pipeline

  - Body: `{"platform": "github|gitlab|jenkins", "stages": []}`

- `POST /trigger` - Trigger workflow

  - Body: `{"pipeline_id": "string", "parameters": {}}`

- `GET /status/{id}` - Check pipeline status

---

## Documentation Agent

**Base URL:** `http://documentation:8006`

### Endpoints

- `POST /documentation` - Generate documentation

  - Body: `{"type": "readme|api|architecture", "content": {}}`

- `POST /update` - Update existing docs

  - Body: `{"doc_id": "string", "changes": {}}`

- `GET /docs/{type}` - Retrieve documentation
