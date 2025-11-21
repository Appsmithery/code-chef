"""
Linear Workspace Notifier - Posts to Approval Hub

Subscribes to approval_required events and posts to workspace-level approval hub.
Security: Only orchestrator should use this (workspace-level access required).

Usage:
    from shared.lib.event_bus import get_event_bus
    from shared.lib.notifiers.linear_workspace_notifier import LinearWorkspaceNotifier
    
    bus = get_event_bus()
    notifier = LinearWorkspaceNotifier(agent_name="orchestrator")
    bus.subscribe("approval_required", notifier.on_approval_required)
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from ..event_bus import Event
from ..linear_client_factory import get_linear_client
from ..linear_workspace_client import LinearWorkspaceClient

logger = logging.getLogger(__name__)


@dataclass
class NotificationConfig:
    """Configuration for workspace notifications."""
    enabled: bool = True
    approver_mention: str = "@lead-minion"  # Default Linear @mention
    min_risk_level: str = "low"  # Only notify if risk >= this level


class LinearWorkspaceNotifier:
    """
    Notifier that posts approval requests to Linear workspace hub.
    
    Security: Requires workspace-level access (orchestrator only).
    """
    
    def __init__(
        self,
        agent_name: str = "orchestrator",
        config: Optional[NotificationConfig] = None
    ):
        """
        Initialize workspace notifier.
        
        Args:
            agent_name: Name of agent (must be "orchestrator")
            config: Notification configuration
        """
        if agent_name != "orchestrator":
            raise ValueError(
                "LinearWorkspaceNotifier requires workspace access. "
                "Only orchestrator can use this notifier."
            )
        
        self.agent_name = agent_name
        self.config = config or NotificationConfig()
        
        # Initialize workspace client
        try:
            self.client: LinearWorkspaceClient = get_linear_client(
                agent_name=agent_name
            )
            logger.info("Linear workspace notifier initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Linear client: {e}")
            self.config.enabled = False
    
    async def on_approval_required(self, event: Event) -> None:
        """
        Handle approval_required event.
        
        Expected event.data:
            - approval_id: UUID of approval request
            - task_description: Human-readable task description
            - risk_level: critical, high, medium, low
            - project_name: Which project this approval is for
            - metadata: Additional context (optional)
        
        Args:
            event: Approval required event
        """
        if not self.config.enabled:
            logger.warning("Linear workspace notifier is disabled")
            return
        
        try:
            # Extract data
            approval_id = event.data.get("approval_id")
            task_description = event.data.get("task_description")
            risk_level = event.data.get("risk_level", "medium")
            project_name = event.data.get("project_name", "unknown")
            metadata = event.data.get("metadata")
            
            if not approval_id or not task_description:
                logger.error(
                    f"Invalid approval event: missing approval_id or task_description"
                )
                return
            
            # Check risk level threshold
            risk_levels = ["low", "medium", "high", "critical"]
            if risk_levels.index(risk_level) < risk_levels.index(self.config.min_risk_level):
                logger.info(
                    f"Skipping notification for {risk_level} risk "
                    f"(min: {self.config.min_risk_level})"
                )
                return
            
            logger.info(
                f"Creating approval sub-issue for {approval_id} "
                f"(risk: {risk_level}, project: {project_name})"
            )
            
            # Create sub-issue from HITL approval template
            issue = await self.client.create_approval_subissue(
                approval_id=approval_id,
                task_description=task_description,
                risk_level=risk_level,
                project_name=project_name,
                agent_name=metadata.get("agent", "orchestrator") if metadata else "orchestrator",
                metadata=metadata
            )
            
            logger.info(
                f"✅ Created approval sub-issue {issue['identifier']} for {approval_id}"
            )
            
        except Exception as e:
            logger.error(
                f"Failed to post approval to workspace hub: {e}",
                exc_info=True
            )
    
    def set_approver_mention(self, mention: str) -> None:
        """
        Update approver @mention.
        
        Args:
            mention: Linear @mention (e.g., "@ops-lead", "@alex")
        """
        self.config.approver_mention = mention
        logger.info(f"Updated approver mention to: {mention}")
    
    def set_min_risk_level(self, level: str) -> None:
        """
        Set minimum risk level for notifications.
        
        Args:
            level: One of: low, medium, high, critical
        """
        valid_levels = ["low", "medium", "high", "critical"]
        if level not in valid_levels:
            raise ValueError(f"Invalid risk level. Must be one of: {valid_levels}")
        
        self.config.min_risk_level = level
        logger.info(f"Updated min risk level to: {level}")
    
    def disable(self) -> None:
        """Disable notifications."""
        self.config.enabled = False
        logger.info("Linear workspace notifier disabled")
    
    def enable(self) -> None:
        """Enable notifications."""
        self.config.enabled = True
        logger.info("Linear workspace notifier enabled")
