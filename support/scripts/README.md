# Dev-Tools Scripts

Operational scripts for deployment, development, and maintenance.

## 📁 Directory Structure

- **admin/** - Administrative utilities
- **agents/** - Agent-specific scripts
- **config/** - Configuration management
- **data/** - Data processing scripts
- **deploy/** - Deployment and infrastructure setup
- **dev/** - Development utilities (up/down/rebuild/logs)
- **docker/** - Docker operations and maintenance
- **init/** - Initialization scripts (resource locks, workflow state)
- **linear/** - Linear project management scripts
- **maintenance/** - Code maintenance and migration scripts
- **testing/** - Test scripts and validation utilities
- **validation/** - Health checks and environment validation
- **workflow/** - Workflow examples and executors

## 🚀 Quick Commands

### Development

```powershell
# Start all services
./support/scripts/dev/up.sh

# Tail logs for specific agent
./support/scripts/dev/logs.sh orchestrator

# Rebuild all containers
./support/scripts/dev/rebuild.sh

# Stop all services
./support/scripts/dev/down.sh
```

### Deployment

```powershell
# Deploy to remote droplet
./support/scripts/deploy/deploy.ps1 -Target remote

# Validate environment configuration
./support/scripts/validation/validate-env.sh

# Check service health
./support/scripts/validation/health-check.sh

# Validate LangSmith tracing
./support/scripts/validation/validate-tracing.sh
```

### Linear Integration

```powershell
# Set API key
$env:LINEAR_API_KEY = "lin_oauth_..."

# Create issue in project
python support/scripts/linear/agent-linear-update.py create-issue --project-id "UUID" --title "Feature"

# Get project UUID by slug
python support/scripts/linear/get-linear-project-uuid.py

# Update workspace hub (PR-68)
python support/scripts/linear/update-linear-pr68.py
```

### Docker Maintenance

```powershell
# Backup Docker volumes
./support/scripts/docker/backup_volumes.sh

# Clean dangling resources
./support/scripts/docker/docker-cleanup.ps1

# Prune old images
./support/scripts/docker/docker-prune.sh

# Prune DockerHub images
./support/scripts/docker/dockerhub-image-prune.ps1
```

### Workflow Management

```powershell
# Monitor workflow state
python support/scripts/workflow/workflow_monitor.py

# Execute PR deployment workflow
python support/scripts/workflow/workflow_pr_deploy.py

# Self-healing workflow
python support/scripts/workflow/workflow_self_healing.py

# Example workflows
python support/scripts/workflow/example_workflow_code_review_dev.py
python support/scripts/workflow/example_workflow_parallel_docs.py
```

### Testing & Validation

```powershell
# Test chat endpoint
python support/scripts/testing/test-chat-endpoint.py

# Test inter-agent communication
python support/scripts/testing/test_inter_agent_communication.py

# Test resource locks
python support/scripts/testing/test_resource_locks.py

# List available Gradient models
python support/scripts/testing/list-gradient-models.py
```

### Initialization

```powershell
# Initialize resource locks in database
./support/scripts/init/init-resource-locks.ps1

# Initialize workflow state schema
./support/scripts/init/init-workflow-state.ps1
```

### Maintenance

```powershell
# Analyze Python imports
python support/scripts/maintenance/analyze_imports.py

# Fix deprecated imports
python support/scripts/maintenance/fix_deprecated_imports.py

# Generate registry integration code
python support/scripts/maintenance/generate-registry-integration.py
```

## 📋 Script Categories

### Deployment Scripts (`deploy/`)

- `deploy.ps1` - Main deployment script (local/remote targets)
- `setup_secrets.sh` - Docker secrets initialization
- `deploy-to-droplet.sh` - DigitalOcean droplet deployment

### Validation Scripts (`validation/`)

- `validate-env.sh` - Environment variable validation
- `validate-phase6.ps1` - Phase 6 integration validation
- `validate-tracing.sh` - LangSmith tracing validation
- `health-check.sh` - Service health checks

### Linear Scripts (`linear/`)

- `agent-linear-update.py` - Create/update Linear issues
- `get-linear-project-uuid.py` - Retrieve project UUIDs
- `update-linear-pr68.py` - Post to approval hub

### Development Scripts (`dev/`)

- `up.sh` - Start Docker Compose stack
- `down.sh` - Stop Docker Compose stack
- `rebuild.sh` - Rebuild and restart containers
- `logs.sh` - Tail agent logs

### Docker Scripts (`docker/`)

- `backup_volumes.sh` - Backup named volumes
- `docker-cleanup.ps1` - Clean dangling resources
- `docker-prune.sh` - Prune unused Docker objects
- `dockerhub-image-prune.ps1` - Clean DockerHub registry
- `prune-dockerhub-manual.ps1` - Manual DockerHub pruning

### Workflow Scripts (`workflow/`)

- `workflow_monitor.py` - Monitor workflow execution
- `workflow_pr_deploy.py` - PR deployment workflow
- `workflow_self_healing.py` - Self-healing workflow
- `example_workflow_*.py` - Example workflow implementations

### Testing Scripts (`testing/`)

- `test-chat-endpoint.py` - Test chat API
- `test_inter_agent_communication.py` - Test agent communication
- `test_resource_locks.py` - Test resource locking
- `test_workflow_state.py` - Test workflow state
- `list-gradient-models.py` - List available LLM models

### Initialization Scripts (`init/`)

- `init-resource-locks.ps1` - Initialize resource locks
- `init-workflow-state.ps1` - Initialize workflow state

### Maintenance Scripts (`maintenance/`)

- `analyze_imports.py` - Analyze Python imports
- `fix_deprecated_imports.py` - Fix deprecated imports
- `generate-registry-integration.py` - Generate registry code

## 🔧 Script Conventions

- **PowerShell scripts (.ps1)** - Windows-compatible, cross-platform via pwsh
- **Bash scripts (.sh)** - Linux/macOS, WSL-compatible
- **Python scripts (.py)** - Requires Python 3.8+, install deps from requirements.txt

### Environment Variables

Most scripts read from `config/env/.env`. Key variables:

- `GRADIENT_API_KEY` - DigitalOcean AI Platform API key
- `LINEAR_API_KEY` - Linear OAuth token (GraphQL API)
- `LANGCHAIN_API_KEY` - LangSmith tracing key
- `DOCKER_USERNAME` / `DOCKER_TOKEN` - Docker registry credentials
- `DO_API_TOKEN` - DigitalOcean Container Registry token

See `config/env/README.md` for full environment variable documentation.

## 📝 Adding New Scripts

1. Place in appropriate subdirectory based on purpose
2. Follow existing naming conventions (`kebab-case` for bash/py, `PascalCase` for ps1)
3. Add usage comments at top of file
4. Update this README with description and usage
5. Test locally before committing

## 🆘 Troubleshooting

**Script not found:**

```powershell
# Ensure you're in repository root
cd d:\INFRA\Dev-Tools\Dev-Tools

# Use relative paths
./support/scripts/dev/up.sh
```

**Permission denied (Linux/macOS):**

```bash
chmod +x support/scripts/dev/up.sh
```

**Python import errors:**

```powershell
# Install dependencies
pip install -r requirements.txt

# Set PYTHONPATH for shared modules
$env:PYTHONPATH = "d:\INFRA\Dev-Tools\Dev-Tools"
```

**Docker compose not found:**

```powershell
# Use docker compose (not docker-compose)
cd deploy
docker compose up -d
```
