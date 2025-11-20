import * as vscode from 'vscode';

export class LinearWatcher {
    private statusBarItem: vscode.StatusBarItem;
    private pollInterval?: NodeJS.Timeout;
    private isWatching: boolean = false;
    private workspaceSlug: string = 'project-roadmaps';

    constructor(private context: vscode.ExtensionContext) {
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        this.statusBarItem.text = '$(check) Dev-Tools';
        this.statusBarItem.tooltip = 'Dev-Tools Orchestrator - Click to view approvals';
        this.statusBarItem.command = 'devtools.showApprovals';
    }

    start(linearHubIssue: string, workspaceSlug: string): void {
        if (this.isWatching) {
            return;
        }

        this.isWatching = true;
        this.statusBarItem.show();
        this.workspaceSlug = workspaceSlug || 'project-roadmaps';

        // Check for Linear extension
        const linearExtension = vscode.extensions.getExtension('linear.linear-vscode');
        
        if (linearExtension) {
            this.watchViaLinearExtension(linearHubIssue);
        } else {
            // Fallback: poll orchestrator for pending approvals
            this.pollForApprovals();
        }
    }

    stop(): void {
        this.isWatching = false;
        
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = undefined;
        }
    }

    private async watchViaLinearExtension(issueId: string): Promise<void> {
        const linearExtension = vscode.extensions.getExtension('linear.linear-vscode');
        
        if (!linearExtension) {
            return;
        }

        if (!linearExtension.isActive) {
            await linearExtension.activate();
        }

        // Use Linear extension API if available
        const linear = linearExtension.exports;
        
        if (linear && typeof linear.subscribeToIssue === 'function') {
            linear.subscribeToIssue(issueId, (update: any) => {
                if (update.type === 'comment' && 
                    (update.body.includes('@devtools') || update.body.includes('approval'))) {
                    this.showApprovalNotification(update);
                }
            });
        } else {
            // Linear extension doesn't support subscriptions, fall back to polling
            this.pollForApprovals();
        }
    }

    private pollForApprovals(): void {
        const config = vscode.workspace.getConfiguration('devtools');
        const orchestratorUrl = config.get('orchestratorUrl');
        
        if (!orchestratorUrl) {
            return;
        }

        this.pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`${orchestratorUrl}/approvals/pending`);
                
                if (!response.ok) {
                    return;
                }

                const approvals = await response.json();
                
                if (Array.isArray(approvals) && approvals.length > 0) {
                    this.statusBarItem.text = `$(alert) ${approvals.length} approval(s)`;
                    this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
                    
                    // Show notification for first approval
                    if (config.get('enableNotifications')) {
                        this.showApprovalNotification(approvals[0]);
                    }
                } else {
                    this.statusBarItem.text = '$(check) Dev-Tools';
                    this.statusBarItem.backgroundColor = undefined;
                }
            } catch (error) {
                console.error('Failed to poll approvals:', error);
                this.statusBarItem.text = '$(error) Dev-Tools';
            }
        }, 30000); // Poll every 30 seconds
    }

    private showApprovalNotification(update: any): void {
        const message = update.title || update.description || 'Dev-Tools approval needed';
        
        vscode.window.showInformationMessage(
            message,
            'View in Linear',
            'Approve',
            'Dismiss'
        ).then(selection => {
            if (selection === 'View in Linear') {
                const config = vscode.workspace.getConfiguration('devtools');
                const linearHub = config.get('linearHubIssue', 'PR-68');
                const url = `https://linear.app/${this.workspaceSlug}/issue/${linearHub}`;
                vscode.env.openExternal(vscode.Uri.parse(url));
            } else if (selection === 'Approve') {
                // Open Copilot chat with pre-filled approval command
                vscode.commands.executeCommand('workbench.action.chat.open', {
                    query: `@devtools /approve ${update.task_id || update.id} ${update.approval_id || ''}`
                });
            }
        });
    }

    dispose(): void {
        this.stop();
        this.statusBarItem.dispose();
    }
}
