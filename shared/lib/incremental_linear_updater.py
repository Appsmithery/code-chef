"""
Incremental Linear Updater

Manages incremental Linear issue updates during task execution.
Creates parent issue + sub-issues upfront, updates each sub-issue as it completes.

Usage:
    from shared.lib.incremental_linear_updater import IncrementalLinearUpdater
    from shared.lib.linear_workspace_client import get_linear_client

    # Initialize
    linear_client = get_linear_client()
    updater = IncrementalLinearUpdater(linear_client)

    # Create issue structure upfront
    parent_issue_id = await updater.create_task_structure(
        task_id="task-123",
        task_description="Implement feature X",
        subtasks=[{"id": "st-1", "agent_type": "feature-dev", "description": "..."}],
        project_id="abc-123"
    )

    # During execution
    await updater.update_subtask_start("st-1")
    await updater.update_subtask_complete("st-1", result={...}, artifacts={...})
"""

from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class IncrementalLinearUpdater:
    """Manages incremental Linear issue updates during task execution."""

    def __init__(self, linear_client):
        """
        Initialize with Linear workspace client.

        Args:
            linear_client: Instance of LinearWorkspaceClient
        """
        self.linear = linear_client
        self.parent_issue_id: Optional[str] = None
        self.parent_identifier: Optional[str] = None  # e.g., "PR-123"
        self.subtask_issue_map: Dict[str, Dict[str, str]] = (
            {}
        )  # subtask_id -> {id, identifier}

    async def create_task_structure(
        self,
        task_id: str,
        task_description: str,
        subtasks: List[Dict],
        project_id: Optional[str] = None,
        team_id: Optional[str] = None,
    ) -> str:
        """
        Create Linear parent issue + sub-issues upfront.

        Args:
            task_id: Orchestrator task ID
            task_description: User's original task description (already enriched with permalinks)
            subtasks: List of subtask dicts with keys: id, agent_type, description, dependencies
            project_id: Linear project ID (optional)
            team_id: Linear team ID (optional)

        Returns:
            Parent issue ID

        Example:
            >>> parent_id = await updater.create_task_structure(
            ...     task_id="task-abc123",
            ...     task_description="Deploy to production",
            ...     subtasks=[
            ...         {"id": "st-1", "agent_type": "feature-dev", "description": "Build image"},
            ...         {"id": "st-2", "agent_type": "cicd", "description": "Deploy to k8s"}
            ...     ],
            ...     project_id="proj-123"
            ... )
        """
        logger.info(f"Creating Linear issue structure for task {task_id}")

        # Create parent issue
        parent_issue = await self.linear.create_issue(
            title=f"Task: {task_description[:80]}...",
            description=self._build_parent_description(task_description, subtasks),
            project_id=project_id,
            team_id=team_id,
            labels=["automated", "orchestrator"],
            state="in_progress",  # Start in "In Progress" since we're executing
        )

        self.parent_issue_id = parent_issue["id"]
        self.parent_identifier = parent_issue.get("identifier", "Unknown")
        logger.info(
            f"Created parent issue: {self.parent_identifier} ({self.parent_issue_id})"
        )

        # Create sub-issues for each subtask
        for i, subtask in enumerate(subtasks, 1):
            sub_issue = await self.linear.create_issue(
                title=f"[{subtask['agent_type']}] {subtask['description'][:70]}...",
                description=self._build_subtask_description(subtask, i, len(subtasks)),
                parent_id=self.parent_issue_id,
                project_id=project_id,
                team_id=team_id,
                labels=["automated", subtask["agent_type"]],
                state="todo",  # Start in "To Do" state
            )

            self.subtask_issue_map[subtask["id"]] = {
                "id": sub_issue["id"],
                "identifier": sub_issue.get("identifier", "Unknown"),
            }
            logger.info(
                f"Created sub-issue {i}/{len(subtasks)}: {sub_issue.get('identifier')} for subtask {subtask['id']}"
            )

        return self.parent_issue_id

    async def update_subtask_start(self, subtask_id: str):
        """
        Mark subtask as in progress.

        Args:
            subtask_id: Orchestrator subtask ID
        """
        issue_info = self.subtask_issue_map.get(subtask_id)
        if not issue_info:
            logger.warning(f"No Linear issue found for subtask {subtask_id}")
            return

        timestamp = datetime.utcnow().isoformat() + "Z"

        await self.linear.update_issue(
            issue_id=issue_info["id"],
            state="in_progress",
            description_append=f"\n\n---\n\n⏳ **Started**: {timestamp}",
        )
        logger.info(
            f"Marked subtask {subtask_id} ({issue_info['identifier']}) as in progress"
        )

    async def update_subtask_complete(
        self,
        subtask_id: str,
        result: Dict,
        artifacts: Optional[Dict[str, str]] = None,
        permalinks: Optional[List[str]] = None,
    ):
        """
        Mark subtask as complete with results and artifacts.

        Args:
            subtask_id: Orchestrator subtask ID
            result: Execution result dict with keys: success, output, error
            artifacts: Optional dict of artifact_name -> content
            permalinks: Optional list of GitHub permalinks generated during execution

        Example:
            >>> await updater.update_subtask_complete(
            ...     subtask_id="st-1",
            ...     result={"success": True, "output": "Build complete"},
            ...     artifacts={"build_log": "...", "git_diff": "..."},
            ...     permalinks=["https://github.com/.../main.py#L45-L67"]
            ... )
        """
        issue_info = self.subtask_issue_map.get(subtask_id)
        if not issue_info:
            logger.warning(f"No Linear issue found for subtask {subtask_id}")
            return

        timestamp = datetime.utcnow().isoformat() + "Z"

        # Build completion message
        completion_msg = f"\n\n---\n\n✅ **Completed**: {timestamp}\n\n"

        # Add result summary
        if result.get("success"):
            completion_msg += "### Result\n"
            completion_msg += f"```\n{result.get('output', 'Success')}\n```\n\n"
        else:
            completion_msg += "### ⚠️ Error\n"
            completion_msg += f"```\n{result.get('error', 'Unknown error')}\n```\n\n"

        # Add permalinks (if any)
        if permalinks:
            completion_msg += "### 📎 Code References\n"
            for permalink in permalinks:
                # Extract file path from URL for display
                file_part = (
                    permalink.split("/blob/")[-1]
                    if "/blob/" in permalink
                    else permalink
                )
                completion_msg += f"- [{file_part}]({permalink})\n"
            completion_msg += "\n"

        # Add artifact placeholders (GitHub Gist integration deferred)
        if artifacts:
            completion_msg += "### 📋 Artifacts\n"
            for name in artifacts.keys():
                completion_msg += f"- {name} (available in orchestrator logs)\n"
            completion_msg += "\n*Note: Artifact upload to GitHub Gist coming soon*\n\n"

        # Update issue
        await self.linear.update_issue(
            issue_id=issue_info["id"], state="done", description_append=completion_msg
        )
        logger.info(
            f"Marked subtask {subtask_id} ({issue_info['identifier']}) as complete"
        )

        # Update parent issue progress
        await self._update_parent_progress()

    async def update_subtask_failed(self, subtask_id: str, error: str):
        """
        Mark subtask as failed with error details.

        Args:
            subtask_id: Orchestrator subtask ID
            error: Error message or stack trace
        """
        issue_info = self.subtask_issue_map.get(subtask_id)
        if not issue_info:
            logger.warning(f"No Linear issue found for subtask {subtask_id}")
            return

        timestamp = datetime.utcnow().isoformat() + "Z"

        await self.linear.update_issue(
            issue_id=issue_info["id"],
            state="canceled",  # Linear uses "canceled" for failed states
            description_append=f"""

---

❌ **Failed**: {timestamp}

### Error
```
{error}
```
            """,
        )
        logger.error(
            f"Marked subtask {subtask_id} ({issue_info['identifier']}) as failed"
        )

        # Update parent issue
        await self._update_parent_progress()

    async def _update_parent_progress(self):
        """Update parent issue with current progress."""
        if not self.parent_issue_id:
            return

        # Count completed/failed subtasks by querying Linear
        total = len(self.subtask_issue_map)
        completed = 0
        failed = 0
        in_progress = 0

        for subtask_id, issue_info in self.subtask_issue_map.items():
            try:
                issue = await self.linear.get_issue(issue_info["id"])
                state_name = issue.get("state", {}).get("name", "").lower()

                if state_name == "done":
                    completed += 1
                elif state_name == "canceled":
                    failed += 1
                elif state_name == "in progress":
                    in_progress += 1
            except Exception as e:
                logger.warning(f"Failed to get issue state for {subtask_id}: {e}")

        # Calculate progress
        progress_pct = int((completed / total) * 100) if total > 0 else 0

        # Build progress message
        timestamp = datetime.utcnow().isoformat() + "Z"
        progress_msg = f"""

---

## 📊 Progress Update

**Status**: {completed}/{total} subtasks complete ({progress_pct}%)

- ✅ Completed: {completed}
- ⏳ In Progress: {in_progress}
- ❌ Failed: {failed}
- 📝 To Do: {total - completed - failed - in_progress}

*Last updated: {timestamp}*
        """.strip()

        # Get current issue
        issue = await self.linear.get_issue(self.parent_issue_id)
        description = issue.get("description", "")

        # Replace progress section or append if not found
        if "## 📊 Progress Update" in description:
            # Remove old progress section
            description = re.sub(
                r"\n---\n\n## 📊 Progress Update\n.*?(?=\n---|\Z)",
                "",
                description,
                flags=re.DOTALL,
            )

        # Append new progress
        new_description = description + "\n\n" + progress_msg

        # Update parent state
        new_state = "done" if completed == total else "in_progress"

        await self.linear.update_issue(
            issue_id=self.parent_issue_id, description=new_description, state=new_state
        )

        logger.info(
            f"Updated parent issue {self.parent_identifier} progress: {progress_pct}%"
        )

    def _build_parent_description(
        self, task_description: str, subtasks: List[Dict]
    ) -> str:
        """Build parent issue description."""
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Format subtask list
        subtask_list = []
        for i, subtask in enumerate(subtasks, 1):
            subtask_list.append(
                f"{i}. **{subtask['agent_type']}**: {subtask['description'][:80]}..."
            )

        return f"""
## 📋 Original Request
{task_description}

## 🎯 Execution Plan
{len(subtasks)} subtasks planned:

{chr(10).join(subtask_list)}

## 📊 Status
⏳ Execution in progress...

*Created: {timestamp}*
*This issue will be updated as subtasks complete.*
        """.strip()

    def _build_subtask_description(self, subtask: Dict, index: int, total: int) -> str:
        """Build subtask issue description."""
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Format dependencies
        deps = subtask.get("dependencies", [])
        deps_text = ", ".join(deps) if deps else "None"

        return f"""
## 🤖 Agent
**{subtask['agent_type']}**

## 📝 Task
{subtask['description']}

## 🔗 Dependencies
{deps_text}

## 📍 Position
Subtask {index} of {total}

## ⏱️ Status
📌 Waiting to execute...

*Created: {timestamp}*
        """.strip()


# Import at module level to avoid circular imports
import re
