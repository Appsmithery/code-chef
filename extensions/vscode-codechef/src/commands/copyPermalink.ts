import { execSync } from 'child_process';
import * as vscode from 'vscode';

/**
 * Register the "Copy GitHub Permalink" command.
 * 
 * Generates a permanent GitHub URL to the selected code with commit SHA.
 * Works with both single-line and multi-line selections.
 */
export function registerCopyPermalinkCommand(context: vscode.ExtensionContext) {
    const command = vscode.commands.registerCommand(
        'codechef.copyPermalink',
        async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showErrorMessage('No active editor');
                return;
            }

            const selection = editor.selection;
            const document = editor.document;
            
            // Get file path relative to workspace
            const workspaceFolder = vscode.workspace.getWorkspaceFolder(document.uri);
            if (!workspaceFolder) {
                vscode.window.showErrorMessage('File not in workspace');
                return;
            }

            // Convert to Unix-style path (GitHub uses forward slashes)
            const relativePath = document.uri.fsPath
                .replace(workspaceFolder.uri.fsPath + '\\', '')
                .replace(/\\/g, '/');

            // Get current commit SHA
            let commitSha: string;
            try {
                commitSha = execSync('git rev-parse HEAD', {
                    cwd: workspaceFolder.uri.fsPath,
                    encoding: 'utf-8'
                }).trim();
            } catch (error) {
                vscode.window.showErrorMessage('Failed to get git commit SHA. Is this a git repository?');
                return;
            }

            // Get git remote URL
            let repoUrl: string;
            try {
                const remoteUrl = execSync('git config --get remote.origin.url', {
                    cwd: workspaceFolder.uri.fsPath,
                    encoding: 'utf-8'
                }).trim();
                
                // Convert SSH URL to HTTPS
                if (remoteUrl.startsWith('git@github.com:')) {
                    repoUrl = remoteUrl
                        .replace('git@github.com:', 'https://github.com/')
                        .replace(/\.git$/, '');
                } else if (remoteUrl.startsWith('https://github.com')) {
                    repoUrl = remoteUrl.replace(/\.git$/, '');
                } else {
                    vscode.window.showErrorMessage('Not a GitHub repository');
                    return;
                }
            } catch (error) {
                vscode.window.showErrorMessage('Failed to get git remote URL');
                return;
            }

            // Build permalink
            const lineStart = selection.start.line + 1;
            const lineEnd = selection.end.line + 1;
            
            let permalink = `${repoUrl}/blob/${commitSha}/${relativePath}`;
            
            // Add line numbers
            if (selection.isEmpty) {
                // No selection - link to current line
                permalink += `#L${lineStart}`;
            } else if (lineStart === lineEnd) {
                // Single line selected
                permalink += `#L${lineStart}`;
            } else {
                // Multi-line selection
                permalink += `#L${lineStart}-L${lineEnd}`;
            }

            // Copy to clipboard
            await vscode.env.clipboard.writeText(permalink);
            
            // Show confirmation
            const lineRangeText = lineStart === lineEnd 
                ? `L${lineStart}` 
                : `L${lineStart}-L${lineEnd}`;
            
            vscode.window.showInformationMessage(
                `📎 GitHub permalink copied: ${relativePath}#${lineRangeText}`
            );
        }
    );

    context.subscriptions.push(command);
}
