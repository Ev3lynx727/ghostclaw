"""
Agent Session Manager - Manages agent session lifecycle and state.

This module provides the AgentSessionManager class which handles:
- Session initialization and lifecycle management
- State tracking and transitions
- Integration with Identity, Memory, and Workspace managers
- Session context and metadata
- Session history and logging
- Automatic persistence and recovery
"""

import json
import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .agent_identity import AgentIdentityManager
from .agent_memory import AgentMemoryManager
from .agent_workspace import AgentWorkspaceManager
from .config import AgentSDKSettings


class SessionState(str, Enum):
    """Session lifecycle states."""
    
    INITIALIZED = "initialized"  # Session created but not started
    ACTIVE = "active"  # Session is running
    PAUSED = "paused"  # Session is paused (can resume)
    COMPLETED = "completed"  # Session finished successfully
    FAILED = "failed"  # Session ended with error
    CANCELLED = "cancelled"  # Session was cancelled


class SessionAction(BaseModel):
    """Log entry for a session action."""
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Action ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="Action timestamp")
    action_type: str = Field(..., description="Type of action (e.g., 'file_edit', 'git_commit')")
    description: str = Field(..., description="Human-readable description")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional action details")
    success: bool = Field(default=True, description="Whether action succeeded")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class SessionContext(BaseModel):
    """Context information for an agent session."""
    
    project_path: Optional[Path] = Field(None, description="Path to project being analyzed")
    project_name: Optional[str] = Field(None, description="Name of project")
    goals: List[str] = Field(default_factory=list, description="Session goals")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")
    tags: List[str] = Field(default_factory=list, description="Session tags")
    environment: Dict[str, str] = Field(default_factory=dict, description="Environment variables")


class SessionMetrics(BaseModel):
    """Metrics for a session."""
    
    total_duration: timedelta = Field(default_factory=timedelta, description="Total session duration")
    action_count: int = Field(default=0, description="Total actions performed")
    file_count: int = Field(default=0, description="Files created/modified")
    git_commits: int = Field(default=0, description="Git commits made")
    memory_entries: int = Field(default=0, description="Memory entries created")
    errors_count: int = Field(default=0, description="Errors encountered")


class SessionSummary(BaseModel):
    """Summary of a completed session."""
    
    session_id: UUID = Field(..., description="Session ID")
    agent_id: UUID = Field(..., description="Agent ID")
    state: SessionState = Field(..., description="Final session state")
    created_at: datetime = Field(..., description="Session creation time")
    started_at: Optional[datetime] = Field(None, description="Session start time")
    ended_at: Optional[datetime] = Field(None, description="Session end time")
    duration: timedelta = Field(..., description="Total session duration")
    goals: List[str] = Field(..., description="Session goals")
    metrics: SessionMetrics = Field(..., description="Session metrics")
    notes: Optional[str] = Field(None, description="Session completion notes")


class AgentSessionManager:
    """
    Manages agent session lifecycle and state.
    
    A session represents a bounded period of agent activity with:
    - Identity context (who the agent is)
    - Memory management (what the agent knows)
    - Workspace isolation (where the agent works)
    - Action logging (what the agent did)
    - State tracking (current session status)
    """
    
    def __init__(
        self,
        agent_id: UUID,
        session_root: Optional[Path] = None,
    ):
        """
        Initialize the session manager.
        
        Args:
            agent_id: Agent ID for this session manager
            session_root: Root directory for session storage
        """
        self.agent_id = agent_id
        self.settings = AgentSDKSettings()
        
        if session_root:
            self.session_root = session_root
        else:
            # Default to ~/.ghostclaw/sessions/agent_id/
            self.session_root = Path.home() / ".ghostclaw" / "sessions" / str(agent_id)
        
        self.session_root.mkdir(parents=True, exist_ok=True)
        
        # Current session state
        self._session_id: Optional[UUID] = None
        self._state = SessionState.INITIALIZED
        self._created_at = datetime.now()
        self._started_at: Optional[datetime] = None
        self._paused_at: Optional[datetime] = None
        self._ended_at: Optional[datetime] = None
        
        # Manager instances
        self._identity_manager: Optional[AgentIdentityManager] = None
        self._memory_manager: Optional[AgentMemoryManager] = None
        self._workspace_manager: Optional[AgentWorkspaceManager] = None
        
        # Session context and logging
        self._context = SessionContext()
        self._actions: List[SessionAction] = []
        self._metrics = SessionMetrics()
        self._paused_duration = timedelta(0)
    
    def create_session(
        self,
        goals: Optional[List[str]] = None,
        context: Optional[SessionContext] = None,
    ) -> UUID:
        """
        Create a new session.
        
        Args:
            goals: List of session goals
            context: Session context information
        
        Returns:
            Session ID (UUID)
        """
        self._session_id = uuid.uuid4()
        self._created_at = datetime.now()
        self._state = SessionState.INITIALIZED
        
        if context:
            self._context = context
        
        if goals:
            self._context.goals = goals
        
        # Save session metadata
        self._save_session_metadata()
        
        return self._session_id
    
    def start_session(self, initialize_managers: bool = True) -> bool:
        """
        Start the current session.
        
        Args:
            initialize_managers: Whether to initialize identity/memory/workspace managers
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self._session_id is None:
                self.create_session()
            
            self._started_at = datetime.now()
            self._state = SessionState.ACTIVE
            
            # Initialize managers if requested
            if initialize_managers:
                self._initialize_managers()
            
            # Log session start
            self._log_action(
                action_type="session_start",
                description=f"Session started with {len(self._context.goals)} goals",
                details={"goals": self._context.goals},
            )
            
            return True
        except Exception:
            self._state = SessionState.FAILED
            return False
    
    def pause_session(self) -> bool:
        """
        Pause the current session.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self._state != SessionState.ACTIVE:
                return False
            
            self._paused_at = datetime.now()
            self._state = SessionState.PAUSED
            
            self._log_action(
                action_type="session_pause",
                description="Session paused",
            )
            
            return True
        except Exception:
            return False
    
    def resume_session(self) -> bool:
        """
        Resume a paused session.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if self._state != SessionState.PAUSED:
                return False
            
            if self._paused_at:
                pause_duration = datetime.now() - self._paused_at
                self._paused_duration += pause_duration
            
            self._paused_at = None
            self._state = SessionState.ACTIVE
            
            self._log_action(
                action_type="session_resume",
                description="Session resumed",
            )
            
            return True
        except Exception:
            return False
    
    def end_session(
        self,
        state: SessionState = SessionState.COMPLETED,
        notes: Optional[str] = None,
    ) -> Optional[SessionSummary]:
        """
        End the current session.
        
        Args:
            state: Final session state (COMPLETED or FAILED)
            notes: Optional session completion notes
        
        Returns:
            SessionSummary with session details
        """
        try:
            self._ended_at = datetime.now()
            self._state = state
            
            # Calculate session duration
            if self._started_at:
                total_duration = self._ended_at - self._started_at - self._paused_duration
            else:
                total_duration = self._ended_at - self._created_at - self._paused_duration
            
            self._metrics.total_duration = total_duration
            
            # Log session end
            self._log_action(
                action_type="session_end",
                description=f"Session ended with state: {state.value}",
                details={"state": state.value, "notes": notes},
            )
            
            # Create summary
            summary = SessionSummary(
                session_id=self._session_id,
                agent_id=self.agent_id,
                state=self._state,
                created_at=self._created_at,
                started_at=self._started_at,
                ended_at=self._ended_at,
                duration=total_duration,
                goals=self._context.goals,
                metrics=self._metrics,
                notes=notes,
            )
            
            # Save session
            self._save_session_data(summary)
            
            return summary
        except Exception:
            return None
    
    def get_session_id(self) -> Optional[UUID]:
        """Get the current session ID."""
        return self._session_id
    
    def get_state(self) -> SessionState:
        """Get the current session state."""
        return self._state
    
    def get_context(self) -> SessionContext:
        """Get the session context."""
        return self._context
    
    def set_context(self, context: SessionContext) -> None:
        """Set the session context."""
        self._context = context
    
    def get_identity_manager(self) -> Optional[AgentIdentityManager]:
        """Get the identity manager for this session."""
        return self._identity_manager
    
    def get_memory_manager(self) -> Optional[AgentMemoryManager]:
        """Get the memory manager for this session."""
        return self._memory_manager
    
    def get_workspace_manager(self) -> Optional[AgentWorkspaceManager]:
        """Get the workspace manager for this session."""
        return self._workspace_manager
    
    def log_action(
        self,
        action_type: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> SessionAction:
        """
        Log an action in the session.
        
        Args:
            action_type: Type of action
            description: Action description
            details: Additional details
            success: Whether action succeeded
            error_message: Error message if failed
        
        Returns:
            Created SessionAction
        """
        action = SessionAction(
            action_type=action_type,
            description=description,
            details=details or {},
            success=success,
            error_message=error_message,
        )
        
        self._log_action(action_type, description, details or {}, success, error_message)
        return action
    
    def get_actions(
        self,
        action_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[SessionAction]:
        """
        Get logged actions.
        
        Args:
            action_type: Optional filter by action type
            limit: Optional limit on results
        
        Returns:
            List of SessionAction objects
        """
        actions = self._actions
        
        if action_type:
            actions = [a for a in actions if a.action_type == action_type]
        
        if limit:
            actions = actions[-limit:]
        
        return actions
    
    def get_metrics(self) -> SessionMetrics:
        """Get session metrics."""
        return self._metrics
    
    def get_duration(self) -> timedelta:
        """
        Get the current session duration.
        
        Returns:
            Session duration as timedelta
        """
        if self._started_at:
            end_time = self._ended_at or datetime.now()
            total = end_time - self._started_at - self._paused_duration
            return max(total, timedelta(0))  # Ensure non-negative
        
        return timedelta(0)
    
    def export_session_data(self) -> Dict[str, Any]:
        """
        Export complete session data.
        
        Returns:
            Dictionary with all session data
        """
        return {
            "session_id": str(self._session_id) if self._session_id else None,
            "agent_id": str(self.agent_id),
            "state": self._state.value,
            "created_at": self._created_at.isoformat(),
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "ended_at": self._ended_at.isoformat() if self._ended_at else None,
            "duration": str(self.get_duration()),
            "context": self._context.model_dump(mode='json'),
            "metrics": self._metrics.model_dump(mode='json'),
            "actions": [
                {
                    "id": a.id,
                    "timestamp": a.timestamp.isoformat(),
                    "action_type": a.action_type,
                    "description": a.description,
                    "details": a.details,
                    "success": a.success,
                    "error_message": a.error_message,
                }
                for a in self._actions
            ],
        }
    
    def load_session(self, session_id: UUID) -> bool:
        """
        Load a previous session by ID.
        
        Args:
            session_id: Session ID to load
        
        Returns:
            True if successful, False otherwise
        """
        try:
            session_file = self.session_root / f"session_{session_id}.json"
            
            if not session_file.exists():
                return False
            
            with open(session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Restore session data
            self._session_id = UUID(data["session_id"])
            self._state = SessionState(data["state"])
            self._created_at = datetime.fromisoformat(data["created_at"])
            
            if data.get("started_at"):
                self._started_at = datetime.fromisoformat(data["started_at"])
            
            if data.get("ended_at"):
                self._ended_at = datetime.fromisoformat(data["ended_at"])
            
            # Restore context
            context_data = data.get("context", {})
            if "project_path" in context_data and context_data["project_path"]:
                context_data["project_path"] = Path(context_data["project_path"])
            self._context = SessionContext(**context_data)
            
            # Restore metrics
            self._metrics = SessionMetrics(**data.get("metrics", {}))
            
            return True
        except Exception:
            return False
    
    def cleanup_session(self, remove_files: bool = False) -> bool:
        """
        Clean up session resources.
        
        Args:
            remove_files: Whether to remove session files
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Clean up workspace
            if self._workspace_manager:
                self._workspace_manager.cleanup(remove_repo=remove_files)
            
            if remove_files:
                # Remove session file
                if self._session_id:
                    session_file = self.session_root / f"session_{self._session_id}.json"
                    if session_file.exists():
                        session_file.unlink()
            
            return True
        except Exception:
            return False
    
    # Private helper methods
    
    def _initialize_managers(self) -> None:
        """Initialize Identity, Memory, and Workspace managers."""
        # Identity manager
        self._identity_manager = AgentIdentityManager(self.agent_id)
        
        # Memory manager
        memory_dir = self.session_root / "memory"
        self._memory_manager = AgentMemoryManager(self.agent_id, memory_root=memory_dir)
        self._memory_manager.initialize()
        
        # Workspace manager
        workspace_dir = self.session_root / "workspace"
        self._workspace_manager = AgentWorkspaceManager(self.agent_id, workspace_root=workspace_dir)
    
    def _log_action(
        self,
        action_type: str,
        description: str,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """Internal method to log an action."""
        action = SessionAction(
            action_type=action_type,
            description=description,
            details=details or {},
            success=success,
            error_message=error_message,
        )
        
        self._actions.append(action)
        
        # Update metrics
        self._metrics.action_count += 1
        if not success:
            self._metrics.errors_count += 1
        
        if action_type == "file_edit":
            self._metrics.file_count += 1
        elif action_type == "git_commit":
            self._metrics.git_commits += 1
        elif action_type == "memory_add":
            self._metrics.memory_entries += 1
    
    def _save_session_metadata(self) -> None:
        """Save session metadata to disk."""
        if self._session_id is None:
            return
        
        metadata = {
            "session_id": str(self._session_id),
            "agent_id": str(self.agent_id),
            "created_at": self._created_at.isoformat(),
            "state": self._state.value,
        }
        
        metadata_file = self.session_root / f"session_{self._session_id}.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
    
    def _save_session_data(self, summary: SessionSummary) -> None:
        """Save complete session data to disk."""
        if self._session_id is None:
            return
        
        session_data = self.export_session_data()
        
        session_file = self.session_root / f"session_{self._session_id}.json"
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, default=str)


__all__ = [
    "AgentSessionManager",
    "SessionState",
    "SessionAction",
    "SessionContext",
    "SessionMetrics",
    "SessionSummary",
]
