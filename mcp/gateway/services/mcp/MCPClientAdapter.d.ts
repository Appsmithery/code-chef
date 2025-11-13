import { MCPServerConfig, MCPTool } from './types.js';
/**
 * Base adapter interface for MCP protocol communication
 */
export interface IMCPAdapter {
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    listTools(): Promise<MCPTool[]>;
    callTool(toolName: string, args: any): Promise<any>;
}
/**
 * HTTP adapter for MCP servers (GitHub Copilot, Supabase, Context7)
 */
export declare class MCPHTTPAdapter implements IMCPAdapter {
    private config;
    private client;
    private connected;
    constructor(config: MCPServerConfig);
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    listTools(): Promise<MCPTool[]>;
    callTool(toolName: string, args: any): Promise<any>;
    /**
     * Resolve environment variable placeholders like ${env:VAR_NAME:default}
     */
    private resolveEnvVar;
}
/**
 * Stdio adapter for local MCP servers (Playwright, Utility, Comet)
 */
export declare class MCPStdioAdapter implements IMCPAdapter {
    private config;
    private process?;
    private connected;
    private messageId;
    private pendingRequests;
    constructor(config: MCPServerConfig);
    connect(): Promise<void>;
    disconnect(): Promise<void>;
    listTools(): Promise<MCPTool[]>;
    callTool(toolName: string, args: any): Promise<any>;
    /**
     * Send JSON-RPC request to stdio process
     */
    private sendRequest;
    /**
     * Handle stdout data from stdio process
     */
    private handleStdout;
    /**
     * Resolve environment variable placeholders
     */
    private resolveEnvVar;
    /**
     * Resolve all environment variables in config object
     */
    private resolveEnvVars;
}
//# sourceMappingURL=MCPClientAdapter.d.ts.map