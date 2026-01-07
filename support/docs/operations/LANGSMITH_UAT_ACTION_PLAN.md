# LangSmith UAT & Automation Action Plan

**Created**: January 6, 2026  
**Purpose**: Optimize LangSmith setup for production monitoring and continuous evaluation during UAT  
**References**:

- [LangSmith Evaluation Concepts](https://docs.langchain.com/langsmith/evaluation-concepts.md)
- [Online Evaluations](https://docs.langchain.com/langsmith/online-evaluations.md)
- [AgentEvals](https://github.com/langchain-ai/agentevals)
- [OpenEvals](https://github.com/langchain-ai/openevals)

---

## Current State Assessment

### ✅ What We Have

- **2 Datasets**: `ds-juicy-moai-98` (empty), `ib-agent-scenarios-v1` (15 examples)
- **0 Annotation Queues**: Need to create structured review queues
- **Tracing**: Enabled in production (`code-chef-production` project)
- **Scripts**:
  - `annotate_bug_traces.py` - Manual bug annotation ✅
  - `auto_annotate_traces.py` - Uncertainty sampling
  - `baseline_runner.py` - A/B testing runner
  - `export_training_dataset.py` - HuggingFace export
  - `sync_dataset_from_annotations.py` - Queue → Dataset sync
  - `detect_regression.py` - Longitudinal tracking

### ❌ What We're Missing

1. **Online Evaluators** - No automated evaluation on production traces
2. **Annotation Queues** - No structured human feedback collection
3. **Reference-Free Evaluators** - Safety, format, quality checks
4. **Agent Trajectory Evaluators** - Tool call validation from AgentEvals
5. **Automated Feedback Loop** - Traces → Annotations → Datasets → Training

---

## Recommended Structure

### Annotation Queues (Single Unified Queue)

**Recommendation**: Use **1 annotation queue** for UAT, not multiple

**Queue Name**: `uat-review-queue`

**Rationale**:

- Simpler workflow during UAT
- Easier to manage priorities
- Can tag traces by category after annotation
- Flexible - no need to pre-categorize

**Configuration**:

```yaml
queue: uat-review-queue
filters:
  - intent_confidence < 0.75 # Low-confidence intent classifications
  - errors IS NOT NULL # Any errors
  - latency_ms > 5000 # Slow responses
  - user_feedback.score < 0.5 # Negative user feedback (when available)
sampling_rate: 0.2 # Review 20% of matching traces
```

**Tags to Apply During Review**:

- `mcp-awareness` - Doesn't understand MCP tools
- `tool-usage` - Incorrect tool selection/invocation
- `routing` - Wrong agent selected
- `accuracy` - Factually incorrect response
- `formatting` - Output structure issues
- `latency` - Performance problems
- `edge-case` - Unusual input/scenario

### Datasets (Expand Existing)

**Dataset 1**: `error-cases-regression-suite` (NEW - create this)

- **Purpose**: Bug regression testing
- **Sources**: Annotated bug traces like we just created
- **Usage**: CI/CD regression tests before deployment

**Dataset 2**: `ib-agent-scenarios-v1` (EXISTING - expand)

- **Purpose**: Common agent scenarios (feature dev, code review, etc.)
- **Sources**: Real production traces + manual curation
- **Usage**: Offline evaluation before deploying changes

**Dataset 3**: `code-chef-gold-standard-v1` (NEW - create during UAT)

- **Purpose**: High-quality reference responses
- **Sources**: Annotated traces from `uat-review-queue`
- **Usage**: Training data + evaluation benchmark

---

## Phase 1: Setup Online Evaluators (Week 1)

### 1.1 Install AgentEvals Prebuilt Evaluators

<function_calls>
<invoke name="run_in_terminal">
<parameter name="command">cd D:\APPS\code-chef; .venv\Scripts\pip.exe install agentevals openevals
