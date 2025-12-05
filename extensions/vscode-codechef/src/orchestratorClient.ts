import axios, { AxiosInstance } from 'axios';

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
}
