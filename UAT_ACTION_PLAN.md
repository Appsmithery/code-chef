# UAT & Annotation Action Plan

**Start Date**: December 29, 2024  
**Goal**: Establish baseline metrics and accumulate 50+ annotated examples  
**Duration**: 2 weeks

---

## Quick Start (Do This Now!)

### 1. Run First Evaluation ✅

```bash
cd D:\APPS\code-chef

# Test with existing dataset (15 examples)
python support/tests/evaluation/run_langsmith_evaluation.py \
    --dataset ib-agent-scenarios-v1 \
    --experiment-prefix uat-baseline \
    --evaluators all \
    --max-concurrency 5 \
    --output baseline-results.json
```

**Expected Output**:

```
Running code-chef evaluation: uat-baseline-20241229-HHMMSS
Using project: code-chef-evaluation
Dataset: ib-agent-scenarios-v1
Evaluators: 13 total evaluators

Evaluation complete!
Results: https://smith.langchain.com/...
```

**Review Results**:

1. Click the LangSmith URL in output
2. Review aggregate metrics (accuracy, latency, token efficiency)
3. Click individual traces to see evaluator scores
4. Note any failing examples for improvement

### 2. Start Using Extension

Use code-chef for normal development tasks:

- "Implement JWT authentication"
- "Review this PR for security issues"
- "Deploy to staging environment"
- "Generate API documentation"
- "Optimize database queries"

**Every request is automatically traced** to LangSmith production project!

### 3. Annotate Your First 5 Traces

**Go to LangSmith**:

1. Visit: https://smith.langchain.com
2. Select project: `code-chef-production`
3. Filter: Recent traces (last 24 hours)
4. Find your traces

**Add Feedback**:
For each trace:

1. Click trace → "Add feedback"
2. Key: `correctness`
3. Score:
   - **1.0**: Perfect response, exactly what you wanted
   - **0.8-0.9**: Good response, minor improvements possible
   - **0.7**: Acceptable, but room for improvement (threshold for dataset inclusion)
   - **<0.7**: Needs improvement, don't add to dataset
4. Comment: Brief explanation of score
5. Tags (optional): `agent_routing`, `token_efficiency`, `mcp_integration`, `workflows`

**Example Annotations**:

✅ **Good Example** (score: 0.9):

```
Trace: "Implement JWT middleware"
Response: Correct agent selected (feature_dev), proper middleware code,
          included error handling, mentioned MCP filesystem tools
Score: 0.9
Comment: "Excellent implementation, minor docs could be improved"
Tags: agent_routing, mcp_integration
```

✅ **Acceptable Example** (score: 0.7):

```
Trace: "Review security in login.py"
Response: Correct agent selected (code_review), found 2/3 vulnerabilities,
          suggested fixes, but missed SQL injection check
Score: 0.7
Comment: "Good catch on auth issues, missed SQL injection"
Tags: agent_routing, workflows
```

❌ **Poor Example** (score: 0.4 - don't add):

```
Trace: "Deploy to production"
Response: Wrong agent selected (feature_dev instead of cicd),
          no approval flow triggered, missing deployment steps
Score: 0.4
Comment: "Incorrect routing, needs improvement"
```

---

## Daily Workflow (10 minutes/day)

### Morning (5 min)

1. Use extension for 2-3 tasks
2. Note any issues or excellent responses

### Evening (5 min)

1. Open LangSmith → code-chef-production
2. Review your traces from today
3. Annotate each with correctness score
4. Focus on high-quality examples (≥0.7)
5. Add relevant tags

### Weekly (Friday, 15 min)

```bash
# Sync annotated traces to dataset
python support/scripts/evaluation/sync_dataset_from_annotations.py \
    --project code-chef-production \
    --dataset ib-agent-scenarios-v1 \
    --min-score 0.7 \
    --days-back 7

# Re-run evaluation
python support/tests/evaluation/run_langsmith_evaluation.py \
    --dataset ib-agent-scenarios-v1 \
    --experiment-prefix uat-week1 \
    --compare-baseline \
    --output week1-results.json

# Check improvement
jq '.comparison.overall_improvement_pct' week1-results.json
```

---

## Week 1 Targets

### Day 1-2 (Mon-Tue)

- [x] Run baseline evaluation ← **Start here!**
- [ ] Annotate 5 traces
- [ ] Document baseline metrics
- [ ] Set up daily annotation routine

### Day 3-4 (Wed-Thu)

- [ ] Annotate 5 more traces (total: 10)
- [ ] Review LangSmith metrics
- [ ] Identify common failure patterns
- [ ] Test different query types

### Day 5-7 (Fri-Sun)

- [ ] Annotate 5 more traces (total: 15)
- [ ] Sync dataset (should have 30 total)
- [ ] Run week 1 evaluation
- [ ] Compare against baseline
- [ ] Document insights

**Week 1 Goal**: 30 total annotated examples (15 existing + 15 new)

---

## Week 2 Targets

### Day 8-10 (Mon-Wed)

- [ ] Annotate 7 traces per day (21 total)
- [ ] Focus on diverse categories:
  - 5 agent_routing examples
  - 5 token_efficiency examples
  - 5 mcp_integration examples
  - 6 workflow examples

### Day 11-12 (Thu-Fri)

- [ ] Annotate 5 more traces (total: 26)
- [ ] Sync dataset (should have 56 total)
- [ ] Run week 2 evaluation
- [ ] Enable GitHub Actions workflow
- [ ] Test automatic evaluation

### Day 13-14 (Weekend)

- [ ] Review metrics trends
- [ ] Document improvement
- [ ] Plan month 2 strategy
- [ ] Consider first fine-tuning if 100+ examples

**Week 2 Goal**: 56 total annotated examples (30 from week 1 + 26 new)

---

## Annotation Categories

### Agent Routing (Target: 15 examples)

Focus on correct agent selection:

- Feature development tasks
- Code review requests
- Infrastructure/IaC operations
- CI/CD pipeline tasks
- Documentation generation

### Token Efficiency (Target: 10 examples)

Focus on token usage optimization:

- Concise responses
- Efficient tool loading
- Minimal context window usage
- Smart caching

### MCP Integration (Target: 10 examples)

Focus on tool usage quality:

- GitHub operations
- Linear issue management
- Filesystem operations
- Memory/context retrieval
- Docker container management

### Workflows (Target: 10 examples)

Focus on multi-step task completion:

- PR deployment workflows
- Feature development lifecycle
- Hotfix procedures
- Documentation updates
- Infrastructure changes

### General (Target: 11 examples)

Miscellaneous high-quality interactions

---

## Monitoring Dashboard

### LangSmith Projects

**Production Traces**:

- URL: https://smith.langchain.com → `code-chef-production`
- Filter: `project_id:"4c4a4e10-9d58-4ca1-a111-82893d6ad495"`
- View: Recent activity, feedback scores, trace details

**Evaluation Results**:

- URL: https://smith.langchain.com → `code-chef-evaluation`
- Filter: `environment:"evaluation"`
- View: Experiment comparisons, metric trends

**Training Jobs** (future):

- URL: https://smith.langchain.com → `code-chef-training`
- Filter: `environment:"training"`
- View: Training progress, model metrics

### Grafana Dashboards

- URL: https://appsmithery.grafana.net
- Dashboards:
  - LLM Token Metrics
  - Evaluation Performance Trends
  - Agent Routing Accuracy
  - Token Efficiency Over Time

### Linear Project

- URL: https://linear.app/dev-ops/project/codechef-78b3b839d36b
- Labels:
  - `evaluation` - Evaluation issues
  - `regression` - Performance regressions
  - `annotation` - Annotation tasks
  - `fine-tuning` - Model training

---

## Success Metrics

### Week 1 Success Criteria

- ✅ Baseline evaluation completed
- ✅ 15 new traces annotated (30 total)
- ✅ Dataset synced successfully
- ✅ Week 1 evaluation shows stable metrics
- ✅ Documented annotation workflow

### Week 2 Success Criteria

- ✅ 26 new traces annotated (56 total)
- ✅ GitHub Actions workflow enabled
- ✅ Automatic evaluation runs successfully
- ✅ Regression detection tested
- ✅ Ready for month 2 automation

### Month 2 Preparation

- [ ] 100+ total annotated examples
- [ ] Automated evaluation on every push
- [ ] Weekly dataset sync
- [ ] First fine-tuning run planned
- [ ] Cost optimization analysis

---

## Troubleshooting

### "Can't find traces in LangSmith"

**Check**:

1. Extension connected to orchestrator
2. LANGCHAIN_TRACING_V2=true in .env
3. LANGCHAIN_API_KEY set correctly
4. Project: code-chef-production selected

**Test**:

```bash
# Make a test request via extension
# Should appear in LangSmith within 30 seconds
```

### "Dataset sync finds no new examples"

**Check**:

1. Traces have correctness scores ≥ 0.7
2. Using correct project name: code-chef-production
3. Date range includes your annotations
4. Traces are recent (last 7 days)

**Debug**:

```bash
python support/scripts/evaluation/sync_dataset_from_annotations.py \
    --project code-chef-production \
    --dataset ib-agent-scenarios-v1 \
    --min-score 0.5 \  # Lower threshold to test
    --days-back 30 \
    --dry-run  # Preview without changes
```

### "Evaluation fails with timeout"

**Solution**:

```bash
# Reduce concurrency
python support/tests/evaluation/run_langsmith_evaluation.py \
    --dataset ib-agent-scenarios-v1 \
    --max-concurrency 2 \  # Reduce from 5
    --evaluators custom  # Skip LLM evaluators to save time
```

### "LLM evaluators return 0.0"

**Check**:

1. OPENAI_API_KEY set correctly
2. GPT-4 access enabled in OpenAI account
3. Sufficient API credits

**Test**:

```bash
python -c "from langchain_openai import ChatOpenAI; llm = ChatOpenAI(model='gpt-4'); print(llm.invoke('test').content)"
```

---

## Quick Commands Reference

```bash
# Run evaluation
python support/tests/evaluation/run_langsmith_evaluation.py \
    --dataset ib-agent-scenarios-v1 \
    --experiment-prefix uat-$(date +%Y%m%d)

# Sync dataset
python support/scripts/evaluation/sync_dataset_from_annotations.py \
    --project code-chef-production \
    --dataset ib-agent-scenarios-v1 \
    --min-score 0.7 \
    --days-back 7

# Check for regression
python support/scripts/evaluation/detect_regression.py \
    --results evaluation_results.json \
    --threshold 0.05 \
    --create-linear-issue

# View dataset examples
python -c "from langsmith import Client; c = Client(); examples = list(c.list_examples(dataset_name='ib-agent-scenarios-v1')); print(f'{len(examples)} examples'); [print(f'{i+1}. {e.inputs.get(\"query\", \"\")}') for i, e in enumerate(examples[:5])]"
```

---

## Resources

- **LangSmith**: https://smith.langchain.com
- **Grafana**: https://appsmithery.grafana.net
- **Linear**: https://linear.app/dev-ops/project/codechef-78b3b839d36b
- **HuggingFace Space**: https://huggingface.co/spaces/alextorelli/code-chef-modelops-trainer

- **Implementation Guide**: `LANGSMITH_INTEGRATION_COMPLETE.md`
- **Fix Summary**: `EVALUATION_SYSTEM_FIX.md`
- **Usage Guide**: `support/tests/evaluation/LANGSMITH_AUTOMATION_README.md`
- **LLM Operations**: `support/docs/operations/LLM_OPERATIONS.md`

---

## Notes

- **Annotation takes ~2 minutes per trace** (review + score + comment)
- **5 traces/day = 10 minutes/day**
- **Goal: 50+ examples in 2 weeks**
- **Quality > Quantity**: Focus on high-quality annotations (≥0.7)
- **Diverse categories**: Balance across agent routing, token efficiency, MCP integration, workflows

**Remember**: Every trace you annotate improves the system! 🚀

---

**Next Step**: Run the baseline evaluation command above and annotate your first 5 traces today! ✅
