// MCP Server data for code/chef platform
// Source: servers.html production content

export interface MCPServer {
  id: string;
  name: string;
  icon: string;
  category: string;
  toolCount: number;
  description: string;
}

export interface ServerCategory {
  id: string;
  name: string;
  icon: string;
  servers: MCPServer[];
}

export const serverCategories: ServerCategory[] = [
  {
    id: 'development',
    name: 'Development & Code',
    icon: '💻',
    servers: [
      {
        id: 'github',
        name: 'GitHub Official',
        icon: '🐙',
        category: 'Source Control',
        toolCount: 40,
        description: 'Full GitHub API with OAuth — repos, branches, PRs, issues, workflows, code search',
      },
      {
        id: 'filesystem',
        name: 'Rust MCP Filesystem',
        icon: '📁',
        category: 'File Operations',
        toolCount: 24,
        description: 'High-performance file I/O — read, write, search, directory trees, file info',
      },
      {
        id: 'playwright',
        name: 'Playwright',
        icon: '🎭',
        category: 'Browser Automation',
        toolCount: 21,
        description: 'E2E testing & scraping — navigate, click, fill, screenshot, PDF generation',
      },
      {
        id: 'nextjs',
        name: 'Next.js DevTools',
        icon: '▲',
        category: 'Framework Tools',
        toolCount: 5,
        description: 'Next.js analysis — routes, build output, performance audits, cache inspection',
      },
    ],
  },
  {
    id: 'infrastructure',
    name: 'Infrastructure & DevOps',
    icon: '🏗️',
    servers: [
      {
        id: 'docker',
        name: 'DockerHub',
        icon: '🐳',
        category: 'Container Management',
        toolCount: 13,
        description: 'Container lifecycle — images, containers, logs, exec, inspect',
      },
      {
        id: 'prometheus',
        name: 'Prometheus',
        icon: '📊',
        category: 'Metrics',
        toolCount: 3,
        description: 'Metrics queries — PromQL, alerts, metric discovery',
      },
      {
        id: 'grafana',
        name: 'Grafana',
        icon: '📈',
        category: 'Dashboards',
        toolCount: 4,
        description: 'Dashboard access — queries, annotations, dashboard listings',
      },
    ],
  },
  {
    id: 'ai-knowledge',
    name: 'AI & Knowledge',
    icon: '🧠',
    servers: [
      {
        id: 'huggingface',
        name: 'Hugging Face',
        icon: '🤗',
        category: 'ML Models',
        toolCount: 9,
        description: 'Model hub access — inference, model search, dataset queries',
      },
      {
        id: 'gemini',
        name: 'Gemini API Docs',
        icon: '💎',
        category: 'API Documentation',
        toolCount: 4,
        description: 'Google Gemini docs — API reference, examples, capabilities',
      },
      {
        id: 'context7',
        name: 'Context7',
        icon: '📖',
        category: 'Documentation',
        toolCount: 3,
        description: 'Library docs — resolve IDs, fetch documentation for any library',
      },
      {
        id: 'llmtxt',
        name: 'LLM.txt',
        icon: '📄',
        category: 'LLM Context',
        toolCount: 2,
        description: 'Fetch llms.txt files — structured context for LLM consumption',
      },
      {
        id: 'zen',
        name: 'Zen',
        icon: '🧘',
        category: 'Workflow Patterns',
        toolCount: 3,
        description: 'Battle-tested patterns — event sourcing, resource dedup, TTL management',
      },
      {
        id: 'sequential-thinking',
        name: 'Sequential Thinking',
        icon: '🔗',
        category: 'Reasoning',
        toolCount: 6,
        description: 'Step-by-step reasoning — decompose complex tasks into structured plans',
      },
    ],
  },
  {
    id: 'productivity',
    name: 'Productivity',
    icon: '📝',
    servers: [
      {
        id: 'notion',
        name: 'Notion',
        icon: '📓',
        category: 'Knowledge Base',
        toolCount: 19,
        description: 'Workspace access — pages, databases, comments, search',
      },
      {
        id: 'gmail',
        name: 'Gmail MCP',
        icon: '✉️',
        category: 'Email',
        toolCount: 5,
        description: 'Email operations — send, search, read messages',
      },
      {
        id: 'youtube',
        name: 'YouTube Transcript',
        icon: '🎬',
        category: 'Video Content',
        toolCount: 2,
        description: 'Extract transcripts from YouTube videos for documentation',
      },
    ],
  },
  {
    id: 'integrations',
    name: 'Integrations',
    icon: '🔌',
    servers: [
      {
        id: 'stripe',
        name: 'Stripe',
        icon: '💳',
        category: 'Payments',
        toolCount: 22,
        description: 'Payment APIs — customers, invoices, subscriptions, payment intents',
      },
      {
        id: 'google-maps',
        name: 'Google Maps',
        icon: '🗺️',
        category: 'Location Services',
        toolCount: 8,
        description: 'Geocoding, directions, places, distance matrix',
      },
      {
        id: 'gateway',
        name: 'MCP API Gateway',
        icon: '🌐',
        category: 'Gateway',
        toolCount: 3,
        description: 'Central gateway — tool discovery, routing, health checks',
      },
      {
        id: 'time',
        name: 'Time',
        icon: '⏰',
        category: 'Utilities',
        toolCount: 2,
        description: 'Time utilities — current time, timezone conversion',
      },
    ],
  },
];

export const serverStats = {
  totalServers: 20,
  totalTools: 178,
  tokenSavings: '80-90%',
};

// Flatten all servers for easy access
export const allServers: MCPServer[] = serverCategories.flatMap(cat => cat.servers);
