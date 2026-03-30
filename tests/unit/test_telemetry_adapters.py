import pytest
from unittest.mock import patch
from ghostclaw.core.adapters.telemetry.logfire_adapter import LogfireTelemetryAdapter

def test_logfire_adapter_inheritance():
    """Verify Logfire adapter inherits from BaseTelemetryAdapter."""
    from ghostclaw.core.adapters.telemetry.base import BaseTelemetryAdapter
    adapter = LogfireTelemetryAdapter()
    assert isinstance(adapter, BaseTelemetryAdapter)
    assert adapter.adapter_type == "telemetry"

def test_logfire_metadata():
    """Verify Logfire adapter metadata."""
    adapter = LogfireTelemetryAdapter()
    metadata = adapter.get_metadata()
    assert metadata.name == "logfire"
    assert "Pydantic Logfire" in metadata.description

def test_logfire_initialization_enabled(monkeypatch):
    """Verify Logfire configuration is called when enabled."""
    monkeypatch.setenv("GHOSTCLAW_TELEMETRY", "1")
    adapter = LogfireTelemetryAdapter()
    
    with patch("ghostclaw.core.adapters.telemetry.logfire_adapter.logfire") as mock_lf:
        # We must ensure logfire is not None in the mock context
        if mock_lf is None:
             pytest.skip("Could not patch logfire")
             
        adapter.initialize()
        mock_lf.configure.assert_called_once()
        mock_lf.instrument_httpx.assert_called_once()
        assert adapter._initialized is True

def test_logfire_initialization_disabled(monkeypatch):
    """Verify Logfire is NOT configured when disabled."""
    monkeypatch.setenv("GHOSTCLAW_TELEMETRY", "0")
    adapter = LogfireTelemetryAdapter()
    
    with patch("ghostclaw.core.adapters.telemetry.logfire_adapter.logfire") as mock_lf:
        adapter.initialize()
        mock_lf.configure.assert_not_called()
        assert adapter._initialized is False

def test_logfire_flush(monkeypatch):
    """Verify Logfire shutdown is called on flush if initialized."""
    adapter = LogfireTelemetryAdapter()
    adapter._initialized = True
    
    with patch("ghostclaw.core.adapters.telemetry.logfire_adapter.logfire") as mock_lf:
        # Mock logfire as not None
        import ghostclaw.core.adapters.telemetry.logfire_adapter as logfire_mod
        monkeypatch.setattr(logfire_mod, "logfire", mock_lf)
        
        adapter.flush()
        mock_lf.shutdown.assert_called_once()

def test_logfire_flush_uninitialized():
    """Verify Logfire shutdown is NOT called if not initialized."""
    adapter = LogfireTelemetryAdapter()
    adapter._initialized = False
    
    with patch("ghostclaw.core.adapters.telemetry.logfire_adapter.logfire") as mock_lf:
        adapter.flush()
        mock_lf.shutdown.assert_not_called()
