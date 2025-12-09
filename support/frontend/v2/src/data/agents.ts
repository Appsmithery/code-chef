// Agent data for code/chef platform
// Source: agents.html production content

export interface Agent {
  id: string;
  name: string;
  role: string;
  icon: string;
  description: string;
  model: string;
  port?: number;
  specialization: string;
  capabilities: string[];
  roleColor: 'mint' | 'lavender' | 'gray-blue' | 'salmon' | 'light-yellow' | 'default';
}

export const agents: Agent[] = [
  {
    id: 'head-chef',
    name: 'Head Chef',
    role: 'Orchestrator',
    icon: '🎯',
    description: 'Coordinates task routing and workflow hand-offs across all specialized agents. Acts as the central coordinator for complex multi-agent development workflows.',
    model: 'llama3.3-70b-instruct',
    port: 8001,
    specialization: 'Coordination',
    capabilities: ['Task Routing', 'Delegation', 'Coordination', 'Workflow Management'],
    roleColor: 'mint',
  },
  {
    id: 'sous-chef',
    name: 'Sous-Chef',
    role: 'Feature-Dev',
    icon: '💻',
    description: 'Handles feature implementation and code generation. Specializes in creating new features, writing application code, and implementing business logic across the stack.',
    model: 'codellama-13b',
    specialization: 'Code Generation',
    capabilities: ['Feature Implementation', 'Refactoring', 'Code Generation'],
    roleColor: 'lavender',
  },
  {
    id: 'code-review',
    name: 'Code Review',
    role: 'Sub-Agent',
    icon: '🔍',
    description: 'Performs automated code reviews, static analysis, and security scanning. Ensures code quality, identifies bugs, and enforces best practices across the codebase.',
    model: 'llama-3.1-70b-instruct',
    specialization: 'Quality Analysis',
    capabilities: ['Code Review', 'Quality Analysis', 'Best Practices'],
    roleColor: 'gray-blue',
  },
  {
    id: 'infrastructure',
    name: 'Infrastructure',
    role: 'Sub-Agent',
    icon: '🏗️',
    description: 'Manages infrastructure as code, Docker, Kubernetes, and Terraform configurations. Handles provisioning, scaling, and deployment infrastructure across cloud providers.',
    model: 'llama-3.1-8b-instruct',
    specialization: 'IaC / DevOps',
    capabilities: ['Docker', 'Kubernetes', 'Terraform', 'Provisioning'],
    roleColor: 'salmon',
  },
  {
    id: 'cicd',
    name: 'CI/CD',
    role: 'Sub-Agent',
    icon: '⚙️',
    description: 'Manages continuous integration and deployment pipelines. Creates and maintains CI/CD workflows for GitHub Actions, GitLab CI, and Jenkins.',
    model: 'llama-3.1-8b-instruct',
    specialization: 'Pipelines',
    capabilities: ['GitHub Actions', 'GitLab CI', 'Deployment'],
    roleColor: 'light-yellow',
  },
  {
    id: 'documentation',
    name: 'Documentation',
    role: 'Sub-Agent',
    icon: '📚',
    description: 'Generates and maintains project documentation, READMEs, API docs, and guides. Keeps technical documentation up-to-date and accessible for the team.',
    model: 'mistral-7b',
    specialization: 'Technical Writing',
    capabilities: ['README Generation', 'API Docs', 'Guides'],
    roleColor: 'default',
  },
];

export const agentStats = {
  totalAgents: 6,
  totalModels: 5,
  totalTools: 178,
};
