import { ValidateFunction } from 'ajv';
import { MCPTool } from './types.js';
/**
 * SchemaCache - Caches compiled Ajv schemas for efficient validation
 * Stores schemas per tool name for reuse across multiple calls
 */
export declare class SchemaCache {
    private ajv;
    private cache;
    constructor();
    /**
     * Get or compile a schema for a tool
     * @param toolName - The name of the tool
     * @param schema - The JSON schema for the tool's input
     * @returns Compiled validation function
     */
    getValidator(toolName: string, schema: Record<string, any>): ValidateFunction;
    /**
     * Bulk load schemas from a list of tools
     * @param tools - Array of MCP tools with inputSchema
     */
    loadSchemas(tools: MCPTool[]): void;
    /**
     * Validate tool arguments against cached schema
     * @param toolName - The name of the tool
     * @param args - Arguments to validate
     * @param schema - Optional schema to use if not cached
     * @returns Validation result with errors if invalid
     */
    validate(toolName: string, args: any, schema?: Record<string, any>): {
        valid: boolean;
        errors?: any[];
    };
    /**
     * Clear all cached schemas
     */
    clear(): void;
    /**
     * Get cache statistics
     */
    getStats(): {
        totalSchemas: number;
        cachedTools: string[];
    };
}
export declare const schemaCache: SchemaCache;
//# sourceMappingURL=SchemaCache.d.ts.map