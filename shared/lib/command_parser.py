"""
Command Parser for slash commands in code-chef.

Parses user messages for slash commands like /execute, /help, /status, /cancel.
This enables explicit command-driven interaction instead of relying on LLM
intent detection.

Created: December 20, 2025
Status: Active
"""

import logging
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CommandType(str, Enum):
    """Supported slash commands."""

    EXECUTE = "execute"
    HELP = "help"
    STATUS = "status"
    CANCEL = "cancel"


def parse_command(message: str) -> Optional[Dict]:
    """
    Parse slash commands from user messages.

    Supported commands:
    - /execute <task description>  - Submit task for agent execution
    - /help                        - Show help message
    - /status <workflow_id>        - Check workflow status
    - /cancel <workflow_id>        - Cancel running workflow

    Args:
        message: User message to parse

    Returns:
        Dict with command, args, raw_message if valid command found
        None if no valid command detected

    Examples:
        >>> parse_command("/execute create login system")
        {
            "command": "execute",
            "args": "create login system",
            "raw_message": "/execute create login system"
        }

        >>> parse_command("hello world")
        None

        >>> parse_command("/help")
        {
            "command": "help",
            "args": "",
            "raw_message": "/help"
        }
    """
    if not message or not isinstance(message, str):
        return None

    message = message.strip()

    # Must start with /
    if not message.startswith("/"):
        return None

    # Split on first whitespace to get command and args
    parts = message.split(maxsplit=1)
    command = parts[0][1:].lower()  # Remove / and normalize
    args = parts[1] if len(parts) > 1 else ""

    # Validate command
    if command not in [cmd.value for cmd in CommandType]:
        logger.debug(f"Unknown command: {command}")
        return None

    logger.info(f"Parsed command: {command} with args: {args[:50]}...")

    return {"command": command, "args": args, "raw_message": message}


def is_execute_command(message: str) -> bool:
    """
    Quick check if message is an execute command.

    Args:
        message: User message to check

    Returns:
        True if message is /execute command
    """
    cmd = parse_command(message)
    return cmd is not None and cmd["command"] == CommandType.EXECUTE.value


def get_help_text() -> str:
    """
    Get help text for available commands.

    Returns:
        Formatted help text string
    """
    return """
**Available Commands:**

• `/execute <task>` - Submit task for agent execution
  Example: /execute Implement JWT authentication with refresh tokens

• `/status <workflow_id>` - Check workflow status
  Example: /status wf-abc123

• `/cancel <workflow_id>` - Cancel running workflow
  Example: /cancel wf-abc123

• `/help` - Show this message

**Tips:**
- Use `/execute` for tasks that require agent work (code implementation, reviews, deployments)
- Regular chat messages (without /) are for questions and conversation
- Each `/execute` creates a Linear issue for tracking
""".strip()


def looks_like_task_request(message: str) -> bool:
    """
    Heuristic check if message looks like a task request without /execute.

    This can be used to provide hints to users about using /execute.

    Args:
        message: User message to analyze

    Returns:
        True if message looks like a task request
    """
    # Skip if already a command
    if message.strip().startswith("/"):
        return False

    message_lower = message.lower()

    # Explicitly conversational (should NOT trigger task hint)
    conversational_keywords = [
        "explain",
        "describe",
        "tell me",
        "what is",
        "what are",
        "how does",
        "how do",
        "why",
        "when",
        "where",
        "which",
        "who",
        "can you explain",
        "help me understand",
    ]

    # Check if it's conversational first
    for pattern in conversational_keywords:
        if message_lower.startswith(pattern):
            return False

    # Common task indicators (comprehensive list)
    task_keywords = [
        # Core actions
        "implement",
        "create",
        "build",
        "add",
        "write",
        "develop",
        "fix",
        "refactor",
        "update",
        "deploy",
        "setup",
        "configure",
        "review",
        "test",
        "migrate",
        # Modification verbs
        "modify",
        "change",
        "edit",
        "delete",
        "remove",
        # Improvement verbs
        "improve",
        "optimize",
        "enhance",
        "upgrade",
    ]

    # Check if message starts with imperative verb
    for keyword in task_keywords:
        if message_lower.startswith(keyword):
            return True

    return False
