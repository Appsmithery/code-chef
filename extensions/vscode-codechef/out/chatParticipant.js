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
const constants_1 = require("./constants");
const contextExtractor_1 = require("./contextExtractor");
const statusHandler_1 = require("./handlers/statusHandler");
const workflowHandler_1 = require("./handlers/workflowHandler");
const orchestratorClient_1 = require("./orchestratorClient");
const promptEnhancer_1 = require("./promptEnhancer");
const responseRenderer_1 = require("./renderers/responseRenderer");
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
        this.promptEnhancer = new promptEnhancer_1.PromptEnhancer();
        // Enable streaming by default, can be configured
        this.useStreaming = config.get('useStreaming', true);
        // Initialize handlers
        this.statusHandler = new statusHandler_1.StatusHandler(this.client, () => this.lastTaskId);
        this.workflowHandler = new workflowHandler_1.WorkflowHandler(this.client, this.contextExtractor);
        // Listen for configuration changes to update API key and streaming
        vscode.workspace.onDidChangeConfiguration(e => {
            if (e.affectsConfiguration('codechef.apiKey')) {
                const newApiKey = vscode.workspace.getConfiguration('codechef').get('apiKey');
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
    extractChatReferences(references) {
        const files = [];
        const symbols = [];
        const strings = [];
        for (const ref of references) {
            if (ref.value instanceof vscode.Uri) {
                // File reference (#file)
                files.push(ref.value.fsPath);
            }
            else if (ref.value instanceof vscode.Location) {
                // Symbol reference (function, class, etc.)
                symbols.push({
                    file: ref.value.uri.fsPath,
                    line: ref.value.range.start.line,
                    name: undefined // VS Code doesn't provide symbol name in Location
                });
            }
            else if (typeof ref.value === 'string') {
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
    extractModelMetadata(model) {
        return {
            vendor: model.vendor,
            family: model.family,
            version: model.version || 'unknown',
            name: model.name,
            maxInputTokens: model.maxInputTokens
            // Note: maxOutputTokens not available in VS Code API
        };
    }
    async handleChatRequest(request, context, stream, token) {
        const userMessage = request.prompt;
        // Handle commands
        if (request.command) {
            return await this.handleCommand(request.command, userMessage, stream, token);
        }
        // Use streaming for conversational chat
        if (this.useStreaming) {
            return await this.handleStreamingChat(userMessage, context, stream, token, request); // Pass request
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
            // Log Linear project creation
            if (response.linear_project?.id) {
                console.log(`code/chef: Created Linear project ${response.linear_project.id} under team`);
                (0, responseRenderer_1.renderLinearProjectCreated)(response.linear_project, stream);
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
            }
            catch (executeError) {
                stream.markdown('\n⚠️ **Task planned but execution failed to start**\n\n');
                stream.markdown(`Error: ${executeError.message}\n\n`);
                stream.markdown(`You can manually execute with: POST /execute/${response.task_id}\n\n`);
            }
            // Stream response
            return (0, responseRenderer_1.renderTaskSubmitted)(response, stream);
        }
        catch (error) {
            (0, responseRenderer_1.renderError)(error, stream);
            return { errorDetails: { message: error.message } };
        }
    }
    /**
     * Handle chat request with real-time SSE streaming.
     * Provides token-by-token response display for natural conversation flow.
     */
    async handleStreamingChat(userMessage, context, stream, token, request // ADD parameter
    ) {
        stream.progress('Connecting to code/chef...');
        try {
            // Extract workspace context
            const workspaceContext = await this.contextExtractor.extract();
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
            let enhancementError;
            if (enhancePrompts) {
                stream.progress('Enhancing task description with Copilot...');
                const template = config.get('enhancementTemplate', 'structured');
                const result = await this.promptEnhancer.enhance(userMessage, request.model, // Use user's selected Copilot model
                template, token);
                finalPrompt = result.enhanced;
                enhancementError = result.error;
                // Log enhancement for debugging
                if (enhancementError) {
                    console.warn(`code/chef: Prompt enhancement failed: ${enhancementError}`);
                }
                else {
                    console.log(`code/chef: Enhanced prompt from ${userMessage.length} to ${finalPrompt.length} chars`);
                }
            }
            // === END ENHANCEMENT ===
            let currentAgent = '';
            let sessionIdFromStream = sessionId;
            let fullResponse = ''; // Accumulate full response for parsing
            let isSuprevisorResponse = false; // Track if we're in supervisor mode
            // Stream response token by token
            for await (const chunk of this.client.chatStream({
                message: finalPrompt, // Use enhanced prompt
                session_id: sessionId,
                context: {
                    ...workspaceContext,
                    chat_references: chatReferences, // NEW
                    copilot_model: copilotModel, // NEW
                    prompt_enhanced: enhancePrompts, // NEW
                    enhancement_error: enhancementError // NEW
                },
                workspace_config: (0, settings_1.buildWorkspaceConfig)()
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
                    sessionId: sessionIdFromStream,
                    promptEnhanced: enhancePrompts,
                    enhancementError
                }
            };
        }
        catch (error) {
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
    extractReasoning(fullResponse) {
        const lines = fullResponse.split('\n');
        const reasoningLines = [];
        let inReasoning = false;
        for (const line of lines) {
            if (line.startsWith('REASONING:')) {
                // Extract reasoning content (skip the REASONING: prefix)
                const reasoningContent = line.substring('REASONING:'.length).trim();
                if (reasoningContent) {
                    reasoningLines.push(reasoningContent);
                }
                inReasoning = true;
            }
            else if (inReasoning && !line.startsWith('NEXT_AGENT:') && !line.startsWith('REQUIRES_APPROVAL:')) {
                // Continue collecting reasoning lines
                reasoningLines.push(line);
            }
            else if (line.startsWith('NEXT_AGENT:') || line.startsWith('REQUIRES_APPROVAL:')) {
                // Skip metadata lines
                inReasoning = false;
            }
        }
        return reasoningLines.join('\n').trim();
    }
    async handleCommand(command, args, stream, token) {
        switch (command) {
            case constants_1.CHAT_COMMANDS.STATUS:
                return await this.statusHandler.handleStatus(args, stream);
            case constants_1.CHAT_COMMANDS.APPROVE:
                return await this.statusHandler.handleApprove(args, stream);
            case constants_1.CHAT_COMMANDS.TOOLS:
                return await this.workflowHandler.handleTools(stream);
            case constants_1.CHAT_COMMANDS.WORKFLOW:
                return await this.workflowHandler.handleWorkflow(args, stream);
            case constants_1.CHAT_COMMANDS.WORKFLOWS:
                return await this.workflowHandler.handleWorkflowsList(stream);
            default:
                stream.markdown(`Unknown command: ${command}\n\n`);
                stream.markdown('Available commands: status, approve, tools, workflow, workflows\n');
                return {};
        }
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