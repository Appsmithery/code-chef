import * as vscode from 'vscode';
import { CHAT_COMMANDS } from './constants';
import { ContextExtractor } from './contextExtractor';
import { StatusHandler } from './handlers/statusHandler';
import { WorkflowHandler } from './handlers/workflowHandler';
import { OrchestratorClient } from './orchestratorClient';
import {
    renderError,
    renderLinearProjectCreated,
    renderTaskSubmitted
} from './renderers/responseRenderer';
import { SessionManager } from './sessionManager';
import { buildWorkspaceConfig } from './settings';

export class CodeChefChatParticipant {
    private client: OrchestratorClient;
    private contextExtractor: ContextExtractor;
    private sessionManager: SessionManager;
    private lastTaskId?: string;
    private useStreaming: boolean;
    
    // Handlers
    private statusHandler: StatusHandler;
    private workflowHandler: WorkflowHandler;

    constructor(private context: vscode.ExtensionContext) {
        const config = vscode.workspace.getConfiguration('codechef');
        this.client = new OrchestratorClient({
            baseUrl: config.get('orchestratorUrl')!,
            apiKey: config.get('apiKey') || undefined
        });
        this.contextExtractor = new ContextExtractor();
        this.sessionManager = new SessionManager(context);
        
        // Enable streaming by default, can be configured
        this.useStreaming = config.get('useStreaming', true);
        
        // Initialize handlers
        this.statusHandler = new StatusHandler(this.client, () => this.lastTaskId);
        this.workflowHandler = new WorkflowHandler(this.client, this.contextExtractor);

        // Listen for configuration changes to update API key and streaming
        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('codechef.apiKey')) {
                const newApiKey = vscode.workspace.getConfiguration('codechef').get<string>('apiKey');
                this.client.setApiKey(newApiKey || undefined);
            }
            if (e.affectsConfiguration('codechef.useStreaming')) {
                this.useStreaming = vscode.workspace.getConfiguration('codechef').get('useStreaming', true);
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

        // Use streaming for conversational chat
        if (this.useStreaming) {
            return await this.handleStreamingChat(userMessage, context, stream, token);
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

            // Log Linear project creation
            if (response.linear_project?.id) {
                console.log(`code/chef: Created Linear project ${response.linear_project.id} under team`);
                renderLinearProjectCreated(response.linear_project, stream);
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
                    stream.markdown(`\`@chef /approve ${response.task_id} ${response.approval_request_id}\`\n`);
                }
                return { metadata: { taskId: response.task_id, requiresApproval: true } };
            }

            // Execute the workflow automatically (Agent mode)
            stream.progress('Executing workflow...');
            try {
                await this.client.execute(response.task_id);
                stream.markdown('\n✅ **Workflow execution started!**\n\n');
                stream.markdown(`Monitor progress: \`@chef /status ${response.task_id}\`\n\n`);
            } catch (executeError: any) {
                stream.markdown('\n⚠️ **Task planned but execution failed to start**\n\n');
                stream.markdown(`Error: ${executeError.message}\n\n`);
                stream.markdown(`You can manually execute with: POST /execute/${response.task_id}\n\n`);
            }

            // Stream response
            return renderTaskSubmitted(response, stream);

        } catch (error: any) {
            renderError(error, stream);
            return { errorDetails: { message: error.message } };
        }
    }

    /**
     * Handle chat request with real-time SSE streaming.
     * Provides token-by-token response display for natural conversation flow.
     */
    private async handleStreamingChat(
        userMessage: string,
        context: vscode.ChatContext,
        stream: vscode.ChatResponseStream,
        token: vscode.CancellationToken
    ): Promise<vscode.ChatResult> {
        stream.progress('Connecting to code/chef...');

        try {
            // Extract workspace context
            const workspaceContext = await this.contextExtractor.extract();
            
            // Get or create session
            const sessionId = this.sessionManager.getOrCreateSession(context);
            
            let currentAgent = '';
            let sessionIdFromStream = sessionId;
            let fullResponse = '';  // Accumulate full response for parsing
            let isSuprevisorResponse = false;  // Track if we're in supervisor mode

            // Stream response token by token
            for await (const chunk of this.client.chatStream({
                message: userMessage,
                session_id: sessionId,
                context: workspaceContext,
                workspace_config: buildWorkspaceConfig()
            })) {
                // Check for cancellation
                if (token.isCancellationRequested) {
                    stream.markdown('\n\n*Response cancelled*');
                    break;
                }

                switch (chunk.type) {
                    case 'content':
                        // Accumulate content for parsing
                        if (chunk.content) {
                            fullResponse += chunk.content;
                            
                            // Check if this is a supervisor routing response
                            if (fullResponse.includes('NEXT_AGENT:') || fullResponse.includes('REQUIRES_APPROVAL:') || fullResponse.includes('REASONING:')) {
                                isSuprevisorResponse = true;
                            }
                            
                            // If it's a supervisor response, buffer until complete
                            // Otherwise stream normally
                            if (!isSuprevisorResponse) {
                                stream.markdown(chunk.content);
                            }
                        }
                        break;
                    
                    case 'agent_complete':
                        // Log agent transitions (optional UI feedback)
                        if (chunk.agent && chunk.agent !== currentAgent) {
                            currentAgent = chunk.agent;
                            console.log(`code/chef: Agent ${chunk.agent} completed`);
                        }
                        break;
                    
                    case 'tool_call':
                        // Optional: show tool usage
                        if (chunk.tool) {
                            console.log(`code/chef: Tool called: ${chunk.tool}`);
                        }
                        break;
                    
                    case 'error':
                        stream.markdown(`\n\n❌ **Error**: ${chunk.error}`);
                        return { 
                            errorDetails: { message: chunk.error || 'Unknown streaming error' } 
                        };
                    
                    case 'done':
                        if (chunk.session_id) {
                            sessionIdFromStream = chunk.session_id;
                        }
                        
                        // If supervisor response, extract and display only reasoning
                        if (isSuprevisorResponse && fullResponse) {
                            const reasoning = this.extractReasoning(fullResponse);
                            if (reasoning) {
                                stream.markdown(reasoning);
                            }
                        }
                        break;
                }
            }

            return { 
                metadata: { 
                    status: 'success',
                    streaming: true,
                    sessionId: sessionIdFromStream
                } 
            };

        } catch (error: any) {
            // Fallback to non-streaming on error
            console.error('Streaming failed, error:', error.message);
            stream.markdown(`\n\n❌ **Streaming Error**: ${error.message}\n\n`);
            stream.markdown('*Tip: You can disable streaming in settings with `codechef.useStreaming: false`*\n');
            return { 
                errorDetails: { message: error.message } 
            };
        }
    }

    /**
     * Extract only the REASONING portion from supervisor routing responses.
     * Filters out NEXT_AGENT and REQUIRES_APPROVAL metadata for cleaner UX.
     * Full trace data is still captured in LangSmith for evaluation.
     */
    private extractReasoning(fullResponse: string): string {
        const lines = fullResponse.split('\n');
        const reasoningLines: string[] = [];
        let inReasoning = false;

        for (const line of lines) {
            if (line.startsWith('REASONING:')) {
                // Extract reasoning content (skip the REASONING: prefix)
                const reasoningContent = line.substring('REASONING:'.length).trim();
                if (reasoningContent) {
                    reasoningLines.push(reasoningContent);
                }
                inReasoning = true;
            } else if (inReasoning && !line.startsWith('NEXT_AGENT:') && !line.startsWith('REQUIRES_APPROVAL:')) {
                // Continue collecting reasoning lines
                reasoningLines.push(line);
            } else if (line.startsWith('NEXT_AGENT:') || line.startsWith('REQUIRES_APPROVAL:')) {
                // Skip metadata lines
                inReasoning = false;
            }
        }

        return reasoningLines.join('\n').trim();
    }

    private async handleCommand(
        command: string,
        args: string,
        stream: vscode.ChatResponseStream,
        token: vscode.CancellationToken
    ): Promise<vscode.ChatResult> {
        switch (command) {
            case CHAT_COMMANDS.STATUS:
                return await this.statusHandler.handleStatus(args, stream);
            
            case CHAT_COMMANDS.APPROVE:
                return await this.statusHandler.handleApprove(args, stream);
            
            case CHAT_COMMANDS.TOOLS:
                return await this.workflowHandler.handleTools(stream);
            
            case CHAT_COMMANDS.WORKFLOW:
                return await this.workflowHandler.handleWorkflow(args, stream);
            
            case CHAT_COMMANDS.WORKFLOWS:
                return await this.workflowHandler.handleWorkflowsList(stream);
            
            default:
                stream.markdown(`Unknown command: ${command}\n\n`);
                stream.markdown('Available commands: status, approve, tools, workflow, workflows\n');
                return {};
        }
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
