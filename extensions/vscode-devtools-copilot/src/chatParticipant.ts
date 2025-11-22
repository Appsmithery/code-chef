import * as vscode from 'vscode';
import { ContextExtractor } from './contextExtractor';
import { OrchestratorClient, TaskResponse } from './orchestratorClient';
import { SessionManager } from './sessionManager';

export class DevToolsChatParticipant {
    private client: OrchestratorClient;
    private contextExtractor: ContextExtractor;
    private sessionManager: SessionManager;
    private lastTaskId?: string;

    constructor(private context: vscode.ExtensionContext) {
        const config = vscode.workspace.getConfiguration('devtools');
        this.client = new OrchestratorClient(config.get('orchestratorUrl')!);
        this.contextExtractor = new ContextExtractor();
        this.sessionManager = new SessionManager(context);
    }

    async handleChatRequest(
        request: vscode.ChatRequest,
        context: vscode.ChatContext,
        stream: vscode.ChatResponseStream,
        token: vscode.CancellationToken
    ): Promise<vscode.ChatResult> {
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
            
            stream.progress('Submitting to Dev-Tools orchestrator...');
            
            // Submit to orchestrator
            const response = await this.client.orchestrate({
                description: userMessage,
                priority: 'medium',
                project_context: workspaceContext,
                session_id: sessionId
            });

            this.lastTaskId = response.task_id;

            // Check if approval is required
            if (response.status === 'approval_pending' || response.approval_request_id) {
                stream.markdown('\n⚠️ **Approval Required**\n\n');
                if (response.risk_level) {
                    stream.markdown(`Risk Level: ${response.risk_level}\n\n`);
                }
                if (response.approval_request_id) {
                    stream.markdown(`Approval ID: ${response.approval_request_id}\n\n`);
                    stream.markdown('This task requires approval before execution. Approve in Linear or use:\n');
                    stream.markdown(`\`@devtools /approve ${response.task_id} ${response.approval_request_id}\`\n`);
                }
                return { metadata: { taskId: response.task_id, requiresApproval: true } };
            }

            // Execute the workflow automatically (Agent mode)
            stream.progress('Executing workflow...');
            try {
                await this.client.execute(response.task_id);
                stream.markdown('\n✅ **Workflow execution started!**\n\n');
                stream.markdown(`Monitor progress: \`@devtools /status ${response.task_id}\`\n\n`);
            } catch (executeError: any) {
                stream.markdown('\n⚠️ **Task planned but execution failed to start**\n\n');
                stream.markdown(`Error: ${executeError.message}\n\n`);
                stream.markdown(`You can manually execute with: POST /execute/${response.task_id}\n\n`);
            }

            // Stream response
            return await this.renderTaskResponse(response, stream);

        } catch (error: any) {
            stream.markdown(`\n\n❌ **Error**: ${error.message}\n\n`);
            
            if (error.message.includes('ECONNREFUSED') || error.message.includes('timeout')) {
                stream.markdown('**Troubleshooting:**\n');
                stream.markdown('1. Check orchestrator URL in settings: `Dev-Tools: Configure`\n');
                stream.markdown('2. Verify service is running: `curl http://45.55.173.72:8001/health`\n');
                stream.markdown('3. Check firewall allows outbound connections\n\n');
            }

            return { errorDetails: { message: error.message } };
        }
    }

    private async handleCommand(
        command: string,
        args: string,
        stream: vscode.ChatResponseStream,
        token: vscode.CancellationToken
    ): Promise<vscode.ChatResult> {
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

    private async handleStatusCommand(
        taskId: string,
        stream: vscode.ChatResponseStream
    ): Promise<vscode.ChatResult> {
        const id = taskId.trim() || this.lastTaskId;
        
        if (!id) {
            stream.markdown('❌ No task ID provided. Use: `@devtools /status <task-id>`\n');
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
        } catch (error: any) {
            stream.markdown(`❌ Failed to get status: ${error.message}\n`);
            return { errorDetails: { message: error.message } };
        }
    }

    private async handleApproveCommand(
        args: string,
        stream: vscode.ChatResponseStream
    ): Promise<vscode.ChatResult> {
        const [taskId, approvalId] = args.trim().split(/\s+/);
        
        if (!taskId || !approvalId) {
            stream.markdown('❌ Usage: `@devtools /approve <task-id> <approval-id>`\n');
            return {};
        }

        stream.progress('Submitting approval...');

        try {
            await this.client.approve(taskId, approvalId);
            stream.markdown(`✅ Task ${taskId} approved! Agents will proceed with execution.\n`);
            return { metadata: { taskId, approvalId } };
        } catch (error: any) {
            stream.markdown(`❌ Failed to approve: ${error.message}\n`);
            return { errorDetails: { message: error.message } };
        }
    }

    private async handleToolsCommand(
        stream: vscode.ChatResponseStream
    ): Promise<vscode.ChatResult> {
        stream.progress('Fetching available tools...');

        try {
            const config = vscode.workspace.getConfiguration('devtools');
            const gatewayUrl = config.get('mcpGatewayUrl', 'http://45.55.173.72:8000');
            
            const response = await fetch(`${gatewayUrl}/tools`);
            const data = await response.json() as { tools: Array<{ name: string; description: string; server: string }> };
            
            stream.markdown(`## Available MCP Tools (${data.tools.length})\n\n`);
            
            // Group by server
            const byServer: Record<string, any[]> = {};
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
        } catch (error: any) {
            stream.markdown(`❌ Failed to fetch tools: ${error.message}\n`);
            return { errorDetails: { message: error.message } };
        }
    }

    private async renderTaskResponse(
        response: TaskResponse,
        stream: vscode.ChatResponseStream
    ): Promise<vscode.ChatResult> {
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
            
            const linearHub = vscode.workspace.getConfiguration('devtools').get('linearHubIssue', 'PR-68');
            const linearUrl = this.getLinearIssueUrl(linearHub);
            stream.markdown(`Check Linear issue [${linearHub}](${linearUrl}) for approval request.\n\n`);
            
            stream.button({
                command: 'devtools.showApprovals',
                title: '📋 View Approvals',
                arguments: []
            });
        }

        // Observability links
        stream.markdown(`\n---\n\n`);
        stream.markdown(`**Observability:**\n\n`);
        
        const langsmithUrl = vscode.workspace.getConfiguration('devtools').get('langsmithUrl');
        if (langsmithUrl) {
            stream.markdown(`- [LangSmith Traces](${langsmithUrl})\n`);
        }
        stream.markdown(`- [Prometheus Metrics](http://45.55.173.72:9090)\n`);
        stream.markdown(`- Check status: \`@devtools /status ${response.task_id}\`\n`);

        return {
            metadata: {
                taskId: response.task_id,
                subtaskCount: response.subtasks.length,
                requiresApproval: !!response.approval_request_id
            }
        };
    }

    private getLinearIssueUrl(issueId: string): string {
        const config = vscode.workspace.getConfiguration('devtools');
        const workspaceSlug = config.get('linearWorkspaceSlug', 'project-roadmaps');
        return `https://linear.app/${workspaceSlug}/issue/${issueId}`;
    }

    private getAgentEmoji(agentType: string): string {
        const emojiMap: Record<string, string> = {
            'feature-dev': '💻',
            'code-review': '🔍',
            'infrastructure': '🏗️',
            'cicd': '🚀',
            'documentation': '📚',
            'orchestrator': '🎯'
        };
        return emojiMap[agentType] || '🤖';
    }

    async submitTask(description: string): Promise<void> {
        try {
            const workspaceContext = await this.contextExtractor.extract();
            const response = await this.client.orchestrate({
                description,
                priority: 'medium',
                project_context: workspaceContext
            });

            this.lastTaskId = response.task_id;

            vscode.window.showInformationMessage(
                `Task submitted: ${response.task_id}`,
                'View Status',
                'View in Linear'
            ).then(selection => {
                if (selection === 'View Status') {
                    vscode.commands.executeCommand('devtools.checkStatus', response.task_id);
                } else if (selection === 'View in Linear') {
                    vscode.commands.executeCommand('devtools.showApprovals');
                }
            });
        } catch (error: any) {
            vscode.window.showErrorMessage(`Failed to submit task: ${error.message}`);
        }
    }

    async checkTaskStatus(taskId: string): Promise<void> {
        try {
            const status = await this.client.checkStatus(taskId);
            
            const message = `Task ${taskId}: ${status.status} (${status.completed_subtasks}/${status.total_subtasks} complete)`;
            vscode.window.showInformationMessage(message);
        } catch (error: any) {
            vscode.window.showErrorMessage(`Failed to get status: ${error.message}`);
        }
    }

    clearCache(): void {
        this.sessionManager.clearSessions();
    }
}
