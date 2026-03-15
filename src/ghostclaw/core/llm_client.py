import json
import logging
import asyncio
from typing import AsyncGenerator, Optional
from pathlib import Path

import httpx
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from ghostclaw.core.config import GhostclawConfig


class TokenBudgetExceededError(ValueError):
    """Raised when token budget for LLM prompt is exceeded."""
    pass

# Setup logger for the file
logger = logging.getLogger("ghostclaw.llm_client")

try:
    import tiktoken
    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False


class TokenBudgetExceededError(Exception):
    pass


class LLMClient:
    """Wrapper for connecting to LLM providers using official SDKs."""

    def __init__(self, config: GhostclawConfig, repo_path: str):
        self.config = config
        self.repo_path = repo_path
        self.max_tokens = 100000  # Default sensible limit
        self.client = None
        # Token usage tracking
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.total_tokens: int = 0

        if self.config.ai_provider == "openrouter":
            base_url = "https://openrouter.ai/api/v1"
            self.model = self.config.ai_model or "anthropic/claude-3.5-sonnet"
            self.client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=base_url,
                default_headers={
                    "HTTP-Referer": "https://github.com/Ev3lynx727/ghostclaw",
                    "X-Title": "Ghostclaw Architecture Engine",
                }
            )
        elif self.config.ai_provider == "openai":
            self.model = self.config.ai_model or "gpt-4o"
            self.client = AsyncOpenAI(api_key=self.config.api_key)
        elif self.config.ai_provider == "anthropic":
            self.model = self.config.ai_model or "claude-3-5-sonnet-20241022"
            self.client = AsyncAnthropic(api_key=self.config.api_key)
        else:
            # Default to OpenRouter as fallback
            base_url = "https://openrouter.ai/api/v1"
            self.model = self.config.ai_model or "anthropic/claude-3.5-sonnet"
            self.client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=base_url,
                default_headers={
                    "HTTP-Referer": "https://github.com/Ev3lynx727/ghostclaw",
                    "X-Title": "Ghostclaw Architecture Engine",
                }
            )

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for a given text."""
        if HAS_TIKTOKEN:
            try:
                encoding = tiktoken.get_encoding("cl100k_base")
                return len(encoding.encode(text))
            except Exception:
                return len(text) // 4
        return len(text) // 4

    def _check_token_budget(self, prompt: str) -> str:
        """Check if prompt fits in budget; throw error or truncate if not."""
        token_count = self._estimate_tokens(prompt)

        # If dry run, just print and return
        if self.config.dry_run:
            print(f"[DRY RUN] Token budget check: Estimated {token_count} tokens.")
            print(f"[DRY RUN] Payload snippet:\n{prompt[:500]}...\n")
            return prompt

        if token_count > self.max_tokens:
            raise TokenBudgetExceededError(
                f"Prompt token count ({token_count}) exceeds the maximum allowed ({self.max_tokens}). "
                "Consider analyzing a smaller subset of the codebase or disabling AST graphs."
            )
        return prompt

    def _log_verbose(self, payload: dict, response_data: dict = None, error: str = None):
        """Log API requests and responses if verbose mode is enabled."""
        if not self.config.verbose:
            return

        debug_log_path = Path(self.repo_path) / ".ghostclaw" / "debug.log"
        debug_log_path.parent.mkdir(parents=True, exist_ok=True)

        log_entry = {"request": payload}
        if response_data:
            log_entry["response"] = response_data
        if error:
            log_entry["error"] = error

        try:
            with open(debug_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, indent=2) + "\n\n")
        except Exception as e:
            logger.error(f"Failed to write verbose log: {e}")

    async def generate_analysis(self, prompt: str) -> dict:
        """Generate analysis from the LLM. Returns dict with 'content' and optional 'reasoning'."""
        prompt = self._check_token_budget(prompt)

        if self.config.dry_run:
            return {"content": "Dry run enabled. API call skipped."}

        if not self.config.api_key:
            raise ValueError("API key not provided. Set GHOSTCLAW_API_KEY environment variable.")

        system_prompt = "You are Ghostclaw, an expert software architect. Analyze the provided codebase metrics and context, and output a markdown report detailing system-level flow, cohesion, and tech stack best practices."

        try:
            if self.config.ai_provider == "anthropic":
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text
                # Capture reasoning if present (Claude 3.7+)
                reasoning = getattr(response, 'thinking', None)
                # Track token usage
                if hasattr(response, 'usage') and response.usage:
                    self.prompt_tokens += response.usage.input_tokens
                    self.completion_tokens += response.usage.output_tokens
                    self.total_tokens = self.prompt_tokens + self.completion_tokens
                return {"content": content, "reasoning": reasoning}
            else:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ]
                )
                message = response.choices[0].message
                content = message.content
                reasoning = getattr(message, 'reasoning_content', None)
                # Track token usage
                if hasattr(response, 'usage') and response.usage:
                    self.prompt_tokens += response.usage.prompt_tokens
                    self.completion_tokens += response.usage.completion_tokens
                    self.total_tokens = self.prompt_tokens + self.completion_tokens
                return {"content": content, "reasoning": reasoning}

        except Exception as e:
            self._log_verbose({"model": self.model, "prompt_snippet": prompt[:100]}, error=str(e))
            raise e

    async def test_connection(self) -> bool:
        """Test the connection to the LLM provider."""
        if not self.client or not self.config.api_key:
            return False

        try:
            if self.config.ai_provider == "anthropic":
                # Anthropic doesn't have a models list endpoint, test with a minimal message
                await self.client.messages.create(
                    model=self.model,
                    max_tokens=1,
                    messages=[{"role": "user", "content": "ping"}]
                )
                return True
            else:
                # OpenAI and OpenRouter support listing models
                await self.client.models.list()
                return True
        except Exception:
            return False

    async def list_models(self) -> list:
        """List available models from the provider."""
        if not self.client or not self.config.api_key:
            return []

        try:
            if self.config.ai_provider in ["openrouter", "openai"]:
                response = await self.client.models.list()
                return sorted([m.id for m in response.data])
            else:
                return [self.model]
        except Exception:
            return [self.model]

    async def _retry(self, func, *args, **kwargs):
        """Retry wrapper for async non-generator functions."""
        attempts = 0
        while attempts < self.config.retry_attempts:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                attempts += 1
                if attempts >= self.config.retry_attempts:
                    raise
                # Do not retry on non-transient errors
                if isinstance(e, (TokenBudgetExceededError, ValueError)):
                    raise
                delay = min(self.config.retry_backoff_factor * (2 ** (attempts - 1)), self.config.retry_max_delay)
                logger.warning(f"Retry {attempts}/{self.config.retry_attempts} for {func.__name__} after error: {type(e).__name__}: {e}")
                await asyncio.sleep(delay)

    async def _retry_stream(self, gen_func, *args, **kwargs):
        """Retry wrapper for async generator functions."""
        attempts = 0
        while attempts < self.config.retry_attempts:
            try:
                async for item in gen_func(*args, **kwargs):
                    yield item
                return
            except Exception as e:
                attempts += 1
                if attempts >= self.config.retry_attempts:
                    raise
                if isinstance(e, (TokenBudgetExceededError, ValueError)):
                    raise
                delay = min(self.config.retry_backoff_factor * (2 ** (attempts - 1)), self.config.retry_max_delay)
                logger.warning(f"Retry stream {attempts}/{self.config.retry_attempts} for {gen_func.__name__} after error: {type(e).__name__}: {e}")
                await asyncio.sleep(delay)

    async def generate_analysis(self, prompt: str) -> dict:
        """Generate analysis from the LLM. Returns dict with 'content' and optional 'reasoning'."""
        prompt = self._check_token_budget(prompt)

        if self.config.dry_run:
            return {"content": "Dry run enabled. API call skipped."}

        if not self.config.api_key:
            raise ValueError("API key not provided. Set GHOSTCLAW_API_KEY environment variable.")

        system_prompt = "You are Ghostclaw, an expert software architect. Analyze the provided codebase metrics and context and output a markdown report detailing system-level flow, cohesion, and tech stack best practices."

        async def _api_call():
            if self.config.ai_provider == "anthropic":
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}]
                )
                content = response.content[0].text
                reasoning = getattr(response, 'thinking', None)
                return {"content": content, "reasoning": reasoning}
            else:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ]
                )
                message = response.choices[0].message
                content = message.content
                reasoning = getattr(message, 'reasoning_content', None)
                return {"content": content, "reasoning": reasoning}

        return await self._retry(_api_call)

    async def stream_analysis(self, prompt: str) -> AsyncGenerator[dict, None]:
        """Stream analysis from the LLM. Yields dicts with 'type' and 'content'."""
        prompt = self._check_token_budget(prompt)

        if self.config.dry_run:
            yield {"type": "content", "content": "Dry run enabled. API call skipped."}
            return

        if not self.config.api_key:
            raise ValueError("API key not provided. Set GHOSTCLAW_API_KEY environment variable.")

        system_prompt = "You are Ghostclaw, an expert software architect. Analyze the provided codebase metrics and context and output a markdown report detailing system-level flow, cohesion, and tech stack best practices."

        # Reset token counters for this stream
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0

        async def _stream_call():
            if self.config.ai_provider == "anthropic":
                async with self.client.messages.stream(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}]
                ) as stream:
                    async for event in stream:
                        if event.type == "text_delta" and event.text is not None:
                            yield {"type": "content", "content": event.text}
                        elif event.type == "thinking_delta" and event.thinking is not None:
                            yield {"type": "reasoning", "content": event.thinking}
                    # After stream completes, capture usage
                    usage = stream.get_final_usage()
                    if usage:
                        self.prompt_tokens += usage.input_tokens
                        self.completion_tokens += usage.output_tokens
                        self.total_tokens = self.prompt_tokens + self.completion_tokens
            else:
                stream = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    stream=True
                )
                async for chunk in stream:
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content is not None:
                        yield {"type": "content", "content": delta.content}
                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content is not None:
                        yield {"type": "reasoning", "content": delta.reasoning_content}
                    # Some providers include usage in the last chunk
                    if hasattr(chunk, 'usage') and chunk.usage:
                        self.prompt_tokens += chunk.usage.prompt_tokens
                        self.completion_tokens += chunk.usage.completion_tokens
                        self.total_tokens = self.prompt_tokens + self.completion_tokens

        async for item in self._retry_stream(_stream_call):
            yield item