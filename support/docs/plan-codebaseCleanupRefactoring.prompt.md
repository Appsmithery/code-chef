# Plan: Codebase Cleanup - Comprehensive Refactoring Audit

This research identifies all deprecated code, MCP gateway references, canary deployment logic, tracing patterns, and provides a prioritized removal/refactoring plan for the code-chef repository.

## Steps

1. **Generate detailed deprecated code inventory** with exact file paths, line numbers, and dependency mappings for safe removal candidates
2. **Map all MCP gateway references** distinguishing between already-deprecated locations and active code requiring terminology updates
3. **Document complete canary deployment removal scope** including registry methods, evaluation logic, tests, documentation, and configuration files
4. **Analyze LangSmith @traceable decorator usage** across ModelOps workflows to identify potential trace contamination between training, evaluation, and testing
5. **Create risk-stratified cleanup roadmap** with dependency trees and removal order recommendations

## Further Considerations

1. **Verify replacement terminology** - What should "mcp-gateway" become in active code? Options: "mcp-server", "mcp-bridge", "mcp-toolkit"
2. **Backup strategy** - Should we archive removed canary code to `_archive/` or delete entirely given Git history?
3. **Testing requirements** - After canary removal, which tests need updating vs deletion?

---

## Comprehensive Research Report: Code-Chef Cleanup Audit

### 1. DEPRECATED CODE AUDIT

#### A. Fully Deprecated Files (Safe to Delete)

**Packages (Already marked deprecated):**
- `packages/MCP_GATEWAY_IMPLEMENTATION_GAP.md` - DEPRECATED package 
- `packages/GITHUB_PACKAGES_INSTALL.md` - DEPRECATED package 
- `packages/mcp-bridge-client/` - Entire NPM package deprecated
- `packages/mcp-bridge-client-py/` - Entire Python package deprecated
- `packages/test-packages.ps1` - Documentation explaining why packages deprecated

**Gateway (Archived December 2025):**
- `shared/gateway/` - Entire directory deprecated Dec 3, 2025
- `_archive/gateway-deprecated-2025-12-03/` - States "Deprecated: December 3, 2025" with archive reference

**Scripts:**
- `support/scripts/fix_deprecated_imports.py` - Tool that itself fixes deprecated imports (meta-deprecated)
- `support/scripts/analyze_deprecated_paths.py` - Analyzes deprecated path references

**Documentation:**
- 13+ files in `_archive/docs-temp/` marked as DEPRECATED in `support/docs/README.md`
- `support/docs/_temp/` - Contains deprecated pre-flight checklists and migration docs

**Environment Variables:**
- `DIGITALOCEAN_KNOWLEDGE_BASE_*` - DEPRECATED in `config/env/.env.template`, collection deleted Jan 2025
- Legacy Qdrant vars - DEPRECATED in `config/env/README.md`

#### B. Active Code with Deprecated References (Needs Refactoring)

**Memory Classes:**
- `shared/lib/langchain_memory.py` - Uses simplified memory because LangChain memory classes deprecated in v0.2+
  - Contains 5 warnings about deprecated memory classes
  - **Recommendation**: Replace with `shared/lib/agent_memory.py` (already implemented replacement)

**Frontend:**
- `support/frontend/deprecated/` - Old static HTML files from frontend-v3
  - Referenced in `support/frontend/README.md`
  - **Status**: Safe to keep archived for reference

#### C. Dependencies with No Downstream Usage (Safe Removal Candidates)

**Test Files Referencing Deprecated Gateway:**
- `support/tests/integration/test_mcp_gateway.py` - File doesn't exist but referenced in:
  - `support/tests/conftest.py`
  - `support/tests/README.md`
- `support/tests/integration/test_mcp_client.py` - Contains `test_gateway_health` method
  - **Recommendation**: Remove test method or update to test new MCP Docker toolkit

---

### 2. MCP GATEWAY REFERENCES AUDIT

#### A. Already-Deprecated Files (Remove During Cleanup)

**Gateway Service Code:**
- `shared/gateway/__init__.py`
- `shared/gateway/main.py`
- `shared/gateway/routes.py`
- Gateway deprecated Dec 3, 2025

**Configuration:**
- `config/rag/indexing.yaml` - `gateway_endpoint: "docker://central-mcp-gateway"`

#### B. Active Code Requiring Terminology Updates

**Service Files (Need MCP_GATEWAY_URL variable updates):**

1. `shared/services/rag/main.py`
   - Line 46: `MCP_GATEWAY_URL = os.getenv("MCP_GATEWAY_URL")`
   - Lines 132, 492, 504, 505: Multiple references to `MCP_GATEWAY_URL`
   - **Impact**: RAG service health checks and tool invocation
   - **Recommendation**: Remove or redirect to Docker MCP toolkit

2. `shared/services/langgraph/main.py` + `src/main.py`
   - Lines 91, 131-132, 135: Health check includes `mcp_gateway` status field
   - **Impact**: Service health endpoint response format
   - **Recommendation**: Replace with `mcp_docker_toolkit_status`

3. `shared/lib/mcp_client.py`
   - Line 88: `gateway_url = os.getenv("MCP_GATEWAY_URL")`
   - **Impact**: MCP client initialization
   - **Recommendation**: Update to use Docker MCP toolkit discovery

**Documentation (26 references):**

All require "mcp-gateway" → "docker-mcp-toolkit" updates:

- `support/docs/DEPLOYMENT.md` - 9 references (lines 312, 332, 338, 566, 577, 653, 658, 666, 678, 689)
- `support/docs/ARCHITECTURE.md` - 2 references (lines 22, 187)
- `support/docs/integrations/langsmith-tracing.md` - States "MCP Gateway (port 8000) is deprecated"
- `support/docs/observability/monitoring.md` - 2 references
- `shared/services/rag/README.md`
- `shared/services/langgraph/README.md` - 2 references
- `agent_orchestrator/agents/infrastructure/README.md` - 2 references

**Environment Templates:**
- `config/env/.env.template` - `MCP_GATEWAY_URL=http://localhost:8000`
- `deploy/.env.template` - Same variable

**Scripts:**
- `support/scripts/validate_environment.py` - Lines 216-235: Checks for `mcp-gateway` in services
- `support/scripts/env_to_config.py` - Lines 112, 155: Includes `MCP_GATEWAY_URL` in env grep
- `support/scripts/analyze_deprecated_paths.py` - Lines 7, 18: References `/opt/central-mcp-gateway/servers/`

**Monitoring:**
- `config/prometheus/alerts.yml` - Alert: `MCPGatewayDown`
- `config/grafana/dashboards/system-health.json` - References alert

**Agent Documentation:**
- `agent_orchestrator/agents/supervisor/system.prompt.md` - Health endpoint example includes `mcp_gateway`

#### C. Correct Replacement Terminology

**Decision needed**: What replaces "mcp-gateway"? --> use "mcp-docker-toolkit"

Current implementation suggests: **"Docker MCP Toolkit"** or **"mcp-docker-toolkit"**

Evidence:
- `support/docs/integrations/langsmith-tracing.md` - "MCP Gateway (8000) deprecated - tools accessed via Docker MCP Toolkit in VS Code"
- `support/docs/DEPLOYMENT.md` - Same reference
- Extensions now use VS Code MCP Docker extension instead of gateway

---

### 3. CANARY DEPLOYMENT REMOVAL AUDIT

#### A. Core Implementation Files (Remove Canary Logic)

**Registry Module** - `agent_orchestrator/agents/infrastructure/modelops/registry.py`

Lines requiring removal:
- **Line 6**: Doc comment mentions "canary" in deployment status
- **Line 91**: `"not_deployed", "canary_20pct", "canary_50pct", "deployed", "archived"` - Remove canary statuses
- **Line 102**: `canary: Optional[AgentModelRef]` - Remove canary field from `AgentData` Pydantic model
- **Lines 161, 167, 173, 179, 185**: Initialization code sets `canary=None` for all agents
- **Line 234**: Doc comment mentions "current/canary/history"
- **Lines 381-432**: **ENTIRE METHOD** `set_canary_model()` - 52 lines
  - Decorated with `@traceable`
  - Accepts `traffic_percent` parameter (20 or 50)
  - Sets deployment_status to `canary_20pct`
  - Manages canary field in registry
- **Lines 434-481**: **ENTIRE METHOD** `promote_canary_to_current()` - 48 lines
  - Decorated with `@traceable`
  - Promotes canary to 100% traffic
  - Clears canary field after promotion
- **Lines 555-565**: **ENTIRE METHOD** `get_canary_model()` - 11 lines
  - Returns current canary model for an agent

**Total Removal**: ~115 lines in `registry.py`

**Evaluation Module** - `agent_orchestrator/agents/infrastructure/modelops/evaluation.py`

Lines requiring removal:
- **Line 77**: `Literal["deploy", "deploy_canary", "needs_review", "reject"]` - Remove `"deploy_canary"` from literal
- **Line 257**: Return value includes `recommendation="deploy_canary"`
- **Line 258**: Reasoning text mentions "canary deployment"
- **Lines 431-432**: Logic returns `"deploy_canary"` for moderate improvements (5-15%)
- **Line 525**: `elif comparison.recommendation == "deploy_canary":`
- **Line 526**: Report text: `"1. 🚦 Deploy to 20% canary\n"`

**Total Removal**: ~10 lines (change logic, remove one recommendation option)

**Deployment Module** - `agent_orchestrator/agents/infrastructure/modelops/deployment.py`

Lines requiring review:
- **Line 5**: Doc comment: "Canary deployments with traffic splitting"
- **Line 53**: Class doc: "Manages model deployment, canary rollouts, and rollbacks"
- Search through entire file for canary-specific deployment logic

**Coordinator Module** - `agent_orchestrator/agents/infrastructure/modelops/coordinator.py`

Lines requiring removal:
- **Line 182**: Doc comment mentions `"deploy_canary"` recommendation
- **Line 264**: Doc mentions rollout strategies: "canary_20pct, or canary_50pct"
- **Lines 448-452**: Status check includes canary_model field:
```python
if agent_data and agent_data.canary:
    result["canary_model"] = {
        "version": agent_data.canary.version,
        "model_id": agent_data.canary.model_id,
        "deployment_status": agent_data.canary.deployment_status,
```

#### B. Test Files (Remove or Update)

**Registry Tests** - `support/tests/agents/infrastructure/modelops/test_registry.py`

Lines requiring removal:
- **Line 78**: Assert `canary=None`
- **Lines 154-173**: **ENTIRE TEST** `test_set_canary_model` - 20 lines
  - Tests 20% canary deployment
  - Verifies canary field and deployment_status
- **Lines 174-204**: **ENTIRE TEST** `test_promote_canary_to_current` - 31 lines
  - Tests canary promotion to current
  - Verifies canary field cleared after promotion

**Total Removal**: 2 complete test methods (~51 lines)

**Evaluation Tests** - `support/tests/agents/infrastructure/modelops/test_evaluation.py`

Lines requiring removal/update:
- **Line 110**: Assert includes `"deploy_canary"` as valid recommendation
- **Line 187**: Assert `== "deploy_canary"`
- **Line 210**: Assert `== "deploy_canary"`
- **Line 313**: Mock data includes `recommendation="deploy_canary"`
- **Line 319**: Assert `== "deploy_canary"`

**Total Changes**: 5 assertions/test data points

**Deployment Tests** - Need to audit `support/tests/agents/infrastructure/modelops/test_deployment.py` for canary-specific tests

#### C. Documentation (26+ references)

**Primary Documentation** - `support/docs/extend Infra agent ModelOps.md`

Critical lines:
- **Line 183**: Tool input mentions `rollout_strategy`: `immediate` or `canary_20pct`
- **Line 197**: Implementation step 4: "If canary: Create traffic split config"
- **Line 279**: JSON schema example shows `deployment_status: "canary_20pct"`
- **Line 289**: Lifecycle mentions `canary_20pct` → `canary_50pct` statuses
- **Line 375**: Recommendation: "Deploy Canary" for 5-15% improvement
- **Line 614**: Workflow example: "Deploy to 20% canary?"
- **Line 652**: Version tracking mentions "canary" states
- **Line 685**: Automatic recommendations include "deploy_canary"
- **Line 713**: **Already marked removed**: "Done - 2025-12-10 (Simplified - no canary deployment)"
- **Line 733**: "Removed canary deployment documentation"
- **Line 747**: Checklist item marked REMOVED
- **Line 784**: Canary deployments marked REMOVED
- **Line 789**: "2 days (including canary removal refactor)"
- **Line 791**: "Key Simplification: Removed canary deployment"
- **Line 880**: Example workflow mentions canary

**Status**: Partially cleaned, but still contains ~15 canary references that need full removal

**Other Documentation:**
- `.github/copilot-instructions.md` - "Automatic recommendations: deploy, deploy_canary"
- `agent_orchestrator/agents/infrastructure/README.md` - Deployment strategies include "canary"
- `support/docs/ARCHITECTURE.md` - Lists "deploy_canary" in recommendations
- Various READMEs - May reference canary in examples

**Linear Scripts** (10+ files with canary references):
- All scripts in `support/scripts/linear/` mentioning canary deployment workflows
- Includes demo scripts, phase update scripts, issue update scripts
- **Recommendation**: Remove canary mentions or mark as historical context

#### D. Configuration Files

**Registry Data** - `config/models/registry.json`

Lines requiring cleanup:
- **Line 10**: `"canary": null` - Contains actual canary deployment data for feature_dev
- **Line 41**: `"deployment_status": "canary_20pct"`
- **Line 77**: History entry with `"deployment_status": "canary_20pct"`
- **Lines 119, 194, 200, 206**: Other agents have `"canary": null`

**Action**: Remove canary field from all agent entries, update schema validation

---

### 4. TRACING CONTAMINATION ANALYSIS

#### A. LangSmith @traceable Decorator Coverage

**Total Decorators Found**: 133 matches across codebase

**Project Separation**:
Per `.github/copilot-instructions.md`:
- Separate projects per agent: `code-chef-feature-dev`, `code-chef-code-review`, etc.
- Each agent has dedicated LangSmith project
- 33+ traceable decorators ensure observability

#### B. ModelOps Training Workflow Tracing

**Training Module** - `agent_orchestrator/agents/infrastructure/modelops/training.py`

Decorators found:
- **Line 101**: `@traceable(name="modelops_health_check")`
- **Line 116**: `@traceable(name="modelops_space_status")`
- **Line 181**: `@traceable(name="modelops_train_model")`
- **Line 199**: `@traceable(name="modelops_validate_training_config")`
- **Line 302**: `@traceable(name="modelops_estimate_cost")`
- **Line 376**: `@traceable(name="modelops_submit_job")`
- **Line 486**: `@traceable(name="modelops_get_training_status")`

**Tags**: No tags specified - **ISSUE**: Training traces not tagged separately from production

**Current Behavior**: Training operations trace to Infrastructure agent's project (`code-chef-infrastructure`)

**Risk**: Training job monitoring contaminating production infrastructure traces

#### C. ModelOps Evaluation Workflow Tracing

**Evaluation Module** - `agent_orchestrator/agents/infrastructure/modelops/evaluation.py`

Decorators found:
- **Line 128**: `@traceable(name="modelops_evaluate_models")`
- **Line 211**: `@traceable(name="modelops_compare_models")`
- **Line 445**: `@traceable(name="modelops_run_evaluation_suite")`
- **Line 545**: `@traceable(name="modelops_generate_comparison_report")`

**Tags**: No tags specified - **ISSUE**: Evaluation traces mixed with production

**Current Behavior**: Evaluation runs appear in Infrastructure agent project

**Risk**: Evaluation dataset runs contaminating production metrics

#### D. ModelOps Registry Tracing

**Registry Module** - `agent_orchestrator/agents/infrastructure/modelops/registry.py`

Decorators found (9 total):
- Lines 226, 244, 293, 326, 381, 434, 482, 496, 524
- All named `registry_*` operations
- **No tags specified**

**Risk**: Registry CRUD operations mixed with production infrastructure operations

#### E. ModelOps Coordinator Tracing

**Coordinator Module** - `agent_orchestrator/agents/infrastructure/modelops/coordinator.py`

Decorators found (8 total):
- **Lines 40, 100, 163, 256, 307, 341, 372, 421**
- All named `modelops_*` operations
- **No tags specified**

**Risk**: ModelOps orchestration traces in main Infrastructure project

#### F. HuggingFace Space Client Tracing

**Space Client Example** - `test_modelops_space.py`

Decorators found:
- **Line 32**: `@traceable`
- **Line 77**: `@traceable`
- **Line 94**: `@traceable`

**Tags**: No tags - **ISSUE**: External training client not isolated

#### G. Testing Infrastructure Tracing

**Workflow Tests** - Multiple test files with traceable decorators:

1. `support/tests/e2e/test_template_workflow_e2e.py` - 4 decorators (lines 19, 43, 69, 96)
2. `support/tests/e2e/test_review_workflow.py` - 4 decorators (lines 23, 48, 80, 117)
3. `support/tests/e2e/test_feature_workflow.py` - 4 decorators (lines 20, 42, 86, 117)

**Tags**: All include `tags=["test", "e2e"]`

**Issue**: No `environment="test"` or `test_run=True` tag to separate test runs from production

#### H. Recommended Tag Strategy

**Current State**: No environment separation in ModelOps traces

**Recommended Tag Structure**:

```python
# Training operations
@traceable(
    name="modelops_train_model",
    tags=["modelops", "training", "infrastructure"],
    metadata={"environment": "training", "agent": agent_name}
)

# Evaluation operations
@traceable(
    name="modelops_evaluate_model", 
    tags=["modelops", "evaluation", "infrastructure"],
    metadata={"environment": "evaluation", "agent": agent_name}
)

# Test operations
@traceable(
    name="test_modelops_workflow",
    tags=["test", "modelops", "infrastructure"],
    metadata={"environment": "test", "test_run": True}
)

# Production operations
@traceable(
    name="modelops_deploy_model",
    tags=["modelops", "deployment", "infrastructure"],
    metadata={"environment": "production", "agent": agent_name}
)
```

**Benefits**:
- Filter traces by environment in LangSmith
- Separate training metrics from production
- Prevent test contamination
- Enable per-environment cost tracking

---

### 5. FILE STRUCTURE ANALYSIS & DEPENDENCY MAPS

#### A. Safe to Delete (No Active Dependencies)

**Complete Removal Candidates** (45+ files/directories):

1. **Gateway Infrastructure** (~10 files)
   - `shared/gateway/` (entire directory)
   - `_archive/gateway-deprecated-2025-12-03/` (entire directory)
   - `_archive/gateway-deprecated-2025-12-03/` (if exists)

2. **Deprecated Packages** (~50+ files)
   - `packages/mcp-bridge-client/` (NPM package)
   - `packages/mcp-bridge-client-py/` (Python package)
   - `packages/MCP_GATEWAY_IMPLEMENTATION_GAP.md`
   - `packages/GITHUB_PACKAGES_INSTALL.md`

3. **Deprecated Documentation** (13+ files)
   - All files marked DEPRECATED in `support/docs/README.md`
   - `support/docs/_temp/` directory contents
   - `_archive/docs-temp/` directory contents

4. **Deprecated Scripts** (2 files)
   - `support/scripts/fix_deprecated_imports.py`
   - `support/scripts/analyze_deprecated_paths.py`

5. **Test Files** (1-2 files)
   - `support/tests/integration/test_mcp_gateway.py` (doesn't exist, remove refs)
   - Update `support/tests/integration/test_mcp_client.py` (remove test method)

**Risk Level**: ✅ **LOW** - No active code depends on these

#### B. Needs Refactoring (Active Dependencies)

**MCP Gateway Variable Updates** (High Priority):

Dependency Tree:
```
MCP_GATEWAY_URL environment variable
  ├── shared/services/rag/main.py (4 references)
  ├── shared/services/langgraph/main.py (5 references)  
  ├── shared/services/langgraph/src/main.py (5 references)
  ├── shared/lib/mcp_client.py (1 reference)
  ├── config/env/.env.template (1 definition)
  └── deploy/.env.template (1 definition)

Health Endpoints Returning mcp_gateway Status
  ├── shared/services/rag/main.py:/health
  └── shared/services/langgraph/main.py:/health
```

**Impact**: 6 service files, 2 config files, multiple documentation pages

**Refactoring Steps**:
1. Define replacement variable name (e.g., `MCP_DOCKER_TOOLKIT_STATUS`)
2. Update service health check logic
3. Update environment templates
4. Update 26 documentation references
5. Update validation/monitoring scripts (3 files)
6. Update Prometheus alerts

**Risk Level**: ⚠️ **MEDIUM** - Breaking change to health endpoint responses

**Memory Module Replacement**:

Dependency Tree:
```
shared/lib/langchain_memory.py (DEPRECATED)
  ├── Uses deprecated LangChain v0.2+ memory classes
  └── Replacement exists: shared/lib/agent_memory.py

Potential Importers (need audit):
  ├── agent_orchestrator/agents/_shared/base_agent.py (?)
  └── Any agent using memory features
```

**Refactoring Steps**:
1. Audit all imports of `langchain_memory.py`
2. Update to use `agent_memory.py`
3. Test memory functionality in all agents
4. Remove `langchain_memory.py`

**Risk Level**: ⚠️ **MEDIUM** - May affect agent memory functionality

**Canary Deployment Removal**:

Dependency Tree:
```
Registry canary field
  ├── agent_orchestrator/agents/infrastructure/modelops/registry.py
  │     ├── set_canary_model() method
  │     ├── promote_canary_to_current() method
  │     └── get_canary_model() method
  ├── agent_orchestrator/agents/infrastructure/modelops/coordinator.py
  │     └── Status endpoint returns canary_model
  ├── agent_orchestrator/agents/infrastructure/modelops/evaluation.py
  │     └── Recommendation logic includes "deploy_canary"
  ├── agent_orchestrator/agents/infrastructure/modelops/deployment.py
  │     └── May have canary-specific deployment logic
  ├── config/models/registry.json
  │     └── Contains actual canary data
  ├── support/tests/agents/infrastructure/modelops/test_registry.py
  │     ├── test_set_canary_model()
  │     └── test_promote_canary_to_current()
  └── support/tests/agents/infrastructure/modelops/test_evaluation.py
        └── Tests for deploy_canary recommendation
```

**Refactoring Steps** (Priority Order):
1. Update evaluation logic: Remove `"deploy_canary"` from recommendations (becomes just `"deploy"` for moderate improvements)
2. Remove registry methods: `set_canary_model()`, `promote_canary_to_current()`, `get_canary_model()`
3. Remove registry field: `canary` from Pydantic model
4. Update registry.json: Remove canary field from all agents
5. Update deployment statuses: Remove `"canary_20pct"`, `"canary_50pct"` from Literal type
6. Remove test methods: 2 complete tests in test_registry.py, update 5 assertions in `test_evaluation.py`
7. Update coordinator: Remove canary_model from status response
8. Clean documentation: Remove 15+ canary references from ModelOps.md, README.md, `copilot-instructions.md`
9. Clean Linear scripts: 10+ files with canary workflow references

**Risk Level**: ⚠️ **MEDIUM-HIGH** - Removes user-facing feature but already marked as "simplified"

**Impact Assessment**: According to `support/docs/extend Infra agent ModelOps.md#L713`, canary deployment was already removed on 2025-12-10 for simplification (single-user scenario). The code/tests/docs just haven't been fully cleaned up yet.

#### C. Keep As-Is (Clean, No Changes Needed)

**Core Agent Infrastructure**:
- All agents in `agent_orchestrator/agents/` (feature_dev, code_review, infrastructure, cicd, documentation, supervisor)
- LangGraph workflow engine
- Progressive MCP loader
- HITL manager
- Linear integration

**Services**:
- State persistence service
- Agent registry service  
- RAG context service (after MCP_GATEWAY_URL cleanup)

**Configuration**:
- `config/agents/models.yaml` (core model config)
- `config/routing/task-router.rules.yaml`
- Most YAML config files in `config/`

**Risk Level**: ✅ **NONE** - No deprecated references

---

### 6. PRIORITY-ORDERED CLEANUP ROADMAP

#### Phase 1: Zero-Risk Deletions (1-2 hours)
**Priority**: 🟢 **LOW RISK**

1. Delete deprecated packages:
   - `packages/mcp-bridge-client/`
   - `packages/mcp-bridge-client-py/`
   - `packages/MCP_GATEWAY_IMPLEMENTATION_GAP.md`
   - `packages/GITHUB_PACKAGES_INSTALL.md`
   - `packages/test-packages.ps1`

2. Delete gateway directories:
   - `shared/gateway/`
   - `_archive/gateway-deprecated-2025-12-03/`

3. Delete deprecated documentation:
   - `_archive/docs-temp/` (13 files)
   - `support/docs/_temp/` contents
   - Verified deprecated files from `support/docs/README.md`

4. Delete deprecated scripts:
   - `support/scripts/fix_deprecated_imports.py`
   - `support/scripts/analyze_deprecated_paths.py`

5. Clean test references:
   - Remove `"test_mcp_gateway"` from `support/tests/conftest.py`
   - Remove reference in `support/tests/README.md`
   - Remove `test_gateway_health` from `support/tests/integration/test_mcp_client.py`

**Validation**: Run tests, verify no import errors

---

#### Phase 2: Canary Deployment Removal (4-6 hours)
**Priority**: ⚠️ **MEDIUM RISK** - User-facing feature removal

1. **Update Evaluation Logic** (30 min):
   - `evaluation.py`: Change `Literal["deploy", "deploy_canary", ...]` → Remove `"deploy_canary"`
   - Lines 257-258, 431-432, 525-526: Update logic to use `"deploy"` for 5-15% improvements instead of `"deploy_canary"`

2. **Remove Registry Methods** (1 hour):
   - `registry.py`: Delete `set_canary_model()` method (52 lines)
   - Lines 434-481: Delete `promote_canary_to_current()` method (48 lines)
   - Lines 555-565: Delete `get_canary_model()` method (11 lines)
   - Line 102: Remove `canary` field
   - Lines 161, 167, 173, 179, 185: Remove `canary=None` initializations
   - Line 91: Update deployment status Literal to remove `"canary_20pct"`, `"canary_50pct"`

3. **Update Configuration** (15 min):
   - `config/models/registry.json`: Remove `canary` field from all agents (lines 10, 119, 194, 200, 206)
   - Remove canary deployment data from feature_dev (lines 10-41)
   - Remove canary entries from history arrays

4. **Remove Test Cases** (30 min):
   - `test_registry.py`: Delete 2 complete test methods (51 lines)
   - Line 78: Update assertion (remove canary check)
   - `test_evaluation.py`: Update 5 assertions/test data (lines 110, 187, 210, 313, 319)

5. **Update Coordinator** (30 min):
   - `coordinator.py`: Remove canary_model from status response
   - Lines 182, 264: Update doc comments

6. **Update Deployment Module** (45 min):
   - `deployment.py`: Audit and remove canary-specific logic
   - Lines 5, 53: Update doc comments

7. **Clean Documentation** (1-2 hours):
   - `ModelOps.md`: Remove all remaining canary references (~15 locations)
   - `.github/copilot-instructions.md`: Update recommendations list
   - `agent_orchestrator/agents/infrastructure/README.md`: Update recommendations
   - Linear scripts in `support/scripts/linear/`: Remove/update canary references in 10+ files

**Validation**: 
- Run ModelOps test suite: `pytest support/tests/agents/infrastructure/modelops/ -v`
- Verify registry operations work without canary
- Test evaluation recommendations
- Verify VS Code extension ModelOps commands still work

---

#### Phase 3: MCP Gateway Terminology Update (3-4 hours)
**Priority**: ⚠️ **MEDIUM RISK** - Breaking change to health endpoints

**Decision Required**: Choose replacement terminology
- Option A: `mcp_docker_toolkit` (recommended - matches current docs)
- Option B: `mcp_server`
- Option C: `mcp_bridge`

1. **Update Service Code** (1.5 hours):
   - `shared/services/rag/main.py`: Replace `MCP_GATEWAY_URL` variable (lines 46, 132, 492, 504, 505)
   - `shared/services/langgraph/main.py` + `src/main.py`: Update health check response format (lines 91, 131-135)
   - `shared/lib/mcp_client.py`: Update gateway_url initialization
   - **Decision**: Redirect to Docker MCP toolkit or remove entirely?

2. **Update Environment Templates** (15 min):
   - `config/env/.env.template`
   - `deploy/.env.template`
   - Add comment: "# MCP Gateway deprecated Dec 2025 - using Docker MCP Toolkit"

3. **Update Configuration** (15 min):
   - `config/rag/indexing.yaml`: Update `gateway_endpoint`

4. **Update Documentation** (1-1.5 hours):
   - `support/docs/DEPLOYMENT.md`: Update 9 references
   - `support/docs/ARCHITECTURE.md`: Update 2 references
   - `support/docs/integrations/langsmith-tracing.md`: Already notes deprecation
   - `support/docs/observability/monitoring.md`: Update 2 references
   - `shared/services/rag/README.md`: Update 1 reference
   - `shared/services/langgraph/README.md`: Update 2 references
   - `agent_orchestrator/agents/infrastructure/README.md`: Update 2 references
   - `agent_orchestrator/agents/supervisor/system.prompt.md`: Update health endpoint example

5. **Update Scripts & Monitoring** (30 min):
   - `support/scripts/validate_environment.py`: Update validation logic
   - `support/scripts/env_to_config.py`: Update env grep patterns
   - `support/scripts/analyze_deprecated_paths.py`: Update path references
   - `config/prometheus/alerts.yml`: Update or remove `MCPGatewayDown` alert

**Validation**:
- Test health endpoints: `/health` should return updated format
- Verify services start successfully
- Check Prometheus alerts still trigger appropriately
- Run validation scripts

---

#### Phase 4: Memory Module Refactoring (2-3 hours)
**Priority**: ⚠️ **MEDIUM RISK** - May affect agent functionality

1. **Audit Imports** (30 min):
   - Search all agent code for imports of `langchain_memory.py`
   - Verify which agents use memory functionality
   - Check `agent_memory.py` implementation

2. **Update Imports** (1 hour):
   - Replace with `agent_memory.py`
   - Update method calls to new API
   - Test each agent individually

3. **Testing** (1 hour):
   - Run agent test suites
   - Verify memory storage/retrieval works
   - Test conversation history functionality

4. **Remove Deprecated File** (5 min):
   - Delete `shared/lib/langchain_memory.py`

**Validation**:
- Full agent test suite
- Manual testing of chat with memory
- Verify no import errors

---

#### Phase 5: Tracing Tag Strategy Implementation (3-4 hours)
**Priority**: 🔵 **LOW RISK** - Improvement, not fix

1. **Define Tag Strategy** (30 min):
   - Document tag structure in config or docs
   - Define environment values: `production`, `training`, `evaluation`, `test`
   - Define required metadata fields

2. **Update ModelOps Training Tracing** (1 hour):
   - `training.py`: Add `tags` and `metadata` to all 7 decorators

3. **Update ModelOps Evaluation Tracing** (30 min):
   - `evaluation.py`: Add `tags` and `metadata` to all 4 decorators

4. **Update ModelOps Registry/Coordinator Tracing** (45 min):
   - `registry.py`: Add tags to 9 decorators
   - `coordinator.py`: Add tags to 8 decorators

5. **Update Test Tracing** (45 min):
   - Add `environment="test"` and `test_run=True` to all workflow test files
   - Update `conftest.py` to set environment tag globally for tests

6. **Update Documentation** (30 min):
   - Add tracing tag strategy to `support/docs/integrations/langsmith-tracing.md`
   - Update `.github/copilot-instructions.md` with tag requirements

**Validation**:
- Check LangSmith UI - verify traces properly tagged
- Verify filtering works by environment
- Confirm no production trace contamination from training/eval

---

### 7. RISK ASSESSMENT SUMMARY

| Phase | Risk Level | Breaking Changes | Test Impact | User Impact |
|-------|-----------|------------------|-------------|-------------|
| 1: Deletions | 🟢 LOW | None | Remove 1 test method | None |
| 2: Canary Removal | ⚠️ MEDIUM-HIGH | Remove registry methods, change eval logic | Update 2 test files | Lose canary feature (already deprecated) |
| 3: MCP Gateway | ⚠️ MEDIUM | Health endpoint format change | Update validation scripts | Monitoring may need updates |
| 4: Memory Module | ⚠️ MEDIUM | Change imports | Agent tests | Potential memory issues |
| 5: Tracing Tags | 🔵 LOW | None - additive | Add test tags | Better trace organization |

**Overall Estimated Effort**: 15-20 hours

**Recommended Sequence**: 
1. Phase 1 (safe deletions) → Immediate
2. Phase 2 (canary removal) → High priority, feature already deprecated
3. Phase 3 (MCP gateway) → Medium priority, requires coordination
4. Phase 5 (tracing tags) → Low priority, improvement
5. Phase 4 (memory module) → Last, most risky

**Critical Dependencies**:
- Phase 2 must complete before updating any model deployment workflows
- Phase 3 requires decision on replacement terminology
- Phase 4 requires thorough testing before deployment

---

### 8. ADDITIONAL FINDINGS

**Potential Issues Not in Original Scope**:

1. **Test File Without Implementation**:
   - `test_mcp_gateway.py` referenced but doesn't exist
   - May indicate incomplete test cleanup

2. **Backup Registry Files**:
   - `config/models/backups/` may contain canary data
   - Should be cleaned during Phase 2

3. **Environment Variable Cleanup**:
   - Several DEPRECATED variables in `.env.template` files
   - DigitalOcean KB sync variables can be removed
   - Legacy Qdrant variables can be removed

4. **Frontend Deprecation**:
   - `support/frontend/deprecated/` exists for reference
   - Safe to keep, but consider archive location

5. **Archive Directory Structure**:
   - Current codebase has `_archive/` directories scattered
   - Recommend consolidating to single archive location

**Recommendations**:
- Create cleanup Linear issue for each phase
- Use feature flags during Phase 3 to allow rollback
- Update `CHANGELOG.md` with all breaking changes
- Create migration guide for health endpoint changes
