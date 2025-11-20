# MCP Gateway Implementation Gap

**Issue**: PR-118 - Implement MCP Tool Discovery Endpoints in Gateway  
**Status**: Todo  
**Priority**: High  
**Created**: November 20, 2025

## Problem

The MCP Bridge Client packages (`@appsmithery/mcp-bridge-client` NPM and `mcp-bridge-client` Python) were built and published to GitHub Packages, but they cannot function because the MCP Gateway at `http://45.55.173.72:8000` lacks the required endpoints.

**Current Gateway State** (shared/gateway/src/app.js):

- ✅ `/health` - Health check
- ✅ `/oauth/linear/install` - Linear OAuth flow
- ✅ `/oauth/linear/callback` - OAuth callback
- ✅ `/oauth/linear/status` - Token status
- ✅ `/api/linear-issues` - Fetch Linear issues
- ✅ `/api/linear-project/:projectId` - Fetch project roadmap

**Missing Endpoints** (Expected by MCP Bridge Clients):

- ❌ `GET /tools` - List all MCP tools (150+ tools from 18 servers)
- ❌ `GET /tools/progressive?task={description}` - Progressive tool loading
- ❌ `POST /tools/{toolName}` - Invoke MCP tool
- ❌ `GET /servers` - List available MCP servers
- ❌ `GET /servers/{serverName}/tools` - Get tools by server

## Impact

**Published Packages Cannot Function:**

```typescript
// This fails with 404 error
import { MCPBridgeClient } from "@appsmithery/mcp-bridge-client";
const client = new MCPBridgeClient({ gatewayUrl: "http://45.55.173.72:8000" });
const tools = await client.listTools(); // ❌ Cannot GET /tools
```

**Error:**

```
AxiosError: Request failed with status code 404
GET http://45.55.173.72:8000/tools → Cannot GET /tools
```

## Root Cause

The gateway was initially built for Linear OAuth integration only. The MCP tool discovery and invocation layer was never implemented, but the client packages assume it exists based on architecture documentation.

## Required Implementation

### 1. Add MCP Server Discovery

The gateway needs to:

1. Connect to MCP servers running in `shared/mcp/servers/`
2. Aggregate tool catalogs from all servers
3. Cache tool metadata (5-minute TTL)
4. Expose unified `/tools` endpoint

### 2. Add Tool Invocation

Route tool invocation requests to appropriate MCP servers:

```javascript
// POST /tools/memory/read
{
  "arguments": { "key": "user-prefs" }
}
```

### 3. Add Progressive Loading

Implement keyword-based filtering:

```javascript
// GET /tools/progressive?task=commit changes to git
// Returns only git-related tools (10-30 instead of 150+)
```

## Proposed Solution

### Option 1: Extend Current Gateway (Recommended)

Add MCP tool routes to `shared/gateway/src/routes.js`:

```javascript
// Add to routes.js
import { MCPServerManager } from "./services/mcpServerManager.js";

const mcpManager = new MCPServerManager();

router.get("/tools", async (req, res) => {
  try {
    const tools = await mcpManager.getAllTools();
    res.json({ tools });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

router.post("/tools/:toolName", async (req, res) => {
  try {
    const { toolName } = req.params;
    const result = await mcpManager.invokeTool(toolName, req.body.arguments);
    res.json({ success: true, result });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
});
```

Create `services/mcpServerManager.js`:

- Discover MCP servers from `shared/mcp/servers/`
- Establish stdio communication with each server
- Cache tool catalogs
- Route tool invocations

### Option 2: Separate MCP Gateway Service

Create dedicated `shared/services/mcp-gateway/` service:

- Runs on different port (8001?)
- Focused solely on MCP tool discovery/invocation
- Current gateway remains Linear-focused
- Update client default URL

### Option 3: Use Orchestrator as Gateway

Route clients directly to orchestrator at `:8001`:

- Orchestrator already has MCP client integration
- Can expose tool discovery endpoints
- Simpler architecture (one less service)
- **Recommended short-term solution**

## Immediate Workaround

Update MCP Bridge Client packages to use orchestrator as default gateway:

**NPM Package** (packages/mcp-bridge-client/src/client.ts):

```typescript
constructor(config: MCPBridgeClientConfig = {}) {
  this.config = {
    gatewayUrl: config.gatewayUrl || 'http://45.55.173.72:8001', // Use orchestrator
    // ...
  };
}
```

**Python Package** (packages/mcp-bridge-client-py/mcp_bridge_client/client.py):

```python
def __init__(
    self,
    gateway_url: str = "http://45.55.173.72:8001",  # Use orchestrator
    # ...
):
```

Then add tool discovery routes to orchestrator.

## Timeline

**Phase 1 (Immediate)**:

- Redirect clients to orchestrator (:8001)
- Add `/tools` endpoint to orchestrator
- Test with published packages
- Publish v0.1.1 with updated default URL

**Phase 2 (Next Sprint)**:

- Implement proper MCP Gateway service
- Full tool discovery and invocation
- Progressive loading support
- Migrate clients back to gateway (:8000)

## Related Issues

- **PR-114**: ✅ Build MCP Bridge Client Libraries (DONE - but non-functional)
- **PR-115**: ✅ Setup GitHub Package Distribution (DONE - packages published)
- **PR-116**: Integration Documentation (should document this gap)
- **PR-117**: Integration Testing (blocked until gateway implemented)
- **PR-118**: 🆕 Implement MCP Tool Discovery Endpoints (THIS ISSUE)

## Testing Checklist

Once implemented, verify:

- [ ] `GET /tools` returns 150+ tools from all MCP servers
- [ ] `GET /servers` lists 18+ MCP servers
- [ ] `POST /tools/memory/read` successfully invokes tool
- [ ] Progressive loading reduces tool count 80-90%
- [ ] NPM package works: `npm install @appsmithery/mcp-bridge-client`
- [ ] Python package works: `pip install mcp-bridge-client`
- [ ] All examples in package READMEs function correctly
- [ ] Gateway handles server failures gracefully
- [ ] Tool catalog caching works (5-minute TTL)

## Next Steps

1. **Decision**: Choose Option 1, 2, or 3 above
2. **Implement**: Add required endpoints
3. **Test**: Verify published packages work
4. **Update**: Publish v0.1.1 if needed
5. **Document**: Update PR-116 with actual implementation
6. **Close**: Mark PR-118 complete

---

**Note**: This is a critical gap that prevents the MCP Bridge integration from being functional despite packages being successfully built and published. The client libraries are production-ready but have no working gateway to connect to.
