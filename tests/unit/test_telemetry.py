import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from ghostclaw.core.adapters.telemetry import bootstrap_telemetry

def test_telemetry_disabled_by_default(monkeypatch):
    """Ensure telemetry does not start if GHOSTCLAW_TELEMETRY is 0 or unset."""
    monkeypatch.setenv("GHOSTCLAW_TELEMETRY", "0")
    
    with patch("ghostclaw.core.adapters.telemetry.logfire_adapter.logfire") as mock_lf:
        bootstrap_telemetry()
        mock_lf.configure.assert_not_called()

def test_telemetry_enabled_via_env(monkeypatch):
    """Ensure telemetry explicitly configures when GHOSTCLAW_TELEMETRY is 1."""
    monkeypatch.setenv("GHOSTCLAW_TELEMETRY", "1")
    
    with patch("ghostclaw.core.adapters.telemetry.logfire.logfire") as mock_lf:
        # Also ensure the module-level variable is the mock
        import ghostclaw.core.adapters.telemetry.logfire_adapter as logfire_mod
        monkeypatch.setattr(logfire_mod, "logfire", mock_lf)
        
        bootstrap_telemetry()
        mock_lf.configure.assert_called()
