# MCP Bridge Client (TypeScript/Node.js)

Lightweight client library for accessing Dev-Tools MCP gateway (150+ tools across 18 servers) from any TypeScript/JavaScript project without cloning the repository.

## Features

- **150+ MCP Tools**: Access memory, filesystem, git, github, linear, notion, terraform, docker, database, and more
- **Progressive Loading**: 80-90% token reduction via keyword-based tool filtering
- **Caching**: 5-minute TTL for tool catalog (configurable)
- **Type Safety**: Full TypeScript support with comprehensive types
- **Zero Configuration**: Works out-of-box with default gateway URL
- **Async/Await**: Modern promise-based API

## Installation

```bash
npm install @appsmithery/mcp-bridge-client
```

## Quick Start

```typescript
import { MCPBridgeClient } from "@appsmithery/mcp-bridge-client";

const client = new MCPBridgeClient({
  gatewayUrl: "http://45.55.173.72:8000",
});

// List all tools
const tools = await client.listTools();
console.log(`Found ${tools.length} tools`);

// Search tools by keyword
const memoryTools = await client.searchTools("memory");
console.log(`Memory tools: ${memoryTools.length}`);

// Invoke a tool
const result = await client.invokeTool("memory/read", { key: "user-prefs" });
if (result.success) {
  console.log("Result:", result.result);
} else {
  console.error("Error:", result.error);
}
```

## Usage Examples

### Progressive Tool Loading

Automatically filter tools based on task description (80-90% token savings):

```typescript
// Only loads relevant tools for git operations
const gitTools = await client.getToolsForTask("commit my changes to git");

// Only loads database and filesystem tools
const dbTools = await client.getToolsForTask(
  "query users from postgres database"
);
```

### Server-Specific Tools

```typescript
// Get all GitHub tools
const githubTools = await client.getToolsByServer("github");

// List all available servers
const servers = await client.listServers();
console.log("Available servers:", servers);
```

### Tool Invocation

```typescript
// Memory operations
await client.invokeTool("memory/write", {
  key: "user-prefs",
  value: { theme: "dark", notifications: true },
});

const prefs = await client.invokeTool("memory/read", { key: "user-prefs" });

// File operations
await client.invokeTool("filesystem/write_file", {
  path: "./config.json",
  content: JSON.stringify({ version: "1.0" }),
});

// Git operations
await client.invokeTool("git/commit", {
  message: "feat: add new feature",
  files: ["src/index.ts"],
});

// GitHub operations
await client.invokeTool("github/create_issue", {
  repo: "owner/repo",
  title: "Bug report",
  body: "Description of the issue",
});

// Linear operations
await client.invokeTool("linear/create_issue", {
  title: "Implement feature X",
  description: "Detailed requirements",
  priority: 1,
});
```

### Configuration

```typescript
const client = new MCPBridgeClient({
  gatewayUrl: "http://45.55.173.72:8000", // MCP gateway endpoint
  timeout: 30000, // Request timeout (ms)
  enableCaching: true, // Enable tool catalog caching
  cacheTTL: 300000, // Cache TTL (ms, default 5min)
  progressiveLoading: true, // Enable keyword-based filtering
});

// Get current config
const config = client.getConfig();
console.log("Config:", config);

// Clear cache
client.clearCache();
```

### Health Checks

```typescript
const health = await client.health();
console.log("Gateway status:", health.status);
console.log("Available servers:", health.servers);
console.log("Total tools:", health.tools);
```

## API Reference

### `MCPBridgeClient`

Main client class for MCP gateway interaction.

#### Constructor

```typescript
new MCPBridgeClient(config?: MCPBridgeClientConfig)
```

#### Methods

- `listTools(forceRefresh?: boolean): Promise<MCPTool[]>` - List all tools
- `getToolsForTask(taskDescription: string): Promise<MCPTool[]>` - Progressive loading
- `searchTools(query: string): Promise<MCPTool[]>` - Search by keyword
- `getToolsByServer(serverName: string): Promise<MCPTool[]>` - Filter by server
- `listServers(): Promise<string[]>` - List all servers
- `invokeTool(toolName: string, args?: Record<string, any>): Promise<ToolInvocationResponse>` - Invoke tool
- `health(): Promise<{ status: string; servers: number; tools: number }>` - Health check
- `clearCache(): void` - Clear tool cache
- `getConfig(): Readonly<Required<MCPBridgeClientConfig>>` - Get configuration

### Types

```typescript
interface MCPTool {
  name: string;
  description: string;
  server: string;
  inputSchema?: Record<string, any>;
}

interface ToolInvocationResponse {
  success: boolean;
  result?: any;
  error?: string;
}

interface MCPBridgeClientConfig {
  gatewayUrl?: string;
  timeout?: number;
  enableCaching?: boolean;
  cacheTTL?: number;
  progressiveLoading?: boolean;
}
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

### Express.js API

```typescript
import express from "express";
import { MCPBridgeClient } from "@appsmithery/mcp-bridge-client";

const app = express();
const mcpClient = new MCPBridgeClient();

app.post("/api/tools/:toolName", async (req, res) => {
  const { toolName } = req.params;
  const result = await mcpClient.invokeTool(toolName, req.body);
  res.json(result);
});

app.get("/api/tools", async (req, res) => {
  const tools = await mcpClient.listTools();
  res.json({ tools });
});

app.listen(3000);
```

### CLI Tool

```typescript
import { MCPBridgeClient } from "@appsmithery/mcp-bridge-client";
import { Command } from "commander";

const program = new Command();
const client = new MCPBridgeClient();

program
  .command("list")
  .description("List all MCP tools")
  .action(async () => {
    const tools = await client.listTools();
    console.table(tools);
  });

program
  .command("invoke <tool> [args...]")
  .description("Invoke an MCP tool")
  .action(async (tool, args) => {
    const parsedArgs = JSON.parse(args[0] || "{}");
    const result = await client.invokeTool(tool, parsedArgs);
    console.log(result);
  });

program.parse();
```

### VS Code Extension

See [vscode-devtools-copilot](../../extensions/vscode-devtools-copilot) for complete extension using this client.

## Development

```bash
# Install dependencies
npm install

# Build
npm run build

# Watch mode
npm run watch

# Run tests
npm test

# Lint
npm run lint
```

## License

MIT

## Related

- [Python Client](../mcp-bridge-client-py) - Python equivalent
- [VS Code Extension](../../extensions/vscode-devtools-copilot) - VS Code integration
- [Dev-Tools Repository](https://github.com/Appsmithery/Dev-Tools) - Main repository
- [MCP Gateway](http://45.55.173.72:8000) - Live gateway endpoint
