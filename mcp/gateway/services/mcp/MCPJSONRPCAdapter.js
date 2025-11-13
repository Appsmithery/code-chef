import { getFetch } from './DockerCatalogSync.js';
/**
 * JSON-RPC HTTP Adapter for Docker MCP Gateway
 * Supports standard JSON-RPC 2.0 POST and streaming (SSE) responses
 */
export class MCPJSONRPCAdapter {
    config;
    connected = false;
    baseUrl;
    fetchFn = null;
    constructor(config) {
        if (config.type !== 'http') {
            throw new Error('MCPJSONRPCAdapter requires http server type');
        }
        if (!config.url) {
            throw new Error('MCPJSONRPCAdapter requires a base URL');
        }
        this.config = config;
        this.baseUrl = config.url.replace(/\/$/, '');
    }
    async connect() {
        this.fetchFn = await getFetch();
        // Optionally, check /health or / endpoint
        this.connected = true;
    }
    async disconnect() {
        this.connected = false;
    }
    async listTools() {
        if (!this.connected || !this.fetchFn)
            throw new Error('Not connected');
        // JSON-RPC: POST {"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}
        const response = await this.jsonRpcRequest('tools/list', {});
        return response.tools || [];
    }
    async callTool(toolName, args, options) {
        if (!this.connected || !this.fetchFn)
            throw new Error('Not connected');
        if (options?.stream) {
            // Streaming via SSE (Server-Sent Events)
            return this.jsonRpcStream('tools/call', { name: toolName, arguments: args });
        }
        else {
            // Standard JSON-RPC call
            return this.jsonRpcRequest('tools/call', { name: toolName, arguments: args });
        }
    }
    /**
     * Standard JSON-RPC 2.0 POST request
     */
    async jsonRpcRequest(method, params) {
        const body = {
            jsonrpc: '2.0',
            method,
            params,
            id: Date.now()
        };
        const res = await this.fetchFn(this.baseUrl + '/jsonrpc', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...this.config.headers
            },
            body: JSON.stringify(body)
        });
        if (!res.ok)
            throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (data.error)
            throw new Error(data.error.message || 'JSON-RPC error');
        return data.result;
    }
    /**
     * Streaming JSON-RPC call using SSE (Server-Sent Events)
     * Returns an async generator yielding streamed results
     */
    async *jsonRpcStream(method, params) {
        const body = {
            jsonrpc: '2.0',
            method,
            params,
            id: Date.now()
        };
        const fetchFn = this.fetchFn;
        const res = await fetchFn(this.baseUrl + '/jsonrpc/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Accept: 'text/event-stream',
                ...this.config.headers
            },
            body: JSON.stringify(body)
        });
        if (!res.ok || !res.body)
            throw new Error(`HTTP ${res.status}`);
        const reader = res.body.getReader();
        let buffer = '';
        while (true) {
            const { value, done } = await reader.read();
            if (done)
                break;
            buffer += new TextDecoder().decode(value);
            let idx;
            while ((idx = buffer.indexOf('\n\n')) !== -1) {
                const chunk = buffer.slice(0, idx).trim();
                buffer = buffer.slice(idx + 2);
                if (chunk) {
                    try {
                        const event = JSON.parse(chunk);
                        yield event;
                    }
                    catch { }
                }
            }
        }
    }
}
//# sourceMappingURL=MCPJSONRPCAdapter.js.map