# Plan: Testing, Tracing & Evaluation Refactoring

**Objective**: Establish longitudinal performance tracking and A/B testing infrastructure to measure code-chef improvement over time and validate superiority vs baseline LLMs.

**Linear Tracking**: [CHEF-238](https://linear.app/dev-ops/issue/CHEF-238) (parent issue with 6 sub-issues)

---

## Steps

### 1. Create Time-Series Performance Database (Foundation for all tracking)

**Linear**: [CHEF-239](https://linear.app/dev-ops/issue/CHEF-239)

- Add `config/state/evaluation_results.sql` with `evaluation_results` table (experiment_id, task_id, experiment_group, extension_version, scores, timestamps)
- Implement `shared/lib/longitudinal_tracker.py` following `shared/lib/token_tracker.py` singleton pattern (async pool, thread-safe aggregation, Prometheus exports)
- Add correlation table `task_comparisons` to link baseline↔code-chef runs via task_id
- Create TimescaleDB hypertable for time-series queries or use indexes for date-range performance

### 2. Complete Baseline Runner Implementation (Enable real A/B testing)

**Linear**: [CHEF-240](https://linear.app/dev-ops/issue/CHEF-240)

- Replace placeholders in `baseline_runner.py:142-210` with real LLM invocations
- Add OpenRouter API client for baseline (pure model, no code-chef) using `shared/lib/gradient_client.py` pattern
- Add VS Code extension API call for code-chef variant (trained models + orchestration)
- Store results in `evaluation_results` table with task_id correlation, not just JSON files
- Capture actual `tokens_used`, `latency_ms`, `cost_usd` from API responses

### 3. Build Comparison Engine with Basic Metrics (Automated reporting)

**Linear**: [CHEF-241](https://linear.app/dev-ops/issue/CHEF-241)

- Create `shared/lib/comparison_engine.py` for side-by-side baseline vs code-chef comparison
- Calculate basic improvement percentages: speed (latency reduction), accuracy, completeness, efficiency, cost
- Generate simple JSON comparison reports using `support/tests/evaluation/evaluators.py` scores
- Query `evaluation_results` grouped by experiment_id and experiment_group for aggregate metrics
- Create `experiment_summaries` table for cacheable comparison results (wins/losses/ties, avg improvements)

### 4. Enhance Evaluation Runner with Database Persistence (Longitudinal tracking) ✅ COMPLETED

**Linear**: [CHEF-242](https://linear.app/dev-ops/issue/CHEF-242)  
**Status**: ✅ Completed (Phase 4)  
**Completed**: December 11, 2025

**Implementation Summary**:

- ✅ Enhanced `run_evaluation.py` with async database persistence via `longitudinal_tracker`
- ✅ Added proper task_id correlation between LangSmith runs and examples with experiment tracking
- ✅ Integrated ModelOps `evaluation.py` with database persistence for all evaluation operations
- ✅ Created `query_evaluation_results.py` with time-series queries, A/B comparison, and CSV export
- ✅ Added comprehensive integration tests in `test_evaluation_persistence.py`

**Key Files Modified**:

- `support/tests/evaluation/run_evaluation.py` - Added async DB persistence with experiment_id/task_id correlation
- `agent_orchestrator/agents/infrastructure/modelops/evaluation.py` - Made async, integrated tracker
- `support/scripts/evaluation/query_evaluation_results.py` - New CLI tool for querying results
- `support/tests/integration/test_evaluation_persistence.py` - Comprehensive test coverage

**Usage Examples**:

```bash
# Run evaluation with database persistence
python support/tests/evaluation/run_evaluation.py \
  --dataset ib-agent-scenarios-v1 \
  --experiment-id exp-2025-01-001 \
  --experiment-group code-chef

# Query metric trends
python support/scripts/evaluation/query_evaluation_results.py \
  --trend --agent feature_dev --metric accuracy --days 30

# Compare experiments
python support/scripts/evaluation/query_evaluation_results.py \
  --compare --experiment exp-2025-01-001

# Export to CSV for Grafana
python support/scripts/evaluation/query_evaluation_results.py \
  --export results.csv --agent feature_dev --days 90
```

### 5. Create Comprehensive A/B Test Suite (Validation & regression detection)

**Linear**: [CHEF-243](https://linear.app/dev-ops/issue/CHEF-243)

- Add `support/tests/evaluation/test_baseline_comparison.py` for end-to-end A/B workflow validation
- Test task execution through both baseline and code-chef with task_id correlation
- Assert statistical significance of improvements using comparison_engine
- Add property-based tests with Hypothesis for evaluator robustness following `conftest.py:110-121` profiles
- Create `support/tests/integration/test_longitudinal_tracking.py` for version-over-version regression detection

### 6. Update Testing Infrastructure & Documentation (Enable team usage)

**Linear**: [CHEF-245](https://linear.app/dev-ops/issue/CHEF-245)

- Add fixtures to `conftest.py`: `longitudinal_tracker_fixture`, `baseline_llm_client`, `ab_experiment_id`
- Update `tracing-schema.yaml` examples with task_id correlation (lines 195-219)
- Document new workflow in `support/docs/operations/llm-operations.md` A/B Testing section
- Add GitHub Actions workflow `.github/workflows/evaluation-regression.yml` to run evaluations on PR merge

---

## Further Considerations

### 1. Database Infrastructure Choice

TimescaleDB extension (recommended for time-series) vs standard PostgreSQL with date indexes vs separate InfluxDB? TimescaleDB keeps everything in Postgres and supports continuous aggregates for fast queries.

### 2. Baseline Model Selection

Which baseline LLM represents "untrained" comparison? Options:

- Claude 3.5 Haiku (fast, $1/1M)
- GPT-4o mini (cheap, $0.15/1M)
- CodeLlama 70B (open source, $0.70/1M via OpenRouter)

### 3. Evaluation Frequency

Run A/B tests on every PR (expensive, ~$2-5/run), nightly (good cadence), or on-demand only? Consider hybrid: quick smoke tests on PR, comprehensive on merge to main.

---

## Implementation Priority

**Phase 1 (Critical - Days 1-2)**: Steps 1-2 (Database + Baseline Runner)
**Phase 2 (High - Days 3-4)**: Steps 3-4 (Comparison Engine + Evaluation Persistence)
**Phase 3 (Medium - Day 5)**: Steps 5-6 (Test Suite + Documentation)

---

## Success Metrics

- ✅ Baseline runner executes real LLM calls (no placeholders)
- ✅ Results stored in PostgreSQL with timestamps for longitudinal analysis
- ✅ A/B comparison reports generate automatically with statistical significance
- ✅ Historical trend queries show improvement over extension versions
- ✅ End-to-end tests validate A/B workflow without manual intervention
- ✅ Team can run evaluations via documented procedures
