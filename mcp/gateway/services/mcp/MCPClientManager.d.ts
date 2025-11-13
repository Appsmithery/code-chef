import { MCPServerConfig } from './types.js';
import { MCPHTTPAdapter, MCPStdioAdapter } from './MCPClientAdapter.js';
import { MCPJSONRPCAdapter } from './MCPJSONRPCAdapter.js';
/**
 * Connection state for a single MCP server client
 */
interface MCPConnection {
    adapter: MCPHTTPAdapter | MCPStdioAdapter | MCPJSONRPCAdapter;
    serverName: string;
    connected: boolean;
    lastUsed: Date;
    failureCount: number;
    nextRetryAfter?: Date;
    inFlightCount: number;
    maxInFlight: number;
    queue: Array<{
        resolve: (value: any) => void;
        reject: (error: Error) => void;
        deadline: Date;
    }>;
}
/**
 * MCPClientManager - Manages lifecycle, connection pooling, and retries for MCP clients
 * Based on Dev-Tools ProspectPro MCP implementation v3.1 patterns
 */
export declare class MCPClientManager {
    private connections;
    private readonly maxRetries;
    private readonly baseRetryDelayMs;
    private readonly maxRetryDelayMs;
    private readonly connectionTimeoutMs;
    private readonly maxIdleTimeMs;
    constructor(options?: {
        maxRetries?: number;
        baseRetryDelayMs?: number;
        maxRetryDelayMs?: number;
        connectionTimeoutMs?: number;
        maxIdleTimeMs?: number;
    });
    /**
     * Get or create a connection to an MCP server
     */
    getConnection(serverName: string, config: MCPServerConfig): Promise<MCPConnection>;
    /**
     * Create a new connection with retry logic
     */
    private createConnection;
    /**
     * Calculate exponential backoff with jitter
     */
    private calculateBackoff;
    /**
     * Create appropriate adapter for server type
     */
    private createAdapter;
    /**
     * Call a tool on a connected server with queueing and deadline support
     */
    callTool(serverName: string, config: MCPServerConfig, toolName: string, args: any, options?: {
        stream?: boolean;
        timeoutMs?: number;
    }): Promise<any>;
    /**
     * Execute a tool call and manage queue processing
     */
    private executeToolCall;
    /**
     * Process queued requests with deadline expiration
     */
    private processQueue;
    /**
     * List tools available on a server
     */
    listTools(serverName: string, config: MCPServerConfig): Promise<any[]>;
    /**
     * Disconnect a specific server
     */
    disconnect(serverName: string, config?: MCPServerConfig): Promise<void>;
    /**
     * Disconnect all servers
     */
    disconnectAll(): Promise<void>;
    /**
     * Get connection statistics
     */
    getStats(): {
        total: number;
        connected: number;
        disconnected: number;
        inBackoff: number;
        details: Array<{
            key: string;
            serverName: string;
            protocol: string;
            url: string;
            connected: boolean;
            lastUsed: string;
            failureCount: number;
            nextRetryAfter?: string;
        }>;
    };
    /**
     * Start periodic cleanup of idle connections
     */
    private startIdleCleanup;
    /**
     * Utility: delay for specified milliseconds
     */
    private delay;
}
export declare const mcpClientManager: MCPClientManager;
export {};
//# sourceMappingURL=MCPClientManager.d.ts.map