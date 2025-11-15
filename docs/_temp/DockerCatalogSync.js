// DockerCatalogSync.ts
// Fetches and caches the MCP catalog from the Docker MCP Gateway (HTTP or CLI)
// Integrates with MCPRegistry for up-to-date tool/server discovery
// Use global fetch if available (Node 18+), else fallback to node-fetch via dynamic import
export async function getFetch() {
    if (typeof fetch === 'function') {
        return fetch;
    }
    else {
        try {
            // ESM dynamic import, cast to any to avoid type errors
            // @ts-expect-error: node-fetch v3+ does not ship types, this is safe for runtime
            const mod = await import('node-fetch');
            return (mod.default || mod);
        }
        catch (e) {
            throw new Error('No fetch implementation found. Please use Node 18+ or install node-fetch.');
        }
    }
}
export class DockerCatalogSync {
    catalog = [];
    timer = null;
    options;
    constructor(options) {
        this.options = options;
    }
    async start() {
        try {
            await this.refresh();
        }
        catch (err) {
            console.error('[DockerCatalogSync] Initial refresh failed:', err.message);
            // Continue with empty catalog
        }
        if (this.options.refreshIntervalMs) {
            this.timer = setInterval(() => this.refresh(), this.options.refreshIntervalMs);
        }
    }
    stop() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    }
    async refresh() {
        try {
            if (this.options.gatewayUrl) {
                const fetchFn = await getFetch();
                const res = await fetchFn(this.options.gatewayUrl);
                if (!res.ok)
                    throw new Error(`HTTP ${res.status}`);
                this.catalog = await res.json();
            }
            else if (this.options.cliCommand) {
                // Use dynamic import for child_process (ESM compatible)
                const mod = await import('child_process');
                const exec = mod.exec;
                this.catalog = await new Promise((resolve, reject) => {
                    exec(this.options.cliCommand, (err, stdout) => {
                        if (err)
                            return reject(err);
                        try {
                            resolve(JSON.parse(stdout));
                        }
                        catch (e) {
                            reject(e);
                        }
                    });
                });
            }
        }
        catch (e) {
            // Log error, keep old catalog
            console.error('DockerCatalogSync refresh failed:', e);
        }
    }
    getCatalog() {
        return this.catalog;
    }
    findByCapability(capability) {
        return this.catalog.filter(entry => entry.capabilities?.includes(capability));
    }
}
//# sourceMappingURL=DockerCatalogSync.js.map