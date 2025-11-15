# Implementation Plan: MCP Toolkit Integration & Linear Access Strategy

## 🎯 Executive Summary

**Current State:**

- Node.js gateway exists but **only implements Linear OAuth** (no MCP tool routing)
- Python agents call `/tools/*` endpoints that **don't exist** (404 errors)
- Docker MCP Toolkit (`docker mcp gateway run`) is **not initialized**
- No actual MCP server enumeration happening

**Recommended Approach:**

1. ✅ **Keep Node.js gateway** for Linear OAuth only (specialized, working well)
2. ✅ **Remove MCP tool routing** from gateway (doesn't belong there)
3. ✅ **Add Python MCP SDK** to agents for direct MCP server access
4. ✅ **Repurpose MCPRegistry.js** as Python discovery tool for orchestrator

---

## 📋 Phase 1: Initialize Docker MCP Toolkit (Immediate)

### Step 1.1: Verify Docker MCP Toolkit Installation

```bash
# On production droplet
ssh root@45.55.173.72

# Verify Docker MCP Toolkit
docker mcp --version

# If not installed, install Docker Desktop or Docker MCP plugin
# https://github.com/docker/mcp-toolkit
```

### Step 1.2: Start MCP Gateway

```bash
# Start the Docker MCP gateway (stdio transport)
docker mcp gateway run

# This spawns MCP servers and makes them available via stdio protocol
# Output should show servers like:
# - memory (9 tools)
# - filesystem (24 tools)
# - gitmcp (5 tools)
# - etc.
```

### Step 1.3: Verify Server Discovery

```bash
# List available MCP servers
docker mcp server list

# List tools for a specific server
docker mcp server tools memory
```

**Expected Output:**

```json
{
  "servers": [
    { "name": "memory", "tools": 9, "status": "running" },
    { "name": "filesystem", "tools": 24, "status": "running" },
    { "name": "gitmcp", "tools": 5, "status": "running" }
  ]
}
```

---

## 📋 Phase 2: Python MCP Discovery Tool (Port MCPRegistry.js)

### Step 2.1: Create Python MCP Discovery Module

```python
"""
MCP Server Discovery via Docker MCP Toolkit
Ports functionality from MCPRegistry.js to Python for orchestrator usage
"""

import subprocess
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MCPToolkitDiscovery:
    """Discovers MCP servers and tools via Docker MCP Toolkit."""

    def __init__(self):
        self.servers: Dict[str, Any] = {}
        self.last_refresh: Optional[datetime] = None
        self._check_toolkit_available()

    def _check_toolkit_available(self) -> bool:
        """Check if Docker MCP Toolkit is installed."""
        try:
            result = subprocess.run(
                ["docker", "mcp", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                logger.info(f"[MCPDiscovery] Docker MCP Toolkit found: {result.stdout.strip()}")
                return True
            else:
                logger.warning("[MCPDiscovery] Docker MCP Toolkit not available")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"[MCPDiscovery] Failed to check Docker MCP Toolkit: {e}")
            return False

    def discover_servers(self) -> Dict[str, Any]:
        """
        Discover all MCP servers via Docker MCP Toolkit.

        Returns:
            {
                "servers": [
                    {
                        "name": "memory",
                        "tools": ["create_entities", "search_nodes", ...],
                        "tool_count": 9,
                        "status": "running"
                    },
                    ...
                ],
                "total_servers": 17,
                "total_tools": 150,
                "discovered_at": "2025-11-15T..."
            }
        """
        try:
            # Execute: docker mcp server list --json
            result = subprocess.run(
                ["docker", "mcp", "server", "list", "--json"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"[MCPDiscovery] Server list failed: {result.stderr}")
                return {"servers": [], "total_servers": 0, "total_tools": 0}

            servers_data = json.loads(result.stdout)

            # Enrich with tool details for each server
            enriched_servers = []
            total_tools = 0

            for server in servers_data.get("servers", []):
                server_name = server["name"]
                tools = self._get_server_tools(server_name)

                enriched_servers.append({
                    "name": server_name,
                    "tools": tools,
                    "tool_count": len(tools),
                    "status": server.get("status", "unknown"),
                    "type": "stdio"  # Docker MCP Toolkit uses stdio transport
                })

                total_tools += len(tools)

            self.servers = {
                "servers": enriched_servers,
                "total_servers": len(enriched_servers),
                "total_tools": total_tools,
                "discovered_at": datetime.utcnow().isoformat()
            }

            self.last_refresh = datetime.utcnow()
            logger.info(f"[MCPDiscovery] Discovered {len(enriched_servers)} servers with {total_tools} tools")

            return self.servers

        except Exception as e:
            logger.error(f"[MCPDiscovery] Discovery failed: {e}", exc_info=True)
            return {"servers": [], "total_servers": 0, "total_tools": 0}

    def _get_server_tools(self, server_name: str) -> List[str]:
        """Get list of tools for a specific server."""
        try:
            result = subprocess.run(
                ["docker", "mcp", "server", "tools", server_name, "--json"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                logger.warning(f"[MCPDiscovery] Failed to get tools for {server_name}")
                return []

            tools_data = json.loads(result.stdout)
            return [tool["name"] for tool in tools_data.get("tools", [])]

        except Exception as e:
            logger.error(f"[MCPDiscovery] Tool enumeration failed for {server_name}: {e}")
            return []

    def get_server(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific server."""
        if not self.servers:
            self.discover_servers()

        for server in self.servers.get("servers", []):
            if server["name"] == server_name:
                return server

        return None

    def get_servers_by_capability(self, capability: str) -> List[str]:
        """
        Get servers that have a specific capability/tool.

        Args:
            capability: Tool name (e.g., "create_entities", "read_file")

        Returns:
            List of server names that provide this tool
        """
        if not self.servers:
            self.discover_servers()

        matching_servers = []
        for server in self.servers.get("servers", []):
            if capability in server.get("tools", []):
                matching_servers.append(server["name"])

        return matching_servers

    def generate_agent_manifest(self) -> Dict[str, Any]:
        """
        Generate agent-to-tool mapping manifest based on discovered servers.

        Uses rules from config/mcp-agent-tool-mapping.yaml to assign tools to agents.
        """
        if not self.servers:
            self.discover_servers()

        # Load agent mapping rules
        import yaml
        from pathlib import Path

        mapping_path = Path(__file__).parent.parent.parent / "config" / "mcp-agent-tool-mapping.yaml"

        try:
            with open(mapping_path, "r") as f:
                mapping_config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"[MCPDiscovery] Failed to load agent mapping config: {e}")
            return {}

        # Map agents to discovered servers
        agent_profiles = []

        for agent_name, agent_config in mapping_config.get("agent_tool_mappings", {}).items():
            recommended_tools = []

            for tool_entry in agent_config.get("recommended_tools", []):
                server_name = tool_entry["server"]
                server_info = self.get_server(server_name)

                if server_info:
                    recommended_tools.append({
                        "server": server_name,
                        "tools": tool_entry["tools"],
                        "available": True,
                        "tool_count": len(tool_entry["tools"])
                    })
                else:
                    logger.warning(f"[MCPDiscovery] Server {server_name} not found for agent {agent_name}")
                    recommended_tools.append({
                        "server": server_name,
                        "tools": tool_entry["tools"],
                        "available": False,
                        "tool_count": 0
                    })

            agent_profiles.append({
                "name": agent_name,
                "mission": agent_config.get("mission"),
                "mcp_tools": {
                    "recommended": recommended_tools,
                    "shared": agent_config.get("shared_tools", [])
                },
                "capabilities": self._derive_capabilities(recommended_tools)
            })

        return {
            "version": "1.0.0",
            "generated_at": datetime.utcnow().isoformat(),
            "discovery_summary": self.servers,
            "profiles": agent_profiles
        }

    def _derive_capabilities(self, recommended_tools: List[Dict]) -> List[str]:
        """Derive agent capabilities from assigned tools."""
        capabilities = set()

        capability_map = {
            "memory": ["knowledge_graph", "state_management"],
            "filesystem": ["file_operations", "code_reading"],
            "gitmcp": ["version_control", "code_collaboration"],
            "dockerhub": ["container_management"],
            "playwright": ["browser_automation", "e2e_testing"],
            "notion": ["documentation", "project_management"]
        }

        for tool_entry in recommended_tools:
            server_name = tool_entry["server"]
            if server_name in capability_map:
                capabilities.update(capability_map[server_name])

        return sorted(list(capabilities))


# Singleton instance
_discovery_instance: Optional[MCPToolkitDiscovery] = None


def get_mcp_discovery() -> MCPToolkitDiscovery:
    """Get or create MCP discovery singleton."""
    global _discovery_instance
    if _discovery_instance is None:
        _discovery_instance = MCPToolkitDiscovery()
    return _discovery_instance
```

### Step 2.2: Add Discovery Endpoint to Orchestrator

```python
# Add this after existing imports

from agents._shared.mcp_discovery import get_mcp_discovery

# Add new endpoints

@app.get("/mcp/discover")
async def discover_mcp_servers():
    """
    Discover all MCP servers via Docker MCP Toolkit.

    Returns real-time server and tool inventory.
    """
    discovery = get_mcp_discovery()

    try:
        servers = discovery.discover_servers()
        return {
            "success": True,
            "discovery": servers,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"[Orchestrator] MCP discovery failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"MCP discovery failed: {str(e)}"
        )


@app.get("/mcp/manifest")
async def get_agent_manifest():
    """
    Generate agent-to-tool mapping manifest based on discovered MCP servers.

    This replaces the static agents/agents-manifest.json with dynamic discovery.
    """
    discovery = get_mcp_discovery()

    try:
        manifest = discovery.generate_agent_manifest()
        return {
            "success": True,
            "manifest": manifest
        }
    except Exception as e:
        logger.error(f"[Orchestrator] Manifest generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Manifest generation failed: {str(e)}"
        )


@app.get("/mcp/server/{server_name}")
async def get_server_details(server_name: str):
    """Get details for a specific MCP server."""
    discovery = get_mcp_discovery()

    server = discovery.get_server(server_name)
    if not server:
        raise HTTPException(
            status_code=404,
            detail=f"MCP server '{server_name}' not found"
        )

    return {
        "success": True,
        "server": server
    }
```

### Step 2.3: Update Requirements

```txt
# ...existing requirements...
pyyaml>=6.0  # For reading mcp-agent-tool-mapping.yaml
```

---

## 📋 Phase 3: Linear Access Strategy

### Recommendation: **Hybrid Approach**

**Keep Node.js Gateway for Linear OAuth (Current Implementation):**

- ✅ OAuth flow working well
- ✅ Token persistence implemented
- ✅ Specialized, focused service
- ✅ Easy to secure with secrets

**Add Python Linear SDK to Specific Agents That Need It:**

#### Option A: Direct Linear SDK Integration (Recommended)

```python
"""
Direct Linear API access using Python SDK.
Only import this in agents that need Linear integration (orchestrator, documentation).
"""

import os
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class LinearIntegration:
    """
    Direct Linear API access without gateway.

    Requires LINEAR_API_KEY environment variable (Personal API token).
    """

    def __init__(self):
        self.api_key = os.getenv("LINEAR_API_KEY")
        self.enabled = bool(self.api_key)

        if self.enabled:
            # Use linear-sdk Python package (install via pip)
            try:
                from linear_sdk import LinearClient
                self.client = LinearClient(api_key=self.api_key)
                logger.info("[Linear] Client initialized with API key")
            except ImportError:
                logger.error("[Linear] linear-sdk package not installed")
                self.enabled = False
                self.client = None
        else:
            logger.warning("[Linear] No LINEAR_API_KEY found - Linear integration disabled")
            self.client = None

    def is_enabled(self) -> bool:
        """Check if Linear integration is available."""
        return self.enabled and self.client is not None

    async def fetch_issues(self, filters: Optional[Dict] = None) -> List[Dict]:
        """
        Fetch issues from Linear workspace.

        Args:
            filters: Optional filters (e.g., {"state": "in_progress"})

        Returns:
            List of issue dictionaries
        """
        if not self.is_enabled():
            logger.warning("[Linear] Cannot fetch issues - integration disabled")
            return []

        try:
            issues = await self.client.issues(filter=filters or {}, first=50)

            return [
                {
                    "id": issue.id,
                    "title": issue.title,
                    "state": issue.state.name if issue.state else None,
                    "priority": issue.priority,
                    "assignee": issue.assignee.name if issue.assignee else None,
                    "url": issue.url,
                    "description": issue.description,
                    "created_at": issue.created_at.isoformat() if issue.created_at else None
                }
                for issue in issues.nodes
            ]

        except Exception as e:
            logger.error(f"[Linear] Failed to fetch issues: {e}", exc_info=True)
            return []

    async def create_issue(
        self,
        title: str,
        description: str,
        team_id: Optional[str] = None,
        priority: int = 0
    ) -> Optional[Dict]:
        """
        Create a new Linear issue.

        Args:
            title: Issue title
            description: Issue description
            team_id: Optional team ID (defaults to personal workspace)
            priority: Priority (0=None, 1=Urgent, 2=High, 3=Normal, 4=Low)

        Returns:
            Created issue data or None if failed
        """
        if not self.is_enabled():
            logger.warning("[Linear] Cannot create issue - integration disabled")
            return None

        try:
            issue = await self.client.create_issue(
                title=title,
                description=description,
                team_id=team_id,
                priority=priority
            )

            logger.info(f"[Linear] Created issue: {issue.id} - {title}")

            return {
                "id": issue.id,
                "title": issue.title,
                "url": issue.url,
                "identifier": issue.identifier
            }

        except Exception as e:
            logger.error(f"[Linear] Failed to create issue: {e}", exc_info=True)
            return None

    async def update_issue(
        self,
        issue_id: str,
        **updates
    ) -> bool:
        """
        Update an existing Linear issue.

        Args:
            issue_id: Linear issue ID
            **updates: Fields to update (title, description, state_id, priority, etc.)

        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            logger.warning("[Linear] Cannot update issue - integration disabled")
            return False

        try:
            await self.client.update_issue(issue_id, **updates)
            logger.info(f"[Linear] Updated issue: {issue_id}")
            return True

        except Exception as e:
            logger.error(f"[Linear] Failed to update issue {issue_id}: {e}", exc_info=True)
            return False

    async def fetch_project_roadmap(self, project_id: str) -> Dict[str, Any]:
        """
        Fetch project roadmap with associated issues.

        Args:
            project_id: Linear project ID

        Returns:
            Project data with issues
        """
        if not self.is_enabled():
            logger.warning("[Linear] Cannot fetch project - integration disabled")
            return {}

        try:
            project = await self.client.project(project_id)
            issues = await project.issues()

            return {
                "project": {
                    "id": project.id,
                    "name": project.name,
                    "state": project.state,
                    "progress": project.progress,
                    "description": project.description
                },
                "issues": [
                    {
                        "id": issue.id,
                        "title": issue.title,
                        "state": issue.state.name if issue.state else None,
                        "priority": issue.priority,
                        "url": issue.url
                    }
                    for issue in issues.nodes
                ]
            }

        except Exception as e:
            logger.error(f"[Linear] Failed to fetch project {project_id}: {e}", exc_info=True)
            return {}


# Singleton instance
_linear_instance: Optional[LinearIntegration] = None


def get_linear_client() -> LinearIntegration:
    """Get or create Linear client singleton."""
    global _linear_instance
    if _linear_instance is None:
        _linear_instance = LinearIntegration()
    return _linear_instance
```

#### Add Linear Endpoints to Orchestrator

```python
from agents._shared.linear_client import get_linear_client

linear_client = get_linear_client()

@app.get("/linear/issues")
async def get_linear_issues():
    """Fetch issues from Linear roadmap."""
    if not linear_client.is_enabled():
        return {
            "success": False,
            "message": "Linear integration not configured"
        }

    issues = await linear_client.fetch_issues()
    return {
        "success": True,
        "count": len(issues),
        "issues": issues
    }


@app.post("/linear/issues")
async def create_linear_issue(request: Dict[str, Any]):
    """Create a new Linear issue."""
    if not linear_client.is_enabled():
        raise HTTPException(
            status_code=503,
            detail="Linear integration not configured"
        )

    issue = await linear_client.create_issue(
        title=request["title"],
        description=request.get("description", ""),
        priority=request.get("priority", 0)
    )

    if issue:
        return {
            "success": True,
            "issue": issue
        }
    else:
        raise HTTPException(
            status_code=500,
            detail="Failed to create Linear issue"
        )


@app.get("/linear/project/{project_id}")
async def get_linear_project(project_id: str):
    """Fetch Linear project roadmap."""
    if not linear_client.is_enabled():
        raise HTTPException(
            status_code=503,
            detail="Linear integration not configured"
        )

    roadmap = await linear_client.fetch_project_roadmap(project_id)
    return {
        "success": True,
        "roadmap": roadmap
    }
```

### Update Requirements

```txt
# ...existing requirements...
linear-sdk>=1.0.0  # Python Linear API client
```

### Update Environment Variables

```yaml
services:
  orchestrator:
    environment:
      # ...existing vars...
      - LINEAR_API_KEY=${LINEAR_API_KEY} # Personal API token from Linear settings
```

```dotenv
# Linear Integration
LINEAR_API_KEY=lin_api_yourpersonalapikey  # From https://linear.app/settings/api
```

---

## 📋 Phase 4: Remove Gateway MCP Tool Routing (Cleanup)

### Step 4.1: Update Gateway to Linear-Only

```javascript
// Remove or comment out the /tools/* stub endpoint

// REMOVED: MCP tool routing is handled by Python agents directly via Docker MCP Toolkit
// router.post("/tools/:server/:tool", async (req, res) => {
//   res.status(501).json({
//     success: false,
//     error: "MCP tool routing moved to Python agents"
//   });
// });

// Keep only Linear routes:
// - /oauth/linear/install
// - /oauth/linear/callback
// - /oauth/linear/status
// - /api/linear-issues
// - /api/linear-project/:projectId
```

### Step 4.2: Update Gateway README

```markdown
# MCP Gateway

**Purpose:** Linear OAuth integration for Dev-Tools agents

This service provides:

- OAuth 2.0 authorization flow for Linear
- Token persistence with automatic refresh
- Linear API endpoints (issues, projects)

**Note:** MCP tool routing is **not** handled by this gateway.
Agents access MCP servers directly via Docker MCP Toolkit and Python MCP SDK.
```

### Step 4.3: Update Python MCP Client

```python
# Remove invoke_tool method (agents will use MCP SDK directly)
# Remove get_gateway_health (no longer checking gateway for MCP tools)

# Keep only:
# - Agent manifest loading
# - Agent profile retrieval
# - Capability queries
```

---

## 📋 Phase 5: Python MCP SDK Integration (Agents Direct Access)

### Step 5.1: Add Python MCP SDK to Agents

```txt
# ...existing requirements...
mcp>=1.0.0  # Python MCP SDK for direct server access
```

### Step 5.2: Create MCP Tool Invocation Helper

```python
"""
Direct MCP tool invocation using Python MCP SDK.
Replaces HTTP gateway calls with stdio transport to Docker MCP servers.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from mcp import StdioServerParameters, stdio_client
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)


class MCPToolClient:
    """
    Direct MCP tool invocation client.

    Uses Python MCP SDK to communicate with servers via stdio transport.
    """

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.server_connections: Dict[str, Any] = {}

    async def invoke_tool(
        self,
        server: str,
        tool: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Invoke an MCP tool on a server.

        Args:
            server: Server name (e.g., "memory", "filesystem")
            tool: Tool name (e.g., "create_entities", "read_file")
            params: Tool parameters

        Returns:
            Tool execution result
        """
        try:
            # Get or create server connection
            if server not in self.server_connections:
                await self._connect_server(server)

            client = self.server_connections[server]

            # List available tools
            tools_response = await client.list_tools()
            tool_definitions = tools_response.tools

            # Find the requested tool
            tool_def = next((t for t in tool_definitions if t.name == tool), None)
            if not tool_def:
                return {
                    "success": False,
                    "error": f"Tool '{tool}' not found on server '{server}'"
                }

            # Invoke the tool
            result = await client.call_tool(tool, params or {})

            # Parse result
            if result.content:
                content = result.content[0]
                if isinstance(content, TextContent):
                    import json
                    try:
                        parsed = json.loads(content.text)
                        return {
                            "success": True,
                            "result": parsed
                        }
                    except json.JSONDecodeError:
                        return {
                            "success": True,
                            "result": content.text
                        }

            return {
                "success": True,
                "result": result.content
            }

        except Exception as e:
            logger.error(f"[{self.agent_name}] Tool invocation failed: {server}/{tool}: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def _connect_server(self, server_name: str):
        """Establish connection to an MCP server via Docker MCP Toolkit."""
        try:
            # Use Docker MCP Toolkit to spawn server
            server_params = StdioServerParameters(
                command="docker",
                args=["mcp", "server", "run", server_name],
                env=os.environ.copy()
            )

            logger.info(f"[{self.agent_name}] Connecting to MCP server: {server_name}")

            # Create stdio client
            stdio_transport = await stdio_client(server_params)
            read, write = stdio_transport

            # Initialize client session
            async with read:
                async with write:
                    from mcp import ClientSession

                    session = ClientSession(read, write)
                    await session.initialize()

                    self.server_connections[server_name] = session
                    logger.info(f"[{self.agent_name}] Connected to MCP server: {server_name}")

        except Exception as e:
            logger.error(f"[{self.agent_name}] Failed to connect to server {server_name}: {e}", exc_info=True)
            raise

    async def list_servers(self) -> List[str]:
        """List available MCP servers."""
        from agents._shared.mcp_discovery import get_mcp_discovery

        discovery = get_mcp_discovery()
        servers = discovery.discover_servers()

        return [s["name"] for s in servers.get("servers", [])]

    async def list_tools(self, server: str) -> List[str]:
        """List tools available on a server."""
        if server not in self.server_connections:
            await self._connect_server(server)

        client = self.server_connections[server]
        tools_response = await client.list_tools()

        return [tool.name for tool in tools_response.tools]
```

### Step 5.3: Update Orchestrator to Use Direct MCP Access

```python
# Replace old mcp_client with new tool client
from agents._shared.mcp_tool_client import MCPToolClient

mcp_tool_client = MCPToolClient(agent_name="orchestrator")

# Update existing MCP tool calls to use new client
# Example: Memory operations
async def log_orchestration_event(task_id: str, event_type: str, metadata: Dict):
    """Log event to shared memory server via direct MCP SDK access."""
    entity = {
        "name": f"orchestrator-{event_type}-{task_id}",
        "type": "orchestration_event",
        "metadata": {
            "agent": "orchestrator",
            "task_id": task_id,
            "event_type": event_type,
            **metadata
        }
    }

    result = await mcp_tool_client.invoke_tool(
        server="memory",
        tool="create_entities",
        params={"entities": [entity]}
    )

    if result.get("success"):
        logger.info(f"[Orchestrator] Logged event: {event_type} for task {task_id}")
    else:
        logger.warning(f"[Orchestrator] Failed to log event: {result.get('error')}")
```

---

## 📋 Phase 6: Update Documentation

### Step 6.1: Update Troubleshooting Guide

````markdown
## Known Issues

### ✅ RESOLVED: MCP Gateway Tool Routing

**Previous Issue:** Python agents were calling `/tools/*` endpoints on Node.js gateway that didn't exist (404 errors).

**Resolution:**

- Node.js gateway **repurposed as Linear OAuth-only service**
- Agents now access MCP servers **directly via Python MCP SDK**
- Docker MCP Toolkit provides stdio transport to MCP servers
- No more HTTP overhead or 404 errors

**Current Architecture:**

```
Agents (Python) → MCP SDK → Docker MCP Toolkit → MCP Servers (stdio)
                                                   ↓
                                              memory, filesystem, gitmcp, etc.
```

**Linear Integration:**

```
Agents (Python) → linear-sdk (direct) → Linear API
                                        ↓
                                   Issues, Projects, Roadmap
```
````

### Step 6.2: Update Architecture Docs

```markdown
## Component Breakdown

### MCP Integration (Revised)

**Python MCP SDK (New):**

- Direct stdio transport to MCP servers
- No HTTP overhead
- Type-safe tool invocation
- Automatic server lifecycle management

**Docker MCP Toolkit:**

- Spawns and manages MCP servers
- Provides stdio interface
- Handles server discovery

**Linear OAuth Gateway (Existing):**

- Node.js service on port 8000
- **Linear OAuth flow only** (not MCP routing)
- Token persistence
- Endpoints: `/oauth/linear/*`, `/api/linear-*`

**Removed:**

- ❌ HTTP-based MCP gateway routing
- ❌ `/tools/*` endpoints (never implemented properly)
```

---

## 🎯 Summary & Next Steps

### ✅ Recommended Implementation Order

1. **Immediate (30 min):**

   - Initialize Docker MCP Toolkit: `docker mcp gateway run`
   - Verify server discovery: `docker mcp server list`

2. **Phase 1 (2 hours):**

   - Create `mcp_discovery.py` (Python port of MCPRegistry.js)
   - Add `/mcp/discover` and `/mcp/manifest` endpoints to orchestrator
   - Test discovery: `GET http://localhost:8001/mcp/discover`

3. **Phase 2 (1 hour):**

   - Create `linear_client.py` (direct Linear SDK integration)
   - Add Linear endpoints to orchestrator
   - Update .env with `LINEAR_API_KEY`

4. **Phase 3 (3 hours):**

   - Create `mcp_tool_client.py` (Python MCP SDK integration)
   - Update orchestrator to use direct MCP access
   - Test tool invocation: memory, filesystem operations

5. **Phase 4 (1 hour):**

   - Update gateway to Linear-only (remove MCP routing stubs)
   - Update documentation
   - Clean up old mcp_client.py HTTP calls

6. **Phase 5 (Deploy):**
   - Commit and push changes
   - Deploy to production
   - Verify MCP tool access and Linear integration

---

### 🎉 Expected Outcome

**Before:**

```
Agent → HTTP → Node.js Gateway (404) → ❌ No MCP servers
Agent → HTTP → Node.js Gateway → Linear OAuth ✅
```

**After:**

```
Agent → Python MCP SDK → Docker MCP Toolkit → MCP Servers ✅
Agent → Python linear-sdk → Linear API ✅
Node.js Gateway → Linear OAuth (unchanged) ✅
```

**Benefits:**

- ✅ No more 404 errors on `/tools/*`
- ✅ Direct, type-safe MCP tool access
- ✅ Faster (no HTTP overhead for MCP)
- ✅ Simpler architecture (one language for agents)
- ✅ Keep working Linear OAuth flow
- ✅ Real-time MCP server discovery
