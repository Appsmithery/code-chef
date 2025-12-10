#!/usr/bin/env python3
"""Update ModelOps Linear issues with revised HuggingFace MCP information."""

import os

import requests

LINEAR_API_KEY = os.environ.get("LINEAR_API_KEY")
if not LINEAR_API_KEY:
    print("❌ LINEAR_API_KEY environment variable not set")
    exit(1)

GRAPHQL_ENDPOINT = "https://api.linear.app/graphql"


def get_issue_id(identifier: str) -> str:
    """Get issue UUID from identifier like CHEF-210."""
    query = """
    query GetIssue($identifier: String!) {
        issue(id: $identifier) {
            id
            identifier
        }
    }
    """
    response = requests.post(
        GRAPHQL_ENDPOINT,
        headers={"Authorization": LINEAR_API_KEY, "Content-Type": "application/json"},
        json={"query": query, "variables": {"identifier": identifier}},
    )
    data = response.json()
    return data.get("data", {}).get("issue", {}).get("id")


def update_issue_description(issue_id: str, description: str) -> bool:
    """Update an issue's description."""
    mutation = """
    mutation UpdateIssue($issueId: String!, $description: String!) {
        issueUpdate(id: $issueId, input: { description: $description }) {
            success
            issue { identifier title }
        }
    }
    """
    response = requests.post(
        GRAPHQL_ENDPOINT,
        headers={"Authorization": LINEAR_API_KEY, "Content-Type": "application/json"},
        json={
            "query": mutation,
            "variables": {"issueId": issue_id, "description": description},
        },
    )
    result = response.json()
    return result.get("data", {}).get("issueUpdate", {}).get("success", False)


# Issue descriptions
CHEF_210_DESC = """## Phase 8: ModelOps Extension for Infrastructure Agent

Add ModelOps capabilities to the Infrastructure agent for fine-tuning subagent models.

### HuggingFace MCP Tools Available
- `model_search` - Find base models for fine-tuning
- `dataset_search` - Discover training datasets
- `hub_repo_details` - Get model/dataset metadata
- `space_search` / `dynamic_space` - Search and invoke Spaces
- `paper_search` - Search ML papers
- `hf_doc_search/fetch` - Documentation access

### Training Approach
- **Discovery**: MCP tools for model/dataset validation
- **Training**: AutoTrain Advanced (auto-configured, simplified)
- **Monitoring**: TensorBoard built-in monitoring
- **Conversion**: GGUF for local deployment
- **Development**: Can run locally OR on HF Spaces

### New Tools
- `train_subagent_model` - AutoTrain integration with demo/production modes
- `monitor_training_job` - AutoTrain API monitoring
- `evaluate_model_vs_baseline` - LangSmith comparison
- `deploy_model_to_agent` - Config updates + canary
- `convert_model_to_gguf` - Quantization for llama.cpp/Ollama

### Authentication
- GitHub Secret: `HUGGINGFACE_TOKEN` ✅ Configured

### Phases
1. **Registry + Training MVP** (CHEF-211) - AutoTrain integration, CSV export, registry
2. **Evaluation Integration** (CHEF-212) - LangSmith comparison
3. **Deployment Automation** (CHEF-213) - Config updates, canary
4. **UX Polish + GGUF** (CHEF-214) - VS Code commands, local deployment

**Spec Document**: [support/docs/extend Infra agent ModelOps.md](https://github.com/Appsmithery/Dev-Tools/blob/main/support/docs/extend%20Infra%20agent%20ModelOps.md)
**References**:
- [AutoTrain Advanced](https://github.com/huggingface/autotrain-advanced)
- [HF Skills Training](https://huggingface.co/blog/hf-skills-training)

---
*Created by 🏗️ Infrastructure [Infrastructure Agent]*
*Agent Tag: @infrastructure-agent*"""

CHEF_211_DESC = """## Phase 1: Registry + Training MVP

**Scope**: Core infrastructure for model versioning and AutoTrain integration

### Files to Create
- `agent_orchestrator/agents/infrastructure/modelops/__init__.py`
- `agent_orchestrator/agents/infrastructure/modelops/registry.py`
- `agent_orchestrator/agents/infrastructure/modelops/training.py`
- `config/models/registry.json`
- `config/modelops/training_defaults.yaml`

### Tasks
- [ ] Install AutoTrain Advanced: `pip install autotrain-advanced`
- [ ] Create `config/models/registry.json` schema
- [ ] Implement `modelops/registry.py` with CRUD operations
- [ ] Implement `modelops/training.py` with AutoTrain integration
- [ ] Add LangSmith to CSV export function (AutoTrain input format)
- [ ] Add `train_subagent_model` tool with demo/production modes
- [ ] Add `monitor_training_job` tool with AutoTrain API
- [ ] Create `config/modelops/training_defaults.yaml` (minimal config)
- [ ] Add HuggingFace tokens to `config/env/.env.template`
- [ ] Unit tests for registry and training
- [ ] Test local training on dev machine (optional)

### AutoTrain Integration
```python
from autotrain.trainers.clm import train as train_sft
from autotrain.trainers.dpo import train as train_dpo
from autotrain import AutoTrainConfig

HF_TOKEN = os.environ.get("HUGGINGFACE_TOKEN")

# Export LangSmith dataset to CSV (AutoTrain format)
dataset.to_csv("/tmp/training.csv", columns=["text", "response"])

# Configure AutoTrain (handles everything automatically)
config = AutoTrainConfig(
    project_name="code-chef-feature-dev-v2",
    model="Qwen/Qwen2.5-Coder-7B",
    data_path="/tmp/training.csv",
    text_column="text",
    target_column="response",
    
    # AutoTrain auto-configures:
    auto_find_batch_size=True,  # Optimal batch/GPU
    use_peft=True,               # LoRA auto-enabled
    quantization="int4",         # 4-bit training
    
    push_to_hub=True,
    repo_id="appsmithery/code-chef-feature-dev-v2",
    token=HF_TOKEN
)

# Submit (works locally OR on HF Spaces)
job = await train_sft(config)
tensorboard_url = job.tensorboard_url
```

### AutoTrain Benefits
- **Auto GPU selection**: t4-small for <1B, a10g-large for 3-7B
- **Auto LoRA config**: Enabled for >3B models automatically
- **Auto dataset validation**: Checks format, suggests fixes
- **Built-in monitoring**: TensorBoard auto-configured
- **Local OR cloud**: Test locally, deploy to Spaces

### Training Methods
- **SFT**: CSV with `text`, `response` columns
- **DPO**: CSV with `prompt`, `chosen`, `rejected` columns
- **Reward Modeling**: CSV with `text`, `score` columns

### Cost & Time (Same as Jobs API)
- **Demo**: 100 examples, 5 min, $0.50
- **Production**: Full dataset, 3 epochs, 90 min, $3.50-$15

**Estimated effort**: 2-3 days (reduced from 4-5 - AutoTrain simplifies)
**References**:
- [AutoTrain Advanced](https://github.com/huggingface/autotrain-advanced)
- [AutoTrain Docs](https://huggingface.co/docs/autotrain)

---
*Subtask 1 of 4 for Phase 8: ModelOps Extension for Infrastructure Agent*"""

CHEF_212_DESC = """## Phase 2: Evaluation Integration

**Scope**: LangSmith integration for model comparison

### Files to Create/Modify
- `agent_orchestrator/agents/infrastructure/modelops/evaluation.py`

### Tasks
- [ ] Implement `modelops/evaluation.py` using existing `support/tests/evaluation/evaluators.py`
- [ ] Add `evaluate_model_vs_baseline` tool
- [ ] Use MCP `hub_repo_details` to get fine-tuned model metadata
- [ ] Create evaluation comparison report format
- [ ] Add experiment tagging (agent, model_version, experiment_type)
- [ ] Unit tests for evaluation workflow

### Integration Points
- Existing evaluators: `agent_routing_accuracy`, `token_efficiency`, `latency_threshold`, etc.
- LangSmith Client pattern from `support/tests/evaluation/run_evaluation.py`
- HuggingFace MCP for model metadata retrieval

**Estimated effort**: 2-3 days

---
*Subtask 2 of 4 for Phase 8: ModelOps Extension for Infrastructure Agent*"""

CHEF_213_DESC = """## Phase 3: Deployment Automation

**Scope**: Automated config updates and canary deployments

### Files to Create/Modify
- `agent_orchestrator/agents/infrastructure/modelops/deployment.py`
- `config/agents/models.yaml` (update logic)

### Tasks
- [ ] Implement `modelops/deployment.py`
- [ ] Add `deploy_model_to_agent` tool
- [ ] Use MCP `hub_repo_details` to validate model before deployment
- [ ] Implement `config/agents/models.yaml` update logic
- [ ] Add canary traffic split configuration
- [ ] Implement rollback procedure
- [ ] Add `list_agent_models` tool
- [ ] Unit tests for deployment

### Deployment Targets
- OpenRouter (check model availability via API)
- HuggingFace Inference Endpoints
- Self-hosted endpoints

**Estimated effort**: 2-3 days

---
*Subtask 3 of 4 for Phase 8: ModelOps Extension for Infrastructure Agent*"""

CHEF_214_DESC = """## Phase 4: UX Polish + GGUF Support

**Scope**: VS Code extension commands, notifications, and local deployment

### Files to Create/Modify
- `extensions/vscode-codechef/package.json` (add commands)
- `extensions/vscode-codechef/src/commands/modelops.ts`
- `agent_orchestrator/agents/infrastructure/modelops/deployment.py` (add GGUF conversion)

### Tasks
- [ ] Add ModelOps commands to `extensions/vscode-codechef/package.json`
- [ ] Implement `src/commands/modelops.ts` handlers
- [ ] Add progress notifications for training jobs with Trackio links
- [ ] Use MCP `model_search` for model selection UI
- [ ] Add cost estimation display (demo vs production)
- [ ] Add model comparison UI with evaluation results
- [ ] Implement `convert_model_to_gguf` tool for local deployment
- [ ] Add usage instructions for llama.cpp, Ollama, LM Studio
- [ ] Integration tests

### New Commands
- `codechef.trainAgentModel` - Train Agent Model
- `codechef.evaluateAgentModel` - Evaluate Agent Model
- `codechef.deployAgentModel` - Deploy Model to Agent
- `codechef.listAgentModels` - List Agent Models
- `codechef.convertModelToGGUF` - Convert to GGUF (local deployment)

### GGUF Conversion
After training, convert to GGUF for local deployment:
```python
# Submit GGUF conversion job
conversion_job = requests.post(
    "https://huggingface.co/api/jobs/convert-gguf",
    json={
        "model_repo": "appsmithery/code-chef-feature-dev-v2",
        "quantization": "Q4_K_M",  # 4-bit, good balance
        "output_repo": "appsmithery/code-chef-feature-dev-gguf"
    }
)

# Use locally:
# llama-server -hf appsmithery/code-chef-feature-dev-gguf:Q4_K_M
```

### User Experience Flow
1. User: "@chef Train feature_dev model using recent traces"
2. Agent exports to CSV, AutoTrain validates format automatically
3. Estimate: "Demo: $0.50, 5 min | Prod: $3.50, 90 min"
4. Run demo → AutoTrain auto-selects GPU, configures LoRA
5. Progress via TensorBoard: "Training 45% (step 850/1200), loss: 1.23, ETA: 20 min"
6. Evaluation: "New model: +12% accuracy, 20% faster. Deploy?"
7. Canary deployment + monitoring
8. Optional: "Convert to GGUF for local testing?"

**Estimated effort**: 3-4 days
**References**:
- [AutoTrain Advanced](https://github.com/huggingface/autotrain-advanced)
- [HF Skills Training - GGUF](https://huggingface.co/blog/hf-skills-training#converting-to-gguf)

---
*Subtask 4 of 4 for Phase 8: ModelOps Extension for Infrastructure Agent*"""


def main():
    updates = [
        ("CHEF-210", CHEF_210_DESC),
        ("CHEF-211", CHEF_211_DESC),
        ("CHEF-212", CHEF_212_DESC),
        ("CHEF-213", CHEF_213_DESC),
        ("CHEF-214", CHEF_214_DESC),
    ]

    for identifier, description in updates:
        print(f"\n📝 Updating {identifier}...")
        issue_id = get_issue_id(identifier)
        if not issue_id:
            print(f"  ❌ Could not find issue {identifier}")
            continue

        if update_issue_description(issue_id, description):
            print(f"  ✅ Updated {identifier}")
        else:
            print(f"  ❌ Failed to update {identifier}")


if __name__ == "__main__":
    main()
