"""
Email Notifier - Fallback Notification Channel

Sends email notifications when Linear notifications fail or as primary channel.

Configuration via environment variables:
- SMTP_HOST: SMTP server hostname
- SMTP_PORT: SMTP server port (default: 587)
- SMTP_USER: SMTP username
- SMTP_PASS: SMTP password
- SMTP_TLS: Whether to use TLS (default: true)
- NOTIFICATION_EMAIL_FROM: Sender email address
- NOTIFICATION_EMAIL_TO: Recipient email addresses (comma-separated)

Usage:
    from shared.lib.event_bus import get_event_bus
    from shared.lib.notifiers.email_notifier import EmailNotifier
    
    bus = get_event_bus()
    notifier = EmailNotifier()
    bus.subscribe("approval_required", notifier.on_approval_required)
"""

import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from dataclasses import dataclass

from ..event_bus import Event

logger = logging.getLogger(__name__)


@dataclass
class EmailConfig:
    """SMTP configuration for email notifications."""
    host: str
    port: int = 587
    user: str = ""
    password: str = ""
    use_tls: bool = True
    from_addr: str = "devtools@appsmithery.co"
    to_addrs: List[str] = None
    enabled: bool = True
    
    def __post_init__(self):
        """Set default to_addrs if not provided."""
        if self.to_addrs is None:
            self.to_addrs = []


class EmailNotifier:
    """
    Email notifier for approval requests and task updates.
    
    Use as fallback when Linear notifications fail, or as primary channel.
    """
    
    def __init__(self, config: Optional[EmailConfig] = None):
        """
        Initialize email notifier.
        
        Args:
            config: Email configuration (loads from env if not provided)
        """
        if config:
            self.config = config
        else:
            self.config = self._load_config_from_env()
        
        # Validate configuration
        if not self.config.host:
            logger.warning("SMTP_HOST not configured, email notifier disabled")
            self.config.enabled = False
        
        if not self.config.to_addrs:
            logger.warning("NOTIFICATION_EMAIL_TO not configured, email notifier disabled")
            self.config.enabled = False
        
        if self.config.enabled:
            logger.info(
                f"Email notifier initialized (SMTP: {self.config.host}:{self.config.port}, "
                f"recipients: {len(self.config.to_addrs)})"
            )
        else:
            logger.warning("Email notifier disabled (missing configuration)")
    
    def _load_config_from_env(self) -> EmailConfig:
        """
        Load email configuration from environment variables.
        
        Returns:
            EmailConfig instance
        """
        to_addrs_str = os.getenv("NOTIFICATION_EMAIL_TO", "")
        to_addrs = [addr.strip() for addr in to_addrs_str.split(",") if addr.strip()]
        
        return EmailConfig(
            host=os.getenv("SMTP_HOST", ""),
            port=int(os.getenv("SMTP_PORT", "587")),
            user=os.getenv("SMTP_USER", ""),
            password=os.getenv("SMTP_PASS", ""),
            use_tls=os.getenv("SMTP_TLS", "true").lower() == "true",
            from_addr=os.getenv("NOTIFICATION_EMAIL_FROM", "devtools@appsmithery.co"),
            to_addrs=to_addrs,
            enabled=True
        )
    
    async def on_approval_required(self, event: Event) -> None:
        """
        Handle approval_required event.
        
        Expected event.data:
            - approval_id: UUID of approval request
            - task_description: Human-readable task description
            - risk_level: critical, high, medium, low
            - project_name: Which project this approval is for
            - approver_email: Email address to send to (optional, overrides config)
        
        Args:
            event: Approval required event
        """
        if not self.config.enabled:
            logger.warning("Email notifier is disabled")
            return
        
        try:
            # Extract data
            approval_id = event.data.get("approval_id")
            task_description = event.data.get("task_description")
            risk_level = event.data.get("risk_level", "medium")
            project_name = event.data.get("project_name", "unknown")
            approver_email = event.data.get("approver_email")
            
            if not approval_id or not task_description:
                logger.error("Invalid approval event: missing approval_id or task_description")
                return
            
            # Determine recipients
            recipients = [approver_email] if approver_email else self.config.to_addrs
            
            # Risk emoji for subject line
            risk_emoji = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🟢"
            }
            
            # Build email
            subject = (
                f"{risk_emoji.get(risk_level, '⚪')} "
                f"{risk_level.upper()} Approval Required: {project_name}"
            )
            
            body = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        .header {{ background-color: #f0f0f0; padding: 20px; }}
        .content {{ padding: 20px; }}
        .risk-critical {{ color: #d32f2f; }}
        .risk-high {{ color: #f57c00; }}
        .risk-medium {{ color: #fbc02d; }}
        .risk-low {{ color: #388e3c; }}
        .action-buttons {{ margin-top: 20px; }}
        .btn {{ padding: 10px 20px; margin: 5px; text-decoration: none; color: white; border-radius: 5px; }}
        .btn-approve {{ background-color: #4caf50; }}
        .btn-reject {{ background-color: #f44336; }}
        code {{ background-color: #f5f5f5; padding: 2px 5px; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="header">
        <h2 class="risk-{risk_level}">{risk_emoji.get(risk_level, '⚪')} {risk_level.upper()} Approval Required</h2>
    </div>
    <div class="content">
        <p><strong>Project:</strong> <code>{project_name}</code></p>
        <p><strong>Approval ID:</strong> <code>{approval_id}</code></p>
        <p><strong>Timestamp:</strong> {event.timestamp.isoformat()}</p>
        
        <h3>Task Description</h3>
        <p>{task_description}</p>
        
        <div class="action-buttons">
            <p><strong>To approve or reject this request:</strong></p>
            <ol>
                <li>SSH to droplet: <code>ssh root@45.55.173.72</code></li>
                <li>Run approval command:
                    <ul>
                        <li>✅ Approve: <code>task workflow:approve REQUEST_ID={approval_id}</code></li>
                        <li>❌ Reject: <code>task workflow:reject REQUEST_ID={approval_id} REASON="&lt;reason&gt;"</code></li>
                    </ul>
                </li>
            </ol>
        </div>
        
        <p><a href="http://45.55.173.72:8001/approvals/{approval_id}">View in Dashboard</a></p>
    </div>
</body>
</html>
"""
            
            # Send email
            await self._send_email(
                to_addrs=recipients,
                subject=subject,
                body_html=body
            )
            
            logger.info(
                f"✅ Sent approval email for {approval_id} to {len(recipients)} recipients"
            )
            
        except Exception as e:
            logger.error(
                f"Failed to send approval email: {e}",
                exc_info=True
            )
    
    async def on_task_failed(self, event: Event) -> None:
        """
        Handle task_failed event.
        
        Expected event.data:
            - task_id: UUID of task
            - task_description: Human-readable description
            - error: Error message/traceback
            - project_name: Which project this task is for
        
        Args:
            event: Task failed event
        """
        if not self.config.enabled:
            logger.warning("Email notifier is disabled")
            return
        
        try:
            task_id = event.data.get("task_id")
            task_description = event.data.get("task_description")
            error = event.data.get("error", "Unknown error")
            project_name = event.data.get("project_name", "unknown")
            
            if not task_id or not task_description:
                logger.error("Invalid task_failed event: missing task_id or description")
                return
            
            subject = f"❌ Task Failed: {project_name}"
            
            body = f"""
<html>
<body>
    <h2>❌ Task Failed</h2>
    <p><strong>Task ID:</strong> <code>{task_id}</code></p>
    <p><strong>Project:</strong> <code>{project_name}</code></p>
    <p><strong>Description:</strong> {task_description}</p>
    <p><strong>Timestamp:</strong> {event.timestamp.isoformat()}</p>
    
    <h3>Error</h3>
    <pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px;">{error}</pre>
    
    <p><strong>Action Required:</strong> Review error and retry or escalate to human operator.</p>
</body>
</html>
"""
            
            await self._send_email(
                to_addrs=self.config.to_addrs,
                subject=subject,
                body_html=body
            )
            
            logger.info(f"✅ Sent task failure email for {task_id}")
            
        except Exception as e:
            logger.error(
                f"Failed to send task failure email: {e}",
                exc_info=True
            )
    
    async def _send_email(
        self,
        to_addrs: List[str],
        subject: str,
        body_html: str
    ) -> None:
        """
        Send email via SMTP.
        
        Args:
            to_addrs: List of recipient email addresses
            subject: Email subject
            body_html: HTML body content
        """
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.config.from_addr
            msg["To"] = ", ".join(to_addrs)
            
            # Attach HTML body
            msg.attach(MIMEText(body_html, "html"))
            
            # Connect to SMTP server
            if self.config.use_tls:
                server = smtplib.SMTP(self.config.host, self.config.port)
                server.starttls()
            else:
                server = smtplib.SMTP(self.config.host, self.config.port)
            
            # Login if credentials provided
            if self.config.user and self.config.password:
                server.login(self.config.user, self.config.password)
            
            # Send email
            server.sendmail(self.config.from_addr, to_addrs, msg.as_string())
            server.quit()
            
            logger.info(f"Sent email to {len(to_addrs)} recipients: {subject}")
            
        except Exception as e:
            logger.error(f"SMTP error: {e}", exc_info=True)
            raise
    
    def disable(self) -> None:
        """Disable email notifications."""
        self.config.enabled = False
        logger.info("Email notifier disabled")
    
    def enable(self) -> None:
        """Enable email notifications."""
        self.config.enabled = True
        logger.info("Email notifier enabled")
