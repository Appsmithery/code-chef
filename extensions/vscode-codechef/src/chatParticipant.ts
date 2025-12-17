import * as vscode from 'vscode';
import { CHAT_COMMANDS } from './constants';
import { ContextExtractor } from './contextExtractor';
import { StatusHandler } from './handlers/statusHandler';
import { WorkflowHandler } from './handlers/workflowHandler';
import { OrchestratorClient } from './orchestratorClient';
import { PromptEnhancer } from './promptEnhancer';
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
    private promptEnhancer: PromptEnhancer;
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
        this.promptEnhancer = new PromptEnhancer();
        
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

    /**
     * Extract chat references (files/symbols selected by user).
     * These provide explicit context signals for better RAG queries.
     */
    private extractChatReferences(references: readonly vscode.ChatPromptReference[]) {
        const files: string[] = [];
        const symbols: Array<{file: string; line: number; name?: string}> = [];
        const strings: string[] = [];

        for (const ref of references) {
            if (ref.value instanceof vscode.Uri) {
                // File reference (#file)
                files.push(ref.value.fsPath);
            } else if (ref.value instanceof vscode.Location) {
                // Symbol reference (function, class, etc.)
                symbols.push({
                    file: ref.value.uri.fsPath,
                    line: ref.value.range.start.line,
                    name: undefined  // VS Code doesn't provide symbol name in Location
                });
            } else if (typeof ref.value === 'string') {
                // String reference (variable name, etc.)
                strings.push(ref.value);
            }
            // Note: SymbolInformation not commonly used in chat refs
        }

        return {
            files,
            symbols,
            strings,
            count: files.length + symbols.length + strings.length
        };
    }

    /**
     * Extract Copilot model metadata for telemetry.
     * Tracks which models users prefer for different task types.
     */
    private extractModelMetadata(model: vscode.LanguageModelChat) {
        return {
            vendor: model.vendor,
            family: model.family,
            version: model.version || 'unknown',
            name: model.name,
            maxInputTokens: model.maxInputTokens
            // Note: maxOutputTokens not available in VS Code API
        };
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
            return await this.handleStreamingChat(userMessage, context, stream, token, request);  // Pass request
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
        token: vscode.CancellationToken,
        request: vscode.ChatRequest  // ADD parameter
    ): Promise<vscode.ChatResult> {
        const overallStartTime = Date.now();
        
        try {
            // Step 1: Pre-flight health check
            stream.progress('Checking orchestrator connection...');
            const clientBaseURL = this.client['client'].defaults.baseURL;
            console.log(`[ChatParticipant] 🏥 Pre-flight health check starting`);
            console.log(`[ChatParticipant] Target URL: ${clientBaseURL}/health`);
            try {
                await this.client.health();
                const healthCheckTime = Date.now() - overallStartTime;
                console.log(`[ChatParticipant] ✅ Health check passed in ${healthCheckTime}ms`);
            } catch (healthError: any) {
                const errorMsg = `Cannot reach orchestrator at ${clientBaseURL}. ${healthError.message || 'Connection failed'}`;
                console.error(`[ChatParticipant] ❌ Health check failed:`, healthError);
                console.error(`[ChatParticipant] Error details:`, {
                    status: healthError.response?.status,
                    statusText: healthError.response?.statusText,
                    data: healthError.response?.data,
                    message: healthError.message
                });
                stream.markdown(`❌ **Connection Error**\n\n${errorMsg}\n\nPlease check:\n- Orchestrator URL in settings\n- Network connectivity\n- API key configuration`);
                return { metadata: { error: errorMsg } };
            }
            
            // Step 2: Extract workspace context
            stream.progress('Extracting workspace context...');
            const contextStartTime = Date.now();
            const workspaceContext = await this.contextExtractor.extract();
            const contextDuration = Date.now() - contextStartTime;
            console.log(`[ChatParticipant] Context extraction completed in ${contextDuration}ms`);
            
            // Step 3: Prepare for streaming
            stream.progress('Connecting to orchestrator...');
            
            // Get or create session
            const sessionId = this.sessionManager.getOrCreateSession(context);
            
            // === COPILOT CONTEXT ENHANCEMENT ===
            const chatReferences = this.extractChatReferences(request.references);
            const copilotModel = this.extractModelMetadata(request.model);

            // Log for debugging (remove after UAT)
            if (chatReferences.count > 0) {
                console.log(`code/chef: Captured ${chatReferences.count} chat references`, chatReferences);
            }
            console.log(`code/chef: Using Copilot model ${copilotModel.family}`, copilotModel);

            // === PROMPT ENHANCEMENT (NEW) ===
            const config = vscode.workspace.getConfiguration('codechef');
            const enhancePrompts = config.get('enhancePrompts', false);
            let finalPrompt = userMessage;
            let enhancementError: string | undefined;

            if (enhancePrompts) {
                stream.progress('Enhancing task description with Copilot...');
                
                const template = config.get<'detailed' | 'structured' | 'minimal'>(
                    'enhancementTemplate',
                    'structured'
                );
                
                const result = await this.promptEnhancer.enhance(
                    userMessage,
                    request.model,  // Use user's selected Copilot model
                    template,
                    token
                );
                
                finalPrompt = result.enhanced;
                enhancementError = result.error;

                // Log enhancement for debugging
                if (enhancementError) {
                    console.warn(`code/chef: Prompt enhancement failed: ${enhancementError}`);
                } else {
                    console.log(`code/chef: Enhanced prompt from ${userMessage.length} to ${finalPrompt.length} chars`);
                }
            }
            // === END ENHANCEMENT ===
            
            let currentAgent = '';
            let sessionIdFromStream = sessionId;
            let fullResponse = '';  // Accumulate full response for parsing
            let isSuprevisorResponse = false;  // Track if we're in supervisor mode
            let chunkCount = 0;  // Track chunks received
            const BUFFER_CHUNKS = 3;  // Buffer first N chunks to detect supervisor responses

            // Create AbortController linked to VS Code CancellationToken
            const abortController = new AbortController();
            token.onCancellationRequested(() => {
                console.log('[ChatParticipant] User cancelled stream via CancellationToken');
                abortController.abort();
            });

            // Stream response token by token with cancellation support
            for await (const chunk of this.client.chatStream({
                message: finalPrompt,  // Use enhanced prompt
                session_id: sessionId,
                context: {
                    ...workspaceContext,
                    chat_references: chatReferences,  // NEW
                    copilot_model: copilotModel,      // NEW
                    prompt_enhanced: enhancePrompts,  // NEW
                    enhancement_error: enhancementError  // NEW
                },
                workspace_config: buildWorkspaceConfig()
            }, abortController.signal)) {
                // Check for cancellation (redundant with AbortController but safe)
                if (token.isCancellationRequested) {
                    stream.markdown('\n\n*Response cancelled*');
                    break;
                }

                switch (chunk.type) {
                    case 'content':
                        // Accumulate content for parsing
                        if (chunk.content) {
                            fullResponse += chunk.content;
                            chunkCount++;
                            
                            // Check if this is a supervisor routing response (look for metadata markers)
                            const hasSupervisorMarkers = fullResponse.includes('NEXT_AGENT:') || 
                                                        fullResponse.includes('REQUIRES_APPROVAL:') || 
                                                        fullResponse.includes('REASONING:');
                            
                            if (hasSupervisorMarkers) {
                                isSuprevisorResponse = true;
                            }
                            
                            // Buffer first few chunks to detect supervisor responses early
                            // After that, only stream if NOT a supervisor response
                            if (chunkCount > BUFFER_CHUNKS && !isSuprevisorResponse) {
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
                    sessionId: sessionIdFromStream,
                    promptEnhanced: enhancePrompts,
                    enhancementError
                } 
            };

        } catch (error: any) {
            // Handle cancellation separately from errors
            if (error.name === 'AbortError') {
                stream.markdown('\n\n_Stream cancelled by user_\n');
                return { 
                    metadata: { 
                        status: 'cancelled',
                        streaming: true 
                    } 
                };
            }
            
            // Fallback to non-streaming on error
            console.error('Streaming failed, error:', error.message);
            stream.markdown(`\n\n❌ **Streaming Error**: ${error.message}\n\n`);
            stream.markdown('*Tip: You can disable streaming in settings with `codechef.useStreaming: false`*\n');
            return { 
                errorDetails: { message: error.message } 
            };
        }
    }    /**
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

    /**
     * Handle /execute command: Submit task to orchestrator for Agent mode execution.
     * This bypasses conversational mode and directly creates a task with workflow execution.
     */
    private async handleExecuteCommand(
        userMessage: string,
        stream: vscode.ChatResponseStream,
        _token: vscode.CancellationToken
    ): Promise<vscode.ChatResult> {
        stream.progress('Analyzing workspace context...');

        try {
            // Extract workspace context
            const workspaceContext = await this.contextExtractor.extract();
            
            // Get session (not used for execute, but maintains consistency)
            const sessionId = this.sessionManager.getOrCreateSession({} as vscode.ChatContext);
            
            stream.progress('Submitting to code/chef orchestrator...');
            
            // Submit to orchestrator (Agent mode)
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
                console.log(`code/chef: Created Linear project ${response.linear_project.id}`);
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

            // Execute workflow automatically
            stream.progress('Executing workflow...');
            try {
                await this.client.execute(response.task_id);
                stream.markdown('\n✅ **Workflow execution started!**\n\n');
                stream.markdown(`Monitor progress: \`@chef /status ${response.task_id}\`\n\n`);
            } catch (executeError: any) {
                stream.markdown('\n⚠️ **Task planned but execution failed to start**\n\n');
                stream.markdown(`Error: ${executeError.message}\n\n`);
            }

            // Stream response
            return renderTaskSubmitted(response, stream);

        } catch (error: any) {
            renderError(error, stream);
            return { errorDetails: { message: error.message } };
        }
    }

    private async handleCommand(
        command: string,
        args: string,
        stream: vscode.ChatResponseStream,
        _token: vscode.CancellationToken
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
            
            case CHAT_COMMANDS.EXECUTE:
                return await this.handleExecuteCommand(args, stream, _token);
            
            default:
                stream.markdown(`Unknown command: ${command}\n\n`);
                stream.markdown('Available commands: status, approve, tools, workflow, workflows, execute\n');
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
