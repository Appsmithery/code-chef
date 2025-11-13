import { MCPServerConfig, MCPTool } from './types.js';
/**
 * JSON-RPC HTTP Adapter for Docker MCP Gateway
 * Supports standard JSON-RPC 2.0 POST and streaming (SSE) responses
 */
export declare class MCPJSONRPCAdapter {
    private config;
    private connected;
    private baseUrl;
    private fetchFn;
    constructor(config: MCPServerConfig);
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    listTools(): Promise<MCPTool[]>;
    callTool(toolName: string, args: any, options?: {
        stream?: boolean;
    }): Promise<any>;
    /**
     * Standard JSON-RPC 2.0 POST request
     */
    private jsonRpcRequest;
    /**
     * Streaming JSON-RPC call using SSE (Server-Sent Events)
     * Returns an async generator yielding streamed results
     */
    private jsonRpcStream;
}
//# sourceMappingURL=MCPJSONRPCAdapter.d.ts.map