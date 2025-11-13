import { MCPRegistryService } from './MCPRegistry.js';
import { MCPClientManager } from './MCPClientManager.js';
import { MCPTool, MCPToolCallRequest, MCPToolCallResponse } from './types.js';
/**
 * MCPRouter - Routes tool calls to appropriate MCP servers with opossum circuit breaking
 */
export declare class MCPRouter {
    private registry;
    private clientManager;
    private circuitBreakers;
    private latencyHistograms;
    constructor(registry?: MCPRegistryService, clientManager?: MCPClientManager);
    /**
     * List all available tools from all enabled servers
     */
    listAllTools(): Promise<MCPTool[]>;
    /**
     * Refresh registry and merged catalog (hot-reload)
     */
    refreshRegistryAndCatalog(): Promise<void>;
    /**
     * Call a tool by routing to the appropriate server
     */
    callTool(request: MCPToolCallRequest): Promise<MCPToolCallResponse>;
    /**
     * Resolve which server should handle a tool
     * Uses capability-based pattern matching from registry
     */
    private resolveServer;
    /**
     * Get or create circuit breaker for a server with opossum
     */
    private getCircuitBreaker;
    /**
     * Record latency for histogram tracking
     */
    private recordLatency;
    /**
     * Get circuit breaker stats for all servers
     */
    getCircuitBreakerStats(): Record<string, any>;
    /**
     * Reset circuit breaker for a specific server
     */
    resetCircuitBreaker(serverName: string): void;
    /**
     * Reset all circuit breakers
     */
    resetAllCircuitBreakers(): void;
    /**
     * Cleanup connections
     */
    shutdown(): Promise<void>;
}
export declare const mcpRouter: MCPRouter;
//# sourceMappingURL=MCPRouter.d.ts.map