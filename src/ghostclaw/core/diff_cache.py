"""
In-memory LRU cache for Git diffs during delta analysis.

Stores diff results (DiffResult objects) keyed by (repo_path, base_ref, current_sha).
Since diffs can be large, the cache is bounded by entry count (default 128).
"""

from collections import OrderedDict
from typing import Optional, Tuple, Any


class DiffCache:
    """Simple bounded LRU cache for diff results."""

    def __init__(self, maxsize: int = 128):
        self.maxsize = maxsize
        self._cache: OrderedDict[Tuple[str, str, str], Any] = OrderedDict()

    def _key(self, repo_path: str, base_ref: str, current_sha: str) -> Tuple[str, str, str]:
        return (repo_path, base_ref, current_sha)

    def get(self, repo_path: str, base_ref: str, current_sha: str) -> Optional[Any]:
        """Retrieve a cached diff if present, moving it to the end (most recently used)."""
        key = self._key(repo_path, base_ref, current_sha)
        if key not in self._cache:
            return None
        # Move to end to mark as recently used
        self._cache.move_to_end(key)
        return self._cache[key]

    def set(self, repo_path: str, base_ref: str, current_sha: str, value: Any) -> None:
        """Store a diff in the cache, evicting oldest entries if over capacity."""
        key = self._key(repo_path, base_ref, current_sha)
        if key in self._cache:
            # Update existing and move to end
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self.maxsize:
            self._cache.popitem(last=False)  # remove oldest

    def clear(self) -> None:
        """Clear all entries."""
        self._cache.clear()


# Global singleton used by analyzer
diff_cache = DiffCache()
