# LangSmith UAT Implementation - Quick Start Guide

**Implementation Date**: January 6, 2026  
**Status**: ✅ Complete - Ready for UAT Phase 1

This guide provides step-by-step instructions for using the LangSmith UAT evaluation system that has been implemented according to the action plan.

---

## 📋 What Was Implemented

### Phase 1: Online Evaluation Setup (Week 1)

✅ **Scripts Created:**

- `create_annotation_queue.py` - Creates UAT review queue in LangSmith
- `setup_trajectory_evaluators.py` - Sets up AgentEvals trajectory matching
- `check_queue_status.py` - Monitors annotation queue health
- Enhanced `auto_annotate_traces.py` with uncertainty sampling
- Enhanced `sync_dataset_from_annotations.py` with queue sync

### Phase 2: Automation Workflows (Week 2)

✅ **Scripts Created:**

- `daily_uat_review.py` - Daily quality check workflow
- `.github/workflows/pre-deploy-evaluation.yml` - Pre-deployment CI/CD check

### Phase 3: UAT-Specific Monitoring (Week 3)

✅ **Tests Created:**

- `test_graph_trajectory.py` - LangGraph routing quality tests
- Expanded `test_property_based.py` - Agent output validation properties

### Existing Tools Verified:

✅ `check_dataset_diversity.py` - Dataset diversity analysis (already exists)  
✅ `detect_regression.py` - Regression detection (already exists)  
✅ `export_training_dataset.py` - Training data export (already exists)

---

## 🚀 Getting Started (Day 1)

### Step 1: Install Dependencies

```bash
# Install required packages
pip install langsmith agentevals openevals

# Verify LangSmith connection
python -c "from langsmith import Client; Client()"
```

### Step 2: Create Annotation Queue

```bash
# Create the UAT review queue in LangSmith
python support/scripts/evaluation/create_annotation_queue.py
```

**Expected Output:**

```
✅ Created annotation queue: <queue-id>
📊 URL: https://smith.langchain.com/annotation-queues/<queue-id>

⚠️  Manual setup required in LangSmith UI:
See "Step 2.5: Set Up Automation Rules" below for detailed instructions
```

### Step 2.5: Set Up Automation Rules to Populate Queue

After creating the annotation queue, you need to configure **automation rules** to automatically route traces to the queue for review.

**Navigation:**
1. Go to LangSmith → **Tracing Projects**
2. Select your project (e.g., `code-chef-production`)
3. Click the **Automations** tab
4. Click **+ New** → **New Automation**

**Create Three Automation Rules:**

#### Rule 1: Low Confidence Traces
- **Name**: "UAT - Low Confidence Review"
- **Filter**: `metadata.intent_confidence < 0.75`
- **Sampling Rate**: `0.2` (20% of matching traces)
- **Action**: Add to annotation queue → `uat-review-queue`
- **Backfill**: Optional - select start date if you want to review historical traces

#### Rule 2: Error Traces
- **Name**: "UAT - Error Review"
- **Filter**: `error IS NOT NULL`
- **Sampling Rate**: `0.2` (20% of error traces)
- **Action**: Add to annotation queue → `uat-review-queue`
- **Backfill**: Optional

#### Rule 3: High Latency Traces
- **Name**: "UAT - Latency Review"
- **Filter**: `latency_ms > 5000`
- **Sampling Rate**: `0.2` (20% of slow traces)
- **Action**: Add to annotation queue → `uat-review-queue`
- **Backfill**: Optional

**Configure Annotation Rubric:**

After setting up automation rules, configure the annotation rubric:
1. Go to **Annotation Queues** → `uat-review-queue`
2. Edit the **Annotation Rubric** section (shown in your screenshots)
3. Add **Instructions** for reviewers:
   ```
   Review traces for:
   - Correctness of agent response
   - Appropriate MCP tool usage
   - Output format quality
   - Error handling
   ```
4. Add **Feedback** keys:
   - `correctness` (Score 0-1): "Is the response correct?"
   - `tool_usage` (Score 0-1): "Are MCP tools used appropriately?"
   - `format_quality` (Score 0-1): "Is the output well-formatted?"
   - `notes` (Text): "Additional observations"

### Step 3: Configure Online Evaluators in LangSmith UI

Navigate to: LangSmith → `code-chef-production` project → **Evaluators** tab

#### Evaluator 1: MCP Tool Awareness (Reference-Free)

- **Type**: LLM-as-Judge
- **Model**: `openrouter/openai/o3-mini`
- **Trigger**: Run-level
- **Sampling**: 20%

**Prompt**:

```
You are evaluating an AI coding agent's response for MCP (Model Context Protocol) tool awareness.

Agent Response: {output}
User Request: {input}

Scoring Criteria (0.0 - 1.0):
- 1.0: Agent correctly identifies and uses MCP tools when appropriate
- 0.7: Agent mentions MCP but doesn't use tools optimally
- 0.4: Agent shows vague awareness of tools
- 0.0: Agent ignores available MCP tools

Output JSON: {"score": <float>, "reasoning": "<string>"}
```

#### Evaluator 2: Output Format Validation (Custom Code)

- **Type**: Custom Code Evaluator
- **Language**: Python
- **Trigger**: Run-level

**Code**: See action plan document (Section 1.2)

#### Evaluator 3: Agent Routing Quality (Thread-Level)

- **Type**: Custom Code Evaluator
- **Language**: Python
- **Trigger**: Thread-level
- **Idle Time**: 5 minutes

**Code**: See action plan document (Section 1.2)

### Step 4: Setup Trajectory Evaluators

```bash
# Install and configure trajectory evaluators
python support/scripts/evaluation/setup_trajectory_evaluators.py
```

This creates evaluators for:

- Feature implementation patterns
- Bug investigation patterns
- Code review patterns
- Deployment workflow patterns

---

## 📅 Daily Operations (Week 1-3)

### Daily Review Workflow

Run this command every morning during UAT:

```bash
python support/scripts/evaluation/daily_uat_review.py
```

**What it does:**

1. ✅ Checks online evaluator scores (last 24h)
2. ✅ Reviews annotation queue status
3. ✅ Checks for regressions
4. ✅ (Optional) Exports training data

**Sample Output:**

```
=== Online Evaluator Scores (Last 24h) ===
✅ mcp-tool-awareness: 0.82 (min: 0.65, max: 0.95, n=45)
✅ format_validation: 0.91 (min: 0.80, max: 1.00, n=45)
⚠️  routing_efficiency: 0.68 (min: 0.40, max: 0.85, n=45)

=== Annotation Queue Status ===
📋 Traces flagged for review: 12
✅ Traces reviewed: 8

=== Regression Checks ===
✅ No regressions detected

=== Summary ===
⚠️  Regressions detected - manual review recommended
```

### Check Queue Status Anytime

```bash
python support/scripts/evaluation/check_queue_status.py
```

### Populate Queue with Uncertain Traces

```bash
# Flag low-confidence traces for review
python support/scripts/evaluation/auto_annotate_traces.py --populate-queue
```

### Sync Reviewed Traces to Dataset

```bash
# Move reviewed traces from queue to gold standard dataset
python support/scripts/evaluation/sync_dataset_from_annotations.py --from-queue
```

---

## 🔄 Weekly Operations

### Sunday: Sync and Evaluate

```bash
# 1. Sync all reviewed traces to dataset
python support/scripts/evaluation/sync_dataset_from_annotations.py --from-queue

# 2. Check dataset diversity
python support/scripts/evaluation/check_dataset_diversity.py \
  --dataset code-chef-gold-standard-v1

# 3. Run baseline comparison
python support/scripts/evaluation/baseline_runner.py \
  --mode baseline \
  --dataset code-chef-gold-standard-v1 \
  --output baseline-week$(date +%U).json

python support/scripts/evaluation/baseline_runner.py \
  --mode code-chef \
  --dataset code-chef-gold-standard-v1 \
  --output codechef-week$(date +%U).json

# 4. Compare results
python support/scripts/evaluation/query_evaluation_results.py \
  --compare \
  --baseline baseline-week$(date +%U).json \
  --candidate codechef-week$(date +%U).json
```

---

## 🧪 Testing

### Run Property-Based Tests

```bash
# Default profile (100 examples)
pytest support/tests/evaluation/test_property_based.py -v

# CI profile (fast, 20 examples)
HYPOTHESIS_PROFILE=ci pytest support/tests/evaluation/test_property_based.py -v

# Thorough profile (500 examples)
HYPOTHESIS_PROFILE=thorough pytest support/tests/evaluation/test_property_based.py -v
```

### Run Graph Trajectory Tests

```bash
# Test LangGraph routing quality
pytest support/tests/evaluation/test_graph_trajectory.py -v -s
```

---

## 🚢 Pre-Deployment Checks

### Automatic: GitHub Actions

When you label a PR with `ready-to-deploy`, the pre-deployment workflow automatically:

1. ✅ Runs baseline evaluation
2. ✅ Checks for regressions
3. ✅ Posts results as PR comment
4. ❌ Fails CI if regressions > 5% threshold

### Manual: Before Deploying

```bash
# Run full evaluation
python support/scripts/evaluation/baseline_runner.py \
  --mode code-chef \
  --tasks support/scripts/evaluation/sample_tasks.json \
  --output pre-deploy-results.json

# Check for regressions
python support/scripts/evaluation/detect_regression.py \
  --results pre-deploy-results.json \
  --threshold 0.05
```

---

## 📊 Key Metrics to Monitor

### Online Evaluator Scores (Target: >0.75)

- **MCP Tool Awareness**: Are agents using MCP tools effectively?
- **Format Validation**: Are responses well-formatted?
- **Routing Efficiency**: Is supervisor routing optimal?

### Queue Health (Target: <10 pending)

- **Pending Reviews**: Traces awaiting human review
- **Review Rate**: Reviews per day
- **Oldest Trace**: Age of oldest pending trace

### Regression Detection (Target: <5% decline)

- **Accuracy**: Correctness of agent responses
- **Latency**: Response time performance
- **Cost**: Token usage efficiency

---

## 🛠 Troubleshooting

### Issue: "LangSmith not available"

```bash
pip install langsmith
export LANGCHAIN_API_KEY=<your-key>
```

### Issue: "AgentEvals not available"

```bash
pip install agentevals openevals
```

### Issue: "Queue not found"

Run the queue creation script again:

```bash
python support/scripts/evaluation/create_annotation_queue.py
```

### Issue: "No traces in queue"

Populate the queue manually:

```bash
python support/scripts/evaluation/auto_annotate_traces.py --populate-queue
```

---

## 📈 Success Metrics

### Week 1 Goals

- [ ] Online evaluators configured and running
- [ ] Annotation queue created with 20+ traces
- [ ] AgentEvals library installed and tested
- [ ] Daily review workflow established

### Week 2 Goals

- [ ] 50+ traces annotated in queue
- [ ] Gold standard dataset has 30+ examples
- [ ] Baseline comparison shows <5% regression
- [ ] Automated sync working (queue → dataset)

### Week 3 Goals

- [ ] Online evaluator scores > 0.80 average
- [ ] Error rate < 3%
- [ ] Intent classification confidence > 0.75 P95
- [ ] Trajectory evaluators passing on regression tests

### End of UAT

- [ ] 100+ annotated traces in gold standard dataset
- [ ] Regression test suite covers all critical bugs
- [ ] Model training decision made (based on baseline comparison)
- [ ] Documentation updated with evaluation procedures

---

## 💡 Quick Reference Commands

```bash
# Daily review
python support/scripts/evaluation/daily_uat_review.py

# Check queue
python support/scripts/evaluation/check_queue_status.py

# Populate queue
python support/scripts/evaluation/auto_annotate_traces.py --populate-queue

# Sync reviewed traces
python support/scripts/evaluation/sync_dataset_from_annotations.py --from-queue

# Check diversity
python support/scripts/evaluation/check_dataset_diversity.py

# Run baseline eval
python support/scripts/evaluation/baseline_runner.py --mode code-chef

# Check regression
python support/scripts/evaluation/detect_regression.py --results evaluation-results.json

# Export training data
python support/scripts/evaluation/export_training_dataset.py --output training.jsonl

# Run tests
pytest support/tests/evaluation/ -v
```

---

## 📚 Additional Resources

- **Original Action Plan**: `.github/prompts/plan-langsmithUatActionPlan.prompt.md`
- **LangSmith Documentation**: https://docs.smith.langchain.com
- **AgentEvals Documentation**: https://github.com/langchain-ai/agentevals
- **LLM Operations Guide**: `support/docs/operations/LLM_OPERATIONS.md`

---

## 🎯 Next Steps

1. **Today**:

   - Run queue creation script
   - Configure online evaluators in LangSmith UI
   - Start daily review workflow

2. **This Week**:

   - Collect 20+ traces in annotation queue
   - Review and annotate traces
   - Run first baseline comparison

3. **Next Week**:

   - Sync reviewed traces to dataset
   - Run trajectory evaluators
   - Analyze regression patterns

4. **Week 3+**:
   - Weekly model evaluation
   - Decide on model fine-tuning
   - Expand regression test suite

---

**Questions or Issues?**

- Check LangSmith dashboard: https://smith.langchain.com
- Review action plan: `.github/prompts/plan-langsmithUatActionPlan.prompt.md`
- Run daily review: `python support/scripts/evaluation/daily_uat_review.py`
