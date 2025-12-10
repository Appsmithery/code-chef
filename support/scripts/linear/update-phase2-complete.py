#!/usr/bin/env python3
"""Update CHEF-212 (Phase 2) to Done and prepare Phase 3."""

import os
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv("config/env/.env")
LINEAR_API_KEY = os.environ.get("LINEAR_CHEF_API_KEY") or os.environ.get(
    "LINEAR_API_KEY"
)
HEADERS = {"Authorization": LINEAR_API_KEY, "Content-Type": "application/json"}

GITHUB_BASE = "https://github.com/Appsmithery/Dev-Tools/blob/main"

CHEF_212_COMPLETE = f"""## ✅ Phase 2 COMPLETE - {datetime.now().strftime("%Y-%m-%d")}

### All Tasks Completed Successfully

**Registry Implementation:**
- ✅ Created `modelops/registry.py` ([link]({GITHUB_BASE}/agent_orchestrator/agents/infrastructure/modelops/registry.py))
  - ModelRegistry class with thread-safe CRUD operations
  - Pydantic validation for TrainingConfig, EvaluationScores, ModelVersion
  - Automatic backup with 10-version history
  - Version tracking: current, canary, archived states
  - Rollback and promotion operations

- ✅ Created `config/models/registry.json` ([link]({GITHUB_BASE}/config/models/registry.json))
  - Schema for 5 agents (feature_dev, code_review, infrastructure, cicd, documentation)
  - Current/canary/history tracking per agent
  - Training metadata and evaluation scores storage

**Evaluation Implementation:**
- ✅ Created `modelops/evaluation.py` ([link]({GITHUB_BASE}/agent_orchestrator/agents/infrastructure/modelops/evaluation.py))
  - ModelEvaluator class integrating with existing evaluators
  - compare_models() for baseline vs candidate comparison
  - Weighted improvement calculation (30% accuracy, 25% completeness, 20% efficiency, 15% latency, 10% integration)
  - Automatic recommendation generation (deploy, deploy_canary, reject, needs_review)
  - Markdown comparison report generation
  - LangSmith experiment tracking

**Testing:**
- ✅ Unit tests for registry ([link]({GITHUB_BASE}/support/tests/agents/infrastructure/modelops/test_registry.py))
  - 15 tests covering CRUD operations, validation, backup
  - All passing ✅
  
- ✅ Unit tests for evaluation ([link]({GITHUB_BASE}/support/tests/agents/infrastructure/modelops/test_evaluation.py))
  - 12 tests covering comparison, recommendation, reports
  - All passing ✅

**Total: 27/27 tests passing**

### Key Features Delivered

**Registry Operations:**
```python
registry = ModelRegistry()

# Add new version
registry.add_model_version(
    agent_name="feature_dev",
    version="v2.0.0",
    model_id="alextorelli/codechef-feature-dev-v2",
    training_config={{...}}
)

# Update eval scores
registry.update_evaluation_scores(
    agent_name="feature_dev",
    version="v2.0.0",
    eval_scores={{"accuracy": 0.87, ...}}
)

# Deploy as canary
registry.set_canary_model("feature_dev", "v2.0.0", canary_pct=20)

# Promote to current
registry.promote_canary_to_current("feature_dev")

# Rollback if needed
registry.rollback_to_version("feature_dev", "v1.0.0")
```

**Evaluation & Comparison:**
```python
evaluator = ModelEvaluator()

# Compare candidate vs baseline
comparison = evaluator.compare_models(
    agent_name="feature_dev",
    candidate_version="v2.0.0",
    baseline_version="v1.0.0"
)

# Get recommendation
print(comparison.recommendation)  # "deploy", "deploy_canary", "reject", "needs_review"
print(comparison.overall_improvement_pct)  # +12.5%
print(comparison.improvements)  # {{"accuracy": 16.0, "latency": 12.3, ...}}

# Generate markdown report
report = evaluator.generate_comparison_report(comparison)
```

**Recommendation Logic:**
- **Deploy**: >15% improvement, no critical degradations
- **Deploy Canary**: 5-15% improvement, validate with 20% traffic
- **Needs Review**: ±5% marginal change, manual review required
- **Reject**: <-5% regression OR >20% degradation in any metric OR min score <0.5

### Architecture Highlights

1. **Pydantic Validation**: All data validated at input (TrainingConfig, EvaluationScores, ModelVersion)
2. **Thread Safety**: File locking and atomic operations for registry updates
3. **Automatic Backups**: Last 10 versions preserved in `config/models/backups/`
4. **LangSmith Integration**: Experiments tagged with agent, version, experiment_type
5. **Existing Evaluators**: Reuses all evaluators from `support/tests/evaluation/evaluators.py`

### Integration Points

- ✅ Integrates with Phase 1 training infrastructure
- ✅ Uses existing LangSmith evaluation framework
- ✅ Ready for Phase 3 deployment automation

### 🎯 Next Steps

Moving to **CHEF-213 (Phase 3: Deployment Automation)**

**Phase 3 will add:**
1. Infrastructure agent integration (route ModelOps intents)
2. deployment.py module
3. deploy_model_to_agent tool
4. config/agents/models.yaml update automation
5. Canary traffic split implementation
6. Rollback procedures

**Status Change:** In Progress → Done ✅
"""

CHEF_213_READY = f"""## 📝 Phase 3 Ready to Start - {datetime.now().strftime("%Y-%m-%d")}

### Dependencies Satisfied

- ✅ Phase 1: Training infrastructure (DONE)
- ✅ Phase 2: Registry + Evaluation (DONE)

### Updated Task List

**Infrastructure Agent Integration:**
1. Update `agents/infrastructure/__init__.py` to route ModelOps intents
2. Add ModelOps tools to `agents/infrastructure/tools.yaml`
3. Update `agents/infrastructure/system.prompt.md` with ModelOps capabilities

**Deployment Module:**
4. Create `modelops/deployment.py`
5. Implement `deploy_model_to_agent` tool with registry integration
6. Implement `config/agents/models.yaml` update logic
7. Add canary traffic split configuration
8. Implement rollback procedure
9. Add `list_agent_models` tool

**Testing:**
10. Unit tests for deployment
11. Integration tests for end-to-end workflow

### Registry Integration

Phase 2 registry provides foundation for deployment:
- Track current/canary/history per agent
- Deployment status tracking (not_deployed, canary_20pct, deployed, archived)
- Rollback support with version history

### Available Deployment Targets

1. **OpenRouter**: Check model availability via API
2. **HuggingFace Inference Endpoints**: Direct model hosting
3. **Self-hosted endpoints**: Custom endpoints

### Canary Deployment Strategy

1. Deploy candidate to 20% of traffic
2. Monitor for 24-48 hours
3. Compare metrics vs baseline
4. Promote to 50%, then 100% if successful
5. Rollback immediately if degradation detected

### Estimated Effort

3-4 days

### Success Criteria

- Infrastructure agent routes ModelOps requests
- Models deployed via single command
- Canary deployments functional with traffic split
- Rollback works in <60 seconds
- Full integration tests passing
"""


def add_comment_and_update_status(issue_id: str, comment: str, new_status: str) -> bool:
    """Add comment and update status."""
    # Get issue UUID
    query = """
    query GetIssue($identifier: String!) {
        issue(id: $identifier) {
            id
            state { id name }
        }
    }
    """
    response = requests.post(
        "https://api.linear.app/graphql",
        headers=HEADERS,
        json={"query": query, "variables": {"identifier": issue_id}},
    )
    data = response.json().get("data", {}).get("issue", {})
    uuid = data.get("id")
    current_state_name = data.get("state", {}).get("name")

    if not uuid:
        print(f"❌ Issue {issue_id} not found")
        return False

    # Add comment
    comment_mutation = """
    mutation CreateComment($issueId: String!, $body: String!) {
        commentCreate(input: { issueId: $issueId, body: $body }) {
            success
        }
    }
    """
    response = requests.post(
        "https://api.linear.app/graphql",
        headers=HEADERS,
        json={
            "query": comment_mutation,
            "variables": {"issueId": uuid, "body": comment},
        },
    )

    if not response.json().get("data", {}).get("commentCreate", {}).get("success"):
        print(f"❌ Failed to add comment to {issue_id}")
        return False

    print(f"✅ Added comment to {issue_id}")

    # Update status if needed
    if new_status.lower() != current_state_name.lower():
        # Get state ID
        state_query = """
        query GetStates {
            workflowStates {
                nodes {
                    id
                    name
                }
            }
        }
        """
        response = requests.post(
            "https://api.linear.app/graphql",
            headers=HEADERS,
            json={"query": state_query},
        )
        states = (
            response.json().get("data", {}).get("workflowStates", {}).get("nodes", [])
        )
        state_id = next(
            (s["id"] for s in states if s["name"].lower() == new_status.lower()), None
        )

        if state_id:
            update_mutation = """
            mutation UpdateIssue($id: String!, $stateId: String!) {
                issueUpdate(id: $id, input: { stateId: $stateId }) {
                    success
                }
            }
            """
            response = requests.post(
                "https://api.linear.app/graphql",
                headers=HEADERS,
                json={
                    "query": update_mutation,
                    "variables": {"id": uuid, "stateId": state_id},
                },
            )

            if response.json().get("data", {}).get("issueUpdate", {}).get("success"):
                print(
                    f"✅ Updated {issue_id} status: {current_state_name} → {new_status}"
                )
            else:
                print(f"❌ Failed to update status for {issue_id}")

    return True


def main():
    if not LINEAR_API_KEY:
        print("❌ LINEAR_API_KEY not found in environment")
        return

    print("📝 Updating Linear issues for Phase 2 completion...\n")

    # Mark Phase 2 complete
    print("Updating CHEF-212 (Phase 2)...")
    add_comment_and_update_status("CHEF-212", CHEF_212_COMPLETE, "Done")

    # Update Phase 3
    print("\nUpdating CHEF-213 (Phase 3)...")
    add_comment_and_update_status("CHEF-213", CHEF_213_READY, "Todo")

    print("\n✅ Phase 2 complete!")
    print("→ Ready to start Phase 3: Deployment Automation")


if __name__ == "__main__":
    main()
