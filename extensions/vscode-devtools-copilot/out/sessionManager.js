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
exports.SessionManager = void 0;
const vscode = __importStar(require("vscode"));
class SessionManager {
    constructor(context) {
        this.context = context;
        this.sessions = new Map();
        this.sessionTimeout = 3600000; // 1 hour
        // Load persisted sessions
        const saved = context.globalState.get('devtools.sessions', {});
        this.sessions = new Map(Object.entries(saved));
        // Cleanup old sessions periodically
        setInterval(() => this.cleanupSessions(), 300000); // Every 5 minutes
    }
    getOrCreateSession(chatContext) {
        // Use chat session ID if available
        const contextKey = this.getChatContextKey(chatContext);
        if (this.sessions.has(contextKey)) {
            return this.sessions.get(contextKey);
        }
        // Create new session
        const sessionId = this.generateSessionId();
        this.sessions.set(contextKey, sessionId);
        this.persistSessions();
        return sessionId;
    }
    getChatContextKey(chatContext) {
        // Create a stable key from chat context
        const history = chatContext.history || [];
        const firstUserMessage = history.find(h => h instanceof vscode.ChatRequestTurn);
        if (firstUserMessage) {
            // Use hash of first message as session key
            return this.hashString(firstUserMessage.prompt);
        }
        // Fallback to timestamp-based key
        return `session_${Date.now()}`;
    }
    generateSessionId() {
        return `devtools_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    hashString(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Convert to 32bit integer
        }
        return `session_${Math.abs(hash).toString(36)}`;
    }
    persistSessions() {
        const obj = Object.fromEntries(this.sessions);
        this.context.globalState.update('devtools.sessions', obj);
    }
    cleanupSessions() {
        // In a real implementation, we'd track last access times
        // For now, just limit session count
        if (this.sessions.size > 50) {
            const entries = Array.from(this.sessions.entries());
            this.sessions = new Map(entries.slice(-25)); // Keep last 25
            this.persistSessions();
        }
    }
    clearSessions() {
        this.sessions.clear();
        this.context.globalState.update('devtools.sessions', {});
    }
}
exports.SessionManager = SessionManager;
//# sourceMappingURL=sessionManager.js.map