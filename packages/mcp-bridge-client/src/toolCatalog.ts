import { MCPTool } from './client';

/**
 * Tool catalog with caching support
 */
export class ToolCatalog {
    private tools: MCPTool[] = [];
    private lastUpdate: number = 0;
    private ttl: number;

    constructor(ttl: number = 300000) {
        this.ttl = ttl;
    }

    /**
     * Set all tools in catalog
     */
    setAll(tools: MCPTool[]): void {
        this.tools = tools;
        this.lastUpdate = Date.now();
    }

    /**
     * Get all tools from catalog
     * Returns empty array if cache expired
     */
    getAll(): MCPTool[] {
        if (this.isExpired()) {
            return [];
        }
        return this.tools;
    }

    /**
     * Check if cache is expired
     */
    isExpired(): boolean {
        return Date.now() - this.lastUpdate > this.ttl;
    }

    /**
     * Clear catalog
     */
    clear(): void {
        this.tools = [];
        this.lastUpdate = 0;
    }

    /**
     * Get tools by server
     */
    getByServer(serverName: string): MCPTool[] {
        return this.tools.filter(t => t.server === serverName);
    }

    /**
     * Get tool by name
     */
    getByName(toolName: string): MCPTool | undefined {
        return this.tools.find(t => t.name === toolName);
    }

    /**
     * Get catalog statistics
     */
    getStats(): { total: number; servers: number; lastUpdate: number; expired: boolean } {
        const servers = new Set(this.tools.map(t => t.server));
        return {
            total: this.tools.length,
            servers: servers.size,
            lastUpdate: this.lastUpdate,
            expired: this.isExpired()
        };
    }
}
