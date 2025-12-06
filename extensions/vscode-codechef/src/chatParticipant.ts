import * as vscode from 'vscode';
import { ContextExtractor } from './contextExtractor';
import { OrchestratorClient, SmartWorkflowResponse, TaskResponse } from './orchestratorClient';
import { SessionManager } from './sessionManager';
import { buildWorkspaceConfig, getWorkflowSettings } from './settings';

export class CodeChefChatParticipant {
    private client: OrchestratorClient;
    private contextExtractor: ContextExtractor;
    private sessionManager: SessionManager;
    private lastTaskId?: string;

    constructor(private context: vscode.ExtensionContext) {
        const config = vscode.workspace.getConfiguration('codechef');
        this.client = new OrchestratorClient({
            baseUrl: config.get('orchestratorUrl')!,
            apiKey: config.get('apiKey') || undefined
        });
        this.contextExtractor = new ContextExtractor();
        this.sessionManager = new SessionManager(context);

        // Listen for configuration changes to update API key
        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('codechef.apiKey')) {
                const newApiKey = vscode.workspace.getConfiguration('codechef').get<string>('apiKey');
                this.client.setApiKey(newApiKey || undefined);
            }
        });
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
            
            stream.progress('Submitting to code/chef orchestrator...');
            
            // Submit to orchestrator with token optimization settings
            const response = await this.client.orchestrate({
                description: userMessage,
                priority: 'medium',
                project_context: workspaceContext,
                workspace_config: buildWorkspaceConfig(),
                session_id: sessionId
            });

            this.lastTaskId = response.task_id;

            // Log Linear project creation (team-level, no workspace save needed)
            if (response.linear_project?.id) {
                console.log(`code/chef: Created Linear project ${response.linear_project.id} under team`);
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
                stream.markdown('1. Check orchestrator URL in settings: `code/chef: Configure`\n');
                stream.markdown('2. Verify service is running: `curl https://codechef.appsmithery.co/api/health`\n');
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
            
            case 'workflow':
                return await this.handleWorkflowCommand(args, stream);
            
            case 'workflows':
                return await this.handleWorkflowsListCommand(stream);
            
            default:
                stream.markdown(`Unknown command: ${command}\n\n`);
                stream.markdown('Available commands: status, approve, tools, workflow, workflows\n');
                return {};
        }
    }

    private async handleStatusCommand(
        taskId: string,
        stream: vscode.ChatResponseStream
    ): Promise<vscode.ChatResult> {
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
            stream.markdown('❌ Usage: `@codechef /approve <task-id> <approval-id>`\n');
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
            const config = vscode.workspace.getConfiguration('codechef');
            const gatewayUrl = config.get('mcpGatewayUrl', 'https://codechef.appsmithery.co/api');
            
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

    private async handleWorkflowCommand(
        args: string,
        stream: vscode.ChatResponseStream
    ): Promise<vscode.ChatResult> {
        const trimmedArgs = args.trim();
        
        if (!trimmedArgs) {
            stream.markdown('❌ Usage: `@codechef /workflow [workflow-name] <task description>`\n\n');
            stream.markdown('Examples:\n');
            stream.markdown('- `@codechef /workflow Deploy PR #123 to production` (auto-select)\n');
            stream.markdown('- `@codechef /workflow feature Implement user authentication` (explicit)\n');
            stream.markdown('- `@codechef /workflow hotfix Fix critical login bug` (explicit)\n\n');
            stream.markdown('Use `@codechef /workflows` to see available workflows.\n');
            return {};
        }

        stream.progress('Analyzing task and selecting workflow...');

        try {
            // Extract workspace context
            const workspaceContext = await this.contextExtractor.extract();
            const workflowSettings = getWorkflowSettings();
            
            // Parse arguments: first word might be workflow name
            const parts = trimmedArgs.split(/\s+/);
            let explicitWorkflow: string | undefined;
            let taskDescription = trimmedArgs;
            
            // Check if first word matches a known workflow
            const knownWorkflows = ['feature', 'pr-deployment', 'hotfix', 'infrastructure', 'docs-update'];
            if (parts.length > 1 && knownWorkflows.includes(parts[0])) {
                explicitWorkflow = parts[0];
                taskDescription = parts.slice(1).join(' ');
            } else if (workflowSettings.defaultWorkflow !== 'auto') {
                explicitWorkflow = workflowSettings.defaultWorkflow;
            }

            // Use dry_run if showWorkflowPreview is enabled and autoExecute is false
            const dryRun = workflowSettings.showWorkflowPreview && !workflowSettings.workflowAutoExecute;

            const response = await this.client.smartExecuteWorkflow({
                task_description: taskDescription,
                explicit_workflow: explicitWorkflow,
                context: workspaceContext,
                dry_run: dryRun,
                confirm_threshold: workflowSettings.workflowConfirmThreshold
            });

            // Render selection result
            await this.renderWorkflowSelection(response, stream, dryRun);

            // If requires confirmation, show Quick Pick
            if (response.requires_confirmation && !dryRun) {
                const confirmed = await this.showWorkflowConfirmation(response);
                if (!confirmed) {
                    stream.markdown('\n⚠️ **Workflow execution cancelled by user.**\n');
                    return { metadata: { cancelled: true } };
                }
                
                // Execute after confirmation
                stream.progress('Executing workflow...');
                const executeResponse = await this.client.smartExecuteWorkflow({
                    task_description: taskDescription,
                    explicit_workflow: response.workflow_name,
                    context: workspaceContext,
                    dry_run: false
                });
                
                stream.markdown(`\n✅ **Workflow started!**\n`);
                if (executeResponse.workflow_id) {
                    stream.markdown(`Workflow ID: \`${executeResponse.workflow_id}\`\n`);
                }
            }

            return { 
                metadata: { 
                    workflow: response.workflow_name,
                    confidence: response.confidence,
                    method: response.method,
                    workflow_id: response.workflow_id
                } 
            };
        } catch (error: any) {
            stream.markdown(`\n❌ **Error**: ${error.message}\n`);
            return { errorDetails: { message: error.message } };
        }
    }

    private async handleWorkflowsListCommand(
        stream: vscode.ChatResponseStream
    ): Promise<vscode.ChatResult> {
        stream.progress('Fetching available workflows...');

        try {
            const response = await this.client.getWorkflowTemplates();
            
            stream.markdown(`## 📋 Available Workflows (${response.count})\n\n`);
            
            for (const template of response.templates) {
                const riskEmoji = template.risk_level === 'high' ? '🔴' : 
                                  template.risk_level === 'medium' ? '🟡' : '🟢';
                const agentEmojis = template.agents_involved.map(a => this.getAgentEmoji(a)).join(' ');
                
                stream.markdown(`### ${template.name}\n`);
                stream.markdown(`${template.description}\n\n`);
                stream.markdown(`| Property | Value |\n`);
                stream.markdown(`|----------|-------|\n`);
                stream.markdown(`| Template | \`${template.template_name}\` |\n`);
                stream.markdown(`| Version | ${template.version} |\n`);
                stream.markdown(`| Risk Level | ${riskEmoji} ${template.risk_level} |\n`);
                stream.markdown(`| Steps | ${template.steps_count} |\n`);
                stream.markdown(`| Duration | ~${template.estimated_duration_minutes} min |\n`);
                stream.markdown(`| Agents | ${agentEmojis} ${template.agents_involved.join(', ')} |\n`);
                
                if (template.required_context.length > 0) {
                    stream.markdown(`| Required Context | \`${template.required_context.join('`, `')}\` |\n`);
                }
                
                stream.markdown('\n');
            }
            
            stream.markdown('---\n\n');
            stream.markdown('**Usage:** `@codechef /workflow [name] <task description>`\n\n');
            stream.markdown('**Example:** `@codechef /workflow pr-deployment Deploy PR #123 to production`\n');

            return { metadata: { templateCount: response.count } };
        } catch (error: any) {
            stream.markdown(`❌ Failed to fetch workflows: ${error.message}\n`);
            return { errorDetails: { message: error.message } };
        }
    }

    private async renderWorkflowSelection(
        response: SmartWorkflowResponse,
        stream: vscode.ChatResponseStream,
        dryRun: boolean
    ): Promise<void> {
        const confidencePercent = Math.round(response.confidence * 100);
        const confidenceEmoji = response.confidence >= 0.8 ? '🟢' : 
                                response.confidence >= 0.6 ? '🟡' : '🔴';
        
        stream.markdown(`## 🎯 Workflow Selection\n\n`);
        stream.markdown(`**Selected:** ${response.workflow_name}\n`);
        stream.markdown(`**Confidence:** ${confidenceEmoji} ${confidencePercent}%\n`);
        stream.markdown(`**Method:** ${response.method}\n`);
        
        if (response.reasoning) {
            stream.markdown(`**Reasoning:** ${response.reasoning}\n`);
        }
        
        stream.markdown('\n');
        
        // Show extracted context
        if (Object.keys(response.context_variables).length > 0) {
            stream.markdown('### Extracted Context\n\n');
            for (const [key, value] of Object.entries(response.context_variables)) {
                if (value !== null && value !== undefined) {
                    stream.markdown(`- **${key}:** ${value}\n`);
                }
            }
            stream.markdown('\n');
        }
        
        // Show alternatives if available
        if (response.alternatives.length > 0) {
            stream.markdown('### Alternative Workflows\n\n');
            for (const alt of response.alternatives) {
                const altConfidence = Math.round((alt.confidence || 0) * 100);
                stream.markdown(`- ${alt.workflow} (${altConfidence}%)\n`);
            }
            stream.markdown('\n');
        }
        
        // Show status
        if (dryRun) {
            stream.markdown('---\n');
            stream.markdown('📝 **Preview Mode** - Workflow not executed.\n');
            stream.markdown('Set `codechef.showWorkflowPreview` to `false` or use `codechef.workflowAutoExecute` to auto-execute.\n');
        } else if (response.requires_confirmation) {
            stream.markdown('---\n');
            stream.markdown('⚠️ **Confirmation Required** - Confidence below threshold.\n');
        } else if (response.workflow_id) {
            stream.markdown('---\n');
            stream.markdown(`✅ **Workflow Started!** ID: \`${response.workflow_id}\`\n`);
            stream.markdown(`Status: ${response.execution_status}\n`);
        } else if (response.execution_status === 'error') {
            stream.markdown('---\n');
            stream.markdown('❌ **Workflow Failed to Start**\n');
        }
    }

    private async showWorkflowConfirmation(response: SmartWorkflowResponse): Promise<boolean> {
        // Build quick pick items
        const items: vscode.QuickPickItem[] = [
            {
                label: `$(check) Execute ${response.workflow_name}`,
                description: `${Math.round(response.confidence * 100)}% confidence`,
                detail: response.reasoning,
                picked: true
            }
        ];
        
        // Add alternatives
        for (const alt of response.alternatives) {
            items.push({
                label: `$(arrow-right) Use ${alt.workflow} instead`,
                description: `${Math.round((alt.confidence || 0) * 100)}% confidence`
            });
        }
        
        items.push({
            label: '$(x) Cancel',
            description: 'Do not execute any workflow'
        });
        
        const selected = await vscode.window.showQuickPick(items, {
            title: 'Confirm Workflow Selection',
            placeHolder: `Select workflow to execute (${response.method} selection)`
        });
        
        if (!selected || selected.label.includes('Cancel')) {
            return false;
        }
        
        return true;
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
        const grafanaUrl = vscode.workspace.getConfiguration('codechef').get('grafanaUrl', 'https://appsmithery.grafana.net');
        stream.markdown(`- [Grafana Metrics](${grafanaUrl})\n`);
        stream.markdown(`- Check status: \`@codechef /status ${response.task_id}\`\n`);

        return {
            metadata: {
                taskId: response.task_id,
                subtaskCount: response.subtasks.length,
                requiresApproval: !!response.approval_request_id
            }
        };
    }

    private getLinearIssueUrl(issueId: string): string {
        const config = vscode.workspace.getConfiguration('codechef');
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
                    vscode.commands.executeCommand('codechef.checkStatus', response.task_id);
                } else if (selection === 'View in Linear') {
                    vscode.commands.executeCommand('codechef.showApprovals');
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
