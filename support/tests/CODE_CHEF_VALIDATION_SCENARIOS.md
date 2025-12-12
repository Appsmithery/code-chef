# Code-Chef Validation Scenarios

**Version**: 1.0.0  
**Last Updated**: December 12, 2025  
**Purpose**: Comprehensive end-to-end validation scenarios for code-chef system

---

## Overview

This document provides **7 realistic validation scenarios** covering all major subsystems:

- Multi-agent orchestration
- HITL approval workflows
- ModelOps training/evaluation/deployment
- A/B testing infrastructure
- Security workflows
- MCP server development
- Regression detection

Each scenario includes:

- **Objective** - What the scenario validates
- **Agents Involved** - Which agents participate
- **Services Used** - Required services and APIs
- **Expected Behavior** - Step-by-step workflow
- **Validation Checklist** - Items to verify
- **LangSmith Validation** - Tracing checks
- **Success Criteria** - Definition of success
- **Common Issues** - Troubleshooting tips

---

## Table of Contents

1. [Scenario 1: Add JWT Authentication to Express API](#scenario-1-add-jwt-authentication-to-express-api)
2. [Scenario 2: Deploy Production Infrastructure Change](#scenario-2-deploy-production-infrastructure-change)
3. [Scenario 3: Train & Deploy New Feature Dev Model](#scenario-3-train--deploy-new-feature-dev-model)
4. [Scenario 4: A/B Test Model Improvement](#scenario-4-ab-test-model-improvement)
5. [Scenario 5: Fix Security Vulnerability in Production](#scenario-5-fix-security-vulnerability-in-production)
6. [Scenario 6: Create New MCP Server for IB-Agent](#scenario-6-create-new-mcp-server-for-ib-agent)
7. [Scenario 7: Regression Detection Across Versions](#scenario-7-regression-detection-across-versions)
8. [Manual LangSmith Validation](#manual-langsmith-validation)
9. [Quick Validation Commands](#quick-validation-commands)
10. [Expected Outcomes Table](#expected-outcomes-table)

---

## Scenario 1: Add JWT Authentication to Express API

**Objective**: Validate multi-agent handoff, Linear issue tracking, code generation

**Agents Involved**:

- Supervisor (routing)
- Feature Dev (implementation)
- Code Review (security audit)
- Documentation (API docs update)

**Services Used**:

- Linear (issue tracking)
- GitHub (PR creation)
- LangSmith (tracing to code-chef-production)

### Expected Behavior

1. User request: "@chef Add JWT authentication middleware to my Express API"
2. Supervisor routes to Feature Dev agent
3. Feature Dev generates middleware code + tests
4. Feature Dev hands off to Code Review for security audit
5. Code Review validates JWT implementation, checks for vulnerabilities
6. Code Review hands off to Documentation for API docs
7. Documentation updates OpenAPI spec and README
8. Linear issue created with 3 sub-tasks (implementation, review, docs)
9. GitHub PR created with all changes

### Validation Checklist

```markdown
- [ ] Linear parent issue created (e.g., CHEF-300)
- [ ] 3 Linear sub-issues created (implementation, review, docs)
- [ ] GitHub PR created with reference to Linear issue
- [ ] JWT middleware code generated in `middleware/auth.js`
- [ ] Unit tests generated in `tests/middleware/auth.test.js`
- [ ] Security audit performed (OWASP checks)
- [ ] API documentation updated (OpenAPI + README)
- [ ] LangSmith traces visible in code-chef-production
- [ ] Traces show agent handoffs (feature_dev → code_review → documentation)
- [ ] All traces have required metadata (experiment_group, environment, module)
```

### LangSmith Validation

- **Project**: `code-chef-production`
- **Filter**: `task_id:` (from workflow)
- **Verify**: 4 traces (supervisor routing + 3 agent executions)
- **Metadata**: `environment="production"`, `module=` (agent name)

### Success Criteria

- All 4 agents executed successfully
- Linear issue + sub-issues created
- GitHub PR created with correct content
- No approval required (medium risk)
- Duration: 10-15 minutes

### Common Issues

- **Linear API rate limiting** - Retry with backoff
- **GitHub PR creation failure** - Check token permissions
- **Agent timeout** - Increase timeout for code review

---

## Scenario 2: Deploy Production Infrastructure Change

**Objective**: Validate HITL Phase 1-4, risk assessment, webhook resume, Prometheus metrics

**Agents Involved**:

- Infrastructure (Terraform changes)
- Approval Node (HITL gate)

**Services Used**:

- Linear (approval request)
- GitHub (PR context)
- Prometheus (metrics emission)
- Grafana (dashboard visualization)
- LangSmith (tracing)

### Expected Behavior

1. User request: "@chef Update production docker-compose to add Redis cache"
2. Infrastructure agent proposes changes
3. Risk assessment: **CRITICAL** (production environment + infrastructure change)
4. Workflow pauses, approval node creates Linear issue
5. Linear issue includes:
   - Operation description
   - Risk level emoji (🔴 CRITICAL)
   - PR context (if PR exists)
   - Approval required from tech lead
6. Prometheus metrics emitted:
   - `hitl_approval_requests_created_total{agent="infrastructure",risk_level="critical"}`
   - `hitl_approval_backlog_total{risk_level="critical"}` incremented
7. Human approver reviews in Linear, approves (👍 emoji or state change)
8. Linear webhook fires → orchestrator `/resume` endpoint
9. Workflow resumes, Infrastructure agent applies changes
10. Prometheus metrics emitted:

- `hitl_approval_requests_resolved_total{status="approved"}`
- `hitl_approval_latency_seconds` histogram observation
- `hitl_approval_backlog_total{risk_level="critical"}` decremented

### Validation Checklist

```markdown
- [ ] Infrastructure agent detects production environment
- [ ] Risk assessment returns "critical" level
- [ ] Workflow pauses (status: "awaiting_approval")
- [ ] Linear issue created with correct template
- [ ] Linear issue includes 🔴 CRITICAL emoji
- [ ] Linear issue includes PR link (if PR context provided)
- [ ] Approval request saved to PostgreSQL
- [ ] Prometheus metric `hitl_approval_requests_created_total` incremented
- [ ] Prometheus gauge `hitl_approval_backlog_total` shows +1
- [ ] Grafana dashboard "Approval Queue Overview" shows pending approval
- [ ] Grafana dashboard "Critical Risk Backlog" shows 1
- [ ] Human approval granted in Linear UI
- [ ] Linear webhook received by orchestrator
- [ ] Workflow resumed successfully
- [ ] Infrastructure changes applied
- [ ] Prometheus metric `hitl_approval_requests_resolved_total` incremented
- [ ] Prometheus histogram `hitl_approval_latency_seconds` recorded
- [ ] Grafana dashboard updated (backlog decremented)
```

### LangSmith Validation

- **Project**: `code-chef-production`
- **Traces**: infrastructure_node, approval_node, infrastructure_node (resumed)
- **Metadata includes**:
  - `environment="production"`
  - `module="infrastructure"`
  - `risk_level="critical"`
  - `requires_approval=true`

### Success Criteria

- Risk assessment accurate (critical for production)
- Linear issue created with correct template
- Workflow paused until approval
- Webhook successfully resumed workflow
- All Prometheus metrics emitted correctly
- Grafana dashboard reflects changes in real-time
- Duration: 5-10 min + approval wait time

### Common Issues

- **Webhook delivery failure** - Check Linear webhook config
- **Approval timeout** - Default 30 min, configure in approval-policies.yaml
- **Prometheus metrics not appearing** - Check /metrics endpoint
- **Grafana dashboard not updating** - Check datasource connection

---

## Scenario 3: Train & Deploy New Feature Dev Model

**Objective**: Validate ModelOps full cycle, LangSmith project routing, cost tracking

**Agents Involved**:

- Infrastructure (ModelOps coordinator)

**Services Used**:

- LangSmith (training data export, evaluation)
- HuggingFace Space (AutoTrain)
- Prometheus (cost tracking)

### Expected Behavior

1. User request (via VS Code): `codechef.modelops.train`
2. Select agent: `feature_dev`
3. Select training mode: `production` (60 min, $3.50)
4. Infrastructure agent (ModelOps coordinator):
   a. Export training data from LangSmith project `code-chef-production`
   b. Submit training job to HuggingFace AutoTrain Space
   c. Monitor job progress (0% → 100%)
   d. Download fine-tuned model when complete
5. ModelOps evaluator:
   a. Run evaluation against baseline (v1.0.0)
   b. Run evaluation against candidate (v2.0.0)
   c. Compare metrics (accuracy, completeness, efficiency, latency, integration)
   d. Generate recommendation (deploy if >15% improvement)
6. If recommendation = "deploy":
   a. Backup current `config/agents/models.yaml`
   b. Update config with new model
   c. Restart orchestrator service
   d. Verify health check

### Validation Checklist

```markdown
- [ ] Training data exported from LangSmith (>100 examples)
- [ ] Training job submitted to AutoTrain Space
- [ ] Job ID returned and tracked
- [ ] Job status polling works (every 30s)
- [ ] TensorBoard link accessible
- [ ] Training completes successfully (status: "completed")
- [ ] Model artifact downloaded from HuggingFace
- [ ] Model registered in `config/models/registry.json`
- [ ] Evaluation runs against baseline
- [ ] Evaluation runs against candidate
- [ ] Comparison report generated
- [ ] Recommendation logic works (>15% = deploy)
- [ ] Config backup created
- [ ] models.yaml updated with new model
- [ ] Orchestrator restarted
- [ ] Health check passes
- [ ] LangSmith traces in code-chef-training project
- [ ] Cost tracked in Prometheus
```

### LangSmith Validation

- **Project**: `code-chef-training` (for training traces)
- **Project**: `code-chef-evaluation` (for evaluation traces)
- **Verify metadata**:
  - `environment="training"` for training operations
  - `module="training"` for AutoTrain job
  - `module="evaluation"` for evaluation runs
  - `model_version` reflects candidate model

### Success Criteria

- Training job completes without errors
- Evaluation shows measurable improvement (>5%)
- Model deployed if recommendation = "deploy"
- All LangSmith traces in correct projects
- Cost accurately tracked ($3.50 for production training)
- Duration: 60-90 min

### Common Issues

- **LangSmith dataset empty** - Need production usage data
- **AutoTrain job failure** - Check GPU availability
- **HuggingFace token expired** - Refresh token
- **Model deployment fails** - Check models.yaml syntax

---

## Scenario 4: A/B Test Model Improvement

**Objective**: Validate A/B testing infrastructure, task_id correlation, experiment_id usage

**Agents Involved**: N/A (uses baseline_runner.py script)

**Services Used**:

- LangSmith (trace separation by experiment_group)
- PostgreSQL (evaluation_results table)
- Comparison engine

### Expected Behavior

1. Create task file with 10 code generation tasks:

   ```json
   {
     "experiment_name": "Q1 2025 Feature Dev Improvement",
     "experiment_id": "exp-2025-01-001",
     "tasks": [
       {"task_id": "task-001", "prompt": "Create JWT middleware"},
       {"task_id": "task-002", "prompt": "Implement pagination"},
       ...
     ]
   }
   ```

2. Run baseline evaluation:

   ```powershell
   $env:EXPERIMENT_GROUP="baseline"
   $env:MODEL_VERSION="phi-3-mini-4k-instruct"  # Base model
   python support/scripts/evaluation/baseline_runner.py --mode baseline --tasks tasks.json
   ```

3. Run code-chef evaluation:

   ```powershell
   $env:EXPERIMENT_GROUP="code-chef"
   $env:MODEL_VERSION="codechef-feature-dev-v2"  # Fine-tuned
   python support/scripts/evaluation/baseline_runner.py --mode code-chef --tasks tasks.json
   ```

4. Compare results:
   ```powershell
   python support/scripts/evaluation/query_evaluation_results.py --compare --experiment exp-2025-01-001
   ```

### Validation Checklist

```markdown
- [ ] Task file created with unique task_ids
- [ ] Baseline evaluation runs successfully
- [ ] Code-chef evaluation runs successfully
- [ ] All tasks use same task_id for correlation
- [ ] Results stored in PostgreSQL evaluation_results table
- [ ] LangSmith traces separated by experiment_group
- [ ] Baseline traces in code-chef-experiments (group=baseline)
- [ ] Code-chef traces in code-chef-experiments (group=code-chef)
- [ ] Comparison report generated
- [ ] Statistical significance calculated
- [ ] Improvement percentages accurate
- [ ] Recommendation provided (deploy/needs_review/reject)
```

### LangSmith Validation

- **Project**: `code-chef-experiments`
- **Filter**: `experiment_id:"exp-2025-01-001"`
- **Verify**:
  - 10 baseline traces with `experiment_group="baseline"`
  - 10 code-chef traces with `experiment_group="code-chef"`
  - Each pair has matching `task_id`
- **Analytics**: Group by `experiment_group`
  - Compare token usage (baseline vs code-chef)
  - Compare costs (baseline vs code-chef)

### Success Criteria

- All 20 evaluations complete (10 baseline + 10 code-chef)
- Task correlation works (same task_id)
- Comparison report shows accurate improvement percentages
- Statistical significance > 95% confidence
- Recommendation aligns with data (>15% = deploy)
- Duration: 20-30 min

### Common Issues

- **Task_id mismatch** - Baseline and code-chef runs must use same IDs
- **Experiment_id not set** - Traces don't correlate
- **Database connection issues** - Check TEST_DATABASE_URL
- **Comparison engine fails** - Missing data in evaluation_results

---

## Scenario 5: Fix Security Vulnerability in Production

**Objective**: Validate security workflow, HITL for prod deploy, multi-agent coordination

**Agents Involved**:

- Code Review (detection)
- Feature Dev (fix implementation)
- CI/CD (test automation)
- Infrastructure (deployment with approval)

**Services Used**:

- Linear (security issue + approval)
- GitHub (PR with security label)
- LangSmith (tracing)

### Expected Behavior

1. Code Review agent scans codebase (scheduled or on-demand)
2. Detects OWASP Top 10 vulnerability (e.g., SQL injection)
3. Creates Linear issue with "security" label + 🔴 HIGH emoji
4. Feature Dev agent assigned to implement fix
5. Feature Dev generates secure code + tests
6. CI/CD agent runs security tests (SAST, dependency scan)
7. If tests pass, Infrastructure agent prepares deployment
8. Risk assessment: **HIGH** (production + security fix)
9. HITL approval required
10. After approval, hotfix deployed

### Validation Checklist

```markdown
- [ ] Code Review detects vulnerability
- [ ] Linear issue created with "security" label
- [ ] Issue includes vulnerability details (OWASP category, severity, location)
- [ ] Feature Dev implements fix
- [ ] Fix includes unit tests
- [ ] CI/CD runs security tests
- [ ] Tests pass (vulnerability remediated)
- [ ] Infrastructure prepares deployment
- [ ] Risk assessment = HIGH
- [ ] HITL approval request created
- [ ] Linear approval issue includes security context
- [ ] Approval granted
- [ ] Hotfix deployed to production
- [ ] Post-deployment verification (security test re-run)
```

### LangSmith Validation

- **Project**: `code-chef-production`
- **Traces**: code_review → feature_dev → cicd → infrastructure → approval → infrastructure
- **Verify metadata includes**:
  - `risk_level="high"`
  - `security_issue=true` (custom metadata)

### Success Criteria

- Vulnerability detected accurately
- Fix implemented correctly (no false positives)
- Security tests validate remediation
- HITL approval required and granted
- Deployment successful
- Duration: 15-20 min + approval

### Common Issues

- **False positive vulnerability detection** - Tune detection rules
- **Security tests timeout** - Increase test timeout
- **Approval delay** - Notify security team

---

## Scenario 6: Create New MCP Server for IB-Agent

**Objective**: Validate multi-agent coordination, RAG context usage, progressive tool loading

**Agents Involved**:

- Feature Dev (MCP server implementation)
- Infrastructure (Docker Compose integration)
- Documentation (integration guide)
- CI/CD (GitHub Actions workflow)

**Services Used**:

- RAG Context Service (library search)
- Linear (project tracking)
- GitHub (PR)
- LangSmith (tracing)

### Expected Behavior

1. User request: "@chef Create MCP server for SEC Edgar filings integration"
2. Supervisor routes to Feature Dev
3. Feature Dev queries RAG for MCP server examples
4. Feature Dev generates:
   - MCP server structure (`mcp_servers/edgar/`)
   - Transport layer (stdio/SSE)
   - Tool definitions (search_filings, get_10k, etc.)
   - Error handling
5. Infrastructure agent:
   - Adds to `docker-compose.yml`
   - Creates health check
   - Configures in `config/mcp-agent-tool-mapping.yaml`
6. Documentation agent:
   - Writes integration guide
   - API documentation
   - Usage examples
7. CI/CD agent:
   - Creates GitHub Actions workflow
   - Adds to test suite

### Validation Checklist

```markdown
- [ ] RAG context search returns relevant MCP examples
- [ ] MCP server code generated (server.py, tools/, tests/)
- [ ] Docker Compose updated
- [ ] Health endpoint added
- [ ] MCP tool mapping configured
- [ ] Integration guide created
- [ ] API docs generated
- [ ] GitHub Actions workflow created
- [ ] Linear issue tracks progress
- [ ] GitHub PR created with all changes
- [ ] Tool loading strategy escalates: MINIMAL → PROGRESSIVE → FULL
```

### LangSmith Validation

- **Project**: `code-chef-production`
- **Traces show**:
  - RAG query in feature_dev trace
  - Tool loading strategy progression
  - Multi-agent handoffs

### Success Criteria

- Complete MCP server scaffolded
- Docker integration working
- Documentation comprehensive
- CI/CD pipeline configured
- Progressive tool loading demonstrated
- Duration: 20-25 min

### Common Issues

- **RAG context not found** - Library not indexed
- **Docker Compose syntax error** - Validation
- **Tool loading strategy not escalating** - Check keywords

---

## Scenario 7: Regression Detection Across Versions

**Objective**: Validate longitudinal tracking, regression detection, version comparison

**Agents Involved**: N/A (uses longitudinal_tracker)

**Services Used**:

- PostgreSQL (evaluation_results history)
- LangSmith (code-chef-evaluation project)
- Comparison engine

### Expected Behavior

1. Run evaluation suite on extension v1.5.0:

   ```powershell
   $env:EXTENSION_VERSION="1.5.0"
   pytest support/tests/evaluation/
   ```

2. Results stored in database:

   - Agent: feature_dev
   - Version: 1.5.0
   - Scores: {accuracy: 0.90, latency: 1.8s}

3. Deploy extension v1.6.0 (with unintended regression)

4. Run evaluation suite on extension v1.6.0:

   ```powershell
   $env:EXTENSION_VERSION="1.6.0"
   pytest support/tests/evaluation/
   ```

5. Results stored:

   - Agent: feature_dev
   - Version: 1.6.0
   - Scores: {accuracy: 0.75, latency: 1.7s} # Accuracy dropped!

6. Longitudinal tracker detects regression:

   ```python
   trend = await tracker.get_metric_trend(agent="feature_dev", metric="accuracy", limit=2)
   # Returns: [(v1.5.0, 0.90), (v1.6.0, 0.75)]
   # Regression: -16.7%
   ```

7. Alert generated: "Accuracy regression detected: v1.5.0 → v1.6.0 (-16.7%)"

8. Recommendation: Rollback to v1.5.0

### Validation Checklist

```markdown
- [ ] Evaluation suite runs on v1.5.0
- [ ] Results stored in evaluation_results table
- [ ] Extension updated to v1.6.0
- [ ] Evaluation suite runs on v1.6.0
- [ ] Results stored with new version
- [ ] Longitudinal tracker queries history
- [ ] Regression detected (accuracy drop)
- [ ] Alert generated
- [ ] Rollback recommendation provided
- [ ] Historical best version identified (v1.5.0)
```

### LangSmith Validation

- **Project**: `code-chef-evaluation`
- **Filter**: `agent:"feature_dev"`
- **Group by**: `extension_version`
- **Compare**: Token costs and latencies across versions

### Success Criteria

- Regression detected accurately
- Alert generated automatically
- Rollback to previous version successful
- Historical data preserved
- Duration: 10-15 min

### Common Issues

- **Insufficient historical data** - Need >2 versions
- **Regression threshold too sensitive** - Tune in config
- **Database query performance** - Add indexes

---

## Manual LangSmith Validation

### Production Traces Validation

**Navigate to**: https://smith.langchain.com → Select project `code-chef-production`

**Steps**:

1. Find recent trace from workflow execution
2. Click trace → Metadata tab
3. **Verify presence** of all 7 fields:

   ```json
   {
     "experiment_group": "code-chef",
     "environment": "production",
     "module": "feature_dev",
     "extension_version": "1.2.3",
     "model_version": "qwen-2.5-coder-32b",
     "config_hash": "sha256:a1b2c3d4...",
     "task_id": "task-uuid-here"
   }
   ```

4. **Verify values**:

   - ✅ `experiment_group` is "code-chef" (not "baseline")
   - ✅ `environment` is "production"
   - ✅ `module` matches agent that executed
   - ✅ `extension_version` is valid semver (X.Y.Z)
   - ✅ `model_version` matches models.yaml
   - ✅ `config_hash` is 64-char hex string
   - ✅ `task_id` is UUID format (if present)

5. Click "Analytics" tab → Group by `module`
6. **Verify** agent distribution makes sense

### A/B Testing Traces Validation

**Navigate to**: https://smith.langchain.com → Select project `code-chef-experiments`

**Steps**:

1. Filter by: `experiment_id:"exp-2025-01-001"`
2. **Verify separation**:
   - Baseline group: `experiment_group="baseline"`
   - Code-chef group: `experiment_group="code-chef"`
3. Sort by `task_id`
4. **Verify correlation**:
   - Each baseline task has matching code-chef task
   - Same `task_id` for paired tasks
5. Click "Analytics" tab → Group by `experiment_group`
6. **Verify cost attribution**:
   - Baseline costs separate from code-chef
   - Token counts accurate per group
   - Cost per task calculable

### Training Traces Validation

**Navigate to**: https://smith.langchain.com → Select project `code-chef-training`

**Steps**:

1. Filter by: `module:"training"`
2. **Verify traces present**:
   - Training job submission
   - Dataset export
   - Job monitoring (multiple traces)
3. Click trace → Metadata
4. **Verify**:
   - `environment="training"`
   - `module="training"`
   - `model_version` reflects training target

### Evaluation Traces Validation

**Navigate to**: https://smith.langchain.com → Select project `code-chef-evaluation`

**Steps**:

1. Filter by: `module:"evaluation"`
2. **Verify traces present**:
   - Evaluation runs
   - Comparison engine executions
3. **Verify metadata**:
   - `environment="evaluation"`
   - `module="evaluation"`

---

## Quick Validation Commands

### Service Health Checks

```powershell
# Check all services healthy
curl http://localhost:8001/health  # Orchestrator
curl http://localhost:8007/health  # RAG Context
curl http://localhost:8008/health  # State Persist
curl http://localhost:9090/-/healthy  # Prometheus
curl http://localhost:3000/api/health  # Grafana
```

### Prometheus Metrics

```powershell
# Check HITL approval metrics
curl http://localhost:8001/metrics | Select-String "hitl_approval"

# Check LLM token metrics
curl http://localhost:8001/metrics | Select-String "llm_tokens"

# Check LLM cost metrics
curl http://localhost:8001/metrics | Select-String "llm_cost"

# Check approval backlog gauge
curl http://localhost:8001/metrics | Select-String "hitl_approval_backlog_total"
```

### Database Queries

```powershell
# Check approval requests
psql -h localhost -U postgres -d devtools -c "SELECT COUNT(*) FROM approval_requests;"

psql -h localhost -U postgres -d devtools -c "SELECT * FROM approval_requests WHERE status='pending' ORDER BY created_at DESC LIMIT 5;"

# Check evaluation results
psql -h localhost -U postgres -d devtools -c "SELECT COUNT(*) FROM evaluation_results;"

psql -h localhost -U postgres -d devtools -c "SELECT agent_name, AVG((scores->>'accuracy')::float) as avg_accuracy FROM evaluation_results GROUP BY agent_name;"

# Check for regressions
psql -h localhost -U postgres -d devtools -c "SELECT extension_version, AVG((scores->>'accuracy')::float) as accuracy FROM evaluation_results WHERE agent_name='feature_dev' GROUP BY extension_version ORDER BY extension_version DESC;"
```

### API Connectivity

```powershell
# Check Linear API
curl -H "Authorization: Bearer $env:LINEAR_API_KEY" -H "Content-Type: application/json" -d '{"query": "{ viewer { id name } }"}' https://api.linear.app/graphql

# Check GitHub API
curl -H "Authorization: token $env:GITHUB_TOKEN" https://api.github.com/user

# Check HuggingFace Space
curl https://alextorelli-code-chef-modelops-trainer.hf.space/health

# Check LangSmith API
curl -H "x-api-key: $env:LANGCHAIN_API_KEY" https://api.smith.langchain.com/health

# Check project exists
curl -H "x-api-key: $env:LANGCHAIN_API_KEY" "https://api.smith.langchain.com/projects?name=code-chef-production"
```

---

## Expected Outcomes Table

| Scenario     | Linear Issues         | GitHub PRs | Approval Required | LangSmith Project     | Agents | Duration            |
| ------------ | --------------------- | ---------- | ----------------- | --------------------- | ------ | ------------------- |
| JWT Auth     | 1 parent + 3 subtasks | 1          | No                | code-chef-production  | 3      | 10-15 min           |
| Prod Deploy  | 1 approval            | 1          | Yes (critical)    | code-chef-production  | 2      | 5-10 min + approval |
| Train Model  | 0                     | 0          | No                | code-chef-training    | 1      | 60-90 min           |
| A/B Test     | 0                     | 0          | No                | code-chef-experiments | 1      | 20-30 min           |
| Security Fix | 2                     | 1          | Yes (prod hotfix) | code-chef-production  | 4      | 15-20 min           |
| New MCP      | 1                     | 1          | No                | code-chef-production  | 4      | 20-25 min           |
| Regression   | 0                     | 0          | No                | code-chef-evaluation  | 1      | 10-15 min           |

---

## Usage Notes

1. **Prerequisites**: All services must be running (orchestrator, RAG, state-persist, Linear, GitHub, LangSmith)
2. **Order**: Execute scenarios 1, 2, 5, 6 first (quick validation), then 3, 4, 7 (longer duration)
3. **Manual Steps**: Scenarios 2 and 5 require human approval in Linear
4. **LangSmith**: Manual validation must be done via UI (automated testing not feasible)
5. **Data Requirements**: Scenario 3 requires production usage data in LangSmith
6. **Environment Variables**: Set all required env vars before running scenarios

---

**Questions?** File an issue in [Linear](https://linear.app/dev-ops/project/codechef-78b3b839d36b) with label `validation`.
