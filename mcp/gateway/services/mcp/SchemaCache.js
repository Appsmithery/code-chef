import Ajv from 'ajv';
/**
 * SchemaCache - Caches compiled Ajv schemas for efficient validation
 * Stores schemas per tool name for reuse across multiple calls
 */
export class SchemaCache {
    ajv;
    cache = new Map();
    constructor() {
        this.ajv = new Ajv({ allErrors: true, strict: false });
    }
    /**
     * Get or compile a schema for a tool
     * @param toolName - The name of the tool
     * @param schema - The JSON schema for the tool's input
     * @returns Compiled validation function
     */
    getValidator(toolName, schema) {
        let validator = this.cache.get(toolName);
        if (!validator) {
            validator = this.ajv.compile(schema);
            this.cache.set(toolName, validator);
            console.log(`[SchemaCache] Compiled schema for tool: ${toolName}`);
        }
        return validator;
    }
    /**
     * Bulk load schemas from a list of tools
     * @param tools - Array of MCP tools with inputSchema
     */
    loadSchemas(tools) {
        for (const tool of tools) {
            if (tool.inputSchema) {
                this.getValidator(tool.name, tool.inputSchema);
            }
        }
        console.log(`[SchemaCache] Loaded ${this.cache.size} schemas`);
    }
    /**
     * Validate tool arguments against cached schema
     * @param toolName - The name of the tool
     * @param args - Arguments to validate
     * @param schema - Optional schema to use if not cached
     * @returns Validation result with errors if invalid
     */
    validate(toolName, args, schema) {
        let validator;
        if (schema) {
            validator = this.getValidator(toolName, schema);
        }
        else {
            validator = this.cache.get(toolName);
        }
        if (!validator) {
            return { valid: true }; // No schema available, skip validation
        }
        const valid = validator(args);
        return {
            valid,
            errors: valid ? undefined : validator.errors || undefined
        };
    }
    /**
     * Clear all cached schemas
     */
    clear() {
        this.cache.clear();
        console.log('[SchemaCache] Cleared all cached schemas');
    }
    /**
     * Get cache statistics
     */
    getStats() {
        return {
            totalSchemas: this.cache.size,
            cachedTools: Array.from(this.cache.keys())
        };
    }
}
// Singleton instance
export const schemaCache = new SchemaCache();
//# sourceMappingURL=SchemaCache.js.map