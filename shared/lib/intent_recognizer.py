"""
Intent Recognition for Conversational AI

Classifies user messages into actionable intents and extracts key parameters.
Uses LLM with structured output for natural language understanding.
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Import for config-based model selection
try:
    from langsmith import Client as LangSmithClient
    from langsmith import get_current_run_tree

    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    logger.warning("LangSmith not available - uncertainty sampling disabled")


class IntentType(str, Enum):
    """Supported intent categories."""

    TASK_SUBMISSION = "task_submission"  # "Add feature X", "Fix bug Y"
    STATUS_QUERY = "status_query"  # "What's the status of task-123?"
    CLARIFICATION = "clarification"  # Response to agent question
    APPROVAL_DECISION = "approval_decision"  # "Approve" or "Reject"
    GENERAL_QUERY = "general_query"  # "What can you do?"
    UNKNOWN = "unknown"  # Fallback for unclear inputs


class Intent(BaseModel):
    """Recognized intent with confidence and parameters."""

    type: IntentType = Field(..., description="Primary intent category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    needs_clarification: bool = Field(
        False, description="Whether more information is needed"
    )
    clarification_question: Optional[str] = Field(
        None, description="Question to ask user"
    )

    # Extracted parameters
    task_type: Optional[str] = Field(
        None, description="Agent to route to (feature-dev, code-review, etc.)"
    )
    task_description: Optional[str] = Field(
        None, description="Normalized task description"
    )
    entity_id: Optional[str] = Field(None, description="Task ID, approval ID, etc.")
    decision: Optional[str] = Field(None, description="approve or reject")

    # Context
    reasoning: str = Field(..., description="Why this intent was chosen")
    suggested_response: Optional[str] = Field(
        None, description="Suggested response to user"
    )


class IntentRecognizer:
    """
    Classify user messages into actionable intents using LLM.

    Uses structured output (JSON mode) for reliable parsing.
    Optimized for low latency with compressed prompts and conditional history.
    """

    # Compressed intent categories (schema-first approach)
    INTENT_SCHEMA = """
JSON API. Schema:
{type: enum[task_submission|status_query|clarification|approval_decision|general_query],
 confidence: float[0-1], needs_clarification: bool, 
 task_type: enum[feature-dev|code-review|infrastructure|cicd|documentation],
 reasoning: str}

Rules: confidence 0.9+ if clear, extract IDs from "task-xyz" patterns, prefer task_type=feature-dev for code
"""

    def __init__(self, llm_client=None):
        """
        Initialize intent recognizer.

        Args:
            llm_client: LLM client (from config) or Gradient client (legacy)
        """
        # Support both new config-based client and legacy gradient_client
        self.llm_client = llm_client
        self.langsmith_client = LangSmithClient() if LANGSMITH_AVAILABLE else None

    async def recognize(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        mode_hint: Optional[str] = None,
    ) -> Intent:
        """
        Recognize intent from user message with adaptive context loading.

        Two-pass approach:
        1. First pass: No history (fast, low tokens)
        2. Second pass: Include history only if confidence < 0.8

        Args:
            message: User's message
            conversation_history: Previous messages (for context)
            mode_hint: Optional mode hint ('ask' or 'agent') to bias classification

        Returns:
            Intent with type, confidence, and extracted parameters
        """
        # Check if LLM client is available
        has_llm = self.llm_client is not None and (
            hasattr(self.llm_client, "is_enabled")
            and self.llm_client.is_enabled()
            or not hasattr(self.llm_client, "is_enabled")
        )

        if not has_llm:
            logger.warning("LLM client not enabled - using fallback intent recognition")
            return self._fallback_recognize(message, mode_hint)

        # First pass: No history (fast)
        intent = await self._classify(message, history=None, mode_hint=mode_hint)

        # Second pass: Include history only if confidence < 0.8
        if intent.confidence < 0.8 or intent.needs_clarification:
            if conversation_history:
                intent = await self._classify(
                    message,
                    history=conversation_history[-3:],  # Last 3 turns only
                    mode_hint=mode_hint,
                )

        # Uncertainty sampling for active learning (Phase 5)
        if intent.confidence < 0.8 and LANGSMITH_AVAILABLE and self.langsmith_client:
            await self._flag_for_review(intent, message)

        return intent

    async def _classify(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
        mode_hint: Optional[str] = None,
    ) -> Intent:
        """
        Internal classification method with optional history.

        Args:
            message: User's message
            history: Optional conversation history (limited to recent turns)
            mode_hint: Optional mode hint

        Returns:
            Intent with classification results
        """
        # Build context from conversation history
        context = ""
        if history:
            context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])

        # Construct compressed prompt
        prompt = self._build_intent_prompt(message, context, mode_hint)

        try:
            # Use JSON mode for structured output
            if hasattr(self.llm_client, "complete"):
                # Gradient client or compatible interface
                response = await self.llm_client.complete(
                    prompt=prompt,
                    system_prompt=self.INTENT_SCHEMA,
                    temperature=0.1,  # Low temperature for consistent classification
                    max_tokens=512,
                )
                content = response.get("content", "")
            else:
                # Assume OpenRouter-compatible client
                response = await self.llm_client.chat(
                    messages=[
                        {"role": "system", "content": self.INTENT_SCHEMA},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,
                    max_tokens=512,
                )
                content = response.get("content", "")

            # Extract content from response dict and parse as JSON
            import json

            logger.debug(
                f"LLM response content: {content[:200]}..."
            )  # Log first 200 chars

            if not content or not content.strip():
                logger.warning("Empty response from LLM, using fallback")
                return self._fallback_recognize(message, mode_hint)

            intent_data = json.loads(content)

            # Validate and construct Intent
            intent = Intent(**intent_data)

            logger.info(
                f"Recognized intent: {intent.type} (confidence: {intent.confidence:.2f})"
            )

            return intent

        except Exception as e:
            logger.error(f"Intent recognition failed: {e}", exc_info=True)
            return self._fallback_recognize(message, mode_hint)

    async def _flag_for_review(self, intent: Intent, message: str):
        """
        Flag low-confidence predictions for manual review (Phase 5: Active Learning).

        Args:
            intent: Recognized intent with low confidence
            message: Original user message
        """
        try:
            current_trace = get_current_run_tree()

            if current_trace and self.langsmith_client:
                self.langsmith_client.create_feedback(
                    run_id=current_trace.id,
                    key="needs_review",
                    value=True,
                    comment=f"Low confidence ({intent.confidence:.2f}) - prioritize for annotation",
                    metadata={
                        "review_priority": (
                            "high" if intent.confidence < 0.6 else "medium"
                        ),
                        "intent_type": intent.type,
                        "add_to_training": True,
                        "message_preview": message[:100],
                    },
                )
                logger.debug(
                    f"Flagged trace for review (confidence: {intent.confidence:.2f})"
                )
        except Exception as e:
            logger.warning(f"Failed to flag trace for review: {e}")

    def _build_intent_prompt(
        self, message: str, context: str, mode_hint: Optional[str] = None
    ) -> str:
        """Build compressed prompt for intent recognition (schema-first approach)."""

        # Compressed mode guidance
        mode_guidance = ""
        if mode_hint == "ask":
            mode_guidance = "Mode: ASK (bias general_query for greetings/questions, task_submission needs >0.9 confidence)\n"
        elif mode_hint == "agent":
            mode_guidance = (
                "Mode: AGENT (bias task_submission, accept >0.6 confidence)\n"
            )

        # Minimal context (only if provided)
        context_str = f"Context:\n{context}\n" if context else ""

        # Compressed prompt (60% token reduction)
        prompt = f"""{mode_guidance}{context_str}Message: \"{message}\"

Classify intent. Extract task-ID patterns. Return JSON:
{{"type": "...", "confidence": 0.95, "needs_clarification": false, "task_type": "...", "task_description": "...", "entity_id": null, "decision": null, "reasoning": "brief", "suggested_response": null}}"""

        return prompt

    def _fallback_recognize(
        self, message: str, mode_hint: Optional[str] = None
    ) -> Intent:
        """Simple keyword-based fallback when LLM is unavailable."""

        message_lower = message.lower()

        # Approval decision keywords
        if any(
            word in message_lower for word in ["approve", "yes", "go ahead", "proceed"]
        ):
            return Intent(
                type=IntentType.APPROVAL_DECISION,
                confidence=0.8,
                decision="approve",
                reasoning="Keyword match: approval language detected",
                suggested_response="Approval recorded. Resuming workflow...",
            )

        if any(word in message_lower for word in ["reject", "no", "cancel", "stop"]):
            return Intent(
                type=IntentType.APPROVAL_DECISION,
                confidence=0.8,
                decision="reject",
                reasoning="Keyword match: rejection language detected",
                suggested_response="Rejection recorded. Canceling workflow...",
            )

        # Mode-aware fallback logic
        if mode_hint == "ask":
            # In Ask mode, bias toward general_query for short/ambiguous messages
            if len(message.split()) <= 5:  # Short messages
                return Intent(
                    type=IntentType.GENERAL_QUERY,
                    confidence=0.7,
                    reasoning="Fallback (Ask mode): Short message, likely informational query",
                    suggested_response="I can help you with:\n- Creating tasks (feature development, code review, infrastructure, CI/CD, documentation)\n- Checking task status\n- Approving/rejecting requests\n\nWhat would you like to do?",
                )

        elif mode_hint == "agent":
            # In Agent mode, bias toward task_submission for action-oriented messages
            action_words = [
                "add",
                "implement",
                "create",
                "fix",
                "update",
                "deploy",
                "build",
                "refactor",
                "test",
            ]
            if any(word in message_lower for word in action_words):
                return Intent(
                    type=IntentType.TASK_SUBMISSION,
                    confidence=0.75,  # Higher confidence in Agent mode
                    task_description=message,
                    reasoning="Fallback (Agent mode): Action verb detected, user expects task execution",
                    suggested_response=None,
                )

        # Status query keywords
        if any(
            word in message_lower
            for word in ["status", "progress", "what's happening", "update"]
        ):
            # Try to extract task ID
            import re

            task_id_match = re.search(r"(task-[\w-]+|PR-\d+|approval-[\w-]+)", message)
            entity_id = task_id_match.group(1) if task_id_match else None

            return Intent(
                type=IntentType.STATUS_QUERY,
                confidence=0.7,
                entity_id=entity_id,
                reasoning="Keyword match: status query detected",
                suggested_response=(
                    f"Looking up status for {entity_id}..."
                    if entity_id
                    else "Which task would you like to check?"
                ),
            )

        # Task submission (default for most messages)
        if len(message.split()) > 3:  # More than 3 words suggests a task description
            # Adjust confidence based on mode
            confidence = 0.7 if mode_hint == "agent" else 0.6
            needs_clarification = (
                mode_hint != "agent"
            )  # Less clarification needed in Agent mode

            return Intent(
                type=IntentType.TASK_SUBMISSION,
                confidence=confidence,
                needs_clarification=needs_clarification,
                clarification_question=(
                    "Which agent should handle this? (feature-dev, code-review, infrastructure, cicd, documentation)"
                    if needs_clarification
                    else None
                ),
                task_description=message,
                reasoning=f"Fallback: message looks like a task description (mode_hint={mode_hint})",
                suggested_response=None,
            )

        # General query (short messages)
        return Intent(
            type=IntentType.GENERAL_QUERY,
            confidence=0.5,
            reasoning="Fallback: unclear intent",
            suggested_response="I can help you with:\n- Creating tasks (feature development, code review, infrastructure, CI/CD, documentation)\n- Checking task status\n- Approving/rejecting requests\n\nWhat would you like to do?",
        )


async def intent_to_task(
    intent: Intent, conversation_history: List[Dict[str, str]]
) -> Dict[str, Any]:
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
            "conversation_id": (
                conversation_history[-1].get("session_id")
                if conversation_history
                else None
            ),
        },
    }

    # Extract additional context from conversation
    if conversation_history:
        relevant_context = "\n".join(
            [
                msg["content"]
                for msg in conversation_history[-3:]
                if msg["role"] == "user"
            ]
        )
        task_request["context"] = relevant_context

    return task_request


def get_intent_recognizer(llm_client=None, gradient_client=None) -> IntentRecognizer:
    """Get intent recognizer singleton.

    Args:
        llm_client: LLM client from config (preferred)
        gradient_client: Legacy Gradient client (fallback)

    Returns:
        IntentRecognizer instance
    """
    client = llm_client if llm_client is not None else gradient_client
    return IntentRecognizer(client)
