// Shared data structures for code/chef platform

export interface Agent {
  id: string;
  name: string;
  description: string;
  model: string;
  provider: string;
  port: number;
  capabilities: string[];
  status: "online" | "offline" | "maintenance";
}

export interface MCPServer {
  id: string;
  name: string;
  description: string;
  toolCount: number;
  category: string;
  status: "active" | "inactive";
}

export const agents: Agent[] = [
  {
    id: "orchestrator",
    name: "Orchestrator (Head Chef)",
    description: "Task routing and workflow coordination. Routes tasks to specialized agents using LangGraph StateGraph with intelligent decision-making.",
    model: "llama3.3-70b-instruct",
    provider: "Gradient",
    port: 8001,
    capabilities: ["Task Routing", "Workflow Coordination", "HITL Management", "Multi-Agent Orchestration"],
    status: "online"
  },
  {
    id: "feature-dev",
    name: "Feature Development (Sous Chef)",
    description: "Code implementation and feature development. Handles code generation, refactoring, and implementation of new features with best practices.",
    model: "codellama-13b",
    provider: "Gradient",
    port: 8002,
    capabilities: ["Code Generation", "Feature Implementation", "Refactoring", "Bug Fixes"],
    status: "online"
  },
  {
    id: "code-review",
    name: "Code Review",
    description: "Security audits and quality reviews. Performs comprehensive code analysis, security scanning, and ensures adherence to coding standards.",
    model: "llama3.3-70b-instruct",
    provider: "Gradient",
    port: 8003,
    capabilities: ["Security Audits", "Quality Review", "Best Practices", "Vulnerability Scanning"],
    status: "online"
  },
  {
    id: "infrastructure",
    name: "Infrastructure",
    description: "IaC, Terraform, and Docker Compose management. Handles infrastructure provisioning, configuration, and deployment automation.",
    model: "llama3-8b-instruct",
    provider: "Gradient",
    port: 8004,
    capabilities: ["Terraform", "Docker Compose", "Infrastructure as Code", "Cloud Provisioning"],
    status: "online"
  },
  {
    id: "cicd",
    name: "CI/CD Pipeline",
    description: "GitHub Actions and pipeline automation. Manages continuous integration and deployment workflows with automated testing and deployment.",
    model: "llama3.3-70b-instruct",
    provider: "Gradient",
    port: 8005,
    capabilities: ["GitHub Actions", "Pipeline Automation", "Automated Testing", "Deployment"],
    status: "online"
  },
  {
    id: "documentation",
    name: "Documentation",
    description: "Technical writing and documentation generation. Creates comprehensive documentation, READMEs, API references, and guides.",
    model: "llama3.3-70b-instruct",
    provider: "Gradient",
    port: 8006,
    capabilities: ["Technical Writing", "API Documentation", "README Generation", "Guides"],
    status: "online"
  }
];

export const mcpServers: MCPServer[] = [
  {
    id: "docker",
    name: "Docker MCP",
    description: "Container management, image operations, and Docker Compose orchestration",
    toolCount: 12,
    category: "Infrastructure",
    status: "active"
  },
  {
    id: "github",
    name: "GitHub MCP",
    description: "Repository management, PR operations, and issue tracking",
    toolCount: 18,
    category: "Development",
    status: "active"
  },
  {
    id: "linear",
    name: "Linear MCP",
    description: "Project management, issue creation, and workflow automation",
    toolCount: 15,
    category: "Project Management",
    status: "active"
  },
  {
    id: "filesystem",
    name: "Filesystem MCP",
    description: "File operations, directory management, and code editing",
    toolCount: 10,
    category: "Development",
    status: "active"
  },
  {
    id: "git",
    name: "Git MCP",
    description: "Version control operations, commits, and branch management",
    toolCount: 14,
    category: "Development",
    status: "active"
  },
  {
    id: "postgres",
    name: "PostgreSQL MCP",
    description: "Database queries, schema management, and data operations",
    toolCount: 8,
    category: "Data",
    status: "active"
  },
  {
    id: "langchain-docs",
    name: "LangChain Docs MCP",
    description: "Semantic search across LangChain documentation",
    toolCount: 5,
    category: "Documentation",
    status: "active"
  },
  {
    id: "python",
    name: "Python MCP",
    description: "Code execution, package management, and environment handling",
    toolCount: 9,
    category: "Development",
    status: "active"
  },
  {
    id: "typescript",
    name: "TypeScript MCP",
    description: "Type checking, compilation, and Node.js operations",
    toolCount: 7,
    category: "Development",
    status: "active"
  },
  {
    id: "aws",
    name: "AWS MCP",
    description: "Cloud resource management and service operations",
    toolCount: 20,
    category: "Cloud",
    status: "active"
  },
  {
    id: "terraform",
    name: "Terraform MCP",
    description: "Infrastructure provisioning and state management",
    toolCount: 11,
    category: "Infrastructure",
    status: "active"
  },
  {
    id: "kubernetes",
    name: "Kubernetes MCP",
    description: "Cluster management, pod operations, and service orchestration",
    toolCount: 16,
    category: "Infrastructure",
    status: "active"
  },
  {
    id: "slack",
    name: "Slack MCP",
    description: "Notifications, channel management, and team communication",
    toolCount: 8,
    category: "Communication",
    status: "active"
  },
  {
    id: "monitoring",
    name: "Monitoring MCP",
    description: "Metrics collection, alerting, and observability",
    toolCount: 10,
    category: "Observability",
    status: "active"
  },
  {
    id: "security",
    name: "Security Scanner MCP",
    description: "Vulnerability scanning, secrets detection, and compliance",
    toolCount: 12,
    category: "Security",
    status: "active"
  }
];

export const totalTools = mcpServers.reduce((sum, server) => sum + server.toolCount, 0);
