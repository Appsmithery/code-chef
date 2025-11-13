export declare class StartupDiscoveryService {
    private readonly DISCOVERY_SCRIPT_PATH;
    private readonly OUTPUT_DIR;
    private readonly STARTUP_DELAY_MS;
    constructor();
    runStartupDiscovery(): Promise<void>;
    private executeDiscovery;
    private ensureOutputDirectory;
    private fileExists;
    private runDiscoveryScript;
    private logDiscoveryResults;
}
export declare const startupDiscoveryService: StartupDiscoveryService;
//# sourceMappingURL=startup-discovery.service.d.ts.map