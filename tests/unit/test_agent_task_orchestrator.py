"""
Tests for AgentTaskOrchestrator - Task execution and planning engine.

Comprehensive test suite for task creation, planning, sequencing,
dependency resolution, and execution lifecycle.
"""

import pytest
from datetime import timedelta
from uuid import UUID

from ghostclaw.core.agent_sdk.agent_task_orchestrator import (
    AgentTaskOrchestrator,
    Task,
    TaskPlan,
    TaskResult,
    TaskState,
    TaskPriority,
    TaskType,
)


class TestTaskModel:
    """Test Task model and properties."""

    def test_task_creation(self):
        """Test creating a task."""
        task = Task(name="Test Task", description="A test task")
        assert task.name == "Test Task"
        assert task.description == "A test task"
        assert task.state == TaskState.PENDING
        assert task.priority == TaskPriority.NORMAL

    def test_task_states(self):
        """Test task state checks."""
        task = Task(name="Test", description="Test")
        assert task.is_pending()
        assert not task.is_running()
        assert not task.is_completed()

    def test_task_with_priority(self):
        """Test task with different priorities."""
        task = Task(
            name="Critical",
            description="Critical task",
            priority=TaskPriority.CRITICAL,
        )
        assert task.priority == TaskPriority.CRITICAL

    def test_task_duration(self):
        """Test task duration calculation."""
        from datetime import datetime

        task = Task(name="Test", description="Test")
        task.started_at = datetime.now()
        task.completed_at = task.started_at + timedelta(seconds=10)

        duration = task.get_duration()
        assert duration is not None
        assert duration.total_seconds() == 10


class TestOrchestratorBasics:
    """Test basic orchestrator functionality."""

    def test_orchestrator_init(self):
        """Test orchestrator initialization."""
        orch = AgentTaskOrchestrator(agent_id="test-agent")
        assert orch.agent_id == "test-agent"
        assert len(orch.get_all_tasks()) == 0

    def test_create_task(self):
        """Test creating a task."""
        orch = AgentTaskOrchestrator()
        task_id = orch.create_task(
            name="Analyze Code",
            description="Analyze the codebase",
            task_type=TaskType.ANALYSIS,
        )
        assert isinstance(task_id, UUID)
        assert len(orch.get_all_tasks()) == 1

    def test_get_task(self):
        """Test retrieving a task."""
        orch = AgentTaskOrchestrator()
        task_id = orch.create_task(name="Test", description="Test task")
        task = orch.get_task(task_id)
        assert task is not None
        assert task.name == "Test"

    def test_update_task(self):
        """Test updating task properties."""
        orch = AgentTaskOrchestrator()
        task_id = orch.create_task(name="Original", description="Original")
        success = orch.update_task(task_id, name="Updated")
        assert success is True
        assert orch.get_task(task_id).name == "Updated"

    def test_task_with_parameters(self):
        """Test task with parameters."""
        orch = AgentTaskOrchestrator()
        params = {"file_path": "/src", "depth": 3}
        task_id = orch.create_task(
            name="Analyze",
            description="Analyze",
            parameters=params,
        )
        task = orch.get_task(task_id)
        assert task.parameters == params

    def test_task_with_tags(self):
        """Test task with tags."""
        orch = AgentTaskOrchestrator()
        tags = ["urgent", "python", "analysis"]
        task_id = orch.create_task(
            name="Analyze",
            description="Analyze",
            tags=tags,
        )
        task = orch.get_task(task_id)
        assert task.tags == tags


class TestDependencies:
    """Test task dependency management."""

    def test_add_dependency(self):
        """Test adding task dependency."""
        orch = AgentTaskOrchestrator()
        task1_id = orch.create_task(name="Setup", description="Setup")
        task2_id = orch.create_task(name="Execute", description="Execute")

        success = orch.add_dependency(task2_id, task1_id)
        assert success is True

        deps = orch.get_task_dependencies(task2_id)
        assert task1_id in deps

    def test_dependency_not_met(self):
        """Test checking unmet dependencies."""
        orch = AgentTaskOrchestrator()
        task1_id = orch.create_task(name="Task1", description="Task1")
        task2_id = orch.create_task(name="Task2", description="Task2")

        orch.add_dependency(task2_id, task1_id)

        # Dependency not met yet
        assert not orch.are_dependencies_met(task2_id)

    def test_dependency_met(self):
        """Test checking met dependencies."""
        orch = AgentTaskOrchestrator()
        task1_id = orch.create_task(name="Task1", description="Task1")
        task2_id = orch.create_task(name="Task2", description="Task2")

        orch.add_dependency(task2_id, task1_id)

        # Complete task1
        orch.start_task(task1_id)
        orch.complete_task(task1_id, success=True)

        # Now dependency is met
        assert orch.are_dependencies_met(task2_id)

    def test_no_dependencies(self):
        """Test task with no dependencies."""
        orch = AgentTaskOrchestrator()
        task_id = orch.create_task(name="Task", description="Task")
        assert orch.are_dependencies_met(task_id)


class TestPlanning:
    """Test task planning and sequencing."""

    def test_create_plan(self):
        """Test creating a task plan."""
        orch = AgentTaskOrchestrator()
        plan_id = orch.create_plan(
            name="Analysis Plan",
            description="Plan for code analysis",
        )
        assert isinstance(plan_id, UUID)

    def test_plan_with_tasks(self):
        """Test plan with tasks."""
        orch = AgentTaskOrchestrator()
        task1_id = orch.create_task(name="Task1", description="Task1")
        task2_id = orch.create_task(name="Task2", description="Task2")

        plan_id = orch.create_plan(
            name="Plan",
            description="Plan",
            task_ids=[task1_id, task2_id],
        )

        plan = orch.get_plan(plan_id)
        assert len(plan.tasks) == 2

    def test_resolve_execution_order_simple(self):
        """Test resolving execution order for simple tasks."""
        orch = AgentTaskOrchestrator()
        task1_id = orch.create_task(
            name="Task1",
            description="Task1",
            priority=TaskPriority.HIGH,
        )
        task2_id = orch.create_task(
            name="Task2",
            description="Task2",
            priority=TaskPriority.NORMAL,
        )

        plan_id = orch.create_plan("Plan", "Plan", task_ids=[task1_id, task2_id])

        order = orch.resolve_execution_order(plan_id)
        # High priority should come first
        assert order[0] == task1_id

    def test_resolve_execution_order_with_dependencies(self):
        """Test resolving order with dependencies."""
        orch = AgentTaskOrchestrator()
        task1_id = orch.create_task(name="Setup", description="Setup")
        task2_id = orch.create_task(name="Execute", description="Execute")
        task3_id = orch.create_task(name="Report", description="Report")

        orch.add_dependency(task2_id, task1_id)
        orch.add_dependency(task3_id, task2_id)

        plan_id = orch.create_plan("Plan", "Plan", task_ids=[task3_id, task1_id, task2_id])

        order = orch.resolve_execution_order(plan_id)
        # Should respect dependencies
        assert order.index(task1_id) < order.index(task2_id)
        assert order.index(task2_id) < order.index(task3_id)


class TestExecution:
    """Test task execution lifecycle."""

    def test_start_task(self):
        """Test starting a task."""
        orch = AgentTaskOrchestrator()
        task_id = orch.create_task(name="Task", description="Task")

        success = orch.start_task(task_id)
        assert success is True

        task = orch.get_task(task_id)
        assert task.state == TaskState.RUNNING
        assert task.started_at is not None

    def test_complete_task_success(self):
        """Test completing a task successfully."""
        orch = AgentTaskOrchestrator()
        task_id = orch.create_task(name="Task", description="Task")
        orch.start_task(task_id)

        output = {"result": "success"}
        success = orch.complete_task(task_id, success=True, output=output)

        assert success is True
        task = orch.get_task(task_id)
        assert task.state == TaskState.COMPLETED
        assert task.progress == 1.0
        assert task.result is not None
        assert task.result.output == output

    def test_complete_task_failure(self):
        """Test completing a task with failure."""
        orch = AgentTaskOrchestrator()
        task_id = orch.create_task(name="Task", description="Task")
        orch.start_task(task_id)

        success = orch.complete_task(
            task_id, success=False, error="Task failed"
        )

        assert success is True
        task = orch.get_task(task_id)
        assert task.state == TaskState.FAILED
        assert task.result.error_message == "Task failed"

    def test_pause_and_resume_task(self):
        """Test pausing and resuming a task."""
        orch = AgentTaskOrchestrator()
        task_id = orch.create_task(name="Task", description="Task")
        orch.start_task(task_id)

        # Pause
        success = orch.pause_task(task_id)
        assert success is True
        assert orch.get_task(task_id).state == TaskState.PAUSED

        # Resume
        success = orch.resume_task(task_id)
        assert success is True
        assert orch.get_task(task_id).state == TaskState.RUNNING

    def test_cancel_task(self):
        """Test cancelling a task."""
        orch = AgentTaskOrchestrator()
        task_id = orch.create_task(name="Task", description="Task")
        orch.start_task(task_id)

        success = orch.cancel_task(task_id)
        assert success is True
        assert orch.get_task(task_id).state == TaskState.CANCELLED

    def test_retry_task(self):
        """Test retrying a failed task."""
        orch = AgentTaskOrchestrator()
        task_id = orch.create_task(
            name="Task",
            description="Task",
        )
        task = orch.get_task(task_id)
        task.max_retries = 3

        # Fail task
        orch.start_task(task_id)
        orch.complete_task(task_id, success=False)

        # Retry
        success = orch.retry_task(task_id)
        assert success is True

        task = orch.get_task(task_id)
        assert task.state == TaskState.PENDING
        assert task.retry_count == 1


class TestProgress:
    """Test progress tracking."""

    def test_update_task_progress(self):
        """Test updating task progress."""
        orch = AgentTaskOrchestrator()
        task_id = orch.create_task(name="Task", description="Task")

        success = orch.update_task_progress(task_id, 0.5)
        assert success is True
        assert orch.get_task(task_id).progress == 0.5

    def test_progress_bounds(self):
        """Test progress bounds (0.0-1.0)."""
        orch = AgentTaskOrchestrator()
        task_id = orch.create_task(name="Task", description="Task")

        # Over 1.0 should be capped
        orch.update_task_progress(task_id, 1.5)
        assert orch.get_task(task_id).progress == 1.0

        # Below 0.0 should be floored
        orch.update_task_progress(task_id, -0.5)
        assert orch.get_task(task_id).progress == 0.0

    def test_plan_progress(self):
        """Test plan progress calculation."""
        orch = AgentTaskOrchestrator()
        task1_id = orch.create_task(name="Task1", description="Task1")
        task2_id = orch.create_task(name="Task2", description="Task2")

        plan_id = orch.create_plan("Plan", "Plan", task_ids=[task1_id, task2_id])

        # Initial progress
        progress = orch.get_plan_progress(plan_id)
        assert progress == 0.0

        # Complete one task
        orch.start_task(task1_id)
        orch.complete_task(task1_id, success=True)

        progress = orch.get_plan_progress(plan_id)
        assert progress == 0.5

    def test_plan_status_summary(self):
        """Test plan status summary."""
        orch = AgentTaskOrchestrator()
        task1_id = orch.create_task(name="Task1", description="Task1")
        task2_id = orch.create_task(name="Task2", description="Task2")

        plan_id = orch.create_plan("Plan", "Plan", task_ids=[task1_id, task2_id])

        # Initial
        summary = orch.get_plan_status_summary(plan_id)
        assert summary["pending"] == 2

        # Start one
        orch.start_task(task1_id)
        summary = orch.get_plan_status_summary(plan_id)
        assert summary["running"] == 1

        # Complete one
        orch.complete_task(task1_id, success=True)
        summary = orch.get_plan_status_summary(plan_id)
        assert summary["completed"] == 1


class TestStatistics:
    """Test execution statistics."""

    def test_execution_statistics(self):
        """Test getting execution statistics."""
        orch = AgentTaskOrchestrator()
        task_id = orch.create_task(name="Task", description="Task")
        orch.start_task(task_id)
        orch.complete_task(task_id, success=True)

        stats = orch.get_execution_statistics()
        assert stats["total_tasks"] == 1
        assert stats["completed_tasks"] == 1
        assert stats["failed_tasks"] == 0

    def test_statistics_with_multiple_tasks(self):
        """Test statistics with multiple tasks."""
        orch = AgentTaskOrchestrator()
        for i in range(5):
            task_id = orch.create_task(name=f"Task{i}", description=f"Task{i}")
            orch.start_task(task_id)
            orch.complete_task(task_id, success=(i < 3), output={"num": i})

        stats = orch.get_execution_statistics()
        assert stats["total_tasks"] == 5
        assert stats["completed_tasks"] == 5
        assert stats["failed_tasks"] == 2


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_cannot_start_completed_task(self):
        """Test that completed tasks cannot be restarted."""
        orch = AgentTaskOrchestrator()
        task_id = orch.create_task(name="Task", description="Task")
        orch.start_task(task_id)
        orch.complete_task(task_id, success=True)

        success = orch.start_task(task_id)
        assert success is False

    def test_cannot_complete_pending_task(self):
        """Test that pending tasks cannot be completed."""
        orch = AgentTaskOrchestrator()
        task_id = orch.create_task(name="Task", description="Task")

        success = orch.complete_task(task_id, success=True)
        assert success is False

    def test_blocked_task_with_unmet_dependency(self):
        """Test task gets blocked if dependencies not met."""
        orch = AgentTaskOrchestrator()
        task1_id = orch.create_task(name="Task1", description="Task1")
        task2_id = orch.create_task(name="Task2", description="Task2")

        orch.add_dependency(task2_id, task1_id)

        # Try to start task2 without completing task1
        success = orch.start_task(task2_id)
        # Should fail or mark as blocked
        assert success is False or orch.get_task(task2_id).state == TaskState.BLOCKED

    def test_get_nonexistent_task(self):
        """Test getting non-existent task."""
        orch = AgentTaskOrchestrator()
        from uuid import uuid4
        task = orch.get_task(uuid4())
        assert task is None

    def test_empty_plan_progress(self):
        """Test progress of empty plan."""
        orch = AgentTaskOrchestrator()
        plan_id = orch.create_plan("Empty Plan", "No tasks")
        progress = orch.get_plan_progress(plan_id)
        assert progress == 0.0
