# LangGraph Studio Setup Guide

## Overview

LangGraph Studio provides interactive visualization and debugging for your multi-agent workflows. This guide covers local setup and remote connection options.

## Prerequisites

✅ **Already Installed**:

- `langgraph-cli` (installed via `pip install -U "langgraph-cli[inmem]"`)
- API Key generated: `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`

## Quick Start (Local Visualization)

### 1. Configuration Files

Two files have been created for you:

**`langgraph.json`** - LangGraph Studio configuration:

```json
{
  "dependencies": ["."],
  "graphs": {
    "orchestrator": "./agent_orchestrator/graph.py:app"
  },
  "env": ".env.local"
}
```

**`.env.local`** - Local environment variables (connects to droplet services)

### 2. Launch LangGraph Studio

```powershell
# From repository root
cd D:\INFRA\Dev-Tools\Dev-Tools

# Start the LangGraph dev server
langgraph dev

# Alternative: Specify custom port
langgraph dev --port 8123
```

### 3. Access Studio UI

Once started, open your browser to:

- **Default**: http://localhost:8123
- Studio will auto-open in your default browser

### 4. Visualize Your Workflow

In LangGraph Studio you'll see:

- **Graph Tab**: Interactive visualization of StateGraph
  - Supervisor node (pink)
  - 5 Agent nodes (blue): feature-dev, code-review, infrastructure, cicd, documentation
  - Conditional edges showing routing logic
  - Approval gates (interrupt nodes)
- **State Tab**: Current workflow state at each node
- **Threads Tab**: All workflow execution threads
- **Run Tab**: Execute workflows with custom inputs

## Architecture Options

### Option A: Hybrid (Recommended for Dev)

**What**: Run LangGraph Studio locally, connect to droplet services

**Benefits**:

- ✅ Fast visualization updates
- ✅ No need to run all services locally
- ✅ Real checkpoints from production PostgreSQL
- ✅ Same environment as production

**Configuration** (already set in `.env.local`):

```bash
DB_HOST=45.55.173.72              # Use droplet PostgreSQL
MCP_GATEWAY_URL=http://45.55.173.72:8000  # Use droplet MCP gateway
LINEAR_API_KEY=lin_oauth_***      # Same Linear access
```

**Firewall Note**: Droplet PostgreSQL (5432) must allow your IP. Check with:

```powershell
ssh root@45.55.173.72 "ufw status"
```

If blocked, allow your IP:

```powershell
ssh root@45.55.173.72 "ufw allow from YOUR_IP to any port 5432"
```

### Option B: Fully Local

**What**: Run all services locally (PostgreSQL, Redis, MCP Gateway, etc.)

**When to Use**: Offline development, testing changes to services

**Setup**:

```powershell
# 1. Start local services via Docker Compose
cd deploy
docker-compose -f docker-compose.local.yml up -d postgres redis gateway-mcp

# 2. Update .env.local
DB_HOST=localhost
MCP_GATEWAY_URL=http://localhost:8000

# 3. Run LangGraph Studio
langgraph dev
```

### Option C: Remote Only

**What**: Use LangGraph Cloud (paid) to visualize remote deployments

**When to Use**: Team collaboration, production monitoring

**Setup**:

1. Deploy to LangGraph Cloud: `langgraph deploy`
2. Access at: `https://your-app.langchain.app`

## Workflow Visualization Features

### 1. Graph Structure View

Shows your current StateGraph:

```
START
  ↓
supervisor (conditional router)
  ├→ feature_dev
  ├→ code_review
  ├→ infrastructure
  ├→ cicd
  └→ documentation
     ↓
approval_gate (interrupt)
     ↓
END
```

### 2. Interactive Execution

**Test Workflows**:

1. Click "New Thread" in Studio
2. Provide input:
   ```json
   {
     "messages": [
       { "role": "user", "content": "Implement user authentication" }
     ],
     "task": "feature-dev"
   }
   ```
3. Click "Run"
4. Watch execution flow in real-time
5. Inspect state at each node

### 3. Checkpoint Inspection

See workflow state at interrupts:

- **Before approval_gate**: Shows task awaiting approval
- **After approval_gate**: Shows approved task resuming
- **State history**: Full timeline of state changes

### 4. Debug Mode

Enable detailed logging:

```powershell
langgraph dev --verbose
```

See:

- Tool invocations
- LLM calls and responses
- State mutations
- Edge routing decisions

## Troubleshooting

### Issue: "Module not found: lib.mcp_client"

**Cause**: Studio can't find shared libraries

**Fix**: Add to Python path

```powershell
$env:PYTHONPATH = "D:\INFRA\Dev-Tools\Dev-Tools\shared;$env:PYTHONPATH"
langgraph dev
```

Or add to `.env.local`:

```bash
PYTHONPATH=./shared:./agent_orchestrator
```

### Issue: "Connection refused: PostgreSQL"

**Cause**: Droplet firewall blocking port 5432

**Fix 1**: Use SSH tunnel

```powershell
# Create tunnel (keep running in separate terminal)
ssh -L 5432:localhost:5432 root@45.55.173.72

# Update .env.local
DB_HOST=localhost
```

**Fix 2**: Use SQLite locally

```bash
# In .env.local
DB_HOST=sqlite:///./langgraph.db
```

### Issue: "Graph not found"

**Cause**: Graph export path incorrect in `langgraph.json`

**Fix**: Verify graph.py exports `app`:

```python
# agent_orchestrator/graph.py
app = create_workflow()  # ✅ Correct
```

Update `langgraph.json` if needed:

```json
{
  "graphs": {
    "orchestrator": "./agent_orchestrator/graph.py:app"
  }
}
```

### Issue: Studio shows empty graph

**Cause**: Graph compiled but has no nodes

**Fix**: Check graph definition:

```python
from agent_orchestrator.graph import app

# Should print node list
print(app.get_graph().nodes)
```

## Advanced: Multiple Graphs

Visualize individual agent nodes:

**Update `langgraph.json`**:

```json
{
  "graphs": {
    "orchestrator": "./agent_orchestrator/graph.py:app",
    "feature_dev_solo": "./agent_orchestrator/agents/feature_dev.py:feature_dev_graph"
  }
}
```

**Create agent-specific graph** (example for feature_dev):

```python
# agent_orchestrator/agents/feature_dev.py

from langgraph.graph import StateGraph

def create_feature_dev_graph():
    workflow = StateGraph(WorkflowState)
    workflow.add_node("analyze", analyze_task)
    workflow.add_node("implement", implement_feature)
    workflow.add_node("test", run_tests)
    workflow.set_entry_point("analyze")
    workflow.add_edge("analyze", "implement")
    workflow.add_edge("implement", "test")
    workflow.add_edge("test", END)
    return workflow.compile()

feature_dev_graph = create_feature_dev_graph()
```

Switch graphs in Studio dropdown.

## Next Steps

### 1. Add State Annotations

Improve visualization by adding type hints:

```python
from typing import TypedDict, Annotated
from langgraph.graph import add_messages

class WorkflowState(TypedDict):
    """Workflow state with rich metadata."""
    messages: Annotated[list, add_messages]
    current_agent: str  # Shows in state inspector
    task_result: dict   # Expandable in UI
    approvals: list     # Shows approval history
```

### 2. Add Node Metadata

Help Studio display better labels:

```python
workflow.add_node(
    "supervisor",
    supervisor_node,
    metadata={
        "label": "Task Router",
        "description": "Routes tasks to appropriate agent",
        "color": "#ff69b4"
    }
)
```

### 3. Conditional Edge Labels

Show routing logic in graph:

```python
workflow.add_conditional_edges(
    "supervisor",
    route_to_agent,
    {
        "feature-dev": "feature_dev",
        "code-review": "code_review",
        "infrastructure": "infrastructure",
        "cicd": "cicd",
        "documentation": "documentation"
    },
    edge_labels={
        "feature-dev": "New Feature",
        "code-review": "Review Code",
        "infrastructure": "Deploy",
        "cicd": "Build Pipeline",
        "documentation": "Update Docs"
    }
)
```

### 4. Test HITL Workflow

Try the approval workflow:

1. Create thread with high-risk task
2. Workflow interrupts at `approval_gate`
3. In Studio, see "Interrupt" state
4. Manually approve via Linear or Studio UI
5. Resume workflow
6. See continuation

## Production Monitoring

### View Live Executions

Studio can connect to production LangGraph Cloud:

```bash
# Deploy orchestrator to LangGraph Cloud
langgraph deploy --config langgraph.json

# Access at cloud URL
https://your-org.langchain.app/orchestrator
```

### Alternative: LangSmith Traces

For production monitoring without Studio:

- https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/projects/p/f967bb5e-2e61-434f-8ee1-0df8c22bc046
- Shows same trace data
- No local setup required
- Already configured in production

## Comparison: Studio vs LangSmith

| Feature                   | LangGraph Studio             | LangSmith Traces       |
| ------------------------- | ---------------------------- | ---------------------- |
| **Graph Visualization**   | ✅ Interactive, editable     | ✅ Static, from traces |
| **Real-time Debugging**   | ✅ Breakpoints, step-through | ❌                     |
| **State Inspection**      | ✅ At each node              | ✅ Final state only    |
| **Local Development**     | ✅ Perfect for dev           | ❌ Cloud only          |
| **Production Monitoring** | ⚠️ Requires deployment       | ✅ Auto-enabled        |
| **Cost**                  | Free (local)                 | Free tier available    |

**Recommendation**: Use **both**:

- **Studio** for local development and debugging
- **LangSmith** for production monitoring and team visibility

## Support

- **LangGraph Studio Docs**: https://docs.langchain.com/langgraph-studio
- **LangSmith Dashboard**: https://smith.langchain.com
- **API Reference**: https://docs.langchain.com/langgraph

## Quick Reference

```powershell
# Start Studio
langgraph dev

# Start with custom port
langgraph dev --port 8123

# Verbose logging
langgraph dev --verbose

# Check version
langgraph --version

# Validate config
langgraph validate

# Deploy to cloud (optional)
langgraph deploy
```

Your setup is ready! Run `langgraph dev` to start visualizing your workflows.
