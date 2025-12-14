/**
 * Handler for /workflow and /workflows commands
 */
import * as vscode from 'vscode';
import { KNOWN_WORKFLOWS } from '../constants';
import { ContextExtractor } from '../contextExtractor';
import { OrchestratorClient, SmartWorkflowResponse } from '../orchestratorClient';
import { renderToolsList, renderWorkflowSelection, renderWorkflowTemplates } from '../renderers/responseRenderer';
import { getWorkflowSettings } from '../settings';

export class WorkflowHandler {
    constructor(
        private client: OrchestratorClient,
        private contextExtractor: ContextExtractor
    ) {}

    /**
     * Handle /workflow command
     */
    async handleWorkflow(
        args: string,
        stream: vscode.ChatResponseStream
    ): Promise<vscode.ChatResult> {
        const trimmedArgs = args.trim();
        
        if (!trimmedArgs) {
            this.showWorkflowUsage(stream);
            return {};
        }

        stream.progress('Analyzing task and selecting workflow...');

        try {
            // Extract workspace context
            const workspaceContext = await this.contextExtractor.extract();
            const workflowSettings = getWorkflowSettings();
            
            // Parse arguments: first word might be workflow name
            const parts = trimmedArgs.split(/\s+/);
            let explicitWorkflow: string | undefined;
            let taskDescription = trimmedArgs;
            
            // Check if first word matches a known workflow
            if (parts.length > 1 && KNOWN_WORKFLOWS.includes(parts[0] as any)) {
                explicitWorkflow = parts[0];
                taskDescription = parts.slice(1).join(' ');
            } else if (workflowSettings.defaultWorkflow !== 'auto') {
                explicitWorkflow = workflowSettings.defaultWorkflow;
            }

            // Use dry_run if showWorkflowPreview is enabled and autoExecute is false
            const dryRun = workflowSettings.showWorkflowPreview && !workflowSettings.workflowAutoExecute;

            const response = await this.client.smartExecuteWorkflow({
                task_description: taskDescription,
                explicit_workflow: explicitWorkflow,
                context: workspaceContext,
                dry_run: dryRun,
                confirm_threshold: workflowSettings.workflowConfirmThreshold
            });

            // Render selection result
            renderWorkflowSelection(response, stream, dryRun);

            // If requires confirmation, show Quick Pick
            if (response.requires_confirmation && !dryRun) {
                const confirmed = await this.showWorkflowConfirmation(response);
                if (!confirmed) {
                    stream.markdown('\n⚠️ **Workflow execution cancelled by user.**\n');
                    return { metadata: { cancelled: true } };
                }
                
                // Execute after confirmation
                stream.progress('Executing workflow...');
                const executeResponse = await this.client.smartExecuteWorkflow({
                    task_description: taskDescription,
                    explicit_workflow: response.workflow_name,
                    context: workspaceContext,
                    dry_run: false
                });
                
                stream.markdown(`\n✅ **Workflow started!**\n`);
                if (executeResponse.workflow_id) {
                    stream.markdown(`Workflow ID: \`${executeResponse.workflow_id}\`\n`);
                }
            }

            return { 
                metadata: { 
                    workflow: response.workflow_name,
                    confidence: response.confidence,
                    method: response.method,
                    workflow_id: response.workflow_id
                } 
            };
        } catch (error: any) {
            stream.markdown(`\n❌ **Error**: ${error.message}\n`);
            return { errorDetails: { message: error.message } };
        }
    }

    /**
     * Handle /workflows command
     */
    async handleWorkflowsList(
        stream: vscode.ChatResponseStream
    ): Promise<vscode.ChatResult> {
        stream.progress('Fetching available workflows...');

        try {
            const response = await this.client.getWorkflowTemplates();
            renderWorkflowTemplates(response.templates, stream);
            return { metadata: { templateCount: response.count } };
        } catch (error: any) {
            stream.markdown(`❌ Failed to fetch workflows: ${error.message}\n`);
            return { errorDetails: { message: error.message } };
        }
    }

    /**
     * Handle /tools command
     */
    async handleTools(
        stream: vscode.ChatResponseStream
    ): Promise<vscode.ChatResult> {
        stream.progress('Fetching available tools...');

        try {
            const config = vscode.workspace.getConfiguration('codechef');
            const gatewayUrl = config.get('orchestratorUrl', 'https://codechef.appsmithery.co/api');
            
            const response = await fetch(`${gatewayUrl}/tools`);
            const data = await response.json() as { tools: Array<{ name: string; description: string; server: string }> };
            
            renderToolsList(data.tools, stream);
            return { metadata: { toolCount: data.tools.length } };
        } catch (error: any) {
            stream.markdown(`❌ Failed to fetch tools: ${error.message}\n`);
            return { errorDetails: { message: error.message } };
        }
    }

    private showWorkflowUsage(stream: vscode.ChatResponseStream): void {
        stream.markdown('❌ Usage: `@chef /workflow [workflow-name] <task description>`\n\n');
        stream.markdown('Examples:\n');
        stream.markdown('- `@chef /workflow Deploy PR #123 to production` (auto-select)\n');
        stream.markdown('- `@chef /workflow feature Implement user authentication` (explicit)\n');
        stream.markdown('- `@chef /workflow hotfix Fix critical login bug` (explicit)\n\n');
        stream.markdown('Use `@chef /workflows` to see available workflows.\n');
    }

    private async showWorkflowConfirmation(response: SmartWorkflowResponse): Promise<boolean> {
        // Build quick pick items
        const items: vscode.QuickPickItem[] = [
            {
                label: `$(check) Execute ${response.workflow_name}`,
                description: `${Math.round(response.confidence * 100)}% confidence`,
                detail: response.reasoning,
                picked: true
            }
        ];
        
        // Add alternatives
        for (const alt of response.alternatives) {
            items.push({
                label: `$(arrow-right) Use ${alt.workflow} instead`,
                description: `${Math.round((alt.confidence || 0) * 100)}% confidence`
            });
        }
        
        items.push({
            label: '$(x) Cancel',
            description: 'Do not execute any workflow'
        });
        
        const selected = await vscode.window.showQuickPick(items, {
            title: 'Confirm Workflow Selection',
            placeHolder: `Select workflow to execute (${response.method} selection)`
        });
        
        if (!selected || selected.label.includes('Cancel')) {
            return false;
        }
        
        return true;
    }
}
