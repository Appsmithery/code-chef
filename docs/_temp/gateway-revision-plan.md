# **Linear/MCP Gateway Refactor Plan** 🚪➡️🐍

Looking at the gateway implementation, I can see it's **primarily a Linear OAuth proxy** with minimal MCP functionality. Let me analyze if we need it:

### Current Gateway Reality

**What it ACTUALLY does:**

1. ✅ Linear OAuth flow (`/oauth/linear/*`)
2. ✅ Linear API proxying (`/api/linear-issues`, `/api/linear-project/:projectId`)
3. ✅ Health checks
4. ❌ **NO MCP tool routing implemented** (the `/tools/*` endpoints don't exist!)

**What agents are TRYING to use:**

1. `/tools/time/get_current_time` → **404 (not implemented)**
2. `/tools/memory/create_entities` → **404 (not implemented)**

### 💡 Key Insight: The Gateway is Unnecessary!

**Reasons:**

1. **No MCP Servers Running**: There's no evidence of actual MCP servers (memory, time, filesystem, etc.) running in the stack. The gateway would need to spawn and manage these processes.

2. **Linear Integration Can Move**: The Linear OAuth functionality can be:

   - Moved to a dedicated Python FastAPI service
   - OR integrated directly into agents that need Linear access
   - OR replaced with direct `@linear/sdk` usage in agents

3. **Python Has Better MCP Support**:

   - mcp Python package exists for MCP client/server
   - All agents are already Python/FastAPI
   - No need for Node.js ↔ Python bridge

4. **Current Implementation is Incomplete**: The gateway doesn't actually route to MCP servers - it would need significant work to become functional

---

## 🎯 Recommended Architecture: Remove Gateway

### New Architecture

```python
"""Direct Linear SDK integration (replaces gateway)."""
import os
from typing import Optional, List, Dict, Any
from linear_sdk import LinearClient  # Use Python Linear SDK

class LinearIntegration:
    """Direct Linear API access without gateway."""

    def __init__(self):
        self.api_key = os.getenv("LINEAR_API_KEY")
        self.client = LinearClient(api_key=self.api_key) if self.api_key else None

    def is_enabled(self) -> bool:
        return self.client is not None

    async def fetch_issues(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Fetch issues directly from Linear API."""
        if not self.client:
            return []

        issues = await self.client.issues(filter=filters or {}, first=50)
        return [
            {
                "id": issue.id,
                "title": issue.title,
                "state": issue.state.name if issue.state else None,
                "priority": issue.priority,
                "assignee": issue.assignee.name if issue.assignee else None,
                "url": issue.url,
            }
            for issue in issues.nodes
        ]

    async def fetch_project(self, project_id: str) -> Dict[str, Any]:
        """Fetch project roadmap directly."""
        if not self.client:
            return {}

        project = await self.client.project(project_id)
        issues = await project.issues()

        return {
            "project": {
                "id": project.id,
                "name": project.name,
                "state": project.state,
                "progress": project.progress,
            },
            "issues": [
                {
                    "id": issue.id,
                    "title": issue.title,
                    "state": issue.state.name if issue.state else None,
                    "priority": issue.priority,
                }
                for issue in issues.nodes
            ],
        }
```

### Updated mcp_client.py - Remove Gateway Dependency

```python
"""MCP client utilities - now with local time/memory fallbacks."""
from datetime import datetime
import uuid
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class MCPClient:
    """
    MCP client with local fallbacks.
    No longer depends on external gateway.
    """

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        # Remove gateway_url - no longer needed
        self._memory_store: Dict[str, Any] = {}  # Local in-memory store

    async def get_current_time(self) -> str:
        """Get current timestamp (local implementation)."""
        return datetime.utcnow().isoformat()

    async def log_event(
        self,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        entity_type: str = "agent_event",
    ) -> bool:
        """Log event to local memory store (replaces MCP memory server)."""
        metadata = dict(metadata or {})
        metadata.setdefault("agent", self.agent_name)
        metadata.setdefault("event_type", event_type)
        metadata.setdefault("timestamp", await self.get_current_time())

        entity_id = f"{self.agent_name}-{event_type}-{uuid.uuid4().hex[:8]}"

        # Store locally (can persist to PostgreSQL via state-persistence later)
        self._memory_store[entity_id] = {
            "id": entity_id,
            "type": entity_type,
            "metadata": metadata,
        }

        logger.info(f"[{self.agent_name}] Event logged: {event_type}")
        return True

    async def get_gateway_health(self) -> Dict[str, Any]:
        """Health check (local only - no gateway)."""
        return {
            "status": "local",
            "agent": self.agent_name,
            "timestamp": await self.get_current_time(),
        }
```

---

## 📊 Comparison: Current vs Proposed

| Aspect                 | Current (Node.js Gateway)           | Proposed (Python-Only)          |
| ---------------------- | ----------------------------------- | ------------------------------- |
| **Components**         | 9 services (includes gateway)       | 8 services (gateway removed)    |
| **Languages**          | Python + Node.js                    | Python only                     |
| **Complexity**         | HTTP bridge + stdio transport       | Direct imports                  |
| **Linear Integration** | OAuth via gateway                   | Direct SDK in agents            |
| **MCP Tools**          | Gateway routes (not implemented)    | Python MCP SDK                  |
| **Dependencies**       | `@linear/sdk`, Express, MCP servers | `linear-sdk` Python, mcp Python |
| **Latency**            | HTTP overhead                       | In-process calls                |
| **Maintenance**        | 2 language stacks                   | 1 language stack                |

---

## 🚀 Migration Plan

### Phase 1: Add Python Linear Client (Immediate)

```bash
# Add to all agent requirements.txt
echo "linear-sdk>=1.0.0" >> agents/orchestrator/requirements.txt
echo "linear-sdk>=1.0.0" >> agents/feature-dev/requirements.txt
# ... repeat for all agents
```

### Phase 2: Update docker-compose.yml

```yaml
# REMOVE gateway-mcp service entirely

orchestrator:
  environment:
    # Remove MCP_GATEWAY_URL
    - LINEAR_API_KEY=${LINEAR_API_KEY} # Add direct Linear access
    # ...existing vars...
  # Remove depends_on: gateway-mcp
```

### Phase 3: Update Agents

```python
from agents._shared.linear_client import LinearIntegration

linear_client = LinearIntegration()

@app.get("/linear/issues")
async def get_linear_issues():
    """Fetch Linear issues directly (no gateway)."""
    if not linear_client.is_enabled():
        return {"issues": [], "message": "Linear integration disabled"}

    issues = await linear_client.fetch_issues()
    return {"issues": issues, "count": len(issues)}
```

### Phase 4: Add Optional MCP Python SDK (Future)

If you need actual MCP tool servers later:

```bash
# Install MCP Python SDK
pip install mcp

# Create MCP server implementations in Python
# agents/_shared/mcp_servers/filesystem.py
# agents/_shared/mcp_servers/memory.py
```

---

## ✅ Recommendation: **Remove the Gateway**

### Rationale

1. **Gateway is Incomplete**: The `/tools/*` endpoints don't exist - it's just a Linear OAuth proxy
2. **Python Ecosystem**: All agents are Python - no need for Node.js bridge
3. **Simpler Stack**: One language, fewer dependencies, easier maintenance
4. **Direct Integration**: Python `linear-sdk` and mcp packages available
5. **Lower Latency**: No HTTP overhead for tool calls
6. **Better Observability**: All tracing in Python (Langfuse already integrated)

### Implementation Steps

1. ✅ **Immediate**: Add 501 stub to gateway (document unavailability)
2. 📝 **This Sprint**: Implement
