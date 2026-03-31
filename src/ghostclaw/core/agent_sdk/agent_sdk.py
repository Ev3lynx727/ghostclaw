"""
AgentSDK - Unified Interface for Ghostclaw Agent Framework.

This module provides the high-level public API for the agent framework.
It wraps all managers (Identity, Memory, Workspace, Session) into a single,
easy-to-use interface.

Example:
    >>> from ghostclaw.core.agent_sdk import AgentSDK
    >>> sdk = AgentSDK(agent_id="my-agent")
    >>> session = sdk.create_session(
    ...     project_path="/path/to/project",
    ...     project_name="my-project"
    ... )
    >>> sdk.add_memory("Important fact", tags=["learning"])
    >>> files = sdk.list_workspace_files("*.py")
    >>> identity = sdk.get_identity()
    >>> sdk.end_session()
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from .agent_cli import AgentCLI, CommandResult
from .agent_identity import AgentIdentityManager
from .agent_memory import AgentMemoryManager
from .agent_session import AgentSessionManager, SessionContext
from .agent_workspace import AgentWorkspaceManager
from .config import AgentSDKSettings


class AgentSDK:
    """
    Unified public API for the Ghostclaw Agent SDK.

    This is the primary entry point for using the agent framework. It provides
    a simplified interface that handles session management and coordinates
    all sub-managers (Identity, Memory, Workspace, CLI).

    Attributes:
        agent_id: Unique identifier for this agent
        session_manager: Session lifecycle manager
        identity_manager: Agent identity manager (available after session starts)
        memory_manager: Agent memory manager (available after session starts)
        workspace_manager: Workspace/git manager (available after session starts)
        cli: Interactive CLI interface
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        settings: Optional[AgentSDKSettings] = None,
    ):
        """
        Initialize the Agent SDK.

        Args:
            agent_id: Optional unique identifier for the agent. Auto-generated if not provided.
            settings: Optional SDK settings. Uses defaults if not provided.
        """
        self.agent_id = agent_id or "default-agent"
        self.settings = settings or AgentSDKSettings()

        # Initialize core managers
        self.session_manager = AgentSessionManager(agent_id=self.agent_id)
        self.cli = AgentCLI(agent_id=self.agent_id)

        # These are set when session starts
        self.identity_manager: Optional[AgentIdentityManager] = None
        self.memory_manager: Optional[AgentMemoryManager] = None
        self.workspace_manager: Optional[AgentWorkspaceManager] = None

        # Track current session state
        self._session_active = False
        self._project_path: Optional[Path] = None
        self._project_name: Optional[str] = None

    # ============================================================================
    # Session Management
    # ============================================================================

    def create_session(
        self,
        project_path: Path,
        project_name: str,
        goals: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> UUID:
        """
        Create and initialize a new session.

        Args:
            project_path: Path to the project directory
            project_name: Name of the project
            goals: Optional list of session goals
            metadata: Optional custom metadata
            tags: Optional session tags

        Returns:
            Session ID (UUID)
        """
        context = SessionContext(
            project_path=Path(project_path),
            project_name=project_name,
            goals=goals or [],
            metadata=metadata or {},
            tags=tags or [],
        )

        session_id = self.session_manager.create_session(goals=goals, context=context)
        self._project_path = Path(project_path)
        self._project_name = project_name

        return session_id

    def start_session(self) -> bool:
        """
        Start the current session and initialize all managers.

        Returns:
            True if session started successfully, False otherwise
        """
        success = self.session_manager.start_session(initialize_managers=True)

        if success:
            self._session_active = True
            self.identity_manager = self.session_manager.get_identity_manager()
            self.memory_manager = self.session_manager.get_memory_manager()
            self.workspace_manager = self.session_manager.get_workspace_manager()

        return success

    def pause_session(self) -> bool:
        """
        Pause the current session.

        Returns:
            True if session paused successfully, False otherwise
        """
        return self.session_manager.pause_session()

    def resume_session(self) -> bool:
        """
        Resume a paused session.

        Returns:
            True if session resumed successfully, False otherwise
        """
        return self.session_manager.resume_session()

    def end_session(self, notes: Optional[str] = None) -> bool:
        """
        End the current session.

        Args:
            notes: Optional completion notes

        Returns:
            True if session ended successfully, False otherwise
        """
        try:
            summary = self.session_manager.end_session(notes=notes)
            if summary is not None:
                self._session_active = False
                self.identity_manager = None
                self.memory_manager = None
                self.workspace_manager = None
                return True
        except Exception:
            pass

        return False

    def get_session_id(self) -> Optional[UUID]:
        """Get the current session ID."""
        return self.session_manager.get_session_id()

    def is_session_active(self) -> bool:
        """Check if a session is currently active."""
        return self._session_active

    # ============================================================================
    # Identity Management
    # ============================================================================

    def get_identity(self) -> Optional[Dict[str, Any]]:
        """
        Get the current agent identity.

        Returns:
            Identity as dict, or None if session not active
        """
        if not self.identity_manager:
            return None

        try:
            identity = self.identity_manager.load_or_create_default()
            if identity:
                return identity.model_dump()
        except Exception:
            pass

        return None

    def set_identity_personality(
        self, personality: str, traits: Optional[List[str]] = None
    ) -> bool:
        """
        Set or update agent personality.

        Args:
            personality: Description of agent personality
            traits: Optional list of personality traits

        Returns:
            True if successful, False otherwise
        """
        if not self.identity_manager:
            return False

        try:
            identity = self.identity_manager.load()
            if identity:
                identity.personality.description = personality
                if traits:
                    identity.personality.traits = traits
                self.identity_manager.save(identity)
                return True
        except Exception:
            pass

        return False

    def export_identity(self) -> Optional[Dict[str, Any]]:
        """
        Export the current agent identity.

        Returns:
            Identity export dict, or None if session not active
        """
        if not self.identity_manager:
            return None

        try:
            identity = self.identity_manager.load_or_create_default()
            if identity:
                return identity.model_dump()
        except Exception:
            pass

        return None

    # ============================================================================
    # Memory Management
    # ============================================================================

    def add_memory(
        self,
        content: str,
        title: Optional[str] = None,
        memory_type: str = "LONGTERM.md",
        tags: Optional[List[str]] = None,
        source: Optional[str] = None,
    ) -> bool:
        """
        Add a memory entry.

        Args:
            content: Memory content
            title: Optional memory title (defaults to first 50 chars of content)
            memory_type: Type of memory file (e.g., "LONGTERM.md", "SESSION.md")
            tags: Optional tags for categorization
            source: Optional source of the memory

        Returns:
            True if successful, False otherwise
        """
        if not self.memory_manager:
            return False

        try:
            self.memory_manager.add_entry(
                memory_type=memory_type,
                title=title or content[:50],
                content=content,
                tags=tags or [],
                source=source,
            )
            return True
        except Exception:
            return False

    def search_memory(self, pattern: str) -> List[Dict[str, Any]]:
        """
        Search memory entries.

        Args:
            pattern: Search pattern (supports regex)

        Returns:
            List of matching memory entries
        """
        if not self.memory_manager:
            return []

        try:
            return self.memory_manager.search_all(pattern)
        except Exception:
            return []

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get memory statistics.

        Returns:
            Dictionary with memory statistics
        """
        if not self.memory_manager:
            return {}

        try:
            return self.memory_manager.get_statistics()
        except Exception:
            return {}

    def export_memory(self, memory_type: str = "LONGTERM.md") -> Optional[Dict[str, Any]]:
        """
        Export memory entries.

        Args:
            memory_type: Type of memory to export

        Returns:
            Exported memory dict, or None if failed
        """
        if not self.memory_manager:
            return None

        try:
            return self.memory_manager.export_memory(memory_type)
        except Exception:
            return None

    # ============================================================================
    # Workspace Management
    # ============================================================================

    def init_workspace(self) -> bool:
        """
        Initialize the workspace git repository.

        Returns:
            True if successful, False otherwise
        """
        if not self.workspace_manager:
            return False

        try:
            self.workspace_manager.initialize_repo()
            return True
        except Exception:
            return False

    def create_branch(self, branch_name: str) -> bool:
        """
        Create a new workspace branch.

        Args:
            branch_name: Name of the branch to create

        Returns:
            True if successful, False otherwise
        """
        if not self.workspace_manager:
            return False

        try:
            self.workspace_manager.create_branch(branch_name)
            return True
        except Exception:
            return False

    def commit_changes(self, message: str) -> bool:
        """
        Commit workspace changes.

        Args:
            message: Commit message

        Returns:
            True if successful, False otherwise
        """
        if not self.workspace_manager:
            return False

        try:
            self.workspace_manager.commit_changes(message)
            return True
        except Exception:
            return False

    def get_commit_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get workspace commit history.

        Args:
            limit: Optional limit on number of commits

        Returns:
            List of commit dicts
        """
        if not self.workspace_manager:
            return []

        try:
            history = self.workspace_manager.get_commit_history()
            if limit:
                history = history[:limit]
            return history
        except Exception:
            return []

    def list_workspace_files(self, pattern: str = "*") -> List[str]:
        """
        List files in the workspace.

        Args:
            pattern: Optional glob pattern (default: "*")

        Returns:
            List of file paths
        """
        if not self._project_path:
            return []

        try:
            files = list(self._project_path.glob(pattern))
            return [str(f) for f in files]
        except Exception:
            return []

    def read_workspace_file(self, filepath: str) -> Optional[str]:
        """
        Read a file from the workspace.

        Args:
            filepath: Path to file

        Returns:
            File contents, or None if failed
        """
        if not self._project_path:
            return None

        try:
            full_path = self._project_path / filepath
            return full_path.read_text(encoding='utf-8')
        except Exception:
            return None

    # ============================================================================
    # CLI Access
    # ============================================================================

    def run_cli_command(self, command: str) -> CommandResult:
        """
        Execute a CLI command.

        Args:
            command: Command string to execute

        Returns:
            CommandResult with execution status and output
        """
        # Update CLI reference to session manager
        self.cli.session_manager = self.session_manager
        self.cli.session_id = self.session_manager.get_session_id()
        self.cli.current_session = {
            "project_name": self._project_name,
            "project_path": str(self._project_path) if self._project_path else None,
            "session_id": str(self.cli.session_id) if self.cli.session_id else None,
        } if self._session_active else None

        return self.cli.run_command(command)

    # ============================================================================
    # Info & Utilities
    # ============================================================================

    def get_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the current SDK state.

        Returns:
            Dictionary with SDK and session information
        """
        return {
            "agent_id": self.agent_id,
            "session_active": self._session_active,
            "session_id": str(self.session_manager.get_session_id())
            if self.session_manager.get_session_id()
            else None,
            "project_path": str(self._project_path) if self._project_path else None,
            "project_name": self._project_name,
            "managers_available": {
                "identity": self.identity_manager is not None,
                "memory": self.memory_manager is not None,
                "workspace": self.workspace_manager is not None,
            },
        }

    def __repr__(self) -> str:
        """String representation of the SDK."""
        session_status = "active" if self._session_active else "inactive"
        return f"AgentSDK(agent_id={self.agent_id}, session={session_status})"


__all__ = ["AgentSDK"]
