"""
AgentTaskOrchestrator - Task execution and planning engine.

This module provides task management and orchestration capabilities:
- Task definition and representation
- Task planning and sequencing
- Dependency resolution
- Progress tracking and monitoring
- Execution lifecycle management
"""

import uuid
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from pydantic import BaseModel, Field


class TaskState(str, Enum):
    """Task lifecycle states."""

    PENDING = "pending"  # Task created, not started
    QUEUED = "queued"  # Task ready to execute, waiting in queue
    RUNNING = "running"  # Task currently executing
    PAUSED = "paused"  # Task paused during execution
    COMPLETED = "completed"  # Task finished successfully
    FAILED = "failed"  # Task failed with error
    CANCELLED = "cancelled"  # Task was cancelled
    BLOCKED = "blocked"  # Task blocked by dependency


class TaskPriority(str, Enum):
    """Task priority levels."""

    CRITICAL = "critical"  # Must run immediately
    HIGH = "high"  # Run soon, before medium/low
    NORMAL = "normal"  # Default priority
    LOW = "low"  # Run when resources available


class TaskType(str, Enum):
    """Task type categories."""

    ANALYSIS = "analysis"  # Code analysis task
    GENERATION = "generation"  # Code generation task
    TRANSFORMATION = "transformation"  # Code transformation
    VALIDATION = "validation"  # Testing/validation
    DOCUMENTATION = "documentation"  # Documentation generation
    CUSTOM = "custom"  # Custom user task


class TaskResult(BaseModel):
    """Result of a completed task."""

    task_id: UUID = Field(..., description="Task ID")
    success: bool = Field(..., description="Whether task succeeded")
    output: Optional[Dict[str, Any]] = Field(None, description="Task output data")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    duration: timedelta = Field(..., description="Task execution duration")
    created_at: datetime = Field(default_factory=datetime.now, description="Result creation time")


class TaskDependency(BaseModel):
    """Dependency between tasks."""

    task_id: UUID = Field(..., description="Task this depends on")
    required: bool = Field(default=True, description="Is this dependency required?")
    type: str = Field(default="completion", description="Dependency type (completion, output_required, etc.)")


class Task(BaseModel):
    """A single task to be executed."""

    id: UUID = Field(default_factory=uuid.uuid4, description="Unique task ID")
    name: str = Field(..., description="Task name/title")
    description: str = Field(..., description="Task description")
    task_type: TaskType = Field(default=TaskType.CUSTOM, description="Task type")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task priority")
    state: TaskState = Field(default=TaskState.PENDING, description="Current task state")
    
    # Task parameters and execution
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    command: Optional[str] = Field(None, description="Command to execute for this task")
    
    # Dependencies
    dependencies: List[TaskDependency] = Field(default_factory=list, description="Task dependencies")
    
    # Scheduling
    created_at: datetime = Field(default_factory=datetime.now, description="Task creation time")
    started_at: Optional[datetime] = Field(None, description="Task start time")
    completed_at: Optional[datetime] = Field(None, description="Task completion time")
    estimated_duration: Optional[timedelta] = Field(None, description="Estimated duration")
    
    # Progress tracking
    progress: float = Field(default=0.0, description="Progress 0.0-1.0")
    result: Optional[TaskResult] = Field(None, description="Task result (if completed)")
    
    # Metadata
    tags: List[str] = Field(default_factory=list, description="Task tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")
    max_retries: int = Field(default=0, description="Maximum retry attempts")
    retry_count: int = Field(default=0, description="Current retry count")

    def is_pending(self) -> bool:
        """Check if task is pending."""
        return self.state == TaskState.PENDING

    def is_running(self) -> bool:
        """Check if task is running."""
        return self.state == TaskState.RUNNING

    def is_completed(self) -> bool:
        """Check if task is completed."""
        return self.state in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED)

    def is_blocked(self) -> bool:
        """Check if task is blocked."""
        return self.state == TaskState.BLOCKED

    def get_duration(self) -> Optional[timedelta]:
        """Get actual execution duration if completed."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None


class TaskPlan(BaseModel):
    """A plan of tasks to execute."""

    id: UUID = Field(default_factory=uuid.uuid4, description="Plan ID")
    name: str = Field(..., description="Plan name")
    description: str = Field(..., description="Plan description")
    tasks: List[Task] = Field(default_factory=list, description="Tasks in plan")
    
    # Planning state
    created_at: datetime = Field(default_factory=datetime.now, description="Plan creation time")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    execution_order: List[UUID] = Field(default_factory=list, description="Planned execution order")
    
    # Execution state
    started_at: Optional[datetime] = Field(None, description="Plan execution start")
    completed_at: Optional[datetime] = Field(None, description="Plan execution end")
    
    # Metadata
    tags: List[str] = Field(default_factory=list, description="Plan tags")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata")

    def get_task(self, task_id: UUID) -> Optional[Task]:
        """Get task by ID."""
        return next((t for t in self.tasks if t.id == task_id), None)

    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks."""
        return [t for t in self.tasks if t.is_pending()]

    def get_completed_tasks(self) -> List[Task]:
        """Get all completed tasks."""
        return [t for t in self.tasks if t.is_completed()]

    def is_complete(self) -> bool:
        """Check if all tasks are completed."""
        return all(t.is_completed() for t in self.tasks)


class AgentTaskOrchestrator:
    """
    Orchestrates task planning, scheduling, and execution.
    
    Manages task lifecycle including creation, planning, sequencing,
    dependency resolution, and progress tracking.
    """

    def __init__(self, agent_id: str = "default-agent"):
        """
        Initialize the task orchestrator.

        Args:
            agent_id: Agent ID for task tracking
        """
        self.agent_id = agent_id
        
        # Task storage
        self._tasks: Dict[UUID, Task] = {}
        self._plans: Dict[UUID, TaskPlan] = {}
        self._active_plan: Optional[TaskPlan] = None
        self._task_results: Dict[UUID, TaskResult] = {}
        
        # Execution queues
        self._execution_queue: List[UUID] = []
        self._completed_queue: List[UUID] = []

    # ============================================================================
    # Task Creation and Management
    # ============================================================================

    def create_task(
        self,
        name: str,
        description: str,
        task_type: TaskType = TaskType.CUSTOM,
        priority: TaskPriority = TaskPriority.NORMAL,
        parameters: Optional[Dict[str, Any]] = None,
        command: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> UUID:
        """
        Create a new task.

        Args:
            name: Task name
            description: Task description
            task_type: Type of task
            priority: Task priority
            parameters: Task parameters
            command: Command to execute
            tags: Task tags

        Returns:
            Task ID
        """
        task = Task(
            name=name,
            description=description,
            task_type=task_type,
            priority=priority,
            parameters=parameters or {},
            command=command,
            tags=tags or [],
        )

        self._tasks[task.id] = task
        return task.id

    def get_task(self, task_id: UUID) -> Optional[Task]:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def update_task(self, task_id: UUID, **kwargs) -> bool:
        """
        Update task properties.

        Args:
            task_id: Task ID
            **kwargs: Properties to update

        Returns:
            True if successful
        """
        task = self.get_task(task_id)
        if not task:
            return False

        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        return True

    def get_all_tasks(self) -> List[Task]:
        """Get all tasks."""
        return list(self._tasks.values())

    # ============================================================================
    # Dependency Management
    # ============================================================================

    def add_dependency(
        self, task_id: UUID, depends_on: UUID, required: bool = True, dep_type: str = "completion"
    ) -> bool:
        """
        Add a dependency between tasks.

        Args:
            task_id: Task that depends on another
            depends_on: Task that must complete first
            required: Whether dependency is required
            dep_type: Type of dependency

        Returns:
            True if successful
        """
        task = self.get_task(task_id)
        if not task:
            return False

        dependency = TaskDependency(task_id=depends_on, required=required, type=dep_type)
        task.dependencies.append(dependency)
        return True

    def get_task_dependencies(self, task_id: UUID) -> List[UUID]:
        """Get all task dependencies."""
        task = self.get_task(task_id)
        if not task:
            return []

        return [dep.task_id for dep in task.dependencies]

    def are_dependencies_met(self, task_id: UUID) -> bool:
        """Check if all dependencies for a task are met."""
        task = self.get_task(task_id)
        if not task or not task.dependencies:
            return True

        for dep in task.dependencies:
            dep_task = self.get_task(dep.task_id)
            if dep.required and (not dep_task or not dep_task.is_completed()):
                return False

        return True

    # ============================================================================
    # Task Planning and Sequencing
    # ============================================================================

    def create_plan(self, name: str, description: str, task_ids: Optional[List[UUID]] = None) -> UUID:
        """
        Create a task plan.

        Args:
            name: Plan name
            description: Plan description
            task_ids: Task IDs to include in plan

        Returns:
            Plan ID
        """
        plan = TaskPlan(name=name, description=description)

        if task_ids:
            for task_id in task_ids:
                task = self.get_task(task_id)
                if task:
                    plan.tasks.append(task)

        self._plans[plan.id] = plan
        return plan.id

    def get_plan(self, plan_id: UUID) -> Optional[TaskPlan]:
        """Get a plan by ID."""
        return self._plans.get(plan_id)

    def resolve_execution_order(self, plan_id: UUID) -> List[UUID]:
        """
        Resolve the optimal execution order for tasks (respecting dependencies).

        Args:
            plan_id: Plan ID

        Returns:
            List of task IDs in execution order
        """
        plan = self.get_plan(plan_id)
        if not plan or not plan.tasks:
            return []

        # Topological sort with priority consideration
        execution_order = []
        processed: Set[UUID] = set()
        in_progress: Set[UUID] = set()

        def visit(task_id: UUID) -> bool:
            """DFS visit for topological sort."""
            if task_id in processed:
                return True
            if task_id in in_progress:
                # Circular dependency detected
                return False

            in_progress.add(task_id)
            task = self.get_task(task_id)

            if task:
                # Visit dependencies first
                for dep in task.dependencies:
                    if not visit(dep.task_id):
                        return False

            in_progress.remove(task_id)
            processed.add(task_id)
            execution_order.append(task_id)
            return True

        # Sort by priority first
        sorted_tasks = sorted(
            plan.tasks,
            key=lambda t: (
                0 if t.priority == TaskPriority.CRITICAL else
                1 if t.priority == TaskPriority.HIGH else
                2 if t.priority == TaskPriority.NORMAL else
                3
            ),
        )

        for task in sorted_tasks:
            if task.id not in processed:
                visit(task.id)

        plan.execution_order = execution_order
        return execution_order

    # ============================================================================
    # Task Execution
    # ============================================================================

    def start_task(self, task_id: UUID) -> bool:
        """
        Start executing a task.

        Args:
            task_id: Task ID

        Returns:
            True if started successfully
        """
        task = self.get_task(task_id)
        if not task or not task.is_pending():
            return False

        if not self.are_dependencies_met(task_id):
            task.state = TaskState.BLOCKED
            return False

        task.state = TaskState.RUNNING
        task.started_at = datetime.now()
        self._execution_queue.append(task_id)
        return True

    def complete_task(
        self, task_id: UUID, success: bool, output: Optional[Dict[str, Any]] = None, error: Optional[str] = None
    ) -> bool:
        """
        Mark a task as completed.

        Args:
            task_id: Task ID
            success: Whether task succeeded
            output: Task output data
            error: Error message if failed

        Returns:
            True if successful
        """
        task = self.get_task(task_id)
        if not task or not task.is_running():
            return False

        task.state = TaskState.COMPLETED if success else TaskState.FAILED
        task.completed_at = datetime.now()
        task.progress = 1.0

        # Create result
        result = TaskResult(
            task_id=task_id,
            success=success,
            output=output,
            error_message=error,
            duration=task.get_duration() or timedelta(0),
        )

        task.result = result
        self._task_results[task_id] = result
        self._completed_queue.append(task_id)

        return True

    def pause_task(self, task_id: UUID) -> bool:
        """Pause a running task."""
        task = self.get_task(task_id)
        if not task or not task.is_running():
            return False

        task.state = TaskState.PAUSED
        return True

    def resume_task(self, task_id: UUID) -> bool:
        """Resume a paused task."""
        task = self.get_task(task_id)
        if not task or task.state != TaskState.PAUSED:
            return False

        task.state = TaskState.RUNNING
        return True

    def cancel_task(self, task_id: UUID) -> bool:
        """Cancel a task."""
        task = self.get_task(task_id)
        if not task or task.is_completed():
            return False

        task.state = TaskState.CANCELLED
        if task.started_at and not task.completed_at:
            task.completed_at = datetime.now()

        return True

    def retry_task(self, task_id: UUID) -> bool:
        """Retry a failed task."""
        task = self.get_task(task_id)
        if not task or task.state != TaskState.FAILED:
            return False

        if task.retry_count >= task.max_retries:
            return False

        task.retry_count += 1
        task.state = TaskState.PENDING
        task.started_at = None
        task.completed_at = None
        task.progress = 0.0
        task.result = None

        return True

    # ============================================================================
    # Progress Tracking
    # ============================================================================

    def update_task_progress(self, task_id: UUID, progress: float) -> bool:
        """
        Update task progress (0.0-1.0).

        Args:
            task_id: Task ID
            progress: Progress value (0.0-1.0)

        Returns:
            True if successful
        """
        task = self.get_task(task_id)
        if not task:
            return False

        task.progress = max(0.0, min(1.0, progress))
        return True

    def get_plan_progress(self, plan_id: UUID) -> float:
        """Get overall plan progress (0.0-1.0)."""
        plan = self.get_plan(plan_id)
        if not plan or not plan.tasks:
            return 0.0

        if all(t.is_completed() for t in plan.tasks):
            return 1.0

        completed = sum(1 for t in plan.tasks if t.is_completed())
        return completed / len(plan.tasks)

    def get_plan_status_summary(self, plan_id: UUID) -> Dict[str, int]:
        """Get count of tasks in each state."""
        plan = self.get_plan(plan_id)
        if not plan:
            return {}

        summary = {
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "blocked": 0,
            "cancelled": 0,
        }

        for task in plan.tasks:
            if task.state == TaskState.PENDING:
                summary["pending"] += 1
            elif task.state == TaskState.RUNNING:
                summary["running"] += 1
            elif task.state == TaskState.COMPLETED:
                summary["completed"] += 1
            elif task.state == TaskState.FAILED:
                summary["failed"] += 1
            elif task.state == TaskState.BLOCKED:
                summary["blocked"] += 1
            elif task.state == TaskState.CANCELLED:
                summary["cancelled"] += 1

        return summary

    # ============================================================================
    # Statistics and Reporting
    # ============================================================================

    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get execution statistics."""
        total_tasks = len(self._tasks)
        completed = len(self._completed_queue)

        durations = []
        for result in self._task_results.values():
            if result.success:
                durations.append(result.duration.total_seconds())

        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed,
            "failed_tasks": sum(1 for r in self._task_results.values() if not r.success),
            "average_duration": sum(durations) / len(durations) if durations else 0,
            "min_duration": min(durations) if durations else 0,
            "max_duration": max(durations) if durations else 0,
            "execution_queue_size": len(self._execution_queue),
        }


__all__ = [
    "AgentTaskOrchestrator",
    "Task",
    "TaskPlan",
    "TaskResult",
    "TaskDependency",
    "TaskState",
    "TaskPriority",
    "TaskType",
]
