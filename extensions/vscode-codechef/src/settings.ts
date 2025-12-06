import * as vscode from 'vscode';

/**
 * Token optimization settings from VS Code configuration
 */
export interface TokenOptimizationSettings {
    environment: 'production' | 'development';
    toolLoadingStrategy: 'minimal' | 'progressive' | 'agent_profile' | 'full';
    maxToolsPerRequest: number;
    enableContext7Cache: boolean;
    maxContextTokens: number;
    maxResponseTokens: number;
    ragEnabled: boolean;
    ragMaxResults: number;
    ragCollection: string;
    dailyTokenBudget: number;
    showTokenUsage: boolean;
    costAlertThreshold: number;
}

/**
 * Workflow settings from VS Code configuration
 */
export interface WorkflowSettings {
    defaultWorkflow: 'auto' | 'feature' | 'pr-deployment' | 'hotfix' | 'infrastructure' | 'docs-update';
    workflowAutoExecute: boolean;
    workflowConfirmThreshold: number;
    showWorkflowPreview: boolean;
}

/**
 * All code/chef extension settings
 */
export interface CodeChefSettings extends TokenOptimizationSettings, WorkflowSettings {
    orchestratorUrl: string;
    apiKey: string;
    autoApproveThreshold: 'low' | 'medium' | 'high' | 'critical' | 'never';
    enableNotifications: boolean;
    linearHubIssue: string;
    linearWorkspaceSlug: string;
    langsmithUrl: string;
    grafanaUrl: string;
}

/**
 * Get all code/chef settings from VS Code configuration
 */
export function getSettings(): CodeChefSettings {
    const config = vscode.workspace.getConfiguration('codechef');
    
    return {
        // Connection
        orchestratorUrl: config.get('orchestratorUrl', 'https://codechef.appsmithery.co/api'),
        apiKey: config.get('apiKey', ''),
        
        // Environment & Model Selection
        environment: config.get('environment', 'production') as 'production' | 'development',
        
        // Tool Loading (Token Optimization)
        toolLoadingStrategy: config.get('toolLoadingStrategy', 'progressive') as any,
        maxToolsPerRequest: config.get('maxToolsPerRequest', 30),
        enableContext7Cache: config.get('enableContext7Cache', true),
        
        // Context Budget
        maxContextTokens: config.get('maxContextTokens', 8000),
        maxResponseTokens: config.get('maxResponseTokens', 2000),
        
        // RAG Settings
        ragEnabled: config.get('ragEnabled', true),
        ragMaxResults: config.get('ragMaxResults', 5),
        ragCollection: config.get('ragCollection', 'code_patterns'),
        
        // Cost Controls
        dailyTokenBudget: config.get('dailyTokenBudget', 0),
        showTokenUsage: config.get('showTokenUsage', true),
        costAlertThreshold: config.get('costAlertThreshold', 0.10),
        
        // Approvals
        autoApproveThreshold: config.get('autoApproveThreshold', 'low') as any,
        enableNotifications: config.get('enableNotifications', true),
        linearHubIssue: config.get('linearHubIssue', 'DEV-68'),
        linearWorkspaceSlug: config.get('linearWorkspaceSlug', 'dev-ops'),
        
        // Workflow Settings
        defaultWorkflow: config.get('defaultWorkflow', 'auto') as any,
        workflowAutoExecute: config.get('workflowAutoExecute', true),
        workflowConfirmThreshold: config.get('workflowConfirmThreshold', 0.7),
        showWorkflowPreview: config.get('showWorkflowPreview', true),
        
        // Observability
        langsmithUrl: config.get('langsmithUrl', 'https://smith.langchain.com'),
        grafanaUrl: config.get('grafanaUrl', 'https://appsmithery.grafana.net')
    };
}

/**
 * Get workflow settings for workflow selection
 */
export function getWorkflowSettings(): WorkflowSettings {
    const config = vscode.workspace.getConfiguration('codechef');
    return {
        defaultWorkflow: config.get('defaultWorkflow', 'auto') as any,
        workflowAutoExecute: config.get('workflowAutoExecute', true),
        workflowConfirmThreshold: config.get('workflowConfirmThreshold', 0.7),
        showWorkflowPreview: config.get('showWorkflowPreview', true)
    };
}

/**
 * Get token optimization settings for API requests
 */
export function getTokenOptimizationSettings(): TokenOptimizationSettings {
    const settings = getSettings();
    return {
        environment: settings.environment,
        toolLoadingStrategy: settings.toolLoadingStrategy,
        maxToolsPerRequest: settings.maxToolsPerRequest,
        enableContext7Cache: settings.enableContext7Cache,
        maxContextTokens: settings.maxContextTokens,
        maxResponseTokens: settings.maxResponseTokens,
        ragEnabled: settings.ragEnabled,
        ragMaxResults: settings.ragMaxResults,
        ragCollection: settings.ragCollection,
        dailyTokenBudget: settings.dailyTokenBudget,
        showTokenUsage: settings.showTokenUsage,
        costAlertThreshold: settings.costAlertThreshold
    };
}

/**
 * Build workspace_config object for orchestrator API
 */
export function buildWorkspaceConfig(): Record<string, any> {
    const settings = getTokenOptimizationSettings();
    const workflowSettings = getWorkflowSettings();
    
    return {
        environment: settings.environment,
        tool_loading: {
            strategy: settings.toolLoadingStrategy,
            max_tools: settings.maxToolsPerRequest,
            context7_cache_enabled: settings.enableContext7Cache
        },
        context: {
            max_tokens: settings.maxContextTokens,
            response_max_tokens: settings.maxResponseTokens
        },
        rag: {
            enabled: settings.ragEnabled,
            max_results: settings.ragMaxResults,
            default_collection: settings.ragCollection
        },
        cost_controls: {
            daily_budget: settings.dailyTokenBudget,
            show_usage: settings.showTokenUsage,
            alert_threshold: settings.costAlertThreshold
        },
        workflow: {
            default_workflow: workflowSettings.defaultWorkflow,
            auto_execute: workflowSettings.workflowAutoExecute,
            confirm_threshold: workflowSettings.workflowConfirmThreshold,
            show_preview: workflowSettings.showWorkflowPreview
        }
    };
}

/**
 * Check if token usage should be displayed
 */
export function shouldShowTokenUsage(): boolean {
    return vscode.workspace.getConfiguration('codechef').get('showTokenUsage', true);
}

/**
 * Check if cost exceeds alert threshold
 */
export function shouldAlertCost(costUsd: number): boolean {
    const threshold = vscode.workspace.getConfiguration('codechef').get('costAlertThreshold', 0.10);
    return threshold > 0 && costUsd > threshold;
}

/**
 * Format token usage for display
 */
export function formatTokenUsage(tokens: number, costUsd?: number): string {
    const tokenStr = tokens.toLocaleString();
    if (costUsd !== undefined) {
        return `${tokenStr} tokens ($${costUsd.toFixed(4)})`;
    }
    return `${tokenStr} tokens`;
}
