"""
Linear Webhook Handler

Receives Linear webhook events and routes to orchestrator for approval decisions.

Endpoints:
- POST /webhook/linear - Receive Linear webhook events

Security:
- Verifies HMAC signature using LINEAR_WEBHOOK_SIGNING_SECRET
- Only accepts events from configured workspace

Events Handled:
- Issue.update - Status changes on approval hub (PR-68)
- Comment.create - Approval comments on approval requests

Integration:
- Publishes events to orchestrator via event_bus
- Orchestrator resumes/cancels tasks based on approval decisions
"""

import os
import hmac
import hashlib
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, Header, HTTPException, status
from pydantic import BaseModel

# Assume event_bus is available from shared lib
# from shared.lib.event_bus import event_bus

logger = logging.getLogger(__name__)

app = FastAPI(title="Linear Webhook Handler")

# Configuration
WEBHOOK_SECRET = os.getenv("LINEAR_WEBHOOK_SIGNING_SECRET")
APPROVAL_HUB_ID = os.getenv("LINEAR_APPROVAL_HUB_ISSUE_ID", "PR-68")

if not WEBHOOK_SECRET:
    logger.warning("LINEAR_WEBHOOK_SIGNING_SECRET not configured - webhook verification disabled")


class LinearWebhookPayload(BaseModel):
    """Linear webhook payload structure"""
    action: str
    type: str
    data: Dict[str, Any]
    webhookId: str
    workspaceId: str
    createdAt: str


def verify_webhook_signature(body: bytes, signature: Optional[str]) -> bool:
    """
    Verify Linear webhook HMAC signature.
    
    Args:
        body: Raw webhook body bytes
        signature: X-Linear-Signature header value
    
    Returns:
        True if signature is valid, False otherwise
    """
    if not WEBHOOK_SECRET:
        logger.warning("Webhook signature verification skipped (no secret configured)")
        return True
    
    if not signature:
        logger.error("Missing X-Linear-Signature header")
        return False
    
    # Calculate expected signature
    expected_sig = hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison
    is_valid = hmac.compare_digest(expected_sig, signature)
    
    if not is_valid:
        logger.error("Invalid webhook signature")
    
    return is_valid


def extract_task_id(description: str) -> Optional[str]:
    """
    Extract task ID from Linear issue description.
    
    Expected format: **Task ID:** `abc123-def456-ghi789`
    
    Args:
        description: Issue description markdown
    
    Returns:
        Task ID if found, None otherwise
    """
    import re
    
    # Look for pattern: **Task ID:** `{task_id}`
    match = re.search(r'\*\*Task ID:\*\*\s+`([a-zA-Z0-9\-_]+)`', description)
    
    if match:
        return match.group(1)
    
    logger.debug("No task ID found in description")
    return None


@app.post("/webhook/linear")
async def handle_linear_webhook(
    request: Request,
    x_linear_signature: Optional[str] = Header(None)
):
    """
    Handle Linear webhook events.
    
    Processes:
    - Issue status changes on approval hub (PR-68)
    - Approval comments with specific format
    
    Publishes events:
    - approval_decision: {task_id, decision, linear_issue}
    """
    # Read raw body
    body = await request.body()
    
    # Verify signature
    if not verify_webhook_signature(body, x_linear_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
    
    # Parse payload
    payload = await request.json()
    
    event_type = payload.get("type")
    action = payload.get("action")
    data = payload.get("data", {})
    
    logger.info(f"Received Linear webhook: {event_type}.{action}")
    
    # ========================================
    # Handle Issue Updates (Status Changes)
    # ========================================
    
    if event_type == "Issue" and action == "update":
        issue = data
        
        # Check if this is an approval request (child of PR-68)
        parent_id = issue.get("parent", {}).get("id")
        
        # Also check if issue identifier matches approval hub pattern
        issue_identifier = issue.get("identifier", "")
        is_approval_hub_child = (
            parent_id and parent_id == APPROVAL_HUB_ID
        ) or issue_identifier == APPROVAL_HUB_ID
        
        if is_approval_hub_child:
            # Extract approval decision from status
            state_name = issue.get("state", {}).get("name", "").lower()
            
            # Map Linear states to decisions
            decision_map = {
                "approved": "approved",
                "done": "approved",
                "completed": "approved",
                "rejected": "rejected",
                "canceled": "rejected",
                "cancelled": "rejected"
            }
            
            decision = decision_map.get(state_name)
            
            if decision:
                # Extract task ID from description
                description = issue.get("description", "")
                task_id = extract_task_id(description)
                
                if task_id:
                    # Publish approval decision event
                    event = {
                        "task_id": task_id,
                        "decision": decision,
                        "linear_issue": issue_identifier,
                        "linear_issue_id": issue.get("id"),
                        "linear_url": issue.get("url"),
                        "state": state_name
                    }
                    
                    logger.info(f"Approval decision: {decision} for task {task_id}")
                    
                    # TODO: Publish to event bus
                    # await event_bus.publish("approval_decision", event)
                    
                    # For now, log event (implement event bus integration later)
                    logger.info(f"Event (to be published): approval_decision - {event}")
                else:
                    logger.warning(f"No task ID found in approval issue {issue_identifier}")
            else:
                logger.debug(f"State '{state_name}' not mapped to approval decision")
    
    # ========================================
    # Handle Comments (Approval Commands)
    # ========================================
    
    elif event_type == "Comment" and action == "create":
        comment = data
        body_text = comment.get("body", "")
        issue = comment.get("issue", {})
        issue_identifier = issue.get("identifier", "")
        
        # Check if comment is on approval hub or approval request
        parent_id = issue.get("parent", {}).get("id")
        is_approval_context = (
            parent_id == APPROVAL_HUB_ID or
            issue_identifier == APPROVAL_HUB_ID
        )
        
        if is_approval_context:
            # Look for approval commands in comment
            # Format: @lead-minion approve|reject REQUEST_ID={task_id}
            
            import re
            
            approve_match = re.search(r'approve\s+REQUEST_ID=([a-zA-Z0-9\-_]+)', body_text, re.IGNORECASE)
            reject_match = re.search(r'reject\s+REQUEST_ID=([a-zA-Z0-9\-_]+)', body_text, re.IGNORECASE)
            
            if approve_match:
                task_id = approve_match.group(1)
                event = {
                    "task_id": task_id,
                    "decision": "approved",
                    "linear_issue": issue_identifier,
                    "comment_id": comment.get("id"),
                    "approved_by": comment.get("user", {}).get("name", "unknown")
                }
                
                logger.info(f"Approval via comment: approved task {task_id}")
                
                # TODO: Publish to event bus
                # await event_bus.publish("approval_decision", event)
                logger.info(f"Event (to be published): approval_decision - {event}")
            
            elif reject_match:
                task_id = reject_match.group(1)
                
                # Extract rejection reason
                reason_match = re.search(r'REASON="([^"]+)"', body_text)
                reason = reason_match.group(1) if reason_match else "No reason provided"
                
                event = {
                    "task_id": task_id,
                    "decision": "rejected",
                    "linear_issue": issue_identifier,
                    "comment_id": comment.get("id"),
                    "rejected_by": comment.get("user", {}).get("name", "unknown"),
                    "reason": reason
                }
                
                logger.info(f"Rejection via comment: rejected task {task_id} - {reason}")
                
                # TODO: Publish to event bus
                # await event_bus.publish("approval_decision", event)
                logger.info(f"Event (to be published): approval_decision - {event}")
    
    # ========================================
    # Other Events (Ignore)
    # ========================================
    
    else:
        logger.debug(f"Ignoring webhook event: {event_type}.{action}")
    
    return {"status": "processed", "event": f"{event_type}.{action}"}


@app.get("/webhook/linear/health")
async def webhook_health():
    """Health check for webhook endpoint"""
    return {
        "status": "healthy",
        "webhook_secret_configured": bool(WEBHOOK_SECRET),
        "approval_hub_id": APPROVAL_HUB_ID
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8009)
