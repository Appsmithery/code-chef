# LangSmith Evaluation - Quick Reference

**One-page cheat sheet for common evaluation tasks**

---

## Daily Commands

### Run Quick Evaluation

```bash
python support/tests/evaluation/run_langsmith_evaluation.py \
    --dataset code-chef-gold-standard-v1
```

### Check for Regression

```bash
python support/scripts/evaluation/detect_regression.py \
    --results evaluation_results.json \
    --threshold 0.05
```

---

## Weekly Commands

### Sync Dataset from Annotations

```bash
python support/scripts/evaluation/sync_dataset_from_annotations.py \
    --dataset code-chef-gold-standard-v1 \
    --days 7
```

### Run with Baseline Comparison

```bash
python support/tests/evaluation/run_langsmith_evaluation.py \
    --dataset code-chef-gold-standard-v1 \
    --compare-baseline \
    --output weekly_results.json
```

---

## Environment Setup

```bash
# Required environment variables
export LANGCHAIN_API_KEY=lsv2_sk_***
export OPENAI_API_KEY=sk-***
export LINEAR_API_KEY=lin_api_***
export ORCHESTRATOR_URL=https://codechef.appsmithery.co
```

---

## File Locations

| File                                                          | Purpose                |
| ------------------------------------------------------------- | ---------------------- |
| `support/tests/evaluation/run_langsmith_evaluation.py`        | Main evaluation runner |
| `support/scripts/evaluation/sync_dataset_from_annotations.py` | Dataset sync           |
| `support/scripts/evaluation/detect_regression.py`             | Regression detection   |
| `.github/workflows/continuous-evaluation.yml`                 | CI/CD workflow         |
| `support/tests/evaluation/evaluators.py`                      | Custom evaluators      |

---

## LangSmith URLs

- **Projects**: https://smith.langchain.com/projects
- **Datasets**: https://smith.langchain.com/datasets
- **Evaluation Results**: https://smith.langchain.com → code-chef-evaluation

---

## Linear

- **Project**: https://linear.app/dev-ops/project/codechef-78b3b839d36b
- **Evaluation Issues**: Filter by label `evaluation`

---

## Common Flags

| Flag                    | Purpose                              |
| ----------------------- | ------------------------------------ |
| `--dataset`             | Dataset name                         |
| `--compare-baseline`    | Run baseline comparison              |
| `--evaluators-only`     | `all`, `custom`, `prebuilt`, `llm`   |
| `--dry-run`             | Preview changes without applying     |
| `--create-linear-issue` | Create issue on regression           |
| `--threshold`           | Regression threshold (default: 0.05) |

---

## Quick Debugging

```bash
# Check orchestrator
curl https://codechef.appsmithery.co/health

# View traces
# Visit: https://smith.langchain.com → code-chef-production

# Check dataset size
python -c "from langsmith import Client; ds = Client().read_dataset('code-chef-gold-standard-v1'); print(f'{ds.example_count} examples')"
```

---

## Keyboard Shortcuts

| Task        | Command                                                  |
| ----------- | -------------------------------------------------------- |
| Run tests   | `Ctrl+Shift+P` → "Tasks: Run Task" → "Run All Tests"     |
| View logs   | `Ctrl+Shift+P` → "Tasks: Run Task" → "View Droplet Logs" |
| SSH droplet | `Ctrl+Shift+P` → "Tasks: Run Task" → "SSH to Droplet"    |

---

## Status Checks

```bash
# Evaluation status
ls -lh evaluation_results.json

# Dataset status
python support/scripts/evaluation/sync_dataset_from_annotations.py --dataset code-chef-gold-standard-v1 --dry-run

# Workflow status
# Visit: https://github.com/Appsmithery/code-chef/actions
```

---

**Documentation**: [LANGSMITH_AUTOMATION_README.md](support/tests/evaluation/LANGSMITH_AUTOMATION_README.md)
