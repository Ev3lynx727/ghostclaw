# AgentTaskOrchestrator - Documentation

## Overview

The `AgentTaskOrchestrator` is a sophisticated task execution and planning engine for AI agents within the Ghostclaw architecture. It provides comprehensive task lifecycle management, dependency resolution, priority-based execution planning, and progress tracking.

## Core Concepts

### Task
A discrete unit of work managed by the orchestrator.

**Properties:**
- `id`: Unique UUID identifier
- `name`: Human-readable name
- `description`: Detailed description of the task
- `state`: Current state (PENDING, RUNNING, COMPLETED, FAILED, PAUSED, CANCELLED, BLOCKED)
- `priority`: Priority level (LOW, NORMAL, HIGH, CRITICAL)
- `type`: Task type (ANALYSIS, IMPLEMENTATION, TESTING, DEBUGGING, VALIDATION, OTHER)
- `parameters`: Input parameters as a dictionary
- `tags`: List of string tags for categorization
- `dependencies`: UUIDs of prerequisite tasks
- `created_at`: ISO timestamp of creation
- `started_at`: ISO timestamp of start
- `completed_at`: ISO timestamp of completion
- `progress`: Float (0.0-1.0) indicating completion percentage
- `result`: TaskResult object with output/error information
- `max_retries`: Maximum number of retry attempts
- `retry_count`: Current number of retries

**Methods:**
- `is_pending()`: Check if task is pending
- `is_running()`: Check if task is running
- `is_completed()`: Check if task is completed
- `get_duration()`: Get timedelta of execution time

### TaskState

Enumeration of possible task states:

- **PENDING**: Task created but not yet started
- **RUNNING**: Task actively executing
- **COMPLETED**: Task finished successfully
- **FAILED**: Task encountered error and failed
- **PAUSED**: Task temporarily paused
- **CANCELLED**: Task cancelled by user
- **BLOCKED**: Task waiting for dependencies

### TaskPriority

Enumeration of task priority levels (impacts execution order):

- **LOW**: 0
- **NORMAL**: 1
- **HIGH**: 2
- **CRITICAL**: 3

### TaskPlan

A collection of tasks organized for coordinated execution.

**Properties:**
- `id`: Unique UUID
- `name`: Plan name
- `description`: Plan description
- `tasks`: List of task UUIDs
- `created_at`: Creation timestamp

## API Reference

### Task Creation and Management

#### `create_task(name, description, task_type=None, priority=None, parameters=None, tags=None)`
Create a new task.

**Parameters:**
- `name` (str): Task name
- `description` (str): Task description
- `task_type` (TaskType, optional): Type of task
- `priority` (TaskPriority, optional): Priority level (default: NORMAL)
- `parameters` (dict, optional): Input parameters
- `tags` (list, optional): List of string tags

**Returns:** UUID of created task

**Example:**
```python
orch = AgentTaskOrchestrator()
task_id = orch.create_task(
    name="Analyze Module",
    description="Analyze core module structure",
    task_type=TaskType.ANALYSIS,
    priority=TaskPriority.HIGH,
    parameters={"path": "src/core", "depth": 3},
    tags=["urgent", "core"]
)
```

#### `get_task(task_id)`
Retrieve a task by ID.

**Parameters:**
- `task_id` (UUID): Task ID

**Returns:** Task object or None if not found

#### `update_task(task_id, **kwargs)`
Update task properties.

**Parameters:**
- `task_id` (UUID): Task ID
- `**kwargs`: Task properties to update (name, description, priority, etc.)

**Returns:** Boolean success indicator

#### `get_all_tasks(state=None, priority=None, tag=None)`
Get all tasks, optionally filtered.

**Parameters:**
- `state` (TaskState, optional): Filter by state
- `priority` (TaskPriority, optional): Filter by priority
- `tag` (str, optional): Filter by tag

**Returns:** List of Task objects

### Dependency Management

#### `add_dependency(task_id, dependency_id)`
Make a task depend on another task.

**Parameters:**
- `task_id` (UUID): Task that depends on another
- `dependency_id` (UUID): Task that must complete first

**Returns:** Boolean success indicator

**Example:**
```python
orch.add_dependency(integration_task_id, analysis_task_id)
# integration_task_id now depends on analysis_task_id completing
```

#### `get_task_dependencies(task_id)`
Get all dependencies for a task.

**Parameters:**
- `task_id` (UUID): Task ID

**Returns:** List of dependency task UUIDs

#### `are_dependencies_met(task_id)`
Check if all dependencies are satisfied.

**Parameters:**
- `task_id` (UUID): Task ID

**Returns:** Boolean indicating all dependencies completed

### Planning API

#### `create_plan(name, description, task_ids=None)`
Create a task plan.

**Parameters:**
- `name` (str): Plan name
- `description` (str): Plan description
- `task_ids` (list, optional): Initial list of task UUIDs

**Returns:** UUID of created plan

#### `get_plan(plan_id)`
Retrieve a plan.

**Parameters:**
- `plan_id` (UUID): Plan ID

**Returns:** TaskPlan object

#### `resolve_execution_order(plan_id)`
Determine optimal execution order for plan tasks.

**Logic:**
1. Respects task dependencies (topological sort)
2. Prioritizes by priority level (CRITICAL > HIGH > NORMAL > LOW)
3. Maintains task creation order as tiebreaker

**Parameters:**
- `plan_id` (UUID): Plan ID

**Returns:** List of task UUIDs in execution order

**Example:**
```python
order = orch.resolve_execution_order(plan_id)
for task_id in order:
    orch.start_task(task_id)
    # ... execute task ...
    orch.complete_task(task_id, success=True)
```

### Execution Control

#### `start_task(task_id)`
Start executing a task.

**Preconditions:**
- Task is in PENDING or PAUSED state
- All dependencies are completed

**Parameters:**
- `task_id` (UUID): Task ID

**Returns:** Boolean success indicator

#### `complete_task(task_id, success, output=None, error=None)`
Mark a task as completed.

**Parameters:**
- `task_id` (UUID): Task ID
- `success` (bool): Whether task succeeded
- `output` (dict, optional): Task output data
- `error` (str, optional): Error message if failed

**Returns:** Boolean success indicator

**Example:**
```python
success = orch.complete_task(
    task_id,
    success=True,
    output={"metrics": {...}, "issues": [...]}
)
```

#### `pause_task(task_id)`
Pause a running task.

**Parameters:**
- `task_id` (UUID): Task ID

**Returns:** Boolean success indicator

#### `resume_task(task_id)`
Resume a paused task.

**Parameters:**
- `task_id` (UUID): Task ID

**Returns:** Boolean success indicator

#### `cancel_task(task_id)`
Cancel a task.

**Parameters:**
- `task_id` (UUID): Task ID

**Returns:** Boolean success indicator

#### `retry_task(task_id)`
Retry a failed task.

**Logic:**
1. Increments retry_count
2. Resets task state to PENDING
3. Fails if max_retries exceeded

**Parameters:**
- `task_id` (UUID): Task ID

**Returns:** Boolean success indicator

### Progress Tracking

#### `update_task_progress(task_id, progress)`
Update task progress.

**Parameters:**
- `task_id` (UUID): Task ID
- `progress` (float): Progress value (0.0-1.0, auto-clamped)

**Returns:** Boolean success indicator

#### `get_plan_progress(plan_id)`
Get overall plan progress.

**Calculation:** Average progress of all plan tasks

**Parameters:**
- `plan_id` (UUID): Plan ID

**Returns:** Float (0.0-1.0)

#### `get_plan_status_summary(plan_id)`
Get descriptive status of all plan tasks.

**Parameters:**
- `plan_id` (UUID): Plan ID

**Returns:** Dictionary with keys:
- `pending`: Count of pending tasks
- `running`: Count of running tasks
- `completed`: Count of completed tasks
- `failed`: Count of failed tasks
- `paused`: Count of paused tasks
- `cancelled`: Count of cancelled tasks
- `blocked`: Count of blocked tasks

**Example:**
```python
summary = orch.get_plan_status_summary(plan_id)
print(f"Progress: {summary['completed']}/{len(plan.tasks)} completed")
```

### Statistics and Monitoring

#### `get_execution_statistics()`
Get overall execution statistics.

**Returns:** Dictionary with keys:
- `total_tasks`: Total number of tasks
- `completed_tasks`: Number of successfully completed tasks
- `failed_tasks`: Number of failed tasks
- `average_duration`: Average execution time (seconds)

**Example:**
```python
stats = orch.get_execution_statistics()
print(f"Success rate: {stats['completed_tasks'] / stats['total_tasks'] * 100}%")
```

## Usage Patterns

### Basic Workflow

```python
from ghostclaw.core.agent_sdk.agent_task_orchestrator import (
    AgentTaskOrchestrator,
    TaskType,
    TaskPriority,
)

# Create orchestrator
orch = AgentTaskOrchestrator(agent_id="my-agent")

# Create tasks
analyze_id = orch.create_task(
    name="Analyze Architecture",
    description="Analyze codebase structure",
    task_type=TaskType.ANALYSIS,
    priority=TaskPriority.HIGH
)

report_id = orch.create_task(
    name="Generate Report",
    description="Generate analysis report",
    task_type=TaskType.ANALYSIS,
    priority=TaskPriority.NORMAL
)

# Set dependency
orch.add_dependency(report_id, analyze_id)

# Create and plan
plan_id = orch.create_plan(
    "Analysis Plan",
    "Complete code analysis and reporting",
    task_ids=[analyze_id, report_id]
)

# Get execution order
order = orch.resolve_execution_order(plan_id)

# Execute
for task_id in order:
    orch.start_task(task_id)
    
    # Perform work...
    progress = 0.0
    for i in range(10):
        progress += 0.1
        orch.update_task_progress(task_id, progress)
    
    # Complete
    result = perform_analysis()  # Your work here
    orch.complete_task(
        task_id,
        success=True,
        output=result
    )
```

### Advanced: Conditional Retries

```python
max_attempts = 3
for attempt in range(max_attempts):
    orch.start_task(task_id)
    
    try:
        result = execute_task(task_id)
        orch.complete_task(task_id, success=True, output=result)
        break
    except Exception as e:
        if attempt < max_attempts - 1:
            orch.retry_task(task_id)
        else:
            orch.complete_task(task_id, success=False, error=str(e))
```

### Advanced: Priority-Based Execution

```python
# Get all high-priority pending tasks
critical_tasks = orch.get_all_tasks(
    state=TaskState.PENDING,
    priority=TaskPriority.CRITICAL
)

# Execute critical tasks first
for task in critical_tasks:
    orch.start_task(task.id)
    # ... execute and complete ...
```

## Integration with Agents

The orchestrator is designed to be integrated into agent workflows:

```python
class MyAgent:
    def __init__(self):
        self.orchestrator = AgentTaskOrchestrator(agent_id="my-agent")
    
    def plan_analysis(self, codebase_path):
        """Plan analysis tasks for the codebase."""
        plan_id = self.orchestrator.create_plan(
            "Code Analysis",
            f"Analyze {codebase_path}"
        )
        
        # Create analysis tasks
        task_ids = []
        for module in discover_modules(codebase_path):
            task_id = self.orchestrator.create_task(
                name=f"Analyze {module}",
                description=f"Analyze {module} module",
                task_type=TaskType.ANALYSIS,
                parameters={"module_path": module}
            )
            task_ids.append(task_id)
        
        return plan_id, task_ids
    
    def execute_plan(self, plan_id):
        """Execute plan with automatic ordering."""
        order = self.orchestrator.resolve_execution_order(plan_id)
        
        for task_id in order:
            task = self.orchestrator.get_task(task_id)
            self.orchestrator.start_task(task_id)
            
            # Execute with agent-specific logic
            result = self.execute_task(task)
            
            self.orchestrator.complete_task(
                task_id,
                success=result.success,
                output=result.data,
                error=result.error if not result.success else None
            )
```

## Error Handling

The orchestrator handles state validation gracefully:

- Invalid state transitions return `False`
- Non-existent tasks return `None`
- Dependencies are checked before execution
- Progress values are automatically clamped (0.0-1.0)

## Performance Considerations

- **Task Operations**: O(1) lookups via UUID
- **Dependency Resolution**: O(n + d) where n = tasks, d = dependencies (topological sort)
- **Execution Planning**: O(n log n) for priority sorting with dependency constraints
- **Statistics**: O(n) single pass calculation

## Testing

Comprehensive test suite in [test_agent_task_orchestrator.py](../../tests/unit/test_agent_task_orchestrator.py):

- 35 unit tests covering all functionality
- Edge case validation (blocked tasks, invalid transitions)
- Dependency resolution correctness
- Progress and statistics accuracy

Run tests:
```bash
python -m pytest tests/unit/test_agent_task_orchestrator.py -v
```
