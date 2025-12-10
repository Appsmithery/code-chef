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
Training uses `huggingface_hub` SDK + AutoTrain API (MCP provides discovery/validation)

### Authentication
- GitHub Secret: `HUGGINGFACE_TOKEN` ✅ Configured

### Phases
1. **Registry + Training MVP** (CHEF-211)
2. **Evaluation Integration** (CHEF-212)
3. **Deployment Automation** (CHEF-213)
4. **UX Polish** (CHEF-214)

**Spec Document**: [support/docs/extend Infra agent ModelOps.md](https://github.com/Appsmithery/Dev-Tools/blob/main/support/docs/extend%20Infra%20agent%20ModelOps.md)

---
*Created by 🏗️ Infrastructure [Infrastructure Agent]*
*Agent Tag: @infrastructure-agent*"""

CHEF_211_DESC = """## Phase 1: Registry + Training MVP

**Scope**: Core infrastructure for model versioning and HuggingFace training

### Files to Create
- `agent_orchestrator/agents/infrastructure/modelops/__init__.py`
- `agent_orchestrator/agents/infrastructure/modelops/registry.py`
- `agent_orchestrator/agents/infrastructure/modelops/training.py`
- `config/models/registry.json`
- `config/modelops/training_defaults.yaml`

### Tasks
- [ ] Create `config/models/registry.json` schema with current/history structure
- [ ] Implement `modelops/registry.py` with CRUD operations
- [ ] Implement `modelops/training.py` with HuggingFace Hub SDK integration
- [ ] Use MCP `model_search` to validate base models exist
- [ ] Use MCP `dataset_search` to discover relevant training datasets
- [ ] Add `train_subagent_model` tool
- [ ] Add `monitor_training_job` tool
- [ ] Add HuggingFace tokens to `config/env/.env.template`
- [ ] Unit tests for registry and training

### HuggingFace MCP Usage
```python
# Validate base model exists
model_info = mcp_huggingface_model_search(query="Qwen2.5-Coder-7B")

# Get detailed model config
details = mcp_huggingface_hub_repo_details(repo_ids=["Qwen/Qwen2.5-Coder-7B"])

# Search for training datasets
datasets = mcp_huggingface_dataset_search(query="code generation")
```

**Estimated effort**: 3-4 days

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

CHEF_214_DESC = """## Phase 4: UX Polish

**Scope**: VS Code extension commands and notifications

### Files to Create/Modify
- `extensions/vscode-codechef/package.json` (add commands)
- `extensions/vscode-codechef/src/commands/modelops.ts`

### Tasks
- [ ] Add ModelOps commands to `extensions/vscode-codechef/package.json`
- [ ] Implement `src/commands/modelops.ts` handlers
- [ ] Add progress notifications for training jobs
- [ ] Use MCP `model_search` for model selection UI
- [ ] Add cost estimation display
- [ ] Add model comparison UI
- [ ] Integration tests

### New Commands
- `codechef.trainAgentModel`
- `codechef.evaluateAgentModel`
- `codechef.deployAgentModel`
- `codechef.listAgentModels`

**Estimated effort**: 2-3 days

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
