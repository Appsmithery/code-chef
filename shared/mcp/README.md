# MCP Python SDK Architecture

**Version**: 2.0  
**Updated**: December 12, 2025  
**Status**: Production

---

## Overview

Direct MCP server access via [Docker MCP Toolkit](https://marketplace.visualstudio.com/items?itemName=ModelContextProtocol.mcp-docker).

### Architecture

```
Python Agents
    ↓
shared/lib/mcp_tool_client.py (stdio transport)
    ↓
docker mcp CLI
    ↓
MCP Servers (memory, filesystem, github, etc.)
```

**Key Benefits:**

- ✅ Direct stdio communication (no HTTP overhead)
- ✅ 178+ tools from 15+ MCP servers
- ✅ Progressive loading (10-30 tools vs all 178)
- ✅ Context-aware tool selection
- ✅ VS Code native integration

---

## Quick Start

### 1. Tool Discovery

```python
from shared.lib.mcp_discovery import get_mcp_discovery

discovery = get_mcp_discovery()
servers = discovery.discover_servers()

# Returns:
{
    "servers": [
        {"name": "memory", "tools": 12},
        {"name": "filesystem", "tools": 8},
        {"name": "github", "tools": 15}
    ],
    "total_tools": 178
}
```

### 2. Direct Tool Invocation

```python
from shared.lib.mcp_tool_client import get_mcp_tool_client

client = get_mcp_tool_client("feature_dev")

# Read a file
result = await client.invoke_tool_simple(
    server="rust-mcp-filesystem",
    tool="read_file",
    params={"path": "/workspace/src/main.py"}
)

# Create memory entities
result = await client.invoke_tool_simple(
    server="memory",
    tool="create_entities",
    params={
        "entities": [{
            "name": "feature-auth",
            "type": "task",
            "metadata": {"status": "in_progress"}
        }]
    }
)
```

### 3. Progressive Tool Loading

**Problem**: Loading all 178 tools wastes context and costs tokens.

**Solution**: Progressive loading selects 10-30 relevant tools based on task.

```python
from shared.lib.progressive_mcp_loader import ProgressiveMCPLoader, ToolLoadingStrategy

loader = ProgressiveMCPLoader(
    mcp_client=client,
    mcp_discovery=discovery,
    default_strategy=ToolLoadingStrategy.PROGRESSIVE
)

# Task: "Implement JWT authentication"
tools = await loader.get_tools_for_task(
    task_description="Implement JWT authentication middleware",
    agent_name="feature_dev"
)

# Returns ~15 tools:
# - rust-mcp-filesystem: read_file, write_file, list_directory
# - memory: create_entities, get_entities
# - github: search_code, get_file_contents
# Instead of all 178 tools!
```

---

## Tool Loading Strategies

| Strategy        | Tool Count | Use Case                            | Token Cost   |
| --------------- | ---------- | ----------------------------------- | ------------ |
| **MINIMAL**     | 10-30      | Simple tasks, keyword-matched       | ~500 tokens  |
| **PROGRESSIVE** | 30-60      | Multi-step tasks, agent-prioritized | ~1500 tokens |
| **FULL**        | 150+       | Debugging tool discovery issues     | ~8000 tokens |

**Recommendation**: Use `PROGRESSIVE` (default) for best balance.

---

## Key Files Reference

| File                                                                       | Purpose                            | Status    |
| -------------------------------------------------------------------------- | ---------------------------------- | --------- |
| [`shared/lib/mcp_tool_client.py`](../lib/mcp_tool_client.py)               | **Direct stdio tool invocation**   | ✅ Active |
| [`shared/lib/mcp_discovery.py`](../lib/mcp_discovery.py)                   | **Server/tool enumeration**        | ✅ Active |
| [`shared/lib/progressive_mcp_loader.py`](../lib/progressive_mcp_loader.py) | **Context-optimized loading**      | ✅ Active |
| [`shared/lib/mcp_client.py`](../lib/mcp_client.py)                         | Agent manifest and profile loading | ✅ Active |

---

## Available MCP Servers

Common servers available via Docker MCP Toolkit:

| Server                | Tools | Use Cases                            |
| --------------------- | ----- | ------------------------------------ |
| `memory`              | 12    | Entity storage, knowledge graphs     |
| `rust-mcp-filesystem` | 8     | File operations, directory traversal |
| `github`              | 15    | Repository search, PR management     |
| `time`                | 3     | Timestamps, date calculations        |
| `sequential-thinking` | 5     | Multi-step reasoning, planning       |
| `brave-search`        | 2     | Web search integration               |
| `fetch`               | 1     | HTTP requests                        |

**Full list**: Run `docker mcp list` or use `mcp_discovery.discover_servers()`.

---

## Agent-Specific Tool Priorities

Each agent has prioritized tools defined in `config/mcp-agent-tool-mapping.yaml`:

```yaml
feature_dev:
  priority_keywords:
    - filesystem # read_file, write_file
    - github # search_code
    - memory # create_entities
  priority_servers:
    - rust-mcp-filesystem
    - memory
```

Progressive loader uses these priorities to select optimal tools per agent.

---

## Troubleshooting

### Tools Not Found

```bash
# Verify Docker MCP Toolkit installed
docker mcp version

# List available servers
docker mcp list

# Test tool invocation
docker mcp invoke memory create_entities \
  --params '{"entities": [{"name": "test", "type": "debug"}]}'
```

### Slow Tool Loading

**Cause**: Using `ToolLoadingStrategy.FULL` loads all 178 tools (~8000 tokens).

**Solution**: Switch to `PROGRESSIVE` (30-60 tools, ~1500 tokens):

```python
loader = ProgressiveMCPLoader(
    default_strategy=ToolLoadingStrategy.PROGRESSIVE
)
```

---

## Related Documentation

- [Architecture Guide](../../support/docs/architecture-and-platform/ARCHITECTURE.md) - System overview
- [Progressive Tool Loading](../lib/progressive_mcp_loader.py) - Implementation details
- [Agent Tool Mapping](../../config/mcp-agent-tool-mapping.yaml) - Priority configuration
- [VS Code Extension](https://marketplace.visualstudio.com/items?itemName=ModelContextProtocol.mcp-docker) - Docker MCP Toolkit

---

## Linear OAuth Service (Not MCP Routing)

The `shared/mcp/gateway/` directory contains a **separate** Node.js service for Linear OAuth authentication. This is NOT an MCP tool router.

**See**: [`shared/mcp/gateway/README.md`](gateway/README.md) for Linear OAuth documentation.

---

**Questions?** File an issue in [Linear](https://linear.app/dev-ops/project/codechef-78b3b839d36b) with label `mcp-integration`.
