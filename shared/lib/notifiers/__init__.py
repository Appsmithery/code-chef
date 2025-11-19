"""
Notifiers Module - Event-Driven Notification Handlers

Provides notifiers that subscribe to event bus and post to various channels:
- Linear workspace hub (approval requests)
- Linear project issues (task updates)
- Email (fallback)

Usage:
    from shared.lib.notifiers import (
        LinearWorkspaceNotifier,
        LinearProjectNotifier,
        EmailNotifier
    )
"""

from .linear_workspace_notifier import LinearWorkspaceNotifier, NotificationConfig
from .linear_project_notifier import LinearProjectNotifier, ProjectNotificationConfig
from .email_notifier import EmailNotifier, EmailConfig

__all__ = [
    "LinearWorkspaceNotifier",
    "LinearProjectNotifier",
    "EmailNotifier",
    "NotificationConfig",
    "ProjectNotificationConfig",
    "EmailConfig",
]
