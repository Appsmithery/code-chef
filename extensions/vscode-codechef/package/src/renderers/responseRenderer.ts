/**
 * Markdown rendering utilities for chat responses
 */
import * as vscode from 'vscode';
import {
    buildLinearIssueUrl,
    getAgentEmoji,
    getConfidenceEmoji,
    getRiskEmoji
} from '../constants';
import type { SmartWorkflowResponse, SubTask, TaskResponse, WorkflowTemplate } from '../orchestratorClient';

// ============================================================================
// Task Response Rendering
// ============================================================================

/**
 * Render a task submission response
 */
export function renderTaskSubmitted(
    response: TaskResponse,
    stream: vscode.ChatResponseStream
): vscode.ChatResult {
    stream.markdown(`## ✅ Task Submitted\n\n`);
    stream.markdown(`**Task ID**: \`${response.task_id}\`\n\n`);
    
    // Subtasks
    stream.markdown(`**Subtasks** (${response.subtasks.length}):\n\n`);
    for (const subtask of response.subtasks) {
        const agentEmoji = getAgentEmoji(subtask.agent_type);
        stream.markdown(`${agentEmoji} **${subtask.agent_type}**: ${subtask.description}\n`);
    }

    // Routing plan
    if (response.routing_plan) {
        stream.markdown(`\n**Estimated Duration**: ${response.routing_plan.estimated_duration_minutes} minutes\n\n`);
    }

    // Approval notification
    if (response.approval_request_id) {
        renderApprovalRequired(response, stream);
    }

    // Observability links
    renderObservabilityLinks(response.task_id, stream);

    return {
        metadata: {
            taskId: response.task_id,
            subtaskCount: response.subtasks.length,
            requiresApproval: !!response.approval_request_id
        }
    };
}

/**
 * Render approval required section
 */
export function renderApprovalRequired(
    response: TaskResponse,
    stream: vscode.ChatResponseStream
): void {
    stream.markdown(`\n⚠️ **Approval Required**\n\n`);
    stream.markdown(`This task requires human approval before execution.\n\n`);
    
    const config = vscode.workspace.getConfiguration('codechef');
    const linearHub = config.get('linearHubIssue', 'DEV-68');
    const workspaceSlug = config.get('linearWorkspaceSlug', 'project-roadmaps');
    const linearUrl = buildLinearIssueUrl(linearHub, workspaceSlug);
    
    stream.markdown(`Check Linear issue [${linearHub}](${linearUrl}) for approval request.\n\n`);
    
    stream.button({
        command: 'codechef.showApprovals',
        title: '📋 View Approvals',
        arguments: []
    });
}

/**
 * Render observability links section
 */
export function renderObservabilityLinks(
    taskId: string,
    stream: vscode.ChatResponseStream
): void {
    stream.markdown(`\n---\n\n`);
    stream.markdown(`**Observability:**\n\n`);
    
    const config = vscode.workspace.getConfiguration('codechef');
    const langsmithUrl = config.get('langsmithUrl');
    if (langsmithUrl) {
        stream.markdown(`- [LangSmith Traces](${langsmithUrl})\n`);
    }
    const grafanaUrl = config.get('grafanaUrl', 'https://appsmithery.grafana.net');
    stream.markdown(`- [Grafana Metrics](${grafanaUrl})\n`);
    stream.markdown(`- Check status: \`@chef /status ${taskId}\`\n`);
}

// ============================================================================
// Linear Project Rendering
// ============================================================================

/**
 * Render Linear project creation notification
 */
export function renderLinearProjectCreated(
    project: { id: string; name: string; url?: string },
    stream: vscode.ChatResponseStream
): void {
    stream.markdown(`\n✨ Created Linear project: **${project.name}**\n`);
    if (project.url) {
        stream.markdown(`📋 [View in Linear](${project.url})\n\n`);
    }
}

// ============================================================================
// Status Rendering
// ============================================================================

/**
 * Render task status response
 */
export function renderTaskStatus(
    taskId: string,
    status: {
        status: string;
        completed_subtasks: number;
        total_subtasks: number;
        subtasks?: SubTask[];
    },
    stream: vscode.ChatResponseStream
): void {
    stream.markdown(`## Task Status: ${taskId}\n\n`);
    stream.markdown(`**Status**: ${status.status}\n`);
    stream.markdown(`**Progress**: ${status.completed_subtasks}/${status.total_subtasks} subtasks\n\n`);
    
    if (status.subtasks && status.subtasks.length > 0) {
        stream.markdown('**Subtasks:**\n\n');
        for (const subtask of status.subtasks) {
            const icon = getStatusIcon(subtask.status);
            stream.markdown(`${icon} **${subtask.agent_type}**: ${subtask.description}\n`);
        }
    }
}

function getStatusIcon(status: string): string {
    switch (status) {
        case 'completed': return '✅';
        case 'in_progress': return '🔄';
        case 'failed': return '❌';
        default: return '⏳';
    }
}

// ============================================================================
// Workflow Rendering
// ============================================================================

/**
 * Render workflow selection result
 */
export function renderWorkflowSelection(
    response: SmartWorkflowResponse,
    stream: vscode.ChatResponseStream,
    dryRun: boolean
): void {
    const confidencePercent = Math.round(response.confidence * 100);
    const confidenceEmoji = getConfidenceEmoji(response.confidence);
    
    stream.markdown(`## 🎯 Workflow Selection\n\n`);
    stream.markdown(`**Selected:** ${response.workflow_name}\n`);
    stream.markdown(`**Confidence:** ${confidenceEmoji} ${confidencePercent}%\n`);
    stream.markdown(`**Method:** ${response.method}\n`);
    
    if (response.reasoning) {
        stream.markdown(`**Reasoning:** ${response.reasoning}\n`);
    }
    
    stream.markdown('\n');
    
    // Show extracted context
    if (Object.keys(response.context_variables).length > 0) {
        stream.markdown('### Extracted Context\n\n');
        for (const [key, value] of Object.entries(response.context_variables)) {
            if (value !== null && value !== undefined) {
                stream.markdown(`- **${key}:** ${value}\n`);
            }
        }
        stream.markdown('\n');
    }
    
    // Show alternatives if available
    if (response.alternatives.length > 0) {
        stream.markdown('### Alternative Workflows\n\n');
        for (const alt of response.alternatives) {
            const altConfidence = Math.round((alt.confidence || 0) * 100);
            stream.markdown(`- ${alt.workflow} (${altConfidence}%)\n`);
        }
        stream.markdown('\n');
    }
    
    // Show status
    if (dryRun) {
        stream.markdown('---\n');
        stream.markdown('📝 **Preview Mode** - Workflow not executed.\n');
        stream.markdown('Set `codechef.showWorkflowPreview` to `false` or use `codechef.workflowAutoExecute` to auto-execute.\n');
    } else if (response.requires_confirmation) {
        stream.markdown('---\n');
        stream.markdown('⚠️ **Confirmation Required** - Confidence below threshold.\n');
    } else if (response.workflow_id) {
        stream.markdown('---\n');
        stream.markdown(`✅ **Workflow Started!** ID: \`${response.workflow_id}\`\n`);
        stream.markdown(`Status: ${response.execution_status}\n`);
    } else if (response.execution_status === 'error') {
        stream.markdown('---\n');
        stream.markdown('❌ **Workflow Failed to Start**\n');
    }
}

/**
 * Render workflow templates list
 */
export function renderWorkflowTemplates(
    templates: WorkflowTemplate[],
    stream: vscode.ChatResponseStream
): void {
    stream.markdown(`## 📋 Available Workflows (${templates.length})\n\n`);
    
    for (const template of templates) {
        const riskEmoji = getRiskEmoji(template.risk_level);
        const agentEmojis = template.agents_involved.map(a => getAgentEmoji(a)).join(' ');
        
        stream.markdown(`### ${template.name}\n`);
        stream.markdown(`${template.description}\n\n`);
        stream.markdown(`| Property | Value |\n`);
        stream.markdown(`|----------|-------|\n`);
        stream.markdown(`| Template | \`${template.template_name}\` |\n`);
        stream.markdown(`| Version | ${template.version} |\n`);
        stream.markdown(`| Risk Level | ${riskEmoji} ${template.risk_level} |\n`);
        stream.markdown(`| Steps | ${template.steps_count} |\n`);
        stream.markdown(`| Duration | ~${template.estimated_duration_minutes} min |\n`);
        stream.markdown(`| Agents | ${agentEmojis} ${template.agents_involved.join(', ')} |\n`);
        
        if (template.required_context.length > 0) {
            stream.markdown(`| Required Context | \`${template.required_context.join('`, `')}\` |\n`);
        }
        
        stream.markdown('\n');
    }
    
    stream.markdown('---\n\n');
    stream.markdown('**Usage:** `@chef /workflow [name] <task description>`\n\n');
    stream.markdown('**Example:** `@chef /workflow pr-deployment Deploy PR #123 to production`\n');
}

// ============================================================================
// Tools Rendering
// ============================================================================

/**
 * Render tools list grouped by server
 */
export function renderToolsList(
    tools: Array<{ name: string; description: string; server: string }>,
    stream: vscode.ChatResponseStream
): void {
    stream.markdown(`## Available MCP Tools (${tools.length})\n\n`);
    
    // Group by server
    const byServer: Record<string, typeof tools> = {};
    for (const tool of tools) {
        if (!byServer[tool.server]) {
            byServer[tool.server] = [];
        }
        byServer[tool.server].push(tool);
    }

    for (const [server, serverTools] of Object.entries(byServer)) {
        stream.markdown(`### ${server} (${serverTools.length} tools)\n\n`);
        for (const tool of serverTools.slice(0, 5)) {
            stream.markdown(`- **${tool.name}**: ${tool.description}\n`);
        }
        if (serverTools.length > 5) {
            stream.markdown(`- ... and ${serverTools.length - 5} more\n`);
        }
        stream.markdown('\n');
    }
}

// ============================================================================
// Error Rendering
// ============================================================================

/**
 * Render error with troubleshooting tips
 */
export function renderError(
    error: Error,
    stream: vscode.ChatResponseStream
): void {
    stream.markdown(`\n\n❌ **Error**: ${error.message}\n\n`);
    
    if (error.message.includes('ECONNREFUSED') || error.message.includes('timeout')) {
        stream.markdown('**Troubleshooting:**\n');
        stream.markdown('1. Check orchestrator URL in settings: `code/chef: Configure`\n');
        stream.markdown('2. Verify service is running: `curl https://codechef.appsmithery.co/api/health`\n');
        stream.markdown('3. Check firewall allows outbound connections\n\n');
    }
}

/**
 * Render connection troubleshooting tips
 */
export function renderConnectionTroubleshooting(
    stream: vscode.ChatResponseStream
): void {
    stream.markdown('**Troubleshooting:**\n');
    stream.markdown('1. Check orchestrator URL in settings: `code/chef: Configure`\n');
    stream.markdown('2. Verify service is running: `curl https://codechef.appsmithery.co/api/health`\n');
    stream.markdown('3. Check firewall allows outbound connections\n\n');
}
