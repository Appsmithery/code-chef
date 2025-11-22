"""
Example: Integrate Linear attachments into orchestrator workflow.

This shows how to attach execution artifacts (logs, diffs, test results) 
to Linear issues after workflow completion.

Add this to agent_orchestrator/main.py:
"""

# 1. Add import at top of main.py
from shared.lib.linear_attachments import attach_execution_artifacts

# 2. In /execute/{task_id} endpoint, before returning, add:

# ... existing execution logic ...

    # Update overall task status
    overall_status = (
        "completed"
        if all(
            r["status"] in ["completed", "pending_implementation"]
            for r in execution_results
        )
        else "failed"
    )
    
    # ========== NEW: Attach execution artifacts to Linear issue ==========
    linear_issue_id = os.getenv("LINEAR_APPROVAL_HUB_ISSUE_ID", "DEV-68")  # Or extract from task context
    
    # Collect artifacts from execution results
    artifacts = {}
    
    # Add deployment logs
    deployment_logs = []
    for result in execution_results:
        if result.get("status") == "completed":
            agent = result.get("agent", "unknown")
            subtask_id = result.get("subtask_id", "")
            
            # Format execution summary
            log_entry = f"""
Subtask: {subtask_id}
Agent: {agent}
Status: {result['status']}
Result: {result.get('result', {}).get('message', 'N/A')}
""".strip()
            deployment_logs.append(log_entry)
    
    if deployment_logs:
        artifacts["Execution Log"] = "\n\n---\n\n".join(deployment_logs)
    
    # Add git diffs (if feature-dev agent returned artifacts)
    for result in execution_results:
        if result.get("agent") == "feature-dev":
            prev_result = result.get("result", {})
            if "artifacts" in prev_result:
                diffs = []
                for artifact in prev_result["artifacts"]:
                    diff = f"""
File: {artifact.get('file_path', 'unknown')}
Type: {artifact.get('type', 'unknown')}

{artifact.get('content', '')}
""".strip()
                    diffs.append(diff)
                
                if diffs:
                    artifacts["Git Diff"] = "\n\n---\n\n".join(diffs)
    
    # Add code review findings (if code-review agent ran)
    for result in execution_results:
        if result.get("agent") == "code-review":
            review_result = result.get("result", {})
            if "issues" in review_result:
                findings = []
                for issue in review_result["issues"]:
                    finding = f"""
File: {issue.get('file', 'unknown')}
Line: {issue.get('line', 'N/A')}
Severity: {issue.get('severity', 'unknown')}
Message: {issue.get('message', 'N/A')}
""".strip()
                    findings.append(finding)
                
                if findings:
                    artifacts["Code Review Findings"] = "\n\n---\n\n".join(findings)
    
    # Upload artifacts to Linear (async, non-blocking)
    if artifacts and os.getenv("LINEAR_API_KEY"):
        try:
            attachments = await attach_execution_artifacts(
                issue_id=linear_issue_id,
                artifacts=artifacts
            )
            logger.info(f"Attached {len(attachments)} artifacts to Linear issue {linear_issue_id}")
        except Exception as e:
            logger.warning(f"Failed to attach artifacts to Linear: {e}")
            # Don't fail the entire execution if attachment fails
    # ========== END NEW CODE ==========

    return {
        "task_id": task_id,
        "status": overall_status,
        "execution_results": execution_results,
        "subtasks": [
            {
                "id": st.id,
                "agent_type": st.agent_type,
                "status": st.status,
                "description": st.description,
            }
            for st in task.subtasks
        ],
    }
