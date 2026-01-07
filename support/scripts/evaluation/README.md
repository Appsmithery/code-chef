# Evaluation Scripts

This directory contains scripts for LangSmith-based evaluation, testing, and model training workflows.

## 📁 Directory Structure

```
evaluation/
├── auto_annotate_traces.py          # Auto-annotate traces with quality metrics
├── baseline_runner.py                # Run baseline vs code-chef comparisons
├── check_dataset_diversity.py        # Analyze dataset coverage
├── check_queue_status.py            # Monitor annotation queue health
├── create_annotation_queue.py        # Setup UAT review queue
├── daily_uat_review.py              # Daily quality check workflow
├── detect_regression.py              # Detect performance regressions
├── export_training_dataset.py        # Export to HuggingFace
├── query_evaluation_results.py       # Query evaluation metrics from DB
├── setup_trajectory_evaluators.py    # Configure AgentEvals
├── sync_dataset_from_annotations.py  # Sync reviewed traces to datasets
└── sample_tasks.json                # Standard evaluation tasks
```

## 🚀 Quick Start

### Daily UAT Workflow

```bash
# Morning: Review quality metrics
python daily_uat_review.py

# Throughout day: Check queue status
python check_queue_status.py

# Evening: Sync reviewed traces
python sync_dataset_from_annotations.py --from-queue
```

### Weekly Workflow

```bash
# Sunday: Full evaluation cycle
python sync_dataset_from_annotations.py --from-queue
python check_dataset_diversity.py
python baseline_runner.py --mode baseline
python baseline_runner.py --mode code-chef
```

## 📊 Script Reference

### auto_annotate_traces.py

Automatically annotates traces with quality scores and flags uncertain traces for review.

```bash
# Annotate recent traces
python auto_annotate_traces.py --days 1

# Populate annotation queue
python auto_annotate_traces.py --populate-queue

# Annotate specific experiment
python auto_annotate_traces.py --experiment exp-2025-01-001
```

### baseline_runner.py

Runs A/B tests comparing baseline (untrained) vs code-chef (trained) models.

```bash
# Run baseline evaluation
python baseline_runner.py --mode baseline --output baseline-results.json

# Run code-chef evaluation
python baseline_runner.py --mode code-chef --output codechef-results.json

# Use specific dataset
python baseline_runner.py --mode code-chef --dataset ib-agent-scenarios-v1
```

### check_dataset_diversity.py

Analyzes training dataset to identify underrepresented task categories.

```bash
python check_dataset_diversity.py --dataset code-chef-gold-standard-v1
```

### check_queue_status.py

Displays annotation queue metrics and health status.

```bash
python check_queue_status.py
python check_queue_status.py --queue uat-review-queue
```

### create_annotation_queue.py

Creates the UAT annotation queue in LangSmith.

```bash
python create_annotation_queue.py
```

**Note**: Requires manual configuration in LangSmith UI afterward (see output for instructions).

### daily_uat_review.py

Comprehensive daily quality check workflow.

```bash
# Standard daily review
python daily_uat_review.py

# With training data export
python daily_uat_review.py --export-training

# Custom agent/metric
python daily_uat_review.py --agent infrastructure --metric latency
```

### detect_regression.py

Detects performance regressions and creates Linear issues.

```bash
# Check results file
python detect_regression.py --results evaluation-results.json --threshold 0.05

# Query historical data
python detect_regression.py --agent feature_dev --metric accuracy --days 30

# Create Linear issue if regression detected
python detect_regression.py --results results.json --create-linear-issue
```

### export_training_dataset.py

Exports annotated traces to HuggingFace dataset format.

```bash
# Export high-quality examples
python export_training_dataset.py --min-score 0.8 --output training.jsonl

# Export from specific dataset
python export_training_dataset.py \
  --dataset code-chef-gold-standard-v1 \
  --output training-$(date +%Y%m%d).jsonl
```

### query_evaluation_results.py

Queries and analyzes evaluation results from PostgreSQL.

```bash
# Compare two experiments
python query_evaluation_results.py \
  --compare \
  --experiment exp-2025-01-001

# Export metrics to CSV
python query_evaluation_results.py --export metrics.csv
```

### setup_trajectory_evaluators.py

Configures AgentEvals trajectory evaluators for regression testing.

```bash
python setup_trajectory_evaluators.py
```

Creates evaluators for:

- Feature implementation patterns
- Bug investigation patterns
- Code review patterns
- Deployment workflows

### sync_dataset_from_annotations.py

Syncs annotated traces to evaluation datasets.

```bash
# Sync from annotation queue
python sync_dataset_from_annotations.py --from-queue

# Sync last 7 days
python sync_dataset_from_annotations.py --days 7

# Sync specific categories
python sync_dataset_from_annotations.py --categories agent_routing,token_efficiency

# Dry run (preview changes)
python sync_dataset_from_annotations.py --dry-run
```

## 🎯 Common Workflows

### Setup (First Time)

```bash
# 1. Install dependencies
pip install langsmith agentevals openevals

# 2. Create annotation queue
python create_annotation_queue.py

# 3. Setup trajectory evaluators
python setup_trajectory_evaluators.py

# 4. Configure online evaluators in LangSmith UI
# (See LANGSMITH_UAT_QUICKSTART.md for instructions)
```

### Daily Operations (UAT)

```bash
# Morning
python daily_uat_review.py

# Monitor queue throughout day
python check_queue_status.py

# Populate queue with uncertain traces
python auto_annotate_traces.py --populate-queue

# Evening sync
python sync_dataset_from_annotations.py --from-queue
```

### Pre-Deployment

```bash
# Run evaluation
python baseline_runner.py --mode code-chef --output pre-deploy.json

# Check for regressions
python detect_regression.py --results pre-deploy.json --threshold 0.05
```

### Weekly Review

```bash
# Sync all data
python sync_dataset_from_annotations.py --from-queue

# Check diversity
python check_dataset_diversity.py

# Run baseline comparison
python baseline_runner.py --mode baseline
python baseline_runner.py --mode code-chef

# Export training data
python export_training_dataset.py --min-score 0.8
```

## 📈 Success Metrics

### Queue Health

- **Good**: <10 pending traces
- **Warning**: 10-50 pending traces
- **Critical**: >50 pending traces

### Evaluator Scores

- **Good**: >0.80 average
- **Warning**: 0.60-0.80
- **Critical**: <0.60

### Regression Threshold

- **Safe**: <5% decline
- **Review**: 5-15% decline
- **Critical**: >15% decline

## 🔗 Related Documentation

- **Quick Start Guide**: `../../LANGSMITH_UAT_QUICKSTART.md`
- **Action Plan**: `../../.github/prompts/plan-langsmithUatActionPlan.prompt.md`
- **LLM Operations**: `../docs/operations/LLM_OPERATIONS.md`
- **Evaluation Tests**: `../tests/evaluation/`

## 💡 Tips

1. **Run daily_uat_review.py every morning** - Catches issues early
2. **Monitor queue status frequently** - Don't let queue get backed up
3. **Sync reviewed traces regularly** - Keeps dataset fresh
4. **Check dataset diversity weekly** - Ensure balanced training data
5. **Review regressions immediately** - Investigate before deploying

## 🛠 Troubleshooting

### "LangSmith not available"

```bash
pip install langsmith
export LANGCHAIN_API_KEY=<your-key>
```

### "AgentEvals not available"

```bash
pip install agentevals openevals
```

### "Queue not found"

```bash
python create_annotation_queue.py
```

### "No data in queue"

```bash
python auto_annotate_traces.py --populate-queue
```

### "Database connection error"

```bash
# Check PostgreSQL is running
docker compose ps
# Or on droplet
ssh root@45.55.173.72 "docker compose ps"
```

## 📞 Support

For issues or questions:

1. Check **LANGSMITH_UAT_QUICKSTART.md**
2. Review **LLM_OPERATIONS.md**
3. Check LangSmith dashboard: https://smith.langchain.com
4. Create Linear issue with label `langsmith-uat`
