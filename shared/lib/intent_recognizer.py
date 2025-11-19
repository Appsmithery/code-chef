"""
Intent Recognition for Conversational AI

Classifies user messages into actionable intents and extracts key parameters.
Uses Gradient AI for natural language understanding with structured output.
"""

import logging
from typing import List, Dict, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Supported intent categories."""
    TASK_SUBMISSION = "task_submission"      # "Add feature X", "Fix bug Y"
    STATUS_QUERY = "status_query"            # "What's the status of task-123?"
    CLARIFICATION = "clarification"          # Response to agent question
    APPROVAL_DECISION = "approval_decision"  # "Approve" or "Reject"
    GENERAL_QUERY = "general_query"          # "What can you do?"
    UNKNOWN = "unknown"                      # Fallback for unclear inputs


class Intent(BaseModel):
    """Recognized intent with confidence and parameters."""
    type: IntentType = Field(..., description="Primary intent category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    needs_clarification: bool = Field(False, description="Whether more information is needed")
    clarification_question: Optional[str] = Field(None, description="Question to ask user")
    
    # Extracted parameters
    task_type: Optional[str] = Field(None, description="Agent to route to (feature-dev, code-review, etc.)")
    task_description: Optional[str] = Field(None, description="Normalized task description")
    entity_id: Optional[str] = Field(None, description="Task ID, approval ID, etc.")
    decision: Optional[str] = Field(None, description="approve or reject")
    
    # Context
    reasoning: str = Field(..., description="Why this intent was chosen")
    suggested_response: Optional[str] = Field(None, description="Suggested response to user")


class IntentRecognizer:
    """
    Classify user messages into actionable intents using LLM.
    
    Uses structured output (JSON mode) for reliable parsing.
    """
    
    INTENT_CATEGORIES = [
        "task_submission - User wants to create a new task (e.g., 'Add error handling to login')",
        "status_query - User wants to check task status (e.g., 'What's the status of task-abc123?')",
        "clarification - User is responding to an agent's question (e.g., 'Use PostgreSQL')",
        "approval_decision - User is approving/rejecting a request (e.g., 'Approve', 'Yes, go ahead')",
        "general_query - User has a general question (e.g., 'What can you do?', 'How does this work?')",
    ]
    
    TASK_TYPES = [
        "feature-dev - New features, bug fixes, code changes",
        "code-review - Pull request reviews, code quality checks",
        "infrastructure - Deployments, scaling, configuration",
        "cicd - Pipeline updates, workflow automation",
        "documentation - README updates, API docs, guides",
    ]
    
    def __init__(self, gradient_client):
        """
        Initialize intent recognizer.
        
        Args:
            gradient_client: Gradient AI client for LLM inference
        """
        self.gradient_client = gradient_client
    
    async def recognize(
        self, 
        message: str, 
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Intent:
        """
        Recognize intent from user message.
        
        Args:
            message: User's message
            conversation_history: Previous messages (for context)
            
        Returns:
            Intent with type, confidence, and extracted parameters
        """
        if not self.gradient_client.is_enabled():
            logger.warning("Gradient client not enabled - using fallback intent recognition")
            return self._fallback_recognize(message)
        
        # Build context from conversation history
        context = ""
        if conversation_history:
            recent_messages = conversation_history[-5:]  # Last 5 turns
            context = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in recent_messages
            ])
        
        # Construct prompt for intent recognition
        prompt = self._build_intent_prompt(message, context)
        
        try:
            # Use JSON mode for structured output
            response = await self.gradient_client.complete(
                prompt=prompt,
                system_prompt="You are a JSON-only API. Respond ONLY with valid JSON, no markdown, no explanations.",
                temperature=0.1,  # Low temperature for consistent classification
                max_tokens=500
            )
            
            # Extract content from response dict and parse as JSON
            import json
            content = response.get("content", "")
            logger.debug(f"LLM response content: {content[:200]}...")  # Log first 200 chars
            
            if not content or not content.strip():
                logger.warning("Empty response from LLM, using fallback")
                return self._fallback_recognize(message)
            
            intent_data = json.loads(content)
            
            # Validate and construct Intent
            intent = Intent(**intent_data)
            
            logger.info(f"Recognized intent: {intent.type} (confidence: {intent.confidence:.2f})")
            
            return intent
            
        except Exception as e:
            logger.error(f"Intent recognition failed: {e}", exc_info=True)
            return self._fallback_recognize(message)
    
    def _build_intent_prompt(self, message: str, context: str) -> str:
        """Build prompt for intent recognition."""
        
        prompt = f"""You are an intent recognition system for a DevOps AI agent platform.

Your task: Classify the user's message into ONE of these intent categories:

{chr(10).join(f"- {cat}" for cat in self.INTENT_CATEGORIES)}

If the intent is "task_submission", also identify the task type:

{chr(10).join(f"- {ttype}" for ttype in self.TASK_TYPES)}

Conversation context:
{context if context else "(No prior conversation)"}

User's message:
"{message}"

Analyze the message and respond with a JSON object following this schema:

{{
  "type": "task_submission|status_query|clarification|approval_decision|general_query",
  "confidence": 0.95,
  "needs_clarification": false,
  "clarification_question": null,
  "task_type": "feature-dev|code-review|infrastructure|cicd|documentation|null",
  "task_description": "normalized task description or null",
  "entity_id": "extracted task ID, approval ID, or null",
  "decision": "approve|reject|null (only for approval_decision)",
  "reasoning": "brief explanation of why this intent was chosen",
  "suggested_response": "suggested response to the user or null"
}}

Guidelines:
- Set confidence to 0.9+ if very clear, 0.5-0.9 if ambiguous
- Set needs_clarification=true if critical information is missing
- Extract entity_id from patterns like "task-abc123", "PR-56", "approval-xyz"
- For task_submission, normalize the description to be clear and actionable
- For approval_decision, look for keywords like "approve", "reject", "yes", "no", "go ahead", "cancel"

Respond ONLY with the JSON object, no other text."""
        
        return prompt
    
    def _fallback_recognize(self, message: str) -> Intent:
        """Simple keyword-based fallback when LLM is unavailable."""
        
        message_lower = message.lower()
        
        # Approval decision keywords
        if any(word in message_lower for word in ["approve", "yes", "go ahead", "proceed"]):
            return Intent(
                type=IntentType.APPROVAL_DECISION,
                confidence=0.8,
                decision="approve",
                reasoning="Keyword match: approval language detected",
                suggested_response="Approval recorded. Resuming workflow..."
            )
        
        if any(word in message_lower for word in ["reject", "no", "cancel", "stop"]):
            return Intent(
                type=IntentType.APPROVAL_DECISION,
                confidence=0.8,
                decision="reject",
                reasoning="Keyword match: rejection language detected",
                suggested_response="Rejection recorded. Canceling workflow..."
            )
        
        # Status query keywords
        if any(word in message_lower for word in ["status", "progress", "what's happening", "update"]):
            # Try to extract task ID
            import re
            task_id_match = re.search(r'(task-[\w-]+|PR-\d+|approval-[\w-]+)', message)
            entity_id = task_id_match.group(1) if task_id_match else None
            
            return Intent(
                type=IntentType.STATUS_QUERY,
                confidence=0.7,
                entity_id=entity_id,
                reasoning="Keyword match: status query detected",
                suggested_response=f"Looking up status for {entity_id}..." if entity_id else "Which task would you like to check?"
            )
        
        # Task submission (default for most messages)
        if len(message.split()) > 3:  # More than 3 words suggests a task description
            return Intent(
                type=IntentType.TASK_SUBMISSION,
                confidence=0.6,
                needs_clarification=True,
                clarification_question="Which agent should handle this? (feature-dev, code-review, infrastructure, cicd, documentation)",
                task_description=message,
                reasoning="Fallback: message looks like a task description",
                suggested_response=None
            )
        
        # General query (short messages)
        return Intent(
            type=IntentType.GENERAL_QUERY,
            confidence=0.5,
            reasoning="Fallback: unclear intent",
            suggested_response="I can help you with:\n- Creating tasks (feature development, code review, infrastructure, CI/CD, documentation)\n- Checking task status\n- Approving/rejecting requests\n\nWhat would you like to do?"
        )


async def intent_to_task(intent: Intent, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Convert recognized intent into task request payload for /orchestrate endpoint.
    
    Args:
        intent: Recognized intent
        conversation_history: Conversation context
        
    Returns:
        Task request dict for /orchestrate endpoint
    """
    if intent.type != IntentType.TASK_SUBMISSION:
        raise ValueError(f"Cannot convert intent type {intent.type} to task")
    
    if not intent.task_type:
        raise ValueError("Task type not specified in intent")
    
    # Build task request
    task_request = {
        "description": intent.task_description or "User-requested task",
        "agent": intent.task_type,
        "priority": "medium",  # Default priority
        "metadata": {
            "source": "chat",
            "intent_confidence": intent.confidence,
            "conversation_id": conversation_history[-1].get("session_id") if conversation_history else None
        }
    }
    
    # Extract additional context from conversation
    if conversation_history:
        relevant_context = "\n".join([
            msg["content"] 
            for msg in conversation_history[-3:] 
            if msg["role"] == "user"
        ])
        task_request["context"] = relevant_context
    
    return task_request


def get_intent_recognizer(gradient_client) -> IntentRecognizer:
    """Get intent recognizer singleton."""
    return IntentRecognizer(gradient_client)
