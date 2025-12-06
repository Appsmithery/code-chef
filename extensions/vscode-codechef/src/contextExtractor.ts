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
                pr_number: null,
                issue_id: null,
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
        
        // Extract PR/issue IDs from branch name
        const branchIds = this.extractIdsFromBranch(gitBranch);

        return {
            workspace_name: workspace.name,
            workspace_path: workspacePath,
            git_branch: gitBranch,
            git_remote: gitRemote,
            
            // GitHub context
            github_repo_url: githubRepoUrl,
            github_commit_sha: commitSha,
            
            // Linear context - team-level binding (CHEF team)
            linear_team_id: this.getLinearTeamId(),
            
            // PR/Issue context (extracted from branch name)
            pr_number: branchIds.prNumber,
            issue_id: branchIds.issueId,
            branch_type: branchIds.branchType,
            
            // Existing fields
            open_files: this.getOpenFiles(),
            project_type: await this.detectProjectType(workspacePath),
            active_editor: this.getActiveEditorContext(),
            languages: this.getWorkspaceLanguages()
        };
    }

    /**
     * Extract PR number, issue ID, and branch type from branch name
     * Supports common branch naming conventions:
     * - feature/123-description
     * - feature/DEV-123-description
     * - fix/ABC-456-bug-title
     * - hotfix/123
     * - release/v1.2.3
     * - pr-123
     */
    private extractIdsFromBranch(branch: string | null): {
        prNumber: string | null;
        issueId: string | null;
        branchType: string | null;
    } {
        if (!branch) {
            return { prNumber: null, issueId: null, branchType: null };
        }

        let prNumber: string | null = null;
        let issueId: string | null = null;
        let branchType: string | null = null;

        // Detect branch type from prefix
        const typeMatch = branch.match(/^(feature|feat|fix|bugfix|hotfix|release|deploy|docs|chore|refactor|test)\//i);
        if (typeMatch) {
            branchType = typeMatch[1].toLowerCase();
        }

        // Extract Linear-style issue ID (e.g., DEV-123, PROJ-456)
        const issueMatch = branch.match(/([A-Z]+-\d+)/i);
        if (issueMatch) {
            issueId = issueMatch[1].toUpperCase();
        }

        // Extract PR number patterns
        // Pattern: pr-123, pr/123
        const prMatch = branch.match(/pr[-\/](\d+)/i);
        if (prMatch) {
            prNumber = prMatch[1];
        }
        
        // Pattern: standalone number after prefix (feature/123-description)
        // Only if we haven't found an issue ID already
        if (!prNumber && !issueId) {
            const numMatch = branch.match(/\/(\d+)[-_]?/);
            if (numMatch) {
                prNumber = numMatch[1];
            }
        }
        
        // Pattern: number at the end (hotfix/critical-fix-123)
        if (!prNumber) {
            const endNumMatch = branch.match(/-(\d+)$/);
            if (endNumMatch) {
                prNumber = endNumMatch[1];
            }
        }

        return { prNumber, issueId, branchType };
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
     * Get Linear team ID from global settings
     * Team-level binding allows @chef to create projects and access all team issues
     */
    private getLinearTeamId(): string | null {
        const config = vscode.workspace.getConfiguration('codechef');
        return config.get('linearTeamId') || null;
    }
}
