# Plan: Optimize Conversational Chat Routing with Intent-Aware Context Extraction

**Goal**: Improve chat response latency by 60-80% for conversational queries while maintaining full context for task execution, leveraging existing backend intent recognition infrastructure.

---

## 1. Add Client-Side Intent Pre-Filter (TypeScript)

**File**: `extensions/vscode-codechef/src/chatParticipant.ts`

**Changes**:

```typescript
// Add before workspace context extraction (line ~225)
private isLikelyConversational(message: string): boolean {
    const conversationalPatterns = [
        /^(hello|hi|hey|greetings|thanks|thank you)/i,
        /^(what|how|why|when|where|who|explain|tell me about)/i,
        /^(help|status|show me)/i,
        /(can you|could you|would you) (explain|tell|show)/i,
    ];

    const shortQuestionPattern = /\?$/;
    const isShortMessage = message.trim().split(/\s+/).length <= 10;

    return conversationalPatterns.some(p => p.test(message)) ||
           (shortQuestionPattern.test(message) && isShortMessage);
}

// Update handleStreamingChat (line ~195)
private async handleStreamingChat(...) {
    const overallStartTime = Date.now();

    try {
        // Step 1: Health check (keep existing)

        // Step 2: NEW - Lightweight intent pre-filter
        const seemsConversational = this.isLikelyConversational(userMessage);
        const shouldExtractContext = !seemsConversational;

        // Step 3: Conditionally extract workspace context
        let workspaceContext = {};
        if (shouldExtractContext) {
            stream.progress('Extracting workspace context...');
            const contextStartTime = Date.now();
            workspaceContext = await this.contextExtractor.extract();
            const contextDuration = Date.now() - contextStartTime;
            console.log(`[ChatParticipant] Context extraction completed in ${contextDuration}ms`);
        } else {
            console.log(`[ChatParticipant] Skipped context extraction (conversational pre-filter)`);
        }
```

**Rationale**: Instant feedback (<10ms) before hitting backend. Filters obvious conversational messages without false negatives (when in doubt, extract context).

---

## 2. Pass Intent Metadata to Backend

**File**: `extensions/vscode-codechef/src/chatParticipant.ts`

**Changes**:

```typescript
// Update chatStream call (line ~315)
for await (const chunk of this.client.chatStream({
    message: finalPrompt,
    session_id: sessionId,
    context: {
        ...workspaceContext,
        chat_references: chatReferences,
        copilot_model: copilotModel,
        prompt_enhanced: enhancePrompts,
        enhancement_error: enhancementError,
        session_mode: 'ask',  // Already exists
        intent_hint: seemsConversational ? 'likely_query' : 'unknown',  // NEW
        context_extracted: shouldExtractContext  // NEW
    },
    workspace_config: buildWorkspaceConfig()
}, abortController.signal)) {
```

**Rationale**: Backend `intent_recognizer.py` already supports `mode_hint` parameter. We add `intent_hint` as supplementary signal (not a directive).

---

## 3. Backend Intent Recognition Integration

**File**: `agent_orchestrator/main.py`

**Changes**:

```python
# Update chat_stream_endpoint (line ~3507)
async def event_generator():
    try:
        # Extract mode hint from request context
        mode_hint = None
        intent_hint = None  # NEW
        if request.context:
            mode_hint = request.context.get("session_mode")  # 'ask' or 'agent'
            intent_hint = request.context.get("intent_hint")  # NEW: 'likely_query' or 'unknown'

        logger.debug(f"[Chat Stream] Mode hint: {mode_hint}, Intent hint: {intent_hint}")

        # Recognize intent with combined hints
        intent = await intent_recognizer.recognize(
            request.message,
            mode_hint=mode_hint  # Already passes this
        )

        # NEW: Override intent if client-side pre-filter was confident
        if intent_hint == 'likely_query' and intent.type == IntentType.TASK_SUBMISSION and intent.confidence < 0.85:
            logger.info(f"[Chat Stream] Client pre-filter suggests conversational, LLM confidence low ({intent.confidence:.2f}), treating as general query")
            intent.type = IntentType.GENERAL_QUERY
            intent.confidence = 0.75
```

**Rationale**: Backend already has full intent recognition. We use client hint to **resolve ambiguity**, not override high-confidence classifications.

---

## 4. Update Backend to Skip RAG/Context for General Queries

**File**: `agent_orchestrator/main.py`

**Changes**:

```python
# After intent recognition in event_generator (line ~3550)
# If this is a general query or conversational response, skip RAG and go straight to conversational handler
if intent.type in [IntentType.GENERAL_QUERY, IntentType.STATUS_QUERY]:
    logger.info(f"[Chat Stream] Conversational intent detected, using lightweight handler")

    # Use conversational_handler_node directly (already exists in graph.py)
    from graph import conversational_handler_node

    # Build minimal state
    state = {
        "messages": [HumanMessage(content=request.message)],
        "session_id": session_id,
        "user_id": request.user_id,
        "current_agent": "conversational",
        # Skip workspace_context, tool_context, rag_context
    }

    # Invoke conversational handler (streaming)
    result = await conversational_handler_node(state)

    # Stream response content
    for chunk in result["messages"][-1].content.split():
        yield f"data: {json.dumps({'type': 'content', 'content': chunk + ' '})}\n\n"

    yield f"data: {json.dumps({'type': 'done', 'session_id': session_id})}\n\n"
    return
```

**Rationale**: Conversational queries don't need RAG context, tool discovery, or supervisor routing. Existing `conversational_handler_node` handles this with simple LLM completion.

---

## 5. Update System Prompts for Intent Awareness

**File**: `agent_orchestrator/agents/supervisor/system.prompt.md`

**Changes**:

```markdown
## Intent Metadata Awareness

When `intent_hint` is provided in metadata:

- **likely_query**: User is asking a question, not requesting work. Provide informational responses.
- **task_submission**: User expects task execution. Route to appropriate specialist agent.
- **unknown**: No strong client-side signal. Rely on your reasoning.

When `context_extracted: false` in metadata:

- Limited workspace context available (user query was lightweight)
- Ask clarifying questions if you need repository structure, file paths, or technical details
- For general queries (capabilities, documentation, status), proceed without context

## Response Patterns by Intent

### General Query (no context needed)

- "What can you do?" → List capabilities concisely
- "How does this work?" → Explain workflow at high level
- "What's my task status?" → Query state-persist service

### Task Submission (context required)

- "Add error handling" → Route to feature-dev with full context
- "Review my PR" → Route to code-review, ensure file references available
- "Deploy to staging" → Route to infrastructure, verify environment context
```

**File**: `agent_orchestrator/agents/feature_dev/system.prompt.md`

**Changes**:

```markdown
## Context Availability Awareness

Check metadata for `context_extracted`:

- **true**: Full workspace context available. Proceed with implementation.
- **false**: Limited context. Request specific files, paths, or structure before coding.

Example response for missing context:
"I need more information to implement this feature. Can you:

1. Share the file where this should be added (#file reference)
2. Describe the current error handling pattern in your codebase
3. Specify error types to handle (validation, network, database, etc.)"
```

**Rationale**: Agents should gracefully degrade when context is missing, asking targeted questions instead of failing silently.

---

## 6. Add Metrics for Optimization Validation

**File**: `agent_orchestrator/main.py`

**Changes**:

```python
# Add new Prometheus metrics (after existing intent recognition metrics)
context_extraction_skipped_total = Counter(
    "orchestrator_context_extraction_skipped_total",
    "Total context extractions skipped due to intent pre-filtering",
    ["intent_hint", "backend_intent_type"]
)

context_extraction_duration = Histogram(
    "orchestrator_context_extraction_duration_seconds",
    "Time spent extracting workspace context",
    ["context_extracted"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

intent_override_total = Counter(
    "orchestrator_intent_override_total",
    "Times client intent hint overrode backend classification",
    ["client_hint", "backend_intent", "final_intent"]
)
```

**File**: `extensions/vscode-codechef/src/chatParticipant.ts`

**Changes**:

```typescript
// Record metrics after context extraction decision
if (shouldExtractContext) {
  console.log(`[ChatParticipant] Context extraction: ${contextDuration}ms`);
} else {
  console.log(
    `[ChatParticipant] Context skipped (saved ~${estimatedContextTime}ms)`
  );
}
```

---

## 7. Backward Compatibility Safeguards

**No Breaking Changes**:

1. **Default behavior unchanged**: If `intent_hint` missing, backend proceeds with normal intent recognition
2. **Context always extracted on ambiguity**: Client-side pre-filter errs on the side of extracting context
3. **Backend final authority**: Client hint only influences low-confidence classifications
4. **Existing `/execute` command untouched**: Still forces Agent mode with full context

**Fallback Path**:

```typescript
// In chatParticipant.ts
const shouldExtractContext = !seemsConversational || chatReferences.count > 0;
// Always extract if user explicitly selected files (#file references)
```

---

## 8. Testing Strategy

**Unit Tests**:

1. `test_intent_prefilter.ts`: Client-side pattern matching accuracy
2. `test_intent_hint_override.py`: Backend behavior with conflicting signals
3. `test_context_skip_performance.py`: Measure latency improvements

**Integration Tests**:

1. Conversational query → no context extraction → fast response
2. Task submission → context extracted → full agent routing
3. Ambiguous message → context extracted (safe fallback)
4. Mid-conversation mode switch → proper state tracking

**E2E Scenarios**:

```typescript
// Test cases
const scenarios = [
  {
    input: "What can you do?",
    expectContextSkip: true,
    expectIntent: "general_query",
  },
  {
    input: "Add error handling to login.py",
    expectContextSkip: false,
    expectIntent: "task_submission",
  },
  {
    input: "How does authentication work?",
    expectContextSkip: true,
    expectIntent: "general_query",
  },
  {
    input: "Fix the bug",
    expectContextSkip: false,
    expectIntent: "task_submission",
  }, // Ambiguous, needs context
];
```

---

## 9. Rollout Plan

**Phase 1**: Client-side pre-filter only (extensions)

- Deploy to dev, measure context skip rate
- Validate no false negatives (tasks misclassified as queries)

**Phase 2**: Backend integration (orchestrator)

- Deploy intent hint passing
- Monitor override rate (should be <5%)

**Phase 3**: System prompt updates (agents)

- Update supervisor and feature-dev prompts
- Test graceful degradation with missing context

**Phase 4**: Metrics and monitoring (Grafana)

- Add dashboards for context extraction savings
- Alert on high override rates (indicates pre-filter drift)

---

## 10. Success Metrics

**Performance**:

- Conversational query latency: **<500ms** (currently 2000-2500ms)
- Context extraction skip rate: **60-70%** for Ask mode traffic
- Task submission false negatives: **<2%** (tasks misidentified as queries)

**Quality**:

- User satisfaction with response speed (VSCode telemetry)
- Zero breaking changes to existing workflows
- Intent classification accuracy maintained at **>92%**

---

## Files Modified Summary

| File                                                     | Lines              | Changes                                        |
| -------------------------------------------------------- | ------------------ | ---------------------------------------------- |
| `extensions/vscode-codechef/src/chatParticipant.ts`      | ~200-320           | Add pre-filter, conditional context extraction |
| `agent_orchestrator/main.py`                             | 3492-3600, 490-510 | Intent hint integration, metrics               |
| `agent_orchestrator/agents/supervisor/system.prompt.md`  | 1-50               | Intent metadata awareness                      |
| `agent_orchestrator/agents/feature_dev/system.prompt.md` | 1-40               | Context availability handling                  |

**Total Estimated Effort**: 8-12 hours (mostly testing and validation)

---

## Further Considerations

1. **LLM cost impact**: Conversational handler uses Claude 3.5 Sonnet. Consider switching to DeepSeek V3 ($0.75/1M vs $3.00/1M) for Ask mode.

2. **Context caching**: For repeated conversational queries in same session, cache workspace context for 5 minutes. Would save extraction cost on follow-ups.

3. **Progressive context loading**: Instead of all-or-nothing, extract minimal context first (repo name, language), then full context only if intent evolves to task submission.

4. **User preference**: Add VSCode setting `codechef.alwaysExtractContext` for users who prefer thoroughness over speed.

5. **Training data collection**: Log (intent_hint, backend_intent, user_feedback) to improve pre-filter patterns over time.

---

**Summary**: This plan leverages 90% existing infrastructure (`intent_recognizer.py`, `conversational_handler_node`, `mode_hint` support) while adding only lightweight client-side optimizations and metadata passing. The key insight is that **backend already does the hard work** - we just need to give it better signals and skip unnecessary operations for obvious conversational queries.
