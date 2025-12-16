import axios, { AxiosInstance } from 'axios';
import EventSource from 'eventsource';

export interface TaskRequest {
    description: string;
    priority: 'low' | 'medium' | 'high' | 'critical';
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
    context_refs?: string[] | null;
    created_at: string;
}

export interface TaskResponse {
    task_id: string;
    subtasks: SubTask[];
    status?: 'pending' | 'approval_pending' | 'in_progress' | 'completed' | 'failed';
    approval_request_id?: string;
    risk_level?: 'low' | 'medium' | 'high' | 'critical';
    routing_plan: {
        execution_order: string[];
        parallel_groups?: string[][];
        estimated_duration_minutes: number;
        tool_validation?: Record<string, any>;
    };
    guardrail_report?: any;
    workspace_context?: Record<string, any>;
    linear_project?: {
        id: string;
        name: string;
        url?: string;
    };
}

export interface TaskStatus {
    task_id: string;
    status: 'pending' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
    subtasks: SubTask[];
    total_subtasks: number;
    completed_subtasks: number;
    created_at: string;
    updated_at: string;
}

export interface ChatMessage {
    message: string;
    session_id: string;
    context?: Record<string, any>;
    workspace_config?: Record<string, any>;
}

export interface ChatReferences {
    files: string[];
    symbols: Array<{file: string; line: number; name?: string}>;
    strings: string[];
    count: number;
}

export interface ChatResponse {
    response: string;
    session_id: string;
    task_id?: string;
    requires_approval?: boolean;
    token_usage?: {
        prompt_tokens: number;
        completion_tokens: number;
        total_tokens: number;
        cost_usd?: number;
    };
}

/**
 * Stream chunk types from /chat/stream SSE endpoint
 */
export interface StreamChunk {
    type: 'content' | 'agent_complete' | 'tool_call' | 'done' | 'error';
    content?: string;
    agent?: string;
    tool?: string;
    session_id?: string;
    error?: string;
}

/**
 * Request body for streaming chat
 */
export interface ChatStreamRequest {
    message: string;
    session_id?: string;
    user_id?: string;
    context?: Record<string, any>;
    workspace_config?: Record<string, any>;
}

export interface SmartWorkflowRequest {
    task_description: string;
    explicit_workflow?: string;
    context?: Record<string, any>;
    dry_run?: boolean;
    confirm_threshold?: number;
}

export interface SmartWorkflowResponse {
    workflow_name: string;
    confidence: number;
    method: 'heuristic' | 'llm' | 'explicit' | 'default';
    reasoning: string;
    requires_confirmation: boolean;
    alternatives: Array<{
        workflow: string;
        confidence: number;
        source?: string;
    }>;
    context_variables: Record<string, any>;
    workflow_id?: string;
    execution_status?: string;
}

export interface WorkflowTemplate {
    template_name: string;
    name: string;
    description: string;
    version: string;
    required_context: string[];
    optional_context: string[];
    steps_count: number;
    agents_involved: string[];
    estimated_duration_minutes: number;
    risk_level: 'low' | 'medium' | 'high';
}

export interface WorkflowTemplatesResponse {
    templates: WorkflowTemplate[];
    count: number;
}

export interface OrchestratorClientConfig {
    baseUrl: string;
    timeout?: number;
    apiKey?: string;
}

export class OrchestratorClient {
    private client: AxiosInstance;
    private apiKey?: string;

    constructor(config: OrchestratorClientConfig);
    constructor(baseUrl: string, timeout?: number);
    constructor(configOrBaseUrl: OrchestratorClientConfig | string, timeout: number = 30000) {
        let baseUrl: string;
        let timeoutMs: number = timeout;
        
        if (typeof configOrBaseUrl === 'string') {
            baseUrl = configOrBaseUrl;
            this.apiKey = undefined;
        } else {
            baseUrl = configOrBaseUrl.baseUrl;
            timeoutMs = configOrBaseUrl.timeout ?? 30000;
            this.apiKey = configOrBaseUrl.apiKey;
        }

        const headers: Record<string, string> = { 'Content-Type': 'application/json' };
        if (this.apiKey) {
            headers['X-API-Key'] = this.apiKey;
        }

        this.client = axios.create({
            baseURL: baseUrl,
            timeout: timeoutMs,
            headers
        });
    }

    /**
     * Update the API key for subsequent requests
     */
    setApiKey(apiKey: string | undefined): void {
        this.apiKey = apiKey;
        if (apiKey) {
            this.client.defaults.headers.common['X-API-Key'] = apiKey;
        } else {
            delete this.client.defaults.headers.common['X-API-Key'];
        }
    }

    async orchestrate(request: TaskRequest): Promise<TaskResponse> {
        const response = await this.client.post('/orchestrate', request);
        return response.data;
    }

    async execute(taskId: string): Promise<any> {
        const response = await this.client.post(`/execute/${taskId}`);
        return response.data;
    }

    async checkStatus(taskId: string): Promise<TaskStatus> {
        const response = await this.client.get(`/tasks/${taskId}`);
        return response.data;
    }

    async chat(message: ChatMessage): Promise<ChatResponse> {
        const response = await this.client.post('/chat', message);
        return response.data;
    }

    /**
     * Stream chat response via Server-Sent Events (SSE)
     * Yields chunks as they arrive for real-time token-by-token display
     * 
     * @param request Chat stream request with message and optional session
     * @yields StreamChunk events from the server
     * 
     * @example
     * ```typescript
     * for await (const chunk of client.chatStream({ message: 'Hello' })) {
     *     if (chunk.type === 'content') {
     *         stream.markdown(chunk.content!);
     *     }
     * }
     * ```
     */
    async *chatStream(request: ChatStreamRequest): AsyncGenerator<StreamChunk> {
        const url = `${this.client.defaults.baseURL}/chat/stream`;
        
        // Use axios for Node.js compatibility (VS Code runs in Node.js, not browser)
        const response = await this.client.post(url, request, {
            responseType: 'stream',
            headers: {
                'Accept': 'text/event-stream',
            }
        });

        // Process SSE stream
        let buffer = '';
        
        for await (const chunk of response.data) {
            buffer += chunk.toString();
            
            // Process complete SSE messages (separated by double newlines)
            const messages = buffer.split('\n\n');
            buffer = messages.pop() || '';

            for (const message of messages) {
                if (message.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(message.slice(6));
                        yield data as StreamChunk;
                    } catch (parseError) {
                        console.warn('Failed to parse SSE message:', message);
                    }
                }
            }
        }

        // Process any remaining buffer
        if (buffer.startsWith('data: ')) {
            try {
                const data = JSON.parse(buffer.slice(6));
                yield data as StreamChunk;
            } catch {
                // Ignore incomplete final message
            }
        }
    }

    async approve(taskId: string, approvalId: string): Promise<void> {
        await this.client.post(`/approvals/${approvalId}/approve`, {
            task_id: taskId,
            approved: true
        });
    }

    async reject(taskId: string, approvalId: string, reason?: string): Promise<void> {
        await this.client.post(`/approvals/${approvalId}/reject`, {
            task_id: taskId,
            approved: false,
            reason
        });
    }

    async getPendingApprovals(): Promise<any[]> {
        const response = await this.client.get('/approvals/pending');
        return response.data;
    }

    async health(): Promise<{ status: string; service: string; version?: string }> {
        const response = await this.client.get('/health');
        return response.data;
    }

    async metrics(): Promise<string> {
        const response = await this.client.get('/metrics', {
            headers: { 'Accept': 'text/plain' }
        });
        return response.data;
    }

    /**
     * Smart workflow selection and execution
     * Uses heuristic matching and LLM fallback for intelligent workflow routing
     */
    async smartExecuteWorkflow(request: SmartWorkflowRequest): Promise<SmartWorkflowResponse> {
        const response = await this.client.post('/workflow/smart-execute', request);
        return response.data;
    }

    /**
     * Get available workflow templates with metadata
     */
    async getWorkflowTemplates(): Promise<WorkflowTemplatesResponse> {
        const response = await this.client.get('/workflow/templates');
        return response.data;
    }

    /**
     * Execute a specific workflow by template name
     */
    async executeWorkflow(templateName: string, context: Record<string, any>): Promise<any> {
        const response = await this.client.post('/workflow/execute', {
            template_name: templateName,
            context
        });
        return response.data;
    }

    /**
     * Get workflow execution status
     */
    async getWorkflowStatus(workflowId: string): Promise<any> {
        const response = await this.client.get(`/workflow/status/${workflowId}`);
        return response.data;
    }
}
