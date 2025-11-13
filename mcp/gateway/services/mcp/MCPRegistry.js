import fs from 'fs';
import path from 'path';
/**
 * MCP Server Registry Manager
 * Handles loading, validation, and querying of MCP server configurations
 */
export class MCPRegistryService {
    static instance = null;
    registry = null;
    registryPath;
    dockerCatalogSync = null;
    mergedServers = {};
    catalogOptions;
    constructor(registryPath, catalogOptions) {
        this.registryPath = registryPath || process.env.MCP_REGISTRY_PATH || './config/mcp-registry.json';
        this.catalogOptions = catalogOptions || {
            gatewayUrl: process.env.DOCKER_MCP_CATALOG_URL || 'http://localhost:8080/catalog',
            refreshIntervalMs: 60000
        };
        // DockerCatalogSync is now disabled - we use Docker MCP Gateway (MCP_DOCKER) as stdio server instead
        // The gateway handles catalog internally and provides tools via stdio protocol
        // Initialize DockerCatalogSync with error handling
        // try {
        //     this.dockerCatalogSync = new DockerCatalogSync(this.catalogOptions);
        //     this.dockerCatalogSync.start().then(() => {
        //         this.refreshMergedServers();
        //     }).catch((err) => {
        //         console.error('[MCPRegistry] DockerCatalogSync start failed:', err.message);
        //         // Continue with static registry only
        //     });
        // } catch (err) {
        //     console.error('[MCPRegistry] Failed to initialize DockerCatalogSync:', err);
        //     // Continue without DockerCatalogSync
        // }
        // Periodically refresh merged servers
        setInterval(() => {
            try {
                this.refreshMergedServers();
            }
            catch (err) {
                console.error('[MCPRegistry] Error refreshing merged servers:', err);
            }
        }, this.catalogOptions.refreshIntervalMs || 60000);
    }
    /**
     * Get singleton instance
     */
    static getInstance(registryPath, catalogOptions) {
        if (!MCPRegistryService.instance) {
            MCPRegistryService.instance = new MCPRegistryService(registryPath, catalogOptions);
        }
        return MCPRegistryService.instance;
    }
    /**
     * Load the MCP registry from disk
     */
    loadRegistry() {
        try {
            const absolutePath = path.resolve(this.registryPath);
            const content = fs.readFileSync(absolutePath, 'utf-8');
            const registry = JSON.parse(content);
            // Validate registry structure
            this.validateRegistry(registry);
            // Substitute environment variables
            this.registry = this.substituteEnvVars(registry);
            this.refreshMergedServers();
            console.log(`[MCPRegistry] Loaded registry v${this.registry.version} with ${Object.keys(this.registry.servers).length} servers`);
            return this.registry;
        }
        catch (error) {
            console.error('[MCPRegistry] Failed to load registry:', error);
            throw new Error(`Failed to load MCP registry from ${this.registryPath}: ${error.message}`);
        }
    }
    /**
     * Get registry (loads if not already loaded)
     */
    getRegistry() {
        if (!this.registry) {
            return this.loadRegistry();
        }
        return this.registry;
    }
    /**
     * Get merged servers (static + Docker catalog)
     */
    getMergedServers() {
        return this.mergedServers;
    }
    /**
     * Get a specific server configuration
     */
    getServer(name) {
        return this.mergedServers[name];
    }
    /**
     * Get all enabled servers
     */
    getEnabledServers() {
        return Object.entries(this.mergedServers)
            .filter(([_, config]) => config.enabled)
            .reduce((acc, [name, config]) => ({ ...acc, [name]: config }), {});
    }
    /**
     * Get servers by capability
     */
    getServersByCapability(capability) {
        return Object.entries(this.mergedServers)
            .filter(([_, config]) => config.enabled && config.capabilities.includes(capability))
            .map(([name]) => name);
    }
    /**
     * Resolve server by tool pattern
     */
    resolveServerByPattern(toolName) {
        const registry = this.getRegistry();
        if (!registry.routing?.capability_patterns) {
            return undefined;
        }
        // Check exact matches first
        for (const [pattern, serverName] of Object.entries(registry.routing.capability_patterns)) {
            if (pattern.endsWith(':*')) {
                const prefix = pattern.slice(0, -2);
                if (toolName.startsWith(prefix + ':')) {
                    return serverName;
                }
            }
            else if (pattern === toolName) {
                return serverName;
            }
        }
        return registry.routing.default_server;
    }
    /**
     * Get server info for UI/API responses
     */
    getServerInfo() {
        return Object.entries(this.mergedServers).map(([name, config]) => ({
            name,
            type: config.type,
            enabled: config.enabled,
            capabilities: config.capabilities,
            description: config.description,
        }));
    }
    /**
     * Refresh merged servers (static + Docker catalog)
     */
    refreshMergedServers() {
        try {
            // Start with static servers from registry
            const staticServers = this.registry ? { ...this.registry.servers } : {};
            // Merge in Docker catalog entries
            if (this.dockerCatalogSync) {
                const catalog = this.dockerCatalogSync.getCatalog();
                for (const entry of catalog) {
                    // If a static server with the same name exists, skip (custom overlay wins)
                    if (staticServers[entry.name])
                        continue;
                    // Map CatalogEntry to MCPServerConfig
                    staticServers[entry.name] = this.catalogEntryToServerConfig(entry);
                }
            }
            this.mergedServers = staticServers;
        }
        catch (err) {
            console.error('[MCPRegistry] Error in refreshMergedServers:', err);
            // Keep existing merged servers on error
        }
    }
    /**
     * Map Docker CatalogEntry to MCPServerConfig
     */
    catalogEntryToServerConfig(entry) {
        // Map Docker catalog fields to MCPServerConfig fields
        return {
            type: entry.type === 'jsonrpc' ? 'http' : entry.type,
            protocol: entry.type === 'jsonrpc' ? 'jsonrpc' : 'rest',
            package: entry.package,
            url: entry.url,
            enabled: true,
            capabilities: entry.capabilities || [],
            health_check_url: entry.health_check_url || null,
            startup_timeout_ms: entry.startup_timeout_ms || 5000,
            response_time_p95_target_ms: entry.response_time_p95_target_ms || 600,
            description: entry.description || entry.name,
        };
    }
    /**
     * Validate registry structure
     */
    validateRegistry(registry) {
        if (!registry.version) {
            throw new Error('Registry missing version field');
        }
        if (!registry.servers || typeof registry.servers !== 'object') {
            throw new Error('Registry missing or invalid servers field');
        }
        for (const [name, config] of Object.entries(registry.servers)) {
            const serverConfig = config;
            if (!serverConfig.type || !['http', 'stdio'].includes(serverConfig.type)) {
                throw new Error(`Server ${name} has invalid type: ${serverConfig.type}`);
            }
            if (serverConfig.type === 'http' && !serverConfig.url) {
                throw new Error(`HTTP server ${name} missing url field`);
            }
            if (serverConfig.type === 'stdio') {
                // Support both new `command`/`args` format and legacy `invocation`/`script_path` format
                if (!serverConfig.command && !serverConfig.invocation) {
                    throw new Error(`stdio server ${name} missing command or invocation field`);
                }
            }
            if (!Array.isArray(serverConfig.capabilities)) {
                throw new Error(`Server ${name} missing or invalid capabilities field`);
            }
        }
    }
    /**
     * Substitute environment variables in registry
     */
    substituteEnvVars(registry) {
        const cloned = JSON.parse(JSON.stringify(registry));
        for (const [name, config] of Object.entries(cloned.servers)) {
            // Substitute in URL
            if (config.url) {
                config.url = this.substituteString(config.url);
            }
            // Substitute in script_path
            if (config.script_path) {
                config.script_path = this.substituteString(config.script_path);
            }
            // Substitute in env vars
            if (config.env) {
                for (const [key, value] of Object.entries(config.env)) {
                    config.env[key] = this.substituteString(value);
                }
            }
            // Substitute in headers
            if (config.headers) {
                for (const [key, value] of Object.entries(config.headers)) {
                    config.headers[key] = this.substituteString(value);
                }
            }
            // Substitute in health_check_url
            if (config.health_check_url) {
                config.health_check_url = this.substituteString(config.health_check_url);
            }
        }
        return cloned;
    }
    /**
     * Substitute environment variables in a string
     * Supports: ${env:VAR_NAME} and ${env:VAR_NAME:default}
     */
    substituteString(str) {
        return str.replace(/\$\{env:([^:}]+)(?::([^}]+))?\}/g, (match, varName, defaultValue) => {
            const value = process.env[varName];
            if (value !== undefined) {
                return value;
            }
            if (defaultValue !== undefined) {
                return defaultValue;
            }
            console.warn(`[MCPRegistry] Environment variable ${varName} not found, using original value`);
            return match;
        });
    }
    /**
     * Reload registry from disk (for hot-reloading)
     */
    reloadRegistry() {
        this.registry = null;
        return this.loadRegistry();
    }
}
//# sourceMappingURL=MCPRegistry.js.map