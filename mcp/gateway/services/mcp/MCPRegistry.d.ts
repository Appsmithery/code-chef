import { MCPRegistry, MCPServerConfig, MCPServerInfo } from './types';
import { DockerCatalogSyncOptions } from './DockerCatalogSync.js';
/**
 * MCP Server Registry Manager
 * Handles loading, validation, and querying of MCP server configurations
 */
export declare class MCPRegistryService {
    private static instance;
    private registry;
    private registryPath;
    private dockerCatalogSync;
    private mergedServers;
    private catalogOptions;
    private constructor();
    /**
     * Get singleton instance
     */
    static getInstance(registryPath?: string, catalogOptions?: DockerCatalogSyncOptions): MCPRegistryService;
    /**
     * Load the MCP registry from disk
     */
    loadRegistry(): MCPRegistry;
    /**
     * Get registry (loads if not already loaded)
     */
    getRegistry(): MCPRegistry;
    /**
     * Get merged servers (static + Docker catalog)
     */
    getMergedServers(): Record<string, MCPServerConfig>;
    /**
     * Get a specific server configuration
     */
    getServer(name: string): MCPServerConfig | undefined;
    /**
     * Get all enabled servers
     */
    getEnabledServers(): Record<string, MCPServerConfig>;
    /**
     * Get servers by capability
     */
    getServersByCapability(capability: string): string[];
    /**
     * Resolve server by tool pattern
     */
    resolveServerByPattern(toolName: string): string | undefined;
    /**
     * Get server info for UI/API responses
     */
    getServerInfo(): MCPServerInfo[];
    /**
     * Refresh merged servers (static + Docker catalog)
     */
    private refreshMergedServers;
    /**
     * Map Docker CatalogEntry to MCPServerConfig
     */
    private catalogEntryToServerConfig;
    /**
     * Validate registry structure
     */
    private validateRegistry;
    /**
     * Substitute environment variables in registry
     */
    private substituteEnvVars;
    /**
     * Substitute environment variables in a string
     * Supports: ${env:VAR_NAME} and ${env:VAR_NAME:default}
     */
    private substituteString;
    /**
     * Reload registry from disk (for hot-reloading)
     */
    reloadRegistry(): MCPRegistry;
}
//# sourceMappingURL=MCPRegistry.d.ts.map