"""
Vibe score calculation logic for Ghostclaw.
"""

from ghostclaw.core.score import ScoringEngine

async def compute_vibe(context_data: dict) -> int:
    """
    Compute the final vibe score, allowing for custom adapter overrides.
    """
    from ghostclaw.core.adapters.registry import registry

    custom_score = await registry.compute_custom_vibe(context=context_data)
    if custom_score is not None:
        return int(custom_score)

    return ScoringEngine.compute_vibe_score(
        context_data["metrics"],
        len(context_data["issues"]),
        len(context_data["ghosts"])
    )
