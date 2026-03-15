"""
Scoring logic for Ghostclaw analyzer.
"""

from typing import Dict, Any, Optional
from ghostclaw.core.score import ScoringEngine


class VibeScorer:
    """Orchestrates vibe score calculation, potentially using custom scoring adapters."""

    @staticmethod
    async def compute_score(context: Dict[str, Any]) -> int:
        """
        Compute the final vibe score.
        
        Attempts to use a custom ScoringAdapter from the registry first, 
        otherwise falls back to ScoringEngine default.
        """
        from ghostclaw.core.adapters.registry import registry
        
        custom_score = await registry.compute_custom_vibe(context=context)
        if custom_score is not None:
            return int(custom_score)
        
        return ScoringEngine.compute_vibe_score(
            context.get("metrics", {}), 
            len(context.get("issues", [])), 
            len(context.get("ghosts", []))
        )
