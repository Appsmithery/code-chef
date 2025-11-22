# Dev-Tools Integration Implementation Plan

**Date**: November 20, 2025  
**Phase**: Post-Phase 5 (LangSmith + HITL Complete)  
**Goal**: Enable seamless Dev-Tools agent access from remote VS Code workspaces

---

## Overview

This plan details implementation of **two primary integration patterns**:

1. **Option 1**: VS Code Extension with Copilot Chat Participant (HTTP API)
2. **Option 2**: MCP Bridge Client Library (Tool-level integration)

Both options support **zero-clone workflows** - use Dev-Tools agents from any project without cloning the Dev-Tools repository.

---

## Option 1: VS Code Extension + Copilot Chat

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ VS Code Workspace (Remote Project)                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Copilot Chat Window                                   │  │
│  │  @devtools "Add auth to my Express API"              │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                          │
│  ┌────────────────▼─────────────────────────────────────┐  │
│  │ Dev-Tools Chat Participant                            │  │
│  │ - Intent parsing                                      │  │
│  │ - Context extraction (workspace files, git, issues)   │  │
│  │ - Session management                                  │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │ HTTP POST                                │
└───────────────────┼──────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ Dev-Tools Droplet (45.55.173.72)                            │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Orchestrator (:8001)                                  │  │
│  │  POST /orchestrate → Decompose task                   │  │
│  │  POST /chat → Multi-turn conversation                 │  │
│  │  GET /task/{id} → Check status                        │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                          │
│  ┌────────────────▼─────────────────────────────────────┐  │
│  │ Linear Workspace Notifier                             │  │
│  │  Posts approval request to PR-68                      │  │
│  │  @mentions user in Linear issue                       │  │
│  └────────────────┬─────────────────────────────────────┘  │
└───────────────────┼──────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ VS Code Linear Connect Extension                            │
│  - Watches PR-68 for new comments                           │
│  - Shows notification toast when approval needed            │
│  - Inline approve/reject buttons                            │
└─────────────────────────────────────────────────────────────┘
```

### Deliverables

#### 1. Extension Scaffold (`extensions/vscode-devtools-copilot/`)

```
vscode-devtools-copilot/
├── package.json                 # Extension manifest
├── tsconfig.json               # TypeScript config
├── src/
│   ├── extension.ts            # Entry point, activate()
│   ├── chatParticipant.ts      # @devtools handler
│   ├── orchestratorClient.ts   # HTTP API wrapper
│   ├── contextExtractor.ts     # Workspace context gathering
│   ├── sessionManager.ts       # Multi-turn conversation state
│   ├── linearWatcher.ts        # Real-time approval notifications
│   └── commands/
│       ├── orchestrate.ts      # Command: devtools.orchestrate
│       ├── checkStatus.ts      # Command: devtools.checkStatus
│       └── approveTask.ts      # Command: devtools.approve
├── prompts/
│   ├── system.md               # Chat participant system prompt
│   ├── task-decomposition.md   # Orchestrator guidance
│   └── error-recovery.md       # Failure handling
├── .vscodeignore
└── README.md
```

**Key Files**:

**`package.json`**:

```json
{
  "name": "vscode-devtools-copilot",
  "displayName": "Dev-Tools Agent Integration",
  "description": "Copilot Chat participant for Dev-Tools orchestrator",
  "version": "0.1.0",
  "publisher": "appsmithery",
  "repository": "https://github.com/Appsmithery/Dev-Tools",
  "engines": { "vscode": "^1.85.0" },
  "categories": ["AI", "Other"],
  "activationEvents": ["onStartupFinished"],
  "contributes": {
    "chatParticipants": [
      {
        "id": "devtools",
        "name": "Dev-Tools Orchestrator",
        "description": "Submit tasks to Dev-Tools agent platform",
        "isSticky": true
      }
    ],
    "commands": [
      {
        "command": "devtools.orchestrate",
        "title": "Submit Task to Orchestrator",
        "category": "Dev-Tools"
      },
      {
        "command": "devtools.checkStatus",
        "title": "Check Task Status",
        "category": "Dev-Tools"
      },
      {
        "command": "devtools.configure",
        "title": "Configure Orchestrator URL",
        "category": "Dev-Tools"
      }
    ],
    "configuration": {
      "title": "Dev-Tools",
      "properties": {
        "devtools.orchestratorUrl": {
          "type": "string",
          "default": "http://45.55.173.72:8001",
          "description": "Dev-Tools orchestrator endpoint"
        },
        "devtools.mcpGatewayUrl": {
          "type": "string",
          "default": "http://45.55.173.72:8000",
          "description": "MCP gateway endpoint"
        },
        "devtools.linearHubIssue": {
          "type": "string",
          "default": "PR-68",
          "description": "Linear issue for approval notifications"
        },
        "devtools.autoApproveThreshold": {
          "type": "string",
          "enum": ["low", "medium", "high", "critical"],
          "default": "low",
          "description": "Auto-approve tasks at or below this risk level"
        }
      }
    }
  },
  "dependencies": {
    "@vscode/chat-extension-utils": "^1.0.0",
    "axios": "^1.6.0",
    "eventsource": "^2.0.2"
  },
  "devDependencies": {
    "@types/vscode": "^1.85.0",
    "@types/node": "^20.0.0",
    "typescript": "^5.3.0"
  }
}
```

**`src/chatParticipant.ts`**:

```typescript
import * as vscode from "vscode";
import { OrchestratorClient } from "./orchestratorClient";
import { ContextExtractor } from "./contextExtractor";
import { SessionManager } from "./sessionManager";

export class DevToolsChatParticipant implements vscode.ChatParticipant {
  private client: OrchestratorClient;
  private contextExtractor: ContextExtractor;
  private sessionManager: SessionManager;

  constructor() {
    const config = vscode.workspace.getConfiguration("devtools");
    this.client = new OrchestratorClient(config.get("orchestratorUrl")!);
    this.contextExtractor = new ContextExtractor();
    this.sessionManager = new SessionManager();
  }

  async handleChatRequest(
    request: vscode.ChatRequest,
    context: vscode.ChatContext,
    stream: vscode.ChatResponseStream,
    token: vscode.CancellationToken
  ): Promise<vscode.ChatResult> {
    const userMessage = request.prompt;
    stream.progress("Analyzing request...");

    // Extract workspace context
    const workspaceContext = await this.contextExtractor.extract();

    // Check for existing session
    const sessionId = this.sessionManager.getOrCreateSession(context);

    try {
      // Submit to orchestrator
      stream.progress("Submitting to Dev-Tools orchestrator...");

      const response = await this.client.orchestrate({
        description: userMessage,
        priority: "medium",
        project_context: workspaceContext,
        session_id: sessionId,
      });

      // Stream response
      stream.markdown(`## Task Submitted\n\n`);
      stream.markdown(`**Task ID**: \`${response.task_id}\`\n\n`);
      stream.markdown(`**Subtasks** (${response.subtasks.length}):\n\n`);

      for (const subtask of response.subtasks) {
        stream.markdown(
          `- **${subtask.agent_type}**: ${subtask.description}\n`
        );
      }

      // Approval notification
      if (response.approval_request_id) {
        stream.markdown(`\n\n⚠️ **Approval Required**\n\n`);
        stream.markdown(
          `Task requires approval. Check Linear issue [${this.getLinearHubIssue()}](https://linear.app/project-roadmaps/issue/${this.getLinearHubIssue()})\n\n`
        );

        stream.button({
          command: "devtools.approveTask",
          title: "Approve Task",
          arguments: [response.task_id, response.approval_request_id],
        });
      }

      // Return with follow-up options
      return {
        metadata: {
          taskId: response.task_id,
          sessionId: sessionId,
        },
      };
    } catch (error: any) {
      stream.markdown(`\n\n❌ **Error**: ${error.message}\n\n`);
      return { errorDetails: { message: error.message } };
    }
  }

  private getLinearHubIssue(): string {
    return vscode.workspace
      .getConfiguration("devtools")
      .get("linearHubIssue", "PR-68");
  }
}
```

**`src/orchestratorClient.ts`**:

```typescript
import axios, { AxiosInstance } from "axios";

export interface TaskRequest {
  description: string;
  priority: "low" | "medium" | "high" | "critical";
  project_context?: Record<string, any>;
  workspace_config?: Record<string, any>;
  session_id?: string;
}

export interface SubTask {
  id: string;
  agent_type: string;
  description: string;
  status: string;
  dependencies?: string[];
}

export interface TaskResponse {
  task_id: string;
  subtasks: SubTask[];
  approval_request_id?: string;
  routing_plan: {
    execution_order: string[];
    estimated_duration_minutes: number;
  };
}

export class OrchestratorClient {
  private client: AxiosInstance;

  constructor(baseUrl: string) {
    this.client = axios.create({
      baseURL: baseUrl,
      timeout: 30000,
      headers: { "Content-Type": "application/json" },
    });
  }

  async orchestrate(request: TaskRequest): Promise<TaskResponse> {
    const response = await this.client.post("/orchestrate", request);
    return response.data;
  }

  async checkStatus(taskId: string): Promise<any> {
    const response = await this.client.get(`/task/${taskId}`);
    return response.data;
  }

  async chat(message: string, sessionId: string): Promise<any> {
    const response = await this.client.post("/chat", {
      message,
      session_id: sessionId,
    });
    return response.data;
  }

  async health(): Promise<{ status: string }> {
    const response = await this.client.get("/health");
    return response.data;
  }
}
```

**`src/contextExtractor.ts`**:

```typescript
import * as vscode from "vscode";
import * as fs from "fs/promises";
import * as path from "path";

export class ContextExtractor {
  async extract(): Promise<Record<string, any>> {
    const workspace = vscode.workspace.workspaceFolders?.[0];
    if (!workspace) {
      return {};
    }

    return {
      workspace_name: workspace.name,
      workspace_path: workspace.uri.fsPath,
      git_branch: await this.getGitBranch(workspace.uri.fsPath),
      open_files: this.getOpenFiles(),
      project_type: await this.detectProjectType(workspace.uri.fsPath),
      active_editor: this.getActiveEditorContext(),
    };
  }

  private async getGitBranch(workspacePath: string): Promise<string | null> {
    try {
      const gitHeadPath = path.join(workspacePath, ".git", "HEAD");
      const content = await fs.readFile(gitHeadPath, "utf-8");
      const match = content.match(/ref: refs\/heads\/(.+)/);
      return match ? match[1].trim() : null;
    } catch {
      return null;
    }
  }

  private getOpenFiles(): string[] {
    return vscode.workspace.textDocuments
      .filter((doc) => !doc.isUntitled && doc.uri.scheme === "file")
      .map((doc) => vscode.workspace.asRelativePath(doc.uri));
  }

  private async detectProjectType(workspacePath: string): Promise<string> {
    const indicators = [
      { file: "package.json", type: "node" },
      { file: "requirements.txt", type: "python" },
      { file: "Cargo.toml", type: "rust" },
      { file: "go.mod", type: "go" },
      { file: "pom.xml", type: "java" },
    ];

    for (const indicator of indicators) {
      try {
        await fs.access(path.join(workspacePath, indicator.file));
        return indicator.type;
      } catch {}
    }

    return "unknown";
  }

  private getActiveEditorContext(): any {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return null;

    return {
      file: vscode.workspace.asRelativePath(editor.document.uri),
      language: editor.document.languageId,
      line: editor.selection.active.line,
      selection: editor.document.getText(editor.selection),
    };
  }
}
```

**`src/linearWatcher.ts`**:

```typescript
import * as vscode from "vscode";
import EventSource from "eventsource";

export class LinearWatcher {
  private eventSource?: EventSource;
  private statusBarItem: vscode.StatusBarItem;

  constructor() {
    this.statusBarItem = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Right,
      100
    );
    this.statusBarItem.text = "$(check) Dev-Tools";
    this.statusBarItem.show();
  }

  start(linearHubIssue: string) {
    // Use Linear Connect extension API if available
    const linearExtension = vscode.extensions.getExtension(
      "linear.linear-vscode"
    );

    if (linearExtension) {
      this.watchViaLinearExtension(linearHubIssue);
    } else {
      // Fallback: poll orchestrator for pending approvals
      this.pollForApprovals();
    }
  }

  private async watchViaLinearExtension(issueId: string) {
    const linearExtension = vscode.extensions.getExtension(
      "linear.linear-vscode"
    );
    if (!linearExtension?.isActive) {
      await linearExtension?.activate();
    }

    // Subscribe to Linear issue updates
    const linear = linearExtension?.exports;
    if (linear?.subscribeToIssue) {
      linear.subscribeToIssue(issueId, (update: any) => {
        if (update.type === "comment" && update.body.includes("@devtools")) {
          this.showApprovalNotification(update);
        }
      });
    }
  }

  private pollForApprovals() {
    setInterval(async () => {
      const config = vscode.workspace.getConfiguration("devtools");
      const orchestratorUrl = config.get("orchestratorUrl");

      try {
        const response = await fetch(`${orchestratorUrl}/approvals/pending`);
        const approvals = await response.json();

        if (approvals.length > 0) {
          this.statusBarItem.text = `$(alert) ${approvals.length} approval(s) pending`;
          this.statusBarItem.command = "devtools.showApprovals";
        } else {
          this.statusBarItem.text = "$(check) Dev-Tools";
        }
      } catch (error) {
        console.error("Failed to poll approvals:", error);
      }
    }, 30000); // Poll every 30 seconds
  }

  private showApprovalNotification(update: any) {
    vscode.window
      .showInformationMessage(
        `Dev-Tools approval needed: ${update.title}`,
        "View in Linear",
        "Approve",
        "Reject"
      )
      .then((selection) => {
        if (selection === "View in Linear") {
          vscode.env.openExternal(vscode.Uri.parse(update.url));
        } else if (selection === "Approve" || selection === "Reject") {
          vscode.commands.executeCommand(
            "devtools.respondToApproval",
            update.taskId,
            selection.toLowerCase()
          );
        }
      });
  }

  dispose() {
    this.eventSource?.close();
    this.statusBarItem.dispose();
  }
}
```

#### 2. Prompt Files (`.github/copilot-prompts/`)

**`.github/copilot-prompts/devtools-participant.md`**:

```markdown
# Dev-Tools Chat Participant System Prompt

You are the **Dev-Tools Orchestrator Assistant**, integrated into VS Code via Copilot Chat.

## Your Role

When users message you with `@devtools`, you:

1. Parse their request to understand the development task
2. Extract relevant workspace context (files, git branch, project type)
3. Submit the task to the Dev-Tools orchestrator at `http://45.55.173.72:8001/orchestrate`
4. Display the decomposed subtasks and routing plan
5. Notify users about approval requirements and provide action buttons

## Task Decomposition

The orchestrator will break down requests into subtasks assigned to specialized agents:

- **feature-dev**: Code generation, scaffolding, test creation
- **code-review**: Quality analysis, security scanning, standards enforcement
- **infrastructure**: IaC authoring, deployment automation, container management
- **cicd**: Pipeline generation, workflow execution, artifact management
- **documentation**: Doc generation, API documentation, diagram synthesis

## Approval Workflow

High-risk tasks require human approval:

1. Task is submitted with risk assessment
2. Approval request posted to Linear issue PR-68
3. User receives notification (via Linear Connect extension or polling)
4. User approves/rejects via inline button
5. Orchestrator proceeds or cancels based on response

## Context Extraction

Always include:

- Workspace name and path
- Git branch
- Open files
- Project type (node, python, rust, go, java)
- Active editor file and selection

## Error Handling

If orchestrator is unreachable:

1. Check health endpoint first
2. Suggest running `devtools.configure` to update URL
3. Provide fallback: manual curl command for user to run

## Example Interactions

**User**: `@devtools Add JWT authentication to my Express API`

**Response**:
```

## Task Submitted

**Task ID**: `a1b2c3d4-e5f6-7890-abcd-ef1234567890`

**Subtasks** (4):

- **feature-dev**: Implement JWT middleware for Express
- **feature-dev**: Add login/logout endpoints with token generation
- **code-review**: Security audit of authentication implementation
- **documentation**: Generate API docs for auth endpoints

⚠️ **Approval Required**

Task requires approval (risk level: medium). Check Linear issue [PR-68](https://linear.app/project-roadmaps/issue/PR-68)

[Approve Task]

```

## Follow-up Commands

- `devtools.checkStatus <task_id>`: Check task execution status
- `devtools.approveTask <task_id> <approval_id>`: Approve pending task
- `devtools.configure`: Update orchestrator URL
```

#### 3. Taskfile for Extension Development (`extensions/vscode-devtools-copilot/Taskfile.yml`)

```yaml
version: "3"

vars:
  EXTENSION_NAME: vscode-devtools-copilot
  VSCE_TOKEN: "{{.VSCE_TOKEN}}"

tasks:
  install:
    desc: Install extension dependencies
    cmds:
      - npm install

  compile:
    desc: Compile TypeScript
    cmds:
      - npm run compile

  watch:
    desc: Watch for changes and recompile
    cmds:
      - npm run watch

  test:
    desc: Run extension tests
    cmds:
      - npm run test

  package:
    desc: Package extension as VSIX
    cmds:
      - npx vsce package
    deps: [compile]

  publish:
    desc: Publish to VS Code Marketplace
    cmds:
      - npx vsce publish -p {{.VSCE_TOKEN}}
    deps: [package]

  install-local:
    desc: Install extension locally for testing
    cmds:
      - code --install-extension {{.EXTENSION_NAME}}-*.vsix
    deps: [package]

  dev:
    desc: Run extension in debug mode (opens Extension Development Host)
    cmds:
      - code --extensionDevelopmentPath=$(pwd)

  clean:
    desc: Clean build artifacts
    cmds:
      - rm -rf out/
      - rm -f *.vsix
```

---

## Option 2: MCP Bridge Client Library

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Remote Project Workspace                                     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Copilot Chat (Native)                                 │  │
│  │  "Use linear-issues to create a bug report"          │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │ Tool Discovery                           │
│  ┌────────────────▼─────────────────────────────────────┐  │
│  │ MCP Bridge Client (NPM/PyPI package)                  │  │
│  │  - Tool catalog cache                                 │  │
│  │  - Progressive loader integration                     │  │
│  │  - Request/response translation                       │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │ HTTP + SSE                               │
└───────────────────┼──────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│ Dev-Tools Droplet (45.55.173.72)                            │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ MCP Gateway (:8000)                                   │  │
│  │  GET /tools → List available tools (150+)            │  │
│  │  POST /tools/invoke → Execute tool                    │  │
│  │  GET /tools/progressive → Task-specific tools         │  │
│  └────────────────┬─────────────────────────────────────┘  │
│                   │                                          │
│  ┌────────────────▼─────────────────────────────────────┐  │
│  │ 18 MCP Servers                                        │  │
│  │  memory, context7, notion, linear, terraform, etc.   │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Deliverables

#### 1. NPM Package (`packages/mcp-bridge-client/`)

```
mcp-bridge-client/
├── package.json
├── tsconfig.json
├── src/
│   ├── index.ts                # Main export
│   ├── MCPBridgeClient.ts      # Core client
│   ├── ToolCatalog.ts          # Tool discovery & caching
│   ├── ProgressiveLoader.ts    # Progressive disclosure
│   ├── types.ts                # TypeScript definitions
│   └── utils/
│       ├── retry.ts            # Retry logic
│       └── cache.ts            # Response caching
├── tests/
│   ├── client.test.ts
│   └── integration.test.ts
└── README.md
```

**`package.json`**:

```json
{
  "name": "@appsmithery/mcp-bridge-client",
  "version": "0.1.0",
  "description": "MCP Bridge client for Dev-Tools gateway",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "repository": "https://github.com/Appsmithery/Dev-Tools",
  "keywords": ["mcp", "dev-tools", "llm", "copilot"],
  "scripts": {
    "build": "tsc",
    "test": "jest",
    "prepublishOnly": "npm run build"
  },
  "dependencies": {
    "axios": "^1.6.0",
    "eventsource": "^2.0.2"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "typescript": "^5.3.0",
    "jest": "^29.7.0"
  }
}
```

**`src/MCPBridgeClient.ts`**:

```typescript
import axios, { AxiosInstance } from "axios";
import EventSource from "eventsource";

export interface MCPTool {
  server: string;
  name: string;
  description: string;
  inputSchema: any;
}

export interface ToolInvocation {
  server: string;
  tool: string;
  arguments: Record<string, any>;
}

export interface ToolResult {
  success: boolean;
  result?: any;
  error?: string;
}

export class MCPBridgeClient {
  private client: AxiosInstance;
  private toolCache: Map<string, MCPTool[]> = new Map();
  private cacheExpiry: number = 300000; // 5 minutes

  constructor(
    private gatewayUrl: string,
    private options: {
      authToken?: string;
      cacheTtl?: number;
      retryAttempts?: number;
    } = {}
  ) {
    this.client = axios.create({
      baseURL: gatewayUrl,
      timeout: 30000,
      headers: {
        "Content-Type": "application/json",
        ...(options.authToken && {
          Authorization: `Bearer ${options.authToken}`,
        }),
      },
    });

    if (options.cacheTtl) {
      this.cacheExpiry = options.cacheTtl;
    }
  }

  /**
   * List all available MCP tools
   */
  async listTools(): Promise<MCPTool[]> {
    const cacheKey = "all_tools";
    const cached = this.getFromCache(cacheKey);
    if (cached) return cached;

    const response = await this.client.get("/tools");
    const tools = response.data.tools;

    this.setCache(cacheKey, tools);
    return tools;
  }

  /**
   * Get tools for a specific task (progressive disclosure)
   */
  async getToolsForTask(taskDescription: string): Promise<MCPTool[]> {
    const response = await this.client.post("/tools/progressive", {
      task_description: taskDescription,
      strategy: "progressive",
    });

    return response.data.tools;
  }

  /**
   * Invoke a specific MCP tool
   */
  async invokeTool(invocation: ToolInvocation): Promise<ToolResult> {
    try {
      const response = await this.client.post("/tools/invoke", {
        server: invocation.server,
        tool: invocation.tool,
        arguments: invocation.arguments,
      });

      return {
        success: true,
        result: response.data.result,
      };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || error.message,
      };
    }
  }

  /**
   * Search for tools by keyword
   */
  async searchTools(query: string): Promise<MCPTool[]> {
    const allTools = await this.listTools();
    const lowerQuery = query.toLowerCase();

    return allTools.filter(
      (tool) =>
        tool.name.toLowerCase().includes(lowerQuery) ||
        tool.description.toLowerCase().includes(lowerQuery) ||
        tool.server.toLowerCase().includes(lowerQuery)
    );
  }

  /**
   * Get tools by server name
   */
  async getToolsByServer(serverName: string): Promise<MCPTool[]> {
    const allTools = await this.listTools();
    return allTools.filter((tool) => tool.server === serverName);
  }

  /**
   * Check gateway health
   */
  async health(): Promise<{ status: string; mcp_gateway: string }> {
    const response = await this.client.get("/health");
    return response.data;
  }

  // Cache management
  private getFromCache(key: string): MCPTool[] | null {
    const cached = this.toolCache.get(key);
    if (!cached) return null;

    // Check expiry
    const now = Date.now();
    if (now - (cached as any)._timestamp > this.cacheExpiry) {
      this.toolCache.delete(key);
      return null;
    }

    return cached;
  }

  private setCache(key: string, tools: MCPTool[]): void {
    (tools as any)._timestamp = Date.now();
    this.toolCache.set(key, tools);
  }

  /**
   * Clear tool cache
   */
  clearCache(): void {
    this.toolCache.clear();
  }
}
```

#### 2. Python Package (`packages/mcp-bridge-client-py/`)

```
mcp-bridge-client-py/
├── pyproject.toml
├── setup.py
├── mcp_bridge_client/
│   ├── __init__.py
│   ├── client.py
│   ├── tool_catalog.py
│   ├── progressive_loader.py
│   └── types.py
├── tests/
│   ├── test_client.py
│   └── test_integration.py
└── README.md
```

**`mcp_bridge_client/client.py`**:

```python
import httpx
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class MCPTool:
    server: str
    name: str
    description: str
    input_schema: Dict[str, Any]

@dataclass
class ToolInvocation:
    server: str
    tool: str
    arguments: Dict[str, Any]

@dataclass
class ToolResult:
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None

class MCPBridgeClient:
    """MCP Bridge client for Dev-Tools gateway"""

    def __init__(
        self,
        gateway_url: str,
        auth_token: Optional[str] = None,
        cache_ttl: int = 300,
        timeout: int = 30
    ):
        self.gateway_url = gateway_url.rstrip('/')
        self.timeout = timeout
        self.cache_ttl = timedelta(seconds=cache_ttl)
        self._tool_cache: Dict[str, tuple[List[MCPTool], datetime]] = {}

        headers = {'Content-Type': 'application/json'}
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'

        self.client = httpx.Client(
            base_url=gateway_url,
            timeout=timeout,
            headers=headers
        )

    def list_tools(self) -> List[MCPTool]:
        """List all available MCP tools"""
        cache_key = 'all_tools'
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        response = self.client.get('/tools')
        response.raise_for_status()

        tools = [
            MCPTool(**tool_data)
            for tool_data in response.json()['tools']
        ]

        self._set_cache(cache_key, tools)
        return tools

    def get_tools_for_task(self, task_description: str) -> List[MCPTool]:
        """Get tools for a specific task (progressive disclosure)"""
        response = self.client.post('/tools/progressive', json={
            'task_description': task_description,
            'strategy': 'progressive'
        })
        response.raise_for_status()

        return [
            MCPTool(**tool_data)
            for tool_data in response.json()['tools']
        ]

    def invoke_tool(self, invocation: ToolInvocation) -> ToolResult:
        """Invoke a specific MCP tool"""
        try:
            response = self.client.post('/tools/invoke', json={
                'server': invocation.server,
                'tool': invocation.tool,
                'arguments': invocation.arguments
            })
            response.raise_for_status()

            return ToolResult(
                success=True,
                result=response.json()['result']
            )
        except httpx.HTTPError as e:
            return ToolResult(
                success=False,
                error=str(e)
            )

    def search_tools(self, query: str) -> List[MCPTool]:
        """Search for tools by keyword"""
        all_tools = self.list_tools()
        query_lower = query.lower()

        return [
            tool for tool in all_tools
            if query_lower in tool.name.lower()
            or query_lower in tool.description.lower()
            or query_lower in tool.server.lower()
        ]

    def get_tools_by_server(self, server_name: str) -> List[MCPTool]:
        """Get tools by server name"""
        all_tools = self.list_tools()
        return [tool for tool in all_tools if tool.server == server_name]

    def health(self) -> Dict[str, str]:
        """Check gateway health"""
        response = self.client.get('/health')
        response.raise_for_status()
        return response.json()

    # Cache management
    def _get_from_cache(self, key: str) -> Optional[List[MCPTool]]:
        if key not in self._tool_cache:
            return None

        tools, timestamp = self._tool_cache[key]
        if datetime.now() - timestamp > self.cache_ttl:
            del self._tool_cache[key]
            return None

        return tools

    def _set_cache(self, key: str, tools: List[MCPTool]) -> None:
        self._tool_cache[key] = (tools, datetime.now())

    def clear_cache(self) -> None:
        """Clear tool cache"""
        self._tool_cache.clear()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()
```

#### 3. Project Templates (`.github/project-templates/`)

**`.github/project-templates/node-with-mcp/.vscode/settings.json`**:

```json
{
  "devtools.orchestratorUrl": "http://45.55.173.72:8001",
  "devtools.mcpGatewayUrl": "http://45.55.173.72:8000",
  "devtools.linearHubIssue": "PR-68",
  "devtools.autoApproveThreshold": "low",

  "mcp.servers": {
    "dev-tools-gateway": {
      "command": "npx",
      "args": [
        "@appsmithery/mcp-bridge-client",
        "--gateway",
        "${config:devtools.mcpGatewayUrl}"
      ]
    }
  }
}
```

**`.github/project-templates/node-with-mcp/package.json`**:

```json
{
  "name": "my-project",
  "devDependencies": {
    "@appsmithery/mcp-bridge-client": "^0.1.0"
  },
  "scripts": {
    "mcp:list-tools": "mcp-bridge list-tools",
    "mcp:health": "mcp-bridge health",
    "devtools:orchestrate": "node scripts/devtools-orchestrate.js"
  }
}
```

**`.github/project-templates/node-with-mcp/scripts/devtools-orchestrate.js`**:

```javascript
#!/usr/bin/env node
const { MCPBridgeClient } = require("@appsmithery/mcp-bridge-client");
const readline = require("readline");

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

const client = new MCPBridgeClient("http://45.55.173.72:8000");

rl.question("Describe your development task: ", async (task) => {
  console.log("\nFinding relevant tools...");

  const tools = await client.getToolsForTask(task);
  console.log(`\nFound ${tools.length} relevant tools:\n`);

  tools.forEach((tool) => {
    console.log(`  - ${tool.server}/${tool.name}: ${tool.description}`);
  });

  rl.close();
  process.exit(0);
});
```

**`.github/project-templates/python-with-mcp/pyproject.toml`**:

```toml
[project]
name = "my-project"
dependencies = []

[project.optional-dependencies]
dev = [
    "mcp-bridge-client>=0.1.0"
]

[tool.mcp]
gateway_url = "http://45.55.173.72:8000"

[tool.devtools]
orchestrator_url = "http://45.55.173.72:8001"
linear_hub_issue = "PR-68"
```

---

## GitHub Package Distribution

### 1. GitHub Packages Setup

**`.github/workflows/publish-packages.yml`**:

```yaml
name: Publish Packages

on:
  push:
    tags:
      - "v*"

jobs:
  publish-npm:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          registry-url: "https://npm.pkg.github.com"
          scope: "@appsmithery"

      - name: Build MCP Bridge Client
        run: |
          cd packages/mcp-bridge-client
          npm install
          npm run build

      - name: Publish to GitHub Packages
        run: |
          cd packages/mcp-bridge-client
          npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  publish-pypi:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Build Python package
        run: |
          cd packages/mcp-bridge-client-py
          pip install build twine
          python -m build

      - name: Publish to PyPI
        run: |
          cd packages/mcp-bridge-client-py
          twine upload dist/*
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_TOKEN }}

  publish-extension:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Build Extension
        run: |
          cd extensions/vscode-devtools-copilot
          npm install
          npm run compile

      - name: Package Extension
        run: |
          cd extensions/vscode-devtools-copilot
          npx vsce package

      - name: Publish to VS Code Marketplace
        run: |
          cd extensions/vscode-devtools-copilot
          npx vsce publish -p ${{ secrets.VSCE_TOKEN }}
```

### 2. Template Repository

Create `github.com/Appsmithery/devtools-project-template`:

```
devtools-project-template/
├── .github/
│   ├── copilot-prompts/
│   │   └── devtools-participant.md
│   └── workflows/
│       ├── devtools-review.yml
│       └── devtools-deploy.yml
├── .vscode/
│   ├── settings.json           # Pre-configured MCP bridge
│   ├── extensions.json          # Recommended extensions
│   └── tasks.json               # Dev-Tools task shortcuts
├── scripts/
│   ├── setup-devtools.sh        # One-time setup script
│   └── orchestrate.js           # CLI orchestration helper
├── Taskfile.yml                 # Dev-Tools tasks
├── .env.template                # Environment template
└── README.md                    # Setup instructions
```

**`scripts/setup-devtools.sh`**:

```bash
#!/bin/bash
set -e

echo "🚀 Setting up Dev-Tools integration..."

# Detect project type
if [ -f "package.json" ]; then
  echo "📦 Detected Node.js project"
  npm install --save-dev @appsmithery/mcp-bridge-client

elif [ -f "pyproject.toml" ] || [ -f "requirements.txt" ]; then
  echo "🐍 Detected Python project"
  pip install mcp-bridge-client

else
  echo "❓ Unknown project type - manual setup required"
  exit 1
fi

# Configure MCP gateway
cat > .vscode/settings.json <<EOF
{
  "devtools.orchestratorUrl": "http://45.55.173.72:8001",
  "devtools.mcpGatewayUrl": "http://45.55.173.72:8000",
  "devtools.linearHubIssue": "PR-68",
  "mcp.servers": {
    "dev-tools-gateway": {
      "command": "mcp-bridge",
      "args": ["--gateway", "\${config:devtools.mcpGatewayUrl}"]
    }
  }
}
EOF

# Test connection
echo "🔌 Testing connection to Dev-Tools..."
curl -s http://45.55.173.72:8001/health | jq .

echo "✅ Setup complete! Install the Dev-Tools Copilot extension from VS Code marketplace."
echo "   Extension ID: appsmithery.vscode-devtools-copilot"
```

**`Taskfile.yml`**:

```yaml
version: "3"

vars:
  ORCHESTRATOR_URL: http://45.55.173.72:8001
  MCP_GATEWAY_URL: http://45.55.173.72:8000

tasks:
  setup:
    desc: Setup Dev-Tools integration
    cmds:
      - ./scripts/setup-devtools.sh

  health:
    desc: Check Dev-Tools health
    cmds:
      - curl -s {{.ORCHESTRATOR_URL}}/health | jq .
      - curl -s {{.MCP_GATEWAY_URL}}/health | jq .

  list-tools:
    desc: List available MCP tools
    cmds:
      - |
        node -e "
        const { MCPBridgeClient } = require('@appsmithery/mcp-bridge-client');
        const client = new MCPBridgeClient('{{.MCP_GATEWAY_URL}}');
        client.listTools().then(tools => {
          console.log(\`Found \${tools.length} tools:\`);
          tools.forEach(t => console.log(\`  - \${t.server}/\${t.name}\`));
        });
        "

  orchestrate:
    desc: Submit task to orchestrator
    cmds:
      - |
        read -p "Task description: " TASK
        curl -X POST {{.ORCHESTRATOR_URL}}/orchestrate \
          -H "Content-Type: application/json" \
          -d "{\"description\": \"$TASK\", \"priority\": \"medium\"}" | jq .

  check-status:
    desc: Check task status
    cmds:
      - |
        read -p "Task ID: " TASK_ID
        curl -s {{.ORCHESTRATOR_URL}}/task/$TASK_ID | jq .
```

---

## Installation Documentation

### Quick Start Guide

**`support/docs/INTEGRATION_QUICKSTART.md`**:

````markdown
# Dev-Tools Integration Quick Start

## Option 1: Copilot Chat Extension (5 minutes)

1. **Install Extension**
   ```bash
   code --install-extension appsmithery.vscode-devtools-copilot
   ```
````

2. **Configure Orchestrator**
   Press `F1` → "Dev-Tools: Configure" → Enter `http://45.55.173.72:8001`

3. **Start Using**
   Open Copilot Chat → Type `@devtools Add auth to my API`

## Option 2: MCP Bridge (10 minutes)

### Node.js Project

```bash
# Install package
npm install --save-dev @appsmithery/mcp-bridge-client

# Configure VS Code
cat > .vscode/settings.json <<EOF
{
  "mcp.servers": {
    "dev-tools": {
      "command": "npx",
      "args": ["@appsmithery/mcp-bridge-client", "--gateway", "http://45.55.173.72:8000"]
    }
  }
}
EOF

# Test connection
npx @appsmithery/mcp-bridge-client health
```

### Python Project

```bash
# Install package
pip install mcp-bridge-client

# Configure
cat > .vscode/settings.json <<EOF
{
  "mcp.servers": {
    "dev-tools": {
      "command": "python",
      "args": ["-m", "mcp_bridge_client", "--gateway", "http://45.55.173.72:8000"]
    }
  }
}
EOF

# Test connection
python -m mcp_bridge_client health
```

## Using Template Repository

```bash
# Create new project from template
gh repo create my-project --template Appsmithery/devtools-project-template

# Clone and setup
git clone https://github.com/yourusername/my-project
cd my-project
./scripts/setup-devtools.sh
```

## Verification

Check that everything works:

```bash
# Health check
curl http://45.55.173.72:8001/health

# List MCP tools
curl http://45.55.173.72:8000/tools | jq '.tools | length'

# Submit test task
curl -X POST http://45.55.173.72:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"description": "Test task", "priority": "low"}' | jq .
```

## Troubleshooting

**Connection refused**:

- Check firewall allows outbound connections to 45.55.173.72
- Verify services are running: `ssh root@45.55.173.72 "docker ps"`

**No tools appearing**:

- Clear cache: Open command palette → "Dev-Tools: Clear Cache"
- Restart VS Code
- Check MCP gateway health: `curl http://45.55.173.72:8000/health`

**Approval notifications not working**:

- Install Linear Connect extension: `code --install-extension linear.linear-vscode`
- Configure Linear API token in extension settings
- Subscribe to PR-68 issue

## Next Steps

- Read full documentation: `support/docs/INTEGRATION_IMPLEMENTATION_PLAN.md`
- Explore example projects: `examples/`
- Join Discord for support: https://discord.gg/appsmithery

```

---

## Summary

This implementation plan provides:

1. **VS Code Extension**: Full-featured Copilot Chat participant with Linear Connect integration
2. **MCP Bridge Client**: NPM + PyPI packages for tool-level integration
3. **GitHub Packages**: Automated publishing pipeline
4. **Template Repository**: Copy-paste project setup
5. **Reusable Scripts**: Taskfile, setup scripts, CLI helpers
6. **Documentation**: Quick start, troubleshooting, API reference

**Next Actions**:
1. Build VS Code extension scaffold
2. Implement MCP bridge client (TypeScript + Python)
3. Create template repository
4. Test integration with sample project
5. Publish to VS Code Marketplace + NPM/PyPI

**Estimated Timeline**: 2-3 weeks for full implementation
```
