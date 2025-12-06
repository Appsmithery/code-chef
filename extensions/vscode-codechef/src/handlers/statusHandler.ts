/**
 * Handler for /status and /approve commands
 */
import * as vscode from 'vscode';
import { OrchestratorClient } from '../orchestratorClient';
import { renderTaskStatus } from '../renderers/responseRenderer';

export class StatusHandler {
    constructor(
        private client: OrchestratorClient,
        private getLastTaskId: () => string | undefined
    ) {}

    /**
     * Handle /status command
     */
    async handleStatus(
        taskId: string,
        stream: vscode.ChatResponseStream
    ): Promise<vscode.ChatResult> {
        const id = taskId.trim() || this.getLastTaskId();
        
        if (!id) {
            stream.markdown('❌ No task ID provided. Use: `@chef /status <task-id>`\n');
            return {};
        }

        stream.progress('Checking task status...');

        try {
            const status = await this.client.checkStatus(id);
            renderTaskStatus(id, status, stream);
            return { metadata: { taskId: id } };
        } catch (error: any) {
            stream.markdown(`❌ Failed to get status: ${error.message}\n`);
            return { errorDetails: { message: error.message } };
        }
    }

    /**
     * Handle /approve command
     */
    async handleApprove(
        args: string,
        stream: vscode.ChatResponseStream
    ): Promise<vscode.ChatResult> {
        const [taskId, approvalId] = args.trim().split(/\s+/);
        
        if (!taskId || !approvalId) {
            stream.markdown('❌ Usage: `@chef /approve <task-id> <approval-id>`\n');
            return {};
        }

        stream.progress('Submitting approval...');

        try {
            await this.client.approve(taskId, approvalId);
            stream.markdown(`✅ Task ${taskId} approved! Agents will proceed with execution.\n`);
            return { metadata: { taskId, approvalId } };
        } catch (error: any) {
            stream.markdown(`❌ Failed to approve: ${error.message}\n`);
            return { errorDetails: { message: error.message } };
        }
    }
}
