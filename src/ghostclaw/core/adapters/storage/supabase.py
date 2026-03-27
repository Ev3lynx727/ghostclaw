"""Storage adapter using Supabase (PostgreSQL) for vibe history persistence."""

import json
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ghostclaw.core.adapters.base import StorageAdapter, AdapterMetadata
from ghostclaw.core.adapters.hooks import hookimpl

# Supabase is optional; check availability
if TYPE_CHECKING:
    # Only for type hints; avoid import at runtime if supabase not installed
    try:
        from supabase import Client
    except ImportError:
        Client = Any  # type: ignore
else:
    Client = Any  # type: ignore

try:
    from supabase import create_client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False
    create_client = None  # type: ignore


class SupabaseStorageAdapter(StorageAdapter):
    """Persists ArchitectureReports to a Supabase (PostgreSQL) database."""

    def __init__(self):
        self._client: Optional[Client] = None
        self._url: Optional[str] = None
        self._key: Optional[str] = None
        self._initialized = False

    def get_metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            name="supabase",
            version="0.1.0",
            description="Supabase cloud storage for vibe history with JSONB support.",
            dependencies=["supabase"],
        )

    async def is_available(self) -> bool:
        """Supabase adapter is available if the supabase library is installed."""
        return HAS_SUPABASE

    async def _ensure_client(self) -> Optional[Client]:
        """Initialize Supabase client from environment if not already done."""
        if self._client is not None:
            return self._client

        if not HAS_SUPABASE:
            return None

        # Read credentials from environment (or could be from config)
        import os

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")

        if not url or not key:
            return None

        try:
            client = create_client(url, key)
            self._client = client
            self._url = url
            self._key = key
            self._initialized = True
            return client
        except Exception:
            return None

    @hookimpl
    async def ghost_save_report(self, report: Any) -> Optional[str]:
        """Hook implementation for saving report."""
        return await self.save_report(report)

    async def save_report(self, report: Any) -> str:
        """Save a report to Supabase and return its ID."""
        client = await self._ensure_client()
        if client is None:
            raise RuntimeError(
                "Supabase client not available. Ensure supabase is installed and "
                "SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables are set."
            )

        # Convert report to dict
        if hasattr(report, "model_dump"):
            data = report.model_dump()
        else:
            data = report

        # Extract top-level fields for the reports table
        repo_path = (
            data.get("repo_path")
            or data.get("metadata", {}).get("repo_path")
            or str(Path.cwd())
        )
        vcs = data.get("metadata", {}).get("vcs", {})

        # Prepare row
        row = {
            "vibe_score": data.get("vibe_score", 0),
            "stack": data.get("stack", "unknown"),
            "files_analyzed": data.get("files_analyzed", 0),
            "total_lines": data.get("total_lines", 0),
            "repo_path": str(repo_path),
            "vcs_commit": vcs.get("commit", ""),
            "vcs_branch": vcs.get("branch", ""),
            "vcs_dirty": vcs.get("dirty", False),
            "report_json": data,  # Insert full report as JSONB (dict will be serialized)
        }

        # Perform insert in a thread to avoid blocking
        def _insert():
            res = client.table("reports").insert(row).execute()
            return res

        try:
            res = await asyncio.to_thread(_insert)
            # Supabase returns data; get the inserted ID
            if res.data and len(res.data) > 0:
                return str(res.data[0].get("id"))
            else:
                raise RuntimeError("No data returned from Supabase insert")
        except Exception as e:
            raise RuntimeError(f"Failed to insert report into Supabase: {e}")

    async def get_history(self, limit: int = 10) -> List[Any]:
        """Retrieve recent reports from Supabase."""
        client = await self._ensure_client()
        if client is None:
            raise RuntimeError(
                "Supabase client not available. Ensure supabase is installed and "
                "SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables are set."
            )

        def _select():
            res = (
                client.table("reports")
                .select("*")
                .order("timestamp", desc=True)
                .limit(limit)
                .execute()
            )
            return res

        try:
            res = await asyncio.to_thread(_select)
            rows = []
            for item in res.data:
                # item is a dict with all columns including report_json
                rows.append(item)
            return rows
        except Exception as e:
            raise RuntimeError(f"Failed to fetch history from Supabase: {e}")

    @hookimpl
    def ghost_get_metadata(self) -> Dict[str, Any]:
        """Expose metadata to the plugin manager."""
        meta = self.get_metadata()
        return {
            "name": meta.name,
            "version": meta.version,
            "description": meta.description,
            "dependencies": meta.dependencies,
            "available": HAS_SUPABASE,
        }
