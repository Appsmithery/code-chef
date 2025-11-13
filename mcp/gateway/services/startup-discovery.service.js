// Startup Discovery Service
// Runs MCP server/tool discovery automation on gateway startup
import { spawn } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';
import { promises as fs } from 'fs';
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
export class StartupDiscoveryService {
    DISCOVERY_SCRIPT_PATH;
    OUTPUT_DIR;
    STARTUP_DELAY_MS = 5000; // Wait 5 seconds after startup
    constructor() {
        const projectRoot = path.resolve(__dirname, '..');
        this.DISCOVERY_SCRIPT_PATH = path.join(projectRoot, 'scripts', 'mcp-server-discovery.mjs');
        this.OUTPUT_DIR = path.join(projectRoot, 'context', 'mcp-discovery', 'output');
    }
    async runStartupDiscovery() {
        try {
            console.log('🔍 Scheduling MCP discovery automation...');
            // Wait for the gateway to fully start
            setTimeout(async () => {
                await this.executeDiscovery();
            }, this.STARTUP_DELAY_MS);
        }
        catch (error) {
            console.error('❌ Failed to schedule startup discovery:', error);
        }
    }
    async executeDiscovery() {
        try {
            console.log('🚀 Starting MCP discovery automation...');
            // Ensure output directory exists
            await this.ensureOutputDirectory();
            // Check if discovery script exists
            if (!(await this.fileExists(this.DISCOVERY_SCRIPT_PATH))) {
                console.warn(`⚠️ Discovery script not found: ${this.DISCOVERY_SCRIPT_PATH}`);
                return;
            }
            // Run discovery script
            const result = await this.runDiscoveryScript();
            if (result.success) {
                console.log('✅ MCP discovery completed successfully!');
                await this.logDiscoveryResults();
            }
            else {
                console.error('❌ MCP discovery failed:', result.error);
            }
        }
        catch (error) {
            console.error('❌ Error executing startup discovery:', error);
        }
    }
    async ensureOutputDirectory() {
        try {
            await fs.mkdir(this.OUTPUT_DIR, { recursive: true });
        }
        catch (error) {
            console.warn('Warning: Could not create discovery output directory:', error);
        }
    }
    async fileExists(filePath) {
        try {
            await fs.access(filePath);
            return true;
        }
        catch {
            return false;
        }
    }
    async runDiscoveryScript() {
        return new Promise((resolve) => {
            const child = spawn('node', [this.DISCOVERY_SCRIPT_PATH], {
                cwd: path.dirname(this.DISCOVERY_SCRIPT_PATH),
                stdio: ['pipe', 'pipe', 'pipe']
            });
            let stdout = '';
            let stderr = '';
            child.stdout?.on('data', (data) => {
                stdout += data.toString();
            });
            child.stderr?.on('data', (data) => {
                stderr += data.toString();
            });
            child.on('close', (code) => {
                if (code === 0) {
                    console.log(stdout);
                    resolve({ success: true });
                }
                else {
                    console.error(stderr);
                    resolve({ success: false, error: `Process exited with code ${code}` });
                }
            });
            child.on('error', (error) => {
                resolve({ success: false, error: error.message });
            });
            // Timeout after 30 seconds
            setTimeout(() => {
                child.kill();
                resolve({ success: false, error: 'Discovery script timed out after 30 seconds' });
            }, 30000);
        });
    }
    async logDiscoveryResults() {
        try {
            const files = await fs.readdir(this.OUTPUT_DIR);
            const mdFiles = files.filter(file => file.endsWith('.md'));
            console.log(`📊 Generated ${mdFiles.length} discovery files:`);
            mdFiles.forEach(file => {
                console.log(`   • ${file}`);
            });
            // Log file sizes for debugging
            for (const file of mdFiles) {
                const filePath = path.join(this.OUTPUT_DIR, file);
                try {
                    const stats = await fs.stat(filePath);
                    console.log(`     └─ ${(stats.size / 1024).toFixed(1)}KB`);
                }
                catch {
                    // Ignore stat errors
                }
            }
            console.log('🔗 Discovery files available for agent context!');
        }
        catch (error) {
            console.warn('Warning: Could not log discovery results:', error);
        }
    }
}
// Export singleton instance
export const startupDiscoveryService = new StartupDiscoveryService();
//# sourceMappingURL=startup-discovery.service.js.map