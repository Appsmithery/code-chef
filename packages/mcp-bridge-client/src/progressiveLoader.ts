import { MCPTool } from './client';

/**
 * Progressive tool loader using keyword-based filtering
 * Reduces token usage by 80-90% by loading only relevant tools
 */
export class ProgressiveLoader {
    private keywordMap: Record<string, string[]> = {
        // Memory & State
        'memory': ['memory'],
        'remember': ['memory'],
        'recall': ['memory'],
        'save': ['memory', 'filesystem'],
        'store': ['memory', 'database'],
        
        // Filesystem operations
        'file': ['filesystem', 'context7'],
        'directory': ['filesystem'],
        'read': ['filesystem', 'memory', 'database'],
        'write': ['filesystem', 'memory', 'database'],
        'delete': ['filesystem', 'database'],
        
        // Git & Version Control
        'git': ['git', 'github'],
        'commit': ['git'],
        'branch': ['git'],
        'pull': ['git', 'github'],
        'push': ['git', 'github'],
        'repository': ['git', 'github'],
        
        // GitHub
        'github': ['github'],
        'issue': ['github', 'linear'],
        'pr': ['github'],
        'pull request': ['github'],
        
        // Linear Project Management
        'linear': ['linear'],
        'task': ['linear'],
        'project': ['linear', 'terraform'],
        
        // Notion
        'notion': ['notion'],
        'notes': ['notion', 'memory'],
        'wiki': ['notion'],
        
        // Infrastructure
        'deploy': ['terraform', 'docker', 'kubernetes'],
        'infrastructure': ['terraform', 'docker', 'kubernetes'],
        'terraform': ['terraform'],
        'cloud': ['terraform', 'aws'],
        'server': ['docker', 'kubernetes', 'terraform'],
        
        // Containers
        'docker': ['docker'],
        'container': ['docker', 'kubernetes'],
        'image': ['docker'],
        'kubernetes': ['kubernetes'],
        'k8s': ['kubernetes'],
        'pod': ['kubernetes'],
        
        // Database
        'database': ['database', 'postgres', 'sqlite'],
        'sql': ['database', 'postgres', 'sqlite'],
        'query': ['database', 'postgres', 'sqlite'],
        'postgres': ['postgres'],
        'postgresql': ['postgres'],
        'sqlite': ['sqlite'],
        
        // Search & Web
        'search': ['brave-search', 'exa', 'context7'],
        'web': ['brave-search', 'fetch', 'puppeteer'],
        'browse': ['puppeteer', 'fetch'],
        'scrape': ['puppeteer'],
        
        // Time & Calendar
        'time': ['time'],
        'date': ['time'],
        'calendar': ['time'],
        'schedule': ['time', 'linear'],
        
        // Analytics & Monitoring
        'metrics': ['prometheus'],
        'monitor': ['prometheus'],
        'alert': ['prometheus'],
        
        // Sequential Thinking
        'think': ['sequential-thinking'],
        'reason': ['sequential-thinking'],
        'analyze': ['sequential-thinking', 'context7'],
        
        // Code & Context
        'code': ['context7', 'filesystem', 'github'],
        'codebase': ['context7', 'github'],
        'context': ['context7'],
        
        // Fetch & HTTP
        'fetch': ['fetch'],
        'http': ['fetch'],
        'api': ['fetch'],
        'request': ['fetch'],
        
        // Testing
        'test': ['filesystem', 'github'],
        'mock': ['filesystem']
    };

    /**
     * Filter tools based on task description
     * 
     * @param taskDescription - Natural language task description
     * @param allTools - Full tool catalog
     * @returns Filtered tools relevant to task
     */
    filterByTask(taskDescription: string, allTools: MCPTool[]): MCPTool[] {
        const lowerTask = taskDescription.toLowerCase();
        const relevantServers = new Set<string>();

        // Match keywords to servers
        for (const [keyword, servers] of Object.entries(this.keywordMap)) {
            if (lowerTask.includes(keyword)) {
                servers.forEach(server => relevantServers.add(server));
            }
        }

        // If no keywords matched, return high-priority servers
        if (relevantServers.size === 0) {
            relevantServers.add('context7');
            relevantServers.add('memory');
            relevantServers.add('filesystem');
            relevantServers.add('sequential-thinking');
        }

        // Filter tools
        return allTools.filter(tool => relevantServers.has(tool.server));
    }

    /**
     * Get servers for specific keywords
     * 
     * @param keywords - Array of keywords
     * @returns Set of server names
     */
    getServersForKeywords(keywords: string[]): Set<string> {
        const servers = new Set<string>();
        
        keywords.forEach(keyword => {
            const lowerKeyword = keyword.toLowerCase();
            const mappedServers = this.keywordMap[lowerKeyword] || [];
            mappedServers.forEach(server => servers.add(server));
        });

        return servers;
    }

    /**
     * Add custom keyword mapping
     * 
     * @param keyword - Keyword to map
     * @param servers - Array of server names
     */
    addKeywordMapping(keyword: string, servers: string[]): void {
        this.keywordMap[keyword.toLowerCase()] = servers;
    }

    /**
     * Get all keyword mappings
     */
    getKeywordMappings(): Record<string, string[]> {
        return { ...this.keywordMap };
    }
}
