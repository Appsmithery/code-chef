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