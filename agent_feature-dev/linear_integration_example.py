"""
Example: Feature-Dev Agent with Linear Sub-Issue Auto-Creation

This demonstrates Phase 5 implementation where agents automatically create
Linear sub-issues when accepting tasks from the orchestrator.

Flow:
1. Orchestrator decomposes task → emits event to feature-dev queue
2. Feature-dev agent receives task via event bus
3. Agent auto-creates Linear sub-issue from template
4. Agent links sub-issue to parent (approval issue)
5. Agent stores task_id → linear_issue_id mapping
6. Agent updates issue status as work progresses
7. On completion, agent posts result comment
"""

import os
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from shared.lib.linear_workspace_client import LinearWorkspaceClient
from shared.lib.state_client import get_state_client

logger = logging.getLogger(__name__)
app = FastAPI(title="Feature-Dev Agent with Linear Integration")

# Initialize Linear client and state client
linear_client = LinearWorkspaceClient()
state_client = get_state_client()

# Configuration
FEATURE_DEV_TEMPLATE_ID = os.getenv("LINEAR_FEATURE_DEV_TEMPLATE_ID", "")
LINEAR_PROJECT_ID = os.getenv("LINEAR_PROJECT_ID", "")


class TaskAssignment(BaseModel):
    """Task assignment from orchestrator"""
    task_id: str
    description: str
    requirements: str
    complexity: str = "moderate"  # simple, moderate, complex
    acceptance_criteria: list[str]
    technical_notes: Optional[str] = None
    dependencies: Optional[list[str]] = None
    files: Optional[list[str]] = None
    orchestrator_issue_id: Optional[str] = None  # Parent Linear issue ID
    orchestrator_issue_identifier: Optional[str] = None  # Parent identifier (PR-XX)


class TaskResult(BaseModel):
    """Task completion result"""
    status: str
    linear_issue: str
    linear_issue_id: str
    summary: str


@app.post("/tasks/accept")
async def accept_task(task: TaskAssignment) -> TaskResult:
    """
    Agent accepts task and creates Linear tracking sub-issue.
    
    This endpoint is called by the orchestrator when delegating work.
    
    Flow:
    1. Create Linear sub-issue from template
    2. Link to parent via parentId
    3. Store mapping in state service
    4. Execute task
    5. Update Linear issue with progress/completion
    """
    
    logger.info(f"Accepting task: {task.task_id}")
    
    # ========================================
    # Step 1: Get Parent Issue ID
    # ========================================
    
    parent_id = task.orchestrator_issue_id
    
    # If only identifier provided, look up the ID
    if not parent_id and task.orchestrator_issue_identifier:
        parent_issue = await linear_client.get_issue_by_identifier(
            task.orchestrator_issue_identifier
        )
        if parent_issue:
            parent_id = parent_issue["id"]
        else:
            logger.warning(f"Parent issue not found: {task.orchestrator_issue_identifier}")
    
    # ========================================
    # Step 2: Create Linear Sub-Issue
    # ========================================
    
    try:
        # Format acceptance criteria as checklist
        criteria_checklist = "\n".join([f"- [ ] {c}" for c in task.acceptance_criteria])
        
        # Prepare template variables
        template_vars = {
            "parent_task_id": task.task_id,
            "complexity": task.complexity,
            "requirements": task.requirements,
            "acceptance_criteria": criteria_checklist,
            "technical_approach": task.technical_notes or "To be determined during implementation",
        }
        
        # Optional fields
        if task.dependencies:
            template_vars["dependencies"] = ", ".join(task.dependencies)
        
        if task.files:
            template_vars["files_affected"] = ", ".join(task.files)
        
        # Add agent-specific fields
        template_vars["test_coverage_target"] = 85
        template_vars["code_generation_strategy"] = "llm_first"
        
        # Create issue from template
        if FEATURE_DEV_TEMPLATE_ID:
            linear_issue = await linear_client.create_issue_from_template(
                template_id=FEATURE_DEV_TEMPLATE_ID,
                template_variables=template_vars,
                title_override=f"[Feature-Dev] {task.description[:50]}...",
                project_id=LINEAR_PROJECT_ID if LINEAR_PROJECT_ID else None,
                parent_id=parent_id
            )
        else:
            # Fallback: Create issue without template
            logger.warning("FEATURE_DEV_TEMPLATE_ID not configured, creating issue without template")
            
            description = f"""# Feature Development Task

**Parent Task:** `{task.task_id}`
**Estimated Complexity:** {task.complexity}

## Requirements

{task.requirements}

## Acceptance Criteria

{criteria_checklist}

## Technical Approach

{task.technical_notes or 'To be determined during implementation'}
"""
            
            if task.dependencies:
                description += f"\n## Dependencies\n\n{', '.join(task.dependencies)}"
            
            if task.files:
                description += f"\n## Files/Modules Affected\n\n{', '.join(task.files)}"
            
            # Create issue without template (requires separate implementation)
            # For now, raise error to force template configuration
            raise ValueError("LINEAR_FEATURE_DEV_TEMPLATE_ID must be configured")
        
        logger.info(f"Created Linear sub-issue: {linear_issue['identifier']}")
        
    except Exception as e:
        logger.error(f"Failed to create Linear sub-issue: {e}")
        raise HTTPException(status_code=500, detail=f"Linear integration failed: {str(e)}")
    
    # ========================================
    # Step 3: Store Mapping (State Service)
    # ========================================
    
    try:
        await state_client.store_task_mapping(
            task_id=task.task_id,
            linear_issue_id=linear_issue["id"],
            linear_identifier=linear_issue["identifier"],
            agent_name="feature-dev",
            parent_issue_id=parent_id,
            parent_identifier=task.orchestrator_issue_identifier,
            status="todo"
        )
        logger.info(f"Task mapping stored: {task.task_id} → {linear_issue['identifier']}")
    except Exception as e:
        logger.error(f"Failed to store task mapping: {e}")
        # Non-fatal: continue with task execution
    
    # ========================================
    # Step 4: Execute Task (Simplified Example)
    # ========================================
    
    try:
        # Update status to "In Progress" (both Linear and state service)
        await linear_client.update_issue_status(
            issue_id=linear_issue["id"],
            status="in_progress"
        )
        await state_client.update_task_status(task.task_id, "in_progress")
        
        # Simulate work...
        # result = await generate_feature_code(task)
        
        # For demo purposes, add progress comment
        await linear_client.add_comment(
            issue_id=linear_issue["id"],
            body=f"""**Progress Update**

Generated code for {len(task.files or [])} files.
Running tests...
"""
        )
        
        # Simulate completion
        summary = f"Successfully implemented {task.description}"
        
        # ========================================
        # Step 5: Update Linear on Completion
        # ========================================
        
        # Mark as done (both Linear and state service)
        await linear_client.update_issue_status(
            issue_id=linear_issue["id"],
            status="done"
        )
        await state_client.update_task_status(task.task_id, "done", mark_completed=True)
        
        # Add completion comment
        await linear_client.add_comment(
            issue_id=linear_issue["id"],
            body=f"""**Task Completed** ✅

{summary}

**Generated Files:**
{chr(10).join([f'- `{f}`' for f in (task.files or ['No files tracked'])])}

**Test Coverage:** 85%
**All Tests:** Passing
"""
        )
        
        logger.info(f"Task completed: {task.task_id}")
        
        return TaskResult(
            status="completed",
            linear_issue=linear_issue["identifier"],
            linear_issue_id=linear_issue["id"],
            summary=summary
        )
        
    except Exception as e:
        logger.error(f"Task execution failed: {e}")
        
        # Update Linear and state service with error
        try:
            await linear_client.update_issue_status(
                issue_id=linear_issue["id"],
                status="canceled"
            )
            await state_client.update_task_status(task.task_id, "canceled", mark_completed=True)
            
            await linear_client.add_comment(
                issue_id=linear_issue["id"],
                body=f"""**Task Failed** ❌

Error: {str(e)}

Agent will retry or escalate to human operator.
"""
            )
        except Exception as linear_error:
            logger.error(f"Failed to update Linear with error: {linear_error}")
        
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "agent": "feature-dev",
        "linear_configured": bool(FEATURE_DEV_TEMPLATE_ID)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
