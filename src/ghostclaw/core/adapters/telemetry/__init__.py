import os
import logging
from typing import Optional
from ghostclaw.core.adapters.telemetry.base import BaseTelemetryAdapter
from ghostclaw.core.adapters.telemetry.logfire_adapter import LogfireTelemetryAdapter

logger = logging.getLogger(__name__)

__all__ = ["BaseTelemetryAdapter", "LogfireTelemetryAdapter", "bootstrap_telemetry"]

def bootstrap_telemetry() -> Optional[BaseTelemetryAdapter]:
    """
    Early bootstrap for telemetry.
    Searches for an available telemetry adapter and initializes it.
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
