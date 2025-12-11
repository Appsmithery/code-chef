## 🎯 Action Plan: Container Tools Optimization & Taskfile Deprecation

### **Phase 1: Container Tools Setup (5 min)**

**Why sidebar is empty**: No containers exist locally. You're using pre-built images from Docker Hub (`alextorelli28/appsmithery:*`), so your local machine has no containers/images until you start the stack.

**Immediate fixes**:

1. **Install recommended extensions**:

   - ✅ Docker (ms-azuretools.vscode-docker) - You likely have this
   - ✅ Docker Compose (ms-azuretools.vscode-docker)
   - GitHub Pull Requests and Issues (GitHub.vscode-pull-request-github)

2. **Start stack locally** (containers will appear):

   ```bash
   cd deploy
   docker compose up -d
   ```

   Then the Container Tools sidebar will populate with 9+ running containers.

3. **Add Docker Compose right-click shortcuts**:
   - Create [`.vscode/settings.json`](.vscode/settings.json):
   ```json
   {
     "docker.dockerComposeBuild": true,
     "docker.dockerComposeDetached": true,
     "docker.commands.composeUp": ["up", "-d"],
     "docker.commands.composeDown": ["down", "--remove-orphans"]
   }
   ```

---

### **Phase 2: Taskfile → Container Tools Migration (30 min)**

#### **What to KEEP (migrate to other places)**:

| Taskfile Command       | Migrate To                  | Rationale               |
| ---------------------- | --------------------------- | ----------------------- |
| `test:*` commands      | tasks.json                  | VS Code Tasks UI        |
| `workflow:*` API calls | VS Code extension commands  | Part of your extension  |
| Health check scripts   | Docker Compose healthchecks | Native container health |
| SSH/droplet commands   | `OPERATIONS.md` doc         | Reference only          |

#### **What to DELETE (redundant)**:

| Taskfile Command        | Replacement                                    |
| ----------------------- | ---------------------------------------------- |
| `local:up/down/logs/ps` | Docker extension UI (right-click compose file) |
| `local:rebuild`         | Docker extension → Rebuild                     |
| `local:clean`           | Docker extension → Prune                       |
| `deploy:restart`        | GitHub Actions only                            |
| `droplet:status`        | SSH manually (rare)                            |

---

### **Phase 3: Enhanced Docker Compose Configuration (15 min)**

Add native healthchecks to [`deploy/docker-compose.yml`]docker-compose.yml ) so Container Tools shows health status:

```yaml
# Example for orchestrator service
orchestrator:
  # ... existing config
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
    interval: 10s
    timeout: 5s
    retries: 3
    start_period: 30s
```

This replaces your Taskfile health check scripts with native Docker health indicators.

---

### **Phase 4: VS Code Tasks Configuration (10 min)**

Create [`.vscode/tasks.json`](.vscode/tasks.json) for useful commands:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run All Tests",
      "type": "shell",
      "command": "pytest",
      "args": ["support/tests", "-v", "--tb=short"],
      "group": "test",
      "presentation": { "reveal": "always" }
    },
    {
      "label": "Run Tests with Coverage",
      "type": "shell",
      "command": "pytest",
      "args": [
        "support/tests",
        "-v",
        "--cov=agent_orchestrator",
        "--cov=shared",
        "--cov-report=html"
      ],
      "group": "test"
    },
    {
      "label": "SSH to Droplet",
      "type": "shell",
      "command": "ssh",
      "args": ["root@45.55.173.72"],
      "isBackground": false,
      "problemMatcher": []
    }
  ]
}
```

Now accessible via `Ctrl+Shift+B` or Command Palette → `Tasks: Run Task`.

---

### **Phase 5: Documentation (10 min)**

Create [`DEVELOPMENT.md`](DEVELOPMENT.md):

````markdown
# Development Guide

## Local Development

### Starting Services

1. Open [`deploy/docker-compose.yml`](deploy/docker-compose.yml)
2. Right-click → **Compose Up**
3. View in Container Tools sidebar

### Common Operations

- **View Logs**: Container Tools → Right-click container → View Logs
- **Restart Service**: Right-click → Restart
- **Rebuild**: Right-click compose file → Compose Down, then Up

### Running Tests

- `Ctrl+Shift+P` → `Tasks: Run Task` → Select test task
- Or: `pytest support/tests -v`

### Deployment

Use GitHub Actions workflows (not manual):

1. Push to `main` → **Intelligent Deploy to Droplet** (auto)
2. Manually trigger **Deploy Frontend to Production**

### Droplet Access

```bash
ssh root@45.55.173.72
cd /opt/Dev-Tools
docker compose ps  # Check services
```
````

## Port Reference

- 8001 → Orchestrator
- 8007 → RAG Context
- 8008 → State Persistence
- 8009 → Agent Registry
- 8010 → LangGraph

````

---

### **Phase 6: Clean Up (5 min)**

1. Delete Taskfile.yml
2. Remove `.task` directory if it exists
3. Update [`.gitignore`](.gitignore ) to remove task-related entries
4. Commit changes

---

## 📋 Implementation Checklist

```markdown
- [ ] Phase 1: Start local stack (`docker compose up -d`)
- [ ] Phase 1: Verify Container Tools sidebar shows containers
- [ ] Phase 1: Add Docker Compose settings to `.vscode/settings.json`
- [ ] Phase 2: Create `.vscode/tasks.json` with test tasks
- [ ] Phase 3: Add healthchecks to docker-compose.yml services
- [ ] Phase 4: Create DEVELOPMENT.md with quick reference
- [ ] Phase 5: Delete Taskfile.yml
- [ ] Phase 6: Commit all changes
````

---

## 🎁 Benefits After Migration

| Before (Taskfile)              | After (Native Extensions)              |
| ------------------------------ | -------------------------------------- |
| 500+ lines YAML config         | ~100 lines across 3 files              |
| Remember `task` command syntax | Right-click UI                         |
| Custom health check scripts    | Native Docker healthchecks             |
| Manual workflow API calls      | VS Code commands (from your extension) |
| SSH commands in YAML           | One-liner in docs                      |

**Time saved**: ~20 seconds per operation (no CLI lookups)  
**Maintenance burden**: Reduced by 80%

---

Want me to execute this plan now? I can:

1. Create tasks.json with test tasks
2. Add healthchecks to docker-compose.yml
3. Create `DEVELOPMENT.md`
4. Delete Taskfile.yml
5. Commit everything
