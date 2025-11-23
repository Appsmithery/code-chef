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
exports.registerCopyPermalinkCommand = registerCopyPermalinkCommand;
const child_process_1 = require("child_process");
const vscode = __importStar(require("vscode"));
/**
 * Register the "Copy GitHub Permalink" command.
 *
 * Generates a permanent GitHub URL to the selected code with commit SHA.
 * Works with both single-line and multi-line selections.
 */
function registerCopyPermalinkCommand(context) {
    const command = vscode.commands.registerCommand('devtools.copyPermalink', async () => {
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
        let commitSha;
        try {
            commitSha = (0, child_process_1.execSync)('git rev-parse HEAD', {
                cwd: workspaceFolder.uri.fsPath,
                encoding: 'utf-8'
            }).trim();
        }
        catch (error) {
            vscode.window.showErrorMessage('Failed to get git commit SHA. Is this a git repository?');
            return;
        }
        // Get git remote URL
        let repoUrl;
        try {
            const remoteUrl = (0, child_process_1.execSync)('git config --get remote.origin.url', {
                cwd: workspaceFolder.uri.fsPath,
                encoding: 'utf-8'
            }).trim();
            // Convert SSH URL to HTTPS
            if (remoteUrl.startsWith('git@github.com:')) {
                repoUrl = remoteUrl
                    .replace('git@github.com:', 'https://github.com/')
                    .replace(/\.git$/, '');
            }
            else if (remoteUrl.startsWith('https://github.com')) {
                repoUrl = remoteUrl.replace(/\.git$/, '');
            }
            else {
                vscode.window.showErrorMessage('Not a GitHub repository');
                return;
            }
        }
        catch (error) {
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
        }
        else if (lineStart === lineEnd) {
            // Single line selected
            permalink += `#L${lineStart}`;
        }
        else {
            // Multi-line selection
            permalink += `#L${lineStart}-L${lineEnd}`;
        }
        // Copy to clipboard
        await vscode.env.clipboard.writeText(permalink);
        // Show confirmation
        const lineRangeText = lineStart === lineEnd
            ? `L${lineStart}`
            : `L${lineStart}-L${lineEnd}`;
        vscode.window.showInformationMessage(`📎 GitHub permalink copied: ${relativePath}#${lineRangeText}`);
    });
    context.subscriptions.push(command);
}
//# sourceMappingURL=copyPermalink.js.map