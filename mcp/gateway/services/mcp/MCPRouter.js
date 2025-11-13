import CircuitBreaker from 'opossum';
import { MCPRegistryService } from './MCPRegistry.js';
import { MCPClientManager } from './MCPClientManager.js';
/**
 * Latency histogram for tracking percentiles
 */
class LatencyHistogram {
    measurements = [];
    maxSize = 1000;
    record(latencyMs) {
        this.measurements.push(latencyMs);
        if (this.measurements.length > this.maxSize) {
            this.measurements.shift();
        }
    }
    getPercentile(p) {
        if (this.measurements.length === 0)
            return 0;
        const sorted = [...this.measurements].sort((a, b) => a - b);
        const index = Math.ceil((p / 100) * sorted.length) - 1;
        return sorted[Math.max(0, index)];
    }
    getStats() {
        return {
            p50: this.getPercentile(50),
            p95: this.getPercentile(95),
            p99: this.getPercentile(99),
            count: this.measurements.length
        };
    }
    reset() {
        this.measurements = [];
    }
}
/**
 * MCPRouter - Routes tool calls to appropriate MCP servers with opossum circuit breaking
 */
export class MCPRouter {
    registry;
    clientManager;
    circuitBreakers = new Map();
    latencyHistograms = new Map();
    constructor(registry, clientManager) {
        this.registry = registry || MCPRegistryService.getInstance();
        this.clientManager = clientManager || new MCPClientManager();
    }
    /**
     * List all available tools from all enabled servers
     */
    async listAllTools() {
        const enabledServersRecord = this.registry.getEnabledServers();
        const enabledServers = Object.entries(enabledServersRecord);
        const allTools = [];
        console.log(`[MCPRouter] Listing tools from ${enabledServers.length} enabled servers`);
        // Query tools from each enabled server in parallel
        const toolPromises = enabledServers.map(async ([serverName, config]) => {
            try {
                const breaker = this.getCircuitBreaker(serverName);
                if (breaker.opened) {
                    console.log(`[MCPRouter] Skipping ${serverName} (circuit open)`);
                    return [];
                }
                const tools = await this.clientManager.listTools(serverName, config);
                // Add server name to each tool
                return tools.map(tool => ({
                    ...tool,
                    server: serverName
                }));
            }
            catch (error) {
                console.error(`[MCPRouter] Failed to list tools from ${serverName}:`, error.message);
                return [];
            }
        });
        const toolArrays = await Promise.all(toolPromises);
        toolArrays.forEach(tools => allTools.push(...tools));
        console.log(`[MCPRouter] Found ${allTools.length} total tools`);
        return allTools;
    }
    /**
     * Refresh registry and merged catalog (hot-reload)
     */
    async refreshRegistryAndCatalog() {
        this.registry.reloadRegistry();
        // DockerCatalogSync refresh is handled by interval, but force refresh here too
        if (this.registry.dockerCatalogSync) {
            await this.registry.dockerCatalogSync.refresh();
            if (this.registry.refreshMergedServers) {
                this.registry.refreshMergedServers();
            }
        }
        console.log('[MCPRouter] Registry and catalog refreshed');
    }
    /**
     * Call a tool by routing to the appropriate server
     */
    async callTool(request) {
        const startTime = Date.now();
        try {
            // Determine which server to route to
            const serverName = await this.resolveServer(request.tool);
            if (!serverName) {
                throw new Error(`No server found for tool: ${request.tool}`);
            }
            // Get server configuration
            const config = this.registry.getServer(serverName);
            if (!config) {
                throw new Error(`Server configuration not found: ${serverName}`);
            }
            if (!config.enabled) {
                throw new Error(`Server ${serverName} is not enabled`);
            }
            console.log(`[MCPRouter] Routing tool ${request.tool} to server ${serverName}`);
            // Get circuit breaker and wrap call
            const breaker = this.getCircuitBreaker(serverName);
            const result = await breaker.fire(serverName, config, request.tool, request.args, { stream: request.stream });
            const duration = Date.now() - startTime;
            this.recordLatency(serverName, duration);
            return {
                result,
                server: serverName,
                duration
            };
        }
        catch (error) {
            const duration = Date.now() - startTime;
            console.error(`[MCPRouter] Tool call failed:`, error.message);
            return {
                result: null,
                server: 'unknown',
                duration,
                error: error.message
            };
        }
    }
    /**
     * Resolve which server should handle a tool
     * Uses capability-based pattern matching from registry
     */
    async resolveServer(toolName) {
        // Try pattern-based resolution first (e.g., "github:search" → "github")
        const patternMatch = this.registry.resolveServerByPattern(toolName);
        if (patternMatch) {
            console.log(`[MCPRouter] Resolved ${toolName} to ${patternMatch} via pattern matching`);
            return patternMatch;
        }
        // Fallback: query all enabled servers for the tool
        console.log(`[MCPRouter] Searching all servers for tool ${toolName}`);
        const enabledServersRecord = this.registry.getEnabledServers();
        const enabledServers = Object.entries(enabledServersRecord);
        for (const [serverName, config] of enabledServers) {
            try {
                const breaker = this.getCircuitBreaker(serverName);
                if (breaker.opened) {
                    continue;
                }
                const tools = await this.clientManager.listTools(serverName, config);
                const hasTooling = tools.some(t => t.name === toolName);
                if (hasTooling) {
                    console.log(`[MCPRouter] Found tool ${toolName} on server ${serverName}`);
                    return serverName;
                }
            }
            catch (error) {
                console.error(`[MCPRouter] Error checking ${serverName} for tool ${toolName}:`, error);
            }
        }
        console.error(`[MCPRouter] Tool ${toolName} not found on any enabled server`);
        return null;
    }
    /**
     * Get or create circuit breaker for a server with opossum
     */
    getCircuitBreaker(serverName) {
        let breaker = this.circuitBreakers.get(serverName);
        if (!breaker) {
            // Wrapper function for opossum
            const callFunction = async (server, config, tool, args, options) => {
                return this.clientManager.callTool(server, config, tool, args, options);
            };
            // Create opossum circuit breaker
            breaker = new CircuitBreaker(callFunction, {
                timeout: 30000, // 30s timeout per call
                errorThresholdPercentage: 50, // Open after 50% errors
                resetTimeout: 60000, // Try again after 60s
                rollingCountTimeout: 10000, // 10s rolling window
                rollingCountBuckets: 10, // 10 buckets in window
                name: serverName
            });
            // Event listeners for logging
            breaker.on('open', () => {
                console.log(`[CircuitBreaker] ${serverName} circuit OPENED`);
            });
            breaker.on('halfOpen', () => {
                console.log(`[CircuitBreaker] ${serverName} circuit HALF-OPEN`);
            });
            breaker.on('close', () => {
                console.log(`[CircuitBreaker] ${serverName} circuit CLOSED`);
            });
            breaker.on('success', (result, latencyMs) => {
                this.recordLatency(serverName, latencyMs);
            });
            breaker.on('failure', (error) => {
                console.error(`[CircuitBreaker] ${serverName} call failed:`, error.message);
            });
            breaker.on('timeout', () => {
                console.error(`[CircuitBreaker] ${serverName} call timed out`);
            });
            this.circuitBreakers.set(serverName, breaker);
        }
        return breaker;
    }
    /**
     * Record latency for histogram tracking
     */
    recordLatency(serverName, latencyMs) {
        let histogram = this.latencyHistograms.get(serverName);
        if (!histogram) {
            histogram = new LatencyHistogram();
            this.latencyHistograms.set(serverName, histogram);
        }
        histogram.record(latencyMs);
    }
    /**
     * Get circuit breaker stats for all servers
     */
    getCircuitBreakerStats() {
        const stats = {};
        this.circuitBreakers.forEach((breaker, serverName) => {
            const histogram = this.latencyHistograms.get(serverName);
            stats[serverName] = {
                state: breaker.opened ? 'OPEN' : breaker.halfOpen ? 'HALF_OPEN' : 'CLOSED',
                stats: breaker.stats,
                latency: histogram ? histogram.getStats() : { p50: 0, p95: 0, p99: 0, count: 0 }
            };
        });
        return stats;
    }
    /**
     * Reset circuit breaker for a specific server
     */
    resetCircuitBreaker(serverName) {
        const breaker = this.circuitBreakers.get(serverName);
        if (breaker) {
            breaker.close();
            const histogram = this.latencyHistograms.get(serverName);
            if (histogram) {
                histogram.reset();
            }
            console.log(`[MCPRouter] Reset circuit breaker for ${serverName}`);
        }
    }
    /**
     * Reset all circuit breakers
     */
    resetAllCircuitBreakers() {
        this.circuitBreakers.forEach((breaker, serverName) => {
            breaker.close();
            const histogram = this.latencyHistograms.get(serverName);
            if (histogram) {
                histogram.reset();
            }
        });
        console.log(`[MCPRouter] Reset all circuit breakers`);
    }
    /**
     * Cleanup connections
     */
    async shutdown() {
        console.log('[MCPRouter] Shutting down...');
        // Shutdown all circuit breakers
        this.circuitBreakers.forEach(breaker => breaker.shutdown());
        await this.clientManager.disconnectAll();
    }
}
// Singleton instance
export const mcpRouter = new MCPRouter(MCPRegistryService.getInstance());
//# sourceMappingURL=MCPRouter.js.map