# Linear Access Architecture Analysis

### Current State: **Only Orchestrator Needs Linear Access**

| Component                                      | Linear Access? | What It Does                                                    |
| ---------------------------------------------- | -------------- | --------------------------------------------------------------- |
| **Orchestrator** (main.py, workflow_engine.py) | ✅ YES         | Creates issues, updates status, adds comments, handles webhooks |
| **Subagent Nodes** (graph.py nodes)            | ❌ NO          | Just execute tasks, return results to orchestrator              |
| **Base Agent** (base_agent.py)                 | ❌ NO          | MCP tools + LLM only, no Linear                                 |

### How It Works:

```
User Task → Orchestrator
              ↓
         Creates parent Linear issue (via LinearWorkspaceClient)
              ↓
         Decomposes → Creates subissues for each subtask
              ↓
         Routes to agent nodes (feature_dev, code_review, etc.)
              ↓
         Agent nodes execute (LLM + MCP tools)
              ↓
         Return results to orchestrator
              ↓
         Orchestrator updates Linear issues with results
```

**Key insight**: Subagents are **nodes within the same process**, not separate services. They don't need their own Linear access - the orchestrator handles all Linear operations.

---

## Revised Minimal Linear Integration Plan

### What You Need (Keep):

| Variable                        | Purpose                           | Required? |
| ------------------------------- | --------------------------------- | --------- |
| `LINEAR_API_KEY`                | GraphQL API access (orchestrator) | ✅ YES    |
| `LINEAR_TEAM_ID`                | Default team for issues           | ✅ YES    |
| `LINEAR_WEBHOOK_SIGNING_SECRET` | Verify HITL approval webhooks     | ✅ YES    |

### What You DON'T Need (Remove):

| Variable                             | Purpose            | Why Remove?                             |
| ------------------------------------ | ------------------ | --------------------------------------- |
| `LINEAR_OAUTH_CLIENT_ID`             | Gateway OAuth flow | Gateway being removed                   |
| `LINEAR_OAUTH_CLIENT_SECRET`         | Gateway OAuth flow | Gateway being removed                   |
| `LINEAR_OAUTH_DEV_TOKEN`             | Gateway fallback   | Duplicate of API_KEY                    |
| `LINEAR_WEBHOOK_URL`                 | Reference only     | Not used in code                        |
| `LINEAR_ORCHESTRATOR_WEBHOOK_SECRET` | Duplicate/unused   | `LINEAR_WEBHOOK_SIGNING_SECRET` is used |

### Final .env Linear Section:

```bash
# ============================================================================
# LINEAR INTEGRATION
# ============================================================================
# Structural config: config/linear/linear-config.yaml
# Python client: shared/lib/linear_workspace_client.py

# API Key (OAuth token for GraphQL API - orchestrator only)
LINEAR_API_KEY=lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571

# Team Configuration
LINEAR_TEAM_ID=f5b610be-ac34-4983-918b-2c9d00aa9b7a

# Webhook Security (for HITL emoji approvals)
LINEAR_WEBHOOK_SIGNING_SECRET=lin_wh_o4QCab9NgVsGjJAe8rOCpk6q4fMLtmvlGQQNBrdqbGIC
```

### Gateway Removal Checklist:

1. ✅ **Linear API access** - Orchestrator uses `LinearWorkspaceClient` directly
2. ✅ **Webhook handling** - Orchestrator has `/webhooks/linear` endpoint
3. ✅ **OAuth token** - Already in .env as `LINEAR_API_KEY`
4. ⚠️ **Fix webhook URL** in Linear settings: `https://theshop.appsmithery.co/webhooks/linear`

### Summary:

**The gateway can be safely removed.** The orchestrator is the single point of Linear integration:

- Creates/updates issues via `LinearWorkspaceClient`
- Handles webhooks at `/webhooks/linear`
- Subagents don't need Linear access (they're nodes, not services)
