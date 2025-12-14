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
exports.getAgentColor = void 0;
exports.getAgentIcon = getAgentIcon;
exports.activate = activate;
exports.deactivate = deactivate;
const path = __importStar(require("path"));
const vscode = __importStar(require("vscode"));
const chatParticipant_1 = require("./chatParticipant");
const copyPermalink_1 = require("./commands/copyPermalink");
const modelops = __importStar(require("./commands/modelops"));
const constants_1 = require("./constants");
const linearWatcher_1 = require("./linearWatcher");
const orchestratorClient_1 = require("./orchestratorClient");
let chatParticipant;
let linearWatcher;
let statusBarItem;
let extensionContext;
function getAgentIconPath(agentName) {
    const iconFile = constants_1.AGENT_ICONS[agentName] || constants_1.AGENT_ICONS['orchestrator'];
    return extensionContext.asAbsolutePath(path.join('src', 'icons', iconFile));
}
function getAgentIcon(agentName) {
    return vscode.Uri.file(getAgentIconPath(agentName));
}
// Re-export getAgentColor from constants for backward compatibility
exports.getAgentColor = constants_1.getAgentColor;
function activate(context) {
    console.log('code/chef extension activating...');
    extensionContext = context;
    try {
        // Initialize status bar
        statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
        statusBarItem.text = '$(rocket) code/chef';
        statusBarItem.tooltip = 'code/chef LangGraph Orchestrator - Click for menu';
        statusBarItem.command = 'codechef.showMenu';
        statusBarItem.show();
        context.subscriptions.push(statusBarItem);
        console.log('code/chef: Status bar created');
        // Initialize chat participant
        chatParticipant = new chatParticipant_1.CodeChefChatParticipant(context);
        // Register chat participant (may fail if Copilot Chat not available)
        try {
            console.log('code/chef: Attempting to register chat participant vscode-codechef.chef...');
            const participant = vscode.chat.createChatParticipant('vscode-codechef.chef', chatParticipant.handleChatRequest.bind(chatParticipant));
            // Set icon for the chat participant
            participant.iconPath = vscode.Uri.joinPath(context.extensionUri, 'icon.png');
            context.subscriptions.push(participant);
            console.log('code/chef: Chat participant registered successfully as @chef');
            // Show success notification on first install
            const hasShownWelcome = context.globalState.get('hasShownChatWelcome', false);
            if (!hasShownWelcome) {
                vscode.window.showInformationMessage('code/chef: Chat participant @chef is ready! Open Copilot Chat and type @chef to get started.', 'Open Chat').then(selection => {
                    if (selection === 'Open Chat') {
                        vscode.commands.executeCommand('workbench.action.chat.open');
                    }
                });
                context.globalState.update('hasShownChatWelcome', true);
            }
        }
        catch (chatError) {
            console.error('code/chef: Failed to register chat participant:', chatError);
            vscode.window.showWarningMessage('code/chef: Chat participant requires GitHub Copilot. Use Command Palette commands instead.', 'Open Commands').then(selection => {
                if (selection === 'Open Commands') {
                    vscode.commands.executeCommand('workbench.action.showCommands');
                }
            });
        }
        // Initialize Linear watcher for approval notifications (non-blocking)
        linearWatcher = new linearWatcher_1.LinearWatcher(context);
        const config = vscode.workspace.getConfiguration('codechef');
        const workspaceSlug = config.get('linearWorkspaceSlug', 'dev-ops');
        context.subscriptions.push(linearWatcher);
        // Start watcher asynchronously to avoid blocking activation
        if (config.get('enableNotifications')) {
            setTimeout(() => {
                linearWatcher.start(config.get('linearHubIssue', 'DEV-68'), workspaceSlug);
            }, 1000);
        }
        // Register copy permalink command
        (0, copyPermalink_1.registerCopyPermalinkCommand)(context);
        // Register commands
        context.subscriptions.push(vscode.commands.registerCommand('codechef.orchestrate', async () => {
            const task = await vscode.window.showInputBox({
                prompt: 'Describe your development task',
                placeHolder: 'e.g., Add JWT authentication to my Express API'
            });
            if (task) {
                await chatParticipant.submitTask(task);
            }
        }));
        context.subscriptions.push(vscode.commands.registerCommand('codechef.checkStatus', async () => {
            const taskId = await vscode.window.showInputBox({
                prompt: 'Enter task ID',
                placeHolder: 'e.g., a1b2c3d4-e5f6-7890-abcd-ef1234567890'
            });
            if (taskId) {
                await chatParticipant.checkTaskStatus(taskId);
            }
        }));
        context.subscriptions.push(vscode.commands.registerCommand('codechef.configure', async () => {
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
        context.subscriptions.push(vscode.commands.registerCommand('codechef.showApprovals', async () => {
            const linearHubIssue = config.get('linearHubIssue', 'PR-68');
            const linearUrl = (0, constants_1.buildLinearIssueUrl)(linearHubIssue, workspaceSlug);
            vscode.env.openExternal(vscode.Uri.parse(linearUrl));
        }));
        context.subscriptions.push(vscode.commands.registerCommand('codechef.clearCache', () => {
            chatParticipant.clearCache();
            vscode.window.showInformationMessage('code/chef cache cleared');
        }));
        // Register status bar menu command
        context.subscriptions.push(vscode.commands.registerCommand('codechef.showMenu', async () => {
            const config = vscode.workspace.getConfiguration('codechef');
            const orchestratorUrl = config.get('orchestratorUrl', 'https://codechef.appsmithery.co/api');
            // langsmithUrl reserved for future use
            const items = [
                {
                    label: '$(rocket) Submit Task',
                    description: 'Send a development task to the orchestrator',
                    detail: 'codechef.orchestrate'
                },
                {
                    label: '$(search) Check Task Status',
                    description: 'Check the status of a submitted task',
                    detail: 'codechef.checkStatus'
                },
                {
                    label: '$(checklist) View Pending Approvals',
                    description: 'Open Linear to see HITL approval requests',
                    detail: 'codechef.showApprovals'
                },
                { label: '', kind: vscode.QuickPickItemKind.Separator },
                {
                    label: '$(pulse) Health Check',
                    description: `Test connection to ${orchestratorUrl}`,
                    detail: 'codechef.healthCheck'
                },
                {
                    label: '$(link-external) Open LangSmith Traces',
                    description: 'View LLM traces and debugging',
                    detail: 'codechef.openLangsmith'
                },
                {
                    label: '$(graph) Open Grafana Metrics',
                    description: 'View Prometheus dashboards',
                    detail: 'codechef.openGrafana'
                },
                { label: '', kind: vscode.QuickPickItemKind.Separator },
                {
                    label: '$(gear) Configure Orchestrator URL',
                    description: 'Change the orchestrator endpoint',
                    detail: 'codechef.configure'
                },
                {
                    label: '$(settings-gear) Open Settings',
                    description: 'View all code/chef settings',
                    detail: 'codechef.openSettings'
                },
                {
                    label: '$(trash) Clear Cache',
                    description: 'Clear session and tool cache',
                    detail: 'codechef.clearCache'
                }
            ];
            const selected = await vscode.window.showQuickPick(items, {
                placeHolder: 'code/chef - Select an action',
                matchOnDescription: true
            });
            if (selected && selected.detail) {
                vscode.commands.executeCommand(selected.detail);
            }
        }));
        // Register health check command
        context.subscriptions.push(vscode.commands.registerCommand('codechef.healthCheck', async () => {
            const config = vscode.workspace.getConfiguration('codechef');
            const url = config.get('orchestratorUrl', 'https://codechef.appsmithery.co/api');
            const apiKey = config.get('apiKey') || undefined;
            vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'Checking orchestrator health...',
                cancellable: false
            }, async () => {
                await checkOrchestratorHealth(url, apiKey);
            });
        }));
        // Register open LangSmith command
        context.subscriptions.push(vscode.commands.registerCommand('codechef.openLangsmith', () => {
            const config = vscode.workspace.getConfiguration('codechef');
            const url = config.get('langsmithUrl', 'https://smith.langchain.com');
            vscode.env.openExternal(vscode.Uri.parse(url));
        }));
        // Register open Grafana command
        context.subscriptions.push(vscode.commands.registerCommand('codechef.openGrafana', () => {
            const config = vscode.workspace.getConfiguration('codechef');
            const url = config.get('grafanaUrl', 'https://appsmithery.grafana.net');
            vscode.env.openExternal(vscode.Uri.parse(url));
        }));
        // Register open settings command
        context.subscriptions.push(vscode.commands.registerCommand('codechef.openSettings', () => {
            vscode.commands.executeCommand('workbench.action.openSettings', 'codechef');
        }));
        // Register ModelOps commands
        const orchestratorClient = new orchestratorClient_1.OrchestratorClient(config.get('orchestratorUrl', 'https://codechef.appsmithery.co/api'), config.get('apiKey') || undefined);
        context.subscriptions.push(vscode.commands.registerCommand('codechef.modelops.trainAgent', async () => {
            await modelops.trainAgentModel(orchestratorClient, context);
        }));
        context.subscriptions.push(vscode.commands.registerCommand('codechef.modelops.evaluateAgent', async () => {
            await modelops.evaluateAgentModel(orchestratorClient);
        }));
        context.subscriptions.push(vscode.commands.registerCommand('codechef.modelops.deployModel', async () => {
            await modelops.deployModel(orchestratorClient);
        }));
        context.subscriptions.push(vscode.commands.registerCommand('codechef.modelops.listModels', async () => {
            await modelops.listAgentModels(orchestratorClient);
        }));
        context.subscriptions.push(vscode.commands.registerCommand('codechef.modelops.convertToGGUF', async () => {
            await modelops.convertToGGUF(orchestratorClient);
        }));
        // Check orchestrator health on startup
        checkOrchestratorHealth(config.get('orchestratorUrl'), config.get('apiKey') || undefined);
        console.log('code/chef extension activated');
    }
    catch (error) {
        console.error('code/chef: Fatal activation error:', error);
        vscode.window.showErrorMessage(`code/chef extension failed to activate: ${error}`);
    }
}
async function checkOrchestratorHealth(url, apiKey) {
    try {
        const client = new orchestratorClient_1.OrchestratorClient({ baseUrl: url, apiKey });
        const health = await client.health();
        if (health.status === 'ok') {
            statusBarItem.text = '$(check) code/chef';
            statusBarItem.tooltip = `Connected to ${url}`;
        }
        else {
            statusBarItem.text = '$(warning) code/chef';
            statusBarItem.tooltip = 'Orchestrator unhealthy';
        }
    }
    catch (error) {
        statusBarItem.text = '$(error) code/chef';
        statusBarItem.tooltip = `Cannot reach orchestrator at ${url}`;
        vscode.window.showErrorMessage('Cannot connect to code/chef orchestrator. Check configuration.', 'Configure').then(selection => {
            if (selection === 'Configure') {
                vscode.commands.executeCommand('codechef.configure');
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