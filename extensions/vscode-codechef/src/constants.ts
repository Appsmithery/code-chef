/**
 * Centralized constants for code/chef extension
 */
import * as vscode from 'vscode';

// ============================================================================
// Agent Types & Emojis
// ============================================================================

export type AgentType = 
    | 'feature-dev'
    | 'code-review'
    | 'infrastructure'
    | 'cicd'
    | 'documentation'
    | 'orchestrator';

export const AGENT_EMOJIS: Record<AgentType | string, string> = {
    'feature-dev': '💻',
    'code-review': '🔍',
    'infrastructure': '🏗️',
    'cicd': '🚀',
    'documentation': '📚',
    'orchestrator': '🎯'
};

export const AGENT_COLORS: Record<AgentType | string, string> = {
    'feature-dev': '#3B82F6',       // Blue
    'code-review': '#22C55E',       // Green
    'infrastructure': '#1E3A8A',    // Navy
    'cicd': '#F97316',              // Orange
    'documentation': '#14B8A6',     // Teal
    'orchestrator': '#9333EA'       // Purple
};

export const AGENT_ICONS: Record<AgentType | string, string> = {
    'orchestrator': 'orchestrator.png',
    'feature-dev': 'feature-dev.png',
    'code-review': 'code-review.png',
    'infrastructure': 'infrastructure.png',
    'cicd': 'cicd.png',
    'documentation': 'documentation.png'
};

/**
 * Get emoji for an agent type
 */
export function getAgentEmoji(agentType: string): string {
    return AGENT_EMOJIS[agentType] || '🤖';
}

/**
 * Get color for an agent type
 */
export function getAgentColor(agentType: string): string {
    return AGENT_COLORS[agentType] || AGENT_COLORS['orchestrator'];
}

// ============================================================================
// Workflow Names
// ============================================================================

export type WorkflowName = 
    | 'auto'
    | 'feature'
    | 'pr-deployment'
    | 'hotfix'
    | 'infrastructure'
    | 'docs-update';

export const KNOWN_WORKFLOWS: readonly WorkflowName[] = [
    'feature',
    'pr-deployment',
    'hotfix',
    'infrastructure',
    'docs-update'
] as const;

// ============================================================================
// API Paths
// ============================================================================

export const API_PATHS = {
    // Core endpoints
    ORCHESTRATE: '/orchestrate',
    HEALTH: '/health',
    METRICS: '/metrics',
    TOOLS: '/tools',
    
    // Task endpoints
    TASKS: '/tasks',
    EXECUTE: '/execute',
    
    // Workflow endpoints
    WORKFLOW_SMART_EXECUTE: '/workflow/smart-execute',
    WORKFLOW_TEMPLATES: '/workflow/templates',
    WORKFLOW_EXECUTE: '/workflow/execute',
    WORKFLOW_STATUS: '/workflow/status',
    
    // Approval endpoints
    APPROVALS_PENDING: '/approvals/pending',
    
    // Chat endpoints
    CHAT: '/chat'
} as const;

// ============================================================================
// Linear URL Building
// ============================================================================

const LINEAR_BASE_URL = 'https://linear.app';

/**
 * Build a Linear issue URL from issue ID
 * @param issueId Issue ID (e.g., 'DEV-68', 'PROJ-123')
 * @param workspaceSlug Optional workspace slug, defaults to config or 'project-roadmaps'
 */
export function buildLinearIssueUrl(issueId: string, workspaceSlug?: string): string {
    const slug = workspaceSlug ?? 
        vscode.workspace.getConfiguration('codechef').get('linearWorkspaceSlug', 'project-roadmaps');
    return `${LINEAR_BASE_URL}/${slug}/issue/${issueId}`;
}

/**
 * Build a Linear project URL
 * @param projectId Project ID or slug
 * @param workspaceSlug Optional workspace slug
 */
export function buildLinearProjectUrl(projectId: string, workspaceSlug?: string): string {
    const slug = workspaceSlug ?? 
        vscode.workspace.getConfiguration('codechef').get('linearWorkspaceSlug', 'project-roadmaps');
    return `${LINEAR_BASE_URL}/${slug}/project/${projectId}`;
}

/**
 * Build a Linear team URL
 * @param teamKey Team key (e.g., 'DEV', 'CHEF')
 * @param workspaceSlug Optional workspace slug
 */
export function buildLinearTeamUrl(teamKey: string, workspaceSlug?: string): string {
    const slug = workspaceSlug ?? 
        vscode.workspace.getConfiguration('codechef').get('linearWorkspaceSlug', 'project-roadmaps');
    return `${LINEAR_BASE_URL}/${slug}/team/${teamKey}`;
}

// ============================================================================
// External URLs
// ============================================================================

export const EXTERNAL_URLS = {
    DEFAULT_LANGSMITH: 'https://smith.langchain.com',
    DEFAULT_GRAFANA: 'https://appsmithery.grafana.net',
    DEFAULT_ORCHESTRATOR: 'https://codechef.appsmithery.co/api'
} as const;

// ============================================================================
// Chat Commands
// ============================================================================

export const CHAT_COMMANDS = {
    STATUS: 'status',
    APPROVE: 'approve',
    TOOLS: 'tools',
    WORKFLOW: 'workflow',
    WORKFLOWS: 'workflows',
    EXECUTE: 'execute'
} as const;

// ============================================================================
// Risk Level Styling
// ============================================================================

export const RISK_LEVEL_EMOJIS: Record<string, string> = {
    'low': '🟢',
    'medium': '🟡',
    'high': '🔴',
    'critical': '🔴'
};

export function getRiskEmoji(riskLevel: string): string {
    return RISK_LEVEL_EMOJIS[riskLevel] || '⚪';
}

// ============================================================================
// Confidence Level Styling
// ============================================================================

export function getConfidenceEmoji(confidence: number): string {
    if (confidence >= 0.8) return '🟢';
    if (confidence >= 0.6) return '🟡';
    return '🔴';
}
