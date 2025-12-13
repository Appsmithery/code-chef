# Development Guide

**Quick Reference for Local Development**

---

## 🚀 Getting Started

### Prerequisites

- Docker Desktop installed and running
- Python 3.11+ with virtual environment activated
- VS Code with recommended extensions:
  - Docker (ms-azuretools.vscode-docker)
  - Python (ms-python.python)
  - GitHub Pull Requests and Issues

### First Time Setup

1. **Clone the repository**:

   ```bash
   git clone https://github.com/Appsmithery/code-chef.git
   cd code-chef
   ```

2. **Set up Python environment**:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or
   source .venv/bin/activate  # Linux/Mac

   pip install -r agent_orchestrator/requirements.txt
   pip install -r support/tests/requirements.txt
   ```

3. **Configure environment variables**:

   - Copy `config/env/.env.example` to `config/env/.env`
   - Add required API keys (Gradient, Linear, OpenRouter, etc.)
   - See [Secrets Management Guide](support/docs/operations/SECRETS_MANAGEMENT.md) for details

4. **Start the local stack**:
   ```bash
   cd deploy
   docker compose up -d
   ```

---

## 🐳 Docker Operations

### Starting Services

**Method 1: VS Code UI (Recommended)**

1. Open [deploy/docker-compose.yml](deploy/docker-compose.yml)
2. Right-click anywhere in the file
3. Select **Compose Up**
4. View running containers in **Container Tools** sidebar

**Method 2: Command Line**

```bash
cd deploy
docker compose up -d
```

### Viewing Logs

**Via Container Tools Sidebar**:

- Click on a container → **Logs** tab
- Or right-click container → **View Logs**

**Via Command Line**:

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f orchestrator

# Last 100 lines
docker compose logs --tail=100 -f
```

### Stopping Services

**Via VS Code**:

1. Right-click [deploy/docker-compose.yml](deploy/docker-compose.yml)
2. Select **Compose Down**

**Via Command Line**:

```bash
cd deploy
docker compose down --remove-orphans
```

### Rebuilding Services

**After code changes**:

1. Right-click compose file → **Compose Down**
2. Right-click compose file → **Compose Up**
3. Or use command line:
   ```bash
   docker compose down
   docker compose up -d --build
   ```

### Cleaning Up

**Remove unused containers/images**:

```bash
docker system prune -f
docker builder prune -f
```

---

## 🧪 Running Tests

### Via VS Code Tasks

Press `Ctrl+Shift+P` → **Tasks: Run Task** → Select:

- **Run All Tests** - Full test suite
- **Run E2E Tests** - End-to-end scenarios
- **Run Integration Tests** - Cross-service integration
- **Run Unit Tests** - Unit tests only
- **Run Performance Tests** - Performance benchmarks
- **Run Tests with Coverage** - Generate coverage report
- **Open Coverage Report** - View HTML coverage

Or use keyboard shortcut: `Ctrl+Shift+B` (Build)

### Via Command Line

```bash
# All tests
pytest support/tests -v

# Specific test types
pytest support/tests/e2e -v -s
pytest support/tests/integration -v -s
pytest support/tests -v -m unit

# With coverage
pytest support/tests -v --cov=agent_orchestrator --cov=shared --cov-report=html
```

### Test Markers

```bash
# Skip tracing tests (faster for dev)
pytest support/tests -v -m "not trace"

# Only property-based tests
pytest support/tests/evaluation/test_property_based.py -v

# Specific hypothesis profile
HYPOTHESIS_PROFILE=ci pytest support/tests/evaluation/test_property_based.py -v
```

---

## 🏗️ Architecture Overview

### Services & Ports

| Service            | Port | Purpose                        | Health Endpoint  |
| ------------------ | ---- | ------------------------------ | ---------------- |
| **orchestrator**   | 8001 | Task routing, LangGraph        | `/health`        |
| **rag-context**    | 8007 | RAG retrieval, embeddings      | `/health`        |
| **state-persist**  | 8008 | Checkpoint storage             | `/health`        |
| **agent-registry** | 8009 | Agent heartbeat, discovery     | `/health`        |
| **langgraph**      | 8010 | LangGraph workflow API         | `/health`        |
| **postgres**       | 5432 | State persistence              | `pg_isready`     |
| **redis**          | 6379 | Event bus, caching             | `redis-cli ping` |
| **prometheus**     | 9090 | Metrics collection             | `/-/healthy`     |
| **grafana**        | 3000 | Metrics visualization          | `/api/health`    |
| **loki**           | 3100 | Log aggregation                | `/ready`         |
| **caddy**          | 80   | Reverse proxy, TLS termination | HTTP 200 on root |

### Health Checks

All services have native Docker healthchecks. View health status in **Container Tools** sidebar:

- ✅ **Green** = Healthy
- ⏳ **Starting** = Waiting for health check
- ❌ **Red** = Unhealthy (check logs)

### Key Directories

```
code-chef/
├── agent_orchestrator/       # LangGraph + FastAPI orchestration
│   ├── agents/               # Supervisor + specialist agents
│   ├── workflows/            # Event-sourced workflow engine
│   └── graph.py              # LangGraph StateGraph definition
├── shared/                   # Shared libraries
│   ├── lib/                  # HITL, MCP loader, risk assessment
│   ├── mcp/                  # MCP client
│   └── services/             # FastAPI microservices
├── config/                   # Configuration files
│   ├── agents/models.yaml    # Model assignments (single source)
│   ├── hitl/                 # HITL approval policies
│   ├── linear/               # Linear integration config
│   ├── mcp-agent-tool-mapping.yaml  # MCP tool routing
│   └── routing/task-router.rules.yaml  # Heuristic routing
├── deploy/
│   └── docker-compose.yml    # All service definitions
├── extensions/
│   └── vscode-codechef/      # VS Code extension
└── support/
    ├── docs/                 # Architecture, deployment guides
    ├── scripts/              # Utility scripts
    └── tests/                # Test suites
```

---

## 🔧 Common Development Tasks

### Modifying Agent Behavior

1. Edit agent system prompt: `agent_orchestrator/agents/<agent>/system.prompt.md`
2. Update tool configuration: `agent_orchestrator/agents/<agent>/tools.yaml`
3. Restart orchestrator: `docker compose restart orchestrator`

### Adding a New Agent Node

See [support/docs/ARCHITECTURE.md](support/docs/ARCHITECTURE.md) for detailed instructions.

**Quick steps**:

1. Create `agent_orchestrator/agents/<name>/` with `__init__.py`, `system.prompt.md`, `tools.yaml`
2. Inherit from `_shared.base_agent.BaseAgent`
3. Wire into `graph.py` StateGraph
4. Update `config/mcp-agent-tool-mapping.yaml`
5. Add to `get_agent()` cache

### Changing Model Assignments

**Single source of truth**: `config/agents/models.yaml`

```yaml
agents:
  feature_dev:
    model: qwen/qwen-2.5-coder-32b-instruct
    cost_per_1m_tokens: 0.07
    context_window: 131072
    max_tokens: 8192
    temperature: 0.3
```

After changes: `docker compose restart orchestrator`

### Working with Workflows

**Declarative workflow templates**: `agent_orchestrator/workflows/templates/*.yaml`

Example:

```yaml
id: code_review_workflow
description: Code review with automated feedback
steps:
  - agent: code_review
    action: analyze_changes
    requires_approval: false
  - agent: feature_dev
    action: implement_fixes
    requires_approval: true # HITL gate
```

**Testing workflows**:

```bash
pytest support/tests/integration/test_workflow_engine.py -v -s
```

### Debugging Issues

**Check service health**:

```bash
# All services
curl http://localhost:8001/health | jq

# Specific service
curl http://localhost:8007/health | jq
curl http://localhost:8008/health | jq
```

**View detailed logs**:

```bash
# Orchestrator (most common)
docker compose logs -f orchestrator

# All agent services
docker compose logs -f orchestrator rag-context state-persistence

# Database queries
docker compose logs -f postgres | grep -i error
```

**Connect to PostgreSQL**:

```bash
docker compose exec postgres psql -U devtools -d devtools

# View tables
\dt

# Check checkpoints
SELECT thread_id, checkpoint_ns, step FROM checkpoints ORDER BY step DESC LIMIT 10;
```

**Redis inspection**:

```bash
docker compose exec redis redis-cli

# Check event bus
KEYS *
GET <key>
```

---

## 🚀 Deployment

### Production Deployment

**DO NOT manually SSH to deploy!** Use GitHub Actions:

1. **Automatic deployment** (on push to `main`):

   - Workflow: `.github/workflows/intelligent-deploy-to-droplet.yml`
   - Triggers on changes to agent/infrastructure code

2. **Manual frontend deployment**:
   - Go to **Actions** tab
   - Select **Deploy Frontend to Production**
   - Click **Run workflow**

### Droplet Access (Emergency Only)

```bash
# SSH access
ssh root@45.55.173.72

# Check services
cd /opt/Dev-Tools
docker compose ps

# View logs
docker compose logs -f --tail=100

# Restart services
docker compose restart <service-name>

# Full restart
docker compose down && docker compose up -d
```

**Droplet Details**:

- **IP**: 45.55.173.72
- **Domain**: codechef.appsmithery.co
- **Path**: `/opt/Dev-Tools`
- **Provider**: DigitalOcean (NYC3 region)

### Verification After Deploy

1. **Health checks**:

   ```bash
   curl https://codechef.appsmithery.co/health | jq
   ```

2. **View Grafana metrics**:

   - URL: https://codechef.appsmithery.co/grafana
   - Credentials in 1Password

3. **Check LangSmith traces**:
   - Project: `code-chef-production`
   - URL: https://smith.langchain.com

---

## 📊 Observability

### LangSmith Tracing

**Projects** (purpose-based):

- `code-chef-production` - Live extension usage
- `code-chef-training` - Model training ops
- `code-chef-evaluation` - Model evaluations
- `code-chef-experiments` - A/B testing

**Environment Variables**:

```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=lsv2_sk_***
export TRACE_ENVIRONMENT=production
export EXPERIMENT_GROUP=code-chef
```

**Filtering traces**:

```
environment:"production" AND module:"feature_dev"
experiment_id:"exp-2025-01-001"
task_id:"task-uuid"
```

### Grafana Dashboards

**URL**: https://appsmithery.grafana.net

**Key Dashboards**:

- **LLM Token Metrics** - Token usage, cost tracking
- **Agent Performance** - Latency, success rates
- **Container Health** - CPU, memory, restarts

**Prometheus Queries**:

```promql
# Token usage (24h)
increase(llm_tokens_total[24h]) by (agent)

# P95 latency
histogram_quantile(0.95, rate(llm_latency_seconds_bucket[5m]))

# Daily cost
sum(increase(llm_cost_usd_total[24h]))
```

### Local Metrics

**Prometheus**: http://localhost:9090  
**Grafana**: http://localhost:3000

---

## 🆘 Troubleshooting

### Container Won't Start

```bash
# View startup logs
docker compose logs <service-name>

# Check resource limits
docker stats

# Verify dependencies
docker compose ps
```

**Common causes**:

- Missing environment variables → Check `config/env/.env`
- Port conflicts → Check if port already in use
- Database not ready → Wait for postgres healthcheck

### Tests Failing

```bash
# Clear pytest cache
rm -rf .pytest_cache __pycache__

# Reinstall dependencies
pip install -r support/tests/requirements.txt

# Check Python environment
python --version  # Should be 3.11+
which python      # Should be in .venv
```

### Can't Connect to Services

```bash
# Verify services running
docker compose ps

# Check health status
docker compose ps --format json | jq '.[] | {name: .Name, health: .Health}'

# Restart specific service
docker compose restart <service-name>

# Nuclear option: full restart
docker compose down && docker compose up -d
```

### Database Issues

```bash
# Reset database
docker compose down
docker volume rm deploy_postgres-data
docker compose up -d

# Or preserve data but reinit schema
docker compose exec postgres psql -U devtools -d devtools -f /docker-entrypoint-initdb.d/agent_registry.sql
```

---

## � Linear & GitHub Integration

### Overview

code-chef integrates with Linear and GitHub for bidirectional issue tracking. All agents have unique identifiers that show up in commits, PRs, and Linear issues.

### Agent Identifiers

| Agent              | GitHub Identifier          | Commit Author                                   |
| ------------------ | -------------------------- | ----------------------------------------------- |
| **Orchestrator**   | `code-chef`                | `code-chef <code-chef@appsmithery.co>`          |
| **Feature Dev**    | `code-chef/feature-dev`    | `code-chef feature-dev <feature-dev@...>`       |
| **Code Review**    | `code-chef/code-review`    | `code-chef code-review <code-review@...>`       |
| **Infrastructure** | `code-chef/infrastructure` | `code-chef infrastructure <infrastructure@...>` |
| **CI/CD**          | `code-chef/cicd`           | `code-chef cicd <cicd@...>`                     |
| **Documentation**  | `code-chef/documentation`  | `code-chef documentation <documentation@...>`   |

### Linking Commits to Linear Issues

Use **magic words** in commit messages to link to Linear issues:

```bash
# Close an issue
git commit -m "feat: add JWT auth

Implements token-based authentication.

Fixes DEV-123
Orchestrated by: code-chef"

# Reference an issue
git commit -m "refactor: optimize database queries

Part of DEV-456
Implemented by: code-chef/infrastructure"

# Multiple issues
git commit -m "feat: add user dashboard

Fixes DEV-789
References DEV-790
Related to DEV-791

Implemented by: code-chef/feature-dev
Coordinated by: code-chef"
```

**Magic words**:

- **Closes issue**: `Fixes`, `Closes`, `Resolves`
- **References issue**: `Refs`, `References`, `Part of`, `Related to`

### PR Format

PRs created by agents follow this format:

```markdown
Title: [code-chef/feature-dev] Add user authentication

Description:

## Summary

Implements JWT-based authentication with refresh tokens

## Changes

- Add JWT middleware
- Implement token refresh endpoint
- Add authentication tests

## Linear Issues

Fixes DEV-123
References DEV-45

## Agent Attribution

- **Agent**: 🚀 Feature Dev
- **Identifier**: code-chef/feature-dev
- **Coordinated by**: code-chef orchestrator

---

🤖 This PR was created by the code-chef agentic platform
```

### Multi-Repo Setup

code-chef can work across **any repository** in the Appsmithery organization:

**Organization-Level Webhook** (Recommended):

1. Go to https://github.com/organizations/Appsmithery/settings/hooks
2. Add webhook with Linear payload URL (see [config/linear/github-webhook-config.yaml](config/linear/github-webhook-config.yaml))
3. Select recommended events (see below)
4. **Result**: All repos automatically get Linear integration

**Recommended Events**:

- ✅ **Essential**: `push`, `pull_request`, `pull_request_review`, `issues`, `issue_comment`
- ✅ **Recommended**: `pull_request_review_comment`, `commit_comment`, `release`, `deployment`, `check_run`, `status`
- ⚪ **Optional**: `project_card`, `milestone`, `label`

**Benefits**:

- ✅ Single webhook for all repos
- ✅ Automatic coverage for new repos
- ✅ Consistent Linear integration
- ✅ Centralized management

### Using code-chef in Other Repos

When working in a different repo (e.g., `Appsmithery/another-project`):

1. **Linear Project**: Create or use existing Linear project
2. **Agent Assignment**: Update [config/linear/agent-project-mapping.yaml](config/linear/agent-project-mapping.yaml)
3. **Commit Format**: Same identifiers work across all repos
4. **Magic Words**: `Fixes DEV-XXX` works regardless of repo

**Example workflow**:

```bash
# In another-project repo
git commit -m "feat: add new feature

Implements feature X for another-project.

Fixes DEV-999
Implemented by: code-chef/feature-dev"

# Linear issue DEV-999 automatically updated with:
# - Commit reference
# - Repo: Appsmithery/another-project
# - Author: code-chef/feature-dev
```

### GitHub Issues Sidebar

With Linear GitHub integration enabled:

- ✅ All Linear issues appear in VS Code GitHub Issues sidebar
- ✅ Issues sync bidirectionally (Linear ↔ GitHub)
- ✅ Comments sync between platforms
- ✅ Status changes reflect in both systems

**View issues**:

1. Open GitHub sidebar (Activity Bar)
2. Expand **Issues** section
3. See all Linear issues synced to GitHub

### Configuration Files

| File                                                                                 | Purpose                                   |
| ------------------------------------------------------------------------------------ | ----------------------------------------- |
| [config/linear/agent-project-mapping.yaml](config/linear/agent-project-mapping.yaml) | Agent identifiers and project assignments |
| [config/linear/github-webhook-config.yaml](config/linear/github-webhook-config.yaml) | GitHub webhook setup and event config     |
| [config/linear/linear-config.yaml](config/linear/linear-config.yaml)                 | Linear API configuration                  |

---

## �📚 Additional Resources

- **Architecture**: [support/docs/ARCHITECTURE.md](support/docs/ARCHITECTURE.md)
- **Deployment**: [support/docs/DEPLOYMENT.md](support/docs/DEPLOYMENT.md)
- **LLM Operations**: [support/docs/operations/llm-operations.md](support/docs/operations/llm-operations.md)
- **Linear Integration**: [config/linear/AGENT_QUICK_REFERENCE.md](config/linear/AGENT_QUICK_REFERENCE.md)
- **Workflow Engine**: [agent_orchestrator/workflows/WORKFLOW_QUICK_REFERENCE.md](agent_orchestrator/workflows/WORKFLOW_QUICK_REFERENCE.md)

---

## 💡 Tips & Best Practices

### Development Workflow

1. **Use Container Tools** for all Docker operations (avoid CLI)
2. **Enable auto-save** (`files.autoSave: "onWindowChange"`)
3. **Run tests frequently** (use VS Code Test Explorer)
4. **Monitor logs** while developing (Container Tools sidebar)
5. **Create Linear issues** for all production changes

### Code Quality

1. **Use type hints** and Pydantic models
2. **Add `@traceable`** decorators for LangSmith visibility
3. **Write tests** for new features (aim for 80%+ coverage)
4. **Follow Black formatting** (auto-formats on save)
5. **Update docs** when changing architecture

### Performance

1. **Use progressive tool loading** (MINIMAL → PROGRESSIVE → FULL)
2. **Cache LLM responses** for repetitive queries
3. **Set reasonable `max_tokens`** to control costs
4. **Monitor token usage** (`/metrics/tokens` endpoint)
5. **Use cheaper models** for dev/test environments

### Security

1. **Never commit secrets** (use `config/env/secrets/`)
2. **Rotate API keys** regularly
3. **Use HITL approval** for high-risk operations
4. **Review Linear webhooks** before production deploy
5. **Enable GitHub 2FA** and protect main branch

---

**Questions?** File an issue in [Linear](https://linear.app/dev-ops/project/codechef-78b3b839d36b) with label `documentation`.
