import * as vscode from 'vscode';
import { DevToolsChatParticipant } from './chatParticipant';
import { LinearWatcher } from './linearWatcher';
import { OrchestratorClient } from './orchestratorClient';

let chatParticipant: DevToolsChatParticipant;
let linearWatcher: LinearWatcher;
let statusBarItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext) {
    console.log('Dev-Tools extension activating...');

    // Initialize status bar
    statusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right,
        100
    );
    statusBarItem.text = '$(rocket) Dev-Tools';
    statusBarItem.tooltip = 'Dev-Tools Orchestrator - Click to check status';
    statusBarItem.command = 'devtools.checkStatus';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    // Register chat participant
    chatParticipant = new DevToolsChatParticipant(context);
    const participant = vscode.chat.createChatParticipant(
        'devtools',
        chatParticipant.handleChatRequest.bind(chatParticipant)
    );
    participant.iconPath = vscode.Uri.joinPath(context.extensionUri, 'icon.png');
    context.subscriptions.push(participant);

    // Initialize Linear watcher for approval notifications
    linearWatcher = new LinearWatcher(context);
    const config = vscode.workspace.getConfiguration('devtools');
    if (config.get('enableNotifications')) {
        linearWatcher.start(config.get('linearHubIssue', 'PR-68'));
    }
    context.subscriptions.push(linearWatcher);

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('devtools.orchestrate', async () => {
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
        vscode.commands.registerCommand('devtools.checkStatus', async () => {
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
        vscode.commands.registerCommand('devtools.configure', async () => {
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
        vscode.commands.registerCommand('devtools.showApprovals', async () => {
            const linearHubIssue = config.get('linearHubIssue', 'PR-68');
            const linearUrl = `https://linear.app/appsmithery/issue/${linearHubIssue}`;
            vscode.env.openExternal(vscode.Uri.parse(linearUrl));
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('devtools.clearCache', () => {
            chatParticipant.clearCache();
            vscode.window.showInformationMessage('Dev-Tools cache cleared');
        })
    );

    // Check orchestrator health on startup
    checkOrchestratorHealth(config.get('orchestratorUrl')!);

    console.log('Dev-Tools extension activated');
}

async function checkOrchestratorHealth(url: string) {
    try {
        const client = new OrchestratorClient(url);
        const health = await client.health();
        
        if (health.status === 'ok') {
            statusBarItem.text = '$(check) Dev-Tools';
            statusBarItem.tooltip = `Connected to ${url}`;
        } else {
            statusBarItem.text = '$(warning) Dev-Tools';
            statusBarItem.tooltip = 'Orchestrator unhealthy';
        }
    } catch (error) {
        statusBarItem.text = '$(error) Dev-Tools';
        statusBarItem.tooltip = `Cannot reach orchestrator at ${url}`;
        
        vscode.window.showErrorMessage(
            'Cannot connect to Dev-Tools orchestrator. Check configuration.',
            'Configure'
        ).then(selection => {
            if (selection === 'Configure') {
                vscode.commands.executeCommand('devtools.configure');
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
