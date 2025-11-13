# Agent Taskfile Workflows

Automated workflows for Dev-Tools agents integrated with GitHub Copilot development cycles.

## Quick Start

Each agent has its own Taskfile at `agents/<agent>/Taskfile.yml` with standardized tasks:

- `health` - Check service availability
- `dev:run` - Run agent locally
- `dev:test` - Execute unit tests
- `build` - Build container image
- `logs` - Tail container logs

## GitHub Copilot Integration Workflows

### 1. Generate Code with Copilot → Review with Code-Review Agent

```bash
# After Copilot generates code in VS Code
task copilot:generate-and-review
```

**What happens:**

1. Feature-dev agent receives implementation request
2. Code-review agent analyzes the generated code
3. Returns approval or revision requests

### 2. Full Deploy Cycle

```bash
# Implement → Review → Infrastructure → Deploy
task copilot:full-deploy
```

**Workflow:**

1. Feature-dev implements the feature
2. Code-review validates quality & security
3. Infrastructure generates deployment configs
4. CI/CD deploys to target environment

### 3. Document Generated Code

```bash
# Generate documentation for current context
task copilot:document
```

### 4. Complete Development Cycle

```bash
# Code → Test → Review → Document
task dev-cycle
```

## Per-Agent Workflows

### Orchestrator (Task Routing)

```bash
# Check orchestrator health
task orchestrator:health

# Submit task for routing
task orchestrator:route -- TASK="Add user authentication"

# Check task status
task orchestrator:task-status -- TASK_ID=abc-123

# List available agents
task orchestrator:list-agents
```

### Feature Development (Code Generation)

```bash
# Generate feature implementation
task feature-dev:implement -- FEATURE="Add JWT middleware"

# Run generated tests
task feature-dev:test

# Query RAG for code context
task feature-dev:query-rag -- QUERY="authentication patterns"

# View cached patterns
task feature-dev:patterns

# Implement and immediately review
task feature-dev:implement-and-review -- FEATURE="Add login endpoint"
```

### Code Review (Quality Assurance)

```bash
# Review staged changes
task code-review:review

# Review specific file
task code-review:review -- FILE=src/auth.py

# Review last commit
task code-review:review-commit

# Review and deploy if approved
task code-review:approve-and-deploy
```

### Documentation

```bash
# Generate README
task documentation:readme

# Generate API docs
task documentation:api-docs

# Generate architecture diagrams
task documentation:architecture

# Custom documentation
task documentation:generate -- TYPE=guide TARGET=user
```

### Infrastructure

```bash
# Generate Docker Compose
task infrastructure:docker-compose

# Generate Terraform
task infrastructure:terraform

# Generate Kubernetes manifests
task infrastructure:kubernetes

# Generate and deploy
task infrastructure:generate-and-deploy -- TYPE=docker
```

### CI/CD

```bash
# Generate GitHub Actions workflow
task cicd:github-actions

# Generate GitLab CI pipeline
task cicd:gitlab-ci

# Deploy to environment
task cicd:deploy -- ENV=staging

# Check deployment status
task cicd:status -- DEPLOY_ID=deploy-123

# Full pipeline generation and deployment
task cicd:pipeline-and-deploy -- PLATFORM=github-actions ENV=production
```

## System Management

```bash
# Check all agent health
task health

# Start all containers
task compose:up

# Stop all containers
task compose:down

# View all logs
task compose:logs
```

## Copilot Development Patterns

### Pattern 1: Iterative Feature Development

```bash
# 1. Use Copilot to generate feature code in VS Code
# 2. Delegate to feature-dev agent for implementation
task feature-dev:implement -- FEATURE="<your-feature>"

# 3. Run tests
task feature-dev:test

# 4. If tests pass, submit for review
task code-review:review

# 5. If approved, generate docs
task documentation:generate -- TYPE=readme
```

### Pattern 2: Infrastructure as Code

```bash
# 1. Use Copilot to draft requirements
# 2. Generate infrastructure
task infrastructure:generate -- TYPE=terraform

# 3. Review generated IaC
task code-review:review

# 4. Deploy if approved
task cicd:deploy -- ENV=staging
```

### Pattern 3: Pipeline Generation

```bash
# 1. Define pipeline stages with Copilot
# 2. Generate pipeline config
task cicd:generate -- PLATFORM=github-actions

# 3. Review configuration
task code-review:review

# 4. Commit and push (triggers actual pipeline)
```

## Local Development

Each agent can run standalone for local testing:

```bash
# Run orchestrator locally
cd agents/orchestrator
task dev:run

# Run feature-dev locally
cd agents/feature-dev
task dev:run

# Run tests for any agent
cd agents/<agent>
task dev:test
```

## Container Operations

```bash
# Build specific agent image
task orchestrator:build
task feature-dev:build
task code-review:build

# View logs for specific agent
task orchestrator:logs
task feature-dev:logs
task cicd:logs
```

## Environment Variables

Set these to customize agent behavior:

```bash
# Override agent host (default: http://localhost)
export AGENT_HOST=http://dev-tools.local

# Custom ports (defaults in each Taskfile)
export ORCHESTRATOR_PORT=8001
export FEATURE_DEV_PORT=8002
```

## Integration with VS Code

Add to `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Review with Agent",
      "type": "shell",
      "command": "task code-review:review",
      "problemMatcher": []
    },
    {
      "label": "Generate Documentation",
      "type": "shell",
      "command": "task documentation:generate",
      "problemMatcher": []
    }
  ]
}
```

## Troubleshooting

```bash
# Check all services are healthy
task health

# View specific agent logs
task <agent>:logs

# Rebuild agent container
task <agent>:build
cd compose
docker compose up -d <agent>

# Restart all services
task compose:down
task compose:up
```

## Best Practices

1. **Check health first**: Always run `task health` before workflows
2. **Use staged reviews**: Review code before deploying with `task code-review:review`
3. **Leverage RAG**: Query context with `task feature-dev:query-rag` for better code generation
4. **Document incrementally**: Run `task documentation:generate` after each feature
5. **Test locally**: Use `task <agent>:dev:run` for debugging before containerization

## Next Steps

- Review agent READMEs in `agents/<agent>/README.md`
- Check API endpoints in `docs/AGENT_ENDPOINTS.md`
- Explore templates in `templates/` directories
- Configure environment in `configs/env/.env`
