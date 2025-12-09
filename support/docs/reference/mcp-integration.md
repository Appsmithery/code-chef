---
status: active
category: reference
last_updated: 2025-12-09
---

# MCP Integration Guide

**Version:** 1.1.0
**Last Updated:** December 9, 2025
**Purpose:** Document MCP Gateway architecture, tool-to-agent mappings, and integration patterns

---

## 🎯 Overview

The Model Context Protocol (MCP) integration provides Dev-Tools agents with 150+ specialized tools across 17 servers. The central MCP Gateway acts as an HTTP-to-stdio bridge, enabling agents to invoke tools via REST API while the gateway manages server lifecycle, health checks, and transport protocols.

### Key Benefits

1. **Tool Abundance** - 150+ tools (filesystem, git, docker, notion, playwright, etc.)
2. **Standardized Interface** - All agents access tools via consistent HTTP API
3. **Isolation** - MCP servers run in isolated processes with resource limits
4. **Dynamic Discovery** - Tools automatically discovered at runtime
5. **MECE Alignment** - Tools mapped to agent domains for specialization

---

## 🏗️ Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Agents                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │Orchestr. │ │Feature-  │ │Code-     │ │Infra     │ ... │
│  │          │ │Dev       │ │Review    │ │          │     │
│  └─────┬────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘     │
│        │           │            │            │             │
│        └───────────┴────────────┴────────────┘             │
│                         │                                   │
│                         │ HTTP (REST)                       │
│                         ▼                                   │
│            ┌────────────────────────────┐                  │
│            │     MCP Gateway (8000)     │                  │
│            │   Node.js/Express Server   │                  │
│            └────────┬───────────────────┘                  │
│                     │                                       │
│                     │ stdio transport                       │
│                     ▼                                       │
│   ┌─────────────────────────────────────────────────────┐ │
│   │              MCP Servers (17)                       │ │
│   │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐      │ │
│   │  │memory  │ │gitmcp  │ │docker  │ │playwright│  ...│ │
│   │  │(9 tools│ │(5 tools│ │(13     │ │(21 tools │      │ │
│   │  └────────┘ └────────┘ └────────┘ └────────┘      │ │
│   └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Component Roles

- **Agents:** Invoke tools via HTTP POST to gateway
- **MCP Gateway:** HTTP→stdio bridge, server lifecycle management
- **MCP Servers:** Implement tool logic (file I/O, git, docker, etc.)

---

## 📋 Available MCP Servers

### Complete Server Inventory

| Server                  | Tools | Primary Use Cases                            | Priority Agents                         |
| ----------------------- | ----- | -------------------------------------------- | --------------------------------------- |
| **rust-mcp-filesystem** | 24    | File I/O, directory management, search       | All agents                              |
| **stripe**              | 22    | Payment processing (conditional)             | Feature-dev (payment features)          |
| **playwright**          | 21    | Browser automation, E2E testing, screenshots | Feature-dev, CI/CD, Documentation       |
| **notion**              | 19    | Task management, documentation, dashboards   | Orchestrator, Documentation             |
| **dockerhub**           | 13    | Container management, image operations       | Infrastructure, CI/CD                   |
| **hugging-face**        | 9     | Code generation, analysis, docstrings        | Feature-dev, Code-review, Documentation |
| **memory**              | 9     | Knowledge graph, entity storage              | All agents (shared context)             |
| **google-maps**         | 8     | Geocoding, region metadata                   | Infrastructure (multi-region)           |
| **gitmcp**              | 5     | Git operations, PRs, diffs                   | Feature-dev, Code-review, CI/CD         |
| **next-devtools**       | 5     | Next.js analysis, routing inspection         | Feature-dev, Documentation              |
| **gmail-mcp**           | 3     | Email notifications, search                  | Orchestrator, Infrastructure, CI/CD     |
| **perplexity-ask**      | 3     | Research, API documentation lookup           | Feature-dev, Documentation              |
| **youtube_transcript**  | 3     | Video transcript extraction                  | Documentation (tutorial conversion)     |
| **context7**            | 2     | Document corpus search                       | All agents (documentation lookup)       |
| **time**                | 2     | Timestamp generation, timezone conversion    | All agents (audit trail)                |
| **fetch**               | 1     | HTTP requests, API calls                     | All agents (external integration)       |
| **sequentialthinking**  | 1     | Step-by-step reasoning for complex tasks     | Orchestrator (task decomposition)       |

**Total:** 17 servers, 150 tools

---

## 🔧 Tool-to-Agent Mapping

### Configuration File

**Location:** `config/mcp-agent-tool-mapping.yaml`

**Structure:**

```yaml
agent_tool_mappings:
  orchestrator:
    mission: "Coordinates task routing, agent hand-offs, workflow state"
    recommended_tools:
      - server: "memory"
        tools:
          ["create_entities", "create_relations", "read_graph", "search_nodes"]
        rationale: "Maintain task graph, agent relationships, workflow state"
        priority: "critical"
        use_cases:
          - "Store task decomposition trees"
          - "Track agent assignments and dependencies"
          - "Query historical workflow patterns"
```

### Mapping Principles

1. **MECE Alignment** - Tools mapped to agent domains (but not exclusive)
2. **Priority Levels** - Critical, high, medium, low based on agent workflows
3. **Rationale Documentation** - Every mapping includes justification
4. **Use Case Examples** - Concrete scenarios for tool application
5. **Shared vs. Exclusive** - Universal tools (memory, time, filesystem) vs. specialized

### Priority Tool Allocations

#### Orchestrator (Critical Tools)

- `memory/*` - Workflow state tracking
- `notion/*` - Global task board management
- `sequentialthinking/think_step` - Complex task decomposition
- `time/*` - Event timestamping and SLA tracking

#### Feature-Dev (Critical Tools)

- `rust-mcp-filesystem/*` - Code generation and file management
- `gitmcp/*` - Branch creation, commits, PRs
- `playwright/*` - E2E test generation
- `hugging-face/generate_code` - AI-powered code synthesis

#### Code-Review (Critical Tools)

- `gitmcp/get_diff` - Retrieve PR diffs
- `rust-mcp-filesystem/read_file` - Read source files
- `hugging-face/analyze_code` - AI-powered code analysis

#### Infrastructure (Critical Tools)

- `dockerhub/*` - Container image management
- `rust-mcp-filesystem/*` - IaC file generation (Terraform, Compose)
- `gitmcp/*` - Infrastructure code versioning

#### CI/CD (Critical Tools)

- `gitmcp/*` - Monitor commits and PRs
- `rust-mcp-filesystem/write_file` - Generate pipeline files
- `dockerhub/*` - Build container execution
- `playwright/*` - E2E test execution

#### Documentation (Critical Tools)

- `rust-mcp-filesystem/*` - Read/write documentation files
- `hugging-face/explain_code` - Generate docstrings
- `notion/*` - Publish to wiki/knowledge base
- `playwright/screenshot` - Capture UI states for docs

---

## 🧠 Memory MCP Tools (CHEF-203)

Cross-agent knowledge sharing via RAG service integration.

### Available Memory Tools

| Tool                | Path                                 | Description                            |
| ------------------- | ------------------------------------ | -------------------------------------- |
| `query_insights`    | `POST /rag/insights/query`           | Retrieve relevant insights for context |
| `store_insight`     | `POST /rag/insights/store`           | Store new insight from agent execution |
| `get_agent_history` | `GET /rag/insights/agent/{agent_id}` | Get insight history for specific agent |

### Tool Configuration

```yaml
memory_tools:
  description: "Cross-agent knowledge sharing via RAG service"
  rag_service_url: "http://rag-context:8007"
  tools:
    - name: query_insights
      path: "/rag/insights/query"
      method: POST
      priority_agents: ["supervisor", "feature_dev", "code_review"]
      keywords: ["insights", "knowledge", "context", "memory", "recall"]
```

### Insight Types

```python
class InsightType(str, Enum):
    ARCHITECTURAL_DECISION = "architectural_decision"
    ERROR_PATTERN = "error_pattern"
    CODE_PATTERN = "code_pattern"
    TASK_RESOLUTION = "task_resolution"
    SECURITY_FINDING = "security_finding"
```

### Integration with Workflow State

Insights are captured during agent execution and persisted in `WorkflowState.captured_insights` for checkpoint recovery. On workflow resume, the last 10 insights are injected as context.

---

## 🌐 MCP Gateway API

### Gateway Endpoints

#### List All Tools

```http
GET /tools
```

**Response:**

```json
{
  "servers": [
    {
      "name": "memory",
      "tools": [
        {"name": "create_entities", "description": "Create entities in knowledge graph"},
        {"name": "create_relations", "description": "Create relationships between entities"},
        ...
      ]
    },
    ...
  ]
}
```

#### Invoke Tool

```http
POST /tools/{server}/{tool}
Content-Type: application/json

{
  "params": {
    "key": "value"
  }
}
```

**Example:**

```bash
curl -X POST http://gateway-mcp:8000/tools/memory/create_entities \
  -H "Content-Type: application/json" \
  -d '{
    "params": {
      "entities": [
        {"name": "task-123", "type": "task", "metadata": {...}}
      ]
    }
  }'
```

**Response:**

```json
{
  "success": true,
  "result": {
    "created_ids": ["entity-uuid-1", "entity-uuid-2"]
  }
}
```

#### Server Status

```http
GET /servers
```

**Response:**

```json
{
  "servers": [
    {"name": "memory", "status": "running", "pid": 12345, "uptime_seconds": 3600},
    {"name": "gitmcp", "status": "running", "pid": 12346, "uptime_seconds": 3600},
    ...
  ]
}
```

#### Health Check

```http
GET /health
```

**Response:**

```json
{
  "status": "ok",
  "service": "mcp-gateway",
  "timestamp": "2025-11-13T22:40:00Z",
  "servers_running": 17,
  "total_tools": 150
}
```

---

## 🔌 Agent Integration Patterns

### Python FastAPI Agent Example

```python
import httpx
from fastapi import FastAPI

app = FastAPI()

# MCP Gateway configuration
MCP_GATEWAY_URL = "http://gateway-mcp:8000"

async def invoke_mcp_tool(server: str, tool: str, params: dict):
    """Generic MCP tool invocation helper"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MCP_GATEWAY_URL}/tools/{server}/{tool}",
            json={"params": params},
            timeout=30.0
        )
        return response.json()

@app.post("/implement")
async def implement_feature(request: dict):
    """Feature-dev agent implementation endpoint"""

    # Step 1: Read existing codebase with rust-mcp-filesystem
    files = await invoke_mcp_tool(
        server="rust-mcp-filesystem",
        tool="list_directory",
        params={"path": "/workspace/src"}
    )

    # Step 2: Generate code with hugging-face
    generated_code = await invoke_mcp_tool(
        server="hugging-face",
        tool="generate_code",
        params={
            "prompt": f"Implement {request['description']}",
            "context": files
        }
    )

    # Step 3: Write generated code
    await invoke_mcp_tool(
        server="rust-mcp-filesystem",
        tool="write_file",
        params={
            "path": "/workspace/src/feature.py",
            "content": generated_code["result"]
        }
    )

    # Step 4: Create git branch and commit
    await invoke_mcp_tool(
        server="gitmcp",
        tool="create_branch",
        params={"branch_name": f"feature/{request['task_id']}"}
    )

    await invoke_mcp_tool(
        server="gitmcp",
        tool="commit_changes",
        params={
            "message": f"Implement {request['description']}",
            "files": ["/workspace/src/feature.py"]
        }
    )

    return {"status": "completed", "artifacts": [...]}
```

### Tool Invocation Best Practices

1. **Timeout Configuration** - Set reasonable timeouts (30s default, 60s for heavy operations)
2. **Error Handling** - Catch HTTPException and provide fallback logic
3. **Batch Operations** - Group related tool calls when possible
4. **Caching** - Cache frequently accessed data (e.g., filesystem listings)
5. **Logging** - Log all tool invocations for audit trail

---

## 🔄 Shared Context Infrastructure

### Memory Server Integration

**Purpose:** Universal knowledge graph for cross-agent context sharing

**Key Tools:**

- `create_entities` - Store tasks, agents, artifacts as graph nodes
- `create_relations` - Link entities (task → agent, agent → artifact)
- `read_graph` - Query entire knowledge graph
- `search_nodes` - Semantic search across entities

**Usage Pattern:**

```python
# Orchestrator logs task decomposition
await invoke_mcp_tool(
    server="memory",
    tool="create_entities",
    params={
        "entities": [
            {
                "name": "task-123",
                "type": "task",
                "metadata": {
                    "description": "Implement user authentication",
                    "status": "pending",
                    "assigned_agent": "feature-dev"
                }
            }
        ]
    }
)

# Feature-dev queries task context
task_context = await invoke_mcp_tool(
    server="memory",
    tool="search_nodes",
    params={"query": "authentication", "type": "task"}
)
```

**Integration with RAG Service:**

The memory server complements (not replaces) the RAG service:

- **Memory Server:** Structured entities, relationships, workflow state
- **RAG Service:** Unstructured text, code snippets, semantic similarity

Both should be queried for comprehensive context:

```python
# Get structured task context from memory
task_graph = await invoke_mcp_tool("memory", "read_graph", {...})

# Get semantic code patterns from RAG
code_patterns = await httpx.post(
  "http://rag-context:8007/query",
  json={"query": "authentication patterns", "collection": "code_patterns"}
)

# Combine contexts
context = {
    "workflow_state": task_graph,
    "code_patterns": code_patterns
}
```

### Time Server Integration

**Purpose:** Universal timestamping and timezone handling

**Key Tools:**

- `get_current_time` - ISO 8601 timestamp
- `convert_timezone` - Convert between timezones

**Usage Pattern:**

```python
# All agents timestamp operations
timestamp = await invoke_mcp_tool(
    server="time",
    tool="get_current_time",
    params={}
)

# Store in audit log
await invoke_mcp_tool(
    server="memory",
    tool="add_observations",
    params={
        "entity_id": "task-123",
        "observations": [f"Started at {timestamp}"]
    }
)
```

---

## 📊 Tool Usage Analytics

### Recommended Monitoring

Track tool invocation patterns to optimize mappings:

```python
# Log tool usage (pseudo-code)
tool_usage_log = {
    "agent": "feature-dev",
    "timestamp": await get_current_time(),
    "tool": "rust-mcp-filesystem/write_file",
    "duration_ms": 150,
    "status": "success"
}

# Store in memory or state persistence
await store_metric(tool_usage_log)
```

**Key Metrics:**

- **Invocation Count** - Which tools are used most by which agents
- **Success Rate** - Tool reliability per agent
- **Latency** - Tool response times
- **Failure Patterns** - Common error scenarios

### Optimization Triggers

- **High failure rate (>10%):** Review tool configuration or agent logic
- **High latency (>5s):** Consider caching or async patterns
- **Low usage (<5/day):** Consider removing from recommended_tools
- **Cross-agent conflicts:** Refine tool allocations in mapping.yaml

---

## 🚀 Deployment Configuration

### Docker Compose Integration

**Current Setup:**

```yaml
# deploy/docker-compose.yml
services:
  gateway-mcp:
    build:
      context: ..
      dockerfile: shared/gateway/Dockerfile
    ports:
      - "8000:8000"
    environment:
      - SERVICE_NAME=gateway-mcp
      - NODE_ENV=production
    networks:
      - devtools-network
    volumes:
      - mcp-config:/app/config

  orchestrator:
    environment:
      - MCP_GATEWAY_URL=http://gateway-mcp:8000
    depends_on:
      - gateway-mcp
```

**Required Environment Variables:**

All agents should include:

```yaml
environment:
  - MCP_GATEWAY_URL=http://gateway-mcp:8000 # Gateway endpoint
  - MCP_TIMEOUT=30 # Tool invocation timeout (seconds)
```

### Secret Configuration

For MCP servers requiring authentication (notion, gmail, stripe):

```yaml
services:
  gateway-mcp:
    secrets:
      - notion_api_key
      - gmail_credentials
      - stripe_api_key

secrets:
  notion_api_key:
    file: ../config/env/secrets/notion_api_key.txt
  gmail_credentials:
    file: ../config/env/secrets/gmail_credentials.json
  stripe_api_key:
    file: ../config/env/secrets/stripe_api_key.txt
```

---

## 🛠️ Validation & Testing

### Configuration Validation Script

**Location:** `scripts/validate-mcp-config.ps1` (to be created)

**Purpose:**

1. Verify gateway connectivity
2. Enumerate available tools
3. Test tool invocations for each agent
4. Validate tool-to-agent mappings against actual capabilities

**Example Workflow:**

```powershell
# scripts/validate-mcp-config.ps1
# 1. Check gateway health
$gatewayHealth = Invoke-RestMethod "http://localhost:8000/health"

# 2. List all tools
$tools = Invoke-RestMethod "http://localhost:8000/tools"

# 3. Verify agent mappings
$mappings = Get-Content "config/mcp-agent-tool-mapping.yaml" | ConvertFrom-Yaml
foreach ($agent in $mappings.agent_tool_mappings.Keys) {
    foreach ($tool in $mappings.agent_tool_mappings[$agent].recommended_tools) {
        # Verify tool exists in gateway
        $serverTools = $tools.servers | Where-Object { $_.name -eq $tool.server }
        if (-not $serverTools) {
            Write-Error "Agent $agent references missing server: $($tool.server)"
        }
    }
}

# 4. Test sample tool invocations
$testResult = Invoke-RestMethod -Method Post `
    -Uri "http://localhost:8000/tools/time/get_current_time" `
    -ContentType "application/json" `
    -Body '{"params": {}}'
```

### Integration Tests

```python
# testing/integration/test_mcp_integration.py
import pytest
import httpx

MCP_GATEWAY = "http://localhost:8000"

@pytest.mark.asyncio
async def test_gateway_health():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{MCP_GATEWAY}/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_tool_invocation():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{MCP_GATEWAY}/tools/time/get_current_time",
            json={"params": {}}
        )
        assert response.status_code == 200
        assert "result" in response.json()

@pytest.mark.asyncio
async def test_memory_server_workflow():
    """Test cross-agent context sharing via memory server"""
    async with httpx.AsyncClient() as client:
        # Orchestrator creates entity
        create_response = await client.post(
            f"{MCP_GATEWAY}/tools/memory/create_entities",
            json={
                "params": {
                    "entities": [{"name": "test-task", "type": "task"}]
                }
            }
        )
        assert create_response.status_code == 200

        # Feature-dev queries entity
        search_response = await client.post(
            f"{MCP_GATEWAY}/tools/memory/search_nodes",
            json={"params": {"query": "test-task", "type": "task"}}
        )
        assert search_response.status_code == 200
        assert len(search_response.json()["result"]) > 0
```

---

## 📈 Performance Optimization

### Tool Invocation Patterns

**Sequential (Slow):**

```python
file1 = await invoke_tool("rust-mcp-filesystem", "read_file", {"path": "a.py"})
file2 = await invoke_tool("rust-mcp-filesystem", "read_file", {"path": "b.py"})
file3 = await invoke_tool("rust-mcp-filesystem", "read_file", {"path": "c.py"})
# Total time: 3 * latency
```

**Parallel (Fast):**

```python
import asyncio

files = await asyncio.gather(
    invoke_tool("rust-mcp-filesystem", "read_file", {"path": "a.py"}),
    invoke_tool("rust-mcp-filesystem", "read_file", {"path": "b.py"}),
    invoke_tool("rust-mcp-filesystem", "read_file", {"path": "c.py"})
)
# Total time: max(latency1, latency2, latency3)
```

### Caching Strategy

```python
from functools import lru_cache
from datetime import datetime, timedelta

# Cache tool results with TTL
tool_cache = {}
cache_ttl = timedelta(minutes=5)

async def invoke_tool_cached(server: str, tool: str, params: dict):
    cache_key = f"{server}:{tool}:{hash(frozenset(params.items()))}"

    if cache_key in tool_cache:
        cached_result, timestamp = tool_cache[cache_key]
        if datetime.now() - timestamp < cache_ttl:
            return cached_result

    result = await invoke_mcp_tool(server, tool, params)
    tool_cache[cache_key] = (result, datetime.now())
    return result
```

---

## 🔍 Troubleshooting

### Common Issues

#### 1. Gateway Not Accessible

**Symptom:** `httpx.ConnectError: Connection refused`

**Solution:**

```bash
# Check gateway status
docker-compose ps gateway-mcp

# View gateway logs
docker-compose logs -f gateway-mcp

# Restart gateway
docker-compose restart gateway-mcp
```

#### 2. Tool Not Found

**Symptom:** `{"error": "Tool 'xyz' not found in server 'abc'"}`

**Solution:**

```bash
# List available tools
curl http://localhost:8000/tools | jq

# Verify tool mapping configuration
cat config/mcp-agent-tool-mapping.yaml
```

#### 3. MCP Server Crashed

**Symptom:** Gateway logs show server spawn failures

**Solution:**

```bash
# Check server status
curl http://localhost:8000/servers | jq

# Manually test server
docker mcp gateway run

# Restart gateway to respawn servers
docker-compose restart gateway-mcp
```

#### 4. Timeout Errors

**Symptom:** `httpx.ReadTimeout: Request timeout`

**Solution:**

```python
# Increase timeout for heavy operations
await invoke_mcp_tool(
    server="playwright",
    tool="screenshot",
    params={...},
    timeout=60.0  # 60 seconds for browser operations
)
```

---

## 📚 Additional Resources

- **[MCP Specification](https://modelcontextprotocol.io)** - Official MCP protocol documentation
- **[config/mcp-agent-tool-mapping.yaml](../config/mcp-agent-tool-mapping.yaml)** - Complete tool mappings
- **[architecture.md](../architecture-and-platform/architecture.md)** - System architecture overview

---

**Maintained by:** Dev-Tools Team
**Questions:** Open an issue on GitHub
**Last Validated:** 2025-11-13 (MCP Gateway discovery showed 150 tools across 17 servers)
