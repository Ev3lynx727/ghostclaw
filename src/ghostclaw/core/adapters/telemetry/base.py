"""Base abstractions for Ghostclaw telemetry and observability adapters."""

from abc import abstractmethod
from typing import Dict, Any, Optional
from ghostclaw.core.adapters.base import BaseAdapter, AdapterMetadata

class BaseTelemetryAdapter(BaseAdapter):
    """
    Interface for telemetry adapters (Logfire, Sentry, etc.).
    Unlike scoring adapters, telemetry adapters are initialized early in the process lifecycle.
    """

    @property
    def adapter_type(self) -> str:
        return "telemetry"

    @abstractmethod
    def get_metadata(self) -> AdapterMetadata:
        pass

    async def is_available(self) -> bool:
        """Check if the telemetry provider is installed."""
        return True

    @abstractmethod
    def initialize(self, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the telemetry engine.
        Should be called as early as possible in the entry points.
        """
        pass

    @abstractmethod
    def flush(self) -> None:
        """
        Force flush any buffered telemetry data before exit.
        """
        pass

    def ghost_get_metadata(self) -> Dict[str, Any]:
        """Return plugin metadata for registry listing."""
        meta = self.get_metadata()
        return {
            "name": meta.name,
            "version": meta.version,
            "description": meta.description
        }
