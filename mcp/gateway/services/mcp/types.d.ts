/**
 * MCP Server Registry Types
 * Based on Dev-Tools active-registry.json schema
 */
export type MCPServerType = 'http' | 'stdio';
export interface MCPServerConfig {
    type: MCPServerType;
    protocol?: 'rest' | 'jsonrpc';
    package?: string;
    url?: string;
    command?: string;
    args?: string[];
    invocation?: string;
    script_path?: string;
    arguments?: string[];
    env?: Record<string, string>;
    headers?: Record<string, string>;
    enabled: boolean;
    capabilities: string[];
    health_check_url?: string | null;
    startup_timeout_ms: number;
    response_time_p95_target_ms: number;
    description?: string;
}
export interface MCPRegistry {
    version: string;
    last_updated: string;
    description?: string;
    servers: Record<string, MCPServerConfig>;
    monitoring: {
        performance_targets: {
            mcp_call_latency_p95_ms: number;
            connection_pool_utilization_max_percent: number;
            error_rate_max_percent: number;
        };
        alerting: Record<string, string>;
    };
    routing?: {
        capability_patterns: Record<string, string>;
        default_server?: string;
        fallback_strategy?: 'error' | 'default';
    };
}
export interface MCPTool {
    name: string;
    description: string;
    inputSchema: Record<string, any>;
    server: string;
}
export interface MCPToolCallRequest {
    tool: string;
    args: Record<string, any>;
    user?: string;
    stream?: boolean;
}
export interface MCPToolCallResponse {
    result: any;
    server: string;
    duration: number;
    cached?: boolean;
    error?: string;
}
export interface MCPServerHealth {
    server: string;
    healthy: boolean;
    latency?: number;
    lastChecked: string;
    error?: string;
}
export interface MCPServerInfo {
    name: string;
    type: MCPServerType;
    enabled: boolean;
    capabilities: string[];
    health?: MCPServerHealth;
    description?: string;
}
//# sourceMappingURL=types.d.ts.map