# Copilot Context Enhancement - Implementation Plan

**Date**: December 13, 2025  
**Version**: 1.0  
**Status**: Ready for Execution  
**Target Release**: v1.0.0-beta.4

---

## Executive Summary

This plan implements three key enhancements to leverage Copilot's chat context:

1. **✅ Tier 1A: Capture Chat References** (MUST - User Priority)

   - Capture files/symbols selected in chat
   - Pass to orchestrator for better RAG context
   - **Effort**: 30 lines, **Value**: High

2. **✅ Tier 1B: Prompt Enhancement with Copilot** (User Requested)

   - Use Copilot model to expand ambiguous requests
   - Opt-in via config (default: off)
   - **Effort**: 60 lines, **Value**: Medium-High

3. **✅ Tier 1C: Capture Copilot Model Metadata** (Telemetry)
   - Track model selection for analytics
   - **Effort**: 5 lines, **Value**: High (long-term)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Feature 1: Chat References](#feature-1-chat-references)
3. [Feature 2: Prompt Enhancement](#feature-2-prompt-enhancement)
4. [Feature 3: Model Telemetry](#feature-3-model-telemetry)
5. [Agent System Prompt Optimizations](#agent-system-prompt-optimizations)
6. [Testing Strategy](#testing-strategy)
7. [Rollout Plan](#rollout-plan)

---

## Architecture Overview

### Current Flow

```
User → VS Code Chat → Extension
                      ↓ (raw prompt)
                  Orchestrator → Agents
```

### Enhanced Flow

```
User → VS Code Chat → Extension
                      ↓
                  1. Capture references (files/symbols)
                  2. Enhance prompt with Copilot (optional)
                  3. Capture model metadata
                      ↓
                  Orchestrator → Agents
                  (with enriched context)
```

### Data Flow

```typescript
// Extension (TypeScript)
ChatRequest {
    prompt: string,
    references: ChatPromptReference[],  // NEW: captured
    model: LanguageModelChat            // NEW: captured
}
    ↓
// Enhanced prompt (if enabled)
enhancedPrompt = await copilotEnhance(prompt, model)
    ↓
// Orchestrator Request (Python)
ChatStreamRequest {
    message: enhancedPrompt,            // Enhanced if enabled
    context: {
        ...workspaceContext,
        chat_references: {...},         // NEW
        copilot_model: {...}           // NEW
    }
}
```

---

## Feature 1: Chat References

### Problem

When users select files/symbols in chat (using `#file` or right-click → "Add to Chat"), the extension **doesn't capture these references**. Orchestrator can't use them for:

- Targeted RAG queries
- Direct file reading
- Context-aware responses

### Solution

Capture `request.references` and pass to orchestrator in `context.chat_references`.

### Implementation

#### Step 1.1: Extract Chat References in Extension

**File**: `extensions/vscode-codechef/src/chatParticipant.ts`

**Location**: In `handleStreamingChat()` method, before calling `client.chatStream()`

**Code**:

```typescript
// After: const workspaceContext = await this.contextExtractor.extract();
// Add:

/**
 * Extract chat references (files/symbols selected by user).
 * These provide explicit context signals for better RAG queries.
 */
private extractChatReferences(references: readonly vscode.ChatPromptReference[]) {
    const files: string[] = [];
    const symbols: Array<{file: string; line: number; name?: string}> = [];
    const strings: string[] = [];

    for (const ref of references) {
        if (ref.value instanceof vscode.Uri) {
            // File reference (#file)
            files.push(ref.value.fsPath);
        } else if (ref.value instanceof vscode.Location) {
            // Symbol reference (function, class, etc.)
            symbols.push({
                file: ref.value.uri.fsPath,
                line: ref.value.range.start.line,
                name: undefined  // VS Code doesn't provide symbol name in Location
            });
        } else if (typeof ref.value === 'string') {
            // String reference (variable name, etc.)
            strings.push(ref.value);
        }
        // Note: SymbolInformation not commonly used in chat refs
    }

    return {
        files,
        symbols,
        strings,
        count: files.length + symbols.length + strings.length
    };
}
```

**Usage**:

```typescript
// In handleStreamingChat():
const chatReferences = this.extractChatReferences(request.references);

// Log for debugging (remove after UAT)
if (chatReferences.count > 0) {
  console.log(
    `code/chef: Captured ${chatReferences.count} chat references`,
    chatReferences
  );
}

await this.client.chatStream({
  message: userMessage,
  session_id: sessionId,
  context: {
    ...workspaceContext,
    chat_references: chatReferences, // NEW
  },
  workspace_config: buildWorkspaceConfig(),
});
```

#### Step 1.2: Update Type Definitions

**File**: `extensions/vscode-codechef/src/orchestratorClient.ts`

**Add interface**:

```typescript
export interface ChatReferences {
  files: string[];
  symbols: Array<{ file: string; line: number; name?: string }>;
  strings: string[];
  count: number;
}

// Update ChatStreamRequest interface
export interface ChatStreamRequest {
  message: string;
  session_id?: string;
  user_id?: string;
  context?: Record<string, any>; // Now includes chat_references
  workspace_config?: Record<string, any>;
}
```

#### Step 1.3: Backend Support (Python)

**File**: `agent_orchestrator/main.py`

**Update model** (already flexible via `context: Optional[Dict[str, Any]]`):

```python
class ChatStreamRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None  # Contains chat_references now
    workspace_config: Optional[Dict[str, Any]] = None
    project_context: Optional[Dict[str, Any]] = None
```

**Access in agents**:

```python
# In BaseAgent or specific agents
chat_refs = state.get("context", {}).get("chat_references", {})
referenced_files = chat_refs.get("files", [])

# Use for RAG queries
if referenced_files:
    # Query RAG service with explicit file filter
    rag_results = await query_rag(
        query=task_description,
        file_filter=referenced_files  # Scope search to these files
    )
```

#### Step 1.4: Update Tracing Schema

**File**: `config/observability/tracing-schema.yaml`

```yaml
# Add to existing schema
metadata:
  # ... existing fields

  chat_references_count:
    type: integer
    description: "Number of files/symbols referenced in chat"
    optional: true

  referenced_files:
    type: array
    items: string
    description: "File paths explicitly referenced in chat"
    optional: true
```

**Log in traces**:

```python
# In chat_stream_endpoint or supervisor_node
@traceable(
    name="chat_stream",
    metadata=lambda: {
        "chat_references_count": len(request.context.get("chat_references", {}).get("files", [])),
        "referenced_files": request.context.get("chat_references", {}).get("files", [])[:5]  # First 5
    }
)
```

---

## Feature 2: Prompt Enhancement

### Problem

Ambiguous user requests lead to poor task decomposition:

- "fix the bug" → which bug?
- "add tests" → for what?
- "deploy" → deploy what to where?

### Solution

Use Copilot's selected model to expand ambiguous requests into structured descriptions **before** sending to orchestrator.

### Design Principles (from vscode-prompt-tsx)

1. **Token Budget Awareness**: Track token usage to stay within limits
2. **Prioritization**: Core instructions > user query > enhancement
3. **Graceful Degradation**: Fall back to raw prompt on error
4. **User Control**: Opt-in via config

### Implementation

#### Step 2.1: Add Configuration

**File**: `extensions/vscode-codechef/package.json`

```json
{
  "configuration": {
    "properties": {
      "codechef.enhancePrompts": {
        "type": "boolean",
        "default": false,
        "description": "Use Copilot to enhance task descriptions before sending to orchestrator (adds 1-2s latency)",
        "order": 15
      },
      "codechef.enhancementTemplate": {
        "type": "string",
        "enum": ["detailed", "structured", "minimal"],
        "default": "structured",
        "description": "Prompt enhancement style",
        "enumDescriptions": [
          "Detailed: Maximum context and specifications",
          "Structured: Balanced structure with key details (recommended)",
          "Minimal: Light enhancement, preserve user style"
        ],
        "order": 16
      }
    }
  }
}
```

#### Step 2.2: Implement Prompt Enhancer

**File**: `extensions/vscode-codechef/src/promptEnhancer.ts` (NEW)

**Inspired by vscode-prompt-tsx patterns**:

```typescript
import * as vscode from "vscode";

/**
 * Enhancement templates based on vscode-prompt-tsx patterns:
 * - System message with high priority
 * - User message with task context
 * - Structured output format
 */
export class PromptEnhancer {
  private readonly enhancementTemplates = {
    detailed: {
      system: `You are a requirements analyst helping to clarify development tasks.

Given a user's brief request, expand it into a comprehensive specification.

Provide:
- **Objective**: Clear statement of what needs to be done
- **Affected Components**: Specific files/modules/services to modify
- **Acceptance Criteria**: Measurable success conditions (Given/When/Then format)
- **Technical Constraints**: Language, framework, architecture, performance requirements
- **Edge Cases**: Error handling, validation, boundary conditions
- **Testing Requirements**: Unit tests, integration tests, manual verification steps

Format your response as structured sections. Be specific about file paths and component names.`,
      maxTokens: 800,
    },

    structured: {
      system: `You are a technical clarifier helping to structure development tasks.

Given a user's request, expand it into a clear, actionable specification.

Provide:
- **Goal**: What needs to be accomplished
- **Scope**: Which files/components are affected
- **Criteria**: How to verify success
- **Constraints**: Technical requirements or limitations

Be concise but specific. Include file paths if implied by context.`,
      maxTokens: 500,
    },

    minimal: {
      system: `Given a development task, add any missing critical details while preserving the user's intent and style.

Focus only on:
- Which files/components are involved
- Expected behavior or outcome
- Any technical constraints

Keep it brief.`,
      maxTokens: 300,
    },
  };

  async enhance(
    originalPrompt: string,
    model: vscode.LanguageModelChat,
    template: "detailed" | "structured" | "minimal",
    token: vscode.CancellationToken
  ): Promise<{ enhanced: string; error?: string }> {
    const config = this.enhancementTemplates[template];

    try {
      // Build messages (vscode-prompt-tsx pattern: System + User)
      const messages = [
        vscode.LanguageModelChatMessage.User(config.system),
        vscode.LanguageModelChatMessage.User(
          `Original request:\n"${originalPrompt}"\n\nExpanded specification:`
        ),
      ];

      // Send request with token limits (vscode-prompt-tsx: PromptSizing concept)
      const request = await model.sendRequest(
        messages,
        {
          justification:
            "Enhancing task description for code-chef orchestrator",
        },
        token
      );

      let enhanced = "";
      let tokenCount = 0;
      const maxTokens = config.maxTokens;

      // Stream response (vscode-prompt-tsx: token-by-token)
      for await (const chunk of request.text) {
        // Rough token estimation (4 chars ≈ 1 token)
        tokenCount += Math.ceil(chunk.length / 4);

        if (tokenCount > maxTokens) {
          // Budget exceeded, truncate gracefully
          break;
        }

        enhanced += chunk;
      }

      // Validate enhancement quality
      if (enhanced.length < 50) {
        return {
          enhanced: originalPrompt,
          error: "Enhancement too short, using original",
        };
      }

      return { enhanced: enhanced.trim() };
    } catch (error: any) {
      console.error("Prompt enhancement failed:", error);

      // Graceful degradation (vscode-prompt-tsx pattern)
      return {
        enhanced: originalPrompt,
        error: error.message,
      };
    }
  }
}
```

#### Step 2.3: Integrate into Chat Participant

**File**: `extensions/vscode-codechef/src/chatParticipant.ts`

**Add member**:

```typescript
export class CodeChefChatParticipant {
  // ... existing members
  private promptEnhancer: PromptEnhancer;

  constructor(private context: vscode.ExtensionContext) {
    // ... existing initialization
    this.promptEnhancer = new PromptEnhancer();
  }
}
```

**Update handleStreamingChat**:

```typescript
private async handleStreamingChat(
    userMessage: string,
    context: vscode.ChatContext,
    stream: vscode.ChatResponseStream,
    token: vscode.CancellationToken,
    request: vscode.ChatRequest  // ADD parameter
): Promise<vscode.ChatResult> {
    stream.progress('Connecting to code/chef...');

    try {
        const workspaceContext = await this.contextExtractor.extract();
        const sessionId = this.sessionManager.getOrCreateSession(context);
        const chatReferences = this.extractChatReferences(request.references);

        // === PROMPT ENHANCEMENT (NEW) ===
        const config = vscode.workspace.getConfiguration('codechef');
        const enhancePrompts = config.get('enhancePrompts', false);
        let finalPrompt = userMessage;
        let enhancementError: string | undefined;

        if (enhancePrompts) {
            stream.progress('Enhancing task description with Copilot...');

            const template = config.get<'detailed' | 'structured' | 'minimal'>(
                'enhancementTemplate',
                'structured'
            );

            const result = await this.promptEnhancer.enhance(
                userMessage,
                request.model,  // Use user's selected Copilot model
                template,
                token
            );

            finalPrompt = result.enhanced;
            enhancementError = result.error;

            // Log enhancement for debugging
            if (enhancementError) {
                console.warn(`code/chef: Prompt enhancement failed: ${enhancementError}`);
            } else {
                console.log(`code/chef: Enhanced prompt from ${userMessage.length} to ${finalPrompt.length} chars`);
            }
        }
        // === END ENHANCEMENT ===

        let currentAgent = '';
        let sessionIdFromStream = sessionId;
        let fullResponse = '';
        let isSupervisionResponse = false;

        for await (const chunk of this.client.chatStream({
            message: finalPrompt,  // Use enhanced prompt
            session_id: sessionId,
            context: {
                ...workspaceContext,
                chat_references: chatReferences,
                prompt_enhanced: enhancePrompts,
                enhancement_error: enhancementError
            },
            workspace_config: buildWorkspaceConfig()
        })) {
            // ... rest of streaming logic
        }

        return {
            metadata: {
                status: 'success',
                streaming: true,
                sessionId: sessionIdFromStream,
                promptEnhanced: enhancePrompts,
                enhancementError
            }
        };

    } catch (error: any) {
        // ... existing error handling
    }
}
```

**Update handleChatRequest signature**:

```typescript
async handleChatRequest(
    request: vscode.ChatRequest,
    context: vscode.ChatContext,
    stream: vscode.ChatResponseStream,
    token: vscode.CancellationToken
): Promise<vscode.ChatResult> {
    const userMessage = request.prompt;

    // Handle commands
    if (request.command) {
        return await this.handleCommand(request.command, userMessage, stream, token);
    }

    // Use streaming for conversational chat
    if (this.useStreaming) {
        return await this.handleStreamingChat(userMessage, context, stream, token, request);  // Pass request
    }

    // ... rest
}
```

---

## Feature 3: Model Telemetry

### Problem

We don't track which Copilot models users select, missing:

- Usage analytics (GPT-4 vs GPT-3.5 preference)
- Correlation with task success rates
- A/B testing opportunities

### Solution

Capture `request.model` metadata and pass to orchestrator for LangSmith traces.

### Implementation

#### Step 3.1: Capture Model Metadata

**File**: `extensions/vscode-codechef/src/chatParticipant.ts`

**Add helper**:

```typescript
/**
 * Extract Copilot model metadata for telemetry.
 * Tracks which models users prefer for different task types.
 */
private extractModelMetadata(model: vscode.LanguageModelChat) {
    return {
        vendor: model.vendor,
        family: model.family,
        version: model.version || 'unknown',
        name: model.name,
        maxInputTokens: model.maxInputTokens,
        maxOutputTokens: model.maxOutputTokens
    };
}
```

**Usage in handleStreamingChat**:

```typescript
// After extracting chatReferences
const copilotModel = this.extractModelMetadata(request.model);

// Log for debugging
console.log(
  `code/chef: Using Copilot model ${copilotModel.family}`,
  copilotModel
);

await this.client.chatStream({
  message: finalPrompt,
  session_id: sessionId,
  context: {
    ...workspaceContext,
    chat_references: chatReferences,
    copilot_model: copilotModel, // NEW
    prompt_enhanced: enhancePrompts,
    enhancement_error: enhancementError,
  },
  workspace_config: buildWorkspaceConfig(),
});
```

#### Step 3.2: Log to LangSmith

**File**: `agent_orchestrator/main.py`

**Update @traceable decorator**:

```python
@app.post("/chat/stream", tags=["chat"])
@traceable(
    name="chat_stream",
    tags=["chat", "streaming", "sse"],
    metadata=lambda: {
        # Existing metadata
        "experiment_group": os.getenv("EXPERIMENT_GROUP", "code-chef"),
        "environment": os.getenv("TRACE_ENVIRONMENT", "production"),
        "extension_version": os.getenv("EXTENSION_VERSION", "1.0.0"),

        # NEW: Copilot model tracking
        "copilot_model_family": request.context.get("copilot_model", {}).get("family", "unknown") if request and request.context else "unknown",
        "copilot_model_vendor": request.context.get("copilot_model", {}).get("vendor", "unknown") if request and request.context else "unknown",

        # NEW: Chat references tracking
        "chat_references_count": len(request.context.get("chat_references", {}).get("files", [])) if request and request.context else 0,

        # NEW: Prompt enhancement tracking
        "prompt_enhanced": request.context.get("prompt_enhanced", False) if request and request.context else False,
    }
)
async def chat_stream_endpoint(request: ChatStreamRequest):
    # ... existing implementation
```

#### Step 3.3: Update Tracing Schema

**File**: `config/observability/tracing-schema.yaml`

```yaml
# Copilot Context Metadata (v1.0.0-beta.4)
copilot_model_family:
  type: string
  description: "Copilot model family selected by user (gpt-4o, gpt-3.5-turbo, etc.)"
  examples: ["gpt-4o", "gpt-3.5-turbo", "claude-3-5-sonnet"]
  optional: true

copilot_model_vendor:
  type: string
  description: "Copilot model vendor (copilot, openai, anthropic)"
  examples: ["copilot", "openai", "anthropic"]
  optional: true

prompt_enhanced:
  type: boolean
  description: "Whether prompt was enhanced using Copilot before orchestration"
  optional: true
```

---

## Agent System Prompt Optimizations

### Learnings from vscode-prompt-tsx

1. **Token Budget Discipline**

   - Specify budget in prompt header
   - Guide agents on compression strategies
   - Priority: instructions > current task > history > context

2. **Structured Output Formats**

   - JSON schemas for parseable responses
   - Reduce ambiguity in agent → agent communication

3. **Context Prioritization**
   - Recent history > older history
   - Referenced files > workspace scan
   - Explicit > inferred context

### Recommended Updates

#### All Agent Prompts

**Add section after "Context Window Budget"**:

```markdown
## Context Prioritization (Priority Order)

Use your token budget efficiently by prioritizing:

1. **System Instructions** (Priority 100): Always included
2. **Current Task** (Priority 90): User's immediate request
3. **Referenced Files** (Priority 85): Files explicitly mentioned or selected in chat
4. **Recent History** (Priority 80): Last 2 conversation turns
5. **RAG Context** (Priority 70): Relevant code patterns, past solutions
6. **Workspace Scan** (Priority 50): General workspace context
7. **Older History** (Priority 30): Earlier conversation turns

If approaching token limit, compress in reverse priority order.
Preserve task description and system instructions at all costs.

## Chat References Integration

When `chat_references` are provided in context:

- **Files**: Read these files first before scanning workspace
- **Symbols**: Focus analysis on referenced functions/classes/methods
- **Strings**: Treat as explicit requirements or constraints

If chat references + task description exceed 50% of budget, skip workspace scan.
```

#### Supervisor Prompt Specifically

**File**: `agent_orchestrator/agents/supervisor/system.prompt.md`

**Add after "Context Window Budget"**:

```markdown
## Prompt Enhancement Awareness

When `prompt_enhanced: true` in context:

- The prompt was already expanded by Copilot
- It likely contains detailed specifications
- Skip clarification questions unless truly ambiguous
- Proceed directly to agent routing

When `chat_references` provided:

- These are explicit user signals about scope
- Prefer routing to agents that can leverage referenced files
- Include reference context in subtask descriptions
```

#### Feature Dev Prompt

**File**: `agent_orchestrator/agents/feature_dev/system.prompt.md`

**Update "Context Compression Rules"**:

````markdown
## Context Compression Rules (Enhanced)

Priority order when approaching token limit:

1. **Never compress**: Task description, acceptance criteria
2. **Compress lightly**: Referenced files (keep structure + key functions)
3. **Compress heavily**: Workspace scan results (summaries only)
4. **Drop if needed**: Older conversation history, unrelated code context

When `chat_references.files` provided:

- Read these files in full (up to 2K tokens each)
- Skip broad workspace scanning
- Focus code generation on referenced components

Example compression:

```plaintext
FULL (2000 tokens):
// auth.ts - complete file with all functions, comments, imports

COMPRESSED (400 tokens):
// auth.ts - exports: validateToken(), refreshToken(), logout()
// Uses JWT, bcrypt. 200 lines. Last modified: 2025-12-10
```
````

````

---

## Testing Strategy

### Unit Tests

**File**: `extensions/vscode-codechef/src/test/chatParticipant.test.ts` (NEW)

```typescript
import * as assert from 'assert';
import * as vscode from 'vscode';
import { CodeChefChatParticipant } from '../chatParticipant';

suite('ChatParticipant - Context Enhancement', () => {
    let participant: CodeChefChatParticipant;

    setup(() => {
        const mockContext = {} as vscode.ExtensionContext;
        participant = new CodeChefChatParticipant(mockContext);
    });

    test('extractChatReferences - files', () => {
        const mockRef: vscode.ChatPromptReference = {
            id: 'file-1',
            value: vscode.Uri.file('/path/to/file.ts')
        };

        const result = participant['extractChatReferences']([mockRef]);

        assert.strictEqual(result.files.length, 1);
        assert.strictEqual(result.files[0], '/path/to/file.ts');
        assert.strictEqual(result.count, 1);
    });

    test('extractChatReferences - symbols', () => {
        const mockRef: vscode.ChatPromptReference = {
            id: 'symbol-1',
            value: new vscode.Location(
                vscode.Uri.file('/path/to/file.ts'),
                new vscode.Position(10, 5)
            )
        };

        const result = participant['extractChatReferences']([mockRef]);

        assert.strictEqual(result.symbols.length, 1);
        assert.strictEqual(result.symbols[0].file, '/path/to/file.ts');
        assert.strictEqual(result.symbols[0].line, 10);
    });

    test('extractModelMetadata', () => {
        const mockModel: vscode.LanguageModelChat = {
            vendor: 'copilot',
            family: 'gpt-4o',
            version: '0125',
            name: 'copilot-gpt-4o',
            maxInputTokens: 128000,
            maxOutputTokens: 4096
        } as vscode.LanguageModelChat;

        const result = participant['extractModelMetadata'](mockModel);

        assert.strictEqual(result.vendor, 'copilot');
        assert.strictEqual(result.family, 'gpt-4o');
        assert.strictEqual(result.maxInputTokens, 128000);
    });
});
````

### Integration Tests

**File**: `extensions/vscode-codechef/src/test/promptEnhancer.test.ts` (NEW)

```typescript
import * as assert from "assert";
import * as vscode from "vscode";
import { PromptEnhancer } from "../promptEnhancer";

suite("PromptEnhancer", () => {
  let enhancer: PromptEnhancer;

  setup(() => {
    enhancer = new PromptEnhancer();
  });

  test("enhance - graceful degradation on error", async () => {
    const mockModel: vscode.LanguageModelChat = {
      sendRequest: async () => {
        throw new Error("Model unavailable");
      },
    } as any;

    const result = await enhancer.enhance(
      "fix the bug",
      mockModel,
      "structured",
      {} as vscode.CancellationToken
    );

    // Should fall back to original
    assert.strictEqual(result.enhanced, "fix the bug");
    assert.ok(result.error);
  });

  test("enhance - token budget enforcement", async () => {
    const mockModel: vscode.LanguageModelChat = {
      sendRequest: async () => ({
        text: (async function* () {
          // Generate text exceeding budget
          for (let i = 0; i < 1000; i++) {
            yield "word ".repeat(100); // ~400 tokens per chunk
          }
        })(),
      }),
    } as any;

    const result = await enhancer.enhance(
      "simple task",
      mockModel,
      "minimal", // 300 token limit
      {} as vscode.CancellationToken
    );

    // Should truncate to ~300 tokens (~1200 chars)
    assert.ok(result.enhanced.length < 1500);
  });
});
```

### E2E Tests

**File**: `support/tests/e2e/test_chat_context.py` (NEW)

```python
"""E2E tests for Copilot context enhancement features."""

import pytest
from agent_orchestrator.main import chat_stream_endpoint

@pytest.mark.asyncio
async def test_chat_references_passed_to_agents():
    """Verify chat references flow through to agents."""
    request = ChatStreamRequest(
        message="Fix the authentication bug",
        context={
            "chat_references": {
                "files": ["/path/to/auth.ts"],
                "symbols": [],
                "strings": [],
                "count": 1
            }
        }
    )

    # Mock agent execution
    # Verify agent receives chat_references in state
    # Assert RAG query scoped to referenced files
    pass  # TODO: Implement with mocks

@pytest.mark.asyncio
async def test_copilot_model_logged_to_langsmith():
    """Verify Copilot model metadata captured in traces."""
    request = ChatStreamRequest(
        message="Add tests",
        context={
            "copilot_model": {
                "vendor": "copilot",
                "family": "gpt-4o",
                "version": "0125"
            }
        }
    )

    # Execute request
    # Verify LangSmith trace includes copilot_model_family metadata
    pass  # TODO: Implement with LangSmith API check

@pytest.mark.asyncio
async def test_prompt_enhancement_flag():
    """Verify enhanced prompts logged correctly."""
    request = ChatStreamRequest(
        message="Detailed task description...",
        context={
            "prompt_enhanced": True
        }
    )

    # Verify flag appears in traces
    # Verify supervisor skips clarification for enhanced prompts
    pass  # TODO: Implement
```

---

## Rollout Plan

### Phase 1: Development (Days 1-2)

**Day 1**:

- [ ] Implement Feature 3 (Model Telemetry) - 30 min
- [ ] Implement Feature 1 (Chat References) - 2 hours
- [ ] Update type definitions - 30 min
- [ ] Update backend to handle new context fields - 1 hour

**Day 2**:

- [ ] Implement Feature 2 (Prompt Enhancement) - 3 hours
- [ ] Write unit tests - 2 hours
- [ ] Update tracing schema - 30 min
- [ ] Update agent system prompts - 1 hour

### Phase 2: Testing (Days 3-4)

**Day 3**:

- [ ] Extension unit tests
- [ ] Integration tests with mock orchestrator
- [ ] Manual testing with real Copilot models
- [ ] Test all 3 enhancement templates

**Day 4**:

- [ ] E2E tests with full stack
- [ ] Test chat references with RAG service
- [ ] Verify LangSmith trace metadata
- [ ] Test error scenarios (model unavailable, timeout, etc.)

### Phase 3: Documentation (Day 5)

- [ ] Update CHANGELOG.md
- [ ] Update README with new features
- [ ] Document configuration options
- [ ] Create user guide for prompt enhancement
- [ ] Update architecture diagrams

### Phase 4: Deployment (Day 5)

**Pre-deployment Checklist**:

- [ ] All tests passing
- [ ] Code reviewed
- [ ] Configuration documented
- [ ] Rollback plan ready

**Deployment Steps**:

1. **Commit and push**:

   ```bash
   git checkout -b feature/copilot-context-enhancement
   git add -A
   git commit -m "feat: Add Copilot context enhancement (chat references, prompt boost, telemetry)"
   git push origin feature/copilot-context-enhancement
   ```

2. **Create PR** with full description from this plan

3. **Deploy to staging**:

   ```bash
   # Build extension
   cd extensions/vscode-codechef
   npm run compile
   npm run package

   # Deploy orchestrator
   cd ../../deploy
   docker compose up -d --build orchestrator
   ```

4. **Smoke test**:

   - Test chat with file references
   - Test with prompt enhancement enabled
   - Verify LangSmith traces include new metadata
   - Check logs for errors

5. **Deploy to production**:

   ```bash
   # Tag release
   git tag v1.0.0-beta.4
   git push origin v1.0.0-beta.4

   # GitHub Actions will build and publish
   ```

6. **Verify production**:
   - Install extension from marketplace
   - Test all three features
   - Monitor LangSmith for 24 hours
   - Check error rates

### Phase 5: Monitoring (Ongoing)

**Key Metrics**:

1. **Chat References**:

   - `chat_references_count` > 0 (percentage of requests)
   - Time saved in RAG queries (faster with scoped search)

2. **Prompt Enhancement**:

   - `prompt_enhanced: true` (usage rate)
   - Average enhancement latency
   - Task success rate (enhanced vs non-enhanced)

3. **Model Telemetry**:
   - `copilot_model_family` distribution (GPT-4 vs GPT-3.5)
   - Correlation with task complexity
   - Cost per model type

**Dashboards**:

```promql
# Grafana queries
# Chat references usage
sum(langsmith_trace_metadata{key="chat_references_count"} > 0) by (copilot_model_family)

# Prompt enhancement adoption
rate(langsmith_trace_metadata{key="prompt_enhanced", value="true"}[1h])

# Model preferences
count(langsmith_trace_metadata{key="copilot_model_family"}) by (copilot_model_family)
```

---

## Success Criteria

### Feature 1: Chat References

- [ ] Extension captures file references from `#file` selections
- [ ] Extension captures symbol references from context menu
- [ ] Orchestrator receives chat_references in context
- [ ] Agents can access referenced files in RAG queries
- [ ] LangSmith traces show `chat_references_count` > 0
- [ ] RAG queries scoped to referenced files return results faster

### Feature 2: Prompt Enhancement

- [ ] Configuration option appears in VS Code settings
- [ ] Enhancement disabled by default
- [ ] When enabled, prompts expanded using Copilot model
- [ ] Enhancement fails gracefully (falls back to original)
- [ ] Enhancement completes in <2 seconds
- [ ] Enhanced prompts improve task decomposition (subjective, UAT feedback)
- [ ] LangSmith traces show `prompt_enhanced: true`

### Feature 3: Model Telemetry

- [ ] Copilot model metadata captured on every request
- [ ] LangSmith traces include `copilot_model_family` and `copilot_model_vendor`
- [ ] Grafana dashboard shows model distribution
- [ ] Can correlate model selection with task success rates

### System Prompt Updates

- [ ] All agent prompts updated with context prioritization section
- [ ] Supervisor prompt aware of prompt enhancement
- [ ] Feature dev prompt optimized for chat references
- [ ] Code review prompt uses referenced files for focused reviews

---

## Risks and Mitigation

| Risk                                | Impact                   | Probability | Mitigation                                      |
| ----------------------------------- | ------------------------ | ----------- | ----------------------------------------------- |
| **Prompt enhancement adds latency** | User experience degraded | Medium      | Make opt-in, default off. Set 2s timeout.       |
| **Copilot model API unavailable**   | Enhancement fails        | Low         | Graceful fallback to original prompt            |
| **Chat references not captured**    | Feature doesn't work     | Low         | Test with multiple VS Code versions             |
| **Token budget exceeded**           | Truncated enhancements   | Medium      | Enforce budget in enhancer, truncate gracefully |
| **Agent prompts too verbose**       | Hit token limits         | Low         | Test with large prompts, compress if needed     |
| **LangSmith trace overhead**        | Increased latency        | Low         | Metadata is async, minimal impact               |

---

## Next Steps

1. **Review this plan** with team
2. **Assign implementation** (developer, QA)
3. **Create Linear issues**:
   - CHEF-xxx: Implement chat references capture
   - CHEF-xxx: Implement prompt enhancement
   - CHEF-xxx: Add Copilot model telemetry
   - CHEF-xxx: Update agent system prompts
   - CHEF-xxx: Write integration tests
4. **Schedule UAT** for v1.0.0-beta.4
5. **Plan Grafana dashboard** updates for new metrics

---

## References

- [Copilot Chat Mode Analysis](./COPILOT_CHAT_MODE_ANALYSIS.md) - Original analysis
- [vscode-prompt-tsx Examples](https://github.com/microsoft/vscode-prompt-tsx/tree/main/examples) - Prompt patterns
- [LangSmith Tracing Guide](../integrations/langsmith-tracing.md) - Metadata schema
- [VS Code Chat API](https://code.visualstudio.com/api/extension-guides/chat) - Reference docs

---

**Plan Version**: 1.0  
**Last Updated**: December 13, 2025  
**Status**: Ready for Implementation  
**Estimated Effort**: 5 days (1 developer)  
**Target Release**: v1.0.0-beta.4
