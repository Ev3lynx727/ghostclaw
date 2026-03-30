import os
import logging
from typing import Optional
from ghostclaw.core.adapters.telemetry.base import BaseTelemetryAdapter
from ghostclaw.core.adapters.telemetry.logfire_adapter import LogfireTelemetryAdapter

# Alias the logfire_adapter module as `logfire` for compatibility
from . import logfire_adapter as logfire

logger = logging.getLogger(__name__)

__all__ = ["BaseTelemetryAdapter", "LogfireTelemetryAdapter", "bootstrap_telemetry", "logfire"]

def bootstrap_telemetry() -> Optional[BaseTelemetryAdapter]:
    """
    Bootstrap telemetry if enabled via GHOSTCLAW_TELEMETRY.
    
    If the environment variable GHOSTCLAW_TELEMETRY is set to "1", attempts to create and initialize a LogfireTelemetryAdapter and return it. If telemetry is not enabled or initialization fails, returns None.
    
    Returns:
        Optional[BaseTelemetryAdapter]: An initialized telemetry adapter when bootstrapping succeeds, `None` otherwise.
    """
    if os.environ.get("GHOSTCLAW_TELEMETRY") != "1":
        return None

    # We instantiate the default Logfire adapter. 
    # In a fully pluggable system, we'd scan 'ghostclaw.plugins' entry points here.
    try:
        adapter = LogfireTelemetryAdapter()
        adapter.initialize()
        return adapter
    except Exception as e:
        logger.error(f"Failed to bootstrap telemetry: {e}")
        return None
