#!/usr/bin/env python3
"""Add Phase 2 completion details and Phase 3 enhancements to Linear."""

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

CHEF_212_ADDENDUM = f"""## 📊 Additional Details - {datetime.now().strftime("%Y-%m-%d")}

### Dataset Strategy Integration

**Phase 1 (Current)**: Bootstrap with public HuggingFace datasets
- Generic code datasets (bigcode/the-stack-dedup, etc.)
- Establishes baseline performance
- Training works immediately

**Phase 2 (3-6 months)**: Hybrid approach
- 80% public datasets + 20% LangSmith traces
- Filter criteria: `success=True`, `feedback_score>=4.0`, `hitl_approved=True`
- Captures: workflow patterns, tool usage sequences, multi-agent handoffs
- Expected: +15-25% improvement over generic baseline

**Phase 3 (6-12 months)**: Proprietary LangSmith datasets
- 100% real code-chef workflow traces
- Target: 10,000+ examples per agent
- Production-validated, domain-specific
- Expected: +40-60% improvement over generic models

**Data Collection Infrastructure** (already in place):
- All workflow executions traced via `@traceable` decorator
- HITL approval status captured
- User feedback scores tracked
- Post-deployment validation tags

### Versioning & Naming Conventions

**Version Format**:
```
{{semantic-version}}-{{suffix}}

Examples:
- v1.0.0            # Baseline production
- v2.0.0            # Major update
- v1.1.0            # Minor update (dataset/hyperparams)
- v2.0.0-demo      # Demo training run
- v2.1.0-sft       # Training method indicator
```

**Model ID Format** (HuggingFace repos):
```
{{org}}/codechef-{{agent}}-{{descriptor}}

Examples:
- alextorelli/codechef-feature-dev-v2
- alextorelli/codechef-code-review-security
- appsmithery/codechef-cicd-optimized
```

**Deployment Status Lifecycle**:
```
not_deployed → canary_20pct → canary_50pct → deployed → archived
                     ↓              ↓            ↓
                  rollback ←────────┴────────────┘
```

**Registry Metadata** (per version):
- Training lineage: base_model, training_method, dataset IDs
- Evaluation scores: all metrics + baseline_improvement_pct
- Deployment tracking: status, deployed_at, rollback history
- Audit trail: trained_at, trained_by, job_id, hub_repo

### Phase 3 Enhancements Planned

**Auto-versioning**:
- `generate_next_version(agent_name, change_type)` - Auto-increment semantic versions
- Supports: major, minor, patch bumps

**Naming Validation**:
- `validate_model_id()` - Enforce org/codechef-{{agent}}-suffix format
- Prevents deployment of incorrectly named models

**Version Lineage**:
- Track parent_version (what this was fine-tuned from)
- Branch support (main, experimental, security)
- Tag system for marking production-ready models

**Changelog Tracking**:
- Auto-generate release notes from training config changes
- Capture: dataset updates, hyperparameter changes, eval improvements
"""

CHEF_213_ENHANCEMENT = f"""## 🔧 Phase 3 Scope Enhancements - {datetime.now().strftime("%Y-%m-%d")}

### Updated from Phase 2 Learnings

**Enhanced Task List**:

**1-3. Infrastructure Agent Integration** (from Phase 1 deferral):
- Route ModelOps intents through Infrastructure agent
- Add tools to `tools.yaml` with progressive loading
- Update `system.prompt.md` with ModelOps capabilities

**4-9. Deployment Module** (core Phase 3):
- `deployment.py` with registry integration
- `deploy_model_to_agent` tool
- `config/agents/models.yaml` atomic updates
- Canary traffic split: 20% → 50% → 100%
- Rollback procedure (<60 seconds)
- `list_agent_models` tool

**10-12. Versioning Enhancements** (informed by Phase 2 registry design):
- Auto-increment version generator
- Model ID naming convention validator
- Version comparison helper (`is_newer_than()`)

**13-14. Testing** (comprehensive):
- Unit tests for deployment operations
- Integration tests: train → evaluate → deploy → rollback

### Registry Integration Points

Phase 2 registry provides these deployment foundations:

**Version Tracking**:
- `current` - Currently deployed model (100% traffic)
- `canary` - Testing model (20%/50% traffic)
- `history` - Full version lineage with rollback support

**Deployment Operations** (already implemented):
- `set_canary_model(agent, version, canary_pct)` - Deploy to partial traffic
- `promote_canary_to_current(agent)` - Full rollout
- `rollback_to_version(agent, version)` - Instant revert
- `get_current_model(agent)` - Query live version
- `list_versions(agent, limit, status_filter)` - Version history

**Status Tracking**:
- `not_deployed` - Trained but not live
- `canary_20pct` - Testing with 20% traffic
- `canary_50pct` - Expanded testing
- `deployed` - Full production (100% traffic)
- `archived` - Replaced by newer version

### Deployment Targets

**1. OpenRouter** (primary):
- Check model availability via API models list
- Update `config/agents/models.yaml` under `openrouter.agent_models`
- Restart orchestrator container or hot-reload

**2. HuggingFace Inference Endpoints**:
- Deploy via HF Inference API
- Update endpoint URL in models.yaml
- Supports custom models not on OpenRouter

**3. Self-hosted endpoints**:
- Deploy to local inference server
- Custom endpoint configuration
- Full control over resources

### Canary Deployment Workflow

```
1. Evaluate model → recommendation = "deploy_canary"
2. deploy_model_to_agent(agent, version, strategy="canary_20pct")
3. Registry: deployment_status = "canary_20pct", deployed_at = now()
4. Update models.yaml with traffic split config
5. Tag requests in LangSmith with model_version
6. Monitor for 24-48 hours
7. Compare canary metrics vs baseline
8. If successful: promote_canary_to_current(agent)
9. If degradation: rollback_to_version(agent, previous_version)
```

### Success Metrics

- Model deployment completes in <60 seconds
- Canary traffic split verified in LangSmith traces (20%/80% ratio)
- Rollback completes in <30 seconds
- Zero-downtime deployments
- Full audit trail in registry + LangSmith

### Demo Scenario

User: `@chef Deploy feature_dev v2.0.0 as canary`

Infrastructure agent → ModelOps deployment:
1. Validate: v2.0.0 exists in registry with eval_scores
2. Check: eval_scores show +12% improvement over baseline
3. Deploy: Update models.yaml with 20% traffic split
4. Registry: Mark as canary_20pct
5. Monitor: Tag all feature_dev requests with model_version
6. Report: "Deployed to 20% canary. Monitor for 24h, then promote?"

After 24h of successful canary:
User: `@chef Promote feature_dev canary to production`

1. Verify: Canary metrics stable or improved
2. Promote: Update to 100% traffic
3. Archive: Old version marked as archived
4. Report: "v2.0.0 now serving 100% of traffic. Old version archived."
"""


def add_comment(issue_id: str, comment: str) -> bool:
    """Add comment to Linear issue."""
    # Get issue UUID
    query = """
    query GetIssue($identifier: String!) {
        issue(id: $identifier) {
            id
        }
    }
    """
    response = requests.post(
        "https://api.linear.app/graphql",
        headers=HEADERS,
        json={"query": query, "variables": {"identifier": issue_id}},
    )
    uuid = response.json().get("data", {}).get("issue", {}).get("id")

    if not uuid:
        print(f"❌ Issue {issue_id} not found")
        return False

    # Add comment
    mutation = """
    mutation CreateComment($issueId: String!, $body: String!) {
        commentCreate(input: { issueId: $issueId, body: $body }) {
            success
        }
    }
    """
    response = requests.post(
        "https://api.linear.app/graphql",
        headers=HEADERS,
        json={"query": mutation, "variables": {"issueId": uuid, "body": comment}},
    )

    success = response.json().get("data", {}).get("commentCreate", {}).get("success")
    if success:
        print(f"✅ Added details to {issue_id}")
    else:
        print(f"❌ Failed to add comment to {issue_id}")

    return success


def main():
    if not LINEAR_API_KEY:
        print("❌ LINEAR_API_KEY not found")
        return

    print("📝 Adding dataset strategy and versioning details to Linear...\n")

    # Add to Phase 2 (CHEF-212)
    print("Updating CHEF-212 (Phase 2) with dataset strategy...")
    add_comment("CHEF-212", CHEF_212_ADDENDUM)

    # Add to Phase 3 (CHEF-213)
    print("\nUpdating CHEF-213 (Phase 3) with enhanced scope...")
    add_comment("CHEF-213", CHEF_213_ENHANCEMENT)

    print("\n✅ Linear issues updated with:")
    print("  - Dataset evolution strategy (3 phases)")
    print("  - Versioning and naming conventions")
    print("  - Registry metadata structure")
    print("  - Phase 3 enhancements from Phase 2 learnings")


if __name__ == "__main__":
    main()
