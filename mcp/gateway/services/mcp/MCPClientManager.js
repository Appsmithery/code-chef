import { MCPHTTPAdapter, MCPStdioAdapter } from './MCPClientAdapter.js';
import { MCPJSONRPCAdapter } from './MCPJSONRPCAdapter.js';
/**
 * Generate a composite key for a connection based on serverName and config
 * Includes protocol, url, invocation, script_path, arguments, env, headers
 */
function getConnectionKey(serverName, config) {
    // Only include fields that affect connection identity
    const keyObj = {
        serverName,
        protocol: config.protocol || 'rest',
        url: config.url || '',
        invocation: config.invocation || '',
        script_path: config.script_path || '',
        arguments: config.arguments ? JSON.stringify(config.arguments) : '',
        env: config.env ? JSON.stringify(config.env) : '',
        headers: config.headers ? JSON.stringify(config.headers) : ''
    };
    return JSON.stringify(keyObj);
}
/**
 * MCPClientManager - Manages lifecycle, connection pooling, and retries for MCP clients
 * Based on Dev-Tools ProspectPro MCP implementation v3.1 patterns
 */
export class MCPClientManager {
    connections = new Map();
    maxRetries;
    baseRetryDelayMs;
    maxRetryDelayMs;
    connectionTimeoutMs;
    maxIdleTimeMs;
    constructor(options) {
        this.maxRetries = options?.maxRetries ?? parseInt(process.env.MCP_MAX_RETRIES || '3');
        this.baseRetryDelayMs = options?.baseRetryDelayMs ?? 1000;
        this.maxRetryDelayMs = options?.maxRetryDelayMs ?? 30000;
        this.connectionTimeoutMs = options?.connectionTimeoutMs ?? parseInt(process.env.MCP_CONNECTION_TIMEOUT_MS || '10000');
        this.maxIdleTimeMs = options?.maxIdleTimeMs ?? 300000; // 5 minutes
        // Start idle connection cleanup
        this.startIdleCleanup();
    }
    /**
     * Get or create a connection to an MCP server
     */
    async getConnection(serverName, config) {
        const key = getConnectionKey(serverName, config);
        const existing = this.connections.get(key);
        // Check if existing connection is usable
        if (existing) {
            // Check if connection is in retry backoff period
            if (existing.nextRetryAfter && existing.nextRetryAfter > new Date()) {
                throw new Error(`Server ${serverName} is in backoff period until ${existing.nextRetryAfter.toISOString()}`);
            }
            // If connected and not stale, return existing
            if (existing.connected) {
                existing.lastUsed = new Date();
                return existing;
            }
        }
        // Create new connection or reconnect
        return await this.createConnection(serverName, config);
    }
    /**
     * Create a new connection with retry logic
     */
    async createConnection(serverName, config) {
        const key = getConnectionKey(serverName, config);
        const existing = this.connections.get(key);
        let failureCount = existing?.failureCount ?? 0;
        for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
            try {
                console.log(`[MCPClientManager] Connecting to ${serverName} (attempt ${attempt + 1}/${this.maxRetries + 1})`);
                // Create adapter based on server type
                const adapter = this.createAdapter(config);
                // Attempt connection with timeout
                const connectPromise = adapter.connect();
                const timeoutPromise = new Promise((_, reject) => setTimeout(() => reject(new Error(`Connection timeout after ${this.connectionTimeoutMs}ms`)), this.connectionTimeoutMs));
                await Promise.race([connectPromise, timeoutPromise]);
                // Success! Reset failure count and store connection
                const maxInFlight = config.max_in_flight || 10;
                const connection = {
                    adapter,
                    serverName,
                    connected: true,
                    lastUsed: new Date(),
                    failureCount: 0,
                    inFlightCount: 0,
                    maxInFlight,
                    queue: []
                };
                this.connections.set(key, connection);
                console.log(`[MCPClientManager] Successfully connected to ${serverName}`);
                return connection;
            }
            catch (error) {
                failureCount++;
                console.error(`[MCPClientManager] Connection attempt ${attempt + 1} failed for ${serverName}:`, error);
                // If not last attempt, apply exponential backoff with jitter
                if (attempt < this.maxRetries) {
                    const backoffMs = this.calculateBackoff(attempt);
                    console.log(`[MCPClientManager] Retrying ${serverName} in ${backoffMs}ms`);
                    await this.delay(backoffMs);
                }
            }
        }
        // All retries exhausted - set backoff period
        const backoffMs = this.calculateBackoff(failureCount);
        const nextRetryAfter = new Date(Date.now() + backoffMs);
        const failedConnection = {
            adapter: this.createAdapter(config), // Create placeholder adapter
            serverName,
            connected: false,
            lastUsed: new Date(),
            failureCount,
            nextRetryAfter,
            inFlightCount: 0,
            maxInFlight: config.max_in_flight || 10,
            queue: []
        };
        this.connections.set(key, failedConnection);
        throw new Error(`Failed to connect to ${serverName} after ${this.maxRetries + 1} attempts. Next retry after ${nextRetryAfter.toISOString()}`);
    }
    /**
     * Calculate exponential backoff with jitter
     */
    calculateBackoff(attempt) {
        const exponentialDelay = Math.min(this.baseRetryDelayMs * Math.pow(2, attempt), this.maxRetryDelayMs);
        // Add jitter (±25%)
        const jitter = exponentialDelay * 0.25 * (Math.random() * 2 - 1);
        return Math.floor(exponentialDelay + jitter);
    }
    /**
     * Create appropriate adapter for server type
     */
    createAdapter(config) {
        if (config.type === 'http') {
            if (config.protocol === 'jsonrpc') {
                return new MCPJSONRPCAdapter(config);
            }
            else {
                return new MCPHTTPAdapter(config);
            }
        }
        else {
            return new MCPStdioAdapter(config);
        }
    }
    /**
     * Call a tool on a connected server with queueing and deadline support
     */
    async callTool(serverName, config, toolName, args, options) {
        const connection = await this.getConnection(serverName, config);
        // Check if we can execute immediately or need to queue
        if (connection.inFlightCount >= connection.maxInFlight) {
            // Queue the request with deadline
            const deadline = new Date(Date.now() + (options?.timeoutMs || 30000));
            return new Promise((resolve, reject) => {
                connection.queue.push({ resolve, reject, deadline });
                console.log(`[MCPClientManager] Queued request for ${serverName}, queue length: ${connection.queue.length}`);
            });
        }
        // Execute immediately
        return this.executeToolCall(connection, config, toolName, args, options);
    }
    /**
     * Execute a tool call and manage queue processing
     */
    async executeToolCall(connection, config, toolName, args, options) {
        connection.inFlightCount++;
        console.log(`[MCPClientManager] Executing tool ${toolName} on ${connection.serverName}, in-flight: ${connection.inFlightCount}/${connection.maxInFlight}`);
        try {
            const result = await connection.adapter.callTool(toolName, args, options);
            connection.lastUsed = new Date();
            connection.failureCount = 0; // Reset on success
            return result;
        }
        catch (error) {
            connection.failureCount++;
            console.error(`[MCPClientManager] Tool call failed for ${connection.serverName}:`, error);
            // If failure count is high, disconnect
            if (connection.failureCount >= 3) {
                await this.disconnect(connection.serverName, config);
            }
            throw error;
        }
        finally {
            connection.inFlightCount--;
            // Process queue if there are pending requests
            this.processQueue(connection, config);
        }
    }
    /**
     * Process queued requests with deadline expiration
     */
    processQueue(connection, config) {
        const now = new Date();
        // Remove expired requests
        const expiredCount = connection.queue.filter(req => req.deadline < now).length;
        if (expiredCount > 0) {
            console.log(`[MCPClientManager] Expiring ${expiredCount} queued requests for ${connection.serverName}`);
        }
        connection.queue = connection.queue.filter(req => {
            if (req.deadline < now) {
                req.reject(new Error('Request deadline expired'));
                return false;
            }
            return true;
        });
        // Process next request if capacity available
        if (connection.inFlightCount < connection.maxInFlight && connection.queue.length > 0) {
            const next = connection.queue.shift();
            console.log(`[MCPClientManager] Processing queued request for ${connection.serverName}, remaining: ${connection.queue.length}`);
            // Execute with deadline as timeout
            const timeoutMs = Math.max(0, next.deadline.getTime() - Date.now());
            this.executeToolCall(connection, config, '', {}, { timeoutMs })
                .then(next.resolve)
                .catch(next.reject);
        }
    }
    /**
     * List tools available on a server
     */
    async listTools(serverName, config) {
        const connection = await this.getConnection(serverName, config);
        try {
            const tools = await connection.adapter.listTools();
            connection.lastUsed = new Date();
            return tools;
        }
        catch (error) {
            connection.failureCount++;
            console.error(`[MCPClientManager] List tools failed for ${serverName}:`, error);
            throw error;
        }
    }
    /**
     * Disconnect a specific server
     */
    async disconnect(serverName, config) {
        // If config is provided, disconnect only that connection; else, disconnect all for serverName
        if (config) {
            const key = getConnectionKey(serverName, config);
            const connection = this.connections.get(key);
            if (connection) {
                try {
                    await connection.adapter.disconnect();
                }
                catch (error) {
                    console.error(`[MCPClientManager] Error disconnecting ${serverName}:`, error);
                }
                this.connections.delete(key);
                console.log(`[MCPClientManager] Disconnected ${serverName} (key: ${key})`);
            }
        }
        else {
            // Disconnect all connections for this serverName
            const keys = Array.from(this.connections.keys()).filter(k => k.includes(`"serverName":"${serverName}"`));
            for (const key of keys) {
                const connection = this.connections.get(key);
                if (connection) {
                    try {
                        await connection.adapter.disconnect();
                    }
                    catch (error) {
                        console.error(`[MCPClientManager] Error disconnecting ${serverName}:`, error);
                    }
                    this.connections.delete(key);
                    console.log(`[MCPClientManager] Disconnected ${serverName} (key: ${key})`);
                }
            }
        }
    }
    /**
     * Disconnect all servers
     */
    async disconnectAll() {
        console.log(`[MCPClientManager] Disconnecting all ${this.connections.size} connections`);
        const disconnectPromises = Array.from(this.connections.entries()).map(([key, conn]) => this.disconnect(conn.serverName, undefined));
        await Promise.all(disconnectPromises);
    }
    /**
     * Get connection statistics
     */
    getStats() {
        let connected = 0;
        let disconnected = 0;
        let inBackoff = 0;
        const now = new Date();
        const details = [];
        for (const [key, conn] of this.connections.entries()) {
            let protocol = 'unknown';
            let url = '';
            // Try to extract protocol and url from key (JSON string)
            try {
                const keyObj = JSON.parse(key);
                protocol = keyObj.protocol || 'unknown';
                url = keyObj.url || '';
            }
            catch { }
            if (conn.connected) {
                connected++;
            }
            else if (conn.nextRetryAfter && conn.nextRetryAfter > now) {
                inBackoff++;
            }
            else {
                disconnected++;
            }
            details.push({
                key,
                serverName: conn.serverName,
                protocol,
                url,
                connected: conn.connected,
                lastUsed: conn.lastUsed.toISOString(),
                failureCount: conn.failureCount,
                nextRetryAfter: conn.nextRetryAfter ? conn.nextRetryAfter.toISOString() : undefined
            });
        }
        return {
            total: this.connections.size,
            connected,
            disconnected,
            inBackoff,
            details
        };
    }
    /**
     * Start periodic cleanup of idle connections
     */
    startIdleCleanup() {
        setInterval(() => {
            const now = new Date();
            const idleConnections = [];
            for (const [name, conn] of this.connections.entries()) {
                const idleTime = now.getTime() - conn.lastUsed.getTime();
                if (conn.connected && idleTime > this.maxIdleTimeMs) {
                    idleConnections.push(name);
                }
            }
            if (idleConnections.length > 0) {
                console.log(`[MCPClientManager] Cleaning up ${idleConnections.length} idle connections`);
                idleConnections.forEach(name => this.disconnect(name));
            }
        }, 60000); // Check every minute
    }
    /**
     * Utility: delay for specified milliseconds
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}
// Singleton instance
export const mcpClientManager = new MCPClientManager();
//# sourceMappingURL=MCPClientManager.js.map