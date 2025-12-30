# LangSmith Evaluation Automation - Activation Checklist

**Purpose**: Step-by-step guide to activate the newly implemented evaluation automation system.

---

## Prerequisites

### 1. Install Dependencies

```bash
# Navigate to project root
cd d:\APPS\code-chef

# Install required packages
pip install langsmith langchain-openai httpx loguru

# Optional: Install langchain for prebuilt evaluators
pip install langchain
```

### 2. Verify Environment Variables

```bash
# Check required variables
echo $LANGCHAIN_API_KEY   # Should start with lsv2_sk_
echo $OPENAI_API_KEY      # Should start with sk-
echo $LINEAR_API_KEY      # For issue creation

# If missing, add to environment:
# Windows PowerShell:
$env:LANGCHAIN_API_KEY = "lsv2_sk_***"
$env:OPENAI_API_KEY = "sk-***"
$env:LINEAR_API_KEY = "lin_api_***"
```

---

## Step 1: Configure GitHub Actions Secrets

**Navigate to**: https://github.com/Appsmithery/code-chef/settings/secrets/actions

**Add these secrets**:

1. **LANGCHAIN_API_KEY**

   - Value: Your LangSmith API key from https://smith.langchain.com
   - Format: `lsv2_sk_***`

2. **OPENAI_API_KEY**

   - Value: Your OpenAI API key
   - Format: `sk-***`

3. **LINEAR_API_KEY**
   - Value: Your Linear API key from https://linear.app/dev-ops/settings/api
   - Format: `lin_api_***`

**Verification**:

```bash
# Run this in GitHub Actions to test
- name: Test secrets
  run: |
    echo "LangSmith: ${LANGCHAIN_API_KEY:0:10}..."
    echo "OpenAI: ${OPENAI_API_KEY:0:10}..."
    echo "Linear: ${LINEAR_API_KEY:0:10}..."
```

---

## Step 2: Create Evaluation Dataset

### Option A: Start Fresh

```bash
python support/scripts/evaluation/sync_dataset_from_annotations.py \
    --dataset code-chef-gold-standard-v1 \
    --days 30 \
    --dry-run

# Review output, then run for real:
python support/scripts/evaluation/sync_dataset_from_annotations.py \
    --dataset code-chef-gold-standard-v1 \
    --days 30
```

### Option B: Use Existing Dataset

If you already have a dataset in LangSmith:

1. Go to https://smith.langchain.com → Datasets
2. Find your dataset name
3. Update `DEFAULT_DATASET` in `run_langsmith_evaluation.py` if needed

---

## Step 3: Annotate Production Traces

**Goal**: Add 10-20 high-quality annotated examples

### Process:

1. **Go to LangSmith**: https://smith.langchain.com → Projects → code-chef-production

2. **Filter for good traces**:

   - Status: Success
   - Recent (last 7 days)
   - Representative examples

3. **Add feedback**:

   - Click trace → Add feedback
   - Key: `correctness`
   - Score: 0.0 - 1.0 (use ≥ 0.7 for dataset inclusion)
   - Comment: Why this is a good/bad example

4. **Add tags** (for categorization):

   - `agent_routing` - Agent selection
   - `token_efficiency` - Token usage
   - `latency` - Response time
   - `workflow_completeness` - Task completion
   - `mcp_integration` - Tool usage

5. **Sync to dataset**:
   ```bash
   python support/scripts/evaluation/sync_dataset_from_annotations.py \
       --dataset code-chef-gold-standard-v1 \
       --days 7
   ```

---

## Step 4: Run First Evaluation

### Local Test Run

```bash
# Set environment
export LANGCHAIN_API_KEY=lsv2_sk_***
export OPENAI_API_KEY=sk-***
export ORCHESTRATOR_URL=https://codechef.appsmithery.co

# Run evaluation
python support/tests/evaluation/run_langsmith_evaluation.py \
    --dataset code-chef-gold-standard-v1 \
    --experiment-prefix test-run \
    --output test_results.json

# Check results
cat test_results.json | jq '.code_chef.results'
```

### With Baseline Comparison

```bash
python support/tests/evaluation/run_langsmith_evaluation.py \
    --dataset code-chef-gold-standard-v1 \
    --compare-baseline \
    --output baseline_comparison.json

# View comparison
cat baseline_comparison.json | jq '.comparison'
```

---

## Step 5: Enable Continuous Evaluation

### Merge Workflow to Main

```bash
# Review workflow file
cat .github/workflows/continuous-evaluation.yml

# Commit and push (will trigger first run)
git add .github/workflows/continuous-evaluation.yml
git commit -m "Enable continuous evaluation workflow"
git push origin main

# Monitor first run
# https://github.com/Appsmithery/code-chef/actions
```

### Verify Workflow Runs

1. **Check Actions tab**: https://github.com/Appsmithery/code-chef/actions
2. **Look for**: "Continuous Evaluation" workflow
3. **Expected duration**: 5-10 minutes
4. **Artifacts**: evaluation-results-{sha} should be created

---

## Step 6: Test Regression Detection

### Simulate Regression

```bash
# Create mock regression results
cat > mock_regression.json << 'EOF'
{
  "comparison": {
    "overall_improvement_pct": -12.5,
    "per_metric": {
      "accuracy": {
        "baseline": 0.85,
        "codechef": 0.72,
        "improvement_pct": -15.3,
        "winner": "baseline"
      }
    }
  }
}
EOF

# Test detection
python support/scripts/evaluation/detect_regression.py \
    --results mock_regression.json \
    --threshold 0.05 \
    --create-linear-issue

# Check Linear for new issue
# https://linear.app/dev-ops/project/codechef-78b3b839d36b
```

---

## Step 7: Monitor & Iterate

### Weekly Tasks

1. **Review evaluation results**

   - LangSmith: https://smith.langchain.com → code-chef-evaluation
   - Check for trends

2. **Update dataset**

   ```bash
   python support/scripts/evaluation/sync_dataset_from_annotations.py \
       --dataset code-chef-gold-standard-v1 \
       --days 7
   ```

3. **Check for regressions**
   - Linear: Review automated issues
   - Investigate any critical regressions

### Monthly Tasks

1. **Review cost tracking**

   ```bash
   # Check evaluation costs
   curl https://codechef.appsmithery.co/metrics/tokens | jq '.evaluation'
   ```

2. **Tune thresholds if needed**

   - Edit `detect_regression.py` thresholds
   - Update based on false positive rate

3. **Add new evaluators**
   - Identify new patterns to test
   - Add to `evaluators.py`
   - Update `run_langsmith_evaluation.py`

---

## Troubleshooting

### Evaluation Fails

**Symptom**: GitHub Actions fails with "Connection refused"

**Solution**:

```bash
# Check orchestrator health
curl https://codechef.appsmithery.co/health

# If down, SSH to droplet and restart
ssh root@45.55.173.72 "cd /opt/code-chef && docker compose restart orchestrator"
```

### No Examples in Dataset

**Symptom**: "No examples found in dataset"

**Solution**:

```bash
# Check dataset exists
python -c "from langsmith import Client; print(Client().list_datasets())"

# If not found, create it
python support/scripts/evaluation/sync_dataset_from_annotations.py \
    --dataset code-chef-gold-standard-v1 \
    --days 30
```

### Linear Issue Not Created

**Symptom**: Regression detected but no Linear issue

**Solution**:

```bash
# Verify Linear API key
echo $LINEAR_API_KEY | cut -c1-10

# Test Linear client
python -c "from shared.lib.linear_client import linear_client; print(linear_client)"

# Check logs
cat evaluation_results.json | jq '.linear_issue_id'
```

### Prebuilt Evaluators Fail

**Symptom**: "ModuleNotFoundError: No module named 'langchain.evaluation'"

**Solution**:

```bash
# Install langchain
pip install langchain

# Or skip prebuilt evaluators
python support/tests/evaluation/run_langsmith_evaluation.py \
    --evaluators-only custom
```

---

## Success Metrics

After activation, you should see:

- ✅ **Weekly evaluation runs** in GitHub Actions
- ✅ **Results artifacts** uploaded to Actions
- ✅ **Traces in LangSmith** project
- ✅ **Dataset growing** with new examples
- ✅ **Linear issues** for regressions (hopefully none!)
- ✅ **Email notifications** on failures
- ✅ **Cost tracking** in metrics

---

## Timeline

| Task                 | Duration | Status     |
| -------------------- | -------- | ---------- |
| Install dependencies | 5 min    | ⏳ Pending |
| Configure secrets    | 10 min   | ⏳ Pending |
| Create dataset       | 30 min   | ⏳ Pending |
| Annotate traces      | 60 min   | ⏳ Pending |
| Run first evaluation | 15 min   | ⏳ Pending |
| Enable workflow      | 5 min    | ⏳ Pending |
| Test regression      | 10 min   | ⏳ Pending |

**Total**: ~2.5 hours to full activation

---

## Next Steps

1. ✅ Complete Steps 1-7 above
2. ✅ Monitor first week of automated runs
3. ✅ Tune thresholds based on experience
4. ✅ Add domain-specific evaluators as needed
5. ✅ Document learnings in Linear

---

## Support

**Questions?** File an issue in [Linear](https://linear.app/dev-ops/project/codechef-78b3b839d36b) with label `evaluation`.

**Documentation**:

- [Automation README](support/tests/evaluation/LANGSMITH_AUTOMATION_README.md)
- [Implementation Summary](IMPLEMENTATION_SUMMARY.md)
- [LLM Operations Guide](support/docs/operations/LLM_OPERATIONS.md)
