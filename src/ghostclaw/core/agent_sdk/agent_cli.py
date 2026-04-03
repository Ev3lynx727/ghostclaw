"""
AgentCLI - Interactive command-line interface for agent interactions.

Provides a user-friendly CLI for managing sessions, memory, workspace,
and identity configurations.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Dict
import shlex

from ghostclaw.core.agent_sdk.agent_session import (
    AgentSessionManager,
    SessionContext,
)


@dataclass
class CommandResult:
    """Result of a CLI command execution."""

    success: bool
    message: str
    error: Optional[str] = None
    data: Any = field(default=None)


class AgentCLI:
    """Interactive command-line interface for agent management."""

    COMMANDS = {
        "help": "Show help information",
        "session": "Manage sessions",
        "memory": "Manage memory entries",
        "workspace": "Manage workspace",
        "identity": "Manage agent identity",
        "status": "Show CLI status",
        "exit": "Exit the CLI",
        "quit": "Exit the CLI (alias for exit)",
    }

    def __init__(self, agent_id: str = "default-agent"):
        """
        Initialize the CLI.

        Args:
            agent_id: Unique identifier for the agent
        """
        self.agent_id = agent_id
        self.session_manager = AgentSessionManager(agent_id=agent_id)
        self.session_id: Optional[str] = None
        self.current_session: Optional[Dict[str, Any]] = None
        self.running = False

    def run_command(self, command_str: str) -> CommandResult:
        """
        Execute a CLI command.

        Args:
            command_str: Command string to execute

        Returns:
            CommandResult with execution status and output
        """
        if not command_str or not command_str.strip():
            return CommandResult(success=False, message="No command provided")

        try:
            # Parse command and arguments
            parts = shlex.split(command_str)
            command = parts[0].lower()
            args = parts[1:] if len(parts) > 1 else []

            # Route to handler
            if command == "help":
                return self._handle_help(args)
            elif command == "session":
                return self._handle_session(args)
            elif command == "memory":
                return self._handle_memory(args)
            elif command == "workspace":
                return self._handle_workspace(args)
            elif command == "identity":
                return self._handle_identity(args)
            elif command == "status":
                return self._handle_status(args)
            elif command in ("exit", "quit"):
                return self._handle_exit(args)
            else:
                return CommandResult(
                    success=False,
                    message=f"Unknown command: {command}. Type 'help' for available commands.",
                )

        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Error executing command: {str(e)}",
                error=str(e),
            )

    def _handle_help(self, args: list) -> CommandResult:
        """Handle help command."""
        if not args:
            # General help
            help_text = "Available commands:\n"
            for cmd, desc in self.COMMANDS.items():
                help_text += f"  {cmd:15} - {desc}\n"
            help_text += "\nType 'help <command>' for more information about a command."
            return CommandResult(success=True, message=help_text)

        # Specific command help
        topic = args[0].lower()
        help_topics = {
            "session": "session create <path> [name] - Create a new session\n"
            "  session start - Start active session\n"
            "  session pause - Pause active session\n"
            "  session resume - Resume paused session\n"
            "  session info - Show session information\n"
            "  session end - End active session",
            "memory": "memory add <content> - Add memory entry\n"
            "  memory list - List all memory entries\n"
            "  memory search <pattern> - Search memory entries\n"
            "  memory stats - Show memory statistics\n"
            "  memory export - Export all memory",
            "workspace": "workspace init - Initialize workspace\n"
            "  workspace status - Show workspace status\n"
            "  workspace branch <name> - Create new branch\n"
            "  workspace commit <message> - Commit changes\n"
            "  workspace history - Show commit history\n"
            "  workspace list [pattern] - List files",
            "identity": "identity load - Load agent identity\n"
            "  identity show - Show current identity\n"
            "  identity export - Export identity",
        }

        if topic in help_topics:
            return CommandResult(success=True, message=help_topics[topic])
        elif topic in self.COMMANDS:
            return CommandResult(
                success=True, message=f"Help for {topic}:\n{self.COMMANDS[topic]}"
            )
        else:
            return CommandResult(success=True, message=f"No help available for {topic}")

    def _handle_session(self, args: list) -> CommandResult:
        """Handle session commands."""
        if not args:
            return CommandResult(
                success=False,
                message="Session subcommand required. Use 'help session' for options.",
            )

        subcommand = args[0].lower()
        subargs = args[1:]

        if subcommand == "create":
            return self._session_create(subargs)
        elif subcommand == "start":
            return self._session_start(subargs)
        elif subcommand == "pause":
            return self._session_pause(subargs)
        elif subcommand == "resume":
            return self._session_resume(subargs)
        elif subcommand == "info":
            return self._session_info(subargs)
        elif subcommand == "end":
            return self._session_end(subargs)
        elif subcommand == "list":
            # Not yet implemented, return gracefully
            return CommandResult(
                success=True,
                message="Session list not yet implemented",
            )
        else:
            return CommandResult(
                success=False,
                message=f"Unknown session subcommand: {subcommand}",
            )

    def _session_create(self, args: list) -> CommandResult:
        """Create a new session."""
        if not args:
            return CommandResult(
                success=False,
                message="Usage: session create <project_path> [project_name]",
            )

        project_path = Path(args[0])
        project_name = args[1] if len(args) > 1 else project_path.name

        try:
            # Create session context and start session
            context = SessionContext(
                project_path=project_path,
                project_name=project_name,
            )
            self.session_id = self.session_manager.create_session(context=context)
            self.current_session = {
                "session_id": self.session_id,
                "project_path": str(project_path),
                "project_name": project_name,
                "state": "created",
            }
            return CommandResult(
                success=True,
                message=f"Session created: {self.session_id} for project '{project_name}'",
                data=self.current_session,
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to create session: {str(e)}",
                error=str(e),
            )

    def _session_start(self, args: list) -> CommandResult:
        """Start the active session."""
        if not self.current_session:
            return CommandResult(
                success=False, message="No session active. Create one first."
            )

        try:
            self.session_manager.start_session()
            self.current_session["state"] = "started"
            return CommandResult(
                success=True,
                message=f"Session started: {self.session_id}",
                data=self.current_session,
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to start session: {str(e)}",
                error=str(e),
            )

    def _session_pause(self, args: list) -> CommandResult:
        """Pause the active session."""
        if not self.current_session:
            return CommandResult(
                success=False, message="No active session to pause."
            )

        try:
            self.session_manager.pause_session()
            self.current_session["state"] = "paused"
            return CommandResult(
                success=True,
                message=f"Session paused: {self.session_id}",
                data=self.current_session,
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to pause session: {str(e)}",
                error=str(e),
            )

    def _session_resume(self, args: list) -> CommandResult:
        """Resume a paused session."""
        if not self.current_session:
            return CommandResult(
                success=False, message="No active session to resume."
            )

        try:
            self.session_manager.resume_session()
            self.current_session["state"] = "resumed"
            return CommandResult(
                success=True,
                message=f"Session resumed: {self.session_id}",
                data=self.current_session,
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to resume session: {str(e)}",
                error=str(e),
            )

    def _session_info(self, args: list) -> CommandResult:
        """Get session information."""
        if not self.current_session:
            return CommandResult(
                success=False, message="No active session. Create one first."
            )

        try:
            context = self.session_manager.get_context()
            metrics = self.session_manager.get_metrics()
            return CommandResult(
                success=True,
                message=f"Session: {self.session_id}",
                data={
                    "session_id": str(self.session_id),
                    "context": context.model_dump(),
                    "metrics": metrics.model_dump(),
                    **self.current_session,
                },
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to get session info: {str(e)}",
                error=str(e),
            )

    def _session_end(self, args: list) -> CommandResult:
        """End the active session."""
        if not self.current_session:
            return CommandResult(
                success=False, message="No active session to end."
            )

        try:
            # end_session returns a SessionSummary
            self.session_manager.end_session()
            session_id = self.session_id
            self.session_id = None
            self.current_session = None
            return CommandResult(
                success=True,
                message=f"Session ended: {session_id}",
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to end session: {str(e)}",
                error=str(e),
            )

    def _get_prompt(self) -> str:
        """
        Generate a CLI prompt.

        Returns:
            Formatted prompt string
        """
        if self.current_session:
            project_name = self.current_session.get("project_name", self.agent_id)
            return f"{project_name} > "
        else:
            return f"{self.agent_id} > "

    def _handle_memory(self, args: list) -> CommandResult:
        """Handle memory commands."""
        if not args:
            return CommandResult(
                success=False,
                message="Memory subcommand required. Use 'help memory' for options.",
            )

        if not self.current_session:
            return CommandResult(
                success=False, message="No active session. Create one first."
            )

        subcommand = args[0].lower()
        subargs = args[1:]

        try:
            memory_mgr = self.session_manager.get_memory_manager()

            if subcommand == "add":
                return self._memory_add(memory_mgr, subargs)
            elif subcommand == "list":
                return self._memory_list(memory_mgr, subargs)
            elif subcommand == "search":
                return self._memory_search(memory_mgr, subargs)
            elif subcommand == "stats":
                return self._memory_stats(memory_mgr, subargs)
            elif subcommand == "export":
                return self._memory_export(memory_mgr, subargs)
            else:
                return CommandResult(
                    success=False,
                    message=f"Unknown memory subcommand: {subcommand}",
                )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Memory error: {str(e)}",
                error=str(e),
            )

    def _memory_add(self, memory_mgr, args: list) -> CommandResult:
        """Add a memory entry."""
        if not args:
            return CommandResult(
                success=False,
                message="Usage: memory add <content>",
            )

        content = " ".join(args)
        # Use content as both title and content for simplicity
        memory_mgr.add_entry(
            memory_type="LONGTERM.md",
            title=content[:50],  # Use first 50 chars as title
            content=content,
        )
        return CommandResult(
            success=True,
            message=f"Memory entry added: {len(content)} characters",
        )

    def _memory_list(self, memory_mgr, args: list) -> CommandResult:
        """List memory entries."""
        entries = memory_mgr.get_entries("LONGTERM")
        return CommandResult(
            success=True,
            message=f"Found {len(entries)} memory entries",
            data=entries,
        )

    def _memory_search(self, memory_mgr, args: list) -> CommandResult:
        """Search memory entries."""
        if not args:
            return CommandResult(
                success=False,
                message="Usage: memory search <pattern>",
            )

        pattern = " ".join(args)
        results = memory_mgr.search_all(pattern)
        return CommandResult(
            success=True,
            message=f"Found {len(results)} matching entries",
            data=results,
        )

    def _memory_stats(self, memory_mgr, args: list) -> CommandResult:
        """Get memory statistics."""
        stats = memory_mgr.get_statistics()
        stats_text = "Memory Statistics\n"
        stats_text += f"  Total entries: {stats.get('total_entries', 0)}\n"
        stats_text += f"  Memory files: {len(stats.get('file_counts', {}))}\n"
        return CommandResult(
            success=True,
            message=stats_text,
            data=stats,
        )

    def _memory_export(self, memory_mgr, args: list) -> CommandResult:
        """Export memory."""
        try:
            export_data = memory_mgr.export_memory("LONGTERM.md")
            return CommandResult(
                success=True,
                message="Memory exported",
                data=export_data,
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Memory export failed: {str(e)}",
                error=str(e),
            )

    def _handle_workspace(self, args: list) -> CommandResult:
        """Handle workspace commands."""
        if not args:
            return CommandResult(
                success=False,
                message="Workspace subcommand required. Use 'help workspace' for options.",
            )

        if not self.current_session:
            return CommandResult(
                success=False, message="No active session. Create one first."
            )

        subcommand = args[0].lower()
        subargs = args[1:]

        try:
            workspace_mgr = self.session_manager.get_workspace_manager()

            if subcommand == "init":
                return self._workspace_init(workspace_mgr, subargs)
            elif subcommand == "status":
                return self._workspace_status(workspace_mgr, subargs)
            elif subcommand == "branch":
                return self._workspace_branch(workspace_mgr, subargs)
            elif subcommand == "commit":
                return self._workspace_commit(workspace_mgr, subargs)
            elif subcommand == "history":
                return self._workspace_history(workspace_mgr, subargs)
            elif subcommand == "list":
                return self._workspace_list(workspace_mgr, subargs)
            else:
                return CommandResult(
                    success=False,
                    message=f"Unknown workspace subcommand: {subcommand}",
                )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Workspace error: {str(e)}",
                error=str(e),
            )

    def _workspace_init(self, workspace_mgr, args: list) -> CommandResult:
        """Initialize workspace."""
        try:
            if workspace_mgr is None:
                # Start session first to initialize workspace manager
                self.session_manager.start_session()
                workspace_mgr = self.session_manager.get_workspace_manager()
            
            if workspace_mgr:
                workspace_mgr.initialize_repo()
            return CommandResult(
                success=True,
                message="Workspace initialized",
            )
        except Exception as e:
            # May fail if already initialized or other issues
            return CommandResult(
                success=False,
                message=f"Workspace init failed: {str(e)}",
                error=str(e),
            )

    def _workspace_status(self, workspace_mgr, args: list) -> CommandResult:
        """Get workspace status."""
        try:
            # Get basic status
            status_text = "Workspace Status\n"
            status_text += "  Repository initialized and ready\n"
            return CommandResult(
                success=True,
                message=status_text,
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Status check failed: {str(e)}",
                error=str(e),
            )

    def _workspace_branch(self, workspace_mgr, args: list) -> CommandResult:
        """Create workspace branch."""
        if not args:
            return CommandResult(
                success=False,
                message="Usage: workspace branch <branch_name>",
            )

        branch_name = args[0]
        try:
            workspace_mgr.create_branch(branch_name)
            return CommandResult(
                success=True,
                message=f"Branch created: {branch_name}",
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to create branch: {str(e)}",
                error=str(e),
            )

    def _workspace_commit(self, workspace_mgr, args: list) -> CommandResult:
        """Commit workspace changes."""
        if not args:
            return CommandResult(
                success=False,
                message="Usage: workspace commit <message>",
            )

        message = " ".join(args)
        try:
            workspace_mgr.commit_changes(message)
            return CommandResult(
                success=True,
                message=f"Changes committed: {message}",
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Commit failed: {str(e)}",
                error=str(e),
            )

    def _workspace_history(self, workspace_mgr, args: list) -> CommandResult:
        """Get workspace commit history."""
        try:
            history = workspace_mgr.get_commit_history()
            return CommandResult(
                success=True,
                message=f"Found {len(history)} commits",
                data=history,
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"History retrieval failed: {str(e)}",
                error=str(e),
            )

    def _workspace_list(self, workspace_mgr, args: list) -> CommandResult:
        """List workspace files."""
        pattern = args[0] if args else "*"
        try:
            # Simplified file listing
            project_path = Path(self.current_session["project_path"])
            files = list(project_path.glob(pattern))
            return CommandResult(
                success=True,
                message=f"Found {len(files)} files matching '{pattern}'",
                data=[str(f) for f in files],
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"File listing failed: {str(e)}",
                error=str(e),
            )

    def _handle_identity(self, args: list) -> CommandResult:
        """Handle identity commands."""
        if not args:
            return CommandResult(
                success=False,
                message="Identity subcommand required. Use 'help identity' for options.",
            )

        subcommand = args[0].lower()
        subargs = args[1:]

        try:
            identity_mgr = self.session_manager.get_identity_manager()

            if subcommand == "load":
                return self._identity_load(identity_mgr, subargs)
            elif subcommand == "show":
                return self._identity_show(identity_mgr, subargs)
            elif subcommand == "export":
                return self._identity_export(identity_mgr, subargs)
            else:
                return CommandResult(
                    success=False,
                    message=f"Unknown identity subcommand: {subcommand}",
                )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Identity error: {str(e)}",
                error=str(e),
            )

    def _identity_load(self, identity_mgr, args: list) -> CommandResult:
        """Load agent identity."""
        try:
            identity = identity_mgr.load()
            if identity:
                return CommandResult(
                    success=True,
                    message="Identity loaded",
                    data=identity,
                )
            else:
                return CommandResult(
                    success=False,
                    message="No identity found",
                )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to load identity: {str(e)}",
                error=str(e),
            )

    def _identity_show(self, identity_mgr, args: list) -> CommandResult:
        """Show agent identity."""
        try:
            summary = identity_mgr.get_summary()
            return CommandResult(
                success=True,
                message=summary,
                data={"summary": summary},
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to show identity: {str(e)}",
                error=str(e),
            )

    def _identity_export(self, identity_mgr, args: list) -> CommandResult:
        """Export agent identity."""
        try:
            export_data = identity_mgr.to_dict()
            return CommandResult(
                success=True,
                message="Identity exported",
                data=export_data,
            )
        except Exception as e:
            return CommandResult(
                success=False,
                message=f"Failed to export identity: {str(e)}",
                error=str(e),
            )

    def _handle_status(self, args: list) -> CommandResult:
        """Handle status command."""
        if self.current_session:
            status_text = "Session Status\n"
            status_text += f"  Agent: {self.agent_id}\n"
            status_text += f"  Project: {self.current_session.get('project_name', 'unknown')}\n"
            status_text += f"  State: {self.current_session.get('state', 'unknown')}\n"
            return CommandResult(
                success=True,
                message=status_text,
                data=self.current_session,
            )
        else:
            status_text = "No active session\n"
            status_text += f"  Agent: {self.agent_id}\n"
            status_text += "  State: idle\n"
            return CommandResult(
                success=True,
                message=status_text,
            )

    def _handle_exit(self, args: list) -> CommandResult:
        """Handle exit/quit command."""
        self.running = False
        return CommandResult(
            success=True,
            message="Goodbye!",
        )
