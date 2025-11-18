# Repository Reorganization Plan - Agent-Centric Architecture

## Executive Summary

Restructure Dev-Tools from artifact-based organization to agent-centric organization, where each agent is a self-contained unit with all its required files in one place.

## Decisions Made

- ✅ **No symlinks** - Clean migration, remove deprecated `chatmodes/` entirely
- ✅ **Monorepo** - Keep all agents in one repository with distinct directories
- ✅ **Shared config** - Continue using single `.env` in `infrastructure/config/env/` accessed by all agents
- ✅ **Integration tests** - Create `tests/integration/` for cross-agent workflows

## Target Structure

```
Dev-Tools/
├── agents/
│   ├── _shared/                      # Shared utilities and base classes
│   │   ├── __init__.py
│   │   ├── mcp_client.py
│   │   ├── gradient_client.py
│   │   ├── langgraph_base.py
│   │   ├── qdrant_client.py
│   │   ├── langchain_memory.py
│   │   ├── observability.py          # Langfuse + Prometheus setup
│   │   └── requirements.txt
│   │
│   ├── orchestrator/
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── models.py
│   │   │   ├── service.py
│   │   │   └── routes/
│   │   ├── config/
│   │   │   └── routing-rules.yaml    # Agent-specific config
│   │   ├── tests/
│   │   │   ├── test_orchestrator.py
│   │   │   └── fixtures/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── README.md
│   │
│   ├── feature-dev/
│   │   ├── src/
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── README.md
│   │
│   ├── code-review/
│   ├── infrastructure/
│   ├── cicd/
│   ├── documentation/
│   ├── rag/
│   ├── state/
│   └── langgraph/
│
├── gateway/                          # MCP Gateway (infrastructure boundary)
│   ├── src/
│   │   ├── index.js
│   │   ├── server.js
│   │   └── routes/
│   ├── servers/                      # MCP server implementations
│   │   ├── github/
│   │   ├── linear/
│   │   ├── filesystem/
│   │   ├── postgres/
│   │   └── ...
│   ├── config/
│   ├── tests/
│   ├── Dockerfile
│   ├── package.json
│   └── README.md
│
├── infrastructure/                   # Deployment & orchestration
│   ├── compose/
│   │   ├── docker-compose.yml
│   │   ├── docker-compose.override.yml.example
│   │   └── networks.env
│   ├── config/
│   │   ├── env/
│   │   │   ├── .env.template
│   │   │   ├── .env                  # Shared by all agents (gitignored)
│   │   │   └── secrets/              # Docker secrets
│   │   ├── caddy/
│   │   ├── prometheus/
│   │   └── postgres/
│   │       └── schema.sql
│   ├── workflows/
│   │   └── docker-hub-deploy.yml
│   ├── scripts/
│   │   ├── deploy.ps1
│   │   ├── push-dockerhub.ps1
│   │   ├── backup_volumes.sh
│   │   └── validate-tracing.sh
│   └── README.md
│
├── docs/
│   ├── README.md                     # Documentation index
│   ├── architecture/
│   │   ├── AGENTS.md
│   │   ├── MCP_INTEGRATION.md
│   │   ├── OBSERVABILITY.md
│   │   └── HYBRID_ARCHITECTURE.md
│   ├── deployment/
│   │   ├── DOCKER_HUB.md
│   │   ├── LOCAL_DEV.md
│   │   └── DROPLET_SETUP.md
│   ├── guides/
│   │   ├── ADDING_NEW_AGENT.md
│   │   └── TRACING_SETUP.md
│   └── _temp/                        # Working files (gitignored)
│
├── templates/
│   ├── agent/                        # Template for new agents
│   │   ├── src/
│   │   ├── tests/
│   │   ├── Dockerfile.template
│   │   ├── requirements.txt.template
│   │   └── README.md.template
│   ├── pipelines/
│   └── docs/
│
├── tests/
│   ├── integration/                  # Cross-agent integration tests
│   │   ├── test_orchestration.py
│   │   ├── test_mcp_gateway.py
│   │   └── conftest.py
│   └── e2e/                          # End-to-end workflow tests
│       └── test_full_stack.py
│
├── .github/
│   └── workflows/                    # Symlink to infrastructure/workflows/
│
├── .gitignore
├── README.md
└── Taskfile.yml
```

## Migration Steps

### Phase 1: Create New Structure (Parallel to Old)

1. Create new directory structure
2. Copy files to new locations (don't move yet)
3. Update Dockerfiles to use new paths
4. Update docker-compose.yml build contexts
5. Test locally

### Phase 2: Update CI/CD & Configs

1. Move `.github/workflows/` → `infrastructure/workflows/`
2. Create symlink `.github/workflows/` → `infrastructure/workflows/`
3. Update workflow paths to reference new structure
4. Update compose env_file paths if needed
5. Test CI/CD pipeline

### Phase 3: Update Imports & Code

1. Ensure `agents/_shared/` has proper `__init__.py`
2. No import changes needed (already using `agents._shared`)
3. Verify all agents can import shared modules
4. Test all agents start successfully

### Phase 4: Cleanup & Documentation

1. Delete old structure (`containers/`, `mcp/`, `compose/`, `config/`)
2. Delete deprecated `chatmodes/`
3. Update all documentation with new paths
4. Update root README with new structure
5. Create `templates/agent/` for future agent scaffolding

## File Migrations

### Agents (orchestrator as example)

```
agents/orchestrator/main.py              → agents/orchestrator/src/main.py
agents/orchestrator/models.py            → agents/orchestrator/src/models.py
agents/orchestrator/service.py           → agents/orchestrator/src/service.py
agents/orchestrator/requirements.txt     → agents/orchestrator/requirements.txt (stays)
containers/orchestrator/Dockerfile       → agents/orchestrator/Dockerfile
config/routing/task-router.rules.yaml    → agents/orchestrator/config/routing-rules.yaml
```

### Gateway

```
mcp/gateway/*                            → gateway/src/
mcp/servers/*                            → gateway/servers/
containers/gateway-mcp/Dockerfile        → gateway/Dockerfile
```

### Infrastructure

```
compose/                                 → infrastructure/compose/
config/                                  → infrastructure/config/
scripts/                                 → infrastructure/scripts/
.github/workflows/                       → infrastructure/workflows/
```

### Documentation

```
docs/AGENT_ENDPOINTS.md                  → docs/architecture/AGENTS.md
docs/MCP_INTEGRATION.md                  → docs/architecture/MCP_INTEGRATION.md
docs/DOCKER_HUB_DEPLOYMENT.md            → docs/deployment/DOCKER_HUB.md
docs/DEPLOYMENT.md                       → docs/deployment/DROPLET_SETUP.md
docs/chatmodes/*                         → DELETE
docs/_temp/revised-architecture-*        → DELETE (consolidated into architecture/)
```

## Docker Compose Updates

```yaml
# infrastructure/compose/docker-compose.yml
services:
  orchestrator:
    build:
      context: ../../agents/orchestrator
      dockerfile: Dockerfile
    env_file:
      - ../config/env/.env
    # ...

  gateway-mcp:
    build:
      context: ../../gateway
      dockerfile: Dockerfile
    env_file:
      - ../config/env/.env
    # ...
```

## Dockerfile Updates

```dockerfile
# agents/orchestrator/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy requirements first (layer caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY ../_shared/ ./agents/_shared/

# Copy agent source
COPY src/ ./

EXPOSE 8001
CMD ["python", "main.py"]
```

## Benefits

| Aspect              | Before                                  | After                                |
| ------------------- | --------------------------------------- | ------------------------------------ |
| **Navigation**      | 5+ directories to find agent files      | 1 directory per agent                |
| **Agent isolation** | Shared files mixed with agent code      | Clear boundaries                     |
| **New agent**       | Copy files from 4 dirs + update 6 files | Copy 1 template dir + update compose |
| **Testing**         | Tests scattered                         | Tests co-located with code           |
| **Documentation**   | Docs by artifact type                   | Docs by agent + topic                |
| **Infrastructure**  | Mixed with application code             | Clean separation                     |

## Rollout Timeline

- **Day 1**: Run migration script, create new structure
- **Day 2**: Update docker-compose.yml, test locally
- **Day 3**: Update CI/CD workflows, test on droplet
- **Day 4**: Update documentation, create templates
- **Day 5**: Delete old structure, final validation

## Automation Scripts

1. **migrate-structure.ps1** - Main migration orchestrator
2. **create-agent-dirs.ps1** - Create new directory structure
3. **move-agent-files.ps1** - Move files to new locations
4. **update-dockerfiles.ps1** - Update all Dockerfiles with new paths
5. **cleanup-old-structure.ps1** - Remove deprecated files
6. **validate-migration.ps1** - Verify all files moved correctly

## Validation Checklist

- [ ] All agent folders exist with correct structure
- [ ] All Dockerfiles build successfully
- [ ] docker-compose.yml references correct build contexts
- [ ] CI/CD workflow runs successfully
- [ ] All agents start and respond to health checks
- [ ] Shared modules import correctly
- [ ] Documentation updated with new paths
- [ ] Old structure removed
- [ ] Templates created for future agents
- [ ] Integration tests pass

## Rollback Plan

If migration fails:

1. Revert git commits
2. Restore from `scripts/backup_volumes.sh` if needed
3. Keep old structure until issues resolved
4. Document blockers and adjust plan

## Next Steps

1. Generate automation scripts
2. Run migration on local dev environment
3. Test locally with `docker compose up`
4. Push to git, trigger CI/CD
5. Validate on droplet
6. Update documentation
7. Create agent template
