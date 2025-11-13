export declare function getFetch(): Promise<(input: string | Request | URL, init?: RequestInit) => Promise<Response>>;
export interface CatalogEntry {
    id: string;
    name: string;
    type: string;
    url: string;
    capabilities: string[];
    [key: string]: any;
}
export interface DockerCatalogSyncOptions {
    gatewayUrl?: string;
    cliCommand?: string;
    refreshIntervalMs?: number;
}
export declare class DockerCatalogSync {
    private catalog;
    private timer;
    private options;
    constructor(options: DockerCatalogSyncOptions);
    start(): Promise<void>;
    stop(): void;
    refresh(): Promise<void>;
    getCatalog(): CatalogEntry[];
    findByCapability(capability: string): CatalogEntry[];
}
//# sourceMappingURL=DockerCatalogSync.d.ts.map