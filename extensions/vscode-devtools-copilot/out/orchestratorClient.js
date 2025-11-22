"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.OrchestratorClient = void 0;
const axios_1 = __importDefault(require("axios"));
class OrchestratorClient {
    constructor(baseUrl, timeout = 30000) {
        this.client = axios_1.default.create({
            baseURL: baseUrl,
            timeout,
            headers: { 'Content-Type': 'application/json' }
        });
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
}
exports.OrchestratorClient = OrchestratorClient;
//# sourceMappingURL=orchestratorClient.js.map