"""
Retry logic and token budgeting for Ghostclaw LLM Client.
"""

import asyncio
import logging
from typing import Any, Callable

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False

logger = logging.getLogger("ghostclaw.llm_client.retry")

class TokenBudgetExceededError(Exception):
    """Raised when token budget for LLM prompt is exceeded."""
    pass

def estimate_tokens(text: str) -> int:
    """Estimate token count for a given text."""
    if HAS_TIKTOKEN:
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            return len(text) // 4
    return len(text) // 4

async def with_retry(func: Callable, config, *args, **kwargs):
    """Retry wrapper for async non-generator functions."""
    attempts = 0
    while attempts < (getattr(config, 'retry_attempts', 1)):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            attempts += 1
            if attempts >= getattr(config, 'retry_attempts', 1):
                raise
            if isinstance(e, (TokenBudgetExceededError, ValueError)):
                raise
            delay = min(getattr(config, 'retry_backoff_factor', 1) * (2 ** (attempts - 1)), getattr(config, 'retry_max_delay', 60))
            logger.warning(f"Retry {attempts} after error: {e}")
            await asyncio.sleep(delay)

async def with_retry_stream(gen_func: Callable, config, *args, **kwargs):
    """Retry wrapper for async generator functions."""
    attempts = 0
    while attempts < (getattr(config, 'retry_attempts', 1)):
        try:
            async for item in gen_func(*args, **kwargs):
                yield item
            return
        except Exception as e:
            attempts += 1
            if attempts >= getattr(config, 'retry_attempts', 1):
                raise
            if isinstance(e, (TokenBudgetExceededError, ValueError)):
                raise
            delay = min(getattr(config, 'retry_backoff_factor', 1) * (2 ** (attempts - 1)), getattr(config, 'retry_max_delay', 60))
            logger.warning(f"Retry stream {attempts} after error: {e}")
            await asyncio.sleep(delay)
