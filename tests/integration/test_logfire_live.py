import os
import pytest
import logfire
from ghostclaw.lib.telemetry import init_telemetry

def test_logfire_live_reporting(monkeypatch):
    """
    This test actually sends data to Logfire.
    It should only be run manually or in environments where Logfire is configured.
    """
    # Ensure telemetry is enabled
    monkeypatch.setenv("GHOSTCLAW_TELEMETRY", "1")
    
    # Initialize real telemetry
    init_telemetry()
    
    # Create a manual span that should appear in the dashboard
    with logfire.span("Ghostclaw Live Integration Test"):
        logfire.info("If you see this, native Logfire integration is Working!")
        print("\n[!] Check your Logfire dashboard for 'Ghostclaw Live Integration Test'")

if __name__ == "__main__":
    # Allow running directly
    os.environ["GHOSTCLAW_TELEMETRY"] = "1"
    init_telemetry()
    with logfire.span("Ghostclaw Manual Run"):
        print("Manual span started...")
