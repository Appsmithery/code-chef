import axios, { AxiosInstance } from 'axios';
import { ProgressiveLoader } from './progressiveLoader';
import { ToolCatalog } from './toolCatalog';

/**
 * MCP Tool definition
 */
export interface MCPTool {
    name: string;
    description: string;
    server: string;
    inputSchema?: Record<string, any>;
}

/**
 * Tool invocation request
 */
export interface ToolInvocationRequest {
    name: string;
    arguments: Record<string, any>;
}

/**
 * Tool invocation response
 */
export interface ToolInvocationResponse {
    success: boolean;
    result?: any;
    error?: string;
}

/**
 * Client configuration
 */
export interface MCPBridgeClientConfig {
    gatewayUrl?: string;
    timeout?: number;
    enableCaching?: boolean;
    cacheTTL?: number;
    progressiveLoading?: boolean;
}

/**
 * MCP Bridge Client
 * 
 * Lightweight client for accessing Dev-Tools MCP gateway from any workspace.
 * Provides access to 150+ tools across 18 MCP servers without cloning the repo.
 * 
 * @example
 * ```typescript
 * const client = new MCPBridgeClient({
 *   gatewayUrl: 'http://45.55.173.72:8000'
 * });
 * 
 * // List all tools
 * const tools = await client.listTools();
 * 
 * // Search tools by keyword
 * const memoryTools = await client.searchTools('memory');
 * 
 * // Invoke a tool
 * const result = await client.invokeTool('memory/read', { key: 'user-prefs' });
 * ```
 */
export class MCPBridgeClient {
    private client: AxiosInstance;
    private catalog: ToolCatalog;
    private loader: ProgressiveLoader;
    private config: Required<MCPBridgeClientConfig>;

    constructor(config: MCPBridgeClientConfig = {}) {
        // CHEF-118: Use orchestrator endpoint for tool discovery (port 8001)
        // The gateway (8000) handles Linear OAuth; orchestrator handles MCP tools
        this.config = {
            gatewayUrl: config.gatewayUrl || 'http://45.55.173.72:8001',
            timeout: config.timeout || 30000,
            enableCaching: config.enableCaching ?? true,
            cacheTTL: config.cacheTTL || 300000, // 5 minutes
            progressiveLoading: config.progressiveLoading ?? true
        };

        this.client = axios.create({
            baseURL: this.config.gatewayUrl,
            timeout: this.config.timeout,
            headers: {
                'Content-Type': 'application/json'
            }
        });

        this.catalog = new ToolCatalog(this.config.cacheTTL);
        this.loader = new ProgressiveLoader();
    }

    /**
     * List all available MCP tools
     * 
     * @param forceRefresh - Bypass cache and fetch fresh data
     * @returns Array of MCP tools
     */
    async listTools(forceRefresh = false): Promise<MCPTool[]> {
        if (!forceRefresh && this.config.enableCaching) {
            const cached = this.catalog.getAll();
            if (cached.length > 0) {
                return cached;
            }
        }

        const response = await this.client.get<{ tools: MCPTool[] }>('/tools');
        const tools = response.data.tools;
        
        if (this.config.enableCaching) {
            this.catalog.setAll(tools);
        }

        return tools;
    }

    /**
     * Get tools relevant to a specific task using progressive loading
     * 
     * @param taskDescription - Natural language task description
     * @returns Filtered array of relevant tools
     */
    async getToolsForTask(taskDescription: string): Promise<MCPTool[]> {
        if (!this.config.progressiveLoading) {
            return this.listTools();
        }

        const allTools = await this.listTools();
        return this.loader.filterByTask(taskDescription, allTools);
    }

    /**
     * Search tools by keyword, server, or description
     * 
     * @param query - Search query
     * @returns Matching tools
     */
    async searchTools(query: string): Promise<MCPTool[]> {
        const allTools = await this.listTools();
        const lowerQuery = query.toLowerCase();

        return allTools.filter(tool =>
            tool.name.toLowerCase().includes(lowerQuery) ||
            tool.description.toLowerCase().includes(lowerQuery) ||
            tool.server.toLowerCase().includes(lowerQuery)
        );
    }

    /**
     * Get tools from a specific MCP server
     * 
     * @param serverName - Name of MCP server
     * @returns Tools from specified server
     */
    async getToolsByServer(serverName: string): Promise<MCPTool[]> {
        const allTools = await this.listTools();
        return allTools.filter(tool => tool.server === serverName);
    }

    /**
     * Get list of available MCP servers
     * 
     * @returns Array of server names
     */
    async listServers(): Promise<string[]> {
        const tools = await this.listTools();
        const servers = new Set(tools.map(t => t.server));
        return Array.from(servers).sort();
    }

    /**
     * Invoke an MCP tool
     * 
     * @param toolName - Name of the tool (e.g., 'memory/read')
     * @param args - Tool arguments
     * @returns Tool invocation result
     */
    async invokeTool(toolName: string, args: Record<string, any> = {}): Promise<ToolInvocationResponse> {
        try {
            const response = await this.client.post<ToolInvocationResponse>(`/tools/${encodeURIComponent(toolName)}`, {
                arguments: args
            });

            return response.data;
        } catch (error: any) {
            return {
                success: false,
                error: error.response?.data?.message || error.message
            };
        }
    }

    /**
     * Check gateway health
     * 
     * @returns Health status
     */
    async health(): Promise<{ status: string; servers: number; tools: number }> {
        const response = await this.client.get('/health');
        return response.data;
    }

    /**
     * Clear tool cache
     */
    clearCache(): void {
        this.catalog.clear();
    }

    /**
     * Get current configuration
     */
    getConfig(): Readonly<Required<MCPBridgeClientConfig>> {
        return { ...this.config };
    }
}
