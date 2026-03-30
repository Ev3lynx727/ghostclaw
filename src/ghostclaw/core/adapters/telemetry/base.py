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
        """
        Adapter type identifier for telemetry adapters.
        
        Returns:
            The adapter category string "telemetry".
        """
        return "telemetry"

    @abstractmethod
    def get_metadata(self) -> AdapterMetadata:
        """
        Provide the adapter's metadata used for registry listing and discovery.
        
        The returned AdapterMetadata should include at least the adapter's name, version, and description so the adapter can be represented in registries and listings.
        
        Returns:
            AdapterMetadata: Metadata describing the adapter (name, version, description).
        """
        pass

    async def is_available(self) -> bool:
        """
        Determine whether the telemetry provider is available.
        
        Returns:
            True if the provider is available, False otherwise. The base implementation always returns True.
        """
        return True

    @abstractmethod
    def initialize(self, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the telemetry engine and perform any provider-specific startup work.
        
        This method is invoked early in application entry points to configure and start the telemetry integration using optional runtime information.
        
        Parameters:
            context (Optional[Dict[str, Any]]): Optional initialization context such as configuration values, environment details, or integration-specific options.
        """
        pass

    @abstractmethod
    def flush(self) -> None:
        """
        Force any buffered telemetry to be transmitted or persisted before the process exits.
        
        Implementations must ensure queued telemetry is sent or reliably stored before returning; this method is intended to be called during shutdown to avoid data loss.
        """
        pass

    def ghost_get_metadata(self) -> Dict[str, Any]:
        """
        Provide adapter metadata as a plain dictionary for registry listing.
        
        Returns:
            dict: A mapping with keys "name", "version", and "description" taken from the adapter's metadata.
        """
        meta = self.get_metadata()
        return {
            "name": meta.name,
            "version": meta.version,
            "description": meta.description
        }
