# Copilot Chat Mode & Model Selection Analysis

**Date**: December 13, 2025  
**Status**: Analysis Complete  
**Purpose**: Evaluate impact of Copilot chat modes (Ask, Plan, etc.) and model selection on code-chef extension and orchestrator

---

## Executive Summary

**Current State**: code-chef extension does NOT capture or use:

- Chat mode selection (Ask, Plan, Explain, etc.)
- Selected Copilot model information (`request.model`)
- Chat location context (terminal, panel, editor, notebook)

**Impact**: **LOW PRIORITY** - Current architecture works well without these signals, but capturing them could enable:

1. **Smarter task routing** based on user intent signals
2. **Cost optimization** through selective model usage
3. **Better RAG context selection** based on task complexity
4. **Enhanced telemetry** for usage patterns

**Recommendation**: **Phase 2 Enhancement** - Implement after core UAT validation is complete.

---

## Available VS Code Chat Context

### ChatRequest Interface

```typescript
interface ChatRequest {
  // Currently used by code-chef
  readonly prompt: string; // ✅ Used
  readonly command: string | undefined; // ✅ Used (/status, /approve, etc.)

  // NOT currently captured
  readonly model: LanguageModelChat; // ❌ Not captured
  readonly references: ChatPromptReference[]; // ❌ Not captured (file refs, symbols)
  readonly toolReferences: ChatLanguageModelToolReference[]; // ❌ Not captured
  readonly toolInvocationToken: ChatParticipantToolToken; // ❌ Not captured
}

interface LanguageModelChat {
  readonly vendor: string; // e.g., "copilot"
  readonly family: string; // e.g., "gpt-4o", "gpt-3.5-turbo"
  readonly version: string; // e.g., "0125"
  readonly name: string; // Full identifier
  readonly maxInputTokens: number;
  readonly maxOutputTokens: number;
}
```

### ChatContext Interface

```typescript
interface ChatContext {
  // Currently used
  readonly history: (ChatRequestTurn | ChatResponseTurn)[]; // ✅ Used indirectly via SessionManager

  // NOT captured
  // No explicit "mode" property - modes are a UI concept, not API
}
```

**Key Finding**: **Chat modes (Ask, Plan, Explain, etc.) are NOT exposed via API**. They're UI hints for user, not programmatic signals.

---

## Chat Mode Analysis

### What Are Chat Modes?

GitHub Copilot Chat offers these modes in the UI:

- **Ask**: General queries ("how does this work?")
- **Explain**: Code explanation ("explain this function")
- **Fix**: Bug diagnosis and repair
- **Generate**: New code creation
- **Test**: Test generation
- **Refactor**: Code restructuring
- **Custom**: User-defined workflows

### Are They Available to Extensions?

**NO** - These modes are:

1. **UI-only hints** to help users frame questions
2. **Pre-fill prompt templates** ("Explain the following code...")
3. **NOT exposed in ChatRequest API**

Extensions receive the **final prompt text** after mode selection, but not the mode itself.

### Workaround: Intent Recognition

code-chef already implements this via `IntentRecognizer`:

```python
# agent_orchestrator/main.py
intent = await intent_recognizer.recognize(request.message, history)

# Intent types:
# - task_submission
# - status_query
# - clarification
# - approval_decision
# - general_query
```

This effectively **reconstructs user intent from prompt**, which is more reliable than trusting UI mode selection.

---

## Model Selection Analysis

### Current Architecture

**Extension** (TypeScript):

```typescript
// chatParticipant.ts - handleChatRequest
async handleChatRequest(
    request: vscode.ChatRequest,  // Has request.model
    context: vscode.ChatContext,
    stream: vscode.ChatResponseStream,
    token: vscode.CancellationToken
): Promise<vscode.ChatResult> {
    // ❌ request.model NOT captured or sent to orchestrator
    const userMessage = request.prompt;

    // Sends to orchestrator without model info
    await this.client.chatStream({
        message: userMessage,
        session_id: sessionId,
        context: workspaceContext,
        workspace_config: buildWorkspaceConfig()
    });
}
```

**Orchestrator** (Python):

```python
# agent_orchestrator/main.py
class ChatStreamRequest(BaseModel):
    message: str
    session_id: Optional[str]
    user_id: Optional[str]
    context: Optional[Dict[str, Any]]
    workspace_config: Optional[Dict[str, Any]]
    project_context: Optional[Dict[str, Any]]
    # ❌ NO copilot_model field
```

**Agent Configuration** (YAML):

```yaml
# config/agents/models.yaml
agents:
  supervisor:
    model: anthropic/claude-3.5-sonnet # Fixed per agent
    cost_per_1m_tokens: 3.00

  feature_dev:
    model: qwen/qwen-2.5-coder-32b # Fixed per agent
    cost_per_1m_tokens: 0.07
```

### Key Observations

1. **Extension doesn't use `request.model`** - Chat participant ignores Copilot's model selection
2. **Orchestrator uses fixed models per agent** - Defined in `config/agents/models.yaml`
3. **No model pass-through** - Copilot's model choice doesn't influence backend agents

**Is this a problem?** **NO** - Architecture is intentional:

- Copilot model handles **extension UI chat** (not used currently, extension streams from orchestrator)
- Backend agents use **specialized models** optimized for their tasks
- Separation of concerns is clean

---

## Optimization Opportunities

### 1. Capture Model Context for Telemetry

**Use Case**: Track which Copilot models users prefer, correlate with task success rates.

**Implementation**:

```typescript
// extensions/vscode-codechef/src/chatParticipant.ts
async handleChatRequest(request: vscode.ChatRequest, ...): Promise<vscode.ChatResult> {
    const copilotModel = {
        vendor: request.model.vendor,
        family: request.model.family,
        version: request.model.version,
        maxInputTokens: request.model.maxInputTokens
    };

    await this.client.chatStream({
        message: userMessage,
        session_id: sessionId,
        context: workspaceContext,
        workspace_config: buildWorkspaceConfig(),
        copilot_model_context: copilotModel  // NEW
    });
}
```

```python
# agent_orchestrator/main.py
class ChatStreamRequest(BaseModel):
    message: str
    # ... existing fields
    copilot_model_context: Optional[Dict[str, Any]] = None  # NEW
```

**Benefits**:

- LangSmith traces include Copilot model used
- Can correlate model selection with task complexity
- A/B test different Copilot models for extension UI

**Cost**: Minimal - just metadata passing

---

### 2. Use Copilot Model for Pre-Processing // ---> I like this, proceed to execute.

**Use Case**: Leverage user's selected Copilot model for prompt enhancement before sending to orchestrator.

**Current**: Extension sends raw prompt → Orchestrator processes

**Enhanced**: Extension uses Copilot model to:

- Expand ambiguous requests
- Extract explicit requirements
- Generate structured task descriptions

**Implementation**:

```typescript
// extensions/vscode-codechef/src/chatParticipant.ts
private async enhancePromptWithCopilot(
    originalPrompt: string,
    model: vscode.LanguageModelChat,
    token: vscode.CancellationToken
): Promise<string> {
    const enhancementPrompt = [
        vscode.LanguageModelChatMessage.User(
            `Expand this development task into a clear, structured description:\n\n"${originalPrompt}"\n\nProvide:\n- Specific files/components to modify\n- Acceptance criteria\n- Technical constraints`
        )
    ];

    const request = await model.sendRequest(enhancementPrompt, {}, token);
    let enhanced = '';
    for await (const chunk of request.text) {
        enhanced += chunk;
    }

    return enhanced;
}

async handleStreamingChat(...): Promise<vscode.ChatResult> {
    // Optional enhancement based on config
    const config = vscode.workspace.getConfiguration('codechef');
    const enhancePrompts = config.get('enhancePrompts', false);

    let finalPrompt = userMessage;
    if (enhancePrompts) {
        stream.progress('Enhancing task description...');
        finalPrompt = await this.enhancePromptWithCopilot(
            userMessage,
            request.model,
            token
        );
    }

    // Send enhanced prompt to orchestrator
    await this.client.chatStream({
        message: finalPrompt,
        // ... rest
    });
}
```

**Benefits**:

- Better task decomposition from enhanced descriptions
- Uses user's Copilot subscription (no backend cost)
- Leverages latest GPT models if user has access

**Costs**:

- Adds ~1-2s latency
- Requires user Copilot consent for model use
- Risk of over-engineering simple requests

**Recommendation**: Make **opt-in via config** (`codechef.enhancePrompts: false` default)

---

### 3. Adaptive Model Selection Based on Task Complexity

**Use Case**: Use Copilot model info to infer task complexity, adjust backend agent models accordingly.

**Logic**:

```typescript
// If user selected GPT-4o → complex task → use expensive backend models
// If user selected GPT-3.5 → simple task → use cheaper backend models
```

**Implementation**:

```typescript
// chatParticipant.ts
async handleStreamingChat(...): Promise<vscode.ChatResult> {
    const taskComplexity = this.inferComplexity(request.model, userMessage);

    await this.client.chatStream({
        message: userMessage,
        session_id: sessionId,
        context: workspaceContext,
        workspace_config: buildWorkspaceConfig(),
        complexity_hint: taskComplexity  // "simple" | "moderate" | "complex"
    });
}

private inferComplexity(
    model: vscode.LanguageModelChat,
    prompt: string
): string {
    // Heuristic: GPT-4 family = complex tasks
    if (model.family.includes('gpt-4')) return 'complex';
    if (model.family.includes('o1')) return 'complex';

    // Word count heuristic
    if (prompt.split(' ').length > 50) return 'complex';

    return 'simple';
}
```

```python
# agent_orchestrator/main.py
class ChatStreamRequest(BaseModel):
    # ... existing
    complexity_hint: Optional[str] = None  # NEW

# In supervisor_node or workflow_router
if request.complexity_hint == 'simple':
    # Use cheaper models, less context
    config_overrides = {"max_tokens": 1000, "use_rag": False}
elif request.complexity_hint == 'complex':
    # Use expensive models, full RAG
    config_overrides = {"max_tokens": 4000, "use_rag": True}
```

**Benefits**:

- Cost optimization without sacrificing quality
- Responsive to user's implicit intent (model choice)
- Reduces token usage on simple queries

**Risks**:

- False assumptions (user might always pick GPT-4)
- Complexity inference is heuristic, not reliable
- Adds complexity to routing logic

**Recommendation**: **Low priority** - Current intent recognition is more reliable

---

### 4. Capture Chat References for Context Enhancement // ---> THIS IS A MUST! Execute accordingly

**Use Case**: User selects files/symbols in chat → pass to orchestrator for better context.

**Available Data**:

```typescript
interface ChatRequest {
  readonly references: readonly ChatPromptReference[];
}

interface ChatPromptReference {
  readonly id: string;
  readonly value: Uri | Location | string | SymbolInformation;
}
```

**Implementation**:

```typescript
// chatParticipant.ts
async handleStreamingChat(...): Promise<vscode.ChatResult> {
    const referencedFiles = request.references
        .filter(ref => ref.value instanceof vscode.Uri)
        .map(ref => (ref.value as vscode.Uri).fsPath);

    const referencedSymbols = request.references
        .filter(ref => ref.value instanceof vscode.Location)
        .map(ref => ({
            file: (ref.value as vscode.Location).uri.fsPath,
            line: (ref.value as vscode.Location).range.start.line
        }));

    await this.client.chatStream({
        message: userMessage,
        session_id: sessionId,
        context: {
            ...workspaceContext,
            chat_references: {
                files: referencedFiles,
                symbols: referencedSymbols
            }
        }
    });
}
```

**Benefits**:

- More accurate context for RAG queries
- Agents can read referenced files directly
- Better workspace awareness

**Recommendation**: **Medium priority** - Useful for UAT feedback loops

---

## Recommendations Summary

### Tier 1 (Implement Soon)

**1. Capture Copilot Model for Telemetry**

- **Effort**: Low (5 lines of code)
- **Value**: High (usage analytics, A/B testing data)
- **Risk**: None
- **Files**: `chatParticipant.ts`, `main.py` (ChatStreamRequest)

**2. Capture Chat References**

- **Effort**: Medium (20-30 lines)
- **Value**: High (better context awareness)
- **Risk**: Low
- **Files**: `chatParticipant.ts`, `contextExtractor.ts`

### Tier 2 (Consider for Phase 2)

**3. Prompt Enhancement with Copilot** ⭐

- **Effort**: Medium (opt-in config, error handling)
- **Value**: Medium (better task descriptions)
- **Risk**: Medium (latency, over-engineering)
- **Recommendation**: Make **opt-in**, default **off**

### Tier 3 (Low Priority)

**4. Adaptive Model Selection**

- **Effort**: High (heuristics, testing, config overrides)
- **Value**: Low (current intent recognition is better)
- **Risk**: High (false assumptions, complexity)
- **Recommendation**: **Skip** - Focus on intent recognition improvement instead

---

## Implementation Plan

### Phase 1: Telemetry & References (v1.0.0-beta.4)

**Files to Modify**:

1. **extensions/vscode-codechef/src/chatParticipant.ts**

   - Capture `request.model` metadata
   - Extract `request.references` (files, symbols)
   - Pass to orchestrator in `context` object

2. **extensions/vscode-codechef/src/orchestratorClient.ts**

   - Add types for `copilot_model_context` and `chat_references`

3. **agent_orchestrator/main.py**

   - Update `ChatStreamRequest` model with new optional fields
   - Log to LangSmith traces (already happens via @traceable)

4. **config/observability/tracing-schema.yaml**
   - Document new metadata fields

**Code Changes**:

```typescript
// chatParticipant.ts
async handleStreamingChat(...): Promise<vscode.ChatResult> {
    // Capture Copilot model
    const copilotModel = {
        vendor: request.model.vendor,
        family: request.model.family,
        version: request.model.version,
        maxInputTokens: request.model.maxInputTokens,
        maxOutputTokens: request.model.maxOutputTokens
    };

    // Capture references
    const referencedFiles = request.references
        .filter(ref => ref.value instanceof vscode.Uri)
        .map(ref => (ref.value as vscode.Uri).fsPath);

    await this.client.chatStream({
        message: userMessage,
        session_id: sessionId,
        context: {
            ...workspaceContext,
            copilot_model: copilotModel,
            referenced_files: referencedFiles
        },
        workspace_config: buildWorkspaceConfig()
    });
}
```

```python
# main.py
class ChatStreamRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None  # Now includes copilot_model, referenced_files
    workspace_config: Optional[Dict[str, Any]] = None
    project_context: Optional[Dict[str, Any]] = None
```

**Testing**:

- Verify model metadata appears in LangSmith traces
- Test with different Copilot models (GPT-4, GPT-3.5)
- Test with file references selected in chat

**Rollout**: **v1.0.0-beta.4** (post-UAT)

---

### Phase 2: Prompt Enhancement (Optional)

**Config Addition**:

```json
// package.json
{
  "configuration": {
    "properties": {
      "codechef.enhancePrompts": {
        "type": "boolean",
        "default": false,
        "description": "Use Copilot to enhance task descriptions before sending to orchestrator (adds 1-2s latency)"
      }
    }
  }
}
```

**Implementation**: After UAT feedback, if users report ambiguous task decompositions.

---

## Answers to Specific Questions

### Q: "How does Copilot chat mode selection influence the extension?"

**A**: **It doesn't directly**. Chat modes (Ask, Plan, Fix, etc.) are:

- UI-only hints for users
- NOT exposed in VS Code extension API
- Pre-fill prompt templates, but extension receives final prompt text

**Workaround**: code-chef uses **intent recognition** on the orchestrator side, which reconstructs user intent from the prompt itself. This is more reliable than trusting UI mode selection.

---

### Q: "How does Copilot model selection influence the orchestrator response?"

**A**: **It doesn't currently**. Here's why:

1. **Extension ignores Copilot model selection**

   - Available in `request.model`, but not captured
   - Extension doesn't use Copilot model for generation (streams from orchestrator)

2. **Orchestrator uses fixed models per agent**

   - Defined in `config/agents/models.yaml`
   - Specialized per agent type (supervisor, feature_dev, etc.)
   - Model selection is task-driven, not user-driven

3. **Architecture is intentional**
   - Copilot model would be for extension-side generation (not used)
   - Backend agents need specialized models for their domains
   - Separation allows independent optimization

**Should we change this?** **Partially** - Capture model info for telemetry, but keep backend model selection independent.

---

### Q: "What optimizations should we make?"

**A**: **Tier 1 Recommendations** (do soon):

1. **Capture Copilot model for telemetry** ⭐

   - Track usage patterns
   - Correlate model choice with task success
   - Enable A/B testing

2. **Capture chat references** ⭐
   - Better context awareness
   - Direct file access for agents
   - Improved RAG relevance

**Tier 2** (consider later):

- Prompt enhancement (opt-in)

**Tier 3** (skip):

- Adaptive model selection (complexity > value)

---

## Conclusion

**Current architecture is sound**. code-chef correctly:

- Uses intent recognition instead of relying on UI mode signals
- Maintains specialized backend models per agent
- Keeps extension and orchestrator concerns separated

**Low-hanging fruit**:

1. Add 5 lines to capture Copilot model metadata
2. Add 20 lines to capture chat references
3. Gain telemetry insights and better context awareness

**High-effort, low-value**:

- Don't build adaptive model selection based on Copilot choice
- Don't over-engineer prompt enhancement
- Don't try to infer modes from prompts (already have intent recognition)

**Next Steps**:

1. Complete UAT with current architecture
2. Implement Tier 1 recommendations in v1.0.0-beta.4
3. Revisit Tier 2 based on user feedback
4. Add telemetry dashboards to track model usage patterns

---

**Related Documentation**:

- [LLM Operations Guide](../operations/LLM_OPERATIONS.md) - Model configuration
- [Streaming Chat Config](../architecture-and-platform/STREAMING_CHAT_CONFIG.md) - Request/response models
- [Tracing Schema](../../config/observability/tracing-schema.yaml) - Metadata definitions
