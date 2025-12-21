# Execute Command Gating - Migration Guide

**Effective Date**: December 20, 2025  
**Breaking Change**: Yes  
**Impact**: User interaction model

---

## What Changed

### Before (Old Behavior)

- `/chat/stream` used LLM-based intent recognition to automatically detect task submissions
- Unpredictable behavior due to LLM hallucinations
- Users had no explicit control over when agents were invoked
- Confusion about conversational vs agent mode

### After (New Behavior)

- `/chat/stream` is **purely conversational** - Ask mode only
- **Explicit `/execute` command** required for task execution - Agent mode
- Clear separation of concerns
- Predictable, user-controlled behavior

---

## New Command Structure

### Available Commands

| Command                 | Purpose                          | Example                                 |
| ----------------------- | -------------------------------- | --------------------------------------- |
| `/execute <task>`       | Submit task for agent execution  | `/execute Implement JWT authentication` |
| `/help`                 | Show available commands and help | `/help`                                 |
| `/status <workflow_id>` | Check workflow status            | `/status exec-abc123`                   |
| `/cancel <workflow_id>` | Cancel running workflow          | `/cancel exec-abc123`                   |

### When to Use Each Mode

**Conversational Mode** (`/chat/stream` - no command):

- Ask questions about your codebase
- Get explanations of concepts
- Discuss architecture decisions
- Code reviews and analysis
- General conversation

**Agent Mode** (`/execute` command):

- Implement new features
- Fix bugs
- Refactor code
- Deploy to environments
- Run tests
- Generate documentation

---

## Migration Examples

### Example 1: Implementing a Feature

**Old (implicit)**:

```
implement login feature with JWT
```

_Sometimes triggered agent mode, sometimes stayed conversational_

**New (explicit)**:

```
/execute implement login feature with JWT
```

_Always triggers agent mode, creates Linear issue, routes to appropriate agent_

---

### Example 2: Asking Questions

**Old**:

```
how does authentication work in this codebase?
```

_Usually conversational, but could accidentally trigger agents_

**New**:

```
how does authentication work in this codebase?
```

_Always conversational - no risk of accidental agent invocation_

---

### Example 3: Getting Help

**Old**:

```
help me understand the command structure
```

_Attempted to answer via LLM_

**New**:

```
/help
```

_Shows formatted command reference_

---

## Linear Integration

### What Happens When You Use `/execute`

1. **Parent Issue Created**

   - Created in Linear project (default: CHEF)
   - Title: "Task: [your request]"
   - Description: Full task details
   - Labels: `orchestrator`, `in-progress`

2. **Supervisor Routes Task**

   - Analyzes task and selects appropriate agent
   - Provides routing reasoning

3. **Subissue Created**

   - One subissue per agent involved
   - Title: "[AGENT-NAME] [task snippet]"
   - Description: Agent assignment reasoning
   - Labels: `[agent-name]`, `subtask`
   - Parent: Links to parent issue

4. **Execution Tracking**
   - Subissue marked "In Progress" when agent starts
   - Subissue marked "Done" when agent completes
   - Parent issue updated with progress
   - Parent issue marked "Done" when workflow completes

### Example Linear Issue Structure

```
Parent: CHEF-123 "Task: Implement JWT authentication"
├── Subissue: CHEF-124 "[FEATURE-DEV] Implement JWT authentication"
│   Status: Done ✅
└── Subissue: CHEF-125 "[CODE-REVIEW] Review JWT implementation"
    Status: In Progress ⏳
```

---

## SSE Event Changes

### New Event Types

**`workflow_status`** - Workflow progress updates:

```json
{
  "type": "workflow_status",
  "status": "issue_created" | "agent_routed" | "subissue_created",
  "issue_id": "CHEF-123",
  "issue_url": "https://linear.app/...",
  "agent": "feature_dev",
  "reasoning": "Task requires code implementation"
}
```

**`redirect`** - Command redirect notification:

```json
{
  "type": "redirect",
  "endpoint": "/execute/stream",
  "reason": "explicit_command",
  "task": "implement login feature"
}
```

---

## Updating Your Integration

### VS Code Extension

No changes required - extension automatically supports new command structure.

**Optional Enhancement**: Add command palette integration:

```typescript
vscode.commands.registerCommand("codechef.executeTask", async () => {
  const task = await vscode.window.showInputBox({
    prompt: "Describe the task to execute",
    placeHolder: "e.g., Implement login feature with OAuth",
  });

  if (task) {
    chatPanel.sendMessage(`/execute ${task}`);
  }
});
```

### API Clients

**Before**:

```typescript
// POST /chat/stream
{
  "message": "implement login feature",
  "user_id": "user-123"
}
// Unpredictable: might trigger agent or stay conversational
```

**After**:

```typescript
// For conversational chat
// POST /chat/stream
{
  "message": "how does authentication work?",
  "user_id": "user-123"
}

// For task execution (NEW)
// POST /chat/stream with /execute command
{
  "message": "/execute implement login feature",
  "user_id": "user-123"
}

// Or POST directly to /execute/stream
{
  "message": "implement login feature",
  "user_id": "user-123"
}
```

### Monitoring Changes

**Metrics to Track**:

- `command_parse_total{command="execute"}` - Execute command usage
- `linear_issue_created_total` - Issues created per task
- `workflow_routing_total{agent="feature_dev"}` - Agent utilization

**Logs to Monitor**:

- `[Chat Stream] /execute command detected` - Command usage
- `[Execute Stream] Creating parent Linear issue` - Issue creation
- `[Execute Stream] Created subissue: CHEF-123 for feature_dev` - Agent routing

---

## Backwards Compatibility

### Deprecated Behavior (Removed)

- Automatic intent recognition in `/chat/stream`
- LLM-based task detection
- Implicit agent mode switching

### Still Supported

- `/execute/stream` endpoint (direct task submission)
- All existing SSE event types
- Session continuity via `session_id`
- Project context passing

---

## Troubleshooting

### "My task isn't executing"

**Problem**: Sent task as regular chat message without `/execute`

**Solution**: Prefix your task with `/execute`:

```
/execute implement the feature
```

### "I see a hint about using /execute"

**Problem**: Your message looks like a task but you didn't use `/execute`

**Solution**: If you want agent execution, use `/execute`. If you just want to discuss, continue as normal.

### "Linear issues aren't being created"

**Possible Causes**:

1. Linear API key not configured
2. Project ID not found
3. Linear API rate limit

**Check**:

```bash
# View logs
docker logs deploy-orchestrator-1 | grep "Linear"

# Check Linear client health
curl http://localhost:8001/health | jq '.dependencies.linear'
```

### "Agent isn't being routed correctly"

**Check**:

```bash
# View supervisor reasoning
docker logs deploy-orchestrator-1 | grep "Supervisor routed to"

# Check agent registry
curl http://localhost:8001/agents
```

---

## FAQ

**Q: Can I still use `/execute/stream` directly?**  
A: Yes! `/execute/stream` still works and is the underlying endpoint.

**Q: What if I forget to use `/execute`?**  
A: Your message will be conversational. If it looks task-like, you'll see a hint.

**Q: Will my existing sessions break?**  
A: No. Existing sessions continue to work. New behavior applies to new messages.

**Q: Can I disable Linear integration?**  
A: Linear integration gracefully degrades - execution continues even if Linear fails.

**Q: How do I see all my execute tasks?**  
A: Visit Linear project (default: CHEF) and filter by `orchestrator` label.

**Q: Can I execute multiple tasks at once?**  
A: Not yet. Future enhancement: `/execute batch task1, task2, task3`

---

## Rollback Procedure

If you need to rollback to the previous behavior:

```bash
# 1. Check out previous commit
git log --oneline | grep "before command gating"
git checkout <commit-hash>

# 2. Rebuild and deploy
docker compose down
docker compose build
docker compose up -d

# 3. Verify
curl http://localhost:8001/health
```

---

## Feedback

Report issues or suggestions:

- Linear: Create issue in CHEF project with label `command-gating`
- GitHub: Open issue in `Appsmithery/code-chef` repo
- Logs: Check `docker logs deploy-orchestrator-1`

---

## Timeline

- **December 20, 2025**: Command gating implemented
- **December 21, 2025**: Deploy to production droplet
- **December 22, 2025**: Monitor usage patterns
- **January 2026**: Evaluate multi-agent workflow improvements

---

**Questions?** File an issue in Linear with label `command-gating`.
