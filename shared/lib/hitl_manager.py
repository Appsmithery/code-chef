"""Human-in-the-Loop (HITL) Manager for autonomous workflow approval.
Coordinates approval requests, policy enforcement, and state persistence.

Issue: CHEF-200 - Added @traceable decorators for LangSmith visibility.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Literal, Optional

import psycopg
import yaml
from langsmith import traceable

from .checkpoint_connection import get_async_connection
from .risk_assessor import RiskLevel, get_risk_assessor

logger = logging.getLogger(__name__)

ApprovalStatus = Literal["pending", "approved", "rejected", "expired", "cancelled"]


class HITLManager:
    """
    Manages Human-in-the-Loop approval workflows.

    Responsibilities:
    - Assess risk of autonomous operations
    - Create approval requests in PostgreSQL
    - Check approval status during workflow resumption
    - Enforce approval policies (role-based authorization)
    - Handle timeout/expiration of approval requests
    """

    def __init__(self, policies_path: Optional[str] = None):
        self.risk_assessor = get_risk_assessor()

        if policies_path is None:
            # Check environment variable first (for container deployments)
            policies_path = os.environ.get("HITL_POLICIES_PATH")

            if policies_path is None:
                # Fall back to relative path (for local development)
                policies_path = os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "..",
                    "config",
                    "hitl",
                    "approval-policies.yaml",
                )
                policies_path = os.path.abspath(policies_path)

        try:
            with open(policies_path) as f:
                self.policies = yaml.safe_load(f)
            logger.info(
                f"[HITLManager] Successfully loaded policies from {policies_path}"
            )
        except FileNotFoundError:
            logger.error(f"[HITLManager] Policies file not found: {policies_path}")
            # Default minimal policies
            self.policies = {
                "roles": {
                    "developer": {"can_approve": ["low"]},
                    "tech_lead": {"can_approve": ["low", "medium", "high"]},
                    "devops_engineer": {
                        "can_approve": ["low", "medium", "high", "critical"]
                    },
                }
            }

        self.db_connection = None

    async def _get_connection(self):
        """Get async database connection context manager"""
        return get_async_connection()

    @traceable(name="hitl_create_approval_request", tags=["hitl", "approval"])
    async def create_approval_request(
        self,
        workflow_id: str,
        thread_id: str,
        checkpoint_id: str,
        task: Dict,
        agent_name: str,
    ) -> str:
        """
        Create approval request in PostgreSQL.

        Args:
            workflow_id: Unique workflow identifier
            thread_id: LangGraph thread ID
            checkpoint_id: LangGraph checkpoint ID (for resumption)
            task: Task dict with operation, environment, resource_type, etc.
            agent_name: Name of agent requesting approval

        Returns:
            Approval request UUID
        """
        # Assess risk
        risk_level = self.risk_assessor.assess_task(task)
        requires_approval = self.risk_assessor.requires_approval(risk_level)

        if not requires_approval:
            logger.info(f"[HITLManager] Task auto-approved (risk_level={risk_level})")
            return None  # No approval needed

        request_id = str(uuid.uuid4())
        timeout_minutes = self.risk_assessor.get_timeout_minutes(risk_level)
        expires_at = datetime.utcnow() + timedelta(minutes=timeout_minutes)

        async with await self._get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    INSERT INTO approval_requests (
                        id, workflow_id, thread_id, checkpoint_id,
                        task_type, task_description,
                        agent_name, risk_level, risk_score, risk_factors,
                        action_type, action_details, action_impact,
                        status, expires_at, created_at,
                        linear_issue_id, linear_issue_url
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        'pending', %s, NOW(),
                        %s, %s
                    )
                    """,
                    (
                        request_id,
                        workflow_id,
                        thread_id,
                        checkpoint_id,
                        task.get("operation", "unknown"),
                        task.get("description", ""),
                        agent_name,
                        risk_level,
                        self._calculate_risk_score(task, risk_level),
                        json.dumps(task.get("risk_factors", [])),
                        task.get("operation", ""),
                        json.dumps(task.get("details", {})),
                        task.get("impact", ""),
                        expires_at,
                        None,  # linear_issue_id placeholder
                        None,  # linear_issue_url placeholder
                    ),
                )
                await conn.commit()

        # NEW: Create Linear issue for tracking
        try:
            from shared.lib.linear_workspace_client import LinearWorkspaceClient

            linear_client = LinearWorkspaceClient()
            project_id = (
                os.environ.get("LINEAR_PROJECT_ID")
                or "b21cbaa1-9f09-40f4-b62a-73e0f86dd501"
            )
            issue = await linear_client.create_issue_with_document(
                title=f"[HITL] {task.get('operation', 'Approval Required')}",
                description=self._format_approval_description(
                    request_id, task, risk_level
                ),
                document_markdown=self._format_approval_description(
                    request_id, task, risk_level
                ),
                project_id=project_id,
                labels=None,
                parent_id=os.environ.get("APPROVAL_HUB_ID"),
                priority=2 if risk_level in ["high", "critical"] else 3,
            )
            # Store Linear issue ID and URL
            async with await self._get_connection() as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute(
                        "UPDATE approval_requests SET linear_issue_id = %s, linear_issue_url = %s WHERE id = %s",
                        (issue["id"], issue["url"], request_id),
                    )
                    await conn.commit()
        except Exception as e:
            logger.error(f"[HITLManager] Failed to create Linear issue: {e}")

        logger.info(
            f"[HITLManager] Created approval request {request_id} "
            f"(risk={risk_level}, expires={expires_at.isoformat()})"
        )

        # Trigger notifications (async, non-blocking)
        await self._send_notifications(request_id, risk_level, task)

        return request_id

    @traceable(name="hitl_check_approval_status", tags=["hitl", "approval"])
    async def check_approval_status(self, request_id: str) -> Dict:
        """
        Check status of approval request.

        Args:
            request_id: Approval request UUID

        Returns:
            Dict with:
                - status: ApprovalStatus
                - approver_id: User who approved (if approved)
                - rejection_reason: Reason if rejected
                - approved_at: Timestamp of approval
                - expired: Boolean indicating if request expired
        """
        async with await self._get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    SELECT status, approver_id, approved_at, rejected_at,
                           rejection_reason, expires_at, risk_level
                    FROM approval_requests
                    WHERE id = %s
                    """,
                    (request_id,),
                )
                row = await cursor.fetchone()

        if not row:
            raise ValueError(f"Approval request {request_id} not found")

        (
            status,
            approver_id,
            approved_at,
            rejected_at,
            rejection_reason,
            expires_at,
            risk_level,
        ) = row

        # Check expiration
        expired = False
        if status == "pending" and datetime.utcnow() > expires_at:
            expired = True
            await self._mark_expired(request_id)
            status = "expired"

        return {
            "status": status,
            "risk_level": risk_level,
            "approver_id": approver_id,
            "rejection_reason": rejection_reason,
            "approved_at": approved_at.isoformat() if approved_at else None,
            "rejected_at": rejected_at.isoformat() if rejected_at else None,
            "expired": expired,
        }

    @traceable(name="hitl_approve_request", tags=["hitl", "approval"])
    async def approve_request(
        self,
        request_id: str,
        approver_id: str,
        approver_role: str,
        justification: Optional[str] = None,
    ) -> bool:
        """
        Approve a pending request.

        Args:
            request_id: Approval request UUID
            approver_id: User ID of approver
            approver_role: Role of approver (for policy check)
            justification: Optional justification text

        Returns:
            True if approval succeeded, False if unauthorized or expired
        """
        # Get request details
        async with await self._get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT risk_level, status, expires_at FROM approval_requests WHERE id = %s",
                    (request_id,),
                )
                row = await cursor.fetchone()

            if not row:
                raise ValueError(f"Approval request {request_id} not found")

            risk_level, status, expires_at = row

            # Check expiration
            if datetime.utcnow() > expires_at:
                await self._mark_expired(request_id)
                logger.warning(f"[HITLManager] Request {request_id} expired")
                return False

            # Check authorization
            if not self._can_approve(approver_role, risk_level):
                logger.warning(
                    f"[HITLManager] User {approver_id} (role={approver_role}) "
                    f"cannot approve risk level {risk_level}"
                )
                return False

            # Check justification requirement
            if (
                self.risk_assessor.requires_justification(risk_level)
                and not justification
            ):
                logger.warning(
                    f"[HITLManager] Justification required for risk level {risk_level}"
                )
                return False

            # Update request
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    UPDATE approval_requests
                    SET status = 'approved',
                        approver_id = %s,
                        approver_role = %s,
                        approved_at = NOW(),
                        approval_justification = %s,
                        updated_at = NOW()
                    WHERE id = %s AND status = 'pending'
                    """,
                    (approver_id, approver_role, justification, request_id),
                )
                await conn.commit()

        logger.info(f"[HITLManager] Request {request_id} approved by {approver_id}")
        return True

    @traceable(name="hitl_reject_request", tags=["hitl", "approval"])
    async def reject_request(
        self, request_id: str, approver_id: str, approver_role: str, reason: str
    ) -> bool:
        """
        Reject a pending request.

        Args:
            request_id: Approval request UUID
            approver_id: User ID of person rejecting
            approver_role: Role of the person rejecting
            reason: Rejection reason

        Returns:
            True if rejection succeeded
        """
        async with await self._get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    """
                    UPDATE approval_requests
                    SET status = 'rejected',
                        approver_id = %s,
                        approver_role = %s,
                        rejected_at = NOW(),
                        rejection_reason = %s,
                        updated_at = NOW()
                    WHERE id = %s AND status = 'pending'
                    """,
                    (approver_id, approver_role, reason, request_id),
                )
                await conn.commit()

        logger.info(
            f"[HITLManager] Request {request_id} rejected by {approver_id} ({approver_role}): {reason}"
        )
        return True

    @traceable(name="hitl_list_pending_requests", tags=["hitl", "approval"])
    async def list_pending_requests(
        self, approver_role: Optional[str] = None, limit: int = 50
    ) -> List[Dict]:
        """
        List pending approval requests.

        Args:
            approver_role: Filter by requests this role can approve (optional)
            limit: Max number of results

        Returns:
            List of approval request dicts
        """
        async with await self._get_connection() as conn:
            query = """
                SELECT id, workflow_id, task_type, task_description,
                       agent_name, risk_level, action_type, action_impact,
                       created_at, expires_at
                FROM approval_requests
                WHERE status = 'pending' AND expires_at > NOW()
                ORDER BY created_at DESC
                LIMIT %s
            """

            async with conn.cursor() as cursor:
                await cursor.execute(query, (limit,))
                rows = await cursor.fetchall()

        results = []
        for row in rows:
            request_dict = {
                "id": row[0],
                "workflow_id": row[1],
                "task_type": row[2],
                "task_description": row[3],
                "agent_name": row[4],
                "risk_level": row[5],
                "action_type": row[6],
                "action_impact": row[7],
                "created_at": row[8].isoformat(),
                "expires_at": row[9].isoformat(),
            }

            # Filter by role if specified
            if approver_role is None or self._can_approve(approver_role, row[5]):
                results.append(request_dict)

        return results

    def _can_approve(self, role: str, risk_level: RiskLevel) -> bool:
        """Check if role can approve risk level"""
        role_config = self.policies.get("roles", {}).get(role, {})
        can_approve_levels = role_config.get("can_approve", [])
        return risk_level in can_approve_levels

    def _calculate_risk_score(self, task: Dict, risk_level: RiskLevel) -> float:
        """Calculate numeric risk score (0.0-10.0)"""
        base_scores = {"low": 2.0, "medium": 5.0, "high": 7.5, "critical": 9.5}

        score = base_scores.get(risk_level, 5.0)

        # Adjust based on additional factors
        if task.get("security_findings"):
            score += 1.0
        if task.get("data_sensitive"):
            score += 1.0
        if task.get("estimated_cost", 0) > 500:
            score += 0.5

        return min(score, 10.0)

    async def _mark_expired(self, request_id: str):
        """Mark request as expired"""
        async with await self._get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "UPDATE approval_requests SET status = 'expired', updated_at = NOW() WHERE id = %s",
                    (request_id,),
                )
                await conn.commit()

    @traceable(name="hitl_send_notifications", tags=["hitl", "notification"])
    async def _send_notifications(
        self, request_id: str, risk_level: RiskLevel, task: Dict
    ):
        """Send notifications about approval request (placeholder)"""
        channels = self.risk_assessor.get_notification_channels(risk_level)
        logger.info(
            f"[HITLManager] Notification: request {request_id}, risk={risk_level}, "
            f"channels={channels}, task={task.get('operation')}"
        )
        # TODO: Implement actual notification sending (Slack, email, etc.)


# Singleton instance
_hitl_manager_instance: Optional[HITLManager] = None


def get_hitl_manager(policies_path: Optional[str] = None) -> HITLManager:
    """Get or create HITLManager singleton instance"""
    global _hitl_manager_instance
    if _hitl_manager_instance is None:
        _hitl_manager_instance = HITLManager(policies_path)
    return _hitl_manager_instance
