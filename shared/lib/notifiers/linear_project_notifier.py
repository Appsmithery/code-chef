"""
Linear Project Notifier - Posts to Project Issues

Subscribes to task events and posts updates to project-specific issues.
Security: Subagents use this with project_id scoping.

Usage:
    from shared.lib.event_bus import get_event_bus
    from shared.lib.notifiers.linear_project_notifier import LinearProjectNotifier
    
    bus = get_event_bus()
    notifier = LinearProjectNotifier(
        agent_name="feature-dev",
        project_name="phase-5-chat"
    )
    bus.subscribe("task_completed", notifier.on_task_completed)
    bus.subscribe("task_failed", notifier.on_task_failed)
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from ..event_bus import Event
from ..linear_client_factory import get_linear_client
from ..linear_project_client import LinearProjectClient

logger = logging.getLogger(__name__)


@dataclass
class ProjectNotificationConfig:
    """Configuration for project notifications."""
    enabled: bool = True
    auto_create_issues: bool = False  # Whether to create issues for events
    update_existing_issues: bool = True  # Whether to comment on existing issues


class LinearProjectNotifier:
    """
    Notifier that posts task updates to project-specific Linear issues.
    
    Security: Scoped to specific project_id (subagent-safe).
    """
    
    def __init__(
        self,
        agent_name: str,
        project_name: str,
        config: Optional[ProjectNotificationConfig] = None
    ):
        """
        Initialize project notifier.
        
        Args:
            agent_name: Name of agent (feature-dev, infrastructure, etc.)
            project_name: Name of Linear project to scope to
            config: Notification configuration
        """
        self.agent_name = agent_name
        self.project_name = project_name
        self.config = config or ProjectNotificationConfig()
        
        # Initialize project-scoped client
        try:
            self.client: LinearProjectClient = get_linear_client(
                agent_name=agent_name,
                project_name=project_name
            )
            logger.info(
                f"Linear project notifier initialized "
                f"(agent: {agent_name}, project: {project_name})"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Linear client: {e}")
            self.config.enabled = False
    
    async def on_task_completed(self, event: Event) -> None:
        """
        Handle task_completed event.
        
        Expected event.data:
            - task_id: UUID of task
            - task_description: Human-readable description
            - issue_id: Linear issue ID to comment on (optional)
            - results: Task results/summary (optional)
        
        Args:
            event: Task completed event
        """
        if not self.config.enabled:
            logger.warning("Linear project notifier is disabled")
            return
        
        try:
            task_id = event.data.get("task_id")
            task_description = event.data.get("task_description")
            issue_id = event.data.get("issue_id")
            results = event.data.get("results", "Task completed successfully")
            
            if not task_id or not task_description:
                logger.error("Invalid task_completed event: missing task_id or description")
                return
            
            # If issue_id provided, add comment
            if issue_id and self.config.update_existing_issues:
                comment_body = f"""
✅ **Task Completed**

**Task ID**: `{task_id}`
**Description**: {task_description}
**Agent**: {self.agent_name}
**Timestamp**: {event.timestamp.isoformat()}

**Results**:
{results}
"""
                
                comment_id = await self.client.add_comment(
                    issue_id=issue_id,
                    body=comment_body
                )
                
                logger.info(
                    f"✅ Commented on issue {issue_id}: task {task_id} completed"
                )
            
            else:
                logger.info(
                    f"Task {task_id} completed but no issue_id provided "
                    f"(update_existing_issues: {self.config.update_existing_issues})"
                )
            
        except Exception as e:
            logger.error(
                f"Failed to post task completion to Linear: {e}",
                exc_info=True
            )
    
    async def on_task_failed(self, event: Event) -> None:
        """
        Handle task_failed event.
        
        Expected event.data:
            - task_id: UUID of task
            - task_description: Human-readable description
            - issue_id: Linear issue ID to comment on (optional)
            - error: Error message/traceback
        
        Args:
            event: Task failed event
        """
        if not self.config.enabled:
            logger.warning("Linear project notifier is disabled")
            return
        
        try:
            task_id = event.data.get("task_id")
            task_description = event.data.get("task_description")
            issue_id = event.data.get("issue_id")
            error = event.data.get("error", "Unknown error")
            
            if not task_id or not task_description:
                logger.error("Invalid task_failed event: missing task_id or description")
                return
            
            # If issue_id provided, add comment
            if issue_id and self.config.update_existing_issues:
                comment_body = f"""
❌ **Task Failed**

**Task ID**: `{task_id}`
**Description**: {task_description}
**Agent**: {self.agent_name}
**Timestamp**: {event.timestamp.isoformat()}

**Error**:
```
{error}
```

**Action Required**: Review error and retry or escalate to human operator.
"""
                
                comment_id = await self.client.add_comment(
                    issue_id=issue_id,
                    body=comment_body
                )
                
                logger.info(
                    f"❌ Commented on issue {issue_id}: task {task_id} failed"
                )
            
            else:
                logger.info(
                    f"Task {task_id} failed but no issue_id provided "
                    f"(update_existing_issues: {self.config.update_existing_issues})"
                )
            
        except Exception as e:
            logger.error(
                f"Failed to post task failure to Linear: {e}",
                exc_info=True
            )
    
    async def on_agent_error(self, event: Event) -> None:
        """
        Handle agent_error event.
        
        Expected event.data:
            - error_type: Type of error (timeout, crash, api_error, etc.)
            - error_message: Error description
            - issue_id: Linear issue ID to comment on (optional)
            - traceback: Full traceback (optional)
        
        Args:
            event: Agent error event
        """
        if not self.config.enabled:
            logger.warning("Linear project notifier is disabled")
            return
        
        try:
            error_type = event.data.get("error_type", "unknown")
            error_message = event.data.get("error_message", "Agent error occurred")
            issue_id = event.data.get("issue_id")
            traceback = event.data.get("traceback")
            
            # If issue_id provided, add comment
            if issue_id and self.config.update_existing_issues:
                comment_body = f"""
🚨 **Agent Error**

**Type**: {error_type}
**Agent**: {self.agent_name}
**Project**: {self.project_name}
**Timestamp**: {event.timestamp.isoformat()}

**Error Message**:
{error_message}
"""
                
                if traceback:
                    comment_body += f"\n\n**Traceback**:\n```\n{traceback}\n```"
                
                comment_id = await self.client.add_comment(
                    issue_id=issue_id,
                    body=comment_body
                )
                
                logger.info(
                    f"🚨 Commented on issue {issue_id}: agent error ({error_type})"
                )
            
            else:
                logger.warning(
                    f"Agent error ({error_type}) but no issue_id provided "
                    f"(update_existing_issues: {self.config.update_existing_issues})"
                )
            
        except Exception as e:
            logger.error(
                f"Failed to post agent error to Linear: {e}",
                exc_info=True
            )
    
    def enable_auto_create(self) -> None:
        """Enable automatic issue creation for events."""
        self.config.auto_create_issues = True
        logger.info("Enabled auto-create issues")
    
    def disable_auto_create(self) -> None:
        """Disable automatic issue creation for events."""
        self.config.auto_create_issues = False
        logger.info("Disabled auto-create issues")
    
    def disable(self) -> None:
        """Disable notifications."""
        self.config.enabled = False
        logger.info("Linear project notifier disabled")
    
    def enable(self) -> None:
        """Enable notifications."""
        self.config.enabled = True
        logger.info("Linear project notifier enabled")
