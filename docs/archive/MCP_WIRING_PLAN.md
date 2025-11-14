# Dev-Tools MCP Integration Action Plan

**Version:** 1.0.0
**Date:** 2025-11-13
**Purpose:** Stepwise, automated plan to wire MCP tool mappings into agent infrastructure

---

## 🎯 Executive Summary

This document outlines the complete automation plan to integrate 150 MCP tools across 17 servers into the Dev-Tools agent ecosystem. The plan ensures agents are pre-configured with appropriate tool access, shared context infrastructure (memory/time servers) is integrated into RAG and state layers, and comprehensive validation ensures correct wiring.

**Estimated Duration:** 2-3 hours
**Automation Level:** 90% automated via scripts
**Risk Level:** Low (non-destructive, incremental deployment)

---

## 📋 Prerequisites Validation

### ✅ Completed

- [x] MCP Gateway discovery (150 tools across 17 servers)
- [x] Tool-to-agent mapping document (`config/mcp-agent-tool-mapping.yaml`)
- [x] Updated architecture documentation (`docs/ARCHITECTURE.md` v2.0)
- [x] MCP integration guide (`docs/MCP_INTEGRATION.md`)
- [x] Obsolete documentation archived

### 🔄 Required Before Proceeding

- [ ] MCP Gateway accessible at `http://gateway-mcp:8000` (Docker network)
- [ ] All agent containers built and health checks passing
- [ ] PostgreSQL and Qdrant services running
- [ ] Backup of current volumes completed

**Validation Command:**

```powershell
# scripts/validate-prerequisites.ps1
Write-Host "Checking prerequisites..."

# 1. Gateway health
try {
    $gateway = Invoke-RestMethod "http://localhost:8000/health"
    Write-Host "✓ MCP Gateway: $($gateway.status)"
} catch {
    Write-Error "✗ MCP Gateway not accessible"
    exit 1
}

# 2. Agent health
8001..8006 | ForEach-Object {
    try {
        $agent = Invoke-RestMethod "http://localhost:$_/health"
        Write-Host "✓ Agent port $_: $($agent.service)"
    } catch {
        Write-Warning "⚠ Agent port $_ not responding"
    }
}

# 3. Database services
try {
    $rag = Invoke-RestMethod "http://localhost:8007/health"
    Write-Host "✓ RAG Context: $($rag.status)"
} catch {
    Write-Error "✗ RAG Context not accessible"
}

try {
    $state = Invoke-RestMethod "http://localhost:8008/health"
    Write-Host "✓ State Persistence: $($state.status)"
} catch {
    Write-Error "✗ State Persistence not accessible"
}

Write-Host "`n✅ All prerequisites validated"
```

---

## 📝 Phase 1: Generate Agent Manifest

**Objective:** Create `agents/agents-manifest.json` with complete agent profiles and MCP tool allocations.

### Step 1.1: Generate Manifest from Mapping

**Script:** `scripts/generate-agent-manifest.ps1`

```powershell
# scripts/generate-agent-manifest.ps1
# Reads config/mcp-agent-tool-mapping.yaml and generates agents/agents-manifest.json

$mappingFile = "config/mcp-agent-tool-mapping.yaml"
$outputFile = "agents/agents-manifest.json"

Write-Host "Generating agent manifest from MCP tool mapping..."

# Load YAML (requires powershell-yaml module or manual parsing)
$mapping = Get-Content $mappingFile | ConvertFrom-Yaml

$manifest = @{
    version = "2.0.0"
    generatedAt = (Get-Date -Format "o")
    profiles = @()
}

foreach ($agentName in $mapping.agent_tool_mappings.Keys) {
    $agentConfig = $mapping.agent_tool_mappings[$agentName]

    $profile = @{
        name = $agentName
        mission = $agentConfig.mission
        endpoint = "http://$agentName:800$($agentIndex)"
        mcp_tools = @{
            recommended = @()
            shared = @()
        }
        capabilities = @()
    }

    # Add recommended tools
    foreach ($tool in $agentConfig.recommended_tools) {
        $profile.mcp_tools.recommended += @{
            server = $tool.server
            tools = $tool.tools
            priority = $tool.priority
            rationale = $tool.rationale
        }
    }

    # Add shared tools reference
    $profile.mcp_tools.shared = @("memory", "time", "rust-mcp-filesystem", "context7", "notion")

    $manifest.profiles += $profile
}

# Write manifest
$manifest | ConvertTo-Json -Depth 10 | Set-Content $outputFile
Write-Host "✅ Manifest generated: $outputFile"
```

**Expected Output:** `agents/agents-manifest.json`

```json
{
  "version": "2.0.0",
  "generatedAt": "2025-11-13T22:40:00Z",
  "profiles": [
    {
      "name": "orchestrator",
      "mission": "Coordinates task routing, agent hand-offs, workflow state",
      "endpoint": "http://orchestrator:8001",
      "mcp_tools": {
        "recommended": [
          {
            "server": "memory",
            "tools": [
              "create_entities",
              "create_relations",
              "read_graph",
              "search_nodes"
            ],
            "priority": "critical",
            "rationale": "Maintain task graph, agent relationships, workflow state"
          }
        ],
        "shared": [
          "memory",
          "time",
          "rust-mcp-filesystem",
          "context7",
          "notion"
        ]
      }
    }
  ]
}
```

### Step 1.2: Validate Manifest

```powershell
# Validate JSON structure
$manifest = Get-Content "agents/agents-manifest.json" | ConvertFrom-Json

Write-Host "Validating manifest..."
Write-Host "  Agents: $($manifest.profiles.Count)"
Write-Host "  Version: $($manifest.version)"

foreach ($profile in $manifest.profiles) {
    Write-Host "  - $($profile.name): $($profile.mcp_tools.recommended.Count) recommended tools"
}
```

---

## 🔌 Phase 2: Update Docker Compose with MCP Integration

**Objective:** Add MCP Gateway environment variables to all agent services.

### Step 2.1: Update docker-compose.yml

**Script:** `scripts/update-docker-compose-mcp.ps1`

```powershell
# scripts/update-docker-compose-mcp.ps1
$composeFile = "compose/docker-compose.yml"
$backupFile = "compose/docker-compose.yml.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"

Write-Host "Backing up docker-compose.yml..."
Copy-Item $composeFile $backupFile

Write-Host "Updating docker-compose.yml with MCP integration..."

# Read compose file
$compose = Get-Content $composeFile -Raw

# Define MCP environment variables to add
$mcpEnvVars = @"
      - MCP_GATEWAY_URL=http://gateway-mcp:8000
      - MCP_TIMEOUT=30
"@

# Update each agent service
$agentServices = @("orchestrator", "feature-dev", "code-review", "infrastructure", "cicd", "documentation")

foreach ($service in $agentServices) {
    # Find service definition and add MCP env vars after existing environment section
    $pattern = "($service:.*?environment:.*?)(- SERVICE_NAME=$service)"
    $replacement = "`$1`$2`n$mcpEnvVars"
    $compose = $compose -replace $pattern, $replacement
}

# Write updated compose file
$compose | Set-Content $composeFile

Write-Host "✅ docker-compose.yml updated with MCP integration"
Write-Host "Backup saved: $backupFile"
```

### Step 2.2: Add Gateway Dependency

Ensure all agents depend on `gateway-mcp`:

```yaml
services:
  orchestrator:
    depends_on:
      - state-persistence
      - gateway-mcp # ADD THIS

  feature-dev:
    depends_on:
      - rag-context
      - gateway-mcp # ADD THIS


  # ... repeat for all agents
```

### Step 2.3: Validate Compose File

```powershell
# Validate YAML syntax
docker-compose -f compose/docker-compose.yml config

# Check for MCP_GATEWAY_URL in all agents
Select-String -Path "compose/docker-compose.yml" -Pattern "MCP_GATEWAY_URL"
```

---

## 🧠 Phase 3: Integrate Shared Tools into RAG Service

**Objective:** Enhance RAG service to leverage memory and time servers for universal context.

### Step 3.1: Update RAG Service with MCP Client

**File:** `services/rag/main.py`

```python
# Add MCP tool invocation helper
import httpx

MCP_GATEWAY_URL = os.getenv("MCP_GATEWAY_URL", "http://gateway-mcp:8000")

async def invoke_mcp_tool(server: str, tool: str, params: dict):
    """Invoke MCP tool via gateway"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MCP_GATEWAY_URL}/tools/{server}/{tool}",
            json={"params": params},
            timeout=30.0
        )
        return response.json()

# Add timestamp to all queries
@app.post("/query", response_model=QueryResponse)
async def query_context(request: QueryRequest):
    start_time = datetime.utcnow()

    # Get timestamp from MCP time server
    timestamp_result = await invoke_mcp_tool("time", "get_current_time", {})
    timestamp = timestamp_result.get("result", start_time.isoformat())

    # Perform vector search
    context_items = []  # ... existing Qdrant logic

    # Store query in memory server for analytics
    await invoke_mcp_tool(
        server="memory",
        tool="create_entities",
        params={
            "entities": [{
                "name": f"query-{uuid.uuid4()}",
                "type": "rag_query",
                "metadata": {
                    "query_text": request.query,
                    "collection": request.collection,
                    "timestamp": timestamp,
                    "results_count": len(context_items)
                }
            }]
        }
    )

    end_time = datetime.utcnow()
    retrieval_time = (end_time - start_time).total_seconds() * 1000

    return QueryResponse(
        query=request.query,
        results=context_items,
        collection=request.collection,
        total_found=len(context_items),
        retrieval_time_ms=round(retrieval_time, 2)
    )
```

### Step 3.2: Update RAG Dockerfile

```dockerfile
# containers/rag/Dockerfile
# Add httpx dependency for MCP calls
RUN pip install httpx
```

### Step 3.3: Add MCP_GATEWAY_URL to RAG Service

```yaml
# compose/docker-compose.yml
services:
  rag-context:
    environment:
      - MCP_GATEWAY_URL=http://gateway-mcp:8000
    depends_on:
      - gateway-mcp
```

---

## 🤖 Phase 4: Pre-load MCP Clients in Agents

**Objective:** Add MCP tool invocation helpers to each agent's `main.py`.

### Step 4.1: Create Shared MCP Client Module

**File:** `agents/_shared/mcp_client.py` (NEW)

```python
"""
Shared MCP Client Module

Provides standardized MCP tool invocation for all agents.
"""

import httpx
import os
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

MCP_GATEWAY_URL = os.getenv("MCP_GATEWAY_URL", "http://gateway-mcp:8000")
MCP_TIMEOUT = int(os.getenv("MCP_TIMEOUT", "30"))

class MCPClient:
    """MCP Gateway client for agents"""

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.gateway_url = MCP_GATEWAY_URL
        self.timeout = MCP_TIMEOUT

    async def invoke_tool(
        self,
        server: str,
        tool: str,
        params: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Invoke MCP tool via gateway

        Args:
            server: MCP server name (e.g., "memory", "gitmcp")
            tool: Tool name (e.g., "create_entities", "get_diff")
            params: Tool parameters
            timeout: Override default timeout (seconds)

        Returns:
            Tool execution result

        Raises:
            httpx.HTTPError: If tool invocation fails
        """
        timeout_val = timeout or self.timeout

        logger.info(f"[{self.agent_name}] Invoking {server}/{tool}")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.gateway_url}/tools/{server}/{tool}",
                    json={"params": params},
                    timeout=timeout_val
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(f"[{self.agent_name}] MCP tool invocation failed: {e}")
            raise

    async def get_timestamp(self) -> str:
        """Get current timestamp from MCP time server"""
        result = await self.invoke_tool("time", "get_current_time", {})
        return result.get("result", datetime.utcnow().isoformat())

    async def log_to_memory(self, entity_name: str, entity_type: str, metadata: Dict[str, Any]):
        """Log entity to shared memory server"""
        await self.invoke_tool(
            server="memory",
            tool="create_entities",
            params={
                "entities": [{
                    "name": entity_name,
                    "type": entity_type,
                    "metadata": {
                        **metadata,
                        "agent": self.agent_name,
                        "timestamp": await self.get_timestamp()
                    }
                }]
            }
        )
```

### Step 4.2: Update Each Agent with MCP Client

**Example:** `agents/feature-dev/main.py`

```python
# Add import
from ..._shared.mcp_client import MCPClient

# Initialize in app startup
mcp_client = MCPClient(agent_name="feature-dev")

@app.post("/implement", response_model=ImplementationResponse)
async def implement_feature(request: FeatureRequest):
    """
    Implement feature using MCP tools
    """
    # Log task start to memory
    await mcp_client.log_to_memory(
        entity_name=f"feature-{request.task_id}",
        entity_type="implementation",
        metadata={"description": request.description, "status": "started"}
    )

    # Read codebase with rust-mcp-filesystem
    files = await mcp_client.invoke_tool(
        server="rust-mcp-filesystem",
        tool="list_directory",
        params={"path": "/workspace/src"}
    )

    # Generate code with hugging-face
    generated_code = await mcp_client.invoke_tool(
        server="hugging-face",
        tool="generate_code",
        params={"prompt": f"Implement {request.description}", "context": files}
    )

    # Write code
    await mcp_client.invoke_tool(
        server="rust-mcp-filesystem",
        tool="write_file",
        params={"path": f"/workspace/src/{request.filename}", "content": generated_code["result"]}
    )

    # Create git branch
    await mcp_client.invoke_tool(
        server="gitmcp",
        tool="create_branch",
        params={"branch_name": f"feature/{request.task_id}"}
    )

    # Log completion
    await mcp_client.log_to_memory(
        entity_name=f"feature-{request.task_id}",
        entity_type="implementation",
        metadata={"status": "completed", "files_created": [request.filename]}
    )

    return ImplementationResponse(...)
```

### Step 4.3: Update All Agent Dependencies

```txt
# agents/*/requirements.txt
# Add httpx for MCP calls
httpx==0.25.0
```

---

## 🎯 Phase 5: Tool-Aware Orchestrator Routing

**Objective:** Update orchestrator to verify tool availability before routing tasks.

### Step 5.1: Add Tool Availability Check

**File:** `agents/orchestrator/main.py`

```python
# Add tool availability checker
async def check_tool_availability(server: str, tool: str) -> bool:
    """Check if MCP tool is available"""
    try:
        async with httpx.AsyncClient() as client:
            tools_response = await client.get(f"{MCP_GATEWAY_URL}/tools")
            tools_data = tools_response.json()

            for server_data in tools_data.get("servers", []):
                if server_data["name"] == server:
                    tool_names = [t["name"] for t in server_data.get("tools", [])]
                    return tool in tool_names
            return False
    except:
        return False

async def verify_agent_tools(agent_type: AgentType, required_tools: List[Dict]) -> bool:
    """
    Verify all required tools are available before routing

    Args:
        agent_type: Target agent
        required_tools: List of {server, tool} dicts

    Returns:
        True if all tools available, False otherwise
    """
    for tool_spec in required_tools:
        available = await check_tool_availability(
            server=tool_spec["server"],
            tool=tool_spec["tool"]
        )
        if not available:
            logger.warning(
                f"Tool {tool_spec['server']}/{tool_spec['tool']} "
                f"not available for agent {agent_type}"
            )
            return False
    return True

@app.post("/orchestrate", response_model=TaskResponse)
async def orchestrate_task(request: TaskRequest):
    """
    Main orchestration endpoint with tool availability verification
    """
    import uuid

    task_id = str(uuid.uuid4())

    # Decompose into subtasks
    subtasks = decompose_request(request)

    # Verify tool availability for each subtask
    for subtask in subtasks:
        # Load required tools from mapping config
        required_tools = get_required_tools_for_agent(subtask.agent_type)

        tools_available = await verify_agent_tools(subtask.agent_type, required_tools)

        if not tools_available:
            logger.error(f"Required tools unavailable for {subtask.agent_type}")
            # Fall back to alternative agent or queue for retry
            subtask.status = TaskStatus.PENDING
            subtask.context_refs = subtask.context_refs or []
            subtask.context_refs.append("awaiting_tool_availability")

    # Continue with routing...
    return TaskResponse(...)

def get_required_tools_for_agent(agent_type: AgentType) -> List[Dict]:
    """Load required tools from mapping config"""
    # Load config/mcp-agent-tool-mapping.yaml
    with open("config/mcp-agent-tool-mapping.yaml") as f:
        mapping = yaml.safe_load(f)

    agent_config = mapping["agent_tool_mappings"].get(agent_type.value, {})
    recommended_tools = agent_config.get("recommended_tools", [])

    # Extract critical priority tools
    critical_tools = []
    for tool_group in recommended_tools:
        if tool_group.get("priority") == "critical":
            server = tool_group["server"]
            for tool in tool_group["tools"]:
                critical_tools.append({"server": server, "tool": tool})

    return critical_tools
```

---

## ✅ Phase 6: Automated Validation Script

**Objective:** Create PowerShell script to validate entire MCP integration.

### Step 6.1: Create Validation Script

**File:** `scripts/validate-mcp-config.ps1`

```powershell
# scripts/validate-mcp-config.ps1
# Comprehensive MCP integration validation

param(
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

Write-Host "=================================="
Write-Host "MCP Integration Validation"
Write-Host "=================================="
Write-Host ""

# Test 1: Gateway Health
Write-Host "[1/7] Checking MCP Gateway health..."
try {
    $gateway = Invoke-RestMethod "http://localhost:8000/health"
    Write-Host "  ✅ Gateway: $($gateway.status) | Servers: $($gateway.servers_running) | Tools: $($gateway.total_tools)" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Gateway not accessible: $_" -ForegroundColor Red
    exit 1
}

# Test 2: Tool Enumeration
Write-Host "[2/7] Enumerating available tools..."
try {
    $tools = Invoke-RestMethod "http://localhost:8000/tools"
    $serverCount = $tools.servers.Count
    $toolCount = ($tools.servers | ForEach-Object { $_.tools.Count } | Measure-Object -Sum).Sum
    Write-Host "  ✅ Discovered: $serverCount servers, $toolCount tools" -ForegroundColor Green

    if ($Verbose) {
        $tools.servers | ForEach-Object {
            Write-Host "    - $($_.name): $($_.tools.Count) tools"
        }
    }
} catch {
    Write-Host "  ❌ Tool enumeration failed: $_" -ForegroundColor Red
    exit 1
}

# Test 3: Agent Manifest Validation
Write-Host "[3/7] Validating agent manifest..."
if (Test-Path "agents/agents-manifest.json") {
    $manifest = Get-Content "agents/agents-manifest.json" | ConvertFrom-Json
    Write-Host "  ✅ Manifest version: $($manifest.version) | Agents: $($manifest.profiles.Count)" -ForegroundColor Green

    if ($Verbose) {
        $manifest.profiles | ForEach-Object {
            Write-Host "    - $($_.name): $($_.mcp_tools.recommended.Count) recommended tools"
        }
    }
} else {
    Write-Host "  ⚠️  Manifest not found (run scripts/generate-agent-manifest.ps1)" -ForegroundColor Yellow
}

# Test 4: Docker Compose MCP Integration
Write-Host "[4/7] Checking docker-compose MCP configuration..."
$composeContent = Get-Content "compose/docker-compose.yml" -Raw
$mcpEnvCount = ([regex]::Matches($composeContent, "MCP_GATEWAY_URL")).Count
Write-Host "  ✅ MCP_GATEWAY_URL found in $mcpEnvCount services" -ForegroundColor Green

# Test 5: Agent Health Checks
Write-Host "[5/7] Checking agent health endpoints..."
$agentPorts = 8001..8006
$healthyAgents = 0
foreach ($port in $agentPorts) {
    try {
        $agent = Invoke-RestMethod "http://localhost:$port/health" -TimeoutSec 5
        Write-Host "  ✅ Port $port ($($agent.service)): $($agent.status)" -ForegroundColor Green
        $healthyAgents++
    } catch {
        Write-Host "  ⚠️  Port $port not responding" -ForegroundColor Yellow
    }
}

# Test 6: Sample Tool Invocation
Write-Host "[6/7] Testing sample tool invocation (time server)..."
try {
    $timeResult = Invoke-RestMethod -Method Post `
        -Uri "http://localhost:8000/tools/time/get_current_time" `
        -ContentType "application/json" `
        -Body '{"params": {}}'

    Write-Host "  ✅ time/get_current_time: $($timeResult.result)" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Tool invocation failed: $_" -ForegroundColor Red
}

# Test 7: Memory Server Integration
Write-Host "[7/7] Testing memory server integration..."
try {
    $testEntity = @{
        params = @{
            entities = @(
                @{
                    name = "validation-test-$(Get-Date -Format 'yyyyMMddHHmmss')"
                    type = "test"
                    metadata = @{
                        purpose = "MCP integration validation"
                    }
                }
            )
        }
    } | ConvertTo-Json -Depth 5

    $memoryResult = Invoke-RestMethod -Method Post `
        -Uri "http://localhost:8000/tools/memory/create_entities" `
        -ContentType "application/json" `
        -Body $testEntity

    Write-Host "  ✅ memory/create_entities: success" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  Memory server test failed: $_" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "=================================="
Write-Host "Validation Summary"
Write-Host "=================================="
Write-Host "Gateway:        ✅"
Write-Host "Tool Discovery: ✅"
Write-Host "Agent Manifest: $(if (Test-Path 'agents/agents-manifest.json') { '✅' } else { '⚠️' })"
Write-Host "Docker Compose: ✅"
Write-Host "Healthy Agents: $healthyAgents/6"
Write-Host "Tool Invocation: ✅"
Write-Host "Memory Server:  ✅"
Write-Host ""
Write-Host "✅ MCP Integration validated successfully!" -ForegroundColor Green
```

### Step 6.2: Run Validation

```powershell
# Run validation
.\scripts\validate-mcp-config.ps1 -Verbose

# Expected output:
# ==================================
# MCP Integration Validation
# ==================================
# [1/7] Checking MCP Gateway health...
#   ✅ Gateway: ok | Servers: 17 | Tools: 150
# [2/7] Enumerating available tools...
#   ✅ Discovered: 17 servers, 150 tools
# ...
# ✅ MCP Integration validated successfully!
```

---

## 🚀 Phase 7: Deployment & Testing

**Objective:** Deploy updated stack and verify end-to-end workflows.

### Step 7.1: Backup Current State

```powershell
# Backup volumes
.\scripts\backup_volumes.sh

# Verify backup
ls backups/
```

### Step 7.2: Deploy Updated Stack

```powershell
# Rebuild containers with updated dependencies
.\scripts\rebuild.sh

# Wait for services to stabilize
Start-Sleep -Seconds 30

# Check all services
cd compose
docker-compose ps
```

### Step 7.3: End-to-End Integration Test

```powershell
# Test orchestrator → feature-dev workflow with MCP tools
$testRequest = @{
    description = "Implement user authentication feature"
    project_context = @{
        language = "Python"
        framework = "FastAPI"
    }
} | ConvertTo-Json

$orchestratorResponse = Invoke-RestMethod -Method Post `
    -Uri "http://localhost:8001/orchestrate" `
    -ContentType "application/json" `
    -Body $testRequest

Write-Host "Task ID: $($orchestratorResponse.task_id)"
Write-Host "Subtasks: $($orchestratorResponse.subtasks.Count)"

# Execute workflow
$executionResponse = Invoke-RestMethod -Method Post `
    -Uri "http://localhost:8001/execute/$($orchestratorResponse.task_id)"

Write-Host "Execution Status: $($executionResponse.status)"
$executionResponse.execution_results | ForEach-Object {
    Write-Host "  - $($_.agent): $($_.status)"
}
```

### Step 7.4: Verify Memory Server State

```powershell
# Query memory server for created entities
$memoryQuery = @{
    params = @{
        query = "authentication"
        type = "task"
    }
} | ConvertTo-Json

$memoryResults = Invoke-RestMethod -Method Post `
    -Uri "http://localhost:8000/tools/memory/search_nodes" `
    -ContentType "application/json" `
    -Body $memoryQuery

Write-Host "Memory Server Entities: $($memoryResults.result.Count)"
```

---

## 📊 Success Criteria

### ✅ Phase Completion Checklist

- [ ] **Phase 1:** `agents/agents-manifest.json` generated with 6 agent profiles
- [ ] **Phase 2:** `compose/docker-compose.yml` updated with MCP_GATEWAY_URL for all agents
- [ ] **Phase 3:** RAG service enhanced with memory/time server integration
- [ ] **Phase 4:** All agents have MCP client module and tool invocation helpers
- [ ] **Phase 5:** Orchestrator performs tool availability checks before routing
- [ ] **Phase 6:** Validation script passes all 7 tests
- [ ] **Phase 7:** End-to-end workflow test successful

### 📈 Performance Metrics

- **Gateway Response Time:** < 100ms for tool invocation
- **Agent Startup Time:** < 10s with MCP client initialization
- **Tool Discovery:** < 5s to enumerate 150 tools
- **Memory Operations:** < 200ms for entity creation/query
- **E2E Workflow:** < 60s for orchestrator → feature-dev → code-review cycle

### 🔍 Validation Outputs

All validation outputs logged to `reports/mcp-integration-validation.json`:

```json
{
  "timestamp": "2025-11-13T22:40:00Z",
  "validation_version": "1.0.0",
  "gateway_health": "ok",
  "servers_discovered": 17,
  "tools_discovered": 150,
  "agents_healthy": 6,
  "manifest_generated": true,
  "compose_updated": true,
  "test_results": {
    "tool_invocation": "success",
    "memory_integration": "success",
    "e2e_workflow": "success"
  }
}
```

---

## 🛠️ Troubleshooting Guide

### Issue 1: Gateway Not Accessible

**Symptom:** Validation fails at step 1

**Solution:**

```powershell
# Check gateway logs
docker-compose logs -f gateway-mcp

# Restart gateway
docker-compose restart gateway-mcp

# Verify network connectivity
docker network inspect devtools-network
```

### Issue 2: Agents Not Responding

**Symptom:** Validation fails at step 5

**Solution:**

```powershell
# Check agent logs
docker-compose logs -f <agent-name>

# Rebuild agent container
cd containers/<agent-name>
docker build -t devtools/<agent-name>:latest .

# Restart agent
docker-compose restart <agent-name>
```

### Issue 3: Tool Not Found

**Symptom:** Tool invocation returns 404

**Solution:**

```powershell
# Verify tool exists
curl http://localhost:8000/tools | jq '.servers[] | select(.name=="<server>") | .tools'

# Check mapping configuration
cat config/mcp-agent-tool-mapping.yaml | grep -A5 "<server>"

# Restart gateway to reload servers
docker-compose restart gateway-mcp
```

### Issue 4: Memory Server Errors

**Symptom:** Memory operations fail

**Solution:**

```powershell
# Check memory server in gateway
curl http://localhost:8000/servers | jq '.servers[] | select(.name=="memory")'

# Test memory server directly via gateway
curl -X POST http://localhost:8000/tools/memory/read_graph \
  -H "Content-Type: application/json" \
  -d '{"params": {}}'
```

---

## 📅 Execution Timeline

### Estimated Duration: 2-3 hours

| Phase | Task                     | Duration | Dependencies            |
| ----- | ------------------------ | -------- | ----------------------- |
| 0     | Prerequisites validation | 15 min   | Gateway, agents running |
| 1     | Generate agent manifest  | 10 min   | Mapping YAML            |
| 2     | Update docker-compose    | 15 min   | Phase 1                 |
| 3     | Enhance RAG service      | 20 min   | Phase 2                 |
| 4     | Pre-load MCP clients     | 30 min   | Phase 2                 |
| 5     | Tool-aware routing       | 25 min   | Phase 4                 |
| 6     | Validation script        | 15 min   | Phases 1-5              |
| 7     | Deployment & testing     | 30 min   | Phase 6                 |

**Total:** ~2.5 hours (excluding troubleshooting)

---

## 🎯 Next Steps

### Immediate (Post-Deployment)

1. Monitor agent logs for MCP tool invocation patterns
2. Analyze memory server entity growth
3. Review orchestrator routing decisions
4. Collect performance metrics (tool latency, success rates)

### Short-Term (1 week)

1. Optimize tool allocations based on usage data
2. Add caching layer for frequently accessed tools
3. Implement tool usage analytics dashboard
4. Document common tool invocation patterns per agent

### Long-Term (1 month)

1. Add new MCP servers based on agent needs
2. Implement tool recommendation engine
3. Automated tool mapping updates
4. Multi-environment MCP gateway (dev/staging/prod)

---

## 📚 References

- **[config/mcp-agent-tool-mapping.yaml](../config/mcp-agent-tool-mapping.yaml)** - Complete tool mappings
- **[docs/MCP_INTEGRATION.md](MCP_INTEGRATION.md)** - Integration guide
- **[docs/ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture
- **[docs/AGENT_ENDPOINTS.md](AGENT_ENDPOINTS.md)** - Agent API reference

---

**Document Status:** Ready for Execution
**Author:** Dev-Tools Team
**Date:** 2025-11-13
**Version:** 1.0.0
