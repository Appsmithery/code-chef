# Plan: Systematic Streaming Participant Audit

A comprehensive debugging plan to diagnose the **ERR_CONNECTION_REFUSED** streaming error by isolating each component in the VS Code extension architecture, focusing on the critical EventSource → fetch migration that likely broke functionality.

## Steps

### 1. Verify Network Layer Baseline

Test [orchestratorClient.ts](extensions/vscode-codechef/src/orchestratorClient.ts) HTTP connectivity using non-streaming `/chat` endpoint and health check, confirm axios instance works with same baseURL that fails for fetch-based streaming

### 2. Isolate fetch API Compatibility

Add diagnostic logging to [chatStream()](extensions/vscode-codechef/src/orchestratorClient.ts#L242-L297) to check if `fetch` is defined, `response.body` exists, and `ReadableStream` is available in VS Code extension host Node.js context

### 3. Test SSE Parser Logic

Create minimal test harness for the manual SSE parsing buffer logic (lines 272-293), verify `\n\n` separator handling and `data: ` prefix extraction work correctly with sample responses

### 4. Compare EventSource vs fetch Implementations

Temporarily restore the old `eventsource` npm package approach in a separate branch, confirm if streaming works with original implementation to definitively identify fetch migration as root cause

### 5. Audit Configuration & Settings

Verify [package.json](extensions/vscode-codechef/package.json) extension manifest, check that `codechef.useStreaming` setting properly toggles behavior in [chatParticipant.ts](extensions/vscode-codechef/src/chatParticipant.ts#L46-L54), confirm orchestratorUrl is correctly resolved

### 6. Trace Full Request Lifecycle

Add end-to-end logging from [handleChatRequest()](extensions/vscode-codechef/src/chatParticipant.ts#L110-L353) through `chatStream()` to capture exact failure point: URL construction, headers, request body, first byte received timing

## Further Considerations

### 1. EventSource Package Recovery

Should we revert to the proven `eventsource` npm library (which was working) rather than continuing to debug fetch polyfill issues? This is low-risk since curl works meaning backend is fine.

### 2. Node.js fetch Polyfill

Does VS Code's bundled Node.js version support native fetch without polyfills? May need to explicitly add `node-fetch` or `undici` as dependency with proper ReadableStream support.

### 3. Supervisor Response Filtering

The 3-chunk buffering logic (lines 252-297) adds complexity—could this interact poorly with the new stream parser causing premature connection closure?

## Key Finding from Research

**Most Critical Issue: EventSource → fetch Migration**

The most significant recent change affecting streaming is the **switch from the `eventsource` npm package to native `fetch`** with `ReadableStream`. This change:

1. **Removes dependency** on `eventsource` library (still imported but unused)
2. **Uses browser-style fetch API** in Node.js context (VS Code extension host)
3. **Manual SSE parsing** via `TextDecoder` and buffer management
4. **Potential compatibility issues** with Node.js fetch polyfill

### Comparison Table

| Aspect             | Old (EventSource)         | New (fetch)                               |
| ------------------ | ------------------------- | ----------------------------------------- |
| **Library**        | `eventsource` npm package | Native `fetch`                            |
| **Transport**      | Axios stream              | ReadableStream                            |
| **SSE Parsing**    | Built-in                  | Manual (`data:` prefix, `\n\n` separator) |
| **Error Handling** | EventSource error events  | try/catch + reader errors                 |
| **Node.js Compat** | Excellent (purpose-built) | Depends on polyfill                       |
| **Browser Compat** | N/A (Node.js only)        | Excellent                                 |

### Potential Issues

- **ERR_CONNECTION_REFUSED**: Likely fetch polyfill not properly configured for Node.js
- **Stream not starting**: `response.body` might be `null` in some Node.js versions
- **Incomplete messages**: Buffer management might have edge cases

### Recommendation

Consider reverting to `eventsource` or using a dedicated SSE client library for Node.js environments.
