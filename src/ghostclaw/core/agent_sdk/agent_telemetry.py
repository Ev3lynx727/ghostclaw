"""
Agent Telemetry Module

Handles telemetry and observability for agent execution including activity tracking,
metrics collection, performance monitoring, and event logging.

Integrates with Ghostclaw's telemetry adapters (Logfire, etc.) for distributed tracing
and observability.

Main class: AgentTelemetryManager - handles telemetry lifecycle and event dispatch
"""

from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID
import json
import logging

from pydantic import BaseModel, Field

from ghostclaw.core.adapters.telemetry import bootstrap_telemetry
from .config import get_settings

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of events tracked by the telemetry manager."""

    # Agent lifecycle events
    AGENT_CREATED = "agent.created"
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_ERROR = "agent.error"

    # Task events
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"

    # Analysis events
    ANALYSIS_STARTED = "analysis.started"
    ANALYSIS_COMPLETED = "analysis.completed"
    ANALYSIS_FAILED = "analysis.failed"

    # Execution events
    EXECUTION_STARTED = "execution.started"
    EXECUTION_COMPLETED = "execution.completed"
    EXECUTION_PAUSED = "execution.paused"
    EXECUTION_RESUMED = "execution.resumed"

    # Custom events
    CUSTOM = "custom"


class EventSeverity(str, Enum):
    """Event severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class TelemetryEvent(BaseModel):
    """Represents a telemetry event."""

    event_type: EventType = Field(..., description="Type of event")
    agent_id: UUID = Field(..., description="Agent ID")
    timestamp: datetime = Field(default_factory=datetime.now, description="Event timestamp")
    severity: EventSeverity = Field(default=EventSeverity.INFO, description="Event severity")
    
    # Event context
    message: str = Field(..., description="Event message/description")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    
    # Performance metrics (optional)
    duration_ms: Optional[float] = Field(None, description="Duration in milliseconds")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Performance metrics")
    
    # Error information (if applicable)
    error_message: Optional[str] = Field(None, description="Error message")
    error_type: Optional[str] = Field(None, description="Error type/class name")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_type": self.event_type.value,
            "agent_id": str(self.agent_id),
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity.value,
            "message": self.message,
            "context": self.context,
            "duration_ms": self.duration_ms,
            "metrics": self.metrics,
            "error_message": self.error_message,
            "error_type": self.error_type,
        }


class MetricPoint(BaseModel):
    """A single metric data point."""

    name: str = Field(..., description="Metric name")
    value: float = Field(..., description="Metric value")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp")
    labels: Dict[str, str] = Field(default_factory=dict, description="Labels/tags")


class AgentTelemetryManager:
    """
    Manages telemetry and observability for agent execution.
    
    Features:
    - Event tracking and recording
    - Performance metrics collection
    - Distributed tracing integration
    - Local event storage with rotation
    - Telemetry adapter integration (Logfire, etc.)
    """

    EVENTS_FILENAME = "events.jsonl"
    MAX_EVENTS_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

    def __init__(self, agent_id: UUID):
        """
        Initialize telemetry manager.

        Args:
            agent_id: Agent ID for telemetry tracking
        """
        self.agent_id = agent_id
        self.settings = get_settings()
        self.telemetry_dir = self.settings.memory_base_dir / str(agent_id) / "telemetry"
        self.events_file = self.telemetry_dir / self.EVENTS_FILENAME
        
        # Initialize telemetry adapter
        self.adapter = bootstrap_telemetry()
        
        # In-memory event buffer
        self._event_buffer: List[TelemetryEvent] = []
        self._metric_buffer: List[MetricPoint] = []
        
        # Session state
        self._session_started_at: Optional[datetime] = None
        self._session_metrics: Dict[str, float] = {}
        
        # Ensure telemetry directory exists
        self.telemetry_dir.mkdir(parents=True, exist_ok=True)

    def start_session(self) -> None:
        """Start a telemetry session."""
        self._session_started_at = datetime.now()
        self._session_metrics = {}
        
        self.record_event(
            EventType.AGENT_STARTED,
            "Telemetry session started",
            severity=EventSeverity.INFO,
        )

    def end_session(self) -> None:
        """End the telemetry session and flush all data."""
        if self._session_started_at:
            duration = datetime.now() - self._session_started_at
            self._session_metrics["session_duration_ms"] = duration.total_seconds() * 1000
        
        self.record_event(
            EventType.AGENT_STOPPED,
            "Telemetry session ended",
            severity=EventSeverity.INFO,
            metrics=self._session_metrics,
        )
        
        self.flush()

    def record_event(
        self,
        event_type: EventType,
        message: str,
        severity: EventSeverity = EventSeverity.INFO,
        context: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        metrics: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_type: Optional[str] = None,
    ) -> None:
        """
        Record a telemetry event.

        Args:
            event_type: Type of event
            message: Event message/description
            severity: Event severity level
            context: Additional context data
            duration_ms: Duration in milliseconds
            metrics: Performance metrics
            error_message: Error message if applicable
            error_type: Error type/class name
        """
        event = TelemetryEvent(
            event_type=event_type,
            agent_id=self.agent_id,
            severity=severity,
            message=message,
            context=context or {},
            duration_ms=duration_ms,
            metrics=metrics or {},
            error_message=error_message,
            error_type=error_type,
        )

        self._event_buffer.append(event)
        
        # Log event locally
        self._write_event(event)
        
        # Forward to telemetry adapter if available
        if self.adapter:
            self._forward_to_adapter(event)

    def record_metric(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        Record a metric data point.

        Args:
            name: Metric name
            value: Metric value
            labels: Optional labels/tags
        """
        metric = MetricPoint(
            name=name,
            value=value,
            labels=labels or {},
        )

        self._metric_buffer.append(metric)
        
        # Update session metrics
        if name not in self._session_metrics:
            self._session_metrics[name] = 0
        self._session_metrics[name] += value

    def record_task_event(
        self,
        task_id: UUID,
        event_type: EventType,
        message: str,
        duration_ms: Optional[float] = None,
        metrics: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
    ) -> None:
        """
        Record a task-related event.

        Args:
            task_id: Task ID
            event_type: Type of task event
            message: Event message
            duration_ms: Task duration
            metrics: Task metrics
            error: Exception if failed
        """
        context = {"task_id": str(task_id)}
        error_message = None
        error_type = None
        
        if error:
            error_message = str(error)
            error_type = type(error).__name__

        self.record_event(
            event_type=event_type,
            message=message,
            severity=EventSeverity.ERROR if error else EventSeverity.INFO,
            context=context,
            duration_ms=duration_ms,
            metrics=metrics,
            error_message=error_message,
            error_type=error_type,
        )

    def record_analysis_event(
        self,
        target_path: str,
        event_type: EventType,
        message: str,
        metrics: Optional[Dict[str, Any]] = None,
        issues: Optional[List[Dict[str, Any]]] = None,
        error: Optional[Exception] = None,
    ) -> None:
        """
        Record an analysis-related event.

        Args:
            target_path: Path being analyzed
            event_type: Type of analysis event
            message: Event message
            metrics: Analysis metrics
            issues: Issues found
            error: Exception if failed
        """
        context = {
            "target_path": target_path,
            "issues_count": len(issues) if issues else 0,
        }
        
        error_message = None
        error_type = None
        
        if error:
            error_message = str(error)
            error_type = type(error).__name__

        self.record_event(
            event_type=event_type,
            message=message,
            severity=EventSeverity.ERROR if error else EventSeverity.INFO,
            context=context,
            metrics=metrics,
            error_message=error_message,
            error_type=error_type,
        )

    def get_session_metrics(self) -> Dict[str, float]:
        """Get accumulated session metrics."""
        return self._session_metrics.copy()

    def get_event_count(self) -> int:
        """Get total event count."""
        return len(self._event_buffer)

    def get_events(self) -> List[TelemetryEvent]:
        """Get buffered events."""
        return self._event_buffer.copy()

    def get_metrics(self) -> List[MetricPoint]:
        """Get buffered metrics."""
        return self._metric_buffer.copy()

    def flush(self) -> None:
        """
        Flush telemetry data (write to disk, send to remote, etc.).
        """
        # Flush adapter if available
        if self.adapter:
            try:
                self.adapter.flush()
            except Exception as e:
                logger.error(f"Error flushing telemetry adapter: {e}")

        # Could optionally clear buffers after flush
        # self._event_buffer.clear()
        # self._metric_buffer.clear()

    def clear_buffers(self) -> None:
        """Clear in-memory buffers."""
        self._event_buffer.clear()
        self._metric_buffer.clear()

    # ========================================================================
    # Internal Helpers
    # ========================================================================

    def _write_event(self, event: TelemetryEvent) -> None:
        """Write event to local storage (JSONL format)."""
        try:
            # Check file size and rotate if needed
            if self.events_file.exists() and self.events_file.stat().st_size > self.MAX_EVENTS_FILE_SIZE:
                self._rotate_events_file()

            # Append event as JSON line
            with open(self.events_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Error writing telemetry event: {e}")

    def _rotate_events_file(self) -> None:
        """Rotate events file when it exceeds max size."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_name = f"events_{timestamp}.jsonl"
            rotated_path = self.telemetry_dir / rotated_name
            self.events_file.rename(rotated_path)
            logger.debug(f"Rotated events file: {rotated_path}")
        except Exception as e:
            logger.error(f"Error rotating events file: {e}")

    def _forward_to_adapter(self, event: TelemetryEvent) -> None:
        """Forward event to telemetry adapter."""
        if not self.adapter:
            return

        try:
            # Map event type to appropriate log level
            level_map = {
                EventSeverity.DEBUG: "debug",
                EventSeverity.INFO: "info",
                EventSeverity.WARNING: "warning",
                EventSeverity.ERROR: "error",
                EventSeverity.CRITICAL: "critical",
            }
            
            log_level = level_map.get(event.severity, "info")
            
            # Create log entry
            log_context = {
                "event_type": event.event_type.value,
                "agent_id": str(event.agent_id),
                **event.context,
            }
            
            if event.duration_ms is not None:
                log_context["duration_ms"] = event.duration_ms
            
            if event.metrics:
                log_context["metrics"] = event.metrics
            
            # Log through adapter
            # Note: This assumes a standard logging interface
            if hasattr(self.adapter, "log"):
                self.adapter.log(
                    message=event.message,
                    level=log_level,
                    **log_context
                )
        except Exception as e:
            logger.debug(f"Error forwarding to adapter: {e}")

    def load_events(self) -> List[Dict[str, Any]]:
        """
        Load events from local storage.

        Returns:
            List of event dictionaries
        """
        if not self.events_file.exists():
            return []

        events = []
        try:
            with open(self.events_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        events.append(json.loads(line))
        except Exception as e:
            logger.error(f"Error loading events: {e}")

        return events


__all__ = [
    "AgentTelemetryManager",
    "TelemetryEvent",
    "MetricPoint",
    "EventType",
    "EventSeverity",
]
