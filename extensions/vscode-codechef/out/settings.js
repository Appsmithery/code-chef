"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.getSettings = getSettings;
exports.getWorkflowSettings = getWorkflowSettings;
exports.getTokenOptimizationSettings = getTokenOptimizationSettings;
exports.buildWorkspaceConfig = buildWorkspaceConfig;
exports.shouldShowTokenUsage = shouldShowTokenUsage;
exports.shouldAlertCost = shouldAlertCost;
exports.formatTokenUsage = formatTokenUsage;
const vscode = __importStar(require("vscode"));
/**
 * Get all code/chef settings from VS Code configuration
 */
function getSettings() {
    const config = vscode.workspace.getConfiguration('codechef');
    return {
        // Connection
        orchestratorUrl: config.get('orchestratorUrl', 'https://codechef.appsmithery.co/api'),
        apiKey: config.get('apiKey', ''),
        // Environment & Model Selection
        environment: config.get('environment', 'production'),
        // Tool Loading (Token Optimization)
        toolLoadingStrategy: config.get('toolLoadingStrategy', 'progressive'),
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
        autoApproveThreshold: config.get('autoApproveThreshold', 'low'),
        enableNotifications: config.get('enableNotifications', true),
        linearHubIssue: config.get('linearHubIssue', 'DEV-68'),
        linearWorkspaceSlug: config.get('linearWorkspaceSlug', 'dev-ops'),
        // Workflow Settings
        defaultWorkflow: config.get('defaultWorkflow', 'auto'),
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
function getWorkflowSettings() {
    const config = vscode.workspace.getConfiguration('codechef');
    return {
        defaultWorkflow: config.get('defaultWorkflow', 'auto'),
        workflowAutoExecute: config.get('workflowAutoExecute', true),
        workflowConfirmThreshold: config.get('workflowConfirmThreshold', 0.7),
        showWorkflowPreview: config.get('showWorkflowPreview', true)
    };
}
/**
 * Get token optimization settings for API requests
 */
function getTokenOptimizationSettings() {
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
function buildWorkspaceConfig() {
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
function shouldShowTokenUsage() {
    return vscode.workspace.getConfiguration('codechef').get('showTokenUsage', true);
}
/**
 * Check if cost exceeds alert threshold
 */
function shouldAlertCost(costUsd) {
    const threshold = vscode.workspace.getConfiguration('codechef').get('costAlertThreshold', 0.10);
    return threshold > 0 && costUsd > threshold;
}
/**
 * Format token usage for display
 */
function formatTokenUsage(tokens, costUsd) {
    const tokenStr = tokens.toLocaleString();
    if (costUsd !== undefined) {
        return `${tokenStr} tokens ($${costUsd.toFixed(4)})`;
    }
    return `${tokenStr} tokens`;
}
//# sourceMappingURL=settings.js.map