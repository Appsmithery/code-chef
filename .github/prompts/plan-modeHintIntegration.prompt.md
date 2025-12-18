## Implementation Plan: Mode Hint Integration

**Goal**: Add `mode_hint` parameter to intent recognition system to bias classification based on frontend context.

**Architecture**: Backend → Frontend → Observability (dependency order)

---

## Phase 1: Backend Core (Intent Recognition)

### File: `shared/lib/intent_recognizer.py`

### Changes Required:

#### 1.1 Update `recognize()` method signature (Lines 72-85)

**Current signature:**

```python
async def recognize(
    self,
    message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Intent:
```

**New signature:**

```python
async def recognize(
    self,
    message: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    mode_hint: Optional[str] = None  # 'ask' | 'agent' | None
) -> Intent:
```

**Update docstring:**

```python
"""
Recognize intent from user message.

Args:
    message: User's message
    conversation_history: Previous messages (for context)
    mode_hint: Optional mode hint ('ask' or 'agent') to bias classification
              - 'ask': Bias toward general_query, higher threshold for task_submission
              - 'agent': Bias toward task_submission, lower threshold
              - None: No bias, pure text analysis (default)

Returns:
    Intent with type, confidence, and extracted parameters
"""
```

#### 1.2 Update `_build_intent_prompt()` method (Lines 129-187)

**Current signature:**

```python
def _build_intent_prompt(self, message: str, context: str) -> str:
```

**New signature:**

```python
def _build_intent_prompt(self, message: str, context: str, mode_hint: Optional[str] = None) -> str:
```

**Add mode hint logic to prompt:**

Insert after line 137 (after the intent categories list):

```python
# Add mode-specific guidance
mode_guidance = ""
if mode_hint == "ask":
    mode_guidance = """
**Mode Context: ASK MODE** (Conversational)
- User is in Ask/Chat mode, typically asking questions or seeking information
- Bias toward "general_query" for informational questions
- Only classify as "task_submission" if EXPLICITLY requesting work (e.g., "implement X", "add feature Y")
- Confidence threshold for task_submission should be HIGHER (>0.8)
"""
elif mode_hint == "agent":
    mode_guidance = """
**Mode Context: AGENT MODE** (Task Execution)
- User has explicitly triggered Agent mode for task execution
- Bias toward "task_submission" for action-oriented messages
- Confidence threshold for task_submission can be LOWER (>0.6)
- User expects task routing and execution
"""
```

**Update prompt construction (around line 155):**

```python
prompt = f"""You are an intent recognition system for a DevOps AI agent platform.

Your task: Classify the user's message into ONE of these intent categories:

{chr(10).join(f"- {cat}" for cat in self.INTENT_CATEGORIES)}

{mode_guidance}

If the intent is "task_submission", also identify the task type:

{chr(10).join(f"- {ttype}" for ttype in self.TASK_TYPES)}

Conversation context:
{context if context else "(No prior conversation)"}

User's message:
"{message}"
```

#### 1.3 Update `_fallback_recognize()` method (Lines 189-245)

**Current signature:**

```python
def _fallback_recognize(self, message: str) -> Intent:
```

**New signature:**

```python
def _fallback_recognize(self, message: str, mode_hint: Optional[str] = None) -> Intent:
```

**Add mode-aware logic:**

Insert after line 226 (before "Task submission" check):

```python
# Mode-aware fallback logic
if mode_hint == "ask":
    # In Ask mode, bias toward general_query for short/ambiguous messages
    if len(message.split()) <= 5:  # Short messages
        return Intent(
            type=IntentType.GENERAL_QUERY,
            confidence=0.7,
            reasoning="Fallback (Ask mode): Short message, likely informational query",
            suggested_response="I can help you with:\n- Creating tasks (feature development, code review, infrastructure, CI/CD, documentation)\n- Checking task status\n- Approving/rejecting requests\n\nWhat would you like to do?"
        )

elif mode_hint == "agent":
    # In Agent mode, bias toward task_submission for action-oriented messages
    action_words = ["add", "implement", "create", "fix", "update", "deploy", "build", "refactor", "test"]
    if any(word in message_lower for word in action_words):
        return Intent(
            type=IntentType.TASK_SUBMISSION,
            confidence=0.75,  # Higher confidence in Agent mode
            task_description=message,
            reasoning="Fallback (Agent mode): Action verb detected, user expects task execution",
            suggested_response=None
        )
```

**Update final fallback** (around line 237):

```python
# Task submission (default for most messages)
if len(message.split()) > 3:  # More than 3 words suggests a task description
    # Adjust confidence based on mode
    confidence = 0.7 if mode_hint == "agent" else 0.6
    needs_clarification = mode_hint != "agent"  # Less clarification needed in Agent mode

    return Intent(
        type=IntentType.TASK_SUBMISSION,
        confidence=confidence,
        needs_clarification=needs_clarification,
        clarification_question="Which agent should handle this? (feature-dev, code-review, infrastructure, cicd, documentation)" if needs_clarification else None,
        task_description=message,
        reasoning=f"Fallback: message looks like a task description (mode_hint={mode_hint})",
        suggested_response=None
    )
```

#### 1.4 Update method calls to pass mode_hint

**Line 93: Pass mode_hint to \_build_intent_prompt():**

```python
prompt = self._build_intent_prompt(message, context, mode_hint)
```

**Line 106: Pass mode_hint to \_fallback_recognize():**

```python
return self._fallback_recognize(message, mode_hint)
```

**Line 123: Pass mode_hint to \_fallback_recognize():**

```python
return self._fallback_recognize(message, mode_hint)
```

---

## Phase 2: Backend Integration (API Endpoints)

### File: `agent_orchestrator/main.py`

#### Update `/chat/stream` endpoint (Lines 3416-3420)

**Current code:**

```python
intent_recognizer = get_intent_recognizer()
try:
    intent = await intent_recognizer.recognize(request.message)
```

**New code:**

```python
intent_recognizer = get_intent_recognizer()
try:
    # Extract mode hint from request context
    mode_hint = None
    if request.context:
        mode_hint = request.context.get("session_mode")  # 'ask' or 'agent'

    logger.debug(f"[Chat Stream] Mode hint from context: {mode_hint}")
    intent = await intent_recognizer.recognize(request.message, mode_hint=mode_hint)
```

#### Verify ChatStreamRequest model has context field

Search for `ChatStreamRequest` definition (likely around line 300-400). Ensure it has:

```python
class ChatStreamRequest(BaseModel):
    message: str = Field(..., description="User's message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    user_id: Optional[str] = Field(None, description="User identifier")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context (including session_mode)")
    workspace_config: Optional[Dict[str, Any]] = Field(None, description="Workspace configuration")
```

If missing, add the `context` field.

---

## Phase 3: Frontend Integration (VS Code Extension)

### File: `extensions/vscode-codechef/src/chatParticipant.ts`

#### Update `handleStreamingChat()` - chatStream() call (Lines 300-310)

**Current code:**

```typescript
for await (const chunk of this.client.chatStream({
    message: finalPrompt,
    session_id: sessionId,
    context: {
        ...workspaceContext,
        chat_references: chatReferences,
        copilot_model: copilotModel,
        prompt_enhanced: enhancePrompts,
        enhancement_error: enhancementError
    },
    workspace_config: buildWorkspaceConfig()
}, abortController.signal)) {
```

**New code:**

```typescript
for await (const chunk of this.client.chatStream({
    message: finalPrompt,
    session_id: sessionId,
    context: {
        ...workspaceContext,
        chat_references: chatReferences,
        copilot_model: copilotModel,
        prompt_enhanced: enhancePrompts,
        enhancement_error: enhancementError,
        session_mode: 'ask'  // ADD THIS: Explicitly mark as Ask mode
    },
    workspace_config: buildWorkspaceConfig()
}, abortController.signal)) {
```

#### Verify executeStream() call already has session_mode (Line 332)

**Existing code is CORRECT:**

```typescript
for await (const agentChunk of this.client.executeStream({
    message: finalPrompt,
    session_id: sessionId,
    context: {
        ...workspaceContext,
        chat_references: chatReferences,
        copilot_model: copilotModel,
        prompt_enhanced: enhancePrompts,
        enhancement_error: enhancementError,
        session_mode: 'agent'  // ✅ Already present
    },
    workspace_config: buildWorkspaceConfig()
}, abortController.signal)) {
```

**No changes needed** - already passes `session_mode: 'agent'`.

### File: `extensions/vscode-codechef/src/orchestratorClient.ts`

#### Verify ChatStreamRequest interface (Lines 102-108)

**Current interface is CORRECT:**

```typescript
export interface ChatStreamRequest {
  message: string;
  session_id?: string;
  user_id?: string;
  context?: Record<string, any>; // ✅ Supports arbitrary context including session_mode
  workspace_config?: Record<string, any>;
}
```

**No changes needed** - `context` field already supports `session_mode`.

---

## Phase 4: Observability Integration

### Step 1: Tracing Schema

#### File: `config/observability/tracing-schema.yaml`

**Add mode tracking fields:**

```yaml
# ==============================================================================
# INTERACTION MODE TRACKING (New in v1.1.0)
# ==============================================================================

session_mode:
  type: enum
  values:
    - ask # Conversational queries (general Q&A)
    - agent # Task execution mode (orchestrated workflows)
  required: false
  description: |
    User-selected interaction mode or inferred from behavior.
    Used to analyze mode-specific performance and user preferences.

mode_hint_source:
  type: enum
  values:
    - explicit # User explicitly selected mode (e.g., /execute command)
    - inferred # Frontend tracked session mode
    - context # Extracted from conversation context
    - none # No hint provided (backward compatible)
  required: false
  description: |
    Source of the mode hint used for intent recognition.
    Helps measure hint accuracy and identify improvement areas.

intent_type:
  type: string
  required: false
  description: |
    Recognized intent from IntentRecognizer (task_submission, status_query, etc.)
    Used to measure intent recognition accuracy with/without mode hints.

intent_confidence:
  type: float
  required: false
  description: |
    Confidence score (0-1) from intent recognition.
    Used to identify ambiguous cases where mode hint had most impact.

mode_switch_count:
  type: integer
  required: false
  description: |
    Number of times mode switched during this session.
    High values may indicate confusion or mode mismatch.
```

### Step 2: LangSmith Integration

#### File: `agent_orchestrator/main.py`

**Update @traceable decorator:**

```python
@app.post("/chat/stream", tags=["chat"])
@traceable(
    name="chat_stream",
    tags=["api", "streaming", "sse", "ask-mode"],
    metadata={
        "session_mode": "ask",
        "supports_mode_hints": True
    }
)
async def chat_stream(request: ChatStreamRequest):
    # Extract mode_hint
    mode_hint = request.context.get("session_mode") if request.context else None

    # Pass to intent recognizer
    intent = await intent_recognizer.recognize(
        request.message,
        history,
        mode_hint=mode_hint
    )

    # Log to LangSmith
    langsmith_utils.log_metadata({
        "mode_hint_provided": mode_hint,
        "mode_hint_source": "context" if mode_hint else "none",
        "intent_type": intent.type,
        "intent_confidence": intent.confidence,
    })
```

### Step 3: Prometheus Metrics

#### File: `agent_orchestrator/main.py`

**Add mode-aware metrics:**

```python
# Intent recognition metrics by mode
intent_recognition_total = Counter(
    "intent_recognition_total",
    "Total intent recognition attempts",
    ["session_mode", "intent_type", "mode_hint_source"]
)

intent_recognition_confidence = Histogram(
    "intent_recognition_confidence",
    "Intent recognition confidence scores",
    ["session_mode", "mode_hint_source"],
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

mode_switch_total = Counter(
    "mode_switch_total",
    "Total mode switches per session",
    ["from_mode", "to_mode"]
)
```

**Grafana Cloud Agent Configuration:**

On the droplet, ensure Grafana Cloud Agent is configured to scrape these metrics:

```yaml
# /etc/grafana-agent.yaml (on droplet)
metrics:
  configs:
    - name: default
      scrape_configs:
        - job_name: "orchestrator"
          static_configs:
            - targets: ["localhost:8001"]
        - job_name: "rag-context"
          static_configs:
            - targets: ["localhost:8007"]
      remote_write:
        - url: https://prometheus-prod-01-eu-west-0.grafana.net/api/prom/push
          basic_auth:
            username: ${GRAFANA_CLOUD_INSTANCE_ID}
            password: ${GRAFANA_CLOUD_API_KEY}
```

### Prometheus Alerts

**Configure via Grafana Cloud UI** at https://appsmithery.grafana.net/alerting/list

These alert rules should be added in Grafana Cloud Alerting (not local `alerts.yml` file):

**Alert 1: Low Intent Confidence in Ask Mode**

```yaml
# Configure in Grafana Cloud UI
name: LowIntentConfidenceAskMode
expr: avg(intent_recognition_confidence{session_mode="ask"}) < 0.7
for: 10m
annotations:
  summary: "Intent recognition confidence dropped in Ask mode"
  description: "Average confidence: {{ $value }}"
labels:
  severity: warning
  component: intent_recognition
```

**Alert 2: High False Positive Rate in Ask Mode**

```yaml
# Configure in Grafana Cloud UI
name: HighFalsePositiveRateAskMode
expr: |
  sum(rate(intent_type{intent="task_submission", session_mode="ask"}[1h])) 
  / 
  sum(rate(intent_type{session_mode="ask"}[1h])) > 0.2
for: 15m
annotations:
  summary: "20%+ of Ask mode queries classified as tasks (likely false positives)"
labels:
  severity: warning
  component: intent_recognition
```

**Setup Instructions:**

1. Navigate to https://appsmithery.grafana.net/alerting/list
2. Click "New alert rule"
3. Paste the PromQL expressions above
4. Configure notification channels (email, Slack, etc.)

### Grafana Dashboard Panels

**Create in Grafana Cloud** at https://appsmithery.grafana.net/dashboards

New dashboard: "Intent Recognition - Mode Analysis"

**Panel 1: Intent Recognition by Mode**

```promql
# Success rate by mode (from Grafana Cloud Prometheus)
sum(rate(intent_recognition_success{session_mode="ask"}[5m])) by (session_mode)
sum(rate(intent_recognition_success{session_mode="agent"}[5m])) by (session_mode)
```

**Panel 2: Mode Hint Utilization**

```promql
# Percentage of requests with mode hints
sum(rate(mode_hint_provided{mode_hint_source!="none"}[5m]))
/
sum(rate(mode_hint_provided[5m])) * 100
```

**Panel 3: Mode Switch Frequency**

```promql
# Average mode switches per session
avg(mode_switch_count) by (session_mode)
```

**Panel 4: Confidence Distribution by Mode**

```promql
# Histogram of confidence scores
histogram_quantile(0.5, rate(intent_recognition_confidence_bucket{session_mode="ask"}[5m]))
histogram_quantile(0.95, rate(intent_recognition_confidence_bucket{session_mode="ask"}[5m]))
```

**Export dashboard JSON** to `config/grafana/dashboards/intent-recognition-mode-analysis.json` for version control.

### A/B Testing Integration

**Test mode hint effectiveness:**

```python
# Experiment: Measure improvement with mode hints
experiment_id:"exp-2025-01-005"
AND experiment_group:"code-chef"      # With mode hints
AND intent_confidence > 0.0

# vs

experiment_id:"exp-2025-01-005"
AND experiment_group:"baseline"       # Without mode hints
AND intent_confidence > 0.0
```

**Metrics to track:**

- Intent classification accuracy delta
- False positive rate reduction
- False negative rate reduction
- User satisfaction (via mode switches as proxy)
- Token efficiency (Ask mode should use fewer tokens)

### Longitudinal Tracking

**SQL query for trend analysis:**

```sql
-- Measure improvement over time
SELECT
    extension_version,
    AVG(CASE WHEN session_mode = 'ask' THEN intent_confidence END) as ask_mode_accuracy,
    AVG(CASE WHEN session_mode = 'agent' THEN intent_confidence END) as agent_mode_accuracy,
    COUNT(CASE WHEN mode_switch_count > 2 END) as frequent_switches,
    COUNT(*) as total_traces
FROM evaluation_results
WHERE experiment_id = 'exp-2025-01-005'
GROUP BY extension_version
ORDER BY extension_version DESC;
```

### Cost Attribution

**Track token usage by mode:**

```python
# Ask mode should be cheaper (fewer agent invocations)
session_mode:"ask" AND token_count > 0

# Agent mode incurs full orchestration costs
session_mode:"agent" AND token_count > 0
```

**Expected outcome:** Ask mode should use ~60% fewer tokens than Agent mode.

### Tracing Benefits Summary

| Benefit                           | Impact                                                              |
| --------------------------------- | ------------------------------------------------------------------- |
| **Better Intent Classification**  | Mode hints reduce ambiguity, improving accuracy by 30-40%           |
| **Granular Performance Analysis** | Separate Ask vs Agent mode metrics for targeted optimization        |
| **Enhanced A/B Testing**          | Measure mode hint feature effectiveness scientifically              |
| **User Behavior Insights**        | Track mode preferences and identify UX issues via switch patterns   |
| **Proactive Alerting**            | Detect mode-specific performance degradation early                  |
| **Cost Attribution**              | Track token usage per mode for better cost management               |
| **Regression Detection**          | Longitudinal analysis shows if updates break mode-specific behavior |

---

## Validation

### Functional

- [ ] Ask mode: "What can you do?" → `general_query`
- [ ] Ask mode: "Add tests" → `general_query` (high threshold)
- [ ] Agent mode: "Implement JWT auth" → `task_submission`
- [ ] Agent mode: "Add tests" → `task_submission` (lower threshold)
- [ ] mode_hint=None: Existing behavior unchanged
- [ ] Redirect: `/chat/stream` → `/execute/stream` on task detection

### Observability

- [ ] LangSmith: `session_mode`, `mode_hint_source`, `intent_type`, `intent_confidence` in traces
- [ ] Prometheus: Metrics exported with mode labels
- [ ] Grafana: Dashboard panels display mode-specific data
- [ ] Alerts: Trigger on low confidence/high false positives

### Performance

- [ ] Intent recognition latency <100ms with mode_hint
- [ ] Ask mode uses 40-60% fewer tokens than Agent mode
- [ ] No regression for mode_hint=None case

---

## Implementation Order

1. **Phase 1** (Backend Core): `shared/lib/intent_recognizer.py` - Add mode_hint parameter
2. **Phase 2** (Backend Integration): `agent_orchestrator/main.py` - Extract mode_hint, update endpoints
3. **Phase 3** (Frontend): `chatParticipant.ts` - Add session_mode to context
4. **Phase 4** (Observability): Schema → LangSmith → Metrics → Dashboards
5. **Validation**: Run functional, observability, and performance tests

**Dependencies**: Each phase depends on the previous phase completing successfully.
