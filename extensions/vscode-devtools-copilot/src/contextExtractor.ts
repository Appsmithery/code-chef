import * as fs from 'fs/promises';
import * as path from 'path';
import * as vscode from 'vscode';

export class ContextExtractor {
    async extract(): Promise<Record<string, any>> {
        const workspace = vscode.workspace.workspaceFolders?.[0];
        if (!workspace) {
            return {
                workspace_name: 'unknown',
                workspace_path: null,
                git_branch: null,
                open_files: [],
                project_type: 'unknown',
                active_editor: null
            };
        }

        return {
            workspace_name: workspace.name,
            workspace_path: workspace.uri.fsPath,
            git_branch: await this.getGitBranch(workspace.uri.fsPath),
            git_remote: await this.getGitRemote(workspace.uri.fsPath),
            open_files: this.getOpenFiles(),
            project_type: await this.detectProjectType(workspace.uri.fsPath),
            active_editor: this.getActiveEditorContext(),
            languages: this.getWorkspaceLanguages()
        };
    }

    private async getGitBranch(workspacePath: string): Promise<string | null> {
        try {
            const gitHeadPath = path.join(workspacePath, '.git', 'HEAD');
            const content = await fs.readFile(gitHeadPath, 'utf-8');
            const match = content.match(/ref: refs\/heads\/(.+)/);
            return match ? match[1].trim() : null;
        } catch {
            return null;
        }
    }

    private async getGitRemote(workspacePath: string): Promise<string | null> {
        try {
            const gitConfigPath = path.join(workspacePath, '.git', 'config');
            const content = await fs.readFile(gitConfigPath, 'utf-8');
            const match = content.match(/\[remote "origin"\][^\[]*url = (.+)/);
            return match ? match[1].trim() : null;
        } catch {
            return null;
        }
    }

    private getOpenFiles(): string[] {
        return vscode.workspace.textDocuments
            .filter(doc => !doc.isUntitled && doc.uri.scheme === 'file')
            .map(doc => vscode.workspace.asRelativePath(doc.uri))
            .slice(0, 20); // Limit to 20 files to avoid context bloat
    }

    private async detectProjectType(workspacePath: string): Promise<string> {
        const indicators = [
            { file: 'package.json', type: 'node' },
            { file: 'requirements.txt', type: 'python' },
            { file: 'pyproject.toml', type: 'python' },
            { file: 'Cargo.toml', type: 'rust' },
            { file: 'go.mod', type: 'go' },
            { file: 'pom.xml', type: 'java' },
            { file: 'build.gradle', type: 'java' },
            { file: '.csproj', type: 'csharp' },
            { file: 'Gemfile', type: 'ruby' }
        ];

        for (const indicator of indicators) {
            try {
                const files = await fs.readdir(workspacePath);
                if (files.some(f => f.endsWith(indicator.file) || f === indicator.file)) {
                    return indicator.type;
                }
            } catch {}
        }

        return 'unknown';
    }

    private getActiveEditorContext(): any {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            return null;
        }

        const selection = editor.selection;
        const selectedText = editor.document.getText(selection);

        return {
            file: vscode.workspace.asRelativePath(editor.document.uri),
            language: editor.document.languageId,
            line: selection.active.line + 1,
            column: selection.active.character,
            selection: selectedText.length > 0 ? selectedText : null,
            selection_lines: selectedText.length > 0 ? 
                (selectedText.match(/\n/g) || []).length + 1 : 0
        };
    }

    private getWorkspaceLanguages(): string[] {
        const languages = new Set<string>();
        
        for (const doc of vscode.workspace.textDocuments) {
            if (!doc.isUntitled && doc.uri.scheme === 'file') {
                languages.add(doc.languageId);
            }
        }

        return Array.from(languages).slice(0, 10); // Top 10 languages
    }
}
