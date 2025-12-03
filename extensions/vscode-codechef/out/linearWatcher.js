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
exports.LinearWatcher = void 0;
const vscode = __importStar(require("vscode"));
class LinearWatcher {
    constructor(context) {
        this.context = context;
        this.isWatching = false;
        this.workspaceSlug = 'project-roadmaps';
        this.statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
        this.statusBarItem.text = '$(check) code/chef';
        this.statusBarItem.tooltip = 'code/chef Orchestrator - Click to view approvals';
        this.statusBarItem.command = 'codechef.showApprovals';
    }
    start(linearHubIssue, workspaceSlug) {
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
        }
        else {
            // Fallback: poll orchestrator for pending approvals
            this.pollForApprovals();
        }
    }
    stop() {
        this.isWatching = false;
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = undefined;
        }
    }
    async watchViaLinearExtension(issueId) {
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
            linear.subscribeToIssue(issueId, (update) => {
                if (update.type === 'comment' &&
                    (update.body.includes('@codechef') || update.body.includes('approval'))) {
                    this.showApprovalNotification(update);
                }
            });
        }
        else {
            // Linear extension doesn't support subscriptions, fall back to polling
            this.pollForApprovals();
        }
    }
    pollForApprovals() {
        const config = vscode.workspace.getConfiguration('codechef');
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
                }
                else {
                    this.statusBarItem.text = '$(check) code/chef';
                    this.statusBarItem.backgroundColor = undefined;
                }
            }
            catch (error) {
                console.error('Failed to poll approvals:', error);
                this.statusBarItem.text = '$(error) code/chef';
            }
        }, 30000); // Poll every 30 seconds
    }
    showApprovalNotification(update) {
        const message = update.title || update.description || 'code/chef approval needed';
        vscode.window.showInformationMessage(message, 'View in Linear', 'Approve', 'Dismiss').then(selection => {
            if (selection === 'View in Linear') {
                const config = vscode.workspace.getConfiguration('codechef');
                const linearHub = config.get('linearHubIssue', 'PR-68');
                const url = `https://linear.app/${this.workspaceSlug}/issue/${linearHub}`;
                vscode.env.openExternal(vscode.Uri.parse(url));
            }
            else if (selection === 'Approve') {
                // Open Copilot chat with pre-filled approval command
                vscode.commands.executeCommand('workbench.action.chat.open', {
                    query: `@codechef /approve ${update.task_id || update.id} ${update.approval_id || ''}`
                });
            }
        });
    }
    dispose() {
        this.stop();
        this.statusBarItem.dispose();
    }
}
exports.LinearWatcher = LinearWatcher;
//# sourceMappingURL=linearWatcher.js.map