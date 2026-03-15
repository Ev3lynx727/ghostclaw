"""
LLM provider initialization and client creation for Ghostclaw.
"""

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

def create_client(config):
    if config.ai_provider == "anthropic":
        return AsyncAnthropic(api_key=config.api_key), config.ai_model or "claude-3-5-sonnet-20241022"

    base_url = None
    if config.ai_provider == "openrouter":
        base_url = "https://openrouter.ai/api/v1"

    return AsyncOpenAI(api_key=config.api_key, base_url=base_url), config.ai_model or "gpt-4o"
