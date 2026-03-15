"""
Knowledge graph and MCP-related aggregation logic for Ghostclaw Memory.
"""

import json
import sqlite3
from collections import defaultdict
from typing import Any, Dict, List, Optional

try:
    import aiosqlite
except ImportError:
    pass

def _empty_knowledge_graph() -> Dict[str, Any]:
    return {
        "total_runs": 0,
        "stacks_seen": [],
        "score_trend": [],
        "recurring_issues": [],
        "recurring_ghosts": [],
        "recurring_flags": [],
        "coupling_hotspots": [],
    }

async def get_knowledge_graph(
    store: Any,
    repo_path: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Build a knowledge graph from accumulated analysis history.
    """
    if not store._db_exists():
        return _empty_knowledge_graph()

    async with aiosqlite.connect(store.db_path) as db:
        db.row_factory = sqlite3.Row

        if repo_path:
            query = (
                "SELECT report_json, timestamp, vibe_score, stack "
                "FROM reports WHERE repo_path = ? "
                "ORDER BY timestamp ASC LIMIT ?"
            )
            params = (repo_path, limit)
        else:
            query = (
                "SELECT report_json, timestamp, vibe_score, stack "
                "FROM reports ORDER BY timestamp ASC LIMIT ?"
            )
            params = (limit,)

        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()

    if not rows:
        return _empty_knowledge_graph()

    issue_counts: Dict[str, int] = defaultdict(int)
    ghost_counts: Dict[str, int] = defaultdict(int)
    flag_counts: Dict[str, int] = defaultdict(int)
    coupling_instability: Dict[str, List[float]] = defaultdict(list)
    score_trend: List[Dict[str, Any]] = []
    stacks_seen: set = set()

    for row in rows:
        row_dict = dict(row)
        score_trend.append({
            "timestamp": row_dict["timestamp"],
            "vibe_score": row_dict["vibe_score"],
        })
        if row_dict.get("stack"):
            stacks_seen.add(row_dict["stack"])

        try:
            report = json.loads(row_dict.get("report_json", "{}"))
        except (json.JSONDecodeError, TypeError):
            continue

        for issue in report.get("issues", []):
            if isinstance(issue, dict):
                key = issue.get("message", json.dumps(issue, sort_keys=True))
            else:
                key = str(issue)
            issue_counts[key] += 1
        for ghost in report.get("architectural_ghosts", []):
            if isinstance(ghost, dict):
                key = ghost.get("message", json.dumps(ghost, sort_keys=True))
            else:
                key = str(ghost)
            ghost_counts[key] += 1
        for flag in report.get("red_flags", []):
            if isinstance(flag, dict):
                key = flag.get("message", json.dumps(flag, sort_keys=True))
            else:
                key = str(flag)
            flag_counts[key] += 1

        # Aggregate coupling metrics
        coupling = report.get("coupling_metrics", {})
        for module, metrics in coupling.items():
            if isinstance(metrics, dict):
                instability = metrics.get("instability")
                if instability is not None:
                    coupling_instability[module].append(instability)

    # Build coupling hotspots: modules with average instability > 0.7
    coupling_hotspots = []
    for module, instabilities in coupling_instability.items():
        avg = sum(instabilities) / len(instabilities)
        if avg > 0.7:
            coupling_hotspots.append({
                "module": module,
                "avg_instability": round(avg, 3),
                "occurrences": len(instabilities),
            })
    coupling_hotspots.sort(key=lambda x: x["avg_instability"], reverse=True)

    # Sort recurring items by frequency (descending)
    def _top_items(counts: Dict[str, int], top_n: int = 20) -> List[Dict[str, Any]]:
        sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [
            {"item": item, "count": count}
            for item, count in sorted_items[:top_n]
        ]

    return {
        "total_runs": len(rows),
        "stacks_seen": sorted(stacks_seen),
        "score_trend": score_trend,
        "recurring_issues": _top_items(issue_counts),
        "recurring_ghosts": _top_items(ghost_counts),
        "recurring_flags": _top_items(flag_counts),
        "coupling_hotspots": coupling_hotspots[:20],
    }
