"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.OrchestratorClient = void 0;
const axios_1 = __importDefault(require("axios"));
class OrchestratorClient {
    constructor(configOrBaseUrl, timeout = 30000) {
        let baseUrl;
        let timeoutMs = timeout;
        if (typeof configOrBaseUrl === 'string') {
            baseUrl = configOrBaseUrl;
            this.apiKey = undefined;
        }
        else {
            baseUrl = configOrBaseUrl.baseUrl;
            timeoutMs = configOrBaseUrl.timeout ?? 30000;
            this.apiKey = configOrBaseUrl.apiKey;
        }
        const headers = { 'Content-Type': 'application/json' };
        if (this.apiKey) {
            headers['X-API-Key'] = this.apiKey;
        }
        this.client = axios_1.default.create({
            baseURL: baseUrl,
            timeout: timeoutMs,
            headers
        });
    }
    /**
     * Update the API key for subsequent requests
     */
    setApiKey(apiKey) {
        this.apiKey = apiKey;
        if (apiKey) {
            this.client.defaults.headers.common['X-API-Key'] = apiKey;
        }
        else {
            delete this.client.defaults.headers.common['X-API-Key'];
        }
    }
    async orchestrate(request) {
        const response = await this.client.post('/orchestrate', request);
        return response.data;
    }
    async execute(taskId) {
        const response = await this.client.post(`/execute/${taskId}`);
        return response.data;
    }
    async checkStatus(taskId) {
        const response = await this.client.get(`/tasks/${taskId}`);
        return response.data;
    }
    async chat(message) {
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
    async *chatStream(request) {
        const url = `${this.client.defaults.baseURL}/chat/stream`;
        const headers = {
            'Content-Type': 'application/json',
        };
        if (this.apiKey) {
            headers['X-API-Key'] = this.apiKey;
        }
        const response = await fetch(url, {
            method: 'POST',
            headers,
            body: JSON.stringify(request),
        });
        if (!response.ok) {
            throw new Error(`Stream failed: ${response.status} ${response.statusText}`);
        }
        if (!response.body) {
            throw new Error('No response body for streaming');
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done)
                    break;
                buffer += decoder.decode(value, { stream: true });
                // Process complete SSE messages (separated by double newlines)
                const messages = buffer.split('\n\n');
                buffer = messages.pop() || '';
                for (const message of messages) {
                    if (message.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(message.slice(6));
                            yield data;
                        }
                        catch (parseError) {
                            console.warn('Failed to parse SSE message:', message);
                        }
                    }
                }
            }
            // Process any remaining buffer
            if (buffer.startsWith('data: ')) {
                try {
                    const data = JSON.parse(buffer.slice(6));
                    yield data;
                }
                catch {
                    // Ignore incomplete final message
                }
            }
        }
        finally {
            reader.releaseLock();
        }
    }
    async approve(taskId, approvalId) {
        await this.client.post(`/approvals/${approvalId}/approve`, {
            task_id: taskId,
            approved: true
        });
    }
    async reject(taskId, approvalId, reason) {
        await this.client.post(`/approvals/${approvalId}/reject`, {
            task_id: taskId,
            approved: false,
            reason
        });
    }
    async getPendingApprovals() {
        const response = await this.client.get('/approvals/pending');
        return response.data;
    }
    async health() {
        const response = await this.client.get('/health');
        return response.data;
    }
    async metrics() {
        const response = await this.client.get('/metrics', {
            headers: { 'Accept': 'text/plain' }
        });
        return response.data;
    }
    /**
     * Smart workflow selection and execution
     * Uses heuristic matching and LLM fallback for intelligent workflow routing
     */
    async smartExecuteWorkflow(request) {
        const response = await this.client.post('/workflow/smart-execute', request);
        return response.data;
    }
    /**
     * Get available workflow templates with metadata
     */
    async getWorkflowTemplates() {
        const response = await this.client.get('/workflow/templates');
        return response.data;
    }
    /**
     * Execute a specific workflow by template name
     */
    async executeWorkflow(templateName, context) {
        const response = await this.client.post('/workflow/execute', {
            template_name: templateName,
            context
        });
        return response.data;
    }
    /**
     * Get workflow execution status
     */
    async getWorkflowStatus(workflowId) {
        const response = await this.client.get(`/workflow/status/${workflowId}`);
        return response.data;
    }
}
exports.OrchestratorClient = OrchestratorClient;
//# sourceMappingURL=orchestratorClient.js.map