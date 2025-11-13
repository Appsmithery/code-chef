import axios from 'axios';
import { spawn } from 'child_process';
/**
 * HTTP adapter for MCP servers (GitHub Copilot, Supabase, Context7)
 */
export class MCPHTTPAdapter {
    config;
    client;
    connected = false;
    constructor(config) {
        if (config.type !== 'http') {
            throw new Error('MCPHTTPAdapter requires http server type');
        }
        this.config = config;
        // Create axios instance with server configuration
        this.client = axios.create({
            baseURL: config.url,
            timeout: config.startup_timeout_ms || 30000,
            headers: {
                'Content-Type': 'application/json',
                ...config.headers
            }
        });
        // Add environment variables as headers if specified
        if (config.env) {
            Object.entries(config.env).forEach(([key, value]) => {
                const envValue = this.resolveEnvVar(value);
                if (envValue) {
                    this.client.defaults.headers.common[key] = envValue;
                }
            });
        }
    }
    async connect() {
        // For HTTP servers, verify connectivity with health check or base endpoint
        try {
            const healthUrl = this.config.health_check_url || '';
            if (healthUrl) {
                await this.client.get(healthUrl);
            }
            else {
                // Just verify base URL is reachable
                await this.client.get('/');
            }
            this.connected = true;
            console.log(`[MCPHTTPAdapter] Connected to ${this.config.url}`);
        }
        catch (error) {
            console.error(`[MCPHTTPAdapter] Connection failed to ${this.config.url}:`, error.message);
            throw new Error(`Failed to connect to HTTP server: ${error.message}`);
        }
    }
    async disconnect() {
        this.connected = false;
        console.log(`[MCPHTTPAdapter] Disconnected from ${this.config.url}`);
    }
    async listTools() {
        if (!this.connected) {
            throw new Error('Not connected to MCP server');
        }
        try {
            // MCP protocol: POST /tools/list
            const response = await this.client.post('/tools/list', {});
            return response.data.tools || [];
        }
        catch (error) {
            console.error(`[MCPHTTPAdapter] List tools failed:`, error.message);
            throw new Error(`Failed to list tools: ${error.message}`);
        }
    }
    async callTool(toolName, args) {
        if (!this.connected) {
            throw new Error('Not connected to MCP server');
        }
        try {
            // MCP protocol: POST /tools/call
            const response = await this.client.post('/tools/call', {
                name: toolName,
                arguments: args
            });
            return response.data;
        }
        catch (error) {
            console.error(`[MCPHTTPAdapter] Tool call failed for ${toolName}:`, error.message);
            throw new Error(`Failed to call tool ${toolName}: ${error.message}`);
        }
    }
    /**
     * Resolve environment variable placeholders like ${env:VAR_NAME:default}
     */
    resolveEnvVar(value) {
        const envVarPattern = /\$\{env:([^:}]+)(?::([^}]*))?\}/g;
        return value.replace(envVarPattern, (_, varName, defaultValue) => {
            return process.env[varName] || defaultValue || '';
        });
    }
}
/**
 * Stdio adapter for local MCP servers (Playwright, Utility, Comet)
 */
export class MCPStdioAdapter {
    config;
    process;
    connected = false;
    messageId = 0;
    pendingRequests = new Map();
    constructor(config) {
        if (config.type !== 'stdio') {
            throw new Error('MCPStdioAdapter requires stdio server type');
        }
        this.config = config;
    }
    async connect() {
        return new Promise((resolve, reject) => {
            try {
                // Support both new `command`/`args` format (MCP_DOCKER) and legacy `invocation`/`script_path` format
                let command;
                let commandArgs;
                if (this.config.command) {
                    // New format: { command: "docker", args: ["mcp", "gateway", "run"] }
                    command = this.config.command;
                    commandArgs = this.config.args || [];
                }
                else {
                    // Legacy format: { invocation: "node", script_path: "./path/to/script.js", arguments: [...] }
                    const scriptPath = this.resolveEnvVar(this.config.script_path || '');
                    command = this.config.invocation || 'node';
                    commandArgs = scriptPath ? [scriptPath, ...(this.config.arguments || [])] : (this.config.arguments || []);
                }
                console.log(`[MCPStdioAdapter] Starting ${command} ${commandArgs.join(' ')}`);
                // Spawn the MCP server process
                this.process = spawn(command, commandArgs, {
                    env: {
                        ...process.env,
                        ...this.resolveEnvVars(this.config.env || {})
                    },
                    stdio: ['pipe', 'pipe', 'pipe']
                });
                // Setup stdout handler for JSON-RPC responses
                this.process.stdout?.on('data', (data) => {
                    this.handleStdout(data);
                });
                // Setup stderr handler for errors
                this.process.stderr?.on('data', (data) => {
                    console.error(`[MCPStdioAdapter] stderr:`, data.toString());
                });
                // Handle process exit
                this.process.on('exit', (code) => {
                    console.log(`[MCPStdioAdapter] Process exited with code ${code}`);
                    this.connected = false;
                    // Reject all pending requests
                    this.pendingRequests.forEach(({ reject }) => {
                        reject(new Error('MCP server process exited'));
                    });
                    this.pendingRequests.clear();
                });
                // Handle process errors
                this.process.on('error', (error) => {
                    console.error(`[MCPStdioAdapter] Process error:`, error);
                    reject(error);
                });
                // Give the process time to start up
                setTimeout(() => {
                    this.connected = true;
                    console.log(`[MCPStdioAdapter] Connected to stdio server`);
                    resolve();
                }, 1000);
            }
            catch (error) {
                console.error(`[MCPStdioAdapter] Failed to start process:`, error);
                reject(error);
            }
        });
    }
    async disconnect() {
        if (this.process) {
            this.process.kill();
            this.process = undefined;
        }
        this.connected = false;
        console.log(`[MCPStdioAdapter] Disconnected from stdio server`);
    }
    async listTools() {
        if (!this.connected) {
            throw new Error('Not connected to MCP server');
        }
        const response = await this.sendRequest('tools/list', {});
        return response.tools || [];
    }
    async callTool(toolName, args) {
        if (!this.connected) {
            throw new Error('Not connected to MCP server');
        }
        return await this.sendRequest('tools/call', {
            name: toolName,
            arguments: args
        });
    }
    /**
     * Send JSON-RPC request to stdio process
     */
    sendRequest(method, params) {
        return new Promise((resolve, reject) => {
            if (!this.process || !this.connected) {
                return reject(new Error('Not connected to MCP server'));
            }
            const id = ++this.messageId;
            const request = {
                jsonrpc: '2.0',
                id,
                method,
                params
            };
            // Store the promise handlers
            this.pendingRequests.set(id, { resolve, reject });
            // Set timeout for request
            setTimeout(() => {
                if (this.pendingRequests.has(id)) {
                    this.pendingRequests.delete(id);
                    reject(new Error(`Request timeout for ${method}`));
                }
            }, this.config.startup_timeout_ms || 30000);
            // Send request to stdin
            this.process.stdin?.write(JSON.stringify(request) + '\n');
        });
    }
    /**
     * Handle stdout data from stdio process
     */
    handleStdout(data) {
        const lines = data.toString().split('\n').filter(line => line.trim());
        for (const line of lines) {
            try {
                const response = JSON.parse(line);
                if (response.id !== undefined) {
                    const pending = this.pendingRequests.get(response.id);
                    if (pending) {
                        this.pendingRequests.delete(response.id);
                        if (response.error) {
                            pending.reject(new Error(response.error.message || 'MCP server error'));
                        }
                        else {
                            pending.resolve(response.result);
                        }
                    }
                }
            }
            catch (error) {
                console.error(`[MCPStdioAdapter] Failed to parse response:`, line, error);
            }
        }
    }
    /**
     * Resolve environment variable placeholders
     */
    resolveEnvVar(value) {
        const envVarPattern = /\$\{env:([^:}]+)(?::([^}]*))?\}/g;
        return value.replace(envVarPattern, (_, varName, defaultValue) => {
            return process.env[varName] || defaultValue || '';
        });
    }
    /**
     * Resolve all environment variables in config object
     */
    resolveEnvVars(env) {
        const resolved = {};
        Object.entries(env).forEach(([key, value]) => {
            resolved[key] = this.resolveEnvVar(value);
        });
        return resolved;
    }
}
//# sourceMappingURL=MCPClientAdapter.js.map