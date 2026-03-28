from unittest.mock import patch

# We need to ensure the module is patched before bootstrap_telemetry uses it
def test_bootstrap_telemetry_disabled(monkeypatch):
    """Verify bootstrap returns None when telemetry is disabled."""
    monkeypatch.setenv("GHOSTCLAW_TELEMETRY", "0")
    from ghostclaw.core.adapters.telemetry import bootstrap_telemetry
    adapter = bootstrap_telemetry()
    assert adapter is None

def test_bootstrap_telemetry_enabled(monkeypatch):
    """Verify bootstrap returns an initialized adapter when enabled."""
    monkeypatch.setenv("GHOSTCLAW_TELEMETRY", "1")
    
    with patch("ghostclaw.core.adapters.telemetry.logfire.logfire") as mock_lf:
        # Manually ensure the module-level 'logfire' is our mock
        import ghostclaw.core.adapters.telemetry.logfire as logfire_mod
        monkeypatch.setattr(logfire_mod, "logfire", mock_lf)
        
        from ghostclaw.core.adapters.telemetry import bootstrap_telemetry
        adapter = bootstrap_telemetry()
        
        from ghostclaw.core.adapters.telemetry.logfire import LogfireTelemetryAdapter
        assert isinstance(adapter, LogfireTelemetryAdapter)
        assert adapter._initialized is True
        mock_lf.configure.assert_called_once()

def test_telemetry_bootstrap_idempotency(monkeypatch):
    """Verify calling bootstrap multiple times works correctly."""
    monkeypatch.setenv("GHOSTCLAW_TELEMETRY", "1")
    
    with patch("ghostclaw.core.adapters.telemetry.logfire.logfire") as mock_lf:
        import ghostclaw.core.adapters.telemetry.logfire as logfire_mod
        monkeypatch.setattr(logfire_mod, "logfire", mock_lf)
        
        from ghostclaw.core.adapters.telemetry import bootstrap_telemetry
        adapter1 = bootstrap_telemetry()
        adapter2 = bootstrap_telemetry()
        
        assert adapter1 is not None
        assert adapter2 is not None
        assert mock_lf.configure.call_count == 2
