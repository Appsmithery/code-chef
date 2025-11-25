# **Review Checklist:** Migrating from Separate Agent Services to LangGraph Workflow Nodes

This checklist is designed to help identify and update any remaining references to the old architecture where each agent (cicd, code-review, feature-dev, infrastructure, documentation) was a separate service. With the migration to using LangGraph workflow nodes within the orchestrator service, it's crucial to ensure all configurations, manifests, and documentation reflect this change.

---

## 1. **LangGraph Workflow Configuration**

The langgraph service nodes are now stubs, but the **LangGraph StateGraph** in the orchestrator might still reference the old architecture:

```python
# Check if graph.py imports or references the old agent_cicd service pattern
# Should use the stub nodes from shared/services/langgraph/nodes/
```

**Action**: Verify graph.py correctly imports from `shared.services.langgraph.nodes.*` and doesn't expect full agent implementations.

---

## 2. **MCP Tool Mappings**

The **MCP agent-tool mapping** configuration likely references the old `agent_cicd`, `agent_code-review`, etc. services:

```yaml
# Old references like:
# agent_cicd:
#   - cicd
#   - github
#
# Should now map to orchestrator or be removed if nodes are stubs
```

**Action**: Update mcp-agent-tool-mapping.yaml to reflect that these agents are now workflow nodes within orchestrator, not separate services.

---

## 3. **Agent Manifest**

The **agents manifest** (agents-manifest.json) likely lists the old agent services:

```json
{
  "agents": [
    {
      "name": "cicd",
      "service": "agent_cicd", // ❌ Should be "orchestrator" or removed
      "tools": ["cicd", "github"]
    }
  ]
}
```

**Action**: Update manifest to reflect that cicd/code_review/feature_dev/infrastructure/documentation are nodes within orchestrator service.

---

## 4. **Prometheus Metrics Configuration**

The **Prometheus scrape config** might still try to scrape the old agent service endpoints:

```yaml
# Old scrape targets like:
# - targets: ['agent-cicd:8002', 'agent-code-review:8003']
#
# Should only scrape orchestrator:8001 now
```

**Action**: Remove any scrape targets for non-existent agent services from `prometheus.yml`.

---

## 5. **Docker Compose Service Definitions**

Verify no **orphaned service definitions** remain in docker-compose:

```yaml
# Check for services like:
# agent-cicd:
# agent-code-review:
# agent-feature-dev:
# agent-infrastructure:
# agent-documentation:
#
# These should NOT exist if architecture consolidated to orchestrator
```

**Action**: Confirm `docker-compose.yml` has no stale service definitions for the old agent\_\* services.

---

## 6. **Health Check Scripts**

The **health validation scripts** might check endpoints for services that no longer exist:

```bash
# Old checks like:
# curl http://localhost:8002/health  # agent-cicd
# curl http://localhost:8003/health  # agent-code-review
```

**Action**: Update validation scripts to only check the 6 active services (gateway, orchestrator, rag, state, agent-registry, langgraph).

---

## 7. **Environment Variables**

Check for **orphaned environment variables** for the old agent services:

```bash
# Old variables like:
# AGENT_CICD_PORT=8002
# AGENT_CODE_REVIEW_PORT=8003
# LANGSMITH_CICD_PROJECT=agents-cicd
```

**Action**: Clean up any environment variables referencing non-existent agent services.

---

## 8. **Documentation**

The **architecture documentation** needs updates to reflect the new consolidated structure:

```markdown
# Update service topology diagrams

# Remove references to agent_cicd, agent_code-review, etc. as separate services

# Clarify that agents are now LangGraph workflow nodes within orchestrator
```

**Action**: Update `ARCHITECTURE.md`, `DEPLOYMENT_GUIDE.md`, and copilot-instructions.md to reflect current architecture.

---

## 9. **Linear Integration Scripts**

The **Linear update scripts** might reference old agent service names:

```python
# Check for hardcoded agent names like:
# VALID_AGENTS = ["cicd", "code-review", "feature-dev", ...]
#
# Should now use orchestrator or agent node names
```

**Action**: Verify Linear scripts use correct agent identifiers (orchestrator or node names, not old service names).

---

## 10. **Deployment Scripts**

The **deployment automation** might still reference old services:

```powershell
# Check for service restarts like:
# docker compose restart agent-cicd agent-code-review
```

**Action**: Update deployment scripts to only manage the 6 active services.

---

## Recommended Next Steps

1. **Run a global search** for `agent_cicd`, `agent-cicd`, `agent_code-review`, etc. across the entire repository
2. **Check configuration files** in config directory for stale references
3. **Validate docker-compose** with `docker compose config` to catch orphaned service definitions
4. **Update health checks** to only monitor active services
5. **Document the architecture change** in docs with migration guide
