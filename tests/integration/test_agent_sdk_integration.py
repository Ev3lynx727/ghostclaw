"""
Integration tests for AgentSDK - Testing interaction between SDK components.

Focused integration tests for task orchestration, telemetry, and component interaction.
"""

import pytest
from uuid import UUID
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch

from ghostclaw.core.agent_sdk import (
    AgentTaskOrchestrator,
    AgentTelemetryManager,
    TaskType,
    TaskPriority,
    EventType,
    EventSeverity,
)


@pytest.fixture
def agent_id():
    """Create a test agent ID."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def task_orch(agent_id):
    """Create task orchestrator for testing."""
    return AgentTaskOrchestrator(agent_id=str(agent_id))


@pytest.fixture
def telemetry_mgr(agent_id, tmp_path):
    """Create telemetry manager for testing."""
    with patch("ghostclaw.core.agent_sdk.config.get_settings") as mock_settings:
        with patch("ghostclaw.core.agent_sdk.agent_telemetry.bootstrap_telemetry"):
            settings = MagicMock()
            settings.memory_base_dir = tmp_path / "memory"
            mock_settings.return_value = settings
            
            mgr = AgentTelemetryManager(agent_id)
            mgr.telemetry_dir = tmp_path / "telemetry"
            mgr.telemetry_dir.mkdir(parents=True, exist_ok=True)
            mgr.events_file = mgr.telemetry_dir / "events.jsonl"
            return mgr


class TestTaskOrchestrationIntegration:
    """Test task orchestration through complete workflow."""

    def test_create_and_execute_task_plan(self, task_orch):
        """Test creating and executing a task plan."""
        # Create tasks
        task1 = task_orch.create_task(
            name="Step 1",
            description="First step",
            task_type=TaskType.ANALYSIS,
            priority=TaskPriority.HIGH,
        )
        
        task2 = task_orch.create_task(
            name="Step 2",
            description="Second step",
            task_type=TaskType.ANALYSIS,
            priority=TaskPriority.NORMAL,
        )
        
        # Create plan with dependencies
        task_orch.add_dependency(task2, task1)
        plan_id = task_orch.create_plan(
            "Test Plan",
            "Test workflow",
            task_ids=[task1, task2],
        )
        
        # Verify execution order respects dependencies and priority
        order = task_orch.resolve_execution_order(plan_id)
        assert len(order) == 2
        assert order[0] == task1  # High priority task first
        assert order[1] == task2  # Dependent task second

    def test_execute_tasks_with_progress(self, task_orch):
        """Test executing tasks with progress tracking."""
        task_id = task_orch.create_task(
            "Execute",
            "Execute operation",
            task_type=TaskType.ANALYSIS,
        )
        
        # Start task
        assert task_orch.start_task(task_id) is True
        
        # Update progress
        task_orch.update_task_progress(task_id, 0.25)
        task_orch.update_task_progress(task_id, 0.50)
        task_orch.update_task_progress(task_id, 0.75)
        task_orch.update_task_progress(task_id, 1.0)
        
        # Complete
        assert task_orch.complete_task(task_id, success=True, output={"result": "ok"}) is True
        
        # Verify
        task = task_orch.get_task(task_id)
        assert task.progress == 1.0
        assert task.is_completed()

    def test_task_failure_and_retry(self, task_orch):
        """Test task failure retry handling."""
        task_id = task_orch.create_task(
            "Failing Task",
            "Task that fails",
            task_type=TaskType.ANALYSIS,
        )
        
        # Set max retries
        task = task_orch.get_task(task_id)
        task.max_retries = 2
        
        # First attempt - fail
        task_orch.start_task(task_id)
        assert task_orch.complete_task(task_id, success=False, error="Operation failed") is True
        
        # Retry
        assert task_orch.retry_task(task_id) is True
        task = task_orch.get_task(task_id)
        assert task.retry_count == 1
        assert task.state.value == "pending"
        
        # Second attempt - succeed
        task_orch.start_task(task_id)
        assert task_orch.complete_task(task_id, success=True) is True

    def test_plan_statistics(self, task_orch):
        """Test plan completion statistics."""
        # Create multiple tasks
        for i in range(5):
            task_id = task_orch.create_task(
                f"Task {i}",
                f"Task {i} description",
                task_type=TaskType.ANALYSIS,
            )
            task_orch.start_task(task_id)
            task_orch.complete_task(task_id, success=(i < 3), output={"task": i})
        
        # Get statistics
        stats = task_orch.get_execution_statistics()
        assert stats["total_tasks"] == 5
        assert stats["completed_tasks"] == 5
        assert stats["failed_tasks"] == 2


class TestTelemetryIntegration:
    """Test telemetry tracking and event recording."""

    def test_session_lifecycle_with_telemetry(self, telemetry_mgr):
        """Test telemetry session lifecycle."""
        # Start session
        telemetry_mgr.start_session()
        
        # Record events
        telemetry_mgr.record_event(
            EventType.AGENT_STARTED,
            "Agent initialized",
            severity=EventSeverity.INFO,
        )
        
        # Record metrics
        telemetry_mgr.record_metric("initialization_time_ms", 150.0)
        telemetry_mgr.record_metric("memory_bytes", 1024.0)
        
        # End session
        telemetry_mgr.end_session()
        
        # Verify
        session_metrics = telemetry_mgr.get_session_metrics()
        assert "session_duration_ms" in session_metrics
        assert session_metrics["initialization_time_ms"] == 150.0
        assert session_metrics["memory_bytes"] == 1024.0

    def test_analysis_event_tracking(self, telemetry_mgr):
        """Test tracking analysis events."""
        # Record analysis start
        telemetry_mgr.record_analysis_event(
            target_path="/src",
            event_type=EventType.ANALYSIS_STARTED,
            message="Starting analysis of /src",
            metrics={"files": 50, "total_lines": 5000},
        )
        
        # Record analysis completion
        telemetry_mgr.record_analysis_event(
            target_path="/src",
            event_type=EventType.ANALYSIS_COMPLETED,
            message="Analysis complete",
            metrics={"issues_found": 3, "duration_ms": 1200},
            issues=[
                {"severity": "high", "count": 1},
                {"severity": "medium", "count": 2},
            ],
        )
        
        # Verify
        events = telemetry_mgr.get_events()
        assert len(events) == 2
        assert events[0].event_type == EventType.ANALYSIS_STARTED
        assert events[1].event_type == EventType.ANALYSIS_COMPLETED

    def test_task_event_tracking(self, telemetry_mgr):
        """Test tracking task-specific events."""
        task_id = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
        
        # Record task events
        telemetry_mgr.record_task_event(
            task_id,
            EventType.TASK_STARTED,
            "Task execution started",
            metrics={"queue_position": 1},
        )
        
        telemetry_mgr.record_task_event(
            task_id,
            EventType.TASK_COMPLETED,
            "Task completed successfully",
            duration_ms=2500.0,
            metrics={"items_processed": 100},
        )
        
        # Verify
        events = telemetry_mgr.get_events()
        assert len(events) == 2

    def test_error_event_tracking(self, telemetry_mgr):
        """Test tracking error events."""
        try:
            raise ValueError("Test error for telemetry")
        except ValueError as e:
            telemetry_mgr.record_event(
                EventType.AGENT_ERROR,
                "Unexpected error occurred",
                severity=EventSeverity.ERROR,
                error_message=str(e),
                error_type=type(e).__name__,
            )
        
        # Verify
        events = telemetry_mgr.get_events()
        assert len(events) == 1
        assert events[0].severity == EventSeverity.ERROR
        assert "ValueError" in events[0].error_type


class TestTaskOrchestrationWithTelemetry:
    """Test task orchestration integrated with telemetry."""

    def test_task_execution_with_telemetry(self, task_orch, telemetry_mgr):
        """Test task execution with telemetry tracking."""
        telemetry_mgr.start_session()
        
        # Create task
        task_id = task_orch.create_task(
            "Analysis Task",
            "Analyze code",
            task_type=TaskType.ANALYSIS,
        )
        
        # Record task creation
        telemetry_mgr.record_task_event(
            task_id,
            EventType.TASK_CREATED,
            f"Task created: {task_id}",
        )
        
        # Execute task with telemetry
        task_orch.start_task(task_id)
        telemetry_mgr.record_task_event(
            task_id,
            EventType.TASK_STARTED,
            "Task execution started",
        )
        
        # Simulate progress
        for progress in [0.25, 0.50, 0.75]:
            task_orch.update_task_progress(task_id, progress)
            telemetry_mgr.record_metric("task_progress", progress * 100)
        
        # Complete task
        task_orch.complete_task(task_id, success=True, output={"result": "ok"})
        telemetry_mgr.record_task_event(
            task_id,
            EventType.TASK_COMPLETED,
            "Task completed successfully",
            duration_ms=1000.0,
            metrics={"output_size_bytes": 256},
        )
        
        # End telemetry session
        telemetry_mgr.end_session()
        
        # Verify integration
        task = task_orch.get_task(task_id)
        events = telemetry_mgr.get_events()
        metrics = telemetry_mgr.get_session_metrics()
        
        assert task.is_completed()
        assert len(events) >= 3  # created, started, completed
        assert "session_duration_ms" in metrics

    def test_multi_task_workflow_with_telemetry(self, task_orch, telemetry_mgr):
        """Test multi-task workflow with telemetry."""
        telemetry_mgr.start_session()
        telemetry_mgr.record_event(
            EventType.AGENT_STARTED,
            "Multi-task workflow started",
        )
        
        # Create interdependent tasks
        task1 = task_orch.create_task(
            "Analyze",
            "Analyze code",
            task_type=TaskType.ANALYSIS,
            priority=TaskPriority.HIGH,
        )
        
        task2 = task_orch.create_task(
            "Report",
            "Generate report",
            task_type=TaskType.ANALYSIS,
            priority=TaskPriority.NORMAL,
        )
        
        task_orch.add_dependency(task2, task1)
        
        # Create plan
        plan_id = task_orch.create_plan(
            "Analysis Workflow",
            "Analyze and report",
            task_ids=[task1, task2],
        )
        
        # Execute plan
        order = task_orch.resolve_execution_order(plan_id)
        for task_id in order:
            task_orch.start_task(task_id)
            telemetry_mgr.record_task_event(task_id, EventType.TASK_STARTED, "Started")
            
            # Simulate work
            task_orch.update_task_progress(task_id, 0.5)
            task_orch.update_task_progress(task_id, 1.0)
            
            task_orch.complete_task(task_id, success=True)
            telemetry_mgr.record_task_event(task_id, EventType.TASK_COMPLETED, "Completed")
        
        # Record workflow completion
        telemetry_mgr.record_event(
            EventType.ANALYSIS_COMPLETED,
            "Multi-task workflow completed",
            context={"tasks_completed": 2},
        )
        
        # End session
        telemetry_mgr.end_session()
        
        # Verify
        stats = task_orch.get_execution_statistics()
        
        assert stats["total_tasks"] == 2
        assert stats["completed_tasks"] == 2
        assert telemetry_mgr.get_event_count() >= 5  # start, created, completed, etc
