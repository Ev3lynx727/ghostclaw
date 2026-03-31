"""
Unit tests for AgentSessionManager.

Tests the session management functionality including:
- Session lifecycle (create, start, pause, resume, end)
- State transitions and validation
- Integration with identity/memory/workspace managers
- Action logging and metrics
- Session persistence and recovery
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from ghostclaw.core.agent_sdk.agent_session import (
    AgentSessionManager,
    SessionAction,
    SessionContext,
    SessionMetrics,
    SessionState,
    SessionSummary,
)


@pytest.fixture
def agent_id():
    """Generate a test agent ID."""
    return uuid4()


@pytest.fixture
def temp_session_dir():
    """Create a temporary session directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def session_manager(agent_id, temp_session_dir):
    """Create an AgentSessionManager instance for testing."""
    manager = AgentSessionManager(agent_id=agent_id, session_root=temp_session_dir)
    return manager


class TestSessionManagerInitialization:
    """Tests for session manager initialization."""
    
    def test_session_manager_initializes(self, agent_id, temp_session_dir):
        """Test that session manager initializes correctly."""
        manager = AgentSessionManager(agent_id=agent_id, session_root=temp_session_dir)
        
        assert manager.agent_id == agent_id
        assert manager.session_root == temp_session_dir
        assert manager.get_state() == SessionState.INITIALIZED
    
    def test_session_root_defaults_to_home_directory(self, agent_id):
        """Test that session root defaults to ~/.ghostclaw/sessions/agent_id/."""
        manager = AgentSessionManager(agent_id=agent_id)
        expected_root = Path.home() / ".ghostclaw" / "sessions" / str(agent_id)
        assert manager.session_root == expected_root
    
    def test_session_manager_creates_directory(self, agent_id, temp_session_dir):
        """Test that session manager creates the session directory."""
        manager = AgentSessionManager(agent_id=agent_id, session_root=temp_session_dir)
        assert temp_session_dir.exists()


class TestSessionLifecycle:
    """Tests for session lifecycle management."""
    
    def test_create_session(self, session_manager):
        """Test creating a new session."""
        goals = ["Analyze code", "Fix bugs"]
        session_id = session_manager.create_session(goals=goals)
        
        assert session_id is not None
        assert session_manager.get_session_id() == session_id
        assert session_manager.get_state() == SessionState.INITIALIZED
        assert session_manager.get_context().goals == goals
    
    def test_start_session(self, session_manager):
        """Test starting a session."""
        session_manager.create_session(goals=["Test Goal"])
        success = session_manager.start_session(initialize_managers=False)
        
        assert success
        assert session_manager.get_state() == SessionState.ACTIVE
        assert session_manager._started_at is not None
    
    def test_start_session_initializes_managers(self, session_manager):
        """Test that starting session initializes managers."""
        session_manager.create_session()
        session_manager.start_session(initialize_managers=True)
        
        assert session_manager.get_identity_manager() is not None
        assert session_manager.get_memory_manager() is not None
        assert session_manager.get_workspace_manager() is not None
    
    def test_pause_session(self, session_manager):
        """Test pausing an active session."""
        session_manager.create_session()
        session_manager.start_session(initialize_managers=False)
        success = session_manager.pause_session()
        
        assert success
        assert session_manager.get_state() == SessionState.PAUSED
    
    def test_pause_inactive_session_fails(self, session_manager):
        """Test that pausing an inactive session fails."""
        session_manager.create_session()
        success = session_manager.pause_session()
        
        assert not success
    
    def test_resume_session(self, session_manager):
        """Test resuming a paused session."""
        session_manager.create_session()
        session_manager.start_session(initialize_managers=False)
        session_manager.pause_session()
        success = session_manager.resume_session()
        
        assert success
        assert session_manager.get_state() == SessionState.ACTIVE
    
    def test_resume_non_paused_session_fails(self, session_manager):
        """Test that resuming non-paused session fails."""
        session_manager.create_session()
        success = session_manager.resume_session()
        
        assert not success
    
    def test_end_session(self, session_manager):
        """Test ending a session."""
        session_manager.create_session(goals=["Test"])
        session_manager.start_session(initialize_managers=False)
        summary = session_manager.end_session(state=SessionState.COMPLETED, notes="All done")
        
        assert summary is not None
        assert summary.state == SessionState.COMPLETED
        assert summary.notes == "All done"
        assert summary.duration >= timedelta(0)
    
    def test_end_session_with_failure_state(self, session_manager):
        """Test ending a session with failure state."""
        session_manager.create_session()
        session_manager.start_session(initialize_managers=False)
        summary = session_manager.end_session(state=SessionState.FAILED)
        
        assert summary.state == SessionState.FAILED


class TestSessionContext:
    """Tests for session context management."""
    
    def test_get_context(self, session_manager):
        """Test getting session context."""
        context = session_manager.get_context()
        assert isinstance(context, SessionContext)
    
    def test_set_context(self, session_manager):
        """Test setting session context."""
        new_context = SessionContext(
            project_name="test-project",
            goals=["Goal 1", "Goal 2"],
            tags=["test", "urgent"],
        )
        session_manager.set_context(new_context)
        
        context = session_manager.get_context()
        assert context.project_name == "test-project"
        assert context.goals == ["Goal 1", "Goal 2"]
        assert context.tags == ["test", "urgent"]
    
    def test_context_with_project_path(self, session_manager, temp_session_dir):
        """Test context with project path."""
        context = SessionContext(
            project_path=temp_session_dir,
            project_name="my-project",
        )
        session_manager.set_context(context)
        
        retrieved_context = session_manager.get_context()
        assert retrieved_context.project_path == temp_session_dir


class TestActionLogging:
    """Tests for action logging."""
    
    def test_log_action(self, session_manager):
        """Test logging an action."""
        session_manager.create_session()
        session_manager.start_session(initialize_managers=False)
        
        action = session_manager.log_action(
            action_type="file_edit",
            description="Edited example.py",
            details={"file": "example.py", "lines": 10},
        )
        
        assert isinstance(action, SessionAction)
        assert action.action_type == "file_edit"
        assert action.description == "Edited example.py"
    
    def test_log_failed_action(self, session_manager):
        """Test logging a failed action."""
        session_manager.create_session()
        session_manager.start_session(initialize_managers=False)
        
        action = session_manager.log_action(
            action_type="test_run",
            description="Run tests",
            success=False,
            error_message="Tests failed",
        )
        
        assert not action.success
        assert action.error_message == "Tests failed"
    
    def test_get_actions(self, session_manager):
        """Test retrieving logged actions."""
        session_manager.create_session()
        session_manager.start_session(initialize_managers=False)
        
        session_manager.log_action("file_edit", "Edit 1")
        session_manager.log_action("file_edit", "Edit 2")
        session_manager.log_action("git_commit", "Commit 1")
        
        all_actions = session_manager.get_actions()
        assert len(all_actions) >= 3
    
    def test_filter_actions_by_type(self, session_manager):
        """Test filtering actions by type."""
        session_manager.create_session()
        session_manager.start_session(initialize_managers=False)
        
        session_manager.log_action("file_edit", "Edit 1")
        session_manager.log_action("file_edit", "Edit 2")
        session_manager.log_action("git_commit", "Commit 1")
        
        file_edits = session_manager.get_actions(action_type="file_edit")
        assert len(file_edits) == 2
    
    def test_limit_actions(self, session_manager):
        """Test limiting action results."""
        session_manager.create_session()
        session_manager.start_session(initialize_managers=False)
        
        for i in range(10):
            session_manager.log_action("test", f"Action {i}")
        
        limited = session_manager.get_actions(limit=5)
        assert len(limited) == 5


class TestSessionMetrics:
    """Tests for session metrics."""
    
    def test_get_metrics(self, session_manager):
        """Test getting session metrics."""
        session_manager.create_session()
        metrics = session_manager.get_metrics()
        
        assert isinstance(metrics, SessionMetrics)
        assert metrics.errors_count == 0
        assert metrics.action_count == 0
    
    def test_metrics_updated_on_action_logging(self, session_manager):
        """Test that metrics are updated when actions are logged."""
        session_manager.create_session()
        session_manager.start_session(initialize_managers=False)
        
        session_manager.log_action("file_edit", "Edit 1")
        session_manager.log_action("file_edit", "Edit 2")
        session_manager.log_action("git_commit", "Commit 1")
        session_manager.log_action("test", "Test", success=False)
        
        metrics = session_manager.get_metrics()
        assert metrics.file_count == 2
        assert metrics.git_commits == 1
        assert metrics.errors_count == 1
    
    def test_duration_calculation(self, session_manager):
        """Test session duration calculation."""
        session_manager.create_session()
        session_manager.start_session(initialize_managers=False)
        
        duration = session_manager.get_duration()
        assert duration >= timedelta(0)
    
    def test_duration_with_pause(self, session_manager):
        """Test duration calculation with pauses."""
        session_manager.create_session()
        session_manager.start_session(initialize_managers=False)
        session_manager.pause_session()
        session_manager.resume_session()
        
        duration = session_manager.get_duration()
        assert duration >= timedelta(0)


class TestSessionPersistence:
    """Tests for session persistence."""
    
    def test_export_session_data(self, session_manager):
        """Test exporting session data."""
        session_manager.create_session(goals=["Test Goal"])
        session_manager.start_session(initialize_managers=False)
        session_manager.log_action("test", "Test action")
        
        exported = session_manager.export_session_data()
        
        assert exported["state"] == "active"
        assert len(exported["actions"]) > 0
        assert "goals" in exported["context"]
    
    def test_session_metadata_saved_on_creation(self, session_manager, temp_session_dir):
        """Test that session metadata is saved on creation."""
        session_id = session_manager.create_session()
        
        # Check that metadata file was created
        metadata_file = temp_session_dir / f"session_{session_id}.json"
        assert metadata_file.exists()
    
    def test_session_data_saved_on_completion(self, session_manager, temp_session_dir):
        """Test that session data is saved on completion."""
        session_id = session_manager.create_session()
        session_manager.start_session(initialize_managers=False)
        session_manager.end_session()
        
        # Check that session file was created
        session_file = temp_session_dir / f"session_{session_id}.json"
        assert session_file.exists()
    
    def test_load_session(self, session_manager, agent_id, temp_session_dir):
        """Test loading a previous session."""
        # Create and end a session
        session_id = session_manager.create_session(goals=["Original Goal"])
        session_manager.start_session(initialize_managers=False)
        session_manager.end_session()
        
        # Create a new manager and load the session
        new_manager = AgentSessionManager(agent_id=agent_id, session_root=temp_session_dir)
        success = new_manager.load_session(session_id)
        
        assert success
        assert new_manager.get_session_id() == session_id
        assert new_manager.get_context().goals == ["Original Goal"]
    
    def test_load_nonexistent_session_fails(self, session_manager):
        """Test that loading nonexistent session fails."""
        from uuid import uuid4
        nonexistent_id = uuid4()
        success = session_manager.load_session(nonexistent_id)
        
        assert not success


class TestSessionCleanup:
    """Tests for session cleanup."""
    
    def test_cleanup_session_without_removing_files(self, session_manager, temp_session_dir):
        """Test cleanup without removing files."""
        session_manager.create_session()
        session_manager.start_session(initialize_managers=True)
        
        success = session_manager.cleanup_session(remove_files=False)
        
        assert success
        # Session directory should still exist
        assert temp_session_dir.exists()
    
    def test_cleanup_with_file_removal(self, session_manager, agent_id, temp_session_dir):
        """Test cleanup with file removal."""
        session_id = session_manager.create_session()
        session_manager.start_session(initialize_managers=False)
        
        success = session_manager.cleanup_session(remove_files=True)
        
        assert success
        
        # Session file should be removed
        session_file = temp_session_dir / f"session_{session_id}.json"
        assert not session_file.exists()


class TestSessionIntegration:
    """Tests for integration with other managers."""
    
    def test_managers_available_after_start(self, session_manager):
        """Test that managers are available after session start."""
        session_manager.create_session()
        session_manager.start_session(initialize_managers=True)
        
        assert session_manager.get_identity_manager() is not None
        assert session_manager.get_memory_manager() is not None
        assert session_manager.get_workspace_manager() is not None
    
    def test_managers_not_initialized_if_disabled(self, session_manager):
        """Test that managers aren't initialized if disabled."""
        session_manager.create_session()
        session_manager.start_session(initialize_managers=False)
        
        assert session_manager.get_identity_manager() is None
        assert session_manager.get_memory_manager() is None
        assert session_manager.get_workspace_manager() is None


class TestSessionSummary:
    """Tests for session summary."""
    
    def test_session_summary_generation(self, session_manager):
        """Test generating session summary."""
        session_manager.create_session(goals=["Goal 1", "Goal 2"])
        session_manager.start_session(initialize_managers=False)
        session_manager.log_action("test", "Test action")
        summary = session_manager.end_session(notes="Session complete")
        
        assert isinstance(summary, SessionSummary)
        assert summary.state == SessionState.COMPLETED
        assert summary.goals == ["Goal 1", "Goal 2"]
        assert summary.notes == "Session complete"
        assert summary.metrics.errors_count == 0


class TestSessionStateTransitions:
    """Tests for valid state transitions."""
    
    def test_state_flow(self, session_manager):
        """Test normal session state flow."""
        assert session_manager.get_state() == SessionState.INITIALIZED
        
        session_manager.create_session()
        assert session_manager.get_state() == SessionState.INITIALIZED
        
        session_manager.start_session(initialize_managers=False)
        assert session_manager.get_state() == SessionState.ACTIVE
        
        session_manager.pause_session()
        assert session_manager.get_state() == SessionState.PAUSED
        
        session_manager.resume_session()
        assert session_manager.get_state() == SessionState.ACTIVE
        
        session_manager.end_session()
        assert session_manager.get_state() == SessionState.COMPLETED
    
    def test_invalid_state_transitions(self, session_manager):
        """Test that invalid state transitions are rejected."""
        session_manager.create_session()
        
        # Can't pause unstarted session
        assert not session_manager.pause_session()
        
        # Can't resume unpaused session
        assert not session_manager.resume_session()
