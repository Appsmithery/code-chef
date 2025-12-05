import * as path from 'path';
import * as vscode from 'vscode';
import { CodeChefChatParticipant } from './chatParticipant';
import { registerCopyPermalinkCommand } from './commands/copyPermalink';
import { LinearWatcher } from './linearWatcher';
import { OrchestratorClient } from './orchestratorClient';

// Agent icon mapping for UI display (agents are LangGraph nodes, not separate services)
const AGENT_ICONS: { [key: string]: string } = {
    'orchestrator': 'orchestrator.png',      // Purple - Coordination
    'feature-dev': 'feature-dev.png',        // Blue - Development
    'code-review': 'code-review.png',        // Green - Quality
    'infrastructure': 'infrastructure.png',  // Navy - Infrastructure
    'cicd': 'cicd.png',                      // Orange - Deployment
    'documentation': 'documentation.png'     // Teal - Knowledge
};

let chatParticipant: CodeChefChatParticipant;
let linearWatcher: LinearWatcher;
let statusBarItem: vscode.StatusBarItem;
let extensionContext: vscode.ExtensionContext;

function buildLinearIssueUrl(issueId: string, workspaceSlug?: string): string {
    const slug = workspaceSlug ?? vscode.workspace.getConfiguration('codechef').get('linearWorkspaceSlug', 'project-roadmaps');
    return `https://linear.app/${slug}/issue/${issueId}`;
}

function getAgentIconPath(agentName: string): string {
    const iconFile = AGENT_ICONS[agentName] || AGENT_ICONS['orchestrator'];
    return extensionContext.asAbsolutePath(path.join('src', 'icons', iconFile));
}

export function getAgentIcon(agentName: string): vscode.Uri {
    return vscode.Uri.file(getAgentIconPath(agentName));
}

export function getAgentColor(agentName: string): string {
    const colors: { [key: string]: string } = {
        'orchestrator': '#9333EA',      // Purple
        'feature-dev': '#3B82F6',       // Blue
        'code-review': '#22C55E',       // Green
        'infrastructure': '#1E3A8A',    // Navy
        'cicd': '#F97316',              // Orange
        'documentation': '#14B8A6'      // Teal
    };
    return colors[agentName] || colors['orchestrator'];
}

export function activate(context: vscode.ExtensionContext) {
    console.log('code/chef extension activating...');
    extensionContext = context;
    
    try {
        // Initialize status bar
        statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        statusBarItem.text = '$(rocket) code/chef';
        statusBarItem.tooltip = 'code/chef LangGraph Orchestrator - Click for menu';
        statusBarItem.command = 'codechef.showMenu';
        statusBarItem.show();
        context.subscriptions.push(statusBarItem);
        console.log('code/chef: Status bar created');

        // Initialize chat participant
        chatParticipant = new CodeChefChatParticipant(context);
        
        // Register chat participant (may fail if Copilot Chat not available)
        try {
            const participant = vscode.chat.createChatParticipant(
                'codechef',
                chatParticipant.handleChatRequest.bind(chatParticipant)
            );
            
            // Set icon for the chat participant
            participant.iconPath = vscode.Uri.joinPath(context.extensionUri, 'icon.png');
            
            context.subscriptions.push(participant);
            console.log('code/chef: Chat participant registered as @codechef');
        } catch (chatError) {
            console.warn('code/chef: Could not register chat participant (Copilot Chat may not be available):', chatError);
            vscode.window.showWarningMessage(
                'code/chef: Chat participant requires GitHub Copilot. Use Command Palette commands instead.',
                'Open Commands'
            ).then(selection => {
                if (selection === 'Open Commands') {
                    vscode.commands.executeCommand('workbench.action.showCommands');
                }
            });
        }

    // Initialize Linear watcher for approval notifications
    linearWatcher = new LinearWatcher(context);
    const config = vscode.workspace.getConfiguration('codechef');
    const workspaceSlug = config.get('linearWorkspaceSlug', 'dev-ops');
    if (config.get('enableNotifications')) {
        linearWatcher.start(config.get('linearHubIssue', 'DEV-68'), workspaceSlug);
    }
    context.subscriptions.push(linearWatcher);

    // Register copy permalink command
    registerCopyPermalinkCommand(context);

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('codechef.orchestrate', async () => {
            const task = await vscode.window.showInputBox({
                prompt: 'Describe your development task',
                placeHolder: 'e.g., Add JWT authentication to my Express API'
            });
            
            if (task) {
                await chatParticipant.submitTask(task);
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('codechef.checkStatus', async () => {
            const taskId = await vscode.window.showInputBox({
                prompt: 'Enter task ID',
                placeHolder: 'e.g., a1b2c3d4-e5f6-7890-abcd-ef1234567890'
            });
            
            if (taskId) {
                await chatParticipant.checkTaskStatus(taskId);
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('codechef.configure', async () => {
            const url = await vscode.window.showInputBox({
                prompt: 'Enter orchestrator URL',
                value: config.get('orchestratorUrl'),
                validateInput: (value) => {
                    try {
                        new URL(value);
                        return null;
                    } catch {
                        return 'Please enter a valid URL';
                    }
                }
            });
            
            if (url) {
                await config.update('orchestratorUrl', url, vscode.ConfigurationTarget.Global);
                vscode.window.showInformationMessage(`Orchestrator URL updated to ${url}`);
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('codechef.showApprovals', async () => {
            const linearHubIssue = config.get('linearHubIssue', 'PR-68');
            const linearUrl = buildLinearIssueUrl(linearHubIssue, workspaceSlug);
            vscode.env.openExternal(vscode.Uri.parse(linearUrl));
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('codechef.clearCache', () => {
            chatParticipant.clearCache();
            vscode.window.showInformationMessage('code/chef cache cleared');
        })
    );

    // Register status bar menu command
    context.subscriptions.push(
        vscode.commands.registerCommand('codechef.showMenu', async () => {
            const config = vscode.workspace.getConfiguration('codechef');
            const orchestratorUrl = config.get('orchestratorUrl', 'https://codechef.appsmithery.co/api');
            const langsmithUrl = config.get('langsmithUrl', '');
            
            const items: vscode.QuickPickItem[] = [
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
        })
    );

    // Register health check command
    context.subscriptions.push(
        vscode.commands.registerCommand('codechef.healthCheck', async () => {
            const config = vscode.workspace.getConfiguration('codechef');
            const url = config.get<string>('orchestratorUrl', 'https://codechef.appsmithery.co/api');
            const apiKey = config.get<string>('apiKey') || undefined;
            
            vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'Checking orchestrator health...',
                cancellable: false
            }, async () => {
                await checkOrchestratorHealth(url, apiKey);
            });
        })
    );

    // Register open LangSmith command
    context.subscriptions.push(
        vscode.commands.registerCommand('codechef.openLangsmith', () => {
            const config = vscode.workspace.getConfiguration('codechef');
            const url = config.get('langsmithUrl', 'https://smith.langchain.com');
            vscode.env.openExternal(vscode.Uri.parse(url));
        })
    );

    // Register open Grafana command
    context.subscriptions.push(
        vscode.commands.registerCommand('codechef.openGrafana', () => {
            vscode.env.openExternal(vscode.Uri.parse('https://appsmithery.grafana.net'));
        })
    );

    // Register open settings command
    context.subscriptions.push(
        vscode.commands.registerCommand('codechef.openSettings', () => {
            vscode.commands.executeCommand('workbench.action.openSettings', 'codechef');
        })
    );

        // Check orchestrator health on startup
        checkOrchestratorHealth(config.get('orchestratorUrl')!, config.get('apiKey') || undefined);

        console.log('code/chef extension activated');
    } catch (error) {
        console.error('code/chef: Fatal activation error:', error);
        vscode.window.showErrorMessage(`code/chef extension failed to activate: ${error}`);
    }
}

async function checkOrchestratorHealth(url: string, apiKey?: string) {
    try {
        const client = new OrchestratorClient({ baseUrl: url, apiKey });
        const health = await client.health();
        
        if (health.status === 'ok') {
            statusBarItem.text = '$(check) code/chef';
            statusBarItem.tooltip = `Connected to ${url}`;
        } else {
            statusBarItem.text = '$(warning) code/chef';
            statusBarItem.tooltip = 'Orchestrator unhealthy';
        }
    } catch (error) {
        statusBarItem.text = '$(error) code/chef';
        statusBarItem.tooltip = `Cannot reach orchestrator at ${url}`;
        
        vscode.window.showErrorMessage(
            'Cannot connect to code/chef orchestrator. Check configuration.',
            'Configure'
        ).then(selection => {
            if (selection === 'Configure') {
                vscode.commands.executeCommand('codechef.configure');
            }
        });
    }
}

export function deactivate() {
    if (linearWatcher) {
        linearWatcher.dispose();
    }
    if (statusBarItem) {
        statusBarItem.dispose();
    }
}
