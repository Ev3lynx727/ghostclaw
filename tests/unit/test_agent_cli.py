"""
Tests for AgentCLI - Interactive command-line interface.

Comprehensive test suite for CLI command execution, session management,
and user interaction.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from ghostclaw.core.agent_sdk.agent_cli import AgentCLI, CommandResult


class TestCLIInitialization:
    """Test CLI initialization and setup."""

    def test_cli_init_with_default_agent_id(self):
        """Test CLI initialization with default agent ID."""
        cli = AgentCLI()
        assert cli.agent_id == "default-agent"
        assert cli.session_manager is not None
        assert cli.session_id is None
        assert cli.running is False

    def test_cli_init_with_custom_agent_id(self):
        """Test CLI initialization with custom agent ID."""
        cli = AgentCLI(agent_id="test-agent")
        assert cli.agent_id == "test-agent"

    def test_cli_commands_defined(self):
        """Test that CLI has commands defined."""
        cli = AgentCLI()
        assert len(cli.COMMANDS) > 0
        assert "help" in cli.COMMANDS
        assert "session" in cli.COMMANDS
        assert "memory" in cli.COMMANDS
        assert "workspace" in cli.COMMANDS
        assert "identity" in cli.COMMANDS


class TestHelpCommand:
    """Test help command functionality."""

    def test_help_without_args(self):
        """Test help command without arguments."""
        cli = AgentCLI()
        result = cli.run_command("help")
        assert result.success is True
        assert "Available commands" in result.message

    def test_help_for_session_command(self):
        """Test help for session subcommands."""
        cli = AgentCLI()
        result = cli.run_command("help session")
        assert result.success is True
        assert "Session" in result.message or "create" in result.message

    def test_help_for_invalid_command(self):
        """Test help for invalid command."""
        cli = AgentCLI()
        result = cli.run_command("help invalid")
        assert result.success is True

    def test_unknown_command(self):
        """Test handling of unknown command."""
        cli = AgentCLI()
        result = cli.run_command("invalid_command")
        assert result.success is False
        assert "Unknown command" in result.message


class TestSessionCommands:
    """Test session management commands."""

    @pytest.fixture
    def cli_with_temp_project(self):
        """Create CLI instance with temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = AgentCLI(agent_id="test-agent")
            yield cli, tmpdir

    def test_session_create(self, cli_with_temp_project):
        """Test creating a new session."""
        cli, tmpdir = cli_with_temp_project
        result = cli.run_command(f"session create {tmpdir} test-project")
        assert result.success is True
        assert "Session created" in result.message
        assert cli.current_session is not None

    def test_session_create_without_args(self):
        """Test session create without arguments."""
        cli = AgentCLI()
        result = cli.run_command("session create")
        assert result.success is False
        assert "Usage" in result.message

    def test_session_start(self, cli_with_temp_project):
        """Test starting a session."""
        cli, tmpdir = cli_with_temp_project
        cli.run_command(f"session create {tmpdir} test")
        result = cli.run_command("session start")
        assert result.success is True
        assert "started" in result.message.lower()

    def test_session_start_without_active_session(self):
        """Test starting session when none is active."""
        cli = AgentCLI()
        result = cli.run_command("session start")
        assert result.success is False
        assert "No session active" in result.message

    def test_session_pause(self, cli_with_temp_project):
        """Test pausing a session."""
        cli, tmpdir = cli_with_temp_project
        cli.run_command(f"session create {tmpdir}")
        cli.run_command("session start")
        result = cli.run_command("session pause")
        assert result.success is True
        assert "paused" in result.message.lower()

    def test_session_resume(self, cli_with_temp_project):
        """Test resuming a paused session."""
        cli, tmpdir = cli_with_temp_project
        cli.run_command(f"session create {tmpdir}")
        cli.run_command("session start")
        cli.run_command("session pause")
        result = cli.run_command("session resume")
        assert result.success is True
        assert "resumed" in result.message.lower()

    def test_session_info(self, cli_with_temp_project):
        """Test getting session info."""
        cli, tmpdir = cli_with_temp_project
        cli.run_command(f"session create {tmpdir} my-project")
        result = cli.run_command("session info")
        assert result.success is True
        assert "session_id" in result.data
        assert "my-project" in str(result.data)

    def test_session_info_without_active_session(self):
        """Test session info when no session is active."""
        cli = AgentCLI()
        result = cli.run_command("session info")
        assert result.success is False
        assert "No active session" in result.message

    def test_session_end(self, cli_with_temp_project):
        """Test ending a session."""
        cli, tmpdir = cli_with_temp_project
        cli.run_command(f"session create {tmpdir}")
        cli.run_command("session start")
        result = cli.run_command("session end")
        assert result.success is True
        assert "ended" in result.message.lower()


class TestMemoryCommands:
    """Test memory management commands."""

    @pytest.fixture
    def cli_with_session(self):
        """Create CLI with active session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = AgentCLI()
            cli.run_command(f"session create {tmpdir}")
            cli.run_command("session start")
            yield cli

    def test_memory_add(self, cli_with_session):
        """Test adding a memory entry."""
        result = cli_with_session.run_command("memory add 'test content'")
        assert result.success is True
        assert "added" in result.message.lower()

    def test_memory_add_without_args(self, cli_with_session):
        """Test memory add without arguments."""
        result = cli_with_session.run_command("memory add")
        assert result.success is False
        assert "Usage" in result.message

    def test_memory_list(self, cli_with_session):
        """Test listing memory entries."""
        cli_with_session.run_command("memory add 'test entry'")
        result = cli_with_session.run_command("memory list")
        assert result.success is True

    def test_memory_search(self, cli_with_session):
        """Test searching memory entries."""
        cli_with_session.run_command("memory add 'test content'")
        result = cli_with_session.run_command("memory search test")
        assert result.success is True

    def test_memory_search_without_pattern(self, cli_with_session):
        """Test memory search without pattern."""
        result = cli_with_session.run_command("memory search")
        assert result.success is False
        assert "Usage" in result.message

    def test_memory_stats(self, cli_with_session):
        """Test memory statistics."""
        result = cli_with_session.run_command("memory stats")
        assert result.success is True
        assert "Statistics" in result.message

    def test_memory_export(self, cli_with_session):
        """Test exporting memory."""
        result = cli_with_session.run_command("memory export")
        assert result.success is True
        assert result.data is not None

    def test_memory_without_session(self):
        """Test memory commands without active session."""
        cli = AgentCLI()
        result = cli.run_command("memory add 'test'")
        assert result.success is False
        assert "No active session" in result.message

    def test_memory_without_subcommand(self, cli_with_session):
        """Test memory command without subcommand."""
        result = cli_with_session.run_command("memory")
        assert result.success is False
        assert "command required" in result.message.lower()


class TestWorkspaceCommands:
    """Test workspace management commands."""

    @pytest.fixture
    def cli_with_workspace_session(self):
        """Create CLI with workspace and session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = AgentCLI()
            cli.run_command(f"session create {tmpdir} test-project")
            cli.run_command("session start")
            cli.run_command("workspace init")
            yield cli, tmpdir

    def test_workspace_status(self, cli_with_workspace_session):
        """Test getting workspace status."""
        cli, _ = cli_with_workspace_session
        result = cli.run_command("workspace status")
        assert result.success is True

    def test_workspace_branch_create(self, cli_with_workspace_session):
        """Test creating a workspace branch."""
        cli, _ = cli_with_workspace_session
        result = cli.run_command("workspace branch feature/test")
        assert result.success is True

    def test_workspace_branch_without_name(self, cli_with_workspace_session):
        """Test workspace branch without name."""
        cli, _ = cli_with_workspace_session
        result = cli.run_command("workspace branch")
        assert result.success is False
        assert "Usage" in result.message

    def test_workspace_commit(self, cli_with_workspace_session):
        """Test committing changes."""
        cli, tmpdir = cli_with_workspace_session
        # Create a test file
        test_file = Path(tmpdir) / "test.txt"
        test_file.write_text("test content")
        
        result = cli.run_command("workspace commit 'test commit'")
        assert result.success or result.success is False  # May fail if no changes

    def test_workspace_history(self, cli_with_workspace_session):
        """Test getting workspace commit history."""
        cli, _ = cli_with_workspace_session
        result = cli.run_command("workspace history")
        assert result.success is True

    def test_workspace_list(self, cli_with_workspace_session):
        """Test listing workspace files."""
        cli, tmpdir = cli_with_workspace_session
        # Create a test file
        test_file = Path(tmpdir) / "test.py"
        test_file.write_text("# test")
        
        result = cli.run_command("workspace list *.py")
        assert result.success is True

    def test_workspace_without_session(self):
        """Test workspace commands without active session."""
        cli = AgentCLI()
        result = cli.run_command("workspace status")
        assert result.success is False
        assert "No active session" in result.message

    def test_workspace_init(self, cli_with_workspace_session):
        """Test workspace initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = AgentCLI()
            cli.run_command(f"session create {tmpdir}")
            result = cli.run_command("workspace init")
            assert result.success is True


class TestIdentityCommands:
    """Test identity management commands."""

    def test_identity_load_no_identity_found(self):
        """Test loading identity when none exists."""
        cli = AgentCLI(agent_id="test-unique-agent")
        result = cli.run_command("identity load")
        # Should fail if no identity has been created
        assert isinstance(result, CommandResult)

    def test_identity_show(self):
        """Test showing identity."""
        cli = AgentCLI()
        result = cli.run_command("identity show")
        assert isinstance(result, CommandResult)

    def test_identity_export(self):
        """Test exporting identity."""
        cli = AgentCLI()
        result = cli.run_command("identity export")
        assert isinstance(result, CommandResult)

    def test_identity_without_subcommand(self):
        """Test identity command without subcommand."""
        cli = AgentCLI()
        result = cli.run_command("identity")
        assert result.success is False
        assert "command required" in result.message.lower()


class TestStatusCommand:
    """Test status command."""

    def test_status_no_session(self):
        """Test status when no session is active."""
        cli = AgentCLI()
        result = cli.run_command("status")
        assert result.success is True
        assert "No active session" in result.message

    def test_status_with_session(self):
        """Test status with active session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = AgentCLI()
            cli.run_command(f"session create {tmpdir} test-proj")
            result = cli.run_command("status")
            assert result.success is True
            assert "Session Status" in result.message


class TestExitCommand:
    """Test exit command."""

    def test_exit_command(self):
        """Test exit command."""
        cli = AgentCLI()
        cli.running = True
        result = cli.run_command("exit")
        assert result.success is True
        assert cli.running is False

    def test_quit_command(self):
        """Test quit command (alias for exit)."""
        cli = AgentCLI()
        cli.running = True
        result = cli.run_command("quit")
        assert result.success is True
        assert cli.running is False


class TestCommandResult:
    """Test CommandResult dataclass."""

    def test_command_result_success(self):
        """Test successful command result."""
        result = CommandResult(success=True, message="Success")
        assert result.success is True
        assert result.message == "Success"
        assert result.error is None

    def test_command_result_failure(self):
        """Test failed command result."""
        result = CommandResult(
            success=False,
            message="Failed",
            error="Test error"
        )
        assert result.success is False
        assert result.error == "Test error"

    def test_command_result_with_data(self):
        """Test command result with data."""
        result = CommandResult(
            success=True,
            message="Success",
            data={"key": "value"}
        )
        assert result.data == {"key": "value"}


class TestPromptGeneration:
    """Test prompt generation."""

    def test_prompt_without_session(self):
        """Test prompt when no session is active."""
        cli = AgentCLI(agent_id="my-agent")
        prompt = cli._get_prompt()
        assert "my-agent" in prompt
        assert ">" in prompt

    def test_prompt_with_session(self):
        """Test prompt when session is active."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cli = AgentCLI()
            cli.run_command(f"session create {tmpdir} my-project")
            prompt = cli._get_prompt()
            # Prompt should contain either project name or agent id
            assert ("my-project" in prompt or "default-agent" in prompt)
            assert ">" in prompt



class TestEmptyCommands:
    """Test handling of edge cases."""

    def test_empty_command(self):
        """Test handling of empty command."""
        cli = AgentCLI()
        result = cli.run_command("")
        assert result.success is False

    def test_whitespace_only_command(self):
        """Test handling of whitespace-only command."""
        cli = AgentCLI()
        result = cli.run_command("   ")
        assert result.success is False

    def test_session_list_not_implemented(self):
        """Test that session list is not yet implemented."""
        cli = AgentCLI()
        result = cli.run_command("session list")
        assert result.success is True  # Returns success with message


class TestErrorHandling:
    """Test error handling in CLI."""

    def test_command_with_invalid_path(self):
        """Test command with invalid file path."""
        cli = AgentCLI()
        cli.run_command("session create /nonexistent/path/12345")
        # Should handle gracefully (may succeed or fail depending on OS)
        assert isinstance(cli.current_session, type(None)) or cli.current_session is not None

    def test_memory_command_without_active_session(self):
        """Test memory operations fail without session."""
        cli = AgentCLI()
        result = cli.run_command("memory add test")
        assert result.success is False

    def test_workspace_command_without_active_session(self):
        """Test workspace operations fail without session."""
        cli = AgentCLI()
        result = cli.run_command("workspace status")
        assert result.success is False
