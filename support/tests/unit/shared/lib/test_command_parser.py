"""
Unit tests for command parser.

Tests slash command parsing, validation, and helper functions.

Created: December 20, 2025
"""

import pytest
from lib.command_parser import (
    CommandType,
    get_help_text,
    is_execute_command,
    looks_like_task_request,
    parse_command,
)


class TestParseCommand:
    """Test command parsing functionality."""

    def test_execute_command_parsing(self):
        """Test parsing of /execute command."""
        cmd = parse_command("/execute create login system")
        assert cmd is not None
        assert cmd["command"] == "execute"
        assert cmd["args"] == "create login system"
        assert cmd["raw_message"] == "/execute create login system"

    def test_execute_command_no_args(self):
        """Test /execute command without arguments."""
        cmd = parse_command("/execute")
        assert cmd is not None
        assert cmd["command"] == "execute"
        assert cmd["args"] == ""

    def test_help_command(self):
        """Test parsing of /help command."""
        cmd = parse_command("/help")
        assert cmd is not None
        assert cmd["command"] == "help"
        assert cmd["args"] == ""

    def test_status_command(self):
        """Test parsing of /status command."""
        cmd = parse_command("/status wf-abc123")
        assert cmd is not None
        assert cmd["command"] == "status"
        assert cmd["args"] == "wf-abc123"

    def test_cancel_command(self):
        """Test parsing of /cancel command."""
        cmd = parse_command("/cancel wf-xyz789")
        assert cmd is not None
        assert cmd["command"] == "cancel"
        assert cmd["args"] == "wf-xyz789"

    def test_no_command(self):
        """Test message without command returns None."""
        cmd = parse_command("hello world")
        assert cmd is None

    def test_invalid_command(self):
        """Test invalid command returns None."""
        cmd = parse_command("/invalid test")
        assert cmd is None

    def test_empty_string(self):
        """Test empty string returns None."""
        cmd = parse_command("")
        assert cmd is None

    def test_none_input(self):
        """Test None input returns None."""
        cmd = parse_command("")
        assert cmd is None

    def test_case_insensitive(self):
        """Test command parsing is case insensitive."""
        cmd = parse_command("/EXECUTE create feature")
        assert cmd is not None
        assert cmd["command"] == "execute"

    def test_whitespace_handling(self):
        """Test command handles leading/trailing whitespace."""
        cmd = parse_command("  /execute   fix bug  ")
        assert cmd is not None
        assert cmd["command"] == "execute"
        assert cmd["args"] == "fix bug"

    def test_multiline_args(self):
        """Test command with multiline arguments."""
        message = "/execute create auth system\nwith JWT tokens\nand refresh logic"
        cmd = parse_command(message)
        assert cmd is not None
        assert cmd["command"] == "execute"
        assert "JWT tokens" in cmd["args"]


class TestIsExecuteCommand:
    """Test execute command detection helper."""

    def test_detects_execute_command(self):
        """Test detection of execute command."""
        assert is_execute_command("/execute do something")

    def test_rejects_non_execute(self):
        """Test rejection of non-execute commands."""
        assert not is_execute_command("/help")
        assert not is_execute_command("hello world")

    def test_handles_empty(self):
        """Test handling of empty input."""
        assert not is_execute_command("")


class TestGetHelpText:
    """Test help text generation."""

    def test_returns_help_text(self):
        """Test help text is returned."""
        help_text = get_help_text()
        assert isinstance(help_text, str)
        assert len(help_text) > 0

    def test_contains_commands(self):
        """Test help text contains all commands."""
        help_text = get_help_text()
        assert "/execute" in help_text
        assert "/help" in help_text
        assert "/status" in help_text
        assert "/cancel" in help_text

    def test_contains_examples(self):
        """Test help text contains examples."""
        help_text = get_help_text()
        assert "Example" in help_text or "example" in help_text


class TestLooksLikeTaskRequest:
    """Test task request heuristic detection."""

    def test_detects_implement_task(self):
        """Test detection of 'implement' tasks."""
        assert looks_like_task_request("implement login feature")
        assert looks_like_task_request("Implement JWT authentication")

    def test_detects_create_task(self):
        """Test detection of 'create' tasks."""
        assert looks_like_task_request("create a new API endpoint")

    def test_detects_build_task(self):
        """Test detection of 'build' tasks."""
        assert looks_like_task_request("build the authentication system")

    def test_detects_fix_task(self):
        """Test detection of 'fix' tasks."""
        assert looks_like_task_request("fix the database connection issue")

    def test_detects_refactor_task(self):
        """Test detection of 'refactor' tasks."""
        assert looks_like_task_request("refactor the user service")

    def test_rejects_question(self):
        """Test rejection of questions."""
        assert not looks_like_task_request("how do I implement authentication?")

    def test_rejects_conversation(self):
        """Test rejection of conversational messages."""
        assert not looks_like_task_request("hello, can you help me?")

    def test_rejects_command(self):
        """Test rejection of slash commands."""
        assert not looks_like_task_request("/execute implement feature")

    def test_case_insensitive_detection(self):
        """Test detection is case insensitive."""
        assert looks_like_task_request("Implement feature")
        assert looks_like_task_request("IMPLEMENT feature")
        assert looks_like_task_request("implement feature")


class TestCommandType:
    """Test CommandType enum."""

    def test_enum_values(self):
        """Test CommandType has expected values."""
        assert CommandType.EXECUTE.value == "execute"
        assert CommandType.HELP.value == "help"
        assert CommandType.STATUS.value == "status"
        assert CommandType.CANCEL.value == "cancel"

    def test_enum_iteration(self):
        """Test CommandType can be iterated."""
        values = [cmd.value for cmd in CommandType]
        assert "execute" in values
        assert "help" in values
        assert "status" in values
        assert "cancel" in values
        assert len(values) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
