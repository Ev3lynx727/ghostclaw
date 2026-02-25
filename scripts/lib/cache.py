"""Vibe score history cache — track repository health over time."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class VibeCache:
    """Stores historical vibe scores for repositories."""

    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            cache_dir = Path.home() / ".cache" / "ghostclaw"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "vibe_history.json"

    def load(self) -> Dict:
        """Load the cache dictionary."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save(self, data: Dict):
        """Save the cache dictionary."""
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def get_history(self, repo_url: str) -> List[Dict]:
        """Get vibe score history for a repository."""
        data = self.load()
        return data.get(repo_url, [])

    def record_score(self, repo_url: str, vibe_score: int, metadata: Dict = None):
        """Record a new vibe score for a repository."""
        data = self.load()
        if repo_url not in data:
            data[repo_url] = []

        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "vibe_score": vibe_score,
            "metadata": metadata or {}
        }
        data[repo_url].append(entry)

        # Keep only last 50 entries per repo
        if len(data[repo_url]) > 50:
            data[repo_url] = data[repo_url][-50:]

        self.save(data)

    def get_latest_score(self, repo_url: str) -> Optional[int]:
        """Get the most recent vibe score for a repository."""
        history = self.get_history(repo_url)
        if history:
            return history[-1]["vibe_score"]
        return None

    def get_score_delta(self, repo_url: str) -> Optional[int]:
        """Get the change in vibe score compared to previous entry."""
        history = self.get_history(repo_url)
        if len(history) >= 2:
            return history[-1]["vibe_score"] - history[-2]["vibe_score"]
        elif len(history) == 1:
            return history[-1]["vibe_score"]  # No previous, return current as delta from unknown
        return None
