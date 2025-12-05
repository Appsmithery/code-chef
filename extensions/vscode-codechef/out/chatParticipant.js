"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.CodeChefChatParticipant = void 0;
const vscode = __importStar(require("vscode"));
const contextExtractor_1 = require("./contextExtractor");
const orchestratorClient_1 = require("./orchestratorClient");
const sessionManager_1 = require("./sessionManager");
const settings_1 = require("./settings");
class CodeChefChatParticipant {
    constructor(context) {
        this.context = context;
        const config = vscode.workspace.getConfiguration('codechef');
        this.client = new orchestratorClient_1.OrchestratorClient({
            baseUrl: config.get('orchestratorUrl'),
            apiKey: config.get('apiKey') || undefined
        });
        this.contextExtractor = new contextExtractor_1.ContextExtractor();
        this.sessionManager = new sessionManager_1.SessionManager(context);
        // Listen for configuration changes to update API key
        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('codechef.apiKey')) {
                const newApiKey = vscode.workspace.getConfiguration('codechef').get('apiKey');
                this.client.setApiKey(newApiKey || undefined);
            }
        });
    }
    async handleChatRequest(request, context, stream, token) {
        const userMessage = request.prompt;
        // Handle commands
        if (request.command) {
            return await this.handleCommand(request.command, userMessage, stream, token);
        }
        stream.progress('Analyzing workspace context...');
        try {
            // Extract workspace context
            const workspaceContext = await this.contextExtractor.extract();
            // Get or create session
            const sessionId = this.sessionManager.getOrCreateSession(context);
            stream.progress('Submitting to code/chef orchestrator...');
            // Submit to orchestrator with token optimization settings
            const response = await this.client.orchestrate({
                description: userMessage,
                priority: 'medium',
                project_context: workspaceContext,
                workspace_config: (0, settings_1.buildWorkspaceConfig)(),
                session_id: sessionId
            });
            this.lastTaskId = response.task_id;
            // Cache Linear project ID if returned (for new projects)
            if (response.linear_project?.id && !workspaceContext.linear_project_id) {
                await this.contextExtractor.saveLinearProjectId(response.linear_project.id);
                stream.markdown(`\n✨ Created Linear project: **${response.linear_project.name}**\n`);
                if (response.linear_project.url) {
                    stream.markdown(`📋 [View in Linear](${response.linear_project.url})\n\n`);
                }
            }
            // Check if approval is required
            if (response.status === 'approval_pending' || response.approval_request_id) {
                stream.markdown('\n⚠️ **Approval Required**\n\n');
                if (response.risk_level) {
                    stream.markdown(`Risk Level: ${response.risk_level}\n\n`);
                }
                if (response.approval_request_id) {
                    stream.markdown(`Approval ID: ${response.approval_request_id}\n\n`);
                    stream.markdown('This task requires approval before execution. Approve in Linear or use:\n');
                    stream.markdown(`\`@codechef /approve ${response.task_id} ${response.approval_request_id}\`\n`);
                }
                return { metadata: { taskId: response.task_id, requiresApproval: true } };
            }
            // Execute the workflow automatically (Agent mode)
            stream.progress('Executing workflow...');
            try {
                await this.client.execute(response.task_id);
                stream.markdown('\n✅ **Workflow execution started!**\n\n');
                stream.markdown(`Monitor progress: \`@codechef /status ${response.task_id}\`\n\n`);
            }
            catch (executeError) {
                stream.markdown('\n⚠️ **Task planned but execution failed to start**\n\n');
                stream.markdown(`Error: ${executeError.message}\n\n`);
                stream.markdown(`You can manually execute with: POST /execute/${response.task_id}\n\n`);
            }
            // Stream response
            return await this.renderTaskResponse(response, stream);
        }
        catch (error) {
            stream.markdown(`\n\n❌ **Error**: ${error.message}\n\n`);
            if (error.message.includes('ECONNREFUSED') || error.message.includes('timeout')) {
                stream.markdown('**Troubleshooting:**\n');
                stream.markdown('1. Check orchestrator URL in settings: `code/chef: Configure`\n');
                stream.markdown('2. Verify service is running: `curl https://codechef.appsmithery.co/api/health`\n');
                stream.markdown('3. Check firewall allows outbound connections\n\n');
            }
            return { errorDetails: { message: error.message } };
        }
    }
    async handleCommand(command, args, stream, token) {
        switch (command) {
            case 'status':
                return await this.handleStatusCommand(args, stream);
            case 'approve':
                return await this.handleApproveCommand(args, stream);
            case 'tools':
                return await this.handleToolsCommand(stream);
            default:
                stream.markdown(`Unknown command: ${command}\n\n`);
                stream.markdown('Available commands: status, approve, tools\n');
                return {};
        }
    }
    async handleStatusCommand(taskId, stream) {
        const id = taskId.trim() || this.lastTaskId;
        if (!id) {
            stream.markdown('❌ No task ID provided. Use: `@codechef /status <task-id>`\n');
            return {};
        }
        stream.progress('Checking task status...');
        try {
            const status = await this.client.checkStatus(id);
            stream.markdown(`## Task Status: ${id}\n\n`);
            stream.markdown(`**Status**: ${status.status}\n`);
            stream.markdown(`**Progress**: ${status.completed_subtasks}/${status.total_subtasks} subtasks\n\n`);
            if (status.subtasks && status.subtasks.length > 0) {
                stream.markdown('**Subtasks:**\n\n');
                for (const subtask of status.subtasks) {
                    const icon = subtask.status === 'completed' ? '✅' :
                        subtask.status === 'in_progress' ? '🔄' : '⏳';
                    stream.markdown(`${icon} **${subtask.agent_type}**: ${subtask.description}\n`);
                }
            }
            return { metadata: { taskId: id } };
        }
        catch (error) {
            stream.markdown(`❌ Failed to get status: ${error.message}\n`);
            return { errorDetails: { message: error.message } };
        }
    }
    async handleApproveCommand(args, stream) {
        const [taskId, approvalId] = args.trim().split(/\s+/);
        if (!taskId || !approvalId) {
            stream.markdown('❌ Usage: `@codechef /approve <task-id> <approval-id>`\n');
            return {};
        }
        stream.progress('Submitting approval...');
        try {
            await this.client.approve(taskId, approvalId);
            stream.markdown(`✅ Task ${taskId} approved! Agents will proceed with execution.\n`);
            return { metadata: { taskId, approvalId } };
        }
        catch (error) {
            stream.markdown(`❌ Failed to approve: ${error.message}\n`);
            return { errorDetails: { message: error.message } };
        }
    }
    async handleToolsCommand(stream) {
        stream.progress('Fetching available tools...');
        try {
            const config = vscode.workspace.getConfiguration('codechef');
            const gatewayUrl = config.get('mcpGatewayUrl', 'https://codechef.appsmithery.co/api');
            const response = await fetch(`${gatewayUrl}/tools`);
            const data = await response.json();
            stream.markdown(`## Available MCP Tools (${data.tools.length})\n\n`);
            // Group by server
            const byServer = {};
            for (const tool of data.tools) {
                if (!byServer[tool.server]) {
                    byServer[tool.server] = [];
                }
                byServer[tool.server].push(tool);
            }
            for (const [server, tools] of Object.entries(byServer)) {
                stream.markdown(`### ${server} (${tools.length} tools)\n\n`);
                for (const tool of tools.slice(0, 5)) {
                    stream.markdown(`- **${tool.name}**: ${tool.description}\n`);
                }
                if (tools.length > 5) {
                    stream.markdown(`- ... and ${tools.length - 5} more\n`);
                }
                stream.markdown('\n');
            }
            return { metadata: { toolCount: data.tools.length } };
        }
        catch (error) {
            stream.markdown(`❌ Failed to fetch tools: ${error.message}\n`);
            return { errorDetails: { message: error.message } };
        }
    }
    async renderTaskResponse(response, stream) {
        stream.markdown(`## ✅ Task Submitted\n\n`);
        stream.markdown(`**Task ID**: \`${response.task_id}\`\n\n`);
        // Subtasks
        stream.markdown(`**Subtasks** (${response.subtasks.length}):\n\n`);
        for (const subtask of response.subtasks) {
            const agentEmoji = this.getAgentEmoji(subtask.agent_type);
            stream.markdown(`${agentEmoji} **${subtask.agent_type}**: ${subtask.description}\n`);
        }
        // Routing plan
        if (response.routing_plan) {
            stream.markdown(`\n**Estimated Duration**: ${response.routing_plan.estimated_duration_minutes} minutes\n\n`);
        }
        // Approval notification
        if (response.approval_request_id) {
            stream.markdown(`\n⚠️ **Approval Required**\n\n`);
            stream.markdown(`This task requires human approval before execution.\n\n`);
            const linearHub = vscode.workspace.getConfiguration('codechef').get('linearHubIssue', 'PR-68');
            const linearUrl = this.getLinearIssueUrl(linearHub);
            stream.markdown(`Check Linear issue [${linearHub}](${linearUrl}) for approval request.\n\n`);
            stream.button({
                command: 'codechef.showApprovals',
                title: '📋 View Approvals',
                arguments: []
            });
        }
        // Observability links
        stream.markdown(`\n---\n\n`);
        stream.markdown(`**Observability:**\n\n`);
        const langsmithUrl = vscode.workspace.getConfiguration('codechef').get('langsmithUrl');
        if (langsmithUrl) {
            stream.markdown(`- [LangSmith Traces](${langsmithUrl})\n`);
        }
        stream.markdown(`- [Prometheus Metrics](https://codechef.appsmithery.co)\n`);
        stream.markdown(`- Check status: \`@codechef /status ${response.task_id}\`\n`);
        return {
            metadata: {
                taskId: response.task_id,
                subtaskCount: response.subtasks.length,
                requiresApproval: !!response.approval_request_id
            }
        };
    }
    getLinearIssueUrl(issueId) {
        const config = vscode.workspace.getConfiguration('codechef');
        const workspaceSlug = config.get('linearWorkspaceSlug', 'project-roadmaps');
        return `https://linear.app/${workspaceSlug}/issue/${issueId}`;
    }
    getAgentEmoji(agentType) {
        const emojiMap = {
            'feature-dev': '💻',
            'code-review': '🔍',
            'infrastructure': '🏗️',
            'cicd': '🚀',
            'documentation': '📚',
            'orchestrator': '🎯'
        };
        return emojiMap[agentType] || '🤖';
    }
    async submitTask(description) {
        try {
            const workspaceContext = await this.contextExtractor.extract();
            const response = await this.client.orchestrate({
                description,
                priority: 'medium',
                project_context: workspaceContext
            });
            this.lastTaskId = response.task_id;
            vscode.window.showInformationMessage(`Task submitted: ${response.task_id}`, 'View Status', 'View in Linear').then(selection => {
                if (selection === 'View Status') {
                    vscode.commands.executeCommand('codechef.checkStatus', response.task_id);
                }
                else if (selection === 'View in Linear') {
                    vscode.commands.executeCommand('codechef.showApprovals');
                }
            });
        }
        catch (error) {
            vscode.window.showErrorMessage(`Failed to submit task: ${error.message}`);
        }
    }
    async checkTaskStatus(taskId) {
        try {
            const status = await this.client.checkStatus(taskId);
            const message = `Task ${taskId}: ${status.status} (${status.completed_subtasks}/${status.total_subtasks} complete)`;
            vscode.window.showInformationMessage(message);
        }
        catch (error) {
            vscode.window.showErrorMessage(`Failed to get status: ${error.message}`);
        }
    }
    clearCache() {
        this.sessionManager.clearSessions();
    }
}
exports.CodeChefChatParticipant = CodeChefChatParticipant;
//# sourceMappingURL=chatParticipant.js.map