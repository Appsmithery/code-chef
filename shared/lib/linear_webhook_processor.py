"""
Linear Webhook Processor for HITL Approvals

Handles emoji reactions on approval comments and triggers workflow state changes.
Supports:
- 👍 Approve (resume workflow)
- 👎 Deny (cancel workflow)
- 💬 Reply (request more info, pause workflow)
"""

import os
import hmac
import hashlib
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class LinearWebhookProcessor:
    """Process Linear webhook events for HITL approvals via emoji reactions."""

    def __init__(self):
        """Initialize webhook processor with signing secret from env or file."""
        # Try direct env var first
        self.signing_secret = os.getenv("LINEAR_WEBHOOK_SIGNING_SECRET")

        # If not found, try Docker secret file
        if not self.signing_secret:
            secret_file = os.getenv("LINEAR_WEBHOOK_SIGNING_SECRET_FILE")
            if secret_file and os.path.exists(secret_file):
                try:
                    with open(secret_file, "r") as f:
                        self.signing_secret = f.read().strip()
                    logger.info(f"Loaded webhook signing secret from {secret_file}")
                except Exception as e:
                    logger.error(
                        f"Failed to read webhook secret from {secret_file}: {e}"
                    )

        if not self.signing_secret:
            logger.warning(
                "LINEAR_WEBHOOK_SIGNING_SECRET not set - webhook signature verification disabled"
            )

    def verify_signature(self, signature: Optional[str], payload: bytes) -> bool:
        """
        Verify Linear webhook signature.

        Args:
            signature: Linear-Signature header value
            payload: Raw request body bytes

        Returns:
            True if signature valid or verification disabled, False otherwise
        """
        if not self.signing_secret:
            return True  # Skip verification if secret not configured

        if not signature:
            logger.warning("No signature provided in webhook request")
            return False

        expected_signature = hmac.new(
            self.signing_secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        is_valid = hmac.compare_digest(signature, expected_signature)
        if not is_valid:
            logger.warning(
                f"Invalid webhook signature - "
                f"Received: {signature[:20]}... "
                f"Expected: {expected_signature[:20]}... "
                f"Using secret: {self.signing_secret[:15]}..."
            )

        return is_valid

    async def process_webhook(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process webhook event and return action result.

        Args:
            event: Webhook event data from Linear

        Returns:
            {
                "action": "resume_workflow" | "cancel_workflow" | "pause_workflow" | "ignore",
                "metadata": {...}
            }
        """
        event_type = event.get("type")
        action = event.get("action")
        data = event.get("data")

        # DEBUG: Log full webhook payload structure
        import json

        logger.info(f"🔍 WEBHOOK RECEIVED: {event_type}.{action}")
        logger.info(f"🔍 Data keys: {list(data.keys()) if data else 'None'}")
        logger.info(
            f"🔍 Full payload (first 2000 chars): {json.dumps(event, indent=2, default=str)[:2000]}"
        )

        logger.debug(f"Processing webhook event: {event_type}.{action}")

        # Handle Reaction events (emoji reactions on comments)
        if event_type == "Reaction" and action == "create":
            return await self._handle_reaction_event(data)

        # Handle Comment update events (legacy reaction handling via reactions array)
        if event_type == "Comment" and action == "update":
            return await self._handle_comment_reaction(data)

        # Handle Comment create events (reply comments requesting more info)
        elif event_type == "Comment" and action == "create":
            return await self._handle_comment_reply(data)

        logger.debug(f"Ignoring webhook event: {event_type}.{action}")
        return {"action": "ignore"}

    async def _handle_comment_reaction(
        self, comment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle emoji reactions on approval comments.

        Args:
            comment_data: Comment data from webhook

        Returns:
            Action dict with "resume_workflow", "cancel_workflow", or "ignore"
        """
        reactions = comment_data.get("reactions", [])
        comment_id = comment_data.get("id")
        comment_body = comment_data.get("body", "")
        issue = comment_data.get("issue", {})
        issue_identifier = issue.get("identifier")

        # Check if this is an approval comment (contains "HITL Approval Required")
        if "HITL Approval Required" not in comment_body:
            logger.debug(f"Comment {comment_id} is not an approval request, ignoring")
            return {"action": "ignore"}

        logger.info(
            f"Processing reactions on approval comment {comment_id} in {issue_identifier}"
        )

        # Check for approval/denial reactions
        for reaction in reactions:
            emoji = reaction.get("emoji")
            count = reaction.get("count", 0)
            user = reaction.get("user", {})

            if emoji == "👍" and count >= 1:
                logger.info(
                    f"✅ Approval detected on {comment_id} by {user.get('email')}"
                )
                return {
                    "action": "resume_workflow",
                    "metadata": {
                        "comment_id": comment_id,
                        "comment_url": comment_data.get("url"),
                        "issue_id": issue.get("id"),
                        "issue_identifier": issue_identifier,
                        "approved_by": user.get("email"),
                        "approved_by_name": user.get("displayName"),
                        "approved_at": reaction.get("createdAt"),
                    },
                }

            elif emoji == "👎" and count >= 1:
                logger.info(
                    f"❌ Denial detected on {comment_id} by {user.get('email')}"
                )
                return {
                    "action": "cancel_workflow",
                    "metadata": {
                        "comment_id": comment_id,
                        "comment_url": comment_data.get("url"),
                        "issue_id": issue.get("id"),
                        "issue_identifier": issue_identifier,
                        "denied_by": user.get("email"),
                        "denied_by_name": user.get("displayName"),
                        "denied_at": reaction.get("createdAt"),
                    },
                }

        logger.debug(f"No approval/denial reactions found on comment {comment_id}")
        return {"action": "ignore"}

    async def _handle_reaction_event(
        self, reaction_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle Reaction.create event when user adds emoji to a comment.

        Linear Reaction event structure:
        {
            "type": "Reaction",
            "action": "create",
            "data": {
                "id": "...",
                "emoji": "👍",
                "comment": {
                    "id": "...",
                    "body": "...",
                    "url": "...",
                    "issue": {
                        "id": "...",
                        "identifier": "DEV-68"
                    }
                },
                "user": {
                    "id": "...",
                    "email": "...",
                    "displayName": "..."
                },
                "createdAt": "..."
            }
        }

        Args:
            reaction_data: Reaction data from webhook

        Returns:
            Action dict with "resume_workflow", "cancel_workflow", or "ignore"
        """
        # DEBUG: Log the full payload structure to understand what Linear sends
        import json

        logger.info(f"🔍 DEBUG: Full Reaction event payload structure:")
        logger.info(f"🔍 reaction_data keys: {list(reaction_data.keys())}")
        logger.info(
            f"🔍 reaction_data: {json.dumps(reaction_data, indent=2, default=str)[:1000]}"
        )

        emoji = reaction_data.get("emoji")
        comment = reaction_data.get("comment", {})
        comment_id = comment.get("id")
        comment_body = comment.get("body", "")
        comment_url = comment.get("url")
        issue = comment.get("issue", {})
        issue_id = issue.get("id")
        issue_identifier = issue.get("identifier")
        user = reaction_data.get("user", {})
        user_email = user.get("email")
        user_name = user.get("displayName")
        created_at = reaction_data.get("createdAt")

        logger.info(
            f"🔍 Extracted data: emoji={emoji}, comment_id={comment_id}, comment_body_length={len(comment_body)}, issue={issue_identifier}, user={user_name}"
        )

        # Check if this is an approval comment (contains "HITL Approval Required")
        if "HITL Approval Required" not in comment_body:
            logger.info(
                f"⚠️ Comment body does NOT contain 'HITL Approval Required'. Body preview: {comment_body[:100]}"
            )
            logger.debug(f"Reaction on non-approval comment {comment_id}, ignoring")
            return {"action": "ignore"}

        logger.info(
            f"Processing {emoji} reaction on approval comment {comment_id} "
            f"in {issue_identifier} by {user_name}"
        )

        # Handle approval reaction (Linear sends "+1" for 👍)
        if emoji in ("+1", "👍"):
            logger.info(f"✅ Approval detected on {comment_id} by {user_email}")
            return {
                "action": "resume_workflow",
                "metadata": {
                    "comment_id": comment_id,
                    "comment_url": comment_url,
                    "issue_id": issue_id,
                    "issue_identifier": issue_identifier,
                    "approved_by": user_email,
                    "approved_by_name": user_name,
                    "approved_at": created_at,
                    "emoji": emoji,
                },
            }

        # Handle denial reaction (Linear sends "-1" for 👎)
        elif emoji in ("-1", "👎"):
            logger.info(f"❌ Denial detected on {comment_id} by {user_email}")
            return {
                "action": "cancel_workflow",
                "metadata": {
                    "comment_id": comment_id,
                    "comment_url": comment_url,
                    "issue_id": issue_id,
                    "issue_identifier": issue_identifier,
                    "denied_by": user_email,
                    "denied_by_name": user_name,
                    "denied_at": created_at,
                    "emoji": emoji,
                },
            }

        # Ignore other emoji reactions
        logger.debug(
            f"Reaction {emoji} on {comment_id} not an approval/denial, ignoring"
        )
        return {"action": "ignore"}

    async def _handle_comment_reply(
        self, comment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle comment replies to approval requests (request more info).

        Args:
            comment_data: Comment data from webhook

        Returns:
            Action dict with "pause_workflow" or "ignore"
        """
        parent_id = comment_data.get("parent", {}).get("id")
        comment_id = comment_data.get("id")
        comment_body = comment_data.get("body", "")
        user = comment_data.get("user", {})
        issue = comment_data.get("issue", {})

        # If this is a reply to another comment, check if parent is an approval request
        if not parent_id:
            return {"action": "ignore"}

        # TODO: Would need to fetch parent comment to check if it's an approval
        # For now, any reply to a comment in the approval hub triggers pause
        logger.info(f"💬 Reply detected on comment thread by {user.get('email')}")
        return {
            "action": "pause_workflow",
            "metadata": {
                "comment_id": comment_id,
                "parent_comment_id": parent_id,
                "comment_url": comment_data.get("url"),
                "issue_id": issue.get("id"),
                "issue_identifier": issue.get("identifier"),
                "requested_by": user.get("email"),
                "requested_by_name": user.get("displayName"),
                "message": comment_body[:200],  # First 200 chars
            },
        }
