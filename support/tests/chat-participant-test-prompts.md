# Code-Chef Chat Participant Test Prompts

⚠️ **IMPORTANT**: These test prompts use hypothetical external projects to avoid modifying the code-chef repository itself.

## Setup Instructions

Create a test workspace with sample files:

```bash
# Create test workspace
mkdir ~/code-chef-test-workspace
cd ~/code-chef-test-workspace

# Sample e-commerce project structure
mkdir -p backend/api backend/models frontend/components tests
touch backend/api/auth.js backend/api/orders.js backend/models/user.js
touch frontend/components/LoginForm.tsx frontend/components/ProductCard.tsx
touch tests/auth.test.js README.md

# Add sample content
echo "// Authentication API endpoints" > backend/api/auth.js
echo "// Order management endpoints" > backend/api/orders.js
echo "// User model definition" > backend/models/user.js
```

Open this workspace in VS Code before testing prompts.

---

## 1. Task Submission Tests

### Simple Feature Request
```
@code-chef implement a shopping cart feature with add/remove items and checkout flow
```
**Expected Trace:**
- Intent: task_submission
- Workflow: feature_development
- Agent: feature_dev
- Tool loading: PROGRESSIVE (30-60 tools)

### Feature with File Context
```
@code-chef #file:backend/api/auth.js add rate limiting to prevent brute force login attempts
```
**Expected Trace:**
- File reference extraction
- RAG query with file embeddings
- Context7 library lookup (express-rate-limit)
- High confidence intent classification

### Infrastructure Task
```
@code-chef deploy our Node.js e-commerce API to AWS ECS with auto-scaling
```
**Expected Trace:**
- Workflow: deployment
- Agent: infrastructure
- IaC tools loaded (terraform, AWS CDK)
- Risk: HIGH → HITL approval required

---

## 2. Status Query Tests

### Check Last Task
```
@code-chef what's the status of my last task?
```
**Expected Trace:**
- Intent: status_query
- Session lookup
- Minimal LLM usage (database query only)

### Specific Task ID
```
@code-chef check status of task-abc123
```
**Expected Trace:**
- Intent: status_query
- Direct task lookup (no LLM)
- Subtask aggregation

---

## 3. Clarification Tests

### Ambiguous Request
```
@code-chef fix the payment bug
```
**Expected Trace:**
- Intent: clarification_needed
- LLM asks: which payment provider? staging or production?
- No task created

### Follow-up with Context
```
@code-chef use Stripe and only fix staging
```
**Expected Trace:**
- Session history loaded
- Intent refined to task_submission
- Task created with clarified context

---

## 4. Approval Tests

### High-Risk Database Operation
```
@code-chef drop all staging database tables and recreate from migrations
```
**Expected Trace:**
- Risk assessment: CRITICAL
- Approval request created
- Linear issue generated
- Workflow interrupted (no execution)

### Production Deployment
```
@code-chef deploy version 2.0.0 to production with blue-green deployment
```
**Expected Trace:**
- Risk: HIGH
- HITL approval required
- Guardrail checks executed
- Waits for manual approval

---

## 5. Multi-Agent Workflow Tests

### End-to-End Feature
```
@code-chef create a blog post editor with rich text, image uploads, auto-save, unit tests, and API docs
```
**Expected Trace:**
- Agents: feature_dev → cicd → documentation
- Multiple subtasks created
- State checkpointing between agents
- Parallel execution (if configured)

### Code Review
```
@code-chef #file:backend/api/auth.js review this authentication code for security vulnerabilities
```
**Expected Trace:**
- Workflow: code_review
- Agent: code_review
- Security tools loaded (eslint, semgrep)
- OWASP checks performed

---

## 6. Context-Heavy Tests

### Multiple File References
```
@code-chef #file:backend/api/auth.js #file:backend/models/user.js implement OAuth2 login with Google and GitHub
```
**Expected Trace:**
- Multiple file embeddings
- RAG retrieval from both files
- Context window optimization
- Progressive disclosure active

### Library-Specific Implementation
```
@code-chef #file:backend/api/orders.js integrate Stripe webhooks for payment processing
```
**Expected Trace:**
- Context7 library lookup: stripe-node
- RAG retrieval from Stripe docs
- High relevance context injection
- Token savings via context pruning

---

## 7. Streaming Tests

### Long-Running Refactor
```
@code-chef migrate our authentication system from sessions to JWT with refresh tokens
```
**Expected Trace:**
- Streaming response chunks
- Agent progress updates
- Tool call events
- Partial completion markers

### Multi-Service Setup
```
@code-chef create a new payments microservice with Stripe, write tests, set up CI/CD, deploy to staging
```
**Expected Trace:**
- Workflow status events
- Agent handoffs (feature_dev → cicd → infrastructure)
- Subtask progression
- Parallel execution groups

---

## 8. Error Handling Tests

### Nonsense Input
```
@code-chef asdfghjkl qwertyuiop
```
**Expected Trace:**
- Intent: general_query (fallback)
- LLM attempts understanding
- Graceful clarification request
- No errors thrown

### Missing Context
```
@code-chef deploy it now
```
**Expected Trace:**
- Intent: clarification_needed
- LLM asks: deploy what? where?
- No assumptions made

---

## 9. RAG Context Tests

### Documentation Query
```
@code-chef how do I implement rate limiting in Express.js?
```
**Expected Trace:**
- Intent: general_query
- RAG search in documentation
- Context7 library: express, express-rate-limit
- Minimal LLM usage (RAG-powered)

### Framework-Specific Task
```
@code-chef set up React Router v6 with protected routes and authentication
```
**Expected Trace:**
- Context7 lookup: react-router-dom, react
- RAG retrieval from React docs
- Token optimization
- Code examples from knowledge base

---

## 10. Optimization Tests

### Minimal Complexity Task
```
@code-chef create a GET /health endpoint that returns {status: 'ok'}
```
**Expected Trace:**
- Tool loading: MINIMAL (10-30 tools)
- No RAG queries needed
- Fast intent recognition
- Total tokens < 500

### Maximum Complexity Analysis
```
@code-chef analyze our entire e-commerce application and suggest architectural improvements
```
**Expected Trace:**
- Tool loading: FULL (150+ tools)
- Extensive RAG retrieval
- Multiple file embeddings
- Token optimization still active

---

## Real-World Scenarios

### Bug Fix Request
```
@code-chef #file:backend/api/orders.js fix the race condition in concurrent order processing
```

### Feature Enhancement
```
@code-chef add email notifications when orders are shipped, include tracking links
```

### Performance Optimization
```
@code-chef optimize our product search API to handle 10k requests per second
```

### Database Migration
```
@code-chef create a migration to add a 'favorites' table with foreign keys to users and products
```

### Testing Request
```
@code-chef write integration tests for the entire checkout flow including payment processing
```

---

## Testing Methodology

1. **Open Test Workspace** in VS Code (not code-chef repo!)
2. **Open Chat Panel** (Ctrl+Alt+I or Cmd+Opt+I)
3. **Type Prompts** using `@code-chef` prefix
4. **Monitor LangSmith** at https://smith.langchain.com/projects/code-chef-production
5. **Review Traces** for:
   - System prompts (full visibility)
   - Token counts (accurate)
   - Latency metrics (P50/P95/P99)
   - Tool invocations (what was loaded)
   - RAG context quality (relevant docs retrieved)
   - Waterfall visualization (nested calls)
   - Error handling (graceful degradation)

## Expected Trace Metadata

Every trace should include:
```json
{
  "environment": "production",
  "extension_version": "2.0.0",
  "experiment_group": "code-chef",
  "model_version": "qwen-2.5-coder-32b",
  "session_id": "session-uuid",
  "user_id": "vscode-machine-id"
}
```

## Validation Checklist

- [ ] All traces visible in LangSmith (no 403 errors)
- [ ] System prompts fully visible
- [ ] Token counts accurate
- [ ] Waterfall shows nested LLM calls
- [ ] RAG context included in traces
- [ ] Intent recognition logged
- [ ] Tool invocations traced
- [ ] Error handling captured
- [ ] Streaming events visible
- [ ] Session continuity maintained
- [ ] No code-chef repo modifications attempted!

---

## Notes

- Always use a **separate test workspace** - never the code-chef repository
- These prompts generate realistic traces without polluting the codebase
- Monitor token costs in LangSmith metrics dashboard
- Use different project types (e-commerce, blog, SaaS) to test variety
- Check that progressive tool loading adapts to task complexity
