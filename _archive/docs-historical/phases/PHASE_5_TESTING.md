# Phase 5 Chat Endpoint - Testing Plan

**Status**: Ready for Testing  
**Components**: Intent Recognition, Session Management, Chat Endpoint  
**Estimated Time**: 5-10 minutes

---

## Recommendation: Test Chat Endpoint Now ✅

### Reasons to Test Early:

1. **Foundation for Phase 5**: The chat endpoint is the entry point for all conversational features. If intent recognition or session management is broken, everything else breaks.

2. **Database Dependencies**: We need to verify:

   - Chat sessions table exists (did we run migrations?)
   - Session persistence works across requests
   - Message history is properly stored

3. **Integration Points**: Chat endpoint integrates with:

   - `/orchestrate` (for task submissions)
   - Task registry (for status queries)
   - Approval endpoints (for approval decisions)
   - If any of these are broken, we'll catch it now vs. after building more features on top

4. **Quick Feedback Loop**: The test script takes ~30 seconds to run. Better to catch issues now than debug a complex multi-component failure later.

5. **Gradient AI Availability**: We should verify the Gradient LLM is working for intent recognition before building more LLM-dependent features.

### What Could Go Wrong:

- ❌ Database schema not deployed → chat sessions fail to persist
- ❌ Gradient API key issues → intent recognition falls back to keywords
- ❌ Session management bugs → multi-turn conversations don't work
- ❌ Import errors → modules not found when orchestrator starts

---

## Testing Plan (5-10 minutes)

### Step 1: Deploy Schema Updates

```bash
# Copy SQL files to droplet
scp config/state/schema.sql root@45.55.173.72:/opt/Dev-Tools/config/state/

# SSH and run migrations
ssh root@45.55.173.72
cd /opt/Dev-Tools/deploy
docker compose exec postgres psql -U devtools -d devtools -f /opt/Dev-Tools/config/state/schema.sql
```

**Verify Migration**:

```bash
# Check tables exist
docker compose exec postgres psql -U devtools -d devtools -c "\dt chat_*"

# Expected output:
#              List of relations
# Schema |     Name      | Type  |  Owner
#--------+---------------+-------+----------
# public | chat_messages | table | devtools
# public | chat_sessions | table | devtools
```

### Step 2: Rebuild & Restart Orchestrator

```bash
ssh root@45.55.173.72
cd /opt/Dev-Tools/deploy

# Pull latest code
git pull origin main

# Rebuild orchestrator with new dependencies
docker compose build orchestrator

# Restart orchestrator
docker compose restart orchestrator

# Wait for startup
sleep 5

# Check health
curl http://localhost:8001/health | jq .
```

**Health Check Verification**:

```json
{
  "status": "ok",
  "service": "orchestrator",
  "chat": {
    "enabled": true,
    "endpoint": "/chat",
    "features": [
      "intent_recognition",
      "multi_turn",
      "task_submission",
      "status_query",
      "approval_decision"
    ]
  }
}
```

### Step 3: Run Test Script Locally (Against Remote)

**Option A: Test Against Remote Droplet**

```powershell
# From local machine
cd D:\INFRA\Dev-Tools\Dev-Tools

# Update test script to use remote URL (already defaults to localhost:8001)
# Edit support/scripts/test-chat-endpoint.py line 14:
# base_url = "http://45.55.173.72:8001"

# Run tests
python support/scripts/test-chat-endpoint.py
```

**Option B: Test Locally (if orchestrator running locally)**

```powershell
cd D:\INFRA\Dev-Tools\Dev-Tools

# Ensure orchestrator is running on localhost:8001
docker compose -f deploy/docker-compose.yml up -d orchestrator

# Run tests
python support/scripts/test-chat-endpoint.py
```

### Step 4: Verify Results

**Expected Output**:

```
============================================================
Phase 5 Chat Endpoint Test
============================================================

[Test 1] Health check...
✓ Service: orchestrator
✓ Chat enabled: True

[Test 2] Task submission - 'Add error handling to login endpoint'
✓ Intent: task_submission
✓ Confidence: 0.85
✓ Session: session-abc123
✓ Response: ✓ Task created: task-12345...
✓ Task created: task-12345

[Test 3] Clarification - 'feature-dev'
✓ Intent: clarification
✓ Response: ✓ Task created: task-67890...
✓ Task created: task-67890

[Test 4] Status query - 'What's the status of task-123?'
✓ Intent: status_query
✓ Response: Task task-123 not found. It may have been completed or doesn't exist...

[Test 5] General query - 'What can you do?'
✓ Intent: general_query
✓ Suggestions: ['Create a task', 'Check task status', 'Approve a request']
✓ Response: I can help you with:

- **Creating tasks**: "Add error handling to login endpoint"
- **Checking sta...

============================================================
✅ All tests completed!
============================================================
```

---

## Validation Checklist

After running tests, verify:

- [ ] Health check shows `"chat": {"enabled": true}`
- [ ] Intent recognition returns confidence scores 0.5-1.0
- [ ] Session IDs are generated and persisted
- [ ] Multi-turn conversations maintain context (same session_id)
- [ ] Task submissions create tasks via `/orchestrate`
- [ ] Status queries return task information
- [ ] Database has records in `chat_sessions` and `chat_messages` tables

**Database Verification**:

```bash
# Check session records
docker compose exec postgres psql -U devtools -d devtools -c "SELECT session_id, user_id, created_at FROM chat_sessions LIMIT 5;"

# Check message records
docker compose exec postgres psql -U devtools -d devtools -c "SELECT session_id, role, substring(content, 1, 50) as content FROM chat_messages ORDER BY created_at DESC LIMIT 10;"
```

---

## If Tests Pass → Move to Day 3-4

Once chat endpoint is verified working:

1. **Day 3**: Build `LinearWorkspaceClient` and `LinearProjectClient`

   - File: `shared/lib/linear_workspace_client.py`
   - File: `shared/lib/linear_project_client.py`
   - File: `shared/lib/linear_client_factory.py`

2. **Day 4**: Build notifiers (Linear + Email)

   - File: `shared/lib/notifiers/linear_workspace_notifier.py`
   - File: `shared/lib/notifiers/linear_project_notifier.py`
   - File: `shared/lib/notifiers/email_notifier.py`
   - File: `shared/lib/event_bus.py`

3. **Day 5**: Wire everything together with event bus

   - Update orchestrator to use client factory
   - Create `config/hitl/notification-config.yaml`
   - Create `config/linear/project-registry.yaml`

4. **Day 6**: End-to-end integration tests
   - Test approval flow with workspace hub
   - Test multi-project isolation
   - Test email fallback

---

## If Tests Fail → Debug Immediately

### Common Issues & Solutions

#### 1. Database Connection Errors

```
Error: could not connect to PostgreSQL
```

**Solution**:

```bash
# Check postgres is running
docker compose ps postgres

# Check connection string in .env
grep DB_ config/env/.env

# Test connection manually
docker compose exec postgres psql -U devtools -d devtools -c "SELECT version();"
```

#### 2. Missing Database Tables

```
Error: relation "chat_sessions" does not exist
```

**Solution**:

```bash
# Run migrations
docker compose exec postgres psql -U devtools -d devtools -f /opt/Dev-Tools/config/state/schema.sql

# Verify tables created
docker compose exec postgres psql -U devtools -d devtools -c "\dt"
```

#### 3. Gradient API Errors

```
Error: Gradient API key not configured
```

**Solution**:

```bash
# Check API key in .env
grep GRADIENT config/env/.env

# Should see:
# GRADIENT_API_KEY=dop_v1_...
# GRADIENT_MODEL=llama3-8b-instruct

# If missing, add and restart:
docker compose restart orchestrator
```

#### 4. Import Errors

```
ModuleNotFoundError: No module named 'lib.intent_recognizer'
```

**Solution**:

```bash
# Rebuild orchestrator with new dependencies
docker compose build orchestrator
docker compose up -d orchestrator

# Check logs
docker compose logs -f orchestrator
```

#### 5. Session Not Persisting

```
Chat works but messages not saved across requests
```

**Solution**:

```bash
# Check session_manager database pool initialization
docker compose logs orchestrator | grep "database pool"

# Verify PostgreSQL credentials
docker compose exec orchestrator env | grep DB_
```

#### 6. Intent Recognition Falls Back to Keywords

```
All intents return confidence 0.5-0.8 (keyword fallback)
```

**Solution**:

```bash
# Check Gradient client initialization
docker compose logs orchestrator | grep -i gradient

# Test Gradient API manually
curl -X POST https://inference.do-ai.run/v1/chat/completions \
  -H "Authorization: Bearer $GRADIENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3-8b-instruct", "messages": [{"role": "user", "content": "Hello"}]}'
```

---

## Manual Testing (Optional)

Test chat endpoint with `curl`:

```bash
# Task submission
curl -X POST http://45.55.173.72:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Add error handling to the login endpoint",
    "user_id": "test-user"
  }' | jq .

# Status query
curl -X POST http://45.55.173.72:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the status of task-123?",
    "user_id": "test-user"
  }' | jq .

# General query
curl -X POST http://45.55.173.72:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What can you do?",
    "user_id": "test-user"
  }' | jq .
```

---

## Performance Benchmarks

Expected response times (with Gradient AI):

- Health check: <100ms
- Intent recognition: 200-500ms (LLM call)
- Task submission: 1-3s (includes /orchestrate)
- Status query: <200ms (database lookup)
- General query: <100ms (no LLM needed)

If response times exceed these, investigate:

1. Gradient API latency (check LangSmith traces)
2. Database connection pool exhaustion
3. Network latency to droplet

---

## Next Steps After Testing

1. **Document Results**: Update this file with actual test results
2. **Commit Test Data**: Save sample sessions for regression testing
3. **Create Baseline Metrics**: Export Prometheus metrics for comparison
4. **Move to Day 3**: Begin Linear client factory implementation

**Test Completion Signature**:

```
Date: _______________
Tester: _______________
Result: [ ] PASS  [ ] FAIL
Notes: _____________________________________
```
