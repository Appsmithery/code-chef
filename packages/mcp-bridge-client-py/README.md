# MCP Bridge Client (Python)

Lightweight Python client library for accessing Dev-Tools MCP gateway (150+ tools across 18 servers) from any Python project without cloning the repository.

## Features

- **150+ MCP Tools**: Access memory, filesystem, git, github, linear, notion, terraform, docker, database, and more
- **Progressive Loading**: 80-90% token reduction via keyword-based tool filtering
- **Caching**: 5-minute TTL for tool catalog (configurable)
- **Type Safety**: Full type hints with Pydantic models
- **Async/Await**: Modern asyncio-based API
- **Context Manager**: Automatic resource cleanup

## Installation

```bash
pip install mcp-bridge-client
```

## Quick Start

```python
import asyncio
from mcp_bridge_client import MCPBridgeClient

async def main():
    async with MCPBridgeClient(gateway_url='http://45.55.173.72:8000') as client:
        # List all tools
        tools = await client.list_tools()
        print(f"Found {len(tools)} tools")

        # Search tools by keyword
        memory_tools = await client.search_tools('memory')
        print(f"Memory tools: {len(memory_tools)}")

        # Invoke a tool
        result = await client.invoke_tool('memory/read', {'key': 'user-prefs'})
        if result.success:
            print('Result:', result.result)
        else:
            print('Error:', result.error)

asyncio.run(main())
```

## Usage Examples

### Progressive Tool Loading

Automatically filter tools based on task description (80-90% token savings):

```python
# Only loads relevant tools for git operations
git_tools = await client.get_tools_for_task('commit my changes to git')

# Only loads database and filesystem tools
db_tools = await client.get_tools_for_task('query users from postgres database')
```

### Server-Specific Tools

```python
# Get all GitHub tools
github_tools = await client.get_tools_by_server('github')

# List all available servers
servers = await client.list_servers()
print('Available servers:', servers)
```

### Tool Invocation

```python
# Memory operations
await client.invoke_tool('memory/write', {
    'key': 'user-prefs',
    'value': {'theme': 'dark', 'notifications': True}
})

prefs = await client.invoke_tool('memory/read', {'key': 'user-prefs'})

# File operations
await client.invoke_tool('filesystem/write_file', {
    'path': './config.json',
    'content': '{"version": "1.0"}'
})

# Git operations
await client.invoke_tool('git/commit', {
    'message': 'feat: add new feature',
    'files': ['src/main.py']
})

# GitHub operations
await client.invoke_tool('github/create_issue', {
    'repo': 'owner/repo',
    'title': 'Bug report',
    'body': 'Description of the issue'
})

# Linear operations
await client.invoke_tool('linear/create_issue', {
    'title': 'Implement feature X',
    'description': 'Detailed requirements',
    'priority': 1
})
```

### Configuration

```python
client = MCPBridgeClient(
    gateway_url='http://45.55.173.72:8000',  # MCP gateway endpoint
    timeout=30.0,                             # Request timeout (seconds)
    enable_caching=True,                      # Enable tool catalog caching
    cache_ttl=300,                            # Cache TTL (seconds, default 5min)
    progressive_loading=True                  # Enable keyword-based filtering
)

# Get current config
config = client.get_config()
print('Config:', config)

# Clear cache
client.clear_cache()
```

### Health Checks

```python
health = await client.health()
print('Gateway status:', health['status'])
print('Available servers:', health['servers'])
print('Total tools:', health['tools'])
```

## API Reference

### `MCPBridgeClient`

Main client class for MCP gateway interaction.

#### Constructor

```python
MCPBridgeClient(
    gateway_url: str = "http://45.55.173.72:8000",
    timeout: float = 30.0,
    enable_caching: bool = True,
    cache_ttl: int = 300,
    progressive_loading: bool = True
)
```

#### Methods

- `list_tools(force_refresh: bool = False) -> List[MCPTool]` - List all tools
- `get_tools_for_task(task_description: str) -> List[MCPTool]` - Progressive loading
- `search_tools(query: str) -> List[MCPTool]` - Search by keyword
- `get_tools_by_server(server_name: str) -> List[MCPTool]` - Filter by server
- `list_servers() -> List[str]` - List all servers
- `invoke_tool(tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> ToolInvocationResponse` - Invoke tool
- `health() -> Dict[str, Any]` - Health check
- `clear_cache() -> None` - Clear tool cache
- `get_config() -> Dict[str, Any]` - Get configuration
- `close() -> None` - Close HTTP client

### Models

```python
class MCPTool(BaseModel):
    name: str
    description: str
    server: str
    inputSchema: Optional[Dict[str, Any]] = None

class ToolInvocationResponse(BaseModel):
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
```

## Available MCP Servers

- **memory** - Persistent key-value storage
- **filesystem** - File and directory operations
- **git** - Git version control operations
- **github** - GitHub API integration
- **linear** - Linear project management
- **notion** - Notion workspace integration
- **context7** - Codebase analysis and search
- **terraform** - Infrastructure as code
- **docker** - Container management
- **kubernetes** - K8s cluster operations
- **postgres** - PostgreSQL database
- **sqlite** - SQLite database
- **brave-search** - Web search
- **fetch** - HTTP requests
- **puppeteer** - Browser automation
- **time** - Date/time operations
- **prometheus** - Metrics and monitoring
- **sequential-thinking** - Reasoning tools

## Integration Examples

### FastAPI Application

```python
from fastapi import FastAPI
from mcp_bridge_client import MCPBridgeClient

app = FastAPI()
mcp_client = MCPBridgeClient()

@app.post("/api/tools/{tool_name}")
async def invoke_tool(tool_name: str, args: dict):
    result = await mcp_client.invoke_tool(tool_name, args)
    return result.dict()

@app.get("/api/tools")
async def list_tools():
    tools = await mcp_client.list_tools()
    return {"tools": [tool.dict() for tool in tools]}

@app.on_event("shutdown")
async def shutdown():
    await mcp_client.close()
```

### CLI Tool

```python
import asyncio
import click
from mcp_bridge_client import MCPBridgeClient

@click.group()
def cli():
    pass

@cli.command()
def list_tools():
    """List all MCP tools"""
    async def _list():
        async with MCPBridgeClient() as client:
            tools = await client.list_tools()
            for tool in tools:
                print(f"{tool.name} - {tool.description}")

    asyncio.run(_list())

@cli.command()
@click.argument('tool')
@click.argument('args', default='{}')
def invoke(tool, args):
    """Invoke an MCP tool"""
    import json

    async def _invoke():
        async with MCPBridgeClient() as client:
            parsed_args = json.loads(args)
            result = await client.invoke_tool(tool, parsed_args)
            print(result.dict())

    asyncio.run(_invoke())

if __name__ == '__main__':
    cli()
```

### Django Management Command

```python
from django.core.management.base import BaseCommand
import asyncio
from mcp_bridge_client import MCPBridgeClient

class Command(BaseCommand):
    help = 'Sync data using MCP tools'

    def handle(self, *args, **options):
        asyncio.run(self.async_handle())

    async def async_handle(self):
        async with MCPBridgeClient() as client:
            # Use MCP tools
            result = await client.invoke_tool('database/query', {
                'query': 'SELECT * FROM users'
            })
            self.stdout.write(self.style.SUCCESS(f'Synced {len(result.result)} users'))
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy mcp_bridge_client

# Linting
ruff check mcp_bridge_client

# Format
black mcp_bridge_client
```

## License

MIT

## Related

- [TypeScript Client](../mcp-bridge-client) - Node.js/TypeScript equivalent
- [VS Code Extension](../../extensions/vscode-devtools-copilot) - VS Code integration
- [Dev-Tools Repository](https://github.com/Appsmithery/Dev-Tools) - Main repository
- [MCP Gateway](http://45.55.173.72:8000) - Live gateway endpoint
