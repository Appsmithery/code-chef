import axios, { AxiosInstance } from 'axios';
import { createParser, EventSourceMessage } from 'eventsource-parser';

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

        // Normalize URL: ensure it ends with /api
        baseUrl = this.normalizeBaseUrl(baseUrl);
        
        // Log final URL for diagnostics (mask sensitive data)
        const maskedUrl = baseUrl.replace(/\/\/([^@]+@)?/, '//***@');
        console.log(`[OrchestratorClient] Initializing with baseURL: ${maskedUrl}`);

        const headers: Record<string, string> = { 'Content-Type': 'application/json' };
        if (this.apiKey) {
            headers['X-API-Key'] = this.maskApiKey(this.apiKey);
            console.log(`[OrchestratorClient] API Key configured: ${this.maskApiKey(this.apiKey)}`);
        }

        this.client = axios.create({
            baseURL: baseUrl,
            timeout: timeoutMs,
            headers: {
                'Content-Type': 'application/json',
                ...(this.apiKey ? { 'X-API-Key': this.apiKey } : {})
            }
        });
        
        console.log(`[OrchestratorClient] ✅ Initialized with baseURL: ${baseUrl}`);
        console.log(`[OrchestratorClient] Full health check URL will be: ${baseUrl}/health`);
        console.log(`[OrchestratorClient] Full chat/stream URL will be: ${baseUrl}/chat/stream`);
    }

    /**
     * Normalize base URL to ensure it ends with /api
     */
    private normalizeBaseUrl(url: string): string {
        // Remove trailing slashes
        url = url.replace(/\/+$/, '');
        
        // Check if already ends with /api
        if (!url.endsWith('/api')) {
            url = `${url}/api`;
            console.log(`[OrchestratorClient] Auto-appended /api to URL`);
        }
        
        return url;
    }

    /**
     * Mask API key for safe logging
     */
    private maskApiKey(key: string): string {
        if (key.length <= 8) return '***';
        return `${key.substring(0, 4)}...${key.substring(key.length - 4)}`;
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
     * Retry helper with exponential backoff for transient errors.
     * Handles rate limits (429), service unavailable (503), and network errors.
     */
    private async retryWithBackoff<T>(
        operation: () => Promise<T>,
        maxRetries: number = 3,
        initialDelay: number = 1000,
        url?: string
    ): Promise<T> {
        let lastError: Error;
        
        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                const startTime = Date.now();
                const result = await operation();
                const duration = Date.now() - startTime;
                console.log(`[OrchestratorClient] Request succeeded in ${duration}ms (attempt ${attempt + 1}/${maxRetries + 1})`);
                return result;
            } catch (error: any) {
                lastError = error;
                
                // Log detailed error information
                const status = error.response?.status || 'NO_RESPONSE';
                const statusText = error.response?.statusText || error.code || 'UNKNOWN';
                console.error(`[OrchestratorClient] ❌ Request failed (attempt ${attempt + 1}/${maxRetries + 1}): ${status} ${statusText}`);
                if (url) {
                    console.error(`[OrchestratorClient] Failed URL: ${url}`);
                }
                if (error.response?.data) {
                    console.error(`[OrchestratorClient] Response data:`, error.response.data);
                }
                console.error(`[OrchestratorClient] Full error:`, {
                    message: error.message,
                    config: {
                        method: error.config?.method,
                        url: error.config?.url,
                        baseURL: error.config?.baseURL,
                        fullURL: error.config?.baseURL + error.config?.url
                    }
                });
                
                // Only retry on transient errors
                const isRetryable = 
                    error.response?.status === 429 || // Rate limit
                    error.response?.status === 503 || // Service unavailable
                    error.code === 'ECONNRESET' ||    // Connection reset
                    error.code === 'ETIMEDOUT';        // Timeout
                
                if (!isRetryable) {
                    console.error(`[OrchestratorClient] Non-retryable error: ${status}`);
                    throw error;
                }
                
                if (attempt === maxRetries) {
                    console.error(`[OrchestratorClient] Max retries exhausted`);
                    throw error;
                }
                
                // Exponential backoff: 1s, 2s, 4s
                const delay = initialDelay * Math.pow(2, attempt);
                console.log(`[OrchestratorClient] Retrying request after ${delay}ms (attempt ${attempt + 1}/${maxRetries})...`);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
        
        throw lastError!;
    }

    /**
     * Stream chat response via Server-Sent Events (SSE).
     * Provides real-time token-by-token response for interactive conversations.
     * 
     * Uses eventsource-parser for robust SSE parsing with automatic:
     * - Comment line handling (: keepalive)
     * - [DONE] signal detection
     * - Multi-line event parsing
     * - Event ID and retry field support
     * 
     * @param request - Chat stream request with message and context
     * @param signal - Optional AbortSignal for cancellation support
     * @returns AsyncGenerator yielding StreamChunk events
     * 
     * @example
     * ```typescript
     * const abortController = new AbortController();
     * for await (const chunk of client.chatStream({ message: 'Hello' }, abortController.signal)) {
     *     if (chunk.type === 'content') {
     *         stream.markdown(chunk.content!);
     *     }
     * }
     * ```
     */
    async *chatStream(
        request: ChatStreamRequest,
        signal?: AbortSignal
    ): AsyncGenerator<StreamChunk> {
        const url = `${this.client.defaults.baseURL}/chat/stream`;
        console.log(`[OrchestratorClient] 🚀 Starting chat stream`);
        console.log(`[OrchestratorClient] BaseURL: ${this.client.defaults.baseURL}`);
        console.log(`[OrchestratorClient] Full streaming URL: ${url}`);
        console.log(`[OrchestratorClient] Request payload:`, JSON.stringify(request, null, 2));
        
        // LangSmith tracing metadata
        const sessionStartTime = Date.now();
        let chunkCount = 0;
        let errorCount = 0;
        let firstChunkTime: number | null = null;
        
        try {
            // Retry wrapper for transient errors (429, 503)
            console.log(`[OrchestratorClient] Initiating POST request with retry logic...`);
            const response = await this.retryWithBackoff(async () => {
                return await this.client.post(url, request, {
                    responseType: 'stream',
                    headers: {
                        'Accept': 'text/event-stream',
                    },
                    signal // Pass AbortSignal for cancellation
                });
            }, 3, 1000, url); // Pass url for logging

            // Track time to first byte (TTFB)
            firstChunkTime = Date.now();
            const ttfb = firstChunkTime - sessionStartTime;
            console.log(`[Streaming] TTFB: ${ttfb}ms`);

            // Use eventsource-parser for robust SSE parsing
            const chunks: StreamChunk[] = [];
            let streamComplete = false;

            const parser = createParser({
                onEvent: (event: EventSourceMessage) => {
                    // Handle [DONE] terminal signal
                    if (event.data === '[DONE]') {
                        console.log('[Streaming] Received [DONE] signal');
                        streamComplete = true;
                        return;
                    }

                    try {
                        const chunk = JSON.parse(event.data);
                        
                        // Check for mid-stream errors
                        if ('error' in chunk && chunk.error) {
                            errorCount++;
                            const errorMessage = typeof chunk.error === 'string' 
                                ? chunk.error 
                                : (chunk.error.message || JSON.stringify(chunk.error));
                            throw new Error(`Stream error: ${errorMessage}`);
                        }
                        
                        chunks.push(chunk as StreamChunk);
                        chunkCount++;
                    } catch (parseError) {
                        console.error('[Streaming] Parse error:', parseError);
                        if (parseError instanceof Error && parseError.message.startsWith('Stream error:')) {
                            throw parseError;
                        }
                    }
                },
                onComment: (comment: string) => {
                    // Log keepalive comments for debugging
                    console.log(`[Streaming] Keepalive: ${comment}`);
                },
                onError: (error) => {
                    console.error('[Streaming] Parser error:', error);
                }
            });

            // Stream processing with cancellation support
            for await (const data of response.data) {
                // Check for cancellation
                if (signal?.aborted) {
                    console.log('[Streaming] Cancelled by user');
                    throw new DOMException('Stream cancelled by user', 'AbortError');
                }

                const text = data.toString();
                parser.feed(text);

                // Yield accumulated chunks
                while (chunks.length > 0) {
                    yield chunks.shift()!;
                }

                // Check if stream completed
                if (streamComplete) {
                    break;
                }
            }

            // Yield any remaining chunks
            while (chunks.length > 0) {
                yield chunks.shift()!;
            }

        } catch (error: any) {
            // Track error in metrics
            errorCount++;
            
            // Re-throw with context
            if (error.name === 'AbortError') {
                console.log('[Streaming] User cancelled stream');
            } else {
                console.error('[Streaming] Error:', error.message);
            }
            throw error;
            
        } finally {
            // LangSmith trace metadata
            const duration = Date.now() - sessionStartTime;
            const ttfb = firstChunkTime ? firstChunkTime - sessionStartTime : null;
            
            const traceMetadata = {
                trace_type: 'streaming_session',
                session_id: request.session_id,
                duration_ms: duration,
                ttfb_ms: ttfb,
                chunk_count: chunkCount,
                error_count: errorCount,
                cancelled: signal?.aborted || false,
                avg_chunk_time_ms: chunkCount > 0 ? duration / chunkCount : null
            };
            
            console.log('[Streaming] Session metrics:', traceMetadata);
            
            // TODO: Send to LangSmith when tracing SDK is available in extension context
            // For now, metrics are logged to console for debugging
            // Future: await langsmith.trace('streaming_session', traceMetadata);
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
