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
                github_repo_url: null,
                github_commit_sha: null,
                linear_project_id: null,
                open_files: [],
                project_type: 'unknown',
                active_editor: null
            };
        }

        const workspacePath = workspace.uri.fsPath;
        const gitBranch = await this.getGitBranch(workspacePath);
        const gitRemote = await this.getGitRemote(workspacePath);
        const githubRepoUrl = this.parseGitHubUrl(gitRemote);
        const commitSha = await this.getCommitSha(workspacePath, gitBranch);
        const linearProjectId = this.getLinearProjectId();

        return {
            workspace_name: workspace.name,
            workspace_path: workspacePath,
            git_branch: gitBranch,
            git_remote: gitRemote,
            
            // GitHub context
            github_repo_url: githubRepoUrl,
            github_commit_sha: commitSha,
            
            // Linear context (may be null for new projects)
            linear_project_id: linearProjectId,
            
            // Existing fields
            open_files: this.getOpenFiles(),
            project_type: await this.detectProjectType(workspacePath),
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

    /**
     * Parse GitHub URL from git remote
     * Handles both SSH and HTTPS formats
     */
    private parseGitHubUrl(gitRemote: string | null): string | null {
        if (!gitRemote) return null;
        
        // SSH: git@github.com:owner/repo.git
        const sshMatch = gitRemote.match(/git@github\.com:([^\/]+\/[^\.]+)\.git/);
        if (sshMatch) {
            return `https://github.com/${sshMatch[1]}`;
        }
        
        // HTTPS: https://github.com/owner/repo.git
        const httpsMatch = gitRemote.match(/https:\/\/github\.com\/([^\/]+\/[^\.]+)\.git/);
        if (httpsMatch) {
            return `https://github.com/${httpsMatch[1]}`;
        }
        
        // Already clean HTTPS URL
        const cleanMatch = gitRemote.match(/https:\/\/github\.com\/([^\/]+\/[^\/]+)/);
        if (cleanMatch) {
            return `https://github.com/${cleanMatch[1]}`;
        }
        
        return null;
    }

    /**
     * Get current commit SHA from git
     * Reads directly from .git/refs/heads/<branch>
     */
    private async getCommitSha(workspacePath: string, branch: string | null): Promise<string | null> {
        if (!branch) return null;
        
        try {
            const refPath = path.join(workspacePath, '.git', 'refs', 'heads', branch);
            const sha = await fs.readFile(refPath, 'utf-8');
            return sha.trim();
        } catch {
            // Try packed-refs fallback
            try {
                const packedRefsPath = path.join(workspacePath, '.git', 'packed-refs');
                const content = await fs.readFile(packedRefsPath, 'utf-8');
                const match = content.match(new RegExp(`^([a-f0-9]{40}) refs/heads/${branch}$`, 'm'));
                return match ? match[1] : null;
            } catch {
                return null;
            }
        }
    }

    /**
     * Get Linear project ID from workspace settings (if exists)
     */
    private getLinearProjectId(): string | null {
        const config = vscode.workspace.getConfiguration('codechef.linear');
        return config.get('projectId') || null;
    }

    /**
     * Save Linear project ID to workspace settings
     * Called after orchestrator creates new project
     */
    async saveLinearProjectId(projectId: string): Promise<void> {
        const config = vscode.workspace.getConfiguration('codechef.linear');
        await config.update('projectId', projectId, vscode.ConfigurationTarget.Workspace);
    }
}
