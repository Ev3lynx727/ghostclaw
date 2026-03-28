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
        """
        Initialize the telemetry adapter and mark it as not configured.
        
        Sets the internal flag `self._initialized` to `False` to indicate Logfire has not been successfully configured yet.
        """
        self._initialized = False

    @property
    def name(self) -> str:
        """
        Adapter name used to identify this telemetry adapter.
        
        Returns:
            str: The adapter name `'logfire'`.
        """
        return "logfire"

    def get_metadata(self) -> Any:
        """
        Provide adapter metadata for the Logfire telemetry adapter.
        
        Returns:
            AdapterMetadata: Metadata with name "logfire", version "1.0.0", description "Pydantic Logfire telemetry integration", and supports_per_file_cache set to False.
        """
        from ghostclaw.core.adapters.base import AdapterMetadata
        return AdapterMetadata(
            name=self.name,
            version="1.0.0",
            description="Pydantic Logfire telemetry integration",
            supports_per_file_cache=False
        )

    async def is_available(self) -> bool:
        """
        Check whether the Logfire library is available for use.
        
        Returns:
            `true` if the Logfire package was successfully imported and is available, `false` otherwise.
        """
        return logfire is not None

    def initialize(self, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize Logfire telemetry when telemetry is enabled via the GHOSTCLAW_TELEMETRY environment variable.
        
        Performs conditional configuration and instrumentation of the Logfire client and marks the adapter as initialized on success. If telemetry is disabled or the Logfire package is unavailable, the function returns without side effects.
        
        Parameters:
            context (Optional[Dict[str, Any]]): Optional initialization context (currently unused).
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
        """
        Provide plugin metadata for registry listing.
        
        Returns:
            metadata (Dict[str, Any]): Dictionary containing the adapter's `name`, `version`, and `description`.
        """
        meta = self.get_metadata()
        return {
            "name": meta.name,
            "version": meta.version,
            "description": meta.description
        }

    def flush(self) -> None:
        """
        Shuts down Logfire to force a flush of any collected telemetry if the adapter was initialized.
        
        If Logfire is available and the adapter was initialized, calls logfire.shutdown(); failures during shutdown are logged.
        """
        if self._initialized and logfire is not None:
            try:
                logfire.shutdown()
            except Exception as e:
                logger.error(f"Failed to shutdown Logfire: {e}")
