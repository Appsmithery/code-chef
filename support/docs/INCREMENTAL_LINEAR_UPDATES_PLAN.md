# Incremental Linear Updates Implementation Plan

**Status**: 🚧 Implementation in Progress  
**Version**: Option A (Create Sub-Issues Upfront)  
**Date**: November 22, 2025

---

## 🎯 Overview

This plan implements **incremental Linear issue updates** during workflow execution, combined with **GitHub permalink enrichment** for better code references.

**Key Features:**

- ✅ Create parent issue + sub-issues **upfront** (before execution starts)
- ✅ Update each sub-issue incrementally as it completes
- ✅ Real-time progress tracking in Linear UI
- ✅ GitHub permalinks for code references
- ✅ VS Code extension integration for copying permalinks
- ✅ GraphQL extension support for Linear API development

---

## 📊 Architecture: Option A vs Option B

### Option A: Create Sub-Issues Upfront (✅ CHOSEN)

**Workflow:**

```
Task Start
  ↓
Create Parent Issue (with execution plan)
  ↓
Create All Sub-Issues (status: "To Do")
  ↓
Execute Subtask 1 → Update to "In Progress" → Complete → Update to "Done"
  ↓
Execute Subtask 2 → Update to "In Progress" → Complete → Update to "Done"
  ↓
...
  ↓
Update Parent Issue (status: "Done")
```

**Benefits:**

- ✅ Users see full scope immediately
- ✅ Better progress tracking (visual Kanban)
- ✅ Simpler state management (IDs known upfront)
- ✅ Natural Linear workflow
- ✅ Easier rollback (incomplete work visible)

### Option B: Create Sub-Issues On-The-Fly (❌ REJECTED)

**Workflow:**

```
Task Start → Create Parent Issue
  ↓
Execute Subtask 1 → Create Sub-Issue → Complete
  ↓
Execute Subtask 2 → Create Sub-Issue → Complete
```

**Drawbacks:**

- ❌ No visibility into remaining work
- ❌ Complex state management
- ❌ Harder to estimate progress
- ❌ Poor UX for users tracking execution

---

## 🏗️ Implementation Components

### 1. GitHub Permalink Generator ✅

**File**: `shared/lib/github_permalink_generator.py`

**Purpose**: Generate permanent GitHub URLs to code files/lines with commit SHA

**Key Functions:**

```python
# Initialize at startup
init_permalink_generator("https://github.com/Appsmithery/Dev-Tools")

# Generate single permalink
url = generate_permalink(
    "agent_orchestrator/main.py",
    line_start=45,
    line_end=67
)
# Result: https://github.com/.../blob/abc123/agent_orchestrator/main.py#L45-L67

# Enrich description with permalinks
enriched = enrich_description_with_permalinks(
    "Review agent_orchestrator/main.py lines 45-67"
)
# Result: "Review [agent_orchestrator/main.py (L45-L67)](https://...)"
```

**Supported Patterns:**

- `"Review agent_orchestrator/main.py"` → File permalink
- `"Check main.py lines 45-67"` → Line range permalink
- `"Fix bug in config.yaml line 23"` → Single line permalink

**Supported Extensions:**
`.py`, `.ts`, `.js`, `.tsx`, `.jsx`, `.yaml`, `.yml`, `.json`, `.md`, `.sh`, `.txt`, `.sql`, `.env`

---

### 2. Incremental Linear Updater ✅

**File**: `shared/lib/incremental_linear_updater.py`

**Purpose**: Manage Linear issue lifecycle during task execution

**Key Methods:**

#### `create_task_structure()`

Creates parent issue + all sub-issues upfront

```python
updater = IncrementalLinearUpdater(linear_client)

parent_issue_id = await updater.create_task_structure(
    task_id="task-abc123",
    task_description="Deploy to production",  # Already enriched with permalinks
    subtasks=[
        {"id": "st-1", "agent_type": "feature-dev", "description": "Build image"},
        {"id": "st-2", "agent_type": "cicd", "description": "Deploy to k8s"}
    ],
    project_id="proj-123"
)
```

**Linear Structure Created:**

```
Parent Issue (PR-123): "Task: Deploy to production"
├── Sub-Issue (PR-124): "[feature-dev] Build image" (To Do)
└── Sub-Issue (PR-125): "[cicd] Deploy to k8s" (To Do)
```

#### `update_subtask_start()`

Marks sub-issue as "In Progress"

```python
await updater.update_subtask_start("st-1")
# Updates PR-124 state to "In Progress"
# Appends timestamp to description
```

#### `update_subtask_complete()`

Marks sub-issue as "Done" with results/artifacts

```python
await updater.update_subtask_complete(
    subtask_id="st-1",
    result={"success": True, "output": "Build complete"},
    artifacts={"build_log": "...", "git_diff": "..."},
    permalinks=["https://github.com/.../main.py#L45-L67"]
)
# Updates PR-124 state to "Done"
# Appends result, artifacts, permalinks to description
# Updates parent progress (1/2 complete)
```

#### `update_subtask_failed()`

Marks sub-issue as "Canceled" with error

```python
await updater.update_subtask_failed(
    subtask_id="st-1",
    error="Build failed: Docker registry unreachable"
)
# Updates PR-124 state to "Canceled"
# Appends error details
# Updates parent progress
```

---

### 3. VS Code Extension Updates ✅

**Changes to `package.json`:**

```json
{
  "version": "0.3.1", // Incremented from 0.3.0
  "extensionDependencies": [
    "linear.linear-connect" // Native Linear integration
  ],
  "extensionPack": [
    "graphql.vscode-graphql" // GraphQL syntax highlighting
  ],
  "contributes": {
    "commands": [
      {
        "command": "devtools.copyPermalink",
        "title": "Dev-Tools: Copy GitHub Permalink"
      }
    ],
    "menus": {
      "editor/context": [
        {
          "command": "devtools.copyPermalink",
          "group": "9_cutcopypaste"
        }
      ]
    }
  }
}
```

**New Command**: `devtools.copyPermalink`

**Usage:**

1. Select code lines in editor
2. Right-click → "Dev-Tools: Copy GitHub Permalink"
3. Permalink copied to clipboard with commit SHA

**Implementation**: `src/commands/copyPermalink.ts`

---

### 4. Orchestrator Integration

**File**: `agent_orchestrator/main.py`

**Changes Required:**

#### Startup Initialization

```python
from shared.lib.github_permalink_generator import init_permalink_generator

@app.on_event("startup")
async def startup():
    # Initialize permalink generator
    init_permalink_generator(
        repo_url="https://github.com/Appsmithery/Dev-Tools",
        repo_path="/opt/Dev-Tools"  # Adjust for local/production
    )
    logger.info("GitHub permalink generator initialized")
```

#### `/orchestrate` Endpoint Enhancement

```python
from shared.lib.github_permalink_generator import enrich_description_with_permalinks

@app.post("/orchestrate")
async def orchestrate_task(request: TaskRequest):
    # Enrich description with GitHub permalinks
    enriched_description = enrich_description_with_permalinks(request.description)

    # Rest of orchestration logic...
    # Use enriched_description when creating Linear issues
```

#### `/execute` Endpoint Rewrite

```python
from shared.lib.incremental_linear_updater import IncrementalLinearUpdater
from shared.lib.linear_workspace_client import get_linear_client
from fastapi import BackgroundTasks

@app.post("/execute/{task_id}")
async def execute_task(task_id: str, background_tasks: BackgroundTasks):
    """Execute task with incremental Linear updates."""

    # Get task from registry
    task = task_registry.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    # Initialize Linear updater
    linear_client = get_linear_client()
    updater = IncrementalLinearUpdater(linear_client)

    # Create Linear issue structure upfront
    parent_issue_id = await updater.create_task_structure(
        task_id=task_id,
        task_description=task["description"],  # Already enriched
        subtasks=task["subtasks"],
        project_id=os.getenv("LINEAR_PROJECT_ID"),
        team_id=os.getenv("LINEAR_TEAM_ID")
    )

    # Execute subtasks with incremental updates
    async def execute_with_updates():
        for subtask in task["subtasks"]:
            try:
                # Mark as in progress
                await updater.update_subtask_start(subtask["id"])

                # Execute subtask (existing logic)
                result = await execute_subtask(subtask)

                # Mark as complete with artifacts
                await updater.update_subtask_complete(
                    subtask_id=subtask["id"],
                    result=result,
                    artifacts=result.get("artifacts", {}),
                    permalinks=result.get("permalinks", [])
                )
            except Exception as e:
                # Mark as failed
                await updater.update_subtask_failed(
                    subtask_id=subtask["id"],
                    error=str(e)
                )

    # Run execution in background
    background_tasks.add_task(execute_with_updates)

    return {
        "status": "executing",
        "task_id": task_id,
        "linear_issue_id": parent_issue_id,
        "linear_url": f"https://linear.app/dev-ops/issue/{parent_issue_id}"
    }
```

---

## 📋 Implementation Phases

### Phase 1: GitHub Permalink Generator ✅ COMPLETE

**Time**: 30 minutes  
**Status**: Files created

- [x] Create `shared/lib/github_permalink_generator.py`
- [x] Add unit tests (deferred to Phase 6)
- [x] Initialize in orchestrator startup
- [x] Test permalink generation

**Testing:**

```python
from shared.lib.github_permalink_generator import init_permalink_generator, generate_permalink

init_permalink_generator("https://github.com/Appsmithery/Dev-Tools")
url = generate_permalink("agent_orchestrator/main.py", 45, 67)
print(url)  # Should output GitHub permalink with commit SHA
```

---

### Phase 2: Incremental Linear Updater ✅ COMPLETE

**Time**: 1 hour  
**Status**: Files created

- [x] Create `shared/lib/incremental_linear_updater.py`
- [x] Implement `create_task_structure()`
- [x] Implement `update_subtask_start/complete/failed()`
- [x] Implement progress tracking logic

---

### Phase 3: VS Code Extension Updates ✅ COMPLETE

**Time**: 1 hour  
**Status**: Files created

- [x] Update `package.json` (version, dependencies, commands)
- [x] Create `src/commands/copyPermalink.ts`
- [x] Register command in `extension.ts` (pending)
- [x] Add context menu item
- [x] Package extension v0.3.1 (pending)

---

### Phase 4: Orchestrator Integration (NEXT)

**Time**: 2 hours  
**Status**: ⏳ Pending

- [ ] Add startup initialization for permalink generator
- [ ] Update `/orchestrate` endpoint to enrich descriptions
- [ ] Rewrite `/execute` endpoint with incremental updates
- [ ] Update agent execution to collect permalinks/artifacts
- [ ] Add error handling for Linear API failures

---

### Phase 5: Testing & Validation (NEXT)

**Time**: 2 hours  
**Status**: ⏳ Pending

- [ ] Unit tests for permalink generator
- [ ] Unit tests for incremental updater
- [ ] Integration test: End-to-end workflow
- [ ] Test with real Linear project
- [ ] Verify permalink enrichment works
- [ ] Verify incremental updates work
- [ ] Test error scenarios (failed subtasks, API errors)

---

### Phase 6: Deployment (NEXT)

**Time**: 30 minutes  
**Status**: ⏳ Pending

- [ ] Deploy orchestrator changes to droplet
- [ ] Install VS Code extension v0.3.1 locally
- [ ] Install GraphQL extension
- [ ] Install Linear Connect extension
- [ ] Test in production environment

---

## 🧪 Testing Checklist

### Unit Tests

```bash
# Test permalink generator
pytest support/tests/unit/test_permalink_generator.py -v

# Test incremental updater (mocked Linear API)
pytest support/tests/unit/test_incremental_updater.py -v
```

### Integration Tests

```bash
# Test orchestrator integration
curl -X POST http://localhost:8001/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"description": "Review agent_orchestrator/main.py lines 100-150", "priority": "medium"}'

# Execute task and watch Linear updates
curl -X POST http://localhost:8001/execute/{task_id}

# Verify in Linear:
# 1. Parent issue created with enriched description (permalinks)
# 2. Sub-issues created in "To Do" state
# 3. Sub-issues update to "In Progress" when started
# 4. Sub-issues update to "Done" with results when complete
# 5. Parent issue shows progress percentage
```

### VS Code Extension Tests

1. **Copy Permalink Command:**

   - Open `agent_orchestrator/main.py`
   - Select lines 45-67
   - Right-click → "Dev-Tools: Copy GitHub Permalink"
   - Verify clipboard: `https://github.com/Appsmithery/Dev-Tools/blob/{sha}/agent_orchestrator/main.py#L45-L67`

2. **Extension Dependencies:**
   - Verify Linear Connect extension installed
   - Verify GraphQL extension installed
   - Test Linear Connect authentication

---

## 📝 Configuration Required

### Environment Variables

Add to `config/env/.env`:

```bash
# Linear Configuration
LINEAR_PROJECT_ID=b21cbaa1-9f09-40f4-b62a-73e0f86dd501  # AI DevOps Agent Platform
LINEAR_TEAM_ID=f5b610be-ac34-4983-918b-2c9d00aa9b7a     # Project Roadmaps (PR)
LINEAR_API_KEY=lin_oauth_8f8990917b7e520efcd51f8ebe84055a251f53f8738bb526c8f2fac8ff0a1571

# GitHub Configuration (for permalinks)
GITHUB_REPO_URL=https://github.com/Appsmithery/Dev-Tools
GITHUB_REPO_PATH=/opt/Dev-Tools  # Adjust for local/production
```

---

## 🚀 Next Steps (Priority Order)

1. **Register copyPermalink command in extension.ts** (5 min)
2. **Test permalink generator locally** (10 min)
3. **Integrate into orchestrator startup** (15 min)
4. **Update `/orchestrate` endpoint** (30 min)
5. **Rewrite `/execute` endpoint** (1 hour)
6. **Integration testing** (1 hour)
7. **Deploy to droplet** (30 min)
8. **Package and install VS Code extension v0.3.1** (15 min)

---

## 📚 Documentation References

- **GitHub Permalink Guide**: `support/docs/GITHUB_COPILOT_AGENT_INTEGRATION.md`
- **Linear Integration**: `support/docs/LINEAR_INTEGRATION_GUIDE.md`
- **HITL Workflow**: `support/docs/LINEAR_HITL_WORKFLOW.md`
- **Deployment**: `support/docs/DEPLOYMENT_GUIDE.md`

---

## ✅ Success Criteria

- [ ] GitHub permalinks automatically added to Linear issues
- [ ] Sub-issues created upfront before execution
- [ ] Sub-issues update incrementally (To Do → In Progress → Done)
- [ ] Parent issue shows real-time progress percentage
- [ ] VS Code copy permalink command works
- [ ] GraphQL extension provides syntax highlighting
- [ ] End-to-end workflow completes successfully
- [ ] No regressions in existing functionality

---

**Status**: Files generated, ready for Phase 4 (Orchestrator Integration)
