import * as vscode from 'vscode';

export class SessionManager {
    private sessions: Map<string, string> = new Map();
    private sessionTimeout: number = 3600000; // 1 hour

    constructor(private context: vscode.ExtensionContext) {
        // Load persisted sessions
        const saved = context.globalState.get<Record<string, string>>('codechef.sessions', {});
        this.sessions = new Map(Object.entries(saved));

        // Cleanup old sessions periodically
        setInterval(() => this.cleanupSessions(), 300000); // Every 5 minutes
    }

    getOrCreateSession(chatContext: vscode.ChatContext): string {
        // Use chat session ID if available
        const contextKey = this.getChatContextKey(chatContext);
        
        if (this.sessions.has(contextKey)) {
            return this.sessions.get(contextKey)!;
        }

        // Create new session
        const sessionId = this.generateSessionId();
        this.sessions.set(contextKey, sessionId);
        this.persistSessions();
        
        return sessionId;
    }

    private getChatContextKey(chatContext: vscode.ChatContext): string {
        // Create a stable key from chat context
        const history = chatContext.history || [];
        const firstUserMessage = history.find(h => h instanceof vscode.ChatRequestTurn);
        
        if (firstUserMessage) {
            // Use hash of first message as session key
            return this.hashString((firstUserMessage as vscode.ChatRequestTurn).prompt);
        }

        // Fallback to timestamp-based key
        return `session_${Date.now()}`;
    }

    private generateSessionId(): string {
        return `codechef_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    private hashString(str: string): string {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32bit integer
        }
        return `session_${Math.abs(hash).toString(36)}`;
    }

    private persistSessions(): void {
        const obj = Object.fromEntries(this.sessions);
        this.context.globalState.update('codechef.sessions', obj);
    }

    private cleanupSessions(): void {
        // In a real implementation, we'd track last access times
        // For now, just limit session count
        if (this.sessions.size > 50) {
            const entries = Array.from(this.sessions.entries());
            this.sessions = new Map(entries.slice(-25)); // Keep last 25
            this.persistSessions();
        }
    }

    clearSessions(): void {
        this.sessions.clear();
        this.context.globalState.update('codechef.sessions', {});
    }
}
