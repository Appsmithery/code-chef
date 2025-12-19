# Streaming Chat Diagnosis & Fix Plan

**Date**: December 19, 2025  
**Status**: 🔴 CRITICAL - Streaming stalling/timing out  
**Priority**: P0 - Blocking user experience

---

## Problem Statement

Streaming chat responses are stalling/timing out despite multiple attempted fixes:

- ✅ eventsource-parser integration (handles SSE comments)
- ✅ Axios retry logic with backoff
- ✅ FastAPI SSE headers (X-Accel-Buffering: no)
- ✅ Keepalive comments every 15s
- ❌ **Still experiencing timeouts/stalls**

---

## Architecture Overview

```
VS Code Extension (Client)
    ↓ HTTPS
Caddy Reverse Proxy :443
    ↓ HTTP
FastAPI orchestrator:8001
    ↓ LangGraph streaming
OpenRouter API (LLM providers)
```

**Key Insight**: Caddy is a **critical bottleneck** - missing SSE-specific configuration!

---

## Root Cause Analysis

### 1. ❌ **Caddy Missing SSE Directives** (LIKELY PRIMARY CAUSE)

**Current Config** (`config/caddy/Caddyfile`):

```caddy
handle /chat/stream {
    reverse_proxy orchestrator:8001
}
```

**Problem**: Missing these CRITICAL directives for SSE:

- `flush_interval 0` - Disable buffering, send chunks immediately
- `request_buffering off` - Don't buffer client request
- `response_buffering size 0` - Don't buffer upstream response

**Evidence**: Caddy by default buffers responses for performance. SSE requires immediate flushing.

**Fix Required**:

```caddy
handle /chat/stream {
    reverse_proxy orchestrator:8001 {
        flush_interval -1      # Disable response buffering (critical for SSE)
        request_buffering off  # Don't buffer request body
        transport http {
            read_timeout 5m    # Allow long-running connections
            write_timeout 5m
        }
    }
}

handle /execute/stream {
    reverse_proxy orchestrator:8001 {
        flush_interval -1
        request_buffering off
        transport http {
            read_timeout 5m
            write_timeout 5m
        }
    }
}
```

**Reference**: https://caddyserver.com/docs/caddyfile/directives/reverse_proxy#streaming

---

### 2. ⚠️ **OpenRouter Keepalive Comments Not Visible**

**OpenRouter Behavior**:

- Sends `: OPENROUTER PROCESSING` keepalive comments
- Prevents connection timeout during slow LLM processing

**Current Code** (orchestratorClient.ts):

```typescript
const parser = createParser({
  onEvent: (event: EventSourceMessage) => {
    /* handles events */
  },
  onComment: (comment: string) => {
    console.log(`[Streaming] Keepalive: ${comment}`); // ✅ Correct
  },
});
```

**Issue**: If Caddy buffers these comments, they never reach the client, causing timeout!

---

### 3. ✅ **FastAPI SSE Implementation** (Likely OK)

**Current Headers**:

```python
headers={
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # ✅ Disables nginx buffering
    "Access-Control-Allow-Origin": "*",
}
```

**Keepalive Logic**:

```python
keepalive_interval = 15  # Send keepalive every 15 seconds
if current_time - last_keepalive > keepalive_interval:
    yield ": keepalive\n\n"
```

**Verdict**: Implementation looks correct per SSE spec.

---

### 4. ⚠️ **Axios Streaming Configuration**

**Current Setup** (orchestratorClient.ts):

```typescript
const response = await this.client.post(url, request, {
  responseType: "stream",
  headers: {
    Accept: "text/event-stream",
  },
  signal, // ✅ AbortSignal for cancellation
});
```

**Potential Issue**: Axios `responseType: 'stream'` expects Node.js environment, but VS Code extensions run in Electron/Chromium.

**Better Approach**: Use native `fetch()` with ReadableStream:

```typescript
const response = await fetch(url, {
  method: "POST",
  headers: {
    Accept: "text/event-stream",
    "Content-Type": "application/json",
  },
  body: JSON.stringify(request),
  signal,
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

// Feed to eventsource-parser
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  parser.feed(decoder.decode(value));
}
```

---

### 5. ⚠️ **Container Resource Limits**

**Current Limits** (docker-compose.yml):

```yaml
deploy:
  resources:
    limits:
      cpus: "2.0"
      memory: 2G
```

**Droplet Specs**: 4GB RAM, 2 vCPUs

**Concern**: If orchestrator hits memory limit during streaming, could cause stalls.

**Check**:

```bash
ssh root@45.55.173.72 "docker stats --no-stream"
```

---

## Testing Strategy

### Phase 1: Isolate Infrastructure vs Application

#### Test 1: Direct Orchestrator Connection (Bypass Caddy)

```bash
# SSH into droplet
ssh root@45.55.173.72

# Test streaming directly to orchestrator (port 8001)
curl -N -H "Accept: text/event-stream" -H "Content-Type: application/json" \
  -d '{"message": "hello", "user_id": "test"}' \
  -X POST http://localhost:8001/chat/stream
```

**Expected**: Should see immediate SSE stream without buffering.

**If works**: Problem is Caddy configuration.  
**If fails**: Problem is FastAPI/LangGraph implementation.

---

#### Test 2: Minimal SSE Endpoint

Add diagnostic endpoint to `agent_orchestrator/main.py`:

```python
@app.get("/test/stream")
async def test_stream():
    """Minimal SSE test endpoint - no LangGraph, just counting."""
    async def count_generator():
        for i in range(10):
            yield f"data: {json.dumps({'count': i})}\n\n"
            await asyncio.sleep(1)
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        count_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

Test:

```bash
# Via Caddy (public endpoint)
curl -N https://codechef.appsmithery.co/test/stream

# Direct to orchestrator
ssh root@45.55.173.72 "curl -N http://localhost:8001/test/stream"
```

**Expected**: Should count 0-9 with 1-second intervals.

---

#### Test 3: OpenRouter Direct Connection

Test if OpenRouter streaming works independently:

```python
import os
import httpx

async def test_openrouter_streaming():
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            async for line in response.aiter_lines():
                print(line)
```

---

### Phase 2: Fix Caddy Configuration

**Changes Required**:

1. **Update `config/caddy/Caddyfile`**:

   - Add `flush_interval -1` to `/chat/stream` and `/execute/stream`
   - Add `request_buffering off`
   - Increase read/write timeouts to 5m

2. **Restart Caddy**:

   ```bash
   ssh root@45.55.173.72 "cd /opt/code-chef/deploy && docker compose restart caddy"
   ```

3. **Validate**:
   ```bash
   curl -N https://codechef.appsmithery.co/test/stream
   ```

---

### Phase 3: Optimize Client-Side Streaming

**Consider Switching from Axios to Fetch**:

Axios in browser context doesn't handle SSE well. Native `fetch()` + ReadableStream is better.

**Benefits**:

- Native browser API (no polyfill needed)
- Better memory management with backpressure
- Simpler cancellation with AbortController
- More predictable behavior in Electron/VS Code

**Example**:

```typescript
async *chatStream(request: ChatStreamRequest, signal?: AbortSignal) {
    const url = `${this.baseURL}/chat/stream`;

    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
            'Authorization': `Bearer ${this.apiKey}`
        },
        body: JSON.stringify(request),
        signal
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }

    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    const parser = createParser({
        onEvent: (event) => {
            if (event.data === '[DONE]') return;
            const chunk = JSON.parse(event.data);
            // Yield chunk via async generator
        }
    });

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        parser.feed(buffer);
        buffer = '';  // Clear after feeding
    }
}
```

---

## Implementation Plan

### ✅ **Step 1: Fix Caddy Configuration** (15 min)

- Update Caddyfile with SSE directives
- Deploy to droplet
- Test `/test/stream` endpoint

### ✅ **Step 2: Add Diagnostic Endpoint** (10 min)

- Add `/test/stream` to main.py
- Deploy and test direct vs via Caddy

### 🔄 **Step 3: Test OpenRouter Direct** (10 min)

- Isolate if issue is upstream vs our infrastructure
- Run test script on droplet

### 🔄 **Step 4: Optimize Client** (30 min)

- Consider switching Axios → Fetch
- Implement proper backpressure handling
- Test in VS Code extension

---

## Success Criteria

1. ✅ `/test/stream` endpoint streams 10 chunks at 1-second intervals
2. ✅ OpenRouter keepalive comments visible in client logs
3. ✅ No timeouts for conversations under 2 minutes
4. ✅ Proper cancellation with AbortSignal
5. ✅ Memory usage stays under 1.5GB for orchestrator container

---

## Rollback Plan

If changes break streaming:

```bash
# Revert Caddyfile
cd /opt/code-chef
git checkout HEAD -- config/caddy/Caddyfile
cd deploy && docker compose restart caddy

# Check health
curl https://codechef.appsmithery.co/health
```

---

## Next Steps

1. **Immediate**: Fix Caddy configuration (highest priority)
2. **Short-term**: Add diagnostic endpoints
3. **Medium-term**: Consider fetch() over Axios
4. **Long-term**: Monitor with Grafana SSE-specific metrics

---

## References

- [Caddy Reverse Proxy Streaming](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy#streaming)
- [OpenRouter SSE Streaming](https://openrouter.ai/docs/api/reference/streaming)
- [SSE Specification](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [eventsource-parser](https://github.com/rexxars/eventsource-parser)
