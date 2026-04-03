"""
Tests for AgentTelemetryManager - Agent telemetry and observability.

Comprehensive test suite for event tracking, metrics collection,
telemetry session management, and integration with telemetry adapters.
"""

import pytest
import json
from datetime import timedelta
from uuid import UUID
from pathlib import Path
from unittest.mock import MagicMock, patch

from ghostclaw.core.agent_sdk.agent_telemetry import (
    AgentTelemetryManager,
    TelemetryEvent,
    MetricPoint,
    EventType,
    EventSeverity,
)


@pytest.fixture
def agent_id():
    """Create a test agent ID."""
    return UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def telemetry_manager(agent_id, tmp_path, monkeypatch):
    """Create a telemetry manager with mock settings."""
    # Mock the settings to use temp directory
    with patch("ghostclaw.core.agent_sdk.agent_telemetry.get_settings") as mock_settings:
        settings = MagicMock()
        settings.memory_base_dir = tmp_path / "memory"
        mock_settings.return_value = settings
        
        with patch("ghostclaw.core.agent_sdk.agent_telemetry.bootstrap_telemetry") as mock_bootstrap:
            mock_bootstrap.return_value = None
            manager = AgentTelemetryManager(agent_id)
            manager.telemetry_dir = tmp_path / "telemetry"
            manager.telemetry_dir.mkdir(parents=True, exist_ok=True)
            manager.events_file = manager.telemetry_dir / "events.jsonl"
            yield manager


class TestTelemetryEventModel:
    """Test TelemetryEvent model."""

    def test_event_creation(self, agent_id):
        """Test creating a telemetry event."""
        event = TelemetryEvent(
            event_type=EventType.AGENT_STARTED,
            agent_id=agent_id,
            message="Agent started successfully",
        )
        assert event.event_type == EventType.AGENT_STARTED
        assert event.agent_id == agent_id
        assert event.message == "Agent started successfully"
        assert event.severity == EventSeverity.INFO

    def test_event_with_context(self, agent_id):
        """Test event with context."""
        context = {"task_id": "123", "duration": 5.0}
        event = TelemetryEvent(
            event_type=EventType.TASK_COMPLETED,
            agent_id=agent_id,
            message="Task completed",
            context=context,
        )
        assert event.context == context

    def test_event_with_error(self, agent_id):
        """Test event with error information."""
        event = TelemetryEvent(
            event_type=EventType.TASK_FAILED,
            agent_id=agent_id,
            message="Task failed",
            severity=EventSeverity.ERROR,
            error_message="ValueError: invalid input",
            error_type="ValueError",
        )
        assert event.error_message == "ValueError: invalid input"
        assert event.error_type == "ValueError"

    def test_event_to_dict(self, agent_id):
        """Test converting event to dictionary."""
        event = TelemetryEvent(
            event_type=EventType.AGENT_STARTED,
            agent_id=agent_id,
            message="Started",
            severity=EventSeverity.INFO,
        )
        event_dict = event.to_dict()
        assert event_dict["event_type"] == "agent.started"
        assert event_dict["severity"] == "info"
        assert event_dict["message"] == "Started"


class TestMetricPointModel:
    """Test MetricPoint model."""

    def test_metric_creation(self):
        """Test creating a metric point."""
        metric = MetricPoint(name="cpu_usage", value=45.5)
        assert metric.name == "cpu_usage"
        assert metric.value == 45.5

    def test_metric_with_labels(self):
        """Test metric with labels."""
        labels = {"host": "server-1", "region": "us-west"}
        metric = MetricPoint(name="memory_usage", value=2048, labels=labels)
        assert metric.labels == labels


class TestTelemetryManagerBasics:
    """Test basic telemetry manager functionality."""

    def test_initialization(self, agent_id, telemetry_manager):
        """Test telemetry manager initialization."""
        assert telemetry_manager.agent_id == agent_id
        assert telemetry_manager.telemetry_dir is not None
        assert len(telemetry_manager._event_buffer) == 0

    def test_start_and_end_session(self, telemetry_manager):
        """Test session lifecycle."""
        telemetry_manager.start_session()
        assert telemetry_manager._session_started_at is not None
        assert len(telemetry_manager._event_buffer) >= 1
        
        telemetry_manager.end_session()
        assert "session_duration_ms" in telemetry_manager._session_metrics

    def test_record_event(self, telemetry_manager):
        """Test recording an event."""
        telemetry_manager.record_event(
            EventType.AGENT_STARTED,
            "Test event",
        )
        assert len(telemetry_manager._event_buffer) == 1
        event = telemetry_manager._event_buffer[0]
        assert event.message == "Test event"

    def test_record_event_with_context(self, telemetry_manager):
        """Test recording event with context."""
        context = {"user": "test", "module": "core"}
        telemetry_manager.record_event(
            EventType.ANALYSIS_STARTED,
            "Analysis starting",
            context=context,
        )
        event = telemetry_manager._event_buffer[0]
        assert event.context == context

    def test_record_event_with_metrics(self, telemetry_manager):
        """Test recording event with performance metrics."""
        metrics = {"items_processed": 100, "errors": 5}
        telemetry_manager.record_event(
            EventType.ANALYSIS_COMPLETED,
            "Analysis complete",
            metrics=metrics,
        )
        event = telemetry_manager._event_buffer[0]
        assert event.metrics == metrics

    def test_record_event_with_error(self, telemetry_manager):
        """Test recording error event."""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            telemetry_manager.record_event(
                EventType.AGENT_ERROR,
                "Error occurred",
                severity=EventSeverity.ERROR,
                error_message=str(e),
                error_type=type(e).__name__,
            )
        
        event = telemetry_manager._event_buffer[0]
        assert event.severity == EventSeverity.ERROR
        assert "Test error" in event.error_message


class TestMetricRecording:
    """Test metric recording functionality."""

    def test_record_metric(self, telemetry_manager):
        """Test recording a metric."""
        telemetry_manager.record_metric("test_metric", 42.5)
        assert len(telemetry_manager._metric_buffer) == 1
        metric = telemetry_manager._metric_buffer[0]
        assert metric.name == "test_metric"
        assert metric.value == 42.5

    def test_record_metric_with_labels(self, telemetry_manager):
        """Test recording metric with labels."""
        labels = {"service": "api", "endpoint": "/analyze"}
        telemetry_manager.record_metric("response_time_ms", 125.0, labels=labels)
        metric = telemetry_manager._metric_buffer[0]
        assert metric.labels == labels

    def test_metric_accumulation(self, telemetry_manager):
        """Test metric accumulation in session."""
        telemetry_manager.record_metric("processed_items", 10)
        telemetry_manager.record_metric("processed_items", 20)
        telemetry_manager.record_metric("processed_items", 30)
        
        assert telemetry_manager._session_metrics["processed_items"] == 60


class TestTaskEventRecording:
    """Test task-specific event recording."""

    def test_record_task_created_event(self, telemetry_manager):
        """Test recording task created event."""
        task_id = UUID("12345678-0000-0000-0000-000000000000")
        telemetry_manager.record_task_event(
            task_id,
            EventType.TASK_CREATED,
            "Task created successfully",
        )
        event = telemetry_manager._event_buffer[0]
        assert event.event_type == EventType.TASK_CREATED
        assert "task_id" in event.context

    def test_record_task_completed_event(self, telemetry_manager):
        """Test recording task completed event."""
        task_id = UUID("12345678-0000-0000-0000-000000000000")
        metrics = {"lines_analyzed": 1000, "issues_found": 5}
        telemetry_manager.record_task_event(
            task_id,
            EventType.TASK_COMPLETED,
            "Task completed",
            duration_ms=1500.5,
            metrics=metrics,
        )
        event = telemetry_manager._event_buffer[0]
        assert event.duration_ms == 1500.5
        assert event.metrics == metrics

    def test_record_task_failed_event(self, telemetry_manager):
        """Test recording task failed event."""
        task_id = UUID("12345678-0000-0000-0000-000000000000")
        error = RuntimeError("Task execution failed")
        telemetry_manager.record_task_event(
            task_id,
            EventType.TASK_FAILED,
            "Task failed with error",
            error=error,
        )
        event = telemetry_manager._event_buffer[0]
        assert event.severity == EventSeverity.ERROR
        assert "RuntimeError" in event.error_type


class TestAnalysisEventRecording:
    """Test analysis-specific event recording."""

    def test_record_analysis_started(self, telemetry_manager):
        """Test recording analysis started event."""
        telemetry_manager.record_analysis_event(
            "/src/path",
            EventType.ANALYSIS_STARTED,
            "Analysis starting for src/path",
        )
        event = telemetry_manager._event_buffer[0]
        assert event.event_type == EventType.ANALYSIS_STARTED
        assert event.context["target_path"] == "/src/path"

    def test_record_analysis_completed(self, telemetry_manager):
        """Test recording analysis completed event."""
        metrics = {"files": 50, "lines": 5000, "complexity": 3.5}
        issues = [{"severity": "high"}, {"severity": "medium"}]
        telemetry_manager.record_analysis_event(
            "/src/path",
            EventType.ANALYSIS_COMPLETED,
            "Analysis completed",
            metrics=metrics,
            issues=issues,
        )
        event = telemetry_manager._event_buffer[0]
        assert event.metrics == metrics
        assert event.context["issues_count"] == 2

    def test_record_analysis_failed(self, telemetry_manager):
        """Test recording analysis failed event."""
        error = FileNotFoundError("File not found: config.py")
        telemetry_manager.record_analysis_event(
            "/src/path",
            EventType.ANALYSIS_FAILED,
            "Analysis failed",
            error=error,
        )
        event = telemetry_manager._event_buffer[0]
        assert event.severity == EventSeverity.ERROR
        assert "FileNotFoundError" in event.error_type


class TestStorageAndPersistence:
    """Test event storage and persistence."""

    def test_write_event_to_disk(self, telemetry_manager):
        """Test writing event to disk."""
        telemetry_manager.record_event(
            EventType.AGENT_STARTED,
            "Test event",
        )
        assert telemetry_manager.events_file.exists()
        
        # Verify JSONL format
        with open(telemetry_manager.events_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data["message"] == "Test event"

    def test_load_events_from_disk(self, telemetry_manager):
        """Test loading events from disk."""
        # Write some events
        telemetry_manager.record_event(EventType.AGENT_STARTED, "Event 1")
        telemetry_manager.record_event(EventType.ANALYSIS_STARTED, "Event 2")
        
        # Load and verify
        loaded = telemetry_manager.load_events()
        assert len(loaded) == 2
        assert loaded[0]["message"] == "Event 1"
        assert loaded[1]["message"] == "Event 2"

    def test_load_empty_events(self, telemetry_manager):
        """Test loading from non-existent file."""
        loaded = telemetry_manager.load_events()
        assert loaded == []

    def test_file_rotation(self, telemetry_manager):
        """Test events file rotation when exceeding max size."""
        # Create large events to exceed rotation threshold
        telemetry_manager.MAX_EVENTS_FILE_SIZE = 500  # 500 bytes for testing
        
        large_context = {"data": "x" * 200}
        for i in range(10):
            telemetry_manager.record_event(
                EventType.CUSTOM,
                f"Large event {i}",
                context=large_context,
            )
        
        # Check that rotation occurred
        telemetry_files = list(telemetry_manager.telemetry_dir.glob("events*.jsonl"))
        assert len(telemetry_files) >= 1


class TestSessionManagement:
    """Test session management."""

    def test_session_metrics_tracking(self, telemetry_manager):
        """Test session metrics accumulation."""
        telemetry_manager.start_session()
        telemetry_manager.record_metric("cpu_usage", 25.0)
        telemetry_manager.record_metric("cpu_usage", 35.0)
        telemetry_manager.record_metric("memory_usage", 2048.0)
        
        metrics = telemetry_manager.get_session_metrics()
        assert metrics["cpu_usage"] == 60.0
        assert metrics["memory_usage"] == 2048.0

    def test_session_duration(self, telemetry_manager):
        """Test session duration tracking."""
        import time
        telemetry_manager.start_session()
        time.sleep(0.1)  # 100ms sleep
        telemetry_manager.end_session()
        
        metrics = telemetry_manager.get_session_metrics()
        assert "session_duration_ms" in metrics
        assert metrics["session_duration_ms"] >= 100

    def test_buffer_clearing(self, telemetry_manager):
        """Test clearing in-memory buffers."""
        telemetry_manager.record_event(EventType.AGENT_STARTED, "Event 1")
        telemetry_manager.record_metric("test", 42.0)
        
        assert len(telemetry_manager.get_events()) == 1
        assert len(telemetry_manager.get_metrics()) == 1
        
        telemetry_manager.clear_buffers()
        assert len(telemetry_manager.get_events()) == 0
        assert len(telemetry_manager.get_metrics()) == 0


class TestGetters:
    """Test getter methods."""

    def test_get_event_count(self, telemetry_manager):
        """Test getting event count."""
        telemetry_manager.record_event(EventType.AGENT_STARTED, "Event 1")
        telemetry_manager.record_event(EventType.AGENT_STARTED, "Event 2")
        assert telemetry_manager.get_event_count() == 2

    def test_get_events(self, telemetry_manager):
        """Test getting events list."""
        telemetry_manager.record_event(EventType.AGENT_STARTED, "Event 1")
        telemetry_manager.record_event(EventType.ANALYSIS_STARTED, "Event 2")
        
        events = telemetry_manager.get_events()
        assert len(events) == 2
        assert isinstance(events[0], TelemetryEvent)

    def test_get_metrics(self, telemetry_manager):
        """Test getting metrics list."""
        telemetry_manager.record_metric("cpu", 50.0)
        telemetry_manager.record_metric("memory", 2048.0)
        
        metrics = telemetry_manager.get_metrics()
        assert len(metrics) == 2
        assert isinstance(metrics[0], MetricPoint)

    def test_get_session_metrics(self, telemetry_manager):
        """Test getting session metrics."""
        telemetry_manager.record_metric("requests", 100)
        telemetry_manager.record_metric("errors", 5)
        
        metrics = telemetry_manager.get_session_metrics()
        assert metrics["requests"] == 100
        assert metrics["errors"] == 5


class TestEventTypes:
    """Test event type enumeration."""

    def test_all_event_types(self):
        """Test all event types are accessible."""
        event_types = [
            EventType.AGENT_CREATED,
            EventType.AGENT_STARTED,
            EventType.AGENT_STOPPED,
            EventType.TASK_CREATED,
            EventType.TASK_STARTED,
            EventType.TASK_COMPLETED,
            EventType.ANALYSIS_STARTED,
            EventType.ANALYSIS_COMPLETED,
            EventType.CUSTOM,
        ]
        assert len(event_types) == 9

    def test_all_severity_levels(self):
        """Test all severity levels are accessible."""
        levels = [
            EventSeverity.DEBUG,
            EventSeverity.INFO,
            EventSeverity.WARNING,
            EventSeverity.ERROR,
            EventSeverity.CRITICAL,
        ]
        assert len(levels) == 5


class TestErrorHandling:
    """Test error handling and resilience."""

    def test_record_event_without_message(self, telemetry_manager):
        """Test that message is required."""
        with pytest.raises(Exception):
            TelemetryEvent(event_type=EventType.AGENT_STARTED, agent_id=UUID("12345678-1234-5678-1234-567812345678"))

    def test_flush_with_adapter(self, telemetry_manager):
        """Test flush with telemetry adapter."""
        mock_adapter = MagicMock()
        telemetry_manager.adapter = mock_adapter
        
        telemetry_manager.flush()
        mock_adapter.flush.assert_called_once()

    def test_flush_without_adapter(self, telemetry_manager):
        """Test flush when no adapter is available."""
        telemetry_manager.adapter = None
        # Should not raise
        telemetry_manager.flush()
