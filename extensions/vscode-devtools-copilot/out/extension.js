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
exports.getAgentIcon = getAgentIcon;
exports.getAgentColor = getAgentColor;
exports.activate = activate;
exports.deactivate = deactivate;
const path = __importStar(require("path"));
const vscode = __importStar(require("vscode"));
const chatParticipant_1 = require("./chatParticipant");
const copyPermalink_1 = require("./commands/copyPermalink");
const linearWatcher_1 = require("./linearWatcher");
const orchestratorClient_1 = require("./orchestratorClient");
// Agent icon mapping for UI display (agents are LangGraph nodes, not separate services)
const AGENT_ICONS = {
    'orchestrator': 'orchestrator.png', // Purple - Coordination
    'feature-dev': 'feature-dev.png', // Blue - Development
    'code-review': 'code-review.png', // Green - Quality
    'infrastructure': 'infrastructure.png', // Navy - Infrastructure
    'cicd': 'cicd.png', // Orange - Deployment
    'documentation': 'documentation.png' // Teal - Knowledge
};
let chatParticipant;
let linearWatcher;
let statusBarItem;
let extensionContext;
function buildLinearIssueUrl(issueId, workspaceSlug) {
    const slug = workspaceSlug ?? vscode.workspace.getConfiguration('devtools').get('linearWorkspaceSlug', 'project-roadmaps');
    return `https://linear.app/${slug}/issue/${issueId}`;
}
function getAgentIconPath(agentName) {
    const iconFile = AGENT_ICONS[agentName] || AGENT_ICONS['orchestrator'];
    return extensionContext.asAbsolutePath(path.join('src', 'icons', iconFile));
}
function getAgentIcon(agentName) {
    return vscode.Uri.file(getAgentIconPath(agentName));
}
function getAgentColor(agentName) {
    const colors = {
        'orchestrator': '#9333EA', // Purple
        'feature-dev': '#3B82F6', // Blue
        'code-review': '#22C55E', // Green
        'infrastructure': '#1E3A8A', // Navy
        'cicd': '#F97316', // Orange
        'documentation': '#14B8A6' // Teal
    };
    return colors[agentName] || colors['orchestrator'];
}
function activate(context) {
    console.log('Dev-Tools extension activating...');
    extensionContext = context;
    try {
        // Initialize status bar
        statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
        statusBarItem.text = '$(rocket) Dev-Tools';
        statusBarItem.tooltip = 'Dev-Tools LangGraph Orchestrator - Click to check status';
        statusBarItem.command = 'devtools.checkStatus';
        statusBarItem.show();
        context.subscriptions.push(statusBarItem);
        console.log('Dev-Tools: Status bar created');
        // Initialize chat participant
        chatParticipant = new chatParticipant_1.DevToolsChatParticipant(context);
        // Register chat participant (may fail if Copilot Chat not available)
        try {
            const participant = vscode.chat.createChatParticipant('devtools', chatParticipant.handleChatRequest.bind(chatParticipant));
            context.subscriptions.push(participant);
            console.log('Dev-Tools: Chat participant registered as @devtools');
        }
        catch (chatError) {
            console.warn('Dev-Tools: Could not register chat participant (Copilot Chat may not be available):', chatError);
            vscode.window.showWarningMessage('Dev-Tools: Chat participant requires GitHub Copilot. Use Command Palette commands instead.', 'Open Commands').then(selection => {
                if (selection === 'Open Commands') {
                    vscode.commands.executeCommand('workbench.action.showCommands');
                }
            });
        }
        // Initialize Linear watcher for approval notifications
        linearWatcher = new linearWatcher_1.LinearWatcher(context);
        const config = vscode.workspace.getConfiguration('devtools');
        const workspaceSlug = config.get('linearWorkspaceSlug', 'dev-ops');
        if (config.get('enableNotifications')) {
            linearWatcher.start(config.get('linearHubIssue', 'DEV-68'), workspaceSlug);
        }
        context.subscriptions.push(linearWatcher);
        // Register copy permalink command
        (0, copyPermalink_1.registerCopyPermalinkCommand)(context);
        // Register commands
        context.subscriptions.push(vscode.commands.registerCommand('devtools.orchestrate', async () => {
            const task = await vscode.window.showInputBox({
                prompt: 'Describe your development task',
                placeHolder: 'e.g., Add JWT authentication to my Express API'
            });
            if (task) {
                await chatParticipant.submitTask(task);
            }
        }));
        context.subscriptions.push(vscode.commands.registerCommand('devtools.checkStatus', async () => {
            const taskId = await vscode.window.showInputBox({
                prompt: 'Enter task ID',
                placeHolder: 'e.g., a1b2c3d4-e5f6-7890-abcd-ef1234567890'
            });
            if (taskId) {
                await chatParticipant.checkTaskStatus(taskId);
            }
        }));
        context.subscriptions.push(vscode.commands.registerCommand('devtools.configure', async () => {
            const url = await vscode.window.showInputBox({
                prompt: 'Enter orchestrator URL',
                value: config.get('orchestratorUrl'),
                validateInput: (value) => {
                    try {
                        new URL(value);
                        return null;
                    }
                    catch {
                        return 'Please enter a valid URL';
                    }
                }
            });
            if (url) {
                await config.update('orchestratorUrl', url, vscode.ConfigurationTarget.Global);
                vscode.window.showInformationMessage(`Orchestrator URL updated to ${url}`);
            }
        }));
        context.subscriptions.push(vscode.commands.registerCommand('devtools.showApprovals', async () => {
            const linearHubIssue = config.get('linearHubIssue', 'PR-68');
            const linearUrl = buildLinearIssueUrl(linearHubIssue, workspaceSlug);
            vscode.env.openExternal(vscode.Uri.parse(linearUrl));
        }));
        context.subscriptions.push(vscode.commands.registerCommand('devtools.clearCache', () => {
            chatParticipant.clearCache();
            vscode.window.showInformationMessage('Dev-Tools cache cleared');
        }));
        // Check orchestrator health on startup
        checkOrchestratorHealth(config.get('orchestratorUrl'));
        console.log('Dev-Tools extension activated');
    }
    catch (error) {
        console.error('Dev-Tools: Fatal activation error:', error);
        vscode.window.showErrorMessage(`Dev-Tools extension failed to activate: ${error}`);
    }
}
async function checkOrchestratorHealth(url) {
    try {
        const client = new orchestratorClient_1.OrchestratorClient(url);
        const health = await client.health();
        if (health.status === 'ok') {
            statusBarItem.text = '$(check) Dev-Tools';
            statusBarItem.tooltip = `Connected to ${url}`;
        }
        else {
            statusBarItem.text = '$(warning) Dev-Tools';
            statusBarItem.tooltip = 'Orchestrator unhealthy';
        }
    }
    catch (error) {
        statusBarItem.text = '$(error) Dev-Tools';
        statusBarItem.tooltip = `Cannot reach orchestrator at ${url}`;
        vscode.window.showErrorMessage('Cannot connect to Dev-Tools orchestrator. Check configuration.', 'Configure').then(selection => {
            if (selection === 'Configure') {
                vscode.commands.executeCommand('devtools.configure');
            }
        });
    }
}
function deactivate() {
    if (linearWatcher) {
        linearWatcher.dispose();
    }
    if (statusBarItem) {
        statusBarItem.dispose();
    }
}
//# sourceMappingURL=extension.js.map