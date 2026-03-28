"""Storage adapter using Supabase (PostgreSQL) for vibe history persistence."""

import asyncio
from pathlib import Path
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
        """
        Initialize the adapter's internal state for lazy Supabase client management.
        
        Sets up cached attributes used during client creation and tracking:
        - _client: cached Supabase client instance or None until created.
        - _url: cached Supabase URL used to create the client.
        - _key: cached Supabase service or anon key used to create the client.
        - _initialized: flag indicating whether an initialization attempt has completed.
        """
        self._client: Optional[Client] = None
        self._url: Optional[str] = None
        self._key: Optional[str] = None
        self._initialized = False

    def get_metadata(self) -> AdapterMetadata:
        """
        Provide adapter metadata for the Supabase storage adapter.
        
        Returns:
            AdapterMetadata: Metadata containing the adapter's name ("supabase"), version ("0.1.0"), a short description indicating JSONB support, and the runtime dependency list (["supabase"]).
        """
        return AdapterMetadata(
            name="supabase",
            version="0.1.0",
            description="Supabase cloud storage for vibe history with JSONB support.",
            dependencies=["supabase"],
        )

    async def is_available(self) -> bool:
        """
        Indicates whether the Supabase storage adapter can be used.
        
        @returns `true` if the Supabase client library is installed and available, `false` otherwise.
        """
        return HAS_SUPABASE

    async def _ensure_client(self) -> Optional[Client]:
        """
        Create and cache a Supabase client using environment credentials if available.
        
        Attempts to build a client from SUPABASE_URL and SUPABASE_SERVICE_KEY (or SUPABASE_ANON_KEY), stores it on the instance, and marks the adapter initialized. Returns `None` if the supabase library is unavailable, required environment variables are missing, or client construction fails.
        
        Returns:
            Client or `None`: The cached `Client` instance if created, `None` otherwise.
        """
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
        """
        Plugin hook that saves a report to Supabase and returns the stored row ID.
        
        Parameters:
        	report (Any): A report object or mapping; if the object supports `model_dump`, its dict representation will be used.
        
        Returns:
        	inserted_id (Optional[str]): The ID of the inserted report row as a string on success, or `None` if the adapter is not available.
        """
        return await self.save_report(report)

    async def save_report(self, report: Any) -> str:
        """
        Persist a report into the Supabase "reports" table and return the inserted row's ID.
        
        The function accepts either a dict-like report or an object exposing `model_dump()`. It extracts repository and VCS context (falling back to sensible defaults), writes summary fields and the full report JSON into the `reports` table, and returns the database ID of the inserted row.
        
        Parameters:
            report (Any): Report data as a dict or an object with a `model_dump()` method.
        
        Returns:
            str: The ID of the inserted report row.
        
        Raises:
            RuntimeError: If the Supabase client is not available, if the insert returns no data, or if insertion fails.
        """
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
            """
            Execute insertion of the prepared `row` into the Supabase "reports" table and return the response.
            
            Returns:
                The Supabase response object returned by the client's `execute()` call (contains `data`, `error`, and related fields).
            """
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
        """
        Fetches recent report rows from Supabase ordered by timestamp descending.
        
        Parameters:
            limit (int): Maximum number of rows to return.
        
        Returns:
            List[Any]: A list of row dictionaries from the `reports` table, ordered newest first.
        
        Raises:
            RuntimeError: If the Supabase client is not available or if fetching the history fails.
        """
        client = await self._ensure_client()
        if client is None:
            raise RuntimeError(
                "Supabase client not available. Ensure supabase is installed and "
                "SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables are set."
            )

        def _select():
            """
            Query the Supabase "reports" table for the most recent rows limited by the enclosing `limit` value.
            
            Returns:
                The Supabase query response object from execute(), which includes the retrieved rows (accessible via `res.data`) and any metadata or error information.
            """
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
        """
        Return adapter metadata formatted for the plugin manager.
        
        Returns:
            metadata (Dict[str, Any]): Mapping with keys "name", "version", "description", "dependencies", and "available" where "available" is `True` if the Supabase client dependency was successfully imported, otherwise `False`.
        """
        meta = self.get_metadata()
        return {
            "name": meta.name,
            "version": meta.version,
            "description": meta.description,
            "dependencies": meta.dependencies,
            "available": HAS_SUPABASE,
        }
