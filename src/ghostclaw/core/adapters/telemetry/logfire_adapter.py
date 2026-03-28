"""Logfire telemetry implementation for Ghostclaw."""

import os
import logging
from typing import Dict, Any, Optional
from ghostclaw.core.adapters.telemetry.base import BaseTelemetryAdapter
from ghostclaw.core.adapters.hooks import hookimpl

logger = logging.getLogger(__name__)

try:
    import logfire
except ImportError:
    logfire = None

if logfire is not None and hasattr(logfire, "__file__"):
    # If shadowing occurs, this file will be the same as the current file
    pass

class LogfireTelemetryAdapter(BaseTelemetryAdapter):
    """
    Logfire implementation of the Telemetry Adapter.
    Heavily integrated with Pydantic Logfire for observability.
    """

    def __init__(self):
        self._initialized = False

    @property
    def name(self) -> str:
        return "logfire"

    def get_metadata(self) -> Any:
        from ghostclaw.core.adapters.base import AdapterMetadata
        return AdapterMetadata(
            name=self.name,
            version="1.0.0",
            description="Pydantic Logfire telemetry integration",
            supports_per_file_cache=False
        )

    async def is_available(self) -> bool:
        return logfire is not None

    def initialize(self, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Configure Logfire based on GHOSTCLAW_TELEMETRY environment variable.
        """
        if os.environ.get("GHOSTCLAW_TELEMETRY") != "1":
            return

        if logfire is None:
            logger.warning("Logfire package not found. Telemetry disabled.")
            return

        try:
            # Configure Logfire
            logfire.configure(
                # Ensure we don't block the startup too long
                send_to_logfire=True,
            )
            
            # Basic instrumentations
            logfire.instrument_httpx()
            
            self._initialized = True
            logger.debug("Logfire telemetry initialized successfully.")
            
        except ImportError as e:
            logger.warning(f"Logfire dependencies missing: {e}. Telemetry disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize Logfire: {e}")

    @hookimpl
    def ghost_get_metadata(self) -> Dict[str, Any]:
        """Return plugin metadata for registry listing."""
        meta = self.get_metadata()
        return {
            "name": meta.name,
            "version": meta.version,
            "description": meta.description
        }

    def flush(self) -> None:
        """Force flush Logfire spans."""
        if self._initialized and logfire is not None:
            try:
                logfire.shutdown()
            except Exception as e:
                logger.error(f"Failed to shutdown Logfire: {e}")
