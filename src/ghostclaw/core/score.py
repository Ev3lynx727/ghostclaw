from typing import Dict

class ScoringEngine:
    """Core mathematical engine for calculating architectural vibe scores."""

    @staticmethod
    def compute_vibe_score(metrics: Dict, issue_count: int, ghost_count: int) -> int:
        """Calculate the final vibe score (0-100)."""
        score = 100
        large_file_penalty = min(30, metrics.get('large_file_count', 0) * 5)
        score -= large_file_penalty

        avg = metrics.get('average_lines', 0)
        if avg > 200:
            score -= 10

        score -= min(20, issue_count * 3)
        score -= min(15, ghost_count * 5)

        return max(0, min(100, score))
