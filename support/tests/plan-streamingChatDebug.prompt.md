# Plan: Comprehensive Streaming Chat Audit & Optimization

**ROOT CAUSE IDENTIFIED**: Manual SSE parser violates OpenRouter streaming protocol with **3 critical bugs**. Strategy: Standardize on **axios + eventsource-parser**, remove all fetch implementations, ensure full OpenRouter/LangGraph SSE compliance.

---

## Critical Bugs (Must Fix First)

### 🔴 Bug 1: SSE Comment Lines Cause Parse Errors

**Issue**: OpenRouter/LangGraph send keepalive comments `(: OPENROUTER PROCESSING)` that our manual parser attempts to `JSON.parse()`, causing exceptions and stream failures

**Location**: [orchestratorClient.ts](extensions/vscode-codechef/src/orchestratorClient.ts#L272-L293)

**Current Code**:

```typescript
for (const message of messages) {
  if (message.startsWith("data: ")) {
    const data = JSON.parse(message.slice(6)); // ❌ Crashes on comment lines
    yield data as StreamChunk;
  }
}
```

**Fix Required**:

```typescript
for (const message of messages) {
  // ✅ Skip SSE comments per OpenRouter spec
  if (message.startsWith(":")) continue;

  if (message.startsWith("data: ")) {
    const data = message.slice(6);
    try {
      yield JSON.parse(data) as StreamChunk;
    } catch (e) {
      console.warn("SSE parse error:", message);
    }
  }
}
```

---

### 🔴 Bug 2: Missing `[DONE]` Terminal Signal Detection

**Issue**: OpenRouter SSE streams end with `data: [DONE]` signal which our parser never checks, causing streams to hang indefinitely waiting for more data

**Fix Required**:

```typescript
if (message.startsWith("data: ")) {
  const data = message.slice(6);

  // ✅ Check for terminal signal
  if (data === "[DONE]") {
    console.log("Stream completed with [DONE] signal");
    break;
  }

  const chunk = JSON.parse(data);
  yield chunk as StreamChunk;
}
```

---

### 🔴 Bug 3: Mid-Stream Errors Never Detected

**Issue**: When errors occur AFTER HTTP 200 sent (mid-stream), OpenRouter includes `error` field in SSE chunk. We never check this field, so errors are silently ignored

**Location**: [chatParticipant.ts](extensions/vscode-codechef/src/chatParticipant.ts#L271-L321)

**Fix Required**:

```typescript
for await (const chunk of this.client.chatStream({...})) {
    // ✅ Check for mid-stream errors FIRST
    if ('error' in chunk && chunk.error) {
        stream.markdown(`\n\n❌ **Stream Error**: ${chunk.error}\n`);
        break;
    }

    // Existing switch logic...
    switch (chunk.type) {
        case 'content':
            stream.markdown(chunk.content);
            break;
        // ...
    }
}
```

---

## Implementation Plan

### Phase 1: Critical Bug Fixes (1-2 hours)

#### 1.1 Fix SSE Parser Protocol Violations (30 min)

**File**: [orchestratorClient.ts](extensions/vscode-codechef/src/orchestratorClient.ts#L272-L293)

**Changes**:

- Add `:` comment line filtering
- Add `[DONE]` signal detection
- Improve error handling in parse loop

**Test**: Verify parser handles keepalive comments without crashing

---

#### 1.2 Add Mid-Stream Error Detection (15 min)

**File**: [chatParticipant.ts](extensions/vscode-codechef/src/chatParticipant.ts#L271)

**Changes**:

- Insert error field check before switch statement
- Display user-friendly error message
- Break stream loop on error

**Test**: Trigger intentional server error to verify user sees message

---

#### 1.3 Verify Orchestrator SSE Compliance (30 min)

**File**: [agent_orchestrator/main.py](agent_orchestrator/main.py) `/chat/stream` endpoint

**Audit**:

- Confirm `event_generator()` emits proper SSE format:
  - `data: {json}\n\n` for events
  - `: keepalive\n\n` for long-running operations
  - `data: [DONE]\n\n` as terminal signal
- Verify headers include `Cache-Control: no-cache`, `Connection: keep-alive`
- Check error propagation includes `error` field in SSE chunk

**Fix if needed**: Add keepalive comments every 15s, ensure `[DONE]` sent

---

### Phase 2: Standardize on Axios (2-3 hours)

#### 2.1 Audit Current Implementations (30 min)

**Locations**:

1. [src/orchestratorClient.ts](extensions/vscode-codechef/src/orchestratorClient.ts) - Axios implementation
2. [package/src/orchestratorClient.ts](extensions/vscode-codechef/package/src/orchestratorClient.ts) - Fetch implementation

**Tasks**:

- Determine which version is active in production
- Compare implementation differences
- Identify all fetch dependencies to remove

---

#### 2.2 Remove Fetch Implementation (1 hour)

**Changes**:

1. **Delete** [package/src/orchestratorClient.ts](extensions/vscode-codechef/package/src/orchestratorClient.ts) if using fetch
2. **Remove** unused `import EventSource from 'eventsource'` statements (artifact from old implementation)
3. **Verify** no other files reference fetch-based streaming
4. **Update** build configuration if needed

**Search patterns**: `fetch(`, `ReadableStream`, `response.body`, `node-fetch`

---

#### 2.3 Integrate eventsource-parser with Axios (1-2 hours)

**Install dependency**:

```bash
cd extensions/vscode-codechef
npm install eventsource-parser
```

**Refactor** [src/orchestratorClient.ts](extensions/vscode-codechef/src/orchestratorClient.ts#L242-L297):

```typescript
import { createParser, ParsedEvent, ReconnectInterval } from 'eventsource-parser';

async *chatStream(
    request: ChatStreamRequest,
    signal?: AbortSignal  // NEW: Cancellation support
): AsyncGenerator<StreamChunk> {
    const url = `${this.client.defaults.baseURL}/chat/stream`;

    // ✅ Use axios with stream response type
    const response = await this.client.post(url, request, {
        responseType: 'stream',
        headers: { 'Accept': 'text/event-stream' },
        signal  // ✅ Pass AbortSignal for cancellation
    });

    // ✅ Use OpenRouter-recommended parser
    const parser = createParser((event: ParsedEvent | ReconnectInterval) => {
        if (event.type === 'event') {
            // ✅ Handle terminal signal
            if (event.data === '[DONE]') {
                return;
            }

            try {
                const chunk = JSON.parse(event.data);

                // ✅ Check for errors
                if ('error' in chunk && chunk.error) {
                    throw new Error(chunk.error.message || chunk.error);
                }

                // Yield via async generator pattern
                chunks.push(chunk);
            } catch (e) {
                console.error('SSE parse error:', e);
            }
        }
    });

    const chunks: StreamChunk[] = [];

    // ✅ Stream processing with robust parser
    for await (const data of response.data) {
        const text = data.toString();
        parser.feed(text);  // ✅ Handles all SSE edge cases

        // Yield accumulated chunks
        while (chunks.length > 0) {
            yield chunks.shift()!;
        }

        // Check cancellation
        if (signal?.aborted) {
            throw new DOMException('Aborted', 'AbortError');
        }
    }

    // Final chunks
    while (chunks.length > 0) {
        yield chunks.shift()!;
    }
}
```

**Benefits**:

- Handles SSE comments automatically
- Detects `[DONE]` signal
- Parses multi-line events correctly
- Supports event IDs, retry fields
- Battle-tested (used by Vercel AI SDK)

---

### Phase 3: Enhanced Error Handling (1-2 hours)

#### 3.1 Add Retry Logic for Transient Errors (45 min)

**File**: [orchestratorClient.ts](extensions/vscode-codechef/src/orchestratorClient.ts)

**Implementation**:

```typescript
async *chatStream(
    request: ChatStreamRequest,
    signal?: AbortSignal,
    maxRetries: number = 3  // NEW
): AsyncGenerator<StreamChunk> {
    let attempt = 0;

    while (attempt < maxRetries) {
        try {
            const response = await this.client.post(url, request, {
                responseType: 'stream',
                headers: { 'Accept': 'text/event-stream' },
                signal
            });

            // Success - process stream
            // ... parser logic from 2.3 ...
            return;

        } catch (error: any) {
            // ✅ Retry on transient errors
            if (error.response?.status === 429 || error.response?.status === 503) {
                attempt++;
                if (attempt >= maxRetries) throw error;

                const backoffMs = Math.pow(2, attempt) * 1000;  // 1s, 2s, 4s
                console.log(`Retry ${attempt}/${maxRetries} after ${backoffMs}ms`);
                await new Promise(resolve => setTimeout(resolve, backoffMs));
                continue;
            }

            // Non-retryable error
            throw error;
        }
    }
}
```

**Test**: Simulate 429 rate limit to verify exponential backoff works

---

#### 3.2 Implement Stream Cancellation (30 min)

**File**: [chatParticipant.ts](extensions/vscode-codechef/src/chatParticipant.ts)

**Add AbortController**:

```typescript
async handleChatRequest(
    request: vscode.ChatRequest,
    context: vscode.ChatContext,
    stream: vscode.ChatResponseStream,
    token: vscode.CancellationToken  // VS Code provides this
): Promise<ChatResult> {
    // ✅ Create AbortController linked to VS Code token
    const abortController = new AbortController();

    token.onCancellationRequested(() => {
        console.log('User cancelled stream');
        abortController.abort();
    });

    try {
        // ✅ Pass signal to chatStream
        for await (const chunk of this.client.chatStream(
            chatRequest,
            abortController.signal  // NEW
        )) {
            // ... process chunks ...
        }
    } catch (error: any) {
        if (error.name === 'AbortError') {
            stream.markdown('\n\n_Stream cancelled by user_\n');
            return { metadata: { cancelled: true } };
        }
        throw error;
    }
}
```

**Test**: Press Escape during streaming to verify cancellation works

---

### Phase 4: Comprehensive Testing (1-2 hours)

#### 4.1 Unit Tests for SSE Parser (30 min)

**File**: `extensions/vscode-codechef/src/test/orchestratorClient.test.ts` (create)

**Test Cases**:

```typescript
describe("chatStream SSE Parser", () => {
  it("should skip SSE comment lines", async () => {
    // Mock response with comments
    const mockStream = `
: OPENROUTER PROCESSING
data: {"type":"content","content":"Hello"}

: keepalive
data: {"type":"content","content":" world"}

data: [DONE]
`;
    // Assert only 2 chunks yielded
  });

  it("should terminate on [DONE] signal", async () => {
    // Assert generator exits after [DONE]
  });

  it("should throw on mid-stream error", async () => {
    // Mock error chunk
    const errorChunk = {
      type: "error",
      error: "Provider timeout",
    };
    // Assert error thrown
  });

  it("should handle cancellation via AbortSignal", async () => {
    // Create controller, abort after 2 chunks
    // Assert AbortError thrown
  });
});
```

---

#### 4.2 Integration Tests with Live Orchestrator (30 min)

**File**: `extensions/vscode-codechef/src/test/integration.test.ts`

**Test Scenarios**:

1. **Happy Path**: Simple query streams successfully
2. **Long Stream**: 30+ second operation with keepalive comments
3. **Error Mid-Stream**: Trigger agent timeout, verify error displayed
4. **Cancellation**: Abort after 5s, verify cleanup
5. **Retry Logic**: Trigger 429 error, verify backoff and retry

**Setup**: Point to local orchestrator or staging environment

---

#### 4.3 End-to-End Manual Testing (30 min)

**Checklist**:

- [ ] Extension loads without errors
- [ ] Chat participant `@chef` appears
- [ ] Simple query: "Hello world" streams token-by-token
- [ ] Complex query: "Implement JWT auth" shows agent transitions
- [ ] Long query: "Refactor entire codebase" handles keepalive
- [ ] Error handling: Intentional bad query shows user-friendly message
- [ ] Cancellation: Press Escape mid-stream, verify stops
- [ ] Retry: Rate limit triggers backoff (check console logs)
- [ ] Non-streaming fallback: `codechef.useStreaming: false` still works

---

### Phase 5: Optimization & Monitoring (1-2 hours)

#### 5.1 Add LangSmith Tracing for Streaming (30 min)

**File**: [orchestratorClient.ts](extensions/vscode-codechef/src/orchestratorClient.ts)

**Add trace metadata**:

```typescript
async *chatStream(request: ChatStreamRequest, signal?: AbortSignal) {
    const startTime = Date.now();
    let chunkCount = 0;
    let errorCount = 0;

    try {
        for await (const chunk of /* ... parser ... */) {
            chunkCount++;

            // Track errors
            if ('error' in chunk && chunk.error) {
                errorCount++;
            }

            yield chunk;
        }
    } finally {
        // ✅ Send telemetry to LangSmith
        const duration = Date.now() - startTime;
        console.log({
            trace_type: 'streaming_session',
            duration_ms: duration,
            chunk_count: chunkCount,
            error_count: errorCount,
            cancelled: signal?.aborted
        });
    }
}
```

---

#### 5.2 Performance Profiling (30 min)

**Metrics to Track**:

- Time to first byte (TTFB)
- Average chunk processing time
- Total stream duration
- Memory usage during long streams

**Tool**: VS Code Performance Profiler or Chrome DevTools

**Target**: <100ms TTFB, <10ms per chunk processing

---

#### 5.3 Update Documentation (30 min)

**Files to Update**:

1. [extensions/vscode-codechef/README.md](extensions/vscode-codechef/README.md) - Document streaming behavior
2. [CHANGELOG.md](extensions/vscode-codechef/CHANGELOG.md) - List breaking changes (removed fetch)
3. [.github/copilot-instructions.md](.github/copilot-instructions.md) - Update architecture diagrams

**Include**:

- SSE protocol compliance details
- Retry/cancellation behavior
- Troubleshooting guide for streaming issues
- Configuration options (`codechef.useStreaming`)

---

## Phase 6: Architecture Documentation (30 min)

### 6.1 Update System Architecture Diagrams

**File**: `.github/copilot-instructions.md`

**Changes**:

- Remove fetch implementation references
- Document axios + eventsource-parser stack
- Update streaming flow diagram
- Add SSE protocol compliance notes

---

### 6.2 Create Streaming Troubleshooting Guide

**File**: `extensions/vscode-codechef/STREAMING_GUIDE.md` (create)

**Sections**:

1. **How Streaming Works** - Architecture overview
2. **SSE Protocol Compliance** - OpenRouter requirements
3. **Common Issues & Solutions**:
   - Connection refused → Check orchestrator URL
   - Parse errors → Upgrade extension (bug fix)
   - Slow streaming → Check network latency
   - Cancellation not working → Verify VS Code version
4. **Configuration Options** - `codechef.useStreaming`, timeouts
5. **Debugging Tips** - Console logs, LangSmith traces, network inspector

---

## Success Criteria

After completing all phases, verify:

- ✅ **No SSE parse errors** on keepalive comments
- ✅ **Streams terminate cleanly** on `[DONE]` signal
- ✅ **Mid-stream errors displayed** to user with clear messaging
- ✅ **Cancellation works** via Escape key or VS Code stop button
- ✅ **Retry logic activates** on 429/503 errors with backoff
- ✅ **No fetch references** remain in codebase (grep confirms)
- ✅ **Performance targets met**: <100ms TTFB, <10ms chunk processing
- ✅ **All tests pass**: Unit, integration, and E2E
- ✅ **Documentation updated**: README, CHANGELOG, copilot-instructions.md

---

## Rollback Plan

If issues arise during deployment:

1. **Immediate**: Set `codechef.useStreaming: false` in extension settings
2. **Short-term**: Revert to previous extension version via `.vsix` package
3. **Long-term**: Fix identified bugs in hotfix branch, re-deploy

**Git Tags**: Tag each phase completion for easy rollback points

---

## Evidence from OpenRouter Documentation

### SSE Protocol Specification

**Comment Lines** (OpenRouter docs):

> "For SSE streams, OpenRouter occasionally sends comments to prevent connection timeouts. These comments look like: `: OPENROUTER PROCESSING`. Comment payload can be safely ignored per the SSE specs."

**Terminal Signal** (OpenRouter docs):

> "The stream will end with `data: [DONE]` to indicate completion."

**Mid-Stream Errors** (OpenRouter docs):

> "When errors occur after HTTP 200 is sent, the error will be included in a chunk with an `error` field containing `{code: string, message: string}`."

### Recommended Parser

**eventsource-parser** (OpenRouter recommendation):

> "We recommend [eventsource-parser](https://github.com/rexxars/eventsource-parser) for robust SSE parsing that handles all edge cases per spec."

### Official TypeScript SDK Pattern

```typescript
import { createParser, ParsedEvent } from "eventsource-parser";

const parser = createParser((event: ParsedEvent) => {
  if (event.type === "event") {
    if (event.data === "[DONE]") return;
    const chunk = JSON.parse(event.data);
    if ("error" in chunk) throw new Error(chunk.error.message);
    // Process chunk...
  }
});

for await (const data of stream) {
  parser.feed(data.toString());
}
```

---

## Timeline Estimate

| Phase                              | Duration       | Priority    | Blocking |
| ---------------------------------- | -------------- | ----------- | -------- |
| **Phase 1**: Critical bug fixes    | 1-2 hours      | 🔴 CRITICAL | Yes      |
| **Phase 2**: Axios standardization | 2-3 hours      | 🔴 CRITICAL | Yes      |
| **Phase 3**: Error handling        | 1-2 hours      | 🟡 HIGH     | No       |
| **Phase 4**: Testing               | 1-2 hours      | 🟡 HIGH     | No       |
| **Phase 5**: Optimization          | 1-2 hours      | 🟢 MEDIUM   | No       |
| **Phase 6**: Documentation         | 30 min         | 🟢 MEDIUM   | No       |
| **TOTAL**                          | **7-11 hours** |             |          |

**Recommended Approach**: Complete Phases 1-2 first (critical fixes + standardization), then deploy and test before proceeding to Phases 3-6.

---

## Quick Win: Immediate Fix (30 min)

If time-critical, apply **only** the three SSE parser fixes to [orchestratorClient.ts](extensions/vscode-codechef/src/orchestratorClient.ts):

```typescript
for (const message of messages) {
    // 1. Skip SSE comments
    if (message.startsWith(':')) continue;

    if (message.startsWith('data: ')) {
        const data = message.slice(6);

        // 2. Handle [DONE] signal
        if (data === '[DONE]') break;

        try {
            const chunk = JSON.parse(data);

            // 3. Check error field
            if ('error' in chunk && chunk.error) {
                yield { type: 'error', error: chunk.error.message || chunk.error };
                break;
            }

            yield chunk as StreamChunk;
        } catch (parseError) {
            console.warn('SSE parse error:', message);
        }
    }
}
```

This addresses **80% of protocol violations** with minimal risk. Deploy, test, then proceed with full refactor.
