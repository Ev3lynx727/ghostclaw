"""
Stack detection and analyzer coordination logic.
"""

from ghostclaw.core.detector import detect_stack
from ghostclaw.stacks import get_analyzer

async def get_stack_info(root: str):
    """Detect stack and return corresponding analyzer instance."""
    import asyncio
    stack = await asyncio.to_thread(detect_stack, root)
    analyzer = get_analyzer(stack)
    return stack, analyzer
